/* Diagnostics plus explicitly labelled ESP32 workflow tests. No flight/controller I/O. */
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

#define JOURNAL_BASE_FIELDS \
    uint32_t version,revision,op_seq,duration_s,period_ms,elapsed_ms,samples,heap_min; \
    int32_t rssi_min,rssi_max; \
    char task_id[33],command_id[33],op[16],state[24];
typedef struct { JOURNAL_BASE_FIELDS } v1_journal_t;
typedef struct {
    JOURNAL_BASE_FIELDS
    char kind[20],area_id[13],point_ids[3][13],event_id[33],test_verdict[16];
    uint32_t point_count,point_duration_s,anomaly_point;
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
    if(nvs_set_blob(storage,"journal_v2",next,sizeof(*next))!=ESP_OK || nvs_commit(storage)!=ESP_OK) { return false; }
    journal=*next;return true;
}
static bool workflow(const char *kind) { return !strcmp(kind,"patrol") || !strcmp(kind,"anomaly_review"); }
static unsigned completed_points(void) {
    if(!journal.point_duration_s) { return 0; }
    unsigned done=journal.elapsed_ms/(journal.point_duration_s*1000U);
    return done>journal.point_count?journal.point_count:done;
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
        if(workflow(journal.kind)) {
            bool done=!strcmp(journal.state,"SUCCEEDED");
            cJSON_AddStringToObject(result,"mode","esp32_test");
            if(!strcmp(journal.kind,"patrol")) {
                unsigned count=completed_points();
                cJSON_AddStringToObject(result,"stage",done?"test_done":"point_check");
                cJSON_AddStringToObject(result,"point",journal.point_ids[count<journal.point_count?count:journal.point_count-1]);
                cJSON_AddNumberToObject(result,"done",count);cJSON_AddNumberToObject(result,"total",journal.point_count);
                /* One test incident per patrol; its ID is the globally unique task ID. */
                if(journal.anomaly_point && count>=journal.anomaly_point) { cJSON_AddStringToObject(result,"event_id",journal.task_id); }
            } else {
                unsigned stage=journal.elapsed_ms*3U/(journal.duration_s*1000U);
                cJSON_AddStringToObject(result,"stage",done?"test_done":(stage==0?"receive_event":(stage==1?"validate_input":"test_result")));
                cJSON_AddStringToObject(result,"event_id",journal.event_id);
                cJSON_AddStringToObject(result,"verdict",done?journal.test_verdict:"pending");
            }
        } else {
            cJSON_AddStringToObject(result,"source","c6");cJSON_AddNumberToObject(result,"samples",journal.samples);
            if(journal.samples) {
                cJSON_AddNumberToObject(result,"heap_min",journal.heap_min);
                if(journal.rssi_min!=INT_MAX) {
                    cJSON_AddNumberToObject(result,"rssi_min",journal.rssi_min);cJSON_AddNumberToObject(result,"rssi_max",journal.rssi_max);
                }
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
static bool short_id(const char *value) { return value && strlen(value)<=12 && app_node_id_valid(value); }
static bool fields_valid(const cJSON *config,const char *const *fields,unsigned count) {
    if(!cJSON_IsObject(config)) { return false; }
    const cJSON *item=NULL;
    cJSON_ArrayForEach(item,config) {
        bool found=false;
        for(unsigned i=0;i<count;i++) { if(item->string && !strcmp(item->string,fields[i])) { found=true;break; } }
        if(!found) { return false; }
    }
    return true;
}
static bool workflow_config(journal_t *next,const char *kind,const cJSON *config) {
    const char *mode=app_json_string(config,"execution_mode");
    if(!mode || strcmp(mode,"esp32_test")) { return false; }
    if(!strcmp(kind,"patrol")) {
        const char *const fields[]={"execution_mode","area_id","point_ids","point_duration_s","anomaly_point"};
        if(strcmp(node_role_name(),"micro_uav") || !fields_valid(config,fields,5)) { return false; }
        const char *area=app_json_string(config,"area_id");
        const cJSON *points=cJSON_GetObjectItemCaseSensitive(config,"point_ids");int seconds,index;
        if(!short_id(area) || !cJSON_IsArray(points) || cJSON_GetArraySize(points)<1 || cJSON_GetArraySize(points)>3 ||
           !number(config,"point_duration_s",1,60,&seconds) || !number(config,"anomaly_point",0,cJSON_GetArraySize(points),&index)) { return false; }
        next->point_count=(uint32_t)cJSON_GetArraySize(points);next->point_duration_s=(uint32_t)seconds;next->anomaly_point=(uint32_t)index;
        snprintf(next->area_id,sizeof(next->area_id),"%s",area);
        for(unsigned i=0;i<next->point_count;i++) {
            const char *point=cJSON_GetStringValue(cJSON_GetArrayItem(points,(int)i));
            if(!short_id(point)) { return false; }
            for(unsigned j=0;j<i;j++) { if(!strcmp(point,next->point_ids[j])) { return false; } }
            snprintf(next->point_ids[i],sizeof(next->point_ids[i]),"%s",point);
        }
        next->duration_s=next->point_count*next->point_duration_s;
    } else if(!strcmp(kind,"anomaly_review")) {
        const char *const fields[]={"execution_mode","event_id","test_verdict","duration_s"};
        if(strcmp(node_role_name(),"uav") || !fields_valid(config,fields,4)) { return false; }
        const char *event=app_json_string(config,"event_id"),*verdict=app_json_string(config,"test_verdict");int seconds;
        if(!app_node_id_valid(event) || !verdict || (strcmp(verdict,"confirmed") && strcmp(verdict,"cleared") && strcmp(verdict,"inconclusive")) ||
           !number(config,"duration_s",1,60,&seconds)) { return false; }
        snprintf(next->event_id,sizeof(next->event_id),"%s",event);snprintf(next->test_verdict,sizeof(next->test_verdict),"%s",verdict);
        next->duration_s=(uint32_t)seconds;
    } else { return false; }
    next->period_ms=1000;return true;
}
static void reject_start(const char *identity,const char *task,int revision,const char *reason) {
    cJSON *event=app_message_new("task.event");if(!event) { return; }
    cJSON_AddStringToObject(event,"msg_id",identity);cJSON_AddStringToObject(event,"task_id",task);
    cJSON_AddStringToObject(event,"boot_id",boot_id);cJSON_AddNumberToObject(event,"revision",revision);
    cJSON_AddNumberToObject(event,"seq",++sequence);cJSON_AddStringToObject(event,"state","REJECTED");
    cJSON_AddNumberToObject(event,"progress",0);cJSON_AddStringToObject(event,"error",reason);emit(event);cJSON_Delete(event);
}
esp_err_t task_agent_init(const char *boot,task_agent_emit_t callback) {
    emit=callback;snprintf(boot_id,sizeof(boot_id),"%s",boot);
    esp_err_t err=nvs_open("m1_task",NVS_READWRITE,&storage);if(err!=ESP_OK) { return err; }
    memset(&journal,0,sizeof(journal));
    size_t size=0;bool from_v1=false;err=nvs_get_blob(storage,"journal_v2",NULL,&size);
    if(err==ESP_ERR_NVS_NOT_FOUND) { from_v1=true;err=nvs_get_blob(storage,"journal",NULL,&size); }
    if(err==ESP_ERR_NVS_NOT_FOUND) { snprintf(journal.kind,sizeof(journal.kind),"diagnostics"); }
    else if(err==ESP_OK && from_v1 && size==sizeof(v1_journal_t)) {
        v1_journal_t old;err=nvs_get_blob(storage,"journal",&old,&size);
        if(err!=ESP_OK || old.version!=1) { return ESP_ERR_INVALID_STATE; }
        memcpy(&journal,&old,sizeof(old));journal.version=2;
        snprintf(journal.kind,sizeof(journal.kind),"diagnostics");
        if(!persist(&journal)) { return ESP_FAIL; }
    } else if(err==ESP_OK && !from_v1 && size==sizeof(journal)) {
        err=nvs_get_blob(storage,"journal_v2",&journal,&size);
        if(err!=ESP_OK || journal.version!=2 || !memchr(journal.kind,'\0',sizeof(journal.kind))) { return ESP_ERR_INVALID_STATE; }
    } else { return ESP_ERR_INVALID_STATE; }
    if(journal.task_id[0]) {
        if(!memchr(journal.task_id,'\0',sizeof(journal.task_id)) || !memchr(journal.command_id,'\0',sizeof(journal.command_id)) ||
           !memchr(journal.op,'\0',sizeof(journal.op)) || !memchr(journal.state,'\0',sizeof(journal.state)) ||
           !app_node_id_valid(journal.task_id)) { return ESP_ERR_INVALID_STATE; }
        if(!strcmp(journal.kind,"patrol")) {
            if(journal.point_count<1 || journal.point_count>3 || journal.point_duration_s<1 || journal.point_duration_s>60 ||
               journal.anomaly_point>journal.point_count || journal.duration_s!=journal.point_count*journal.point_duration_s) { return ESP_ERR_INVALID_STATE; }
            for(unsigned i=0;i<journal.point_count;i++) {
                if(!memchr(journal.point_ids[i],'\0',sizeof(journal.point_ids[i])) || !short_id(journal.point_ids[i])) { return ESP_ERR_INVALID_STATE; }
            }
        } else if(!strcmp(journal.kind,"anomaly_review")) {
            if(journal.duration_s<1 || journal.duration_s>60 || !memchr(journal.event_id,'\0',sizeof(journal.event_id)) ||
               !memchr(journal.test_verdict,'\0',sizeof(journal.test_verdict)) || !app_node_id_valid(journal.event_id)) { return ESP_ERR_INVALID_STATE; }
        } else if(strcmp(journal.kind,"diagnostics")) { return ESP_ERR_INVALID_STATE; }
    }
    if(journal.task_id[0] && !terminal(journal.state)) {
        journal_t next=journal;snprintf(next.state,sizeof(next.state),"UNKNOWN");
        if(!persist(&next)) { return ESP_FAIL; }
    }
    last_tick=esp_timer_get_time()/1000;return ESP_OK;
}
void task_agent_capabilities(cJSON *capabilities) {
    cJSON *types=cJSON_AddArrayToObject(capabilities,"task_types");cJSON_AddItemToArray(types,cJSON_CreateString("diagnostics"));
    if(!strcmp(node_role_name(),"micro_uav")) { cJSON_AddItemToArray(types,cJSON_CreateString("patrol")); }
    if(!strcmp(node_role_name(),"uav")) { cJSON_AddItemToArray(types,cJSON_CreateString("anomaly_review")); }
    if(!strcmp(node_role_name(),"micro_uav") || !strcmp(node_role_name(),"uav")) { cJSON_AddStringToObject(capabilities,"execution_mode","esp32_test"); }
    cJSON *ops=cJSON_AddArrayToObject(capabilities,"task_operations");
    const char *names[]={"start","pause","resume","cancel","query"};
    for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++) { cJSON_AddItemToArray(ops,cJSON_CreateString(names[i])); }
    cJSON_AddStringToObject(capabilities,"task_role",node_role_name());
    bool busy=journal.task_id[0] && !terminal(journal.state);
    cJSON_AddStringToObject(capabilities,"task_status",busy?journal.state:"IDLE");
    if(busy) { cJSON_AddStringToObject(capabilities,"task_id",journal.task_id); }
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
        journal_t prepared={0};
        if(!kind) { reject_start(identity,task,revision,"unsupported_task_kind");return; }
        if(!strcmp(kind,"diagnostics")) {
            if(!number(config,"duration_s",1,3600,&duration) || !number(config,"period_ms",200,10000,&period)) { reject_start(identity,task,revision,"invalid_config");return; }
            prepared.duration_s=(uint32_t)duration;prepared.period_ms=(uint32_t)period;
        } else if(!workflow_config(&prepared,kind,config)) { reject_start(identity,task,revision,"invalid_test_config_or_role");return; }
        if(journal.task_id[0] && (!terminal(journal.state) || !strcmp(task,journal.task_id))) {
            report(identity,task,revision,"agent_busy_or_replayed_task");return;
        }
        next=prepared;next.version=2;next.revision=(uint32_t)revision;
        snprintf(next.kind,sizeof(next.kind),"%s",kind);
        next.heap_min=UINT_MAX;next.rssi_min=INT_MAX;next.rssi_max=INT_MIN;
        snprintf(next.task_id,sizeof(next.task_id),"%s",task);snprintf(next.state,sizeof(next.state),"ACCEPTED");
    } else if(!strcmp(op,"cancel") && (!journal.task_id[0] || (terminal(journal.state) && strcmp(task,journal.task_id)))) {
        /* Persist a cancellation tombstone so a delayed start cannot revive this task. */
        memset(&next,0,sizeof(next));next.version=2;next.revision=revision;next.duration_s=1;next.period_ms=1000;
        snprintf(next.kind,sizeof(next.kind),"diagnostics");
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
        unsigned previous_done=completed_points();
        unsigned previous_stage=journal.duration_s?journal.elapsed_ms*3U/(journal.duration_s*1000U):0;
        if(delta>0) { journal.elapsed_ms+=(uint32_t)delta; }
        if(!connected) {
            journal_t next=journal;snprintf(next.state,sizeof(next.state),"PAUSED");
            if(!persist(&next)) { snprintf(journal.state,sizeof(journal.state),"UNKNOWN"); }
        } else {
            if(!workflow(journal.kind) && now-last_sample>=journal.period_ms) {
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
                report(NULL,NULL,journal.revision,NULL);last_report=now;
            } else if(!strcmp(journal.kind,"patrol") && completed_points()!=previous_done) {
                journal_t next=journal;
                if(!persist(&next)) { snprintf(journal.state,sizeof(journal.state),"UNKNOWN"); }
                report(NULL,NULL,journal.revision,NULL);last_report=now;
            } else if(!strcmp(journal.kind,"anomaly_review") && journal.elapsed_ms*3U/(journal.duration_s*1000U)!=previous_stage) {
                journal_t next=journal;
                if(!persist(&next)) { snprintf(journal.state,sizeof(journal.state),"UNKNOWN"); }
                report(NULL,NULL,journal.revision,NULL);last_report=now;
            }
        }
    }
    if(connected && now-last_report>=1000) { report(NULL,NULL,journal.revision,NULL);last_report=now; }
}
