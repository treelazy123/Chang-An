#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
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
#define SERVICE_PORT CONFIG_APP_MQTT_PORT
#define SERVICE_TTL_MS 15000
#define ROOT_NETIF "WIFI_AP_DEF"
#define ROOT_MIN_LEVEL 1

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
    bool address_changed;
    portENTER_CRITICAL(&s_lock);
    address_changed = s_service.address != incoming.address || s_service.ap_address != incoming.ap_address || strcmp(s_service.epoch, incoming.epoch);
    // Forwarded copies of the same announcement cannot keep a dead service alive.
    if (s_service.address != incoming.address || s_service.ap_address != incoming.ap_address || s_service.sequence != incoming.sequence ||
        strcmp(s_service.epoch, incoming.epoch)) { s_service = incoming; }
    portEXIT_CRITICAL(&s_lock);
    if (address_changed) {
        ESP_LOGI(TAG, "UGV_SERVICE node=%s ugv=%s target=%s:%d", node_role_id(), id, ip, SERVICE_PORT);
    }
    return NULL;
}
static const esp_mesh_lite_msg_action_t s_actions[] = {
    {SERVICE_TYPE, NULL, service_received},
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
static void discovery_task(void *arg)
{
    (void)arg;
    uint32_t generation = 0;
#if CONFIG_APP_ROOT_GATEWAY
    uint32_t last_announced_ip = 0;
#endif
    char epoch[17];
    snprintf(epoch, sizeof(epoch), "%08" PRIx32 "%08" PRIx32, esp_random(), esp_random());
    for (;;) {
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
        if (payload && !node_role_is_leaf()) { announce(payload, esp_mesh_lite_send_broadcast_msg_to_child); }
        cJSON_Delete(payload);
        vTaskDelay(pdMS_TO_TICKS(3000));
    }
}
esp_err_t service_discovery_start(void)
{
    if (!app_node_id_valid(CONFIG_APP_UGV_NODE_ID)) { return ESP_ERR_INVALID_ARG; }
#if CONFIG_APP_ROOT_GATEWAY
    if (strcmp(node_role_id(), CONFIG_APP_UGV_NODE_ID)) { return ESP_ERR_INVALID_ARG; }
#endif
    esp_err_t result = esp_mesh_lite_msg_action_list_register(s_actions);
    if (result != ESP_OK) { return result; }
    return xTaskCreate(discovery_task, "ugv_discovery", 4096, NULL, 3, NULL) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
