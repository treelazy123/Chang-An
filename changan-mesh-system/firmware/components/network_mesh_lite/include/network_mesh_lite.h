#pragma once
#include "esp_err.h"

esp_err_t network_mesh_lite_configure_addresses(void);
void network_mesh_lite_start(void);
void network_mesh_lite_log_status(void);
