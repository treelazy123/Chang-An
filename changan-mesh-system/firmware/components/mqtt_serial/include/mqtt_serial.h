#pragma once
#include "esp_err.h"
typedef enum {
    MQTT_SERIAL_UGV_STA,
    MQTT_SERIAL_UGV_SOFTAP,
} mqtt_serial_ingress_t;
esp_err_t mqtt_serial_start(mqtt_serial_ingress_t ingress);
