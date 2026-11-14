/* Car USB endpoint and the UGV STA ingress belong to the root application. */
#include "sdkconfig.h"
#include "role_app.h"
#include "mqtt_serial.h"
#include "serial_gateway.h"
#include "transport_tcp.h"

esp_err_t role_app_start(void)
{
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
    esp_err_t err = serial_gateway_start();
    return err == ESP_OK ? mqtt_serial_start(MQTT_SERIAL_UGV_STA) : err;
#else
    return transport_tcp_start();
#endif
}
