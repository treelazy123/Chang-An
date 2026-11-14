/* micro_uav uses the discovered UGV SoftAP ingress, including through a relay. */
#include "sdkconfig.h"
#include "role_app.h"
#include "mqtt_serial.h"
#include "transport_tcp.h"

esp_err_t role_app_start(void)
{
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
    return mqtt_serial_start(MQTT_SERIAL_UGV_SOFTAP);
#else
    return transport_tcp_start();
#endif
}
