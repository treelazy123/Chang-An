#include <string.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/usb_serial_jtag.h"
#include "esp_log.h"
#include "serial_gateway.h"

#if CONFIG_APP_ROLE_PC_ROOT
static QueueHandle_t s_to_pc;
static QueueHandle_t s_from_pc;
static const char *TAG = "serial_gateway";

static void received(const char *json, size_t size, void *ctx)
{
    (void)ctx;
    serial_message_t message = {.size = size};
    memcpy(message.json, json, size + 1);
    // Keep USB RX independent of TCP delays; never block the receiver on a full queue.
    if (xQueueSend(s_from_pc, &message, 0) != pdTRUE) {
        ESP_LOGW(TAG, "PC command queue full; command discarded (PC will time out)");
    }
}
static void rx_task(void *arg)
{
    (void)arg;
    app_frame_decoder_t decoder = {0};
    uint8_t buffer[128];
    TickType_t last_byte = xTaskGetTickCount();
    for (;;) {
        int size = usb_serial_jtag_read_bytes(buffer, sizeof(buffer), pdMS_TO_TICKS(100));
        if (size > 0) { last_byte = xTaskGetTickCount(); }
        else if (decoder.used && xTaskGetTickCount() - last_byte > pdMS_TO_TICKS(1000)) {
            decoder.used = 0;
        }
        for (int i = 0; i < size; ++i) { app_frame_feed(&decoder, buffer[i], received, NULL); }
    }
}
static void tx_task(void *arg)
{
    (void)arg;
    serial_message_t message;
    uint8_t frame[APP_FRAME_MAX];
    for (;;) {
        if (xQueueReceive(s_to_pc, &message, portMAX_DELAY) != pdTRUE) { continue; }
        size_t total = app_frame_encode(message.json, message.size, frame);
        size_t sent = 0;
        while (sent < total) {
            int size = usb_serial_jtag_write_bytes(frame + sent, total - sent, pdMS_TO_TICKS(100));
            if (size <= 0) {
                // A truncated frame is recoverable through magic/CRC resynchronization.
                ESP_LOGW(TAG, "PC serial TX timed out; unsent frame discarded");
                break;
            }
            sent += (size_t)size;
        }
    }
}
esp_err_t serial_gateway_start(void)
{
    s_to_pc = xQueueCreate(CONFIG_APP_SERIAL_QUEUE_LENGTH, sizeof(serial_message_t));
    s_from_pc = xQueueCreate(CONFIG_APP_SERIAL_QUEUE_LENGTH, sizeof(serial_message_t));
    if (!s_to_pc || !s_from_pc) { return ESP_ERR_NO_MEM; }
    usb_serial_jtag_driver_config_t config = {
        .rx_buffer_size = 4096,
        .tx_buffer_size = 4096,
    };
    esp_err_t result = usb_serial_jtag_driver_install(&config);
    if (result != ESP_OK) { return result; }
    if (xTaskCreate(rx_task, "pc_serial_rx", 6144, NULL, 4, NULL) != pdPASS ||
        xTaskCreate(tx_task, "pc_serial_tx", 4096, NULL, 4, NULL) != pdPASS) { return ESP_ERR_NO_MEM; }
    ESP_LOGI(TAG, "Native USB ready; console logs stay on UART0");
    return ESP_OK;
}
bool serial_gateway_publish(const char *json, size_t size)
{
    if (!s_to_pc || size < 2 || size > APP_JSON_MAX) { return false; }
    serial_message_t message = {.size = size};
    memcpy(message.json, json, size);
    message.json[size] = '\0';
    if (xQueueSend(s_to_pc, &message, 0) != pdTRUE) {
        ESP_LOGW(TAG, "PC output queue full; message discarded");
        return false;
    }
    return true;
}
bool serial_gateway_receive(serial_message_t *message)
{
    return s_from_pc && xQueueReceive(s_from_pc, message, 0) == pdTRUE;
}
#else
esp_err_t serial_gateway_start(void) { return ESP_ERR_NOT_SUPPORTED; }
bool serial_gateway_publish(const char *json, size_t size) { (void)json; (void)size; return false; }
bool serial_gateway_receive(serial_message_t *message) { (void)message; return false; }
#endif
