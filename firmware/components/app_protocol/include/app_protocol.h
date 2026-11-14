#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cJSON.h"

#define APP_PROTOCOL_VERSION 1
#define APP_JSON_MAX 1024
#define APP_FRAME_HEADER 8
#define APP_FRAME_MAX (APP_JSON_MAX + APP_FRAME_HEADER)
#define APP_NODE_ID_MAX 32
#define APP_MSG_ID_MAX 64

typedef struct {
    size_t used;
    uint8_t data[APP_FRAME_MAX];
} app_frame_decoder_t;
typedef void (*app_frame_callback_t)(const char *json, size_t size, void *ctx);
uint16_t app_crc16(const uint8_t *data, size_t size);
size_t app_frame_encode(const char *json, size_t size, uint8_t out[APP_FRAME_MAX]);
void app_frame_feed(app_frame_decoder_t *decoder, uint8_t byte,
                    app_frame_callback_t callback, void *ctx);
cJSON *app_message_parse(const char *json, size_t size);
bool app_node_id_valid(const char *id);
const char *app_json_string(const cJSON *object, const char *key);
bool app_command_valid(const cJSON *message);
cJSON *app_message_new(const char *type);
cJSON *app_status_payload(void);
cJSON *app_command_reply(const cJSON *command);
