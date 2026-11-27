#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
esp_err_t service_discovery_start(void);
/* Returns a network-byte-order UGV STA address, never the immediate parent GW. */
bool service_discovery_ugv(uint32_t *address);

/* MQTT downstream endpoint: advertised UGV SoftAP, not Micro parent GW. */
bool service_discovery_ugv_ap(uint32_t *address);

/* Wake the MQTT task when discovery or STA IP changes; bounded fallback wait. */
void service_discovery_wait(uint32_t timeout_ms);
