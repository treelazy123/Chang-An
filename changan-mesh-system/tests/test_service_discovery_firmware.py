"""Actual discovery C worker/callbacks on a fake Mesh/RTOS, no network or IDF build."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SDK=r'''
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERR_INVALID_ARG 1
#define ESP_ERR_NO_MEM 2
#define CONFIG_APP_MQTT_PORT 8883
#define CONFIG_APP_TRANSPORT_MQTT_SERIAL 1
#define CONFIG_APP_MQTT_SERVER_NAME "ugv-broker.lab"
#define CONFIG_APP_UGV_NODE_ID "ugv-root"
typedef void *EventGroupHandle_t;
typedef void *TaskHandle_t;
typedef int esp_event_base_t;
typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(p) ((void)(p))
#define portEXIT_CRITICAL(p) ((void)(p))
#define pdTRUE 1
#define pdFALSE 0
#define pdPASS 1
#define pdMS_TO_TICKS(x) (x)
#define eSetBits 1
#define IP_EVENT 1
#define WIFI_EVENT 2
#define IP_EVENT_STA_GOT_IP 1
#define WIFI_EVENT_AP_STACONNECTED 2
#define ESP_MESH_LITE_JSON_MSG 1
#define ESP_LOGI(tag,...) ((void)(tag))
#define ESP_LOGW(tag,...) ((void)(tag))
#define AF_INET 2
#define INADDR_BROADCAST 0xffffffff
#define IPSTR "%u"
#define IP2STR(p) ((p)->addr)
struct in_addr {uint32_t s_addr;};
typedef struct {uint32_t addr;} ip_t;
typedef struct {ip_t ip;} esp_netif_ip_info_t;
typedef int esp_netif_t;
typedef struct cJSON {char key[32],text[64];int type;double valuedouble;struct cJSON *child,*next;} cJSON;
typedef struct {const char *send_msg,*expect_msg;int max_retry,retry_interval;cJSON *req_payload;esp_err_t(*resend)(const char*);} json_msg_t;
typedef struct {json_msg_t json_msg;} esp_mesh_lite_msg_config_t;
typedef struct {const char *name,*reply;cJSON*(*callback)(cJSON*,uint32_t);} esp_mesh_lite_msg_action_t;
cJSON *cJSON_CreateObject(void);
void cJSON_AddStringToObject(cJSON*,const char*,const char*);
void cJSON_AddNumberToObject(cJSON*,const char*,double);
void cJSON_Delete(cJSON*);
cJSON *cJSON_GetObjectItemCaseSensitive(const cJSON*,const char*);
bool cJSON_IsNumber(const cJSON*);
const char *app_json_string(const cJSON*,const char*);
bool app_node_id_valid(const char*);
bool node_role_is_leaf(void);
const char *node_role_id(void);
const char *esp_err_to_name(int);
int64_t esp_timer_get_time(void);
uint32_t esp_random(void);
int inet_pton(int,const char*,void*);
const char *inet_ntop(int,const void*,char*,size_t);
esp_netif_t *esp_netif_get_handle_from_ifkey(const char*);
int esp_netif_get_ip_info(esp_netif_t*,esp_netif_ip_info_t*);
int esp_mesh_lite_get_level(void);
int esp_mesh_lite_send_msg(int,const esp_mesh_lite_msg_config_t*);
int esp_mesh_lite_send_msg_to_parent(const char*);
int esp_mesh_lite_send_broadcast_msg_to_child(const char*);
int esp_mesh_lite_msg_action_list_register(const esp_mesh_lite_msg_action_t*);
int esp_event_handler_register(int,int,void(*)(void*,int,int,void*),void*);
void *xEventGroupCreate(void);
int xEventGroupSetBits(void*,unsigned);
int xEventGroupWaitBits(void*,unsigned,int,int,unsigned);
void xTaskNotify(void*,unsigned,int);
int xTaskNotifyWait(unsigned,unsigned,unsigned*,unsigned);
void vTaskDelay(unsigned);
int xTaskCreate(void(*)(void*),const char*,unsigned,void*,unsigned,void**);
'''
SHIM=r'''
static int64_t clock_ms=1000,last_query_time;
static int queries,announcements,steps;
static unsigned pending;
static jmp_buf stop_worker;
cJSON *cJSON_CreateObject(void) {return calloc(1,sizeof(cJSON));}
static cJSON *add(cJSON *p,const char*k) {cJSON*n=cJSON_CreateObject();strcpy(n->key,k);n->next=p->child;p->child=n;return n;}
void cJSON_AddStringToObject(cJSON*p,const char*k,const char*v) {cJSON*n=add(p,k);n->type=1;strcpy(n->text,v);}
void cJSON_AddNumberToObject(cJSON*p,const char*k,double v) {cJSON*n=add(p,k);n->type=2;n->valuedouble=v;}
void cJSON_Delete(cJSON*p) {if(!p)return;cJSON_Delete(p->child);cJSON_Delete(p->next);free(p);}
cJSON *cJSON_GetObjectItemCaseSensitive(const cJSON*p,const char*k) {if(p)for(cJSON*n=p->child;n;n=n->next)if(!strcmp(n->key,k))return n;return 0;}
bool cJSON_IsNumber(const cJSON*p) {return p&&p->type==2;}
const char *app_json_string(const cJSON*p,const char*k) {cJSON*n=cJSON_GetObjectItemCaseSensitive(p,k);return n&&n->type==1?n->text:0;}
bool app_node_id_valid(const char*p) {return p&&*p;}
bool node_role_is_leaf(void) {return false;}
const char *node_role_id(void) {return CONFIG_APP_ROOT_GATEWAY?"ugv-root":"ugv-001";}
const char *esp_err_to_name(int err) {return "fake";}
int64_t esp_timer_get_time(void) {return clock_ms*1000;}
uint32_t esp_random(void) {return 123;}
int inet_pton(int family,const char*text,void*out) {if(!strchr(text,'.'))return 0;*(uint32_t*)out=123;return 1;}
const char *inet_ntop(int family,const void*in,char*out,size_t size) {snprintf(out,size,"192.168.5.1");return out;}
esp_netif_t *esp_netif_get_handle_from_ifkey(const char*k) {static int netif;return &netif;}
int esp_netif_get_ip_info(esp_netif_t*n,esp_netif_ip_info_t*ip) {ip->ip.addr=123;return 0;}
int esp_mesh_lite_get_level(void) {return 1;}
int esp_mesh_lite_send_msg(int kind,const esp_mesh_lite_msg_config_t*config) {
 if(!strcmp(config->json_msg.send_msg,SERVICE_QUERY)) {queries++;last_query_time=clock_ms;}
 else announcements++;return 0;
}
int esp_mesh_lite_send_msg_to_parent(const char*p) {return 0;}
int esp_mesh_lite_send_broadcast_msg_to_child(const char*p) {return 0;}
int esp_mesh_lite_msg_action_list_register(const esp_mesh_lite_msg_action_t*a) {return 0;}
int esp_event_handler_register(int b,int id,void(*f)(void*,int,int,void*),void*a) {return 0;}
void *xEventGroupCreate(void) {return (void*)1;}
int xEventGroupSetBits(void*p,unsigned b) {return 0;}
int xEventGroupWaitBits(void*p,unsigned b,int c,int all,unsigned t) {return 0;}
void xTaskNotify(void*p,unsigned bits,int action) {pending|=bits;}
int xTaskNotifyWait(unsigned a,unsigned b,unsigned*bits,unsigned wait) {
 if(--steps<=0)longjmp(stop_worker,1);
 *bits=pending;pending=0;if(!*bits)clock_ms+=wait;return 1;
}
void vTaskDelay(unsigned t) {clock_ms+=t;}
int xTaskCreate(void(*f)(void*),const char*n,unsigned stack,void*a,unsigned prio,void**h) {*h=(void*)1;return 1;}
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif
API void reset_probe(void) {memset(&s_service,0,sizeof(s_service));clock_ms=1000;pending=0;
 queries=announcements=0;last_query_time=0;s_discovery_task=0;service_discovery_start();}
API void receive_probe(int generation) {
 cJSON*p=cJSON_CreateObject();cJSON_AddStringToObject(p,"node_id","ugv-root");
 cJSON_AddStringToObject(p,"ip","192.168.5.1");cJSON_AddStringToObject(p,"ap_ip","192.168.5.1");
 cJSON_AddStringToObject(p,"broker","ugv-broker.lab");cJSON_AddStringToObject(p,"epoch","boot");
 cJSON_AddNumberToObject(p,"generation",generation);cJSON_AddNumberToObject(p,"port",8883);
 service_received(p,0);cJSON_Delete(p);
}
API void time_probe(int time) {clock_ms=time;}
API void ip_probe(void) {network_event(0,IP_EVENT,IP_EVENT_STA_GOT_IP,0);}
API void query_probe(void) {cJSON*p=cJSON_CreateObject();cJSON_AddStringToObject(p,"root_id","ugv-root");service_requested(p,0);cJSON_Delete(p);}
API void run_probe(int count) {steps=count;if(!setjmp(stop_worker))discovery_task(0);}
API int value_probe(int key) {uint32_t ip;switch(key) {case 0:return queries;case 1:return announcements;
 case 2:return service_discovery_ugv(&ip);case 3:return (int)last_query_time;default:return 0;}}
'''


class DiscoveryFirmware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc=os.environ.get('MESH_HOST_CC') or shutil.which('cc')
        portable=ROOT/'build/host-test-tools/native-cc.cmd'
        if not cc and portable.is_file():cc=str(portable)
        if not cc:raise unittest.SkipTest('Native C compiler unavailable; set MESH_HOST_CC')
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        folder=Path(cls.temp.name);(folder/'fake_sdk.h').write_text(SDK)
        for name in ('esp_err.h','freertos/FreeRTOS.h','freertos/task.h','freertos/event_groups.h','esp_event.h',
                     'esp_wifi.h','esp_random.h','esp_log.h','esp_timer.h','esp_netif.h','esp_mesh_lite.h',
                     'lwip/sockets.h','lwip/inet.h','app_protocol.h','node_role.h'):
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#include "fake_sdk.h"\n')
        (folder/'sdkconfig.h').write_text('#include "fake_sdk.h"\n')
        source=(ROOT/'firmware/components/service_discovery/service_discovery.c').as_posix()
        (folder/'probe.c').write_text('#include <stdlib.h>\n#include <setjmp.h>\n'+f'#include "{source}"\n'+SHIM)
        cls.libraries=[]
        for root in (0,1):
            library=folder/(f'probe{root}'+('.dll' if os.name=='nt' else '.so'))
            cmd=[cc,'-shared',f'-DCONFIG_APP_ROOT_GATEWAY={root}','-I',str(folder),'-I',str(ROOT/'firmware/components/service_discovery/include')]
            if os.name!='nt':cmd.append('-fPIC')
            result=subprocess.run(cmd+[str(folder/'probe.c'),'-o',str(library)],capture_output=True,text=True,timeout=90)
            if result.returncode:raise RuntimeError(result.stderr)
            cls.libraries.append(ctypes.CDLL(str(library)))
        cls.addClassCleanup(cls.unload)

    @classmethod
    def unload(cls):
        import _ctypes
        for lib in cls.libraries:
            if os.name=='nt':_ctypes.FreeLibrary(lib._handle)
            else:_ctypes.dlclose(lib._handle)

    def setUp(self):
        self.relay,self.root=self.libraries
        for lib in self.libraries:lib.reset_probe()

    def test_got_ip_requests_service_without_waiting_for_periodic_announcement(self):
        self.relay.ip_probe();self.relay.run_probe(3)
        self.assertGreaterEqual(self.relay.value_probe(0),1)
        self.assertLessEqual(self.relay.value_probe(3),1700)

    def test_duplicate_generation_cannot_refresh_expired_service(self):
        self.relay.receive_probe(1);self.assertTrue(self.relay.value_probe(2))
        self.relay.time_probe(17000);self.relay.receive_probe(1)
        self.assertFalse(self.relay.value_probe(2))
        self.relay.query_probe();self.relay.run_probe(3)
        self.assertEqual(0,self.relay.value_probe(1))
        self.assertGreater(self.relay.value_probe(0),0)
        self.relay.receive_probe(2);self.assertTrue(self.relay.value_probe(2))

    def test_parent_replies_from_live_cache_and_root_can_announce_without_upstream(self):
        self.relay.receive_probe(1);self.relay.query_probe();self.relay.run_probe(3)
        self.assertGreater(self.relay.value_probe(1),0)
        self.assertEqual(0,self.relay.value_probe(0))
        self.root.query_probe();self.root.run_probe(3)
        self.assertGreater(self.root.value_probe(1),0)
        self.assertEqual(0,self.root.value_probe(0))
