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

static const char *TAG = "mesh_lab";

void network_mesh_lite_log_status(void)
{
    uint8_t sta_mac[6] = {0}, ap_mac[6] = {0}, channel = 0;
    wifi_second_chan_t secondary;
    wifi_ap_record_t parent = {0};
    wifi_sta_list_t children = {0};
    esp_netif_ip_info_t sta_ip = {0}, ap_ip = {0};

    /* AP/STA mode changes may race this diagnostic sample. A temporarily
     * unavailable interface is not a reason to reboot the node. */
    (void)esp_wifi_get_mac(WIFI_IF_STA, sta_mac);
    (void)esp_wifi_get_mac(WIFI_IF_AP, ap_mac);
    (void)esp_wifi_get_channel(&channel, &secondary);
    const bool parent_connected = esp_wifi_sta_get_ap_info(&parent) == ESP_OK;
    const esp_err_t children_result = esp_wifi_ap_get_sta_list(&children);
    const int associated_count = children_result == ESP_OK ? (int)children.num : -1;
    uint16_t ap_inactive_s = 0;
    const esp_err_t inactive_result = esp_wifi_get_inactive_time(WIFI_IF_AP, &ap_inactive_s);
    esp_netif_t *sta = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_t *ap = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    if (sta != NULL) {
        (void)esp_netif_get_ip_info(sta, &sta_ip);
    }
    if (ap != NULL) {
        (void)esp_netif_get_ip_info(ap, &ap_ip);
    }

    ESP_LOGI(TAG, "STATUS node=%s role=%s topology=%s level=%u channel=%u parent_connected=%u parent=" MACSTR " rssi=%d children=%d heap=%u heap_min=%u",
             node_role_id(), node_role_name(), node_topology_name(),
             (unsigned)esp_mesh_lite_get_level(), (unsigned)channel,
             (unsigned)parent_connected, MAC2STR(parent.bssid),
             parent_connected ? parent.rssi : -127,
             associated_count, (unsigned)esp_get_free_heap_size(),
             (unsigned)esp_get_minimum_free_heap_size());
    /* This is the driver's association table, not the number of live TCP peers.
     * Read the configured timeout instead of assuming the SDK default applies. */
    ESP_LOGI(TAG, "AP_TRACKING node=%s wifi_assoc=%d inactive_s=%d list_rc=%s timeout_rc=%s",
             node_role_id(), associated_count,
             inactive_result == ESP_OK ? (int)ap_inactive_s : -1,
             esp_err_to_name(children_result), esp_err_to_name(inactive_result));
    if (children_result == ESP_OK) {
        const int capacity = sizeof(children.sta) / sizeof(children.sta[0]);
        for (int i = 0; i < associated_count && i < capacity; ++i) {
            const wifi_sta_info_t *child = &children.sta[i];
            uint16_t aid = 0;
            const esp_err_t aid_result = esp_wifi_ap_get_sta_aid(child->mac, &aid);
            ESP_LOGI(TAG, "AP_ASSOC node=%s mac=" MACSTR " aid=%u aid_rc=%s rssi_recorded=%d mesh_child=%u",
                     node_role_id(), MAC2STR(child->mac), (unsigned)aid,
                     esp_err_to_name(aid_result), (int)child->rssi, (unsigned)child->is_mesh_child);
        }
    }
    ESP_LOGI(TAG, "ADDR node=%s sta_mac=" MACSTR " ap_mac=" MACSTR " sta_ip=" IPSTR " gateway=" IPSTR " ap_ip=" IPSTR,
             node_role_id(), MAC2STR(sta_mac), MAC2STR(ap_mac),
             IP2STR(&sta_ip.ip), IP2STR(&sta_ip.gw), IP2STR(&ap_ip.ip));
    /* IDF reports high-water marks in bytes. This samples the shared timer task. */
    ESP_LOGI(TAG, "STACK node=%s timer_size=%u timer_min_free=%u",
             node_role_id(), (unsigned)CONFIG_FREERTOS_TIMER_TASK_STACK_DEPTH,
             (unsigned)uxTaskGetStackHighWaterMark(xTimerGetTimerDaemonTaskHandle()));
}
