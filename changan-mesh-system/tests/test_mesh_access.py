"""Run the actual scan adapter with a native C compiler and fake Wi-Fi/NVS.

No IDF compilation, radio, COM or live services. Concurrency and RF need hardware.
"""
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
#define ESP_FAIL -1
#define ESP_ERR_INVALID_STATE 0x103
#define ESP_ERR_WIFI_STATE 0x3006
#define WIFI_IF_STA 0
#define WIFI_IF_AP 1
#define WIFI_SCAN_TYPE_ACTIVE 0
#define WIFI_EVENT 1
#define ESP_EVENT_ANY_ID -1
#define WIFI_EVENT_SCAN_DONE 1
#define WIFI_EVENT_STA_CONNECTED 2
#define WIFI_EVENT_STA_DISCONNECTED 3
#define NVS_READONLY 0
#define NVS_READWRITE 1
typedef int wifi_interface_t;
typedef int esp_event_base_t;
typedef int nvs_handle_t;
typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(x) ((void)(x))
#define portEXIT_CRITICAL(x) ((void)(x))
#define ESP_LOGI(tag,...) ((void)(tag))
#define ESP_LOGW(tag,...) ((void)(tag))
typedef struct {uint32_t min,max;} active_t;
typedef struct {active_t active;uint32_t passive;} scan_time_t;
typedef struct {uint8_t *ssid,*bssid;uint8_t channel;bool show_hidden;int scan_type;
 scan_time_t scan_time;uint8_t home_chan_dwell_time;uint64_t channel_bitmap;bool coex_background_scan;} wifi_scan_config_t;
typedef struct {int unused;} wifi_config_t;
typedef struct {uint8_t channel,bssid[6];} wifi_event_sta_connected_t;
bool node_role_is_root(void);
const char *node_role_id(void);
int64_t esp_timer_get_time(void);
int esp_event_handler_register(int,int,void(*)(void*,int,int,void*),void*);
void esp_mesh_lite_connect(void);
int esp_wifi_disconnect(void);
int nvs_open(const char*,int,int*);
int nvs_get_u8(int,const char*,uint8_t*);
int nvs_get_blob(int,const char*,void*,size_t*);
int nvs_set_u8(int,const char*,uint8_t);
int nvs_set_blob(int,const char*,const void*,size_t);
int nvs_commit(int);
void nvs_close(int);
'''
SHIM=r'''
static int64_t clock_ms=1000;
static bool root;
static int real_scans,real_connects,selections,disconnects,configs,commits,fail_scan,fail_connect,deauth_calls;
static uint8_t saved_channel,saved_mac[6];
static wifi_scan_config_t captured;
bool node_role_is_root(void) {return root;}
const char *node_role_id(void) {return root?"ugv-root":"uav-001";}
int64_t esp_timer_get_time(void) {return clock_ms*1000;}
int esp_event_handler_register(int b,int id,void(*f)(void*,int,int,void*),void*a) {return 0;}
void esp_mesh_lite_connect(void) {selections++;}
int esp_wifi_disconnect(void) {disconnects++;network_event(0,WIFI_EVENT,WIFI_EVENT_STA_DISCONNECTED,0);return 0;}
int nvs_open(const char*n,int mode,int*h) {*h=1;return 0;}
int nvs_get_u8(int h,const char*k,uint8_t*v) {*v=saved_channel;return saved_channel?0:-1;}
int nvs_get_blob(int h,const char*k,void*v,size_t*n) {memcpy(v,saved_mac,6);*n=6;return 0;}
int nvs_set_u8(int h,const char*k,uint8_t v) {saved_channel=v;return 0;}
int nvs_set_blob(int h,const char*k,const void*v,size_t n) {memcpy(saved_mac,v,6);return 0;}
int nvs_commit(int h) {commits++;return 0;}
void nvs_close(int h) {}
int __real_esp_wifi_scan_start(const wifi_scan_config_t*c,bool b) {captured=*c;real_scans++;return fail_scan;}
int __real_esp_wifi_connect(void) {real_connects++;return fail_connect;}
int __real_esp_wifi_set_config(int i,wifi_config_t*c) {configs++;return 0;}
int __real_esp_wifi_deauth_sta(uint16_t aid) {deauth_calls++;return aid==99?-1:0;}
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif
API void reset_probe(int is_root,int channel) {
 enabled=associated=scanning=connecting=hint_dirty=false;scans=0;first_hint_scan=true;
 deauth_count=deauth_calls=0;last_deauth_log=0;
 root=is_root;hint_channel=6;memset(hint_bssid,0,6);saved_channel=channel;
 const uint8_t mac[6]={2,1,2,3,4,5};memcpy(saved_mac,mac,6);
 real_scans=real_connects=selections=disconnects=configs=commits=fail_scan=fail_connect=0;
 clock_ms=1000;last_selection=settle_until=scan_started=connect_started=0;mesh_access_init();
}
API void time_probe(int t) {clock_ms=t;}
API int scan_probe(int block,int fail) {
 // Poison extended fields as an old precompiled caller may do; the adapter must not propagate them.
 wifi_scan_config_t config;memset(&config,0x17,sizeof(config));
 config.ssid=0;config.bssid=0;config.channel=0;config.scan_type=0;config.show_hidden=false;
 fail_scan=fail;return __wrap_esp_wifi_scan_start(&config,block);
}
API void event_probe(int event) {
 wifi_event_sta_connected_t data={.channel=11,.bssid={2,9,8,7,6,5}};
 network_event(0,WIFI_EVENT,event,event==WIFI_EVENT_STA_CONNECTED?&data:0);
}
API int connect_probe(int fail) {fail_connect=fail;return __wrap_esp_wifi_connect();}
API int config_probe(int interface) {wifi_config_t c;return __wrap_esp_wifi_set_config(interface,&c);}
API int retry_probe(int proof) {return mesh_access_retry_selection(proof);}
API int connected_probe(void) {return mesh_access_connected();}
API int deauth_probe(int aid) {return __wrap_esp_wifi_deauth_sta(aid);}
API int value_probe(int field) {
 switch(field) {case 0:return captured.channel;case 1:return captured.scan_time.active.max;
 case 2:return captured.channel_bitmap!=0 || captured.coex_background_scan;
 case 3:return real_scans;case 4:return real_connects;case 5:return selections;
 case 6:return disconnects;case 7:return commits;case 8:return captured.bssid!=0;
 case 9:return deauth_calls;default:return 0;}
}
'''


class MeshAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc=os.environ.get('MESH_HOST_CC') or shutil.which('cc')
        portable=ROOT/'build/host-test-tools/native-cc.cmd'
        if not cc and portable.is_file():cc=str(portable)
        if not cc:raise unittest.SkipTest('Native C compiler unavailable; set MESH_HOST_CC')
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        folder=Path(cls.temp.name)
        (folder/'fake_sdk.h').write_text(SDK)
        for header in ('esp_err.h','node_role.h','esp_mesh_lite.h','esp_wifi.h','esp_event.h','esp_timer.h',
                       'esp_log.h','nvs.h','freertos/FreeRTOS.h'):
            p=folder/header;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#include "fake_sdk.h"\n')
        (folder/'sdkconfig.h').write_text('#define CONFIG_APP_MESH_CHANNEL 6\n')
        production=(ROOT/'firmware/components/mesh_access/mesh_access.c').as_posix()
        (folder/'probe.c').write_text(f'#include "{production}"\n'+SHIM)
        library=folder/('probe.dll' if os.name=='nt' else 'probe.so')
        command=[cc,'-shared','-I',str(folder),'-I',str(ROOT/'firmware/components/mesh_access/include')]
        if os.name!='nt':command.append('-fPIC')
        result=subprocess.run(command+[str(folder/'probe.c'),'-o',str(library)],capture_output=True,text=True,timeout=90)
        if result.returncode:raise RuntimeError(result.stderr)
        cls.lib=ctypes.CDLL(str(library));cls.addClassCleanup(cls.unload)

    @classmethod
    def unload(cls):
        import _ctypes
        if os.name=='nt':_ctypes.FreeLibrary(cls.lib._handle)
        else:_ctypes.dlclose(cls.lib._handle)

    def setUp(self):self.lib.reset_probe(0,0)

    def test_preferred_channel_then_full_scan_and_clean_extended_fields(self):
        for channel in (6,6,6,0,6):
            self.assertEqual(0,self.lib.scan_probe(0,0))
            self.assertEqual(channel,self.lib.value_probe(0))
            self.assertEqual(60,self.lib.value_probe(1))
            self.assertEqual(0,self.lib.value_probe(2))
            self.lib.event_probe(1)

    def test_scan_and_association_are_serialized_and_failures_release_state(self):
        self.assertEqual(0,self.lib.scan_probe(0,0))
        self.assertEqual(0x3006,self.lib.connect_probe(0))
        self.assertFalse(self.lib.retry_probe(1))
        self.lib.event_probe(1)
        self.assertEqual(0,self.lib.connect_probe(0))
        self.assertEqual(0x3006,self.lib.scan_probe(0,0))
        self.assertEqual(0x3006,self.lib.config_probe(0))
        self.assertEqual(0,self.lib.config_probe(1))  # AP configuration is independent.
        self.lib.event_probe(3)
        self.assertEqual(-1,self.lib.scan_probe(0,-1))
        self.assertEqual(-1,self.lib.connect_probe(-1))
        self.assertEqual(0,self.lib.scan_probe(0,0))

    def test_verified_retry_waits_for_scan_processing_and_never_interrupts_association(self):
        self.assertEqual(0,self.lib.scan_probe(0,0))
        self.lib.time_probe(1200);self.lib.event_probe(1)
        self.assertFalse(self.lib.retry_probe(1))
        self.lib.time_probe(1300);self.assertTrue(self.lib.retry_probe(1))
        self.assertFalse(self.lib.retry_probe(1))
        self.assertEqual(0,self.lib.connect_probe(0))
        self.lib.time_probe(1500);self.assertFalse(self.lib.retry_probe(1))
        self.lib.time_probe(11300);self.assertFalse(self.lib.retry_probe(1))
        self.assertEqual(1,self.lib.value_probe(6))  # Explicit disconnect on timeout, then fresh selection.
        self.lib.time_probe(11400);self.assertTrue(self.lib.retry_probe(1))

    def test_radio_cache_is_only_a_hint_and_is_persisted_outside_event_callback(self):
        self.lib.reset_probe(0,11)
        self.assertFalse(self.lib.connected_probe())
        self.lib.scan_probe(0,0)
        self.assertEqual(11,self.lib.value_probe(0));self.assertTrue(self.lib.value_probe(8))
        self.lib.event_probe(1);self.lib.event_probe(2)
        self.assertEqual(0,self.lib.value_probe(7))
        self.assertFalse(self.lib.retry_probe(1))
        self.assertEqual(1,self.lib.value_probe(7))

    def test_root_does_not_retry_and_blocking_scan_does_not_stick_busy(self):
        self.lib.reset_probe(1,0);self.lib.time_probe(10000)
        self.assertFalse(self.lib.retry_probe(1))
        self.assertEqual(0,self.lib.scan_probe(1,0))
        self.assertEqual(0,self.lib.scan_probe(1,0))
        self.assertEqual(2,self.lib.value_probe(3))

    def test_failed_associations_do_not_prevent_full_channel_fallback(self):
        for channel in (6,6,6,0):
            self.lib.scan_probe(0,0);self.assertEqual(channel,self.lib.value_probe(0))
            self.lib.event_probe(1);self.lib.connect_probe(0);self.lib.event_probe(3)

    def test_offline_preferred_scan_retries_are_bounded(self):
        self.lib.scan_probe(0,0);self.lib.event_probe(1)
        self.lib.time_probe(1499);self.assertFalse(self.lib.retry_probe(0))
        self.lib.time_probe(1500);self.assertTrue(self.lib.retry_probe(0))
        self.assertFalse(self.lib.retry_probe(0))

    def test_fresh_proof_gets_preferred_scan_even_after_three_pre_auth_attempts(self):
        self.lib.reset_probe(0,6)
        for _ in range(3):
            self.lib.scan_probe(0,0);self.assertEqual(6,self.lib.value_probe(0));self.lib.event_probe(1)
        self.lib.time_probe(2300)
        self.assertTrue(self.lib.retry_probe(1))
        for channel in (6,6,6,0):
            self.lib.scan_probe(0,0)
            self.assertEqual(channel,self.lib.value_probe(0))
            self.assertFalse(self.lib.value_probe(8))  # A stale BSSID must not override the verified candidate.
            self.lib.event_probe(1)

    def test_proof_waiting_during_scan_does_not_reset_budget_until_safe_retry(self):
        for _ in range(3):
            self.lib.scan_probe(0,0);self.lib.event_probe(1)
        self.lib.time_probe(2300);self.lib.scan_probe(0,0)
        self.assertEqual(0,self.lib.value_probe(0))
        self.assertFalse(self.lib.retry_probe(1))
        self.lib.event_probe(1);self.lib.time_probe(2400)
        self.assertTrue(self.lib.retry_probe(1))
        self.lib.scan_probe(0,0);self.assertEqual(6,self.lib.value_probe(0))

    def test_deauth_diagnostics_preserve_driver_calls_and_errors(self):
        self.assertEqual(0,self.lib.deauth_probe(1))
        self.assertEqual(-1,self.lib.deauth_probe(99))
        self.lib.time_probe(3000);self.assertEqual(0,self.lib.deauth_probe(0))
        self.assertEqual(3,self.lib.value_probe(9))
