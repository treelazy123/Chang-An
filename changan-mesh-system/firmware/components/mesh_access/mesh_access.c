#include <string.h>
#include <stddef.h>
#include "sdkconfig.h"
#include "mesh_access.h"
#include "node_role.h"
#include "esp_mesh_lite.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"

#if CONFIG_IDF_TARGET_ESP32C6
_Static_assert(offsetof(wifi_scan_config_t,home_chan_dwell_time)==28,
               "Audit the Mesh-Lite legacy scan prefix for this SDK ABI");
#endif

static const char *TAG="mesh_access";
static portMUX_TYPE lock=portMUX_INITIALIZER_UNLOCKED;
static bool enabled,associated,scanning,connecting,hint_dirty;
static bool first_hint_scan=true;
static unsigned scans;
static unsigned deauth_count;
static int64_t last_deauth_log;
static uint8_t hint_channel=CONFIG_APP_MESH_CHANNEL, hint_bssid[6];
static int64_t scan_started,connect_started,last_selection,settle_until;
static int64_t now_ms(void) { return esp_timer_get_time()/1000; }
esp_err_t __real_esp_wifi_scan_start(const wifi_scan_config_t *config,bool block);
esp_err_t __real_esp_wifi_connect(void);
esp_err_t __real_esp_wifi_set_config(wifi_interface_t interface,wifi_config_t *config);
esp_err_t __real_esp_wifi_deauth_sta(uint16_t aid);

static void network_event(void *arg,esp_event_base_t base,int32_t id,void *data)
{
    (void)arg;(void)base;
    int64_t now=now_ms();
    portENTER_CRITICAL(&lock);
    if(id==WIFI_EVENT_SCAN_DONE) {
        scanning=false;settle_until=now+100;
    } else if(id==WIFI_EVENT_STA_CONNECTED && data) {
        const wifi_event_sta_connected_t *event=data;
        associated=true;connecting=false;scans=0;
        hint_channel=event->channel;memcpy(hint_bssid,event->bssid,6);hint_dirty=true;
    } else if(id==WIFI_EVENT_STA_DISCONNECTED) {
        associated=false;connecting=false;settle_until=now+100;
    }
    portEXIT_CRITICAL(&lock);
    if(id==WIFI_EVENT_SCAN_DONE) {
        ESP_LOGI(TAG,"SCAN_DONE node=%s elapsed_ms=%lld",node_role_id(),(long long)(now-scan_started));
    }
}

bool mesh_access_connected(void)
{
    portENTER_CRITICAL(&lock);bool value=associated;portEXIT_CRITICAL(&lock);
    return value;
}

esp_err_t __wrap_esp_wifi_scan_start(const wifi_scan_config_t *config,bool block)
{
    if(!enabled) { return __real_esp_wifi_scan_start(config,block); }
    wifi_scan_config_t safe={0};
    /* Mesh-Lite 1.0.2 passes its older scan struct to IDF 6.1. Only read the
     * shared prefix; never copy sizeof(IDF6 config) from a legacy allocation.
     * Explicit channel scanning replaces bitmap extensions in this project. */
    if(config) {
        safe.ssid=config->ssid;safe.bssid=config->bssid;safe.channel=config->channel;
        safe.show_hidden=config->show_hidden;safe.scan_type=config->scan_type;safe.scan_time=config->scan_time;
    }
    bool fast=false;
    portENTER_CRITICAL(&lock);
    if(connecting || scanning) { portEXIT_CRITICAL(&lock);return ESP_ERR_WIFI_STATE; }
    if(!associated && !node_role_is_root()) {
        // Three bounded single-channel attempts, then a full scan; repeat if offline.
        fast=(scans++%4)!=3;
        safe.channel=fast ? hint_channel : 0;
        // The first attempt may target the old BSSID, but the proof filter still runs.
        const uint8_t empty_mac[6]={0};
        if(fast && first_hint_scan && memcmp(hint_bssid,empty_mac,6)) { safe.bssid=hint_bssid; }
        else { safe.bssid=NULL; }
        first_hint_scan=false;
        safe.scan_type=WIFI_SCAN_TYPE_ACTIVE;
        safe.scan_time.active.min=40;safe.scan_time.active.max=60;
    }
    safe.home_chan_dwell_time=30;
    scanning=true;scan_started=now_ms();
    portEXIT_CRITICAL(&lock);
    ESP_LOGI(TAG,"SCAN_START node=%s mode=%s channel=%u max_ms=%lu bitmap=0",
             node_role_id(),fast?"preferred":"fallback",(unsigned)safe.channel,(unsigned long)safe.scan_time.active.max);
    esp_err_t result=__real_esp_wifi_scan_start(&safe,block);
    if(result!=ESP_OK || block) {
        portENTER_CRITICAL(&lock);scanning=false;portEXIT_CRITICAL(&lock);
    }
    return result;
}

esp_err_t __wrap_esp_wifi_connect(void)
{
    if(!enabled || node_role_is_root()) { return __real_esp_wifi_connect(); }
    portENTER_CRITICAL(&lock);
    if(connecting || scanning || associated) { portEXIT_CRITICAL(&lock);return ESP_ERR_WIFI_STATE; }
    connecting=true;connect_started=now_ms();
    portEXIT_CRITICAL(&lock);
    ESP_LOGI(TAG,"ASSOC_START node=%s uptime_ms=%lld",node_role_id(),(long long)connect_started);
    esp_err_t result=__real_esp_wifi_connect();
    if(result!=ESP_OK) {
        portENTER_CRITICAL(&lock);connecting=false;portEXIT_CRITICAL(&lock);
    }
    return result;
}

esp_err_t __wrap_esp_wifi_set_config(wifi_interface_t interface,wifi_config_t *config)
{
    portENTER_CRITICAL(&lock);
    bool busy=enabled && interface==WIFI_IF_STA && connecting;
    portEXIT_CRITICAL(&lock);
    if(busy) { return ESP_ERR_WIFI_STATE; }
    return __real_esp_wifi_set_config(interface,config);
}

/* Diagnose the Mesh core's deauth loop without adding or suppressing any kick. */
__attribute__((noinline)) esp_err_t __wrap_esp_wifi_deauth_sta(uint16_t aid)
{
    int64_t now=now_ms();unsigned count;bool report;
    portENTER_CRITICAL(&lock);
    count=++deauth_count;
    report=enabled && (count==1 || now-last_deauth_log>=1000);
    if(report) { last_deauth_log=now; }
    portEXIT_CRITICAL(&lock);
    if(report) {
        ESP_LOGW(TAG,"AP_DEAUTH_REQUEST node=%s aid=%u count=%u caller=%p",
                 node_role_id(),(unsigned)aid,count,__builtin_return_address(0));
    }
    return __real_esp_wifi_deauth_sta(aid);
}

bool mesh_access_retry_selection(bool proof_ready)
{
    int64_t now=now_ms();
    uint8_t channel,mac[6];bool save;
    portENTER_CRITICAL(&lock);
    save=hint_dirty;hint_dirty=false;channel=hint_channel;memcpy(mac,hint_bssid,6);
    bool busy=scanning || connecting || associated || now<settle_until;
    bool expired=connecting && now-connect_started>=10000;
    if(expired) { connect_started=now; }
    unsigned retry_ms=proof_ready?100:((scans%4)?500:2000);
    bool retry=enabled && !node_role_is_root() && !busy && now-last_selection>=retry_ms;
    if(retry) {
        last_selection=now;settle_until=now+500;
        // Pre-auth discovery attempts must not consume the post-proof fast path.
        // Do not pin this scan to a cached BSSID: the proof may be for another parent.
        if(proof_ready) { scans=0;first_hint_scan=false; }
    }
    portEXIT_CRITICAL(&lock);
    // Persist only a radio hint, in worker context; cached data never grants admission.
    if(save) {
        nvs_handle_t handle;
        if(nvs_open("mesh_access",NVS_READWRITE,&handle)==ESP_OK) {
            if(nvs_set_u8(handle,"channel",channel)==ESP_OK && nvs_set_blob(handle,"bssid",mac,6)==ESP_OK) {
                (void)nvs_commit(handle);
            }
            nvs_close(handle);
        }
    }
    if(expired) {
        ESP_LOGW(TAG,"ASSOC_TIMEOUT node=%s; requesting disconnect before retry",node_role_id());
        (void)esp_wifi_disconnect();
    }
    if(retry) {
        ESP_LOGI(TAG,"SELECT_RETRY node=%s trigger=%s",node_role_id(),proof_ready?"proof":"offline");
        esp_mesh_lite_connect();
    }
    return retry;
}

esp_err_t mesh_access_init(void)
{
    if(enabled) { return ESP_ERR_INVALID_STATE; }
    nvs_handle_t handle;
    if(nvs_open("mesh_access",NVS_READONLY,&handle)==ESP_OK) {
        uint8_t channel=0;size_t size=6;
        if(nvs_get_u8(handle,"channel",&channel)==ESP_OK && channel>=1 && channel<=14) {
            hint_channel=channel;
            if(nvs_get_blob(handle,"bssid",hint_bssid,&size)!=ESP_OK || size!=6 || (hint_bssid[0]&1)) {
                memset(hint_bssid,0,6);
            }
        }
        nvs_close(handle);
    }
    esp_err_t result=esp_event_handler_register(WIFI_EVENT,ESP_EVENT_ANY_ID,network_event,NULL);
    if(result==ESP_OK) { enabled=true;last_selection=now_ms(); }
    return result;
}
