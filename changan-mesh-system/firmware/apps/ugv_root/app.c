/* Root radio carries authenticated node TLS streams to the host broker. */
#include "sdkconfig.h"
#include "role_app.h"
#include "service_discovery.h"
esp_err_t serial_tunnel_start(void);
esp_err_t role_app_start(void)
{
    esp_err_t err = service_discovery_start();
    return err == ESP_OK ? serial_tunnel_start() : err;
}
