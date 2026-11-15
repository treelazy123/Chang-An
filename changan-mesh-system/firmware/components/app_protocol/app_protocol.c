#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "esp_mesh_lite.h"
#include "node_role.h"
#include "app_protocol.h"

static const uint8_t MAGIC[4] = {'M', 'L', 'T', '1'};
uint16_t app_crc16(const uint8_t *data, size_t size)
{
    uint16_t crc = 0xffff;
    for (size_t i = 0; i < size; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (int bit = 0; bit < 8; ++bit) {
            crc = (uint16_t)((crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1);
        }
    }
    return crc;
}
size_t app_frame_encode(const char *json, size_t size, uint8_t out[APP_FRAME_MAX])
{
    if (!json || size < 2 || size > APP_JSON_MAX) { return 0; }
    memcpy(out, MAGIC, 4);
    out[4] = (uint8_t)(size >> 8);
    out[5] = (uint8_t)size;
    uint16_t crc = app_crc16((const uint8_t *)json, size);
    out[6] = (uint8_t)(crc >> 8);
    out[7] = (uint8_t)crc;
    memcpy(out + APP_FRAME_HEADER, json, size);
    return size + APP_FRAME_HEADER;
}
static void discard(app_frame_decoder_t *decoder, size_t size)
{
    memmove(decoder->data, decoder->data + size, decoder->used - size);
    decoder->used -= size;
}
void app_frame_feed(app_frame_decoder_t *decoder, uint8_t byte,
                    app_frame_callback_t callback, void *ctx)
{
    if (decoder->used == sizeof(decoder->data)) { discard(decoder, 1); }
    decoder->data[decoder->used++] = byte;
    while (decoder->used >= 4) {
        if (memcmp(decoder->data, MAGIC, 4)) { discard(decoder, 1); continue; }
        if (decoder->used < APP_FRAME_HEADER) { return; }
        size_t size = ((size_t)decoder->data[4] << 8) | decoder->data[5];
        if (size < 2 || size > APP_JSON_MAX) { discard(decoder, 1); continue; }
        if (decoder->used < APP_FRAME_HEADER + size) { return; }
        uint16_t expected = ((uint16_t)decoder->data[6] << 8) | decoder->data[7];
        if (app_crc16(decoder->data + APP_FRAME_HEADER, size) != expected) {
            discard(decoder, 1); continue;
        }
        char json[APP_JSON_MAX + 1];
        memcpy(json, decoder->data + APP_FRAME_HEADER, size);
        json[size] = '\0';
        discard(decoder, APP_FRAME_HEADER + size);
        callback(json, size, ctx);
    }
}
const char *app_json_string(const cJSON *object, const char *key)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, key);
    return cJSON_IsString(item) ? item->valuestring : NULL;
}
bool app_node_id_valid(const char *id)
{
    if (!id || !id[0] || strlen(id) > APP_NODE_ID_MAX) { return false; }
    for (const unsigned char *p = (const unsigned char *)id; *p; ++p) {
        if (!((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
              (*p >= '0' && *p <= '9') || *p == '-' || *p == '_')) { return false; }
    }
    return true;
}
cJSON *app_message_parse(const char *json, size_t size)
{
    if (!json || size < 2 || size > APP_JSON_MAX || memchr(json, '\0', size)) { return NULL; }
    const char *end = NULL;
    cJSON *message = cJSON_ParseWithLengthOpts(json, size + 1, &end, true);
    if (!cJSON_IsObject(message)) { cJSON_Delete(message); return NULL; }
    const cJSON *version = cJSON_GetObjectItemCaseSensitive(message, "v");
    const char *type = app_json_string(message, "type");
    if (!cJSON_IsNumber(version) || version->valuedouble != APP_PROTOCOL_VERSION ||
        !type || !type[0] || strlen(type) > 24) {
        cJSON_Delete(message); return NULL;
    }
    // Reject duplicate top-level keys to keep PC and firmware interpretation identical.
    for (const cJSON *a = message->child; a; a = a->next) {
        for (const cJSON *b = a->next; b; b = b->next) {
            if (!strcmp(a->string, b->string)) { cJSON_Delete(message); return NULL; }
        }
    }
    return message;
}
bool app_command_valid(const cJSON *message)
{
    const char *type = app_json_string(message, "type");
    const char *target = app_json_string(message, "target");
    const char *id = app_json_string(message, "msg_id");
    const char *op = app_json_string(message, "op");
    if (!type || strcmp(type, "command") || !app_node_id_valid(target) ||
        !id || !id[0] || strlen(id) > APP_MSG_ID_MAX || !op || !op[0] || strlen(op) > 24) { return false; }
    return true;
}
cJSON *app_message_new(const char *type)
{
    cJSON *message = cJSON_CreateObject();
    if (message) {
        cJSON_AddNumberToObject(message, "v", APP_PROTOCOL_VERSION);
        cJSON_AddStringToObject(message, "type", type);
        cJSON_AddStringToObject(message, "node_id", node_role_id());
    }
    return message;
}
static void status_add_ip(cJSON *payload, const char *key, const esp_ip4_addr_t *ip)
{
    if (ip->addr) {
        char text[16];
        snprintf(text, sizeof(text), IPSTR, IP2STR(ip));
        cJSON_AddStringToObject(payload, key, text);
    }
}
static void status_add_network(cJSON *payload)
{
    esp_netif_ip_info_t info = {0};
    esp_netif_t *sta = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_t *ap = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    if (sta && esp_netif_get_ip_info(sta, &info) == ESP_OK && info.ip.addr) {
        status_add_ip(payload, "sta_ip", &info.ip);
        status_add_ip(payload, "gateway", &info.gw);
        status_add_ip(payload, "netmask", &info.netmask);
    }
    if (ap && esp_netif_get_ip_info(ap, &info) == ESP_OK) {
        status_add_ip(payload, "ap_ip", &info.ip);
    }
    uint8_t mac[6];
    char text[18];
    if (esp_wifi_get_mac(WIFI_IF_STA, mac) == ESP_OK) {
        snprintf(text, sizeof(text), MACSTR, MAC2STR(mac));
        cJSON_AddStringToObject(payload, "sta_mac", text);
    }
    if (esp_wifi_get_mac(WIFI_IF_AP, mac) == ESP_OK) {
        snprintf(text, sizeof(text), MACSTR, MAC2STR(mac));
        cJSON_AddStringToObject(payload, "ap_mac", text);
    }
    wifi_ap_record_t parent = {0};
    bool connected = esp_wifi_sta_get_ap_info(&parent) == ESP_OK;
    cJSON_AddBoolToObject(payload, "parent_connected", connected);
    if (connected) {
        snprintf(text, sizeof(text), MACSTR, MAC2STR(parent.bssid));
        cJSON_AddStringToObject(payload, "parent_bssid", text);
        cJSON_AddNumberToObject(payload, "rssi", parent.rssi);
    }
    uint8_t channel;
    wifi_second_chan_t secondary;
    if (esp_wifi_get_channel(&channel, &secondary) == ESP_OK) {
        cJSON_AddNumberToObject(payload, "channel", channel);
    }
    wifi_sta_list_t children = {0};
    if (esp_wifi_ap_get_sta_list(&children) == ESP_OK) {
        cJSON_AddNumberToObject(payload, "associated_children", children.num);
    }
}
cJSON *app_status_payload(void)
{
    cJSON *payload = cJSON_CreateObject();
    if (payload) {
        cJSON_AddStringToObject(payload, "role", node_role_name());
        cJSON_AddStringToObject(payload, "topology", node_topology_name());
        cJSON_AddNumberToObject(payload, "level", esp_mesh_lite_get_level());
        cJSON_AddNumberToObject(payload, "heap", esp_get_free_heap_size());
        cJSON_AddNumberToObject(payload, "heap_min", esp_get_minimum_free_heap_size());
        cJSON_AddNumberToObject(payload, "uptime_ms", (double)(esp_timer_get_time() / 1000));
        status_add_network(payload);
    }
    return payload;
}
cJSON *app_command_reply(const cJSON *command)
{
    if (!app_command_valid(command)) { return NULL; }
    const char *target = app_json_string(command, "target");
    const char *op = app_json_string(command, "op");
    cJSON *reply = app_message_new("ack");
    if (!reply) { return NULL; }
    cJSON_AddStringToObject(reply, "msg_id", app_json_string(command, "msg_id"));
    cJSON_AddStringToObject(reply, "op", op);
    bool addressed = !strcmp(target, node_role_id());
    bool supported = !strcmp(op, "ping") || !strcmp(op, "status") || !strcmp(op, "echo");
    cJSON_AddBoolToObject(reply, "ok", addressed && supported);
    if (!addressed) {
        cJSON_AddStringToObject(reply, "error", "wrong_target");
    } else if (!supported) {
        cJSON_AddStringToObject(reply, "error", "unsupported_operation");
    } else if (!strcmp(op, "echo")) {
        const cJSON *payload = cJSON_GetObjectItemCaseSensitive(command, "payload");
        cJSON *copy = payload ? cJSON_Duplicate(payload, true) : cJSON_CreateNull();
        if (copy) { cJSON_AddItemToObject(reply, "payload", copy); }
    } else {
        cJSON *status = app_status_payload();
        if (status) { cJSON_AddItemToObject(reply, "payload", status); }
    }
    return reply;
}
