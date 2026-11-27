#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "cJSON.h"

void cap_measure_init(void);
void cap_measure_clear(void);
bool cap_measure_new_request(const cJSON *request);
void cap_measure_begin(cJSON *cap,const char *boot,const cJSON *request,int64_t now_us,bool mci);
void cap_measure_discard(const char *cap_id);
void cap_measure_receipt(const cJSON *receipt,const char *boot,int64_t now_us);
void cap_measure_tick(const char *boot,int64_t now_us,bool (*send)(const cJSON*));
