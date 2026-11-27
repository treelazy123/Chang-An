#pragma once
#include <stdbool.h>
#include "esp_err.h"

/* Initialize after Wi-Fi/Mesh init and before Mesh start. */
esp_err_t mesh_access_init(void);
bool mesh_access_connected(void);
/* Called by the parent-auth worker. Never interrupts a scan or association. */
bool mesh_access_retry_selection(bool proof_ready);
