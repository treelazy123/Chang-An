#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cJSON.h"

#define APP_PROTOCOL_VERSION 1
#define APP_JSON_MAX 1024
#define APP_COMMAND_MAX 1024
#define APP_NODE_ID_MAX 32
#define APP_MSG_ID_MAX 64

uint16_t app_crc16(uint16_t crc, const uint8_t *data, size_t size);
cJSON *app_message_parse(const char *json, size_t size);
bool app_node_id_valid(const char *id);
const char *app_json_string(const cJSON *object, const char *key);
bool app_command_valid(const cJSON *message);
cJSON *app_message_new(const char *type);
cJSON *app_status_payload(void);
cJSON *app_command_reply(const cJSON *command);
