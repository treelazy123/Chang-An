#include "sdkconfig.h"
#include "mqtt_serial.h"
#include "parent_policy.h"
#include "parent_auth.h"
#include "cap_measure.h"
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
#include "service_discovery.h"
#if !CONFIG_APP_ROOT_GATEWAY
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"
#include "mqtt_client.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "esp_netif.h"
#include "esp_mesh_lite.h"
#include "lwip/sockets.h"
#include "lwip/inet.h"
#include "node_role.h"
#include "app_protocol.h"
#include "task_agent.h"
#include "image_upload.h"
#include "mbedtls/base64.h"
extern const char ca[] asm("_binary_ca_pem_start");
extern const char cert[] asm("_binary_client_pem_start");
extern const char key[] asm("_binary_client_key_start");
#define CONNECTED (1U << 0)
#define SUBSCRIBED (1U << 1)
#define CLOCKED (1U << 2)
#define LOST (1U << 3)
static const char *TAG="mesh_mqtt";
static EventGroupHandle_t state;
static QueueHandle_t commands;
static esp_mqtt_client_handle_t client;
static char command_topic[100],boot[17];
static int subscription,task_subscription;
static char task_topic[100];
#define TASK_READY (1U << 5)

static void access_phase(const char *phase) {
    ESP_LOGI(TAG,"ACCESS_PHASE node=%s boot_id=%s phase=%s uptime_ms=%lld",node_role_id(),boot,phase,
             (long long)(esp_timer_get_time()/1000));
}

typedef struct { char json[APP_COMMAND_MAX+1]; } command_t;
static command_t assembly;
static int assembled;
static bool receiving;
typedef struct { char id[65];char request[APP_COMMAND_MAX+1];char reply[APP_JSON_MAX+1]; } cache_t;
static cache_t cache[8];static unsigned cache_pos;
static int publish(const char *suffix,const cJSON *body,int qos,bool retain) {
    char topic[128];snprintf(topic,sizeof(topic),"mesh/v1/nodes/%s/%s",node_role_id(),suffix);
    char *json=cJSON_PrintUnformatted(body);if(!json) { return -1; }
    size_t size=strlen(json);
    int id=size<=APP_JSON_MAX?esp_mqtt_client_enqueue(client,topic,json,size,qos,retain,true):-1;
    cJSON_free(json);return id;
}

/* ---------------- Image upload (leaf -> root -> host) ----------------
 * Frames queued by a producer (video capture, or the embedded self-test assets)
 * are streamed up the existing node->broker MQTT/TLS session in base64 JSON
 * chunks; the tree routing is the mesh IP path, no relay code.
 */
#define IMAGE_CHUNK 512

static size_t base64_encode(const uint8_t *src,size_t slen,char *dst) {
    static const char *T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    size_t i=0,o=0;
    for(;i+3<=slen;i+=3) {
        uint32_t v=((uint32_t)src[i]<<16)|((uint32_t)src[i+1]<<8)|src[i+2];
        dst[o++]=T[(v>>18)&63];dst[o++]=T[(v>>12)&63];
        dst[o++]=T[(v>>6)&63];dst[o++]=T[v&63];
    }
    if(i<slen) {
        uint32_t v=(uint32_t)src[i]<<16;
        if(i+1<slen) { v|=(uint32_t)src[i+1]<<8; }
        dst[o++]=T[(v>>18)&63];dst[o++]=T[(v>>12)&63];
        dst[o++]=(i+1<slen)?T[(v>>6)&63]:'=';
        dst[o++]='=';
    }
    dst[o]='\0';
    return o;
}

static image_frame_t *image_current;   /* frame being streamed; NULL when idle */
static size_t image_chunk_idx;
static bool images_primed;

/* Stream the oldest queued frame, one base64 chunk per call so the MQTT loop stays
 * responsive; runs from mqtt_task only. */
static void image_upload_tick(void) {
    if(image_current==NULL) {
        image_current=image_upload_pop();
        if(image_current==NULL) { return; }
        image_chunk_idx=0;
    }
    const image_frame_t *img=image_current;
    size_t n_chunks=(img->len+IMAGE_CHUNK-1)/IMAGE_CHUNK;
    if(n_chunks==0) { n_chunks=1; }
    size_t s=image_chunk_idx;
    size_t off=s*IMAGE_CHUNK;
    size_t n=img->len-off;
    if(n>IMAGE_CHUNK) { n=IMAGE_CHUNK; }
    char b64[IMAGE_CHUNK*4/3+4];
    base64_encode(img->data+off,n,b64);
    cJSON *body=app_message_new("image");
    if(body) {
        cJSON_AddStringToObject(body,"image_id",img->id);
        cJSON_AddStringToObject(body,"name",img->id);
        cJSON_AddNumberToObject(body,"seq",(double)s);
        cJSON_AddNumberToObject(body,"count",(double)n_chunks);
        cJSON_AddNumberToObject(body,"total_bytes",(double)img->len);
        cJSON_AddStringToObject(body,"data",b64);
        int mid=publish("image",body,1,false);
        cJSON_Delete(body);
        /* Outbox backpressure: keep the chunk index so this chunk is retried. */
        if(mid<0) { return; }
    }
    if(s+1>=n_chunks) {
        image_upload_release(image_current);
        image_current=NULL;
        image_chunk_idx=0;
    } else {
        image_chunk_idx++;
    }
}
static void mqtt_event(void *ctx,esp_event_base_t base,int32_t id,void *data) {
    (void)ctx;(void)base;esp_mqtt_event_handle_t e=data;
    if(id==MQTT_EVENT_CONNECTED) {
        access_phase("MQTT_CONNECTED");
        receiving=false;assembled=0;xEventGroupSetBits(state,CONNECTED);
        subscription=esp_mqtt_client_subscribe_single(client,command_topic,1);
        task_subscription=esp_mqtt_client_subscribe_single(client,task_topic,1);
        (void)esp_mqtt_client_subscribe_single(client,"mesh/v1/clock",1);
    } else if(id==MQTT_EVENT_SUBSCRIBED && e->error_handle &&
              e->error_handle->error_type==MQTT_ERROR_TYPE_SUBSCRIBE_FAILED) {
        xEventGroupSetBits(state,LOST);
        xEventGroupClearBits(state,CONNECTED|SUBSCRIBED|CLOCKED|TASK_READY);
    } else if(id==MQTT_EVENT_SUBSCRIBED && e->msg_id==subscription) {
        xEventGroupSetBits(state,SUBSCRIBED);
        access_phase("COMMAND_SUBSCRIBED");
    } else if(id==MQTT_EVENT_SUBSCRIBED && e->msg_id==task_subscription) {
        xEventGroupSetBits(state,TASK_READY);
        access_phase("TASK_SUBSCRIBED");
    } else if(id==MQTT_EVENT_DISCONNECTED || id==MQTT_EVENT_ERROR) {
        parent_auth_online(false);
        xEventGroupClearBits(state,CONNECTED|SUBSCRIBED|CLOCKED|TASK_READY);xEventGroupSetBits(state,LOST);
        if(id==MQTT_EVENT_ERROR && e->error_handle) {
            ESP_LOGE(TAG,"TLS/MQTT error type=%d tls=0x%x stack=0x%x verify=0x%x connack=%d",e->error_handle->error_type,
                e->error_handle->esp_tls_last_esp_err,e->error_handle->esp_tls_stack_err,
                e->error_handle->esp_tls_cert_verify_flags,e->error_handle->connect_return_code);
        }
    } else if(id==MQTT_EVENT_DATA) {

        if(e->current_data_offset==0 && e->topic_len==13 && !memcmp(e->topic,"mesh/v1/clock",13)) {
            if(e->total_data_len!=e->data_len || e->data_len<=0 || e->data_len>100) { return; }
            char text[101];memcpy(text,e->data,e->data_len);text[e->data_len]='\0';
            cJSON *msg=cJSON_Parse(text);const cJSON *t=cJSON_GetObjectItemCaseSensitive(msg,"unix");
            if(cJSON_IsNumber(t) && t->valuedouble>=CONFIG_APP_TLS_BOOTSTRAP_UNIX && t->valuedouble<2147483647) {
                if (!(xEventGroupGetBits(state)&CLOCKED)) { access_phase("CLOCK_RECEIVED"); }
                struct timeval tv={.tv_sec=(time_t)t->valuedouble};settimeofday(&tv,NULL);xEventGroupSetBits(state,CLOCKED);
            }
            cJSON_Delete(msg);return;
        }
        if(e->current_data_offset==0) {
            receiving=!e->retain && ((e->topic_len==(int)strlen(command_topic) && !memcmp(e->topic,command_topic,e->topic_len)) ||
                 (e->topic_len==(int)strlen(task_topic) && !memcmp(e->topic,task_topic,e->topic_len))) &&
                 e->total_data_len>0 && e->total_data_len<=APP_COMMAND_MAX;
            assembled=0;
        }
        if(!receiving || e->current_data_offset!=assembled || e->data_len<=0 ||
           e->data_len>APP_COMMAND_MAX-assembled || e->data_len>e->total_data_len-assembled) {
            receiving=false;return;
        }
        memcpy(assembly.json+assembled,e->data,e->data_len);assembled+=e->data_len;
        if(assembled==e->total_data_len) {
            assembly.json[assembled]='\0';
            if(xQueueSend(commands,&assembly,0)!=pdTRUE) { ESP_LOGW(TAG,"command queue full"); }
            receiving=false;
        }
    }
}
static bool endpoint(uint32_t *ip) {
    esp_netif_ip_info_t local={0};esp_netif_t *sta=esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if(!sta || esp_mesh_lite_get_level()<1 || esp_netif_get_ip_info(sta,&local)!=ESP_OK) { return false; }
    if(!local.ip.addr) { return false; }
    return service_discovery_ugv_ap(ip);
}
static void announce_capabilities(bool force,const cJSON *request);
static void reply_command(const command_t *packet) {
    cJSON *cmd=app_message_parse(packet->json,strlen(packet->json));
    const char *kind=app_json_string(cmd,"type"),*target=app_json_string(cmd,"target");
    if(kind&&target&&!strcmp(target,node_role_id())) {
        if(!strcmp(kind,"cap.receipt")) {
            cap_measure_receipt(cmd,boot,esp_timer_get_time());cJSON_Delete(cmd);return;
        }
        if(!strcmp(kind,"cap.request")) {
            const char *requested_boot=app_json_string(cmd,"boot_id");
            const cJSON *deadline=cJSON_GetObjectItemCaseSensitive(cmd,"deadline_unix");
            time_t now=time(NULL);
            if(requested_boot&&!strcmp(requested_boot,boot)&&(xEventGroupGetBits(state)&CLOCKED)&&
               cJSON_IsNumber(deadline)&&deadline->valuedouble>=now&&deadline->valuedouble<=now+60&&cap_measure_new_request(cmd)) {
                announce_capabilities(true,cmd);
            }
            cJSON_Delete(cmd);return;
        }
    }
    if(cmd && app_json_string(cmd,"type") && !strcmp(app_json_string(cmd,"type"),"parent.auth.grant")) {
        const char *proof=app_json_string(cmd,"proof");uint8_t grant[PA_GRANT_SIZE];size_t size=0;
        if(proof && strlen(proof)==416 && mbedtls_base64_decode(grant,sizeof(grant),&size,(const uint8_t*)proof,strlen(proof))==0) {
            (void)parent_auth_accept_grant(grant,size);
        }
        cJSON_Delete(cmd);return;
    }
    if(cmd && app_json_string(cmd,"type") && !strcmp(app_json_string(cmd,"type"),"task.command")) {
        task_agent_command(cmd,(xEventGroupGetBits(state)&CLOCKED)!=0);cJSON_Delete(cmd);return;
    }
    if(!app_command_valid(cmd) || strcmp(app_json_string(cmd,"target"),node_role_id())) { cJSON_Delete(cmd);return; }
    const char *id=app_json_string(cmd,"msg_id");
    for(int i=0;i<8;i++) {
        if(!strcmp(cache[i].id,id)) {
            if(!strcmp(cache[i].request,packet->json)) {
                char topic[100];snprintf(topic,sizeof(topic),"mesh/v1/nodes/%s/acks",node_role_id());
                esp_mqtt_client_enqueue(client,topic,cache[i].reply,0,1,false,true);
            } else { ESP_LOGW(TAG,"task ID conflict rejected"); }
            cJSON_Delete(cmd);return;
        }
    }
    const cJSON *expiry=cJSON_GetObjectItemCaseSensitive(cmd,"deadline_unix");
    cJSON *reply=app_command_reply(cmd);if(!reply) { cJSON_Delete(cmd);return; }
    time_t now=time(NULL);
    if(!cJSON_IsNumber(expiry) || expiry->valuedouble<now || expiry->valuedouble>now+60 ||
       !(xEventGroupGetBits(state)&CLOCKED)) {
        cJSON_ReplaceItemInObjectCaseSensitive(reply,"ok",cJSON_CreateBool(false));
        cJSON_AddStringToObject(reply,"error","expired_or_invalid_deadline");
    } else if (node_role_is_leaf() && !strcmp(app_json_string(cmd,"op"),"parent")) {
        const char *error=parent_policy_prepare(cJSON_GetObjectItemCaseSensitive(cmd,"payload"));
        if (error) {
            cJSON_ReplaceItemInObjectCaseSensitive(reply,"ok",cJSON_CreateBool(false));
            cJSON_AddStringToObject(reply,"error",error);
        }
    }
    char *json=cJSON_PrintUnformatted(reply);
    if(json && strlen(json)<=APP_JSON_MAX) {
        cache_t *saved=&cache[cache_pos++%8];snprintf(saved->id,sizeof(saved->id),"%s",id);
        snprintf(saved->request,sizeof(saved->request),"%s",packet->json);snprintf(saved->reply,sizeof(saved->reply),"%s",json);
        publish("acks",reply,1,false);
    }
    cJSON_free(json);cJSON_Delete(reply);cJSON_Delete(cmd);
}
static bool capabilities_dirty=true;
static char capability_state[24],capability_task[33];
static bool task_emit(const cJSON *body) { capabilities_dirty=true;return publish("task_events",body,1,false)>=0; }
static bool cap_result_emit(const cJSON *body) { return publish("telemetry",body,1,false)>=0; }
static void announce_capabilities(bool force,const cJSON *request) {
    int64_t announce_started=esp_timer_get_time();
    bool mci=request==NULL;
    if(force && mci) { capabilities_dirty=true; }
    cJSON *wire=mci?cJSON_CreateObject():app_message_new("capabilities");
    if(wire) {
        cJSON *cap=wire;
        if(mci) {
            cJSON_AddNumberToObject(wire,"v",1);
            cJSON_AddStringToObject(wire,"service","Mesh_Node");
            cJSON_AddStringToObject(wire,"method","Ntf_Capabilities");
            cJSON_AddStringToObject(wire,"nodeId",node_role_id());
            cJSON_AddStringToObject(wire,"bootId",boot);
            cap=cJSON_AddObjectToObject(wire,"params");
            if(!cap) { cJSON_Delete(wire);return; }
        } else {
            cJSON_AddStringToObject(wire,"boot_id",boot);
        }
        cJSON *ops=cJSON_AddArrayToObject(cap,"operations");
        cJSON_AddItemToArray(ops,cJSON_CreateString("ping"));cJSON_AddItemToArray(ops,cJSON_CreateString("status"));
        cJSON_AddItemToArray(ops,cJSON_CreateString("echo"));task_agent_capabilities(cap,mci);
        if (node_role_is_leaf()) { cJSON_AddItemToArray(ops,cJSON_CreateString("parent")); }
        const char *status=app_json_string(cap,mci?"taskStatus":"task_status");
        const char *task=app_json_string(cap,mci?"taskId":"task_id");
        if(!task) { task=""; }
        if(status && (force || strcmp(status,capability_state) || strcmp(task,capability_task))) {
            cap_measure_begin(cap,boot,request,announce_started,mci);
            if(publish("capabilities",wire,1,mci)>=0) {
                if(mci) {
                    snprintf(capability_state,sizeof(capability_state),"%s",status);
                    snprintf(capability_task,sizeof(capability_task),"%s",task);
                    capabilities_dirty=false;
                }
            } else { cap_measure_discard(app_json_string(cap,mci?"capId":"cap_id")); }
        } else if(mci) { capabilities_dirty=false; }
        cJSON_Delete(wire);
    }
}
static void announce_ready(void) {
    capability_state[0]='\0';
    announce_capabilities(true,NULL);
    cJSON *presence=app_message_new("presence");if(presence) {
        cJSON_AddBoolToObject(presence,"online",true);cJSON_AddStringToObject(presence,"boot_id",boot);
        publish("presence",presence,1,true);cJSON_Delete(presence);
    }
    ESP_LOGI(TAG,"READY node=%s MQTT TLS authenticated; command subscription active",node_role_id());
    access_phase("APPLICATION_READY");
}
static void mqtt_task(void *arg) {
    (void)arg;char uri[80],ip_text[16],will[160],presence[100];
    snprintf(boot,sizeof(boot),"%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random());
    cap_measure_init();
    access_phase("MQTT_TASK_STARTED");
    snprintf(command_topic,sizeof(command_topic),"mesh/v1/nodes/%s/commands",node_role_id());
    snprintf(task_topic,sizeof(task_topic),"mesh/v1/nodes/%s/task_commands",node_role_id());
    ESP_ERROR_CHECK(task_agent_init(boot,task_emit));
    snprintf(presence,sizeof(presence),"mesh/v1/nodes/%s/presence",node_role_id());
    snprintf(will,sizeof(will),"{\"v\":1,\"type\":\"presence\",\"node_id\":\"%s\",\"online\":false}",node_role_id());
    if(time(NULL)<CONFIG_APP_TLS_BOOTSTRAP_UNIX) {
        struct timeval tv={.tv_sec=CONFIG_APP_TLS_BOOTSTRAP_UNIX};settimeofday(&tv,NULL);
    }
    for(;;) {
        task_agent_tick(false);
        uint32_t address;
        if(!endpoint(&address)) { service_discovery_wait(1000);continue; }
        struct in_addr a={.s_addr=address};inet_ntop(AF_INET,&a,ip_text,sizeof(ip_text));
        snprintf(uri,sizeof(uri),"mqtts://%s:%d",ip_text,CONFIG_APP_MQTT_PORT);
        esp_mqtt_client_config_t config={
            .broker.address.uri=uri,
            .broker.verification.certificate=ca,
            .broker.verification.common_name=CONFIG_APP_MQTT_SERVER_NAME,
            .credentials.client_id=node_role_id(),
            .credentials.authentication.certificate=cert,.credentials.authentication.key=key,
            .session.protocol_ver=MQTT_PROTOCOL_V_3_1_1,.session.keepalive=15,
            .session.last_will={.topic=presence,.msg=will,.qos=1,.retain=true},
            .network.disable_auto_reconnect=true,.network.timeout_ms=15000,
            .task.stack_size=8192,.buffer.size=1024,.buffer.out_size=1024,.outbox.limit=8192,
        };
        xEventGroupClearBits(state,CONNECTED|SUBSCRIBED|CLOCKED|TASK_READY|LOST);xQueueReset(commands);
        client=esp_mqtt_client_init(&config);
        if(!client) { vTaskDelay(pdMS_TO_TICKS(2000));continue; }
        ESP_LOGI(TAG,"CONNECT node=%s target=%s identity=%s",node_role_id(),uri,CONFIG_APP_MQTT_SERVER_NAME);
        access_phase("MQTT_CONNECT_START");
        esp_mqtt_client_register_event(client,ESP_EVENT_ANY_ID,mqtt_event,NULL);
        esp_err_t err=esp_mqtt_client_start(client);
        int64_t started=esp_timer_get_time()/1000,last_status=0;bool announced=false,first_status=true;
#if CONFIG_APP_IMAGE_SELFTEST_PERIOD_S > 0
        int64_t last_prime=0;
#endif
        while(err==ESP_OK && !(xEventGroupGetBits(state)&LOST)) {
            uint32_t current;
            if(!endpoint(&current) || current!=address) { break; }
            EventBits_t bits=xEventGroupGetBits(state);
            bool active=(bits&(CONNECTED|SUBSCRIBED|CLOCKED|TASK_READY))==(CONNECTED|SUBSCRIBED|CLOCKED|TASK_READY);
            parent_auth_online(active);
            if(active) {
                pa_request_t request;
                if(parent_auth_take_request(&request)) {
                    uint8_t proof[240];size_t size=0;
                    if(mbedtls_base64_encode(proof,sizeof(proof),&size,(const uint8_t*)&request,sizeof(request))==0) {
                        proof[size]='\0';
                        cJSON *message=cJSON_CreateObject();
                        if(message) {
                            cJSON_AddNumberToObject(message,"v",1);cJSON_AddStringToObject(message,"type","parent.auth.request");
                            cJSON_AddStringToObject(message,"proof",(char*)proof);publish("telemetry",message,1,false);cJSON_Delete(message);
                        }
                    }
                }
            }
            task_agent_tick(active);
            if(!announced && active) { announce_ready();announced=true; }
            if(active && !images_primed) {
                images_primed=true;image_upload_prime();
#if CONFIG_APP_IMAGE_SELFTEST_PERIOD_S > 0
                last_prime=esp_timer_get_time()/1000;
#endif
            }
#if CONFIG_APP_IMAGE_SELFTEST_PERIOD_S > 0
            else if(active && esp_timer_get_time()/1000-last_prime>=1000LL*CONFIG_APP_IMAGE_SELFTEST_PERIOD_S) {
                image_upload_prime();
                last_prime=esp_timer_get_time()/1000;
            }
#endif
            if(announced && active && capabilities_dirty) { announce_capabilities(false,NULL); }
            if(!announced && esp_timer_get_time()/1000-started>45000) { break; }
            if(active) {
                command_t packet;
                if(xQueueReceive(commands,&packet,0)==pdTRUE) { reply_command(&packet); }
                image_upload_tick();
                cap_measure_tick(boot,esp_timer_get_time(),cap_result_emit);
                if(first_status || esp_timer_get_time()/1000-last_status>=CONFIG_APP_STATUS_PERIOD_MS) {
                    cJSON *msg=app_message_new("telemetry");if(msg) {
                        cJSON_AddItemToObject(msg,"payload",app_status_payload());cJSON_AddStringToObject(msg,"boot_id",boot);
                        /* First live telemetry completes the host's readiness check.
                         * Send now on every connection, then keep the normal cadence. */
                        if(publish("telemetry",msg,first_status?1:0,false)>=0) {
                            last_status=esp_timer_get_time()/1000;
                            if(first_status) { access_phase("FIRST_TELEMETRY_ENQUEUED"); }
                            first_status=false;
                        }
                        cJSON_Delete(msg);
                    }
                }
            }
            vTaskDelay(pdMS_TO_TICKS(50));
        }
        task_agent_tick(false);
        parent_auth_online(false);
        cap_measure_clear();
        esp_mqtt_client_stop(client);esp_mqtt_client_destroy(client);client=NULL;
        xEventGroupClearBits(state,CONNECTED|SUBSCRIBED|CLOCKED|TASK_READY);
        xQueueReset(commands);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}
esp_err_t mqtt_serial_start(void) {
    if(CONFIG_APP_TLS_BOOTSTRAP_UNIX<1700000000) { ESP_LOGE(TAG,"Provision trusted lab UTC and certificates first");return ESP_ERR_INVALID_STATE; }
    state=xEventGroupCreate();commands=xQueueCreate(4,sizeof(command_t));
    image_upload_init();
    if(!state || !commands) { return ESP_ERR_NO_MEM; }
    esp_err_t err=service_discovery_start();if(err!=ESP_OK) { return err; }
    return xTaskCreate(mqtt_task,"mesh_mqtt_app",6144,NULL,3,NULL)==pdPASS?ESP_OK:ESP_ERR_NO_MEM;
}
#endif
#else
esp_err_t mqtt_serial_start(void) { return ESP_ERR_NOT_SUPPORTED; }
#endif
