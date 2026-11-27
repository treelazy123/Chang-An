#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_event.h"
#include "esp_wifi.h"
#include "esp_random.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_netif.h"
#include "esp_mesh_lite.h"
#include "lwip/sockets.h"
#include "lwip/inet.h"
#include "app_protocol.h"
#include "node_role.h"
#include "service_discovery.h"

#define SERVICE_TYPE "changan_ugv_mqtt_v1"
#define SERVICE_QUERY "changan_ugv_mqtt_query_v1"
#define SERVICE_PORT CONFIG_APP_MQTT_PORT
#define SERVICE_TTL_MS 15000
#define ROOT_NETIF "WIFI_AP_DEF"
#define ROOT_MIN_LEVEL 1
#define DISCOVERY_CHANGED (1U << 0)
#define CHILD_JOINED (1U << 1)
#define IP_READY (1U << 2)
#define SERVICE_REQUESTED (1U << 3)
#define FAST_PERIOD_MS 500
#define NORMAL_PERIOD_MS 3000
#define JOIN_BURST_MS 8000

typedef struct {
    uint32_t address;
    uint32_t ap_address;
    uint32_t sequence;
    char epoch[17];
    int64_t seen_ms;
} service_t;
static const char *TAG = "ugv_discovery";
static service_t s_service;
static portMUX_TYPE s_lock = portMUX_INITIALIZER_UNLOCKED;
static EventGroupHandle_t s_changed;
static TaskHandle_t s_discovery_task;

static void network_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg; (void)data;
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        xEventGroupSetBits(s_changed, DISCOVERY_CHANGED);
        if(s_discovery_task) { xTaskNotify(s_discovery_task, IP_READY, eSetBits); }
    }
    if (base == WIFI_EVENT && id == WIFI_EVENT_AP_STACONNECTED && s_discovery_task) {
        xTaskNotify(s_discovery_task, CHILD_JOINED, eSetBits);
    }
}

void service_discovery_wait(uint32_t timeout_ms)
{
    if (s_changed) {
        xEventGroupWaitBits(s_changed, DISCOVERY_CHANGED, pdTRUE, pdFALSE, pdMS_TO_TICKS(timeout_ms));
    } else {
        vTaskDelay(pdMS_TO_TICKS(timeout_ms));
    }
}

static cJSON *service_received(cJSON *payload, uint32_t sequence)
{
    (void)sequence;
    const char *id = app_json_string(payload, "node_id");
    const char *ip = app_json_string(payload, "ip");
    const char *epoch = app_json_string(payload, "epoch");
    const cJSON *seq = cJSON_GetObjectItemCaseSensitive(payload, "generation");
    const cJSON *port = cJSON_GetObjectItemCaseSensitive(payload, "port");
    struct in_addr address;
    struct in_addr ap_address = {0};
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
    const char *ap_ip = app_json_string(payload, "ap_ip");
    const char *broker = app_json_string(payload, "broker");
    if (!ap_ip || !broker || strcmp(broker, CONFIG_APP_MQTT_SERVER_NAME) ||
        inet_pton(AF_INET, ap_ip, &ap_address) != 1 || !ap_address.s_addr ||
        ap_address.s_addr == INADDR_BROADCAST) { return NULL; }
#endif
    if (!id || strcmp(id, CONFIG_APP_UGV_NODE_ID) || !ip || !epoch ||
        !epoch[0] || strlen(epoch) > 16 || !cJSON_IsNumber(seq) ||
        seq->valuedouble < 0 || seq->valuedouble > UINT32_MAX ||
        !cJSON_IsNumber(port) || port->valuedouble != SERVICE_PORT ||
        inet_pton(AF_INET, ip, &address) != 1 || !address.s_addr ||
        address.s_addr == INADDR_BROADCAST) { return NULL; }
    service_t incoming = {.address = address.s_addr, .ap_address = ap_address.s_addr, .sequence = (uint32_t)seq->valuedouble,
                          .seen_ms = esp_timer_get_time() / 1000};
    snprintf(incoming.epoch, sizeof(incoming.epoch), "%s", epoch);
    bool address_changed, updated;
    portENTER_CRITICAL(&s_lock);
    address_changed = s_service.address != incoming.address || s_service.ap_address != incoming.ap_address || strcmp(s_service.epoch, incoming.epoch);
    // Forwarded copies of the same announcement cannot keep a dead service alive.
    updated = address_changed || s_service.sequence != incoming.sequence;
    if (updated) { s_service = incoming; }
    portEXIT_CRITICAL(&s_lock);
    if (updated) {
        xEventGroupSetBits(s_changed, DISCOVERY_CHANGED);
        if (s_discovery_task) { xTaskNotify(s_discovery_task, DISCOVERY_CHANGED, eSetBits); }
    }
    if (address_changed) {
        ESP_LOGI(TAG, "UGV_SERVICE node=%s ugv=%s target=%s:%d", node_role_id(), id, ip, SERVICE_PORT);
    }
    return NULL;
}
static cJSON *service_requested(cJSON *payload,uint32_t sequence)
{
    (void)sequence;
    const char *root=app_json_string(payload,"root_id");
    if(root && !strcmp(root,CONFIG_APP_UGV_NODE_ID) && !node_role_is_leaf() && s_discovery_task) {
        // Coalesced and rate-limited by the worker. A query only triggers discovery.
        xTaskNotify(s_discovery_task,SERVICE_REQUESTED,eSetBits);
    }
    return NULL;
}
static const esp_mesh_lite_msg_action_t s_actions[] = {
    {SERVICE_TYPE, NULL, service_received},
    {SERVICE_QUERY, NULL, service_requested},
    {NULL, NULL, NULL},
};
bool service_discovery_ugv(uint32_t *address)
{
    service_t value;
    portENTER_CRITICAL(&s_lock); value = s_service; portEXIT_CRITICAL(&s_lock);
    if (!value.address || esp_timer_get_time() / 1000 - value.seen_ms > SERVICE_TTL_MS) { return false; }
    *address = value.address;
    return true;
}
bool service_discovery_ugv_ap(uint32_t *address)
{
    service_t value;
    portENTER_CRITICAL(&s_lock); value = s_service; portEXIT_CRITICAL(&s_lock);
    if (!value.ap_address || esp_timer_get_time()/1000-value.seen_ms>SERVICE_TTL_MS) { return false; }
    *address = value.ap_address; return true;
}
static void add_mqtt_metadata(cJSON *payload, uint32_t ap)
{
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
    char ip[16]; struct in_addr a = {.s_addr=ap};
    if (inet_ntop(AF_INET,&a,ip,sizeof(ip))) { cJSON_AddStringToObject(payload,"ap_ip",ip); }
    cJSON_AddStringToObject(payload,"broker",CONFIG_APP_MQTT_SERVER_NAME);
#else
    (void)payload; (void)ap;
#endif
}
static void announce(cJSON *payload, esp_err_t (*send)(const char *))
{
    esp_mesh_lite_msg_config_t config = {.json_msg = {
        .send_msg = SERVICE_TYPE, .expect_msg = NULL, .max_retry = 1,
        .retry_interval = 1000, .req_payload = payload, .resend = send,
    }};
    esp_err_t result = esp_mesh_lite_send_msg(ESP_MESH_LITE_JSON_MSG, &config);
    if (result != ESP_OK) { ESP_LOGW(TAG, "Service announcement failed: %s", esp_err_to_name(result)); }
}
static void request_service(void)
{
    cJSON *payload=cJSON_CreateObject();
    if(!payload) { return; }
    cJSON_AddStringToObject(payload,"root_id",CONFIG_APP_UGV_NODE_ID);
    cJSON_AddStringToObject(payload,"node_id",node_role_id());
    esp_mesh_lite_msg_config_t config={.json_msg={.send_msg=SERVICE_QUERY,.expect_msg=NULL,
        .max_retry=1,.retry_interval=1000,.req_payload=payload,.resend=esp_mesh_lite_send_msg_to_parent}};
    esp_err_t result=esp_mesh_lite_send_msg(ESP_MESH_LITE_JSON_MSG,&config);
    ESP_LOGI(TAG,"SERVICE_QUERY node=%s result=%s",node_role_id(),esp_err_to_name(result));
    cJSON_Delete(payload);
}
static void discovery_task(void *arg)
{
    (void)arg;
    uint32_t generation = 0;
#if CONFIG_APP_ROOT_GATEWAY
    uint32_t last_announced_ip = 0;
#endif
    char epoch[17];
    snprintf(epoch, sizeof(epoch), "%08" PRIx32 "%08" PRIx32, esp_random(), esp_random());
    int64_t fast_until = esp_timer_get_time() / 1000 + JOIN_BURST_MS;
    int64_t query_until=0,last_query=-1000,last_announce=-500;
    uint32_t events=0;
    for (;;) {
        int64_t now=esp_timer_get_time()/1000;
        if(events & (IP_READY|CHILD_JOINED|SERVICE_REQUESTED)) { fast_until=now+JOIN_BURST_MS; }
        if(events & IP_READY) { query_until=now+JOIN_BURST_MS; }
#if !CONFIG_APP_ROOT_GATEWAY
        uint32_t cached;
        bool have_service=service_discovery_ugv(&cached);
        if((events&SERVICE_REQUESTED) && !have_service) { query_until=now+JOIN_BURST_MS; }
        if(now-last_query>=500 && ((now<query_until && !have_service) ||
                                  ((events&SERVICE_REQUESTED) && !have_service))) {
            request_service();last_query=now;
        }
#endif
        cJSON *payload = NULL;
#if CONFIG_APP_ROOT_GATEWAY
        esp_netif_t *sta = esp_netif_get_handle_from_ifkey(ROOT_NETIF);
        esp_netif_ip_info_t local = {0};
        if (sta && esp_mesh_lite_get_level() >= ROOT_MIN_LEVEL &&
            esp_netif_get_ip_info(sta, &local) == ESP_OK && local.ip.addr) {
            char ip[16]; snprintf(ip, sizeof(ip), IPSTR, IP2STR(&local.ip));
            if (last_announced_ip != local.ip.addr) {
                ESP_LOGI(TAG, "UGV_ADVERTISE node=%s target=%s:%d", node_role_id(), ip, SERVICE_PORT);
                last_announced_ip = local.ip.addr;
            }
            payload = cJSON_CreateObject();
            if (payload) {
                cJSON_AddStringToObject(payload, "node_id", node_role_id());
                cJSON_AddStringToObject(payload, "ip", ip);
                esp_netif_ip_info_t ap_info = {0};
                esp_netif_t *ap = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
                if(ap) { (void)esp_netif_get_ip_info(ap,&ap_info); }
                add_mqtt_metadata(payload,ap_info.ip.addr);
                cJSON_AddStringToObject(payload, "epoch", epoch);
                cJSON_AddNumberToObject(payload, "generation", ++generation);
                cJSON_AddNumberToObject(payload, "port", SERVICE_PORT);
                // The root announces its AP ingress down the registered mesh tree.

            }
        }
#else
        (void)generation;
        uint32_t address;
        if (service_discovery_ugv(&address)) {
            service_t record;
            portENTER_CRITICAL(&s_lock); record = s_service; portEXIT_CRITICAL(&s_lock);
            char ip[16]; struct in_addr ipv4 = {.s_addr = record.address};
            if (inet_ntop(AF_INET, &ipv4, ip, sizeof(ip))) {
                payload = cJSON_CreateObject();
                if (payload) {
                    cJSON_AddStringToObject(payload, "node_id", CONFIG_APP_UGV_NODE_ID);
                    cJSON_AddStringToObject(payload, "ip", ip);
                    add_mqtt_metadata(payload,record.ap_address);
                    cJSON_AddStringToObject(payload, "epoch", record.epoch);
                    cJSON_AddNumberToObject(payload, "generation", record.sequence);
                    cJSON_AddNumberToObject(payload, "port", SERVICE_PORT);
                }
            }
        }
#endif
        if (payload && !node_role_is_leaf() && now-last_announce>=100) {
            announce(payload, esp_mesh_lite_send_broadcast_msg_to_child);last_announce=now;
        }
        cJSON_Delete(payload);
        // Bound work even when several children send queries simultaneously.
        int64_t elapsed=esp_timer_get_time()/1000-now;
        if(elapsed<100) { vTaskDelay(pdMS_TO_TICKS(100-elapsed)); }
        uint32_t period = esp_timer_get_time() / 1000 < fast_until ? FAST_PERIOD_MS : NORMAL_PERIOD_MS;
        events=0;
        xTaskNotifyWait(0, UINT32_MAX, &events, pdMS_TO_TICKS(period));
        if (events & CHILD_JOINED) { fast_until = esp_timer_get_time() / 1000 + JOIN_BURST_MS; }
    }
}
esp_err_t service_discovery_start(void)
{
    if (!app_node_id_valid(CONFIG_APP_UGV_NODE_ID)) { return ESP_ERR_INVALID_ARG; }
#if CONFIG_APP_ROOT_GATEWAY
    if (strcmp(node_role_id(), CONFIG_APP_UGV_NODE_ID)) { return ESP_ERR_INVALID_ARG; }
#endif
    s_changed = xEventGroupCreate();
    if (!s_changed) { return ESP_ERR_NO_MEM; }
    esp_err_t result = esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, network_event, NULL);
    if (result != ESP_OK) { return result; }
    result = esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_AP_STACONNECTED, network_event, NULL);
    if (result != ESP_OK) { return result; }
    result = esp_mesh_lite_msg_action_list_register(s_actions);
    if (result != ESP_OK) { return result; }
    return xTaskCreate(discovery_task, "ugv_discovery", 4096, NULL, 3, &s_discovery_task) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
