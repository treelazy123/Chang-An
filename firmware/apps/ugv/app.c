/* UGV terminates the Wi-Fi TCP proxy and carries TLS bytes over native USB. */
#include "sdkconfig.h"
#include "role_app.h"
#include "service_discovery.h"
#include "transport_tcp.h"

#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
esp_err_t serial_tunnel_start(void);
#endif
esp_err_t role_app_start(void)
{
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
    esp_err_t err = service_discovery_start();
    return err == ESP_OK ? serial_tunnel_start() : err;
#else
    return transport_tcp_start();
#endif
}
