#include <stdio.h>
#include <string.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/timers.h"
#include "esp_err.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "esp_bridge.h"
#include "esp_mesh_lite.h"
#include "node_role.h"
#include "network_mesh_lite.h"
#include "parent_policy.h"

static const char *TAG = "mesh_lab";

static void ap_peer_event(void *arg, esp_event_base_t base, int32_t event_id, void *data)
{
    (void)arg;
    (void)base;
    if (!data) { return; }
    if (event_id == WIFI_EVENT_AP_STACONNECTED) {
        const wifi_event_ap_staconnected_t *event = data;
        ESP_LOGI(TAG, "AP_JOIN node=%s mac=" MACSTR " aid=%u mesh_child=%u",
                 node_role_id(), MAC2STR(event->mac), (unsigned)event->aid,
                 (unsigned)event->is_mesh_child);
    } else if (event_id == WIFI_EVENT_AP_STADISCONNECTED) {
        const wifi_event_ap_stadisconnected_t *event = data;
        ESP_LOGI(TAG, "AP_LEAVE node=%s mac=" MACSTR " aid=%u reason=%u mesh_child=%u",
                 node_role_id(), MAC2STR(event->mac), (unsigned)event->aid,
                 (unsigned)event->reason, (unsigned)event->is_mesh_child);
    }
}


void network_mesh_lite_start(void)
{
    const size_t password_len = strlen(CONFIG_APP_SOFTAP_PASSWORD);
    ESP_ERROR_CHECK(password_len >= 8 && password_len <= 63
                    ? ESP_OK : ESP_ERR_INVALID_ARG);
    /* Do not silently erase persisted state on an NVS error. */
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, WIFI_EVENT_AP_STACONNECTED,
                                                       ap_peer_event, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, WIFI_EVENT_AP_STADISCONNECTED,
                                                       ap_peer_event, NULL, NULL));
    esp_bridge_create_all_netif();
    ESP_ERROR_CHECK(network_mesh_lite_configure_addresses());

    wifi_config_t station_config = {0};
    ESP_ERROR_CHECK(esp_bridge_wifi_set_config(WIFI_IF_STA, &station_config));

    wifi_config_t ap_config = {0};
    /* IoT-Bridge appends the MAC suffix when the shared default enables it. */
    snprintf((char *)ap_config.ap.ssid, sizeof(ap_config.ap.ssid), "%.20s",
             CONFIG_APP_SOFTAP_PREFIX);
    snprintf((char *)ap_config.ap.password, sizeof(ap_config.ap.password),
             "%s", CONFIG_APP_SOFTAP_PASSWORD);
    ap_config.ap.channel = CONFIG_APP_MESH_CHANNEL;
    ESP_ERROR_CHECK(esp_bridge_wifi_set_config(WIFI_IF_AP, &ap_config));

    esp_mesh_lite_config_t config = ESP_MESH_LITE_DEFAULT_INIT();
    config.join_mesh_ignore_router_status = true;
    config.join_mesh_without_configured_wifi = !node_role_is_root();
    config.leaf_node = node_role_is_leaf();
    esp_mesh_lite_init(&config);
    wifi_config_t applied_ap = {0};
    ESP_ERROR_CHECK(esp_wifi_get_config(WIFI_IF_AP, &applied_ap));
    char ssid[sizeof(applied_ap.ap.ssid) + 1] = {0};
    memcpy(ssid, applied_ap.ap.ssid, sizeof(applied_ap.ap.ssid));
    ESP_ERROR_CHECK(esp_mesh_lite_set_softap_info(ssid, CONFIG_APP_SOFTAP_PASSWORD));
    if (node_role_is_leaf()) {
        /* Mesh-Lite initializes AP bookkeeping, but leaves must not serve a LAN. */
        esp_mesh_lite_set_leaf_node_softap_status(DISABLE_SOFTAP);
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        esp_netif_t *ap = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
        if (ap) {
            esp_netif_ip_info_t current = {0}, empty = {0};
            ESP_ERROR_CHECK(esp_netif_get_ip_info(ap, &current));
            ESP_ERROR_CHECK(esp_bridge_netif_set_ip_info(ap, &current, false, false));
            esp_netif_dhcp_status_t state;
            ESP_ERROR_CHECK(esp_netif_dhcps_get_status(ap, &state));
            if (state != ESP_NETIF_DHCP_STOPPED) { ESP_ERROR_CHECK(esp_netif_dhcps_stop(ap)); }
            ESP_ERROR_CHECK(esp_netif_set_ip_info(ap, &empty));
        }
        ESP_LOGI(TAG, "AP_DISABLED node=%s mode=STA", node_role_id());
    }

    if (!node_role_is_root()) {
        ESP_ERROR_CHECK(esp_mesh_lite_set_disallowed_level(1));
    }
    const uint8_t fixed_level = node_role_fixed_level();
    if (fixed_level != 0) {
        ESP_ERROR_CHECK(esp_mesh_lite_set_allowed_level(fixed_level));
    }

    ESP_LOGI(TAG, "BOOT node=%s role=%s topology=%s fixed_level=%u target=esp32c6 idf=%s",
             node_role_id(), node_role_name(), node_topology_name(),
             (unsigned)fixed_level, esp_get_idf_version());
    ESP_ERROR_CHECK(parent_policy_init());
    esp_mesh_lite_start();
}

