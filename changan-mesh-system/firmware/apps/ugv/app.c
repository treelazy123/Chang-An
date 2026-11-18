#include "role_app.h"
#include "mqtt_serial.h"
esp_err_t role_app_start(void) { return mqtt_serial_start(); }
