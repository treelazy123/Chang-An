#include "sdkconfig.h"
#include "esp_bridge.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mesh_lite.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "node_role.h"
#include "network_mesh_lite.h"

static const char *TAG = "mesh_address";

static void parent_ip_received(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg; (void)base; (void)id;
    const ip_event_got_ip_t *event = data;
    esp_netif_ip_info_t ap_ip = {0};
    esp_netif_t *ap = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    if (!event || !ap || esp_netif_get_ip_info(ap, &ap_ip) != ESP_OK) { return; }
    /* A managed /24 can still overlap a legacy parent's broader subnet. */
    const uint32_t different = event->ip_info.ip.addr ^ ap_ip.ip.addr;
    if ((different & event->ip_info.netmask.addr) == 0 ||
        (different & ap_ip.netmask.addr) == 0) {
        ESP_LOGE(TAG, "AP_SUBNET_OVERLAP node=%s sta=" IPSTR " ap=" IPSTR
                 "; disconnecting mesh; correct the parent address plan and restart",
                 node_role_id(), IP2STR(&event->ip_info.ip), IP2STR(&ap_ip.ip));
        /* Never silently replace the reserved subnet with another node's lease. */
        (void)esp_mesh_lite_disconnect();
        (void)esp_wifi_deauth_sta(0);
    }
}

esp_err_t network_mesh_lite_configure_addresses(void)
{
    if (node_role_is_leaf()) { return CONFIG_APP_SOFTAP_SUBNET == 0 ? ESP_OK : ESP_ERR_INVALID_ARG; }
    if (CONFIG_APP_SOFTAP_SUBNET < 4 || CONFIG_APP_SOFTAP_SUBNET > 254) {
        ESP_LOGE(TAG, "No valid reserved AP subnet; build this device with tools/lab.py");
        return ESP_ERR_INVALID_ARG;
    }
    esp_netif_t *ap = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    if (!ap) { return ESP_ERR_INVALID_STATE; }
    esp_netif_ip_info_t planned = {
        .ip.addr = ESP_IP4TOADDR(192, 168, CONFIG_APP_SOFTAP_SUBNET, 1),
        .gw.addr = ESP_IP4TOADDR(192, 168, CONFIG_APP_SOFTAP_SUBNET, 1),
        .netmask.addr = ESP_IP4TOADDR(255, 255, 255, 0),
    };
    /* Own the address in the application. Keep DHCP and NAPT, but prevent the
     * bridge's local/ancestor allocator from replacing it. No NVS erase/write. */
    esp_err_t result = esp_bridge_netif_set_ip_info(ap, &planned, false, false);
    if (result != ESP_OK) { return result; }
    result = esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                                parent_ip_received, NULL, NULL);
    if (result != ESP_OK) { return result; }
    ESP_LOGI(TAG, "AP_ADDRESS_PLAN node=%s ap=" IPSTR "/24", node_role_id(), IP2STR(&planned.ip));
    return ESP_OK;
}
