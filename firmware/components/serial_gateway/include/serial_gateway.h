#pragma once
#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"
#include "app_protocol.h"

typedef struct {
    size_t size;
    char json[APP_JSON_MAX + 1];
} serial_message_t;
esp_err_t serial_gateway_start(void);
bool serial_gateway_publish(const char *json, size_t size);
bool serial_gateway_receive(serial_message_t *message);
