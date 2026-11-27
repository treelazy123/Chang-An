#include <string.h>
#include "sdkconfig.h"
#include "parent_auth.h"
#include "mesh_access.h"
#include "node_role.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "esp_mesh_lite.h"
#include "esp_wifi.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "psa/crypto.h"

/* All crypto and ESP-NOW TX runs here, never in the Wi-Fi receive callback or
 * Mesh candidate callback. Wire packets are <=178 bytes, including type 200. */
#define SLOTS 8
#define FRAGMENT (PA_GRANT_SIZE/2)
#define FRAGMENT_SIZE (4+16+1+FRAGMENT)
#define PA_TYPE ESPNOW_DATA_TYPE_RESERVE
enum { DISCOVER=1, RADIO, GRANT };
typedef struct {
    uint8_t kind, src[6], dst[6];
    uint8_t required[32];
    uint16_t size;
    uint8_t data[PA_GRANT_SIZE];
} event_t;
typedef struct {
    bool used;
    uint8_t mac[6], nonce[16], parts, node[32], required[32];
    int64_t asked, sent, until, fragments_at, last_seen;
    uint8_t assembly[PA_GRANT_SIZE];
} candidate_t;
typedef struct {
    bool used;
    uint8_t mac[6], nonce[16];
    int64_t asked;
} forward_t;
extern const uint8_t auth_key[] asm("_binary_auth_key_start");
extern const uint8_t authority_pub[] asm("_binary_authority_pub_start");
static const char *TAG="parent_auth";
static QueueHandle_t inbox,requests;
static SemaphoreHandle_t lock;
static candidate_t candidates[SLOTS];
static forward_t forwards[SLOTS];
static uint8_t local_boot[16], local_ap[6], local_sta[6], own_nonce[16], own_public[65];
static uint8_t local_node[32], local_root[32];
static int64_t own_asked, own_until, own_sent, last_disconnect, radio_window;
static unsigned radio_count;
static bool online;
static bool selection_ready;
static psa_key_id_t signing_key;
static int64_t now_ms(void) { return esp_timer_get_time()/1000; }

static bool crypto_verify(const uint8_t *public,const void *data,size_t size,const uint8_t signature[64])
{
    psa_key_attributes_t attr=PSA_KEY_ATTRIBUTES_INIT;
    psa_key_id_t id=0;
    uint8_t hash[32];size_t length=0;
    psa_set_key_type(&attr,PSA_KEY_TYPE_ECC_PUBLIC_KEY(PSA_ECC_FAMILY_SECP_R1));
    psa_set_key_bits(&attr,256);
    psa_set_key_usage_flags(&attr,PSA_KEY_USAGE_VERIFY_HASH);
    psa_set_key_algorithm(&attr,PSA_ALG_ECDSA(PSA_ALG_SHA_256));
    bool ok=psa_hash_compute(PSA_ALG_SHA_256,data,size,hash,sizeof(hash),&length)==PSA_SUCCESS &&
        length==32 && psa_import_key(&attr,public,65,&id)==PSA_SUCCESS;
    if(ok) { ok=psa_verify_hash(id,PSA_ALG_ECDSA(PSA_ALG_SHA_256),hash,32,signature,64)==PSA_SUCCESS; }
    if(id) { psa_destroy_key(id); }
    psa_reset_key_attributes(&attr);
    return ok;
}
static bool crypto_sign(pa_request_t *request)
{
    uint8_t hash[32];size_t length=0;
    if(psa_hash_compute(PSA_ALG_SHA_256,(uint8_t*)request,PA_REQUEST_BODY,hash,sizeof(hash),&length)!=PSA_SUCCESS) { return false; }
    return length==32 && psa_sign_hash(signing_key,PSA_ALG_ECDSA(PSA_ALG_SHA_256),hash,32,
        request->signature,sizeof(request->signature),&length)==PSA_SUCCESS && length==64;
}
static bool grant_valid(const pa_grant_t *grant)
{
    return !memcmp(grant->request.magic,"PAR1",4) && grant->request.purpose<=1 && grant->ttl==20 &&
        !memcmp(grant->request.root,local_root,32) &&
        crypto_verify(authority_pub,grant,PA_GRANT_BODY,grant->signature) &&
        crypto_verify(grant->public_key,&grant->request,PA_REQUEST_BODY,grant->request.signature);
}
static esp_err_t radio_send(const uint8_t mac[6],wifi_interface_t interface,const void *data,size_t size)
{
    esp_now_peer_info_t peer={0};
    if(size>FRAGMENT_SIZE) { return ESP_ERR_INVALID_SIZE; }
    /* Never mutate a peer owned by Mesh core or overwrite its encryption keys. */
    if(esp_now_get_peer(mac,&peer)!=ESP_OK) {
        memcpy(peer.peer_addr,mac,6);peer.ifidx=interface;peer.channel=0;
        esp_err_t err=esp_now_add_peer(&peer);
        if(err!=ESP_OK) { return err; }
    } else if(peer.ifidx!=interface || peer.encrypt) { return ESP_ERR_INVALID_STATE; }
    uint8_t packet[1+FRAGMENT_SIZE];packet[0]=PA_TYPE;memcpy(packet+1,data,size);
    return esp_now_send(mac,packet,size+1);
}
static void radio_send_logged(const uint8_t mac[6],wifi_interface_t interface,const void *data,size_t size)
{
    static int64_t last_error;
    static unsigned failures;
    esp_err_t result=radio_send(mac,interface,data,size);
    if(result!=ESP_OK) {
        failures++;
        int64_t now=now_ms();
        if(!last_error || now-last_error>=2000) {
            ESP_LOGW(TAG,"PARENT_RADIO_SEND_FAILED node=%s interface=%d peer=%02x:%02x:%02x:%02x:%02x:%02x error=%s failures=%u",
                     node_role_id(),(int)interface,mac[0],mac[1],mac[2],mac[3],mac[4],mac[5],esp_err_to_name(result),failures);
            last_error=now;
        }
    }
}
static void make_request(pa_request_t *request,uint8_t purpose,const uint8_t nonce[16],const uint8_t child[6])
{
    memset(request,0,sizeof(*request));memcpy(request->magic,"PAR1",4);request->purpose=purpose;
    memcpy(request->node,local_node,32);memcpy(request->root,local_root,32);
    memcpy(request->boot,local_boot,16);memcpy(request->ap,local_ap,6);
    memcpy(request->nonce,nonce,16);memcpy(request->child,child,6);
}
static bool request_grant(uint8_t purpose,const uint8_t nonce[16],const uint8_t child[6])
{
    pa_request_t request;
    make_request(&request,purpose,nonce,child);
    return crypto_sign(&request) && xQueueSend(requests,&request,0)==pdTRUE;
}
static esp_err_t radio_received(const esp_now_recv_info_t *info,const uint8_t *data,int length)
{
    if(!inbox || !info || !data || (length!=27 && length!=FRAGMENT_SIZE)) { return ESP_OK; }
    bool challenge=length==27 && !memcmp(data,"PAC1",4) && !memcmp(info->des_addr,local_ap,6) && !node_role_is_leaf();
    bool fragment=length==FRAGMENT_SIZE && !memcmp(data,"PAF1",4) && !memcmp(info->des_addr,local_sta,6);
    if(!challenge && !fragment) { return ESP_OK; }
    event_t event={.kind=RADIO,.size=(uint16_t)length};
    memcpy(event.src,info->src_addr,6);memcpy(event.dst,info->des_addr,6);memcpy(event.data,data,length);
    (void)xQueueSend(inbox,&event,0);
    return ESP_OK;
}
void parent_auth_online(bool connected)
{
    if(!lock) { return; }
    xSemaphoreTake(lock,portMAX_DELAY);
    if(online!=connected) {
        online=connected;own_until=0;own_sent=0;own_asked=0;
        memset(own_nonce,0,sizeof(own_nonce));memset(forwards,0,sizeof(forwards));
        /* A new transport session must not consume a previous session's work. */
        xQueueReset(requests);
    }
    xSemaphoreGive(lock);
}
bool parent_auth_take_request(pa_request_t *request)
{
    return requests && xQueueReceive(requests,request,0)==pdTRUE;
}
void parent_auth_disconnected(void)
{
    if(!lock) { return; }
    parent_auth_online(false);
    xSemaphoreTake(lock,portMAX_DELAY);
    for(int i=0;i<SLOTS;i++) {
        candidates[i].until=0;candidates[i].asked=0;candidates[i].sent=0;candidates[i].parts=0;
        memset(candidates[i].nonce,0,16);
    }
    xSemaphoreGive(lock);
}
bool parent_auth_accept_grant(const void *data,size_t size)
{
    if(!inbox || !data || size!=PA_GRANT_SIZE) { return false; }
    event_t event={.kind=GRANT,.size=PA_GRANT_SIZE};memcpy(event.data,data,size);
    return xQueueSend(inbox,&event,0)==pdTRUE;
}
bool parent_auth_candidate(const uint8_t mac[6],const char *expected_id)
{
    if(!lock || !mac || node_role_is_root()) { return false; }
    if(expected_id && strlen(expected_id)>32) { return false; }
    bool allowed=false;int64_t now=now_ms();
    xSemaphoreTake(lock,portMAX_DELAY);
    for(int i=0;i<SLOTS;i++) {
        candidate_t *c=&candidates[i];
        if(c->used && !memcmp(mac,c->mac,6)) {
            c->last_seen=now;
            if(expected_id) { memset(c->required,0,32);memcpy(c->required,expected_id,strlen(expected_id)); }
            allowed=c->until>now && (!c->required[0] || !memcmp(c->required,c->node,32));
            break;
        }
    }
    xSemaphoreGive(lock);
    if(!allowed) {
        event_t event={.kind=DISCOVER};memcpy(event.src,mac,6);
        if(expected_id) { memcpy(event.required,expected_id,strlen(expected_id)); }
        (void)xQueueSend(inbox,&event,0);
    }
    return allowed;
}
static void discover(const uint8_t mac[6],const uint8_t required[32])
{
    int free_slot=-1;int64_t now=now_ms();
    if(!memcmp(mac,local_ap,6) || (mac[0]&1)) { return; }
    xSemaphoreTake(lock,portMAX_DELAY);
    for(int i=0;i<SLOTS;i++) {
        if(candidates[i].used && !memcmp(candidates[i].mac,mac,6)) { candidates[i].last_seen=now;xSemaphoreGive(lock);return; }
        if(!candidates[i].used || (candidates[i].until<=now && now-candidates[i].asked>10000)) { free_slot=i; }
    }
    if(free_slot>=0) {
        candidate_t *candidate=&candidates[free_slot];memset(candidate,0,sizeof(*candidate));
        candidate->used=true;candidate->last_seen=now;memcpy(candidate->mac,mac,6);
        memcpy(candidate->required,required,32);
    }
    xSemaphoreGive(lock);
}
static void handle_grant(const pa_grant_t *grant)
{
    if(!grant_valid(grant)) { return; }
    const pa_request_t *request=&grant->request;
    int64_t now=now_ms();
    if(memcmp(request->node,local_node,32) || memcmp(request->boot,local_boot,16) ||
       memcmp(request->ap,local_ap,6) || memcmp(grant->public_key,own_public,65) || grant->level!=node_role_fixed_level()) { return; }
    xSemaphoreTake(lock,portMAX_DELAY);
    if(!online) { xSemaphoreGive(lock);return; }
    if(request->purpose==0) {
        if(own_asked && now-own_asked<PA_RESPONSE_MS && !memcmp(request->nonce,own_nonce,16) &&
           !memcmp(request->child,local_sta,6)) {
            bool first=own_until<=now;own_until=own_asked+PA_LEASE_MS;
            xSemaphoreGive(lock);
            if(first) { ESP_LOGI(TAG,"PARENT_AUTHORIZED node=%s lease_ms=%d",node_role_id(),PA_LEASE_MS); }
            return;
        }
    } else {
        for(int i=0;i<SLOTS;i++) {
            forward_t *f=&forwards[i];
            if(f->used && now-f->asked<PA_RESPONSE_MS && !memcmp(f->nonce,request->nonce,16) &&
               !memcmp(f->mac,request->child,6)) {
                f->used=false;
                xSemaphoreGive(lock);
                uint8_t fragment[FRAGMENT_SIZE];memcpy(fragment,"PAF1",4);memcpy(fragment+4,request->nonce,16);
                for(int part=0;part<2;part++) {
                    fragment[20]=part;memcpy(fragment+21,(const uint8_t*)grant+part*FRAGMENT,FRAGMENT);
                    radio_send_logged(request->child,WIFI_IF_AP,fragment,sizeof(fragment));
                }
                return;
            }
        }
    }
    xSemaphoreGive(lock);
}
static void handle_radio(const event_t *event)
{
    int64_t now=now_ms();
    if(now-radio_window>=1000) { radio_window=now;radio_count=0; }
    if(++radio_count>24) { return; }
    if(event->size==27 && !memcmp(event->data,"PAC1",4)) {
        if(node_role_is_leaf() || memcmp(event->dst,local_ap,6) ||
           memcmp(event->data+20,event->src,6) || event->data[26]!=node_role_fixed_level()) { return; }
        int slot=-1;
        xSemaphoreTake(lock,portMAX_DELAY);
        bool eligible=online && own_until>now;
        if(eligible) {
            for(int i=0;i<SLOTS;i++) {
                if(forwards[i].used && now-forwards[i].asked<PA_RESPONSE_MS &&
                   !memcmp(forwards[i].mac,event->src,6) && !memcmp(forwards[i].nonce,event->data+4,16)) {
                    xSemaphoreGive(lock);return;
                }
                if(!forwards[i].used || now-forwards[i].asked>=PA_RESPONSE_MS) { slot=i; }
            }
            if(slot>=0) {
                forwards[slot].used=true;forwards[slot].asked=now;
                memcpy(forwards[slot].mac,event->src,6);memcpy(forwards[slot].nonce,event->data+4,16);
            }
        }
        xSemaphoreGive(lock);
        if(eligible && slot>=0 && !request_grant(1,event->data+4,event->src)) {
            xSemaphoreTake(lock,portMAX_DELAY);
            if(!memcmp(forwards[slot].nonce,event->data+4,16)) { forwards[slot].used=false; }
            xSemaphoreGive(lock);
        }
        if(eligible && slot>=0) {
            // Diagnose stale AP associations without disconnecting any station.
            wifi_sta_list_t stations={0};bool present=false;
            if(esp_wifi_ap_get_sta_list(&stations)==ESP_OK) {
                for(int i=0;i<stations.num;i++) {
                    if(!memcmp(stations.sta[i].mac,event->src,6)) { present=true;break; }
                }
                ESP_LOGI(TAG,"PARENT_ASSOC_CHECK node=%s child=%02x:%02x:%02x:%02x:%02x:%02x already_associated=%d sta_count=%d",
                    node_role_id(),event->src[0],event->src[1],event->src[2],event->src[3],event->src[4],event->src[5],present,stations.num);
            }
        }
        return;
    }
    if(event->size!=FRAGMENT_SIZE || memcmp(event->data,"PAF1",4) || event->data[20]>1) { return; }
    pa_grant_t grant;int slot=-1;
    xSemaphoreTake(lock,portMAX_DELAY);
    for(int i=0;i<SLOTS;i++) {
        candidate_t *c=&candidates[i];
        if(c->used && !memcmp(c->mac,event->src,6) && !memcmp(c->nonce,event->data+4,16) &&
           c->asked && now-c->asked<PA_RESPONSE_MS && !memcmp(event->dst,local_sta,6)) { slot=i;break; }
    }
    if(slot<0) { xSemaphoreGive(lock);return; }
    candidate_t *candidate=&candidates[slot];
    if(now-candidate->fragments_at>2000) { candidate->parts=0; }
    if(!candidate->parts) { candidate->fragments_at=now; }
    unsigned part=event->data[20],mask=1U<<part;
    uint8_t *target=candidate->assembly+part*FRAGMENT;
    if((candidate->parts&mask) && memcmp(target,event->data+21,FRAGMENT)) { candidate->parts=0;xSemaphoreGive(lock);return; }
    memcpy(target,event->data+21,FRAGMENT);candidate->parts|=mask;
    if(candidate->parts!=3) { xSemaphoreGive(lock);return; }
    memcpy(&grant,candidate->assembly,sizeof(grant));candidate->parts=0;
    uint8_t nonce[16];memcpy(nonce,candidate->nonce,16);int64_t asked=candidate->asked;
    xSemaphoreGive(lock);
    if(!grant_valid(&grant) || grant.request.purpose!=1 || grant.level+1!=node_role_fixed_level() ||
       memcmp(grant.request.nonce,nonce,16) || memcmp(grant.request.child,local_sta,6) ||
       memcmp(grant.request.ap,event->src,6)) { return; }
    xSemaphoreTake(lock,portMAX_DELAY);
    candidate=&candidates[slot];
    if(candidate->used && !memcmp(candidate->nonce,nonce,16) &&
       (!candidate->required[0] || !memcmp(candidate->required,grant.request.node,32))) {
        bool first=candidate->until<=now;
        memcpy(candidate->node,grant.request.node,32);
        candidate->until=asked+PA_LEASE_MS;
        if(first) { selection_ready=true; }
        if(first) { ESP_LOGI(TAG,"PARENT_VERIFIED node=%s parent=%.32s level=%u",
                            node_role_id(),(const char*)grant.request.node,(unsigned)grant.level); }
    }
    xSemaphoreGive(lock);
}
/* Mesh-Lite owns scanning/association. A rejected scan has no Wi-Fi disconnect
 * event to restart recovery, so do not rely on that event for offline retries.
 * Never disconnect here: doing so would invalidate the proof just obtained. */
static void recover_selection(int64_t now)
{
    (void)now;
    if(mesh_access_retry_selection(selection_ready) || mesh_access_connected()) { selection_ready=false; }
}
static void worker(void *arg)
{
    (void)arg;event_t event;
    for(;;) {
        if(xQueueReceive(inbox,&event,pdMS_TO_TICKS(50))==pdTRUE) {
            if(event.kind==DISCOVER) { discover(event.src,event.required); }
            else if(event.kind==GRANT) { pa_grant_t grant;memcpy(&grant,event.data,sizeof(grant));handle_grant(&grant); }
            else if(event.kind==RADIO) { handle_radio(&event); }
        }
        int64_t now=now_ms();bool renew=false;
        xSemaphoreTake(lock,portMAX_DELAY);
        if(online && !node_role_is_leaf() && (!own_sent || now-own_sent>=5000)) {
            esp_fill_random(own_nonce,16);own_asked=now;own_sent=now;renew=true;
        }
        xSemaphoreGive(lock);
        if(renew) { (void)request_grant(0,own_nonce,local_sta); }
        for(int i=0;i<SLOTS;i++) {
            uint8_t challenge[27],mac[6];bool send=false;
            xSemaphoreTake(lock,portMAX_DELAY);
            candidate_t *c=&candidates[i];
            if(c->used && now-c->last_seen>30000) { c->used=false;c->until=0; }
            if(c->used) {
                if(!c->asked || now-c->asked>=5000) {
                    esp_fill_random(c->nonce,16);c->asked=now;c->sent=0;c->parts=0;
                }
                if(!c->sent || now-c->sent>=500) {
                    uint8_t jitter;esp_fill_random(&jitter,1);
                    c->sent=now+jitter%100;send=true;memcpy(mac,c->mac,6);
                    memcpy(challenge,"PAC1",4);memcpy(challenge+4,c->nonce,16);
                    memcpy(challenge+20,local_sta,6);challenge[26]=node_role_fixed_level()-1;
                }
            }
            xSemaphoreGive(lock);
            if(send) { radio_send_logged(mac,WIFI_IF_STA,challenge,sizeof(challenge)); }
        }
        if(!node_role_is_root() && now-last_disconnect>1000 && mesh_access_connected()) {
            last_disconnect=now;
            wifi_ap_record_t parent={0};
            if(esp_wifi_sta_get_ap_info(&parent)==ESP_OK && !parent_auth_candidate(parent.bssid,NULL)) {
                ESP_LOGW(TAG,"PARENT_LEASE_LOST node=%s; selecting a verified parent",node_role_id());
                (void)esp_mesh_lite_disconnect();esp_mesh_lite_connect();last_disconnect=now;
            }
        }
        recover_selection(now);
    }
}
void parent_auth_status(cJSON *payload)
{
    if(!lock) { return; }
    int64_t now=now_ms();
    xSemaphoreTake(lock,portMAX_DELAY);
    cJSON *status=cJSON_AddObjectToObject(payload,"parent_auth");
    cJSON_AddStringToObject(status,"protocol","espnow-online-v1");
    cJSON_AddBoolToObject(status,"relay_authorized",online && own_until>now && !node_role_is_leaf());
    cJSON_AddNumberToObject(status,"relay_lease_ms",own_until>now ? (double)(own_until-now) : 0);
    xSemaphoreGive(lock);
}
esp_err_t parent_auth_init(void)
{
    if(inbox) { return ESP_ERR_INVALID_STATE; }
    if(!strlen(node_role_id()) || strlen(node_role_id())>32 ||
       !strlen(CONFIG_APP_UGV_NODE_ID) || strlen(CONFIG_APP_UGV_NODE_ID)>32) { return ESP_ERR_INVALID_ARG; }
    if(psa_crypto_init()!=PSA_SUCCESS) { return ESP_FAIL; }
    lock=xSemaphoreCreateMutex();inbox=xQueueCreate(16,sizeof(event_t));requests=xQueueCreate(8,sizeof(pa_request_t));
    if(!lock || !inbox || !requests) { return ESP_ERR_NO_MEM; }
    memcpy(local_node,node_role_id(),strlen(node_role_id()));memcpy(local_root,CONFIG_APP_UGV_NODE_ID,strlen(CONFIG_APP_UGV_NODE_ID));
    esp_fill_random(local_boot,sizeof(local_boot));
    ESP_ERROR_CHECK(esp_wifi_get_mac(WIFI_IF_STA,local_sta));ESP_ERROR_CHECK(esp_wifi_get_mac(WIFI_IF_AP,local_ap));
    psa_key_attributes_t attr=PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_type(&attr,PSA_KEY_TYPE_ECC_KEY_PAIR(PSA_ECC_FAMILY_SECP_R1));psa_set_key_bits(&attr,256);
    psa_set_key_usage_flags(&attr,PSA_KEY_USAGE_SIGN_HASH);
    psa_set_key_algorithm(&attr,PSA_ALG_ECDSA(PSA_ALG_SHA_256));
    if(psa_import_key(&attr,auth_key,32,&signing_key)!=PSA_SUCCESS) { psa_reset_key_attributes(&attr);return ESP_FAIL; }
    psa_reset_key_attributes(&attr);size_t size=0;
    if(psa_export_public_key(signing_key,own_public,sizeof(own_public),&size)!=PSA_SUCCESS || size!=65) { return ESP_FAIL; }
    if(!memcmp(own_public,authority_pub,65)) { return ESP_ERR_INVALID_STATE; }
    esp_err_t result=esp_mesh_lite_espnow_recv_cb_register(PA_TYPE,radio_received);
    if(result!=ESP_OK) { return result; }
    ESP_LOGI(TAG,"INIT node=%s parent admission defaults to deny; AP state unchanged",node_role_id());
    return xTaskCreate(worker,"parent_auth",8192,NULL,4,NULL)==pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
