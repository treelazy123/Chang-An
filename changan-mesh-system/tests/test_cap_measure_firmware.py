"""Actual capability measurement C state machine, fake JSON/MQTT and supplied monotonic time."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_service_discovery_firmware import SDK,SHIM

ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
static const char *boot="aaaaaaaaaaaaaaaa";
static char ids[32][26];static unsigned ids_count,sequence_seen,emitted;
static bool send_ok=true;
static int64_t last_elapsed,last_confirmed;
static bool last_timeout;
cJSON *app_message_new(const char *type) {
 cJSON*p=cJSON_CreateObject();cJSON_AddStringToObject(p,"type",type);return p;
}
static bool capture(const cJSON *body) {
 cJSON *e=cJSON_GetObjectItemCaseSensitive(body,"elapsed_us"),*c=cJSON_GetObjectItemCaseSensitive(body,"confirmed_us");
 last_elapsed=e?(int64_t)e->valuedouble:-1;last_confirmed=c?(int64_t)c->valuedouble:-1;
 last_timeout=app_json_string(body,"error")!=0;if(send_ok)emitted++;return send_ok;
}
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif
API void reset_probe(void) {cap_measure_init();ids_count=sequence_seen=emitted=0;send_ok=true;last_elapsed=last_confirmed=-1;last_timeout=false;}
static int begin(int64_t time,bool mci) {
 cJSON *p=cJSON_CreateObject();cap_measure_begin(p,boot,0,time,mci);
 const char *id=app_json_string(p,mci?"capId":"cap_id");if(id)strcpy(ids[ids_count++],id);
 cJSON *seq=cJSON_GetObjectItemCaseSensitive(p,mci?"capSeq":"cap_seq");
 cJSON *sent=cJSON_GetObjectItemCaseSensitive(p,mci?"sentUs":"sent_us");
 cJSON *version=cJSON_GetObjectItemCaseSensitive(p,mci?"capMeasureV":"cap_measure_v");
 sequence_seen=seq && sent && version && sent->valuedouble==time && version->valuedouble==1
     ? (unsigned)seq->valuedouble : 0;
 cJSON_Delete(p);return sequence_seen;
}
API int begin_probe(int64_t time) { return begin(time,false); }
API int begin_mci(int64_t time) { return begin(time,true); }
API void receipt_probe(unsigned index,int valid_boot,int valid_seq,int valid_token,int64_t now) {
 cJSON *p=cJSON_CreateObject();cJSON_AddStringToObject(p,"cap_id",ids[index]);
 cJSON_AddStringToObject(p,"boot_id",valid_boot?boot:"bbbbbbbbbbbbbbbb");
 cJSON_AddStringToObject(p,"receipt_token",valid_token?"0123456789abcdef0123456789abcdef":"invalid");
 cJSON_AddNumberToObject(p,"cap_seq",valid_seq?index+1:99);cap_measure_receipt(p,boot,now);cJSON_Delete(p);
}
API void tick_probe(int64_t now,int publish_ok) {send_ok=publish_ok;cap_measure_tick(boot,now,capture);}
API void clear_probe(void) {cap_measure_clear();}
API void discard_probe(unsigned index) {cap_measure_discard(ids[index]);}
API int request_probe(int valid) {
 cJSON*p=cJSON_CreateObject();cJSON_AddStringToObject(p,"probe_id","0123456789abcdef0123456789abcdef");
 cJSON_AddStringToObject(p,"batch_id",valid?"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa":"invalid");
 bool result=cap_measure_new_request(p);cJSON_Delete(p);return result;
}
API int64_t value_probe(int field) {switch(field) {case 0:return emitted;case 1:return last_elapsed;
 case 2:return last_confirmed;case 3:return last_timeout;default:return 0;}}
'''


class CapabilityFirmware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc=os.environ.get('MESH_HOST_CC') or shutil.which('cc')
        portable=ROOT/'build/host-test-tools/native-cc.cmd'
        if not cc and portable.is_file():cc=str(portable)
        if not cc:raise unittest.SkipTest('Native C compiler unavailable; set MESH_HOST_CC')
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        folder=Path(cls.temp.name)
        (folder/'fake_sdk.h').write_text(SDK+'\ncJSON *app_message_new(const char*);\n')
        for name in ('cJSON.h','app_protocol.h'):(folder/name).write_text('#include "fake_sdk.h"\n')
        production=(ROOT/'firmware/components/mqtt_serial/cap_measure.c').as_posix()
        json_shim=SHIM[SHIM.index('cJSON *cJSON_CreateObject'):SHIM.index('bool app_node_id_valid')]
        (folder/'probe.c').write_text('#include <stdlib.h>\n'+f'#include "{production}"\n'+json_shim+PROBE)
        library=folder/('probe.dll' if os.name=='nt' else 'probe.so')
        command=[cc,'-shared','-I',str(folder),'-I',str(ROOT/'firmware/components/mqtt_serial/include')]
        if os.name!='nt':command.append('-fPIC')
        result=subprocess.run(command+[str(folder/'probe.c'),'-o',str(library)],capture_output=True,text=True,timeout=90)
        if result.returncode:raise RuntimeError(result.stderr)
        cls.lib=ctypes.CDLL(str(library));cls.addClassCleanup(cls.unload)
        cls.lib.begin_probe.argtypes=[ctypes.c_int64]
        cls.lib.begin_mci.argtypes=[ctypes.c_int64]
        cls.lib.receipt_probe.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int64]
        cls.lib.tick_probe.argtypes=[ctypes.c_int64,ctypes.c_int]
        cls.lib.value_probe.restype=ctypes.c_int64

    @classmethod
    def unload(cls):
        import _ctypes
        if os.name=='nt':_ctypes.FreeLibrary(cls.lib._handle)
        else:_ctypes.dlclose(cls.lib._handle)

    def setUp(self):self.lib.reset_probe()

    def test_receipt_records_single_clock_interval_and_is_not_overwritten_by_duplicate(self):
        self.assertEqual(1,self.lib.begin_probe(1000000))
        self.lib.receipt_probe(0,1,1,1,1800000)
        self.lib.receipt_probe(0,1,1,1,1900000)
        self.lib.tick_probe(1950000,1)
        self.assertEqual(800000,self.lib.value_probe(1));self.assertEqual(1800000,self.lib.value_probe(2))
        self.lib.tick_probe(2000000,1);self.assertEqual(1,self.lib.value_probe(0))

    def test_mci_announcement_uses_same_receipt_protocol_and_sequence(self):
        self.assertEqual(1,self.lib.begin_mci(1000000))
        self.assertEqual(2,self.lib.begin_probe(1050000))
        self.lib.receipt_probe(0,1,1,1,1100000)
        self.lib.tick_probe(1150000,1)
        self.assertEqual(1,self.lib.value_probe(0))
        self.assertEqual(100000,self.lib.value_probe(1))

    def test_wrong_boot_sequence_token_and_negative_time_never_confirm(self):
        self.lib.begin_probe(1000000)
        for boot,seq,token,now in [(0,1,1,1100000),(1,0,1,1100000),(1,1,0,1100000),(1,1,1,999999)]:
            self.lib.receipt_probe(0,boot,seq,token,now)
        self.lib.tick_probe(2999999,1);self.assertEqual(0,self.lib.value_probe(0))
        self.lib.tick_probe(3000000,1)
        self.assertTrue(self.lib.value_probe(3));self.assertEqual(-1,self.lib.value_probe(1))

    def test_report_enqueue_failure_retries_without_changing_measurement(self):
        self.lib.begin_probe(1000000);self.lib.receipt_probe(0,1,1,1,1100000)
        self.lib.tick_probe(1200000,0);self.assertEqual(0,self.lib.value_probe(0))
        self.lib.tick_probe(9000000,1)
        self.assertEqual(100000,self.lib.value_probe(1));self.assertEqual(1,self.lib.value_probe(0))

    def test_disconnect_and_enqueue_failure_clear_pending_but_never_reuse_ids(self):
        self.lib.begin_probe(1000000);self.lib.discard_probe(0)
        self.lib.tick_probe(9000000,1);self.assertEqual(0,self.lib.value_probe(0))
        self.assertEqual(2,self.lib.begin_probe(10000000));self.lib.clear_probe()
        self.lib.tick_probe(19000000,1);self.assertEqual(0,self.lib.value_probe(0))
        self.assertEqual(3,self.lib.begin_probe(20000000))

    def test_bounded_pending_and_request_deduplication(self):
        self.assertFalse(self.lib.request_probe(0));self.assertTrue(self.lib.request_probe(1));self.assertFalse(self.lib.request_probe(1))
        for _ in range(9):self.lib.begin_probe(1000000)
        self.lib.tick_probe(3000000,1);self.assertEqual(8,self.lib.value_probe(0))
