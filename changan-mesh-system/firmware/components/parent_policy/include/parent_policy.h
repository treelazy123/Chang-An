#pragma once
#include "esp_err.h"
#include "cJSON.h"
esp_err_t parent_policy_init(void);
const char *parent_policy_prepare(const cJSON *payload);
void parent_policy_status(cJSON *payload);
