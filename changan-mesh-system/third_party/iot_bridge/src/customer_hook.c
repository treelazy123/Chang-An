/*
 * SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "esp_wifi.h"
#include "lwip/lwip_napt.h"

__attribute__((weak)) int custom_hook_ip4_napt_add_failed(void)
{
    printf("IP_NAPT_MAX:%d, IP_PORTMAP_MAX:%d, IP_NAPT_TIMEOUT_MS_TCP:%d\r\n", IP_NAPT_MAX, IP_PORTMAP_MAX, IP_NAPT_TIMEOUT_MS_TCP);
    return 0;
}

/* Serialize NAPT table mutations with packet processing on the TCP/IP task. */
#include "esp_netif.h"
#include "esp_err.h"

void ip_napt_table_clear(void);

static esp_err_t bridge_napt_clear_in_tcpip(void *ctx)
{
    (void)ctx;
    ip_napt_table_clear();
    return ESP_OK;
}

void bridge_napt_table_clear(void)
{
    ESP_ERROR_CHECK(esp_netif_tcpip_exec(bridge_napt_clear_in_tcpip, NULL));
}
