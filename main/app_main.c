#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"
#include "network_mesh_lite.h"
#include "transport_tcp.h"
#include "mqtt_serial.h"
#include "esp_err.h"

void app_main(void)
{
    network_mesh_lite_start();
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL
    ESP_ERROR_CHECK(mqtt_serial_start());
#else
    ESP_ERROR_CHECK(transport_tcp_start());
#endif
    for (;;) {
        network_mesh_lite_log_status();
        vTaskDelay(pdMS_TO_TICKS(CONFIG_APP_STATUS_PERIOD_MS));
    }
}
