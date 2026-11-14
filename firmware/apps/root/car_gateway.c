#include "sdkconfig.h"
#if CONFIG_APP_ROLE_PC_ROOT
#include <stdio.h>
#include <string.h>
#include "car_gateway.h"
#include "serial_gateway.h"
#include "app_protocol.h"
#include "node_role.h"
#include "esp_log.h"
static char requests[128],responses[128],events[128];
static int subscriptions[2],ready_mask,used;
static bool receiving;
static serial_message_t rx;
static bool task_request(const char *type) {
    const char *types[]={"task.create","task.get","task.list","task.control","task.update","task.events"};
    for(unsigned i=0;i<sizeof(types)/sizeof(types[0]);i++) { if(!strcmp(type,types[i])) { return true; } }
    return false;
}
static void error(const cJSON *request,const char *reason) {
    cJSON *reply=app_message_new("error");if(!reply) { return; }
    const char *identity=app_json_string(request,"msg_id");
    if(identity) { cJSON_AddStringToObject(reply,"msg_id",identity); }
    cJSON_AddStringToObject(reply,"error",reason);
    char *text=cJSON_PrintUnformatted(reply);
    if(text) { serial_gateway_publish(text,strlen(text));cJSON_free(text); }
    cJSON_Delete(reply);
}
void car_gateway_init(void) {
    snprintf(requests,sizeof(requests),"mesh/v1/terminals/%s/requests",node_role_id());
    snprintf(responses,sizeof(responses),"mesh/v1/terminals/%s/responses",node_role_id());
    snprintf(events,sizeof(events),"mesh/v1/terminals/%s/events",node_role_id());
}
bool car_gateway_event(esp_mqtt_client_handle_t client,int32_t id,esp_mqtt_event_handle_t event) {
    if(id==MQTT_EVENT_CONNECTED) {
        ready_mask=0;receiving=false;
        subscriptions[0]=esp_mqtt_client_subscribe_single(client,responses,1);
        subscriptions[1]=esp_mqtt_client_subscribe_single(client,events,1);
    } else if(id==MQTT_EVENT_SUBSCRIBED) {
        for(int i=0;i<2;i++) { if(event->msg_id==subscriptions[i]) { ready_mask|=1<<i; } }
    } else if(id==MQTT_EVENT_DISCONNECTED || id==MQTT_EVENT_ERROR) { ready_mask=0;receiving=false; }
    else if(id==MQTT_EVENT_DATA) {
        if(event->current_data_offset==0) {
            bool topic=(event->topic_len==(int)strlen(responses) && !memcmp(event->topic,responses,event->topic_len)) ||
                       (event->topic_len==(int)strlen(events) && !memcmp(event->topic,events,event->topic_len));
            receiving=topic && !event->retain && event->total_data_len>0 && event->total_data_len<=APP_JSON_MAX;
            used=0;
        }
        if(!receiving) { return false; }
        if(event->current_data_offset!=used || event->data_len<0 || used+event->data_len>APP_JSON_MAX) { receiving=false;return true; }
        memcpy(rx.json+used,event->data,event->data_len);used+=event->data_len;
        if(used==event->total_data_len) {
            rx.json[used]='\0';cJSON *message=app_message_parse(rx.json,used);
            if(message && !serial_gateway_publish(rx.json,used)) { ESP_LOGW("car_gateway","USB queue full; query task.events to recover"); }
            cJSON_Delete(message);receiving=false;
        }
        return true;
    }
    return false;
}
void car_gateway_poll(esp_mqtt_client_handle_t client,bool active) {
    serial_message_t packet;
    for(int i=0;i<4 && serial_gateway_receive(&packet);i++) {
        cJSON *request=app_message_parse(packet.json,packet.size);
        const char *type=app_json_string(request,"type"),*identity=app_json_string(request,"msg_id");
        if(!request || !type || !identity || !identity[0] || strlen(identity)>64 ||
           (strcmp(type,"list") && !app_command_valid(request) && !task_request(type))) {
            error(request,"invalid_request");cJSON_Delete(request);continue;
        }
        if(!active || ready_mask!=3) { error(request,"gateway_not_ready");cJSON_Delete(request);continue; }
        cJSON_DeleteItemFromObjectCaseSensitive(request,"node_id");
        cJSON_AddStringToObject(request,"node_id",node_role_id());
        char *text=cJSON_PrintUnformatted(request);
        if(!text || strlen(text)>512) { error(request,"request_too_large"); }
        else if(esp_mqtt_client_enqueue(client,requests,text,0,1,false,true)<0) { error(request,"mqtt_queue_full"); }
        cJSON_free(text);cJSON_Delete(request);
    }
}
#endif
