/* M1: real link/resource sampling only. No flight, survey, patrol or camera actions. */
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "task_agent.h"
#include "app_protocol.h"
#include "node_role.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "esp_mesh_lite.h"
#include "esp_wifi.h"
#include "nvs.h"

typedef struct {
    uint32_t version,revision,op_seq,duration_s,period_ms,elapsed_ms,samples,heap_min;
    int32_t rssi_min,rssi_max;
    char task_id[33],command_id[33],op[16],state[24];
} journal_t;
static journal_t journal;
static nvs_handle_t storage;
static task_agent_emit_t emit;
static char boot_id[17];
static uint32_t sequence;
static int64_t last_tick,last_sample,last_report;
static bool terminal(const char *state) {
    return !strcmp(state,"SUCCEEDED") || !strcmp(state,"FAILED") || !strcmp(state,"CANCELLED") || !strcmp(state,"REJECTED");
}
static bool persist(const journal_t *next) {
    if(nvs_set_blob(storage,"journal",next,sizeof(*next))!=ESP_OK || nvs_commit(storage)!=ESP_OK) { return false; }
    journal=*next;return true;
}
static void report(const char *response_id,const char *requested_task,int revision,const char *override_error) {
    cJSON *event=app_message_new("task.event");if(!event) { return; }
    bool found=journal.task_id[0] && (!requested_task || !strcmp(requested_task,journal.task_id));
    cJSON_AddStringToObject(event,"msg_id",response_id?response_id:journal.command_id);
    cJSON_AddStringToObject(event,"task_id",found?journal.task_id:(requested_task?requested_task:""));
    cJSON_AddNumberToObject(event,"revision",found?journal.revision:revision);
    cJSON_AddStringToObject(event,"boot_id",boot_id);cJSON_AddNumberToObject(event,"seq",++sequence);
    cJSON_AddStringToObject(event,"state",found?journal.state:"NOT_FOUND");
    uint32_t progress=found && journal.duration_s?journal.elapsed_ms/(journal.duration_s*10U):0;
    cJSON_AddNumberToObject(event,"progress",progress>100?100:progress);
    if(override_error) { cJSON_AddStringToObject(event,"error",override_error); }
    if(found) {
        cJSON *result=cJSON_AddObjectToObject(event,"result");
        cJSON_AddStringToObject(result,"source","c6");cJSON_AddNumberToObject(result,"samples",journal.samples);
        if(journal.samples) {
            cJSON_AddNumberToObject(result,"heap_min",journal.heap_min);
            if(journal.rssi_min!=INT_MAX) {
                cJSON_AddNumberToObject(result,"rssi_min",journal.rssi_min);cJSON_AddNumberToObject(result,"rssi_max",journal.rssi_max);
            }
        }
    }
    emit(event);cJSON_Delete(event);
}
static bool number(const cJSON *object,const char *name,int low,int high,int *out) {
    const cJSON *n=cJSON_GetObjectItemCaseSensitive(object,name);
    if(!cJSON_IsNumber(n) || n->valuedouble<low || n->valuedouble>high || n->valuedouble!=(double)n->valueint) { return false; }
    *out=n->valueint;return true;
}
esp_err_t task_agent_init(const char *boot,task_agent_emit_t callback) {
    emit=callback;snprintf(boot_id,sizeof(boot_id),"%s",boot);
    esp_err_t err=nvs_open("m1_task",NVS_READWRITE,&storage);if(err!=ESP_OK) { return err; }
    size_t size=sizeof(journal);err=nvs_get_blob(storage,"journal",&journal,&size);
    if(err==ESP_ERR_NVS_NOT_FOUND) { memset(&journal,0,sizeof(journal)); }
    else if(err!=ESP_OK || size!=sizeof(journal) || journal.version!=1) { return ESP_ERR_INVALID_STATE; }
    if(journal.task_id[0] && !terminal(journal.state)) {
        journal_t next=journal;snprintf(next.state,sizeof(next.state),"UNKNOWN");
        if(!persist(&next)) { return ESP_FAIL; }
    }
    last_tick=esp_timer_get_time()/1000;return ESP_OK;
}
void task_agent_capabilities(cJSON *capabilities) {
    cJSON *types=cJSON_AddArrayToObject(capabilities,"task_types");cJSON_AddItemToArray(types,cJSON_CreateString("diagnostics"));
    cJSON *ops=cJSON_AddArrayToObject(capabilities,"task_operations");
    const char *names[]={"start","pause","resume","cancel","query"};
    for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++) { cJSON_AddItemToArray(ops,cJSON_CreateString(names[i])); }
    cJSON_AddStringToObject(capabilities,"task_role",node_role_name());
}
void task_agent_command(const cJSON *command,bool clocked) {
    const char *target=app_json_string(command,"target"),*task=app_json_string(command,"task_id");
    const char *identity=app_json_string(command,"msg_id"),*op=app_json_string(command,"op"),*boot=app_json_string(command,"boot_id");
    int revision;
    const cJSON *deadline=cJSON_GetObjectItemCaseSensitive(command,"deadline_unix");
    if(!target || strcmp(target,node_role_id()) || !app_node_id_valid(task) || !app_node_id_valid(identity) ||
       !op || !boot || strcmp(boot,boot_id) || !number(command,"revision",1,INT_MAX,&revision) ||
       !clocked || !cJSON_IsNumber(deadline) || deadline->valuedouble<time(NULL) || deadline->valuedouble>time(NULL)+60) { return; }
    if(!strcmp(op,"query")) { report(identity,task,revision,NULL);return; }
    int operation_sequence;
    if(!number(command,"op_seq",1,INT_MAX,&operation_sequence)) { return; }
    if(!strcmp(task,journal.task_id) && (uint32_t)operation_sequence<=journal.op_seq) {
        bool duplicate=(uint32_t)operation_sequence==journal.op_seq && !strcmp(identity,journal.command_id) && !strcmp(op,journal.op);
        report(identity,task,revision,duplicate?NULL:"stale_operation");return;
    }
    if(!strcmp(identity,journal.command_id)) {
        if(!strcmp(task,journal.task_id) && !strcmp(op,journal.op) && (uint32_t)revision==journal.revision) { report(identity,task,revision,NULL); }
        return;
    }
    journal_t next=journal;
    if(!strcmp(op,"start")) {
        const char *kind=app_json_string(command,"kind");
        const cJSON *config=cJSON_GetObjectItemCaseSensitive(command,"config");int duration,period;
        if(!kind || strcmp(kind,"diagnostics") || !number(config,"duration_s",1,3600,&duration) || !number(config,"period_ms",200,10000,&period)) { return; }
        if(journal.task_id[0] && (!terminal(journal.state) || !strcmp(task,journal.task_id))) {
            report(identity,task,revision,"agent_busy_or_replayed_task");return;
        }
        memset(&next,0,sizeof(next));next.version=1;next.revision=revision;next.duration_s=duration;next.period_ms=period;
        next.heap_min=UINT_MAX;next.rssi_min=INT_MAX;next.rssi_max=INT_MIN;
        snprintf(next.task_id,sizeof(next.task_id),"%s",task);snprintf(next.state,sizeof(next.state),"ACCEPTED");
    } else if(!strcmp(op,"cancel") && (!journal.task_id[0] || (terminal(journal.state) && strcmp(task,journal.task_id)))) {
        /* Persist a cancellation tombstone so a delayed start cannot revive this task. */
        memset(&next,0,sizeof(next));next.version=1;next.revision=revision;next.duration_s=1;next.period_ms=1000;
        snprintf(next.task_id,sizeof(next.task_id),"%s",task);snprintf(next.state,sizeof(next.state),"CANCELLED");
    } else {
        if(strcmp(task,journal.task_id) || (uint32_t)revision!=journal.revision) { report(identity,task,revision,"task_or_revision_mismatch");return; }
        if(!strcmp(op,"pause") && !strcmp(journal.state,"RUNNING")) { snprintf(next.state,sizeof(next.state),"PAUSED"); }
        else if(!strcmp(op,"resume") && !strcmp(journal.state,"PAUSED")) { snprintf(next.state,sizeof(next.state),"RUNNING"); }
        else if(!strcmp(op,"cancel") && !terminal(journal.state)) { snprintf(next.state,sizeof(next.state),"CANCELLED"); }
        else { report(identity,task,revision,"invalid_task_transition");return; }
    }
    next.op_seq=(uint32_t)operation_sequence;
    snprintf(next.command_id,sizeof(next.command_id),"%s",identity);snprintf(next.op,sizeof(next.op),"%s",op);
    if(!persist(&next)) { report(identity,task,revision,"agent_storage_error");return; }
    report(identity,task,revision,NULL);
    if(!strcmp(next.state,"ACCEPTED")) {
        snprintf(next.state,sizeof(next.state),"RUNNING");
        if(!persist(&next)) { return; }
        report(identity,task,revision,NULL);
    }
    last_tick=esp_timer_get_time()/1000;
    if(!strcmp(op,"start")) { last_sample=last_tick-journal.period_ms; }
}
void task_agent_tick(bool connected) {
    int64_t now=esp_timer_get_time()/1000,delta=now-last_tick;last_tick=now;
    if(!journal.task_id[0]) { return; }
    if(!strcmp(journal.state,"RUNNING")) {
        if(delta>0) { journal.elapsed_ms+=(uint32_t)delta; }
        if(!connected) {
            journal_t next=journal;snprintf(next.state,sizeof(next.state),"PAUSED");
            if(!persist(&next)) { snprintf(journal.state,sizeof(journal.state),"UNKNOWN"); }
        } else {
            if(now-last_sample>=journal.period_ms) {
                journal.samples++;uint32_t heap=esp_get_free_heap_size();if(heap<journal.heap_min) { journal.heap_min=heap; }
                wifi_ap_record_t parent;
                if(esp_wifi_sta_get_ap_info(&parent)==ESP_OK) {
                    if(parent.rssi<journal.rssi_min) { journal.rssi_min=parent.rssi; }
                    if(parent.rssi>journal.rssi_max) { journal.rssi_max=parent.rssi; }
                }
                last_sample=now;
            }
            if(journal.elapsed_ms>=journal.duration_s*1000U) {
                journal_t next=journal;next.elapsed_ms=next.duration_s*1000U;snprintf(next.state,sizeof(next.state),"SUCCEEDED");
                if(!persist(&next)) { snprintf(journal.state,sizeof(journal.state),"UNKNOWN"); }
            }
        }
    }
    if(connected && now-last_report>=1000) { report(NULL,NULL,journal.revision,NULL);last_report=now; }
}
