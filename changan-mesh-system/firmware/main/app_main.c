#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"
#include "network_mesh_lite.h"
#include "role_app.h"
#include "esp_err.h"

void app_main(void)
{
    network_mesh_lite_start();
    ESP_ERROR_CHECK(role_app_start());
    for (;;) {
        network_mesh_lite_log_status();
        vTaskDelay(pdMS_TO_TICKS(CONFIG_APP_STATUS_PERIOD_MS));
    }
}
