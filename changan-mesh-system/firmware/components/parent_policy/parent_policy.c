#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include "sdkconfig.h"
#include "parent_policy.h"
#include "node_role.h"
#include "esp_mesh_lite.h"
#include "esp_wifi.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

typedef struct {
    uint32_t schema, revision;
    char mode[8], parent[33], bssid[18], ssid[33];
} policy_t;
static policy_t policy = {.schema=1,.mode="auto"};
static SemaphoreHandle_t lock;
static int64_t apply_at, attempt_at;
static bool fallback, pending;
static uint8_t allowed_mac[6];
static const char *TAG="parent_policy";

static const char *string(const cJSON *object,const char *key)
{
    const cJSON *value=cJSON_GetObjectItemCaseSensitive(object,key);
    return cJSON_IsString(value) ? value->valuestring : NULL;
}
static bool parse_mac(const char *text,uint8_t mac[6])
{
    unsigned int b[6];char end;
    if (!text || strlen(text)!=17 || sscanf(text,"%2x:%2x:%2x:%2x:%2x:%2x%c",&b[0],&b[1],&b[2],&b[3],&b[4],&b[5],&end)!=6) { return false; }
    unsigned any=0,all=255;
    for (int i=0;i<6;i++) { mac[i]=b[i];any|=b[i];all&=b[i]; }
    return any && all!=255 && !(mac[0]&1);
}
static bool valid(const policy_t *p)
{
    if (p->schema!=1 || !memchr(p->mode,0,sizeof(p->mode)) ||
        !memchr(p->parent,0,sizeof(p->parent)) || !memchr(p->ssid,0,sizeof(p->ssid)) ||
        !memchr(p->bssid,0,sizeof(p->bssid))) { return false; }
    if (!strcmp(p->mode,"auto")) { return !p->parent[0] && !p->ssid[0] && !p->bssid[0]; }
    uint8_t mac[6];
    return (!strcmp(p->mode,"prefer") || !strcmp(p->mode,"fixed")) && p->parent[0] && p->ssid[0] && parse_mac(p->bssid,mac);
}
static const uint8_t *candidate(const uint8_t *mac)
{
    /* Mesh-Lite copies the returned SSID immediately; static storage outlives callback. */
    static uint8_t ssid[33];
    xSemaphoreTake(lock,portMAX_DELAY);
    bool automatic=!strcmp(policy.mode,"auto") || fallback;
    bool allowed=mac && (automatic || !memcmp(mac,allowed_mac,6));
    if (allowed && !automatic) { memcpy(ssid,policy.ssid,sizeof(ssid)); }
    xSemaphoreGive(lock);
    if (!allowed) { return NULL; }
    if (automatic) {
        /* Match mesh_start's shared SSID convention without consuming scan records. */
#if CONFIG_BRIDGE_SOFTAP_SSID_END_WITH_THE_MAC
        snprintf((char *)ssid,sizeof(ssid),"%.20s_%02x%02x%02x",CONFIG_APP_SOFTAP_PREFIX,mac[3],mac[4],mac[5]);
#else
        snprintf((char *)ssid,sizeof(ssid),"%.20s",CONFIG_APP_SOFTAP_PREFIX);
#endif
    }
    return ssid;
}
static void policy_task(void *arg)
{
    (void)arg;
    for (;;) {
        bool reconnect=false;
        int64_t now=esp_timer_get_time()/1000;
        wifi_ap_record_t parent={0};bool connected=esp_wifi_sta_get_ap_info(&parent)==ESP_OK;
        xSemaphoreTake(lock,portMAX_DELAY);
        if (pending && now>=apply_at) { pending=false;fallback=false;attempt_at=now;reconnect=true; }
        if (!pending && !strcmp(policy.mode,"prefer") && !fallback) {
            if (connected && !memcmp(parent.bssid,allowed_mac,6)) { attempt_at=now; }
            else if (now-attempt_at>=30000) { fallback=true;reconnect=true; }
        }
        xSemaphoreGive(lock);
        if (reconnect) {
            ESP_LOGI(TAG,"Applying parent selection; wireless/MQTT reconnect expected");
            (void)esp_mesh_lite_disconnect();esp_mesh_lite_connect();
        }
        vTaskDelay(pdMS_TO_TICKS(250));
    }
}
esp_err_t parent_policy_init(void)
{
    if (!node_role_is_leaf()) { return ESP_OK; }
    lock=xSemaphoreCreateMutex();if (!lock) { return ESP_ERR_NO_MEM; }
    nvs_handle_t handle;esp_err_t result=nvs_open("parent_policy",NVS_READONLY,&handle);
    if (result==ESP_OK) {
        policy_t loaded={0};size_t size=sizeof(loaded);
        result=nvs_get_blob(handle,"config",&loaded,&size);nvs_close(handle);
        if (result==ESP_OK && size==sizeof(loaded) && valid(&loaded)) { policy=loaded; }
        else if (result!=ESP_ERR_NVS_NOT_FOUND) { return ESP_ERR_INVALID_STATE; }
    } else if (result!=ESP_ERR_NVS_NOT_FOUND) { return result; }
#if CONFIG_APP_PARENT_POLICY_RECOVERY_AUTO
    strcpy(policy.mode,"auto");policy.parent[0]=policy.ssid[0]=policy.bssid[0]=0;
    ESP_LOGW(TAG,"Maintenance recovery: ignoring saved parent binding for this boot");
#endif
    if (strcmp(policy.mode,"auto")) { (void)parse_mac(policy.bssid,allowed_mac); }
    attempt_at=esp_timer_get_time()/1000;
    result=esp_mesh_lite_get_ssid_by_mac_cb_register(candidate,true);
    if (result!=ESP_OK) { return result; }
    return xTaskCreate(policy_task,"parent_policy",6144,NULL,4,NULL)==pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
const char *parent_policy_prepare(const cJSON *payload)
{
    if (!lock || !node_role_is_leaf() || !cJSON_IsObject(payload)) { return "parent_policy_not_supported"; }
    policy_t next={.schema=1};uint8_t mac[6]={0};
    const char *mode=string(payload,"mode"),*parent=string(payload,"parent"),*bssid=string(payload,"bssid"),*ssid=string(payload,"ssid");
    const cJSON *revision=cJSON_GetObjectItemCaseSensitive(payload,"revision");
    if (!mode || strlen(mode)>=sizeof(next.mode) || !cJSON_IsNumber(revision) || revision->valuedouble<1 ||
        revision->valuedouble>UINT32_MAX || (double)(uint32_t)revision->valuedouble!=revision->valuedouble) { return "invalid_parent_policy"; }
    next.revision=(uint32_t)revision->valuedouble;strcpy(next.mode,mode);
    if (strcmp(mode,"auto")) {
        if (!parent || !parent[0] || strlen(parent)>32 || !ssid || !ssid[0] || strlen(ssid)>32 || !parse_mac(bssid,mac)) { return "invalid_parent_radio"; }
        strcpy(next.parent,parent);strcpy(next.bssid,bssid);strcpy(next.ssid,ssid);
    }
    if (!valid(&next)) { return "invalid_parent_policy"; }
    xSemaphoreTake(lock,portMAX_DELAY);
    if (next.revision<=policy.revision) {
        bool same=!memcmp(&next,&policy,sizeof(next));xSemaphoreGive(lock);
        return same ? NULL : "stale_parent_revision";
    }
    nvs_handle_t handle;esp_err_t result=nvs_open("parent_policy",NVS_READWRITE,&handle);
    if (result==ESP_OK) {
        result=nvs_set_blob(handle,"config",&next,sizeof(next));
        if (result==ESP_OK) { result=nvs_commit(handle); }nvs_close(handle);
    }
    if (result==ESP_OK) {
        policy=next;memcpy(allowed_mac,mac,6);pending=true;fallback=false;
        apply_at=esp_timer_get_time()/1000+2000;
    }
    xSemaphoreGive(lock);return result==ESP_OK ? NULL : "parent_policy_storage_failed";
}
void parent_policy_status(cJSON *payload)
{
    if (!lock || !node_role_is_leaf()) { return; }
    xSemaphoreTake(lock,portMAX_DELAY);
    cJSON *p=cJSON_AddObjectToObject(payload,"parent_policy");
    cJSON_AddStringToObject(p,"mode",policy.mode);cJSON_AddNumberToObject(p,"revision",policy.revision);
    cJSON_AddStringToObject(p,"parent",policy.parent);
    cJSON_AddStringToObject(p,"stage",pending ? "pending" : (fallback ? "fallback" : "active"));
    xSemaphoreGive(lock);
}
