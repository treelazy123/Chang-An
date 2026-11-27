#pragma once
#include <stdbool.h>
#include "esp_err.h"
#include "cJSON.h"
typedef bool (*task_agent_emit_t)(const cJSON *event);
esp_err_t task_agent_init(const char *boot,task_agent_emit_t emit);
void task_agent_capabilities(cJSON *capabilities, bool mci);
void task_agent_command(const cJSON *command,bool clocked);
void task_agent_tick(bool connected);
