#pragma once
#include <stdbool.h>
#include "sdkconfig.h"
#include "mqtt_client.h"
#if CONFIG_APP_ROLE_PC_ROOT
void car_gateway_init(void);
bool car_gateway_event(esp_mqtt_client_handle_t client,int32_t id,esp_mqtt_event_handle_t event);
void car_gateway_poll(esp_mqtt_client_handle_t client,bool active);
#else
static inline void car_gateway_init(void) {}
static inline bool car_gateway_event(esp_mqtt_client_handle_t client,int32_t id,esp_mqtt_event_handle_t event) {
    (void)client;(void)id;(void)event;return false;
}
static inline void car_gateway_poll(esp_mqtt_client_handle_t client,bool active) {(void)client;(void)active;}
#endif
