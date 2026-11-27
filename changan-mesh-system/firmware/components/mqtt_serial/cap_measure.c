#include <string.h>
#include <stdio.h>
#include "cap_measure.h"
#include "app_protocol.h"

typedef struct {
    char id[26],token[33];
    uint32_t seq;
    int64_t sent,confirmed;
    bool used,ready,timeout;
} pending_t;
static pending_t pending[8];
static uint32_t sequence;
static char requests[16][33];
static unsigned request_position;

static bool hex32(const char *text) {
    if(!text || strlen(text)!=32) { return false; }
    for(int i=0;i<32;i++) { if(!((text[i]>='0'&&text[i]<='9')||(text[i]>='a'&&text[i]<='f'))) { return false; } }
    return true;
}
void cap_measure_clear(void) { memset(pending,0,sizeof(pending)); }
void cap_measure_init(void) { cap_measure_clear();sequence=0;memset(requests,0,sizeof(requests));request_position=0; }
bool cap_measure_new_request(const cJSON *request) {
    const char *probe=app_json_string(request,"probe_id"),*batch=app_json_string(request,"batch_id");
    if(!hex32(probe)||!hex32(batch)) { return false; }
    for(int i=0;i<16;i++) { if(!strcmp(probe,requests[i])) { return false; } }
    snprintf(requests[request_position++%16],33,"%s",probe);return true;
}
void cap_measure_begin(cJSON *cap,const char *boot,const cJSON *request,int64_t now,bool mci) {
    cJSON_AddNumberToObject(cap,mci?"capMeasureV":"cap_measure_v",1);
    if(sequence==UINT32_MAX) { return; } // Never reuse an ID in this boot.
    char id[26];uint32_t seq=++sequence;
    snprintf(id,sizeof(id),"%s-%08lx",boot,(unsigned long)seq);
    cJSON_AddStringToObject(cap,mci?"capId":"cap_id",id);cJSON_AddNumberToObject(cap,mci?"capSeq":"cap_seq",seq);
    cJSON_AddNumberToObject(cap,mci?"sentUs":"sent_us",(double)now);
    if(request) {
        cJSON_AddStringToObject(cap,"probe_id",app_json_string(request,"probe_id"));
        cJSON_AddStringToObject(cap,"batch_id",app_json_string(request,"batch_id"));
    }
    for(int i=0;i<8;i++) {
        if(!pending[i].used) {
            pending_t *p=&pending[i];memset(p,0,sizeof(*p));p->used=true;p->seq=seq;p->sent=now;
            snprintf(p->id,sizeof(p->id),"%s",id);break;
        }
    }
}
void cap_measure_discard(const char *id) {
    if(!id) { return; }
    for(int i=0;i<8;i++) { if(pending[i].used&&!strcmp(pending[i].id,id)) { pending[i].used=false; } }
}
void cap_measure_receipt(const cJSON *receipt,const char *boot,int64_t now) {
    const char *id=app_json_string(receipt,"cap_id"),*received_boot=app_json_string(receipt,"boot_id");
    const char *token=app_json_string(receipt,"receipt_token");
    const cJSON *seq=cJSON_GetObjectItemCaseSensitive(receipt,"cap_seq");
    if(!id||!received_boot||strcmp(boot,received_boot)||!hex32(token)||!cJSON_IsNumber(seq)) { return; }
    for(int i=0;i<8;i++) {
        pending_t *p=&pending[i];
        if(p->used&&!p->ready&&!strcmp(id,p->id)&&seq->valuedouble==p->seq&&now>=p->sent&&now-p->sent<=2000000) {
            p->confirmed=now;p->ready=true;snprintf(p->token,sizeof(p->token),"%s",token);return;
        }
    }
}
void cap_measure_tick(const char *boot,int64_t now,bool (*send)(const cJSON*)) {
    for(int i=0;i<8;i++) {
        pending_t *p=&pending[i];if(!p->used) { continue; }
        if(!p->ready&&now-p->sent>=2000000) { p->ready=true;p->timeout=true; }
        if(!p->ready) { continue; }
        cJSON *msg=app_message_new("cap.result");if(!msg) { continue; }
        cJSON_AddStringToObject(msg,"boot_id",boot);cJSON_AddStringToObject(msg,"cap_id",p->id);
        cJSON_AddNumberToObject(msg,"cap_seq",p->seq);
        if(p->timeout) { cJSON_AddStringToObject(msg,"error","receipt_timeout"); }
        else {
            cJSON_AddStringToObject(msg,"receipt_token",p->token);
            cJSON_AddNumberToObject(msg,"confirmed_us",(double)p->confirmed);
            cJSON_AddNumberToObject(msg,"elapsed_us",(double)(p->confirmed-p->sent));
        }
        if(send(msg)) { p->used=false; }cJSON_Delete(msg);
    }
}
