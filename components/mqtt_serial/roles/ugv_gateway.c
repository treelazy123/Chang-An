#include "sdkconfig.h"
#include "mqtt_serial.h"
#include "service_discovery.h"
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL && CONFIG_APP_ROLE_UGV
esp_err_t serial_tunnel_start(void);
esp_err_t mqtt_serial_start(void) {
    esp_err_t err=service_discovery_start();
    return err==ESP_OK?serial_tunnel_start():err;
}
#endif
