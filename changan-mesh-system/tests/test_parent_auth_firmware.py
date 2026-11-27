"""Execute production parent_auth.c on the host with a fake radio/RTOS.

PSA adapters call real P-256/SHA-256 in Python. This tests firmware decisions and
wire interoperability, not ESP-IDF compilation, radio behavior or concurrency.
MESH_HOST_CC must be a native compiler; the ESP cross compiler is never invoked.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from changan_ugv.nodes.parent_authority import REQUEST, field, sign, public_bytes, verify

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
#define ESP_ERR_INVALID_SIZE 0x104
#define ESP_ERR_INVALID_ARG 0x102
#define ESP_ERR_NO_MEM 0x101
#define ESP_ERROR_CHECK(x) do { if((x)!=0) abort(); } while(0)
typedef void *QueueHandle_t;
typedef void *SemaphoreHandle_t;
typedef int wifi_interface_t;
#define WIFI_IF_STA 0
#define WIFI_IF_AP 1
typedef struct {uint8_t bssid[6];} wifi_ap_record_t;
typedef struct {int num;struct {uint8_t mac[6];} sta[8];} wifi_sta_list_t;
typedef struct {uint8_t peer_addr[6];int ifidx;uint8_t channel;bool encrypt;} esp_now_peer_info_t;
typedef struct {uint8_t *src_addr,*des_addr;} esp_now_recv_info_t;
#define ESPNOW_DATA_TYPE_RESERVE 200
typedef struct cJSON {int unused;} cJSON;
typedef unsigned psa_key_id_t;
typedef int psa_key_attributes_t;
#define PSA_KEY_ATTRIBUTES_INIT 0
#define PSA_KEY_TYPE_ECC_PUBLIC_KEY(x) 1
#define PSA_KEY_TYPE_ECC_KEY_PAIR(x) 2
#define PSA_ECC_FAMILY_SECP_R1 1
#define PSA_KEY_USAGE_VERIFY_HASH 1
#define PSA_KEY_USAGE_SIGN_HASH 2
#define PSA_ALG_SHA_256 1
#define PSA_ALG_ECDSA(x) 2
#define PSA_SUCCESS 0
#define portMAX_DELAY 0xffffffff
#define pdTRUE 1
#define pdPASS 1
#define pdMS_TO_TICKS(x) (x)
#define ESP_LOGI(tag,...) ((void)(tag))
#define ESP_LOGW(tag,...) ((void)(tag))
QueueHandle_t xQueueCreate(unsigned count,unsigned size);
int xQueueSend(QueueHandle_t,const void*,unsigned);
int xQueueReceive(QueueHandle_t,void*,unsigned);
void xQueueReset(QueueHandle_t);
SemaphoreHandle_t xSemaphoreCreateMutex(void);
int xSemaphoreTake(SemaphoreHandle_t,unsigned);
void xSemaphoreGive(SemaphoreHandle_t);
void vTaskDelay(unsigned);
int xTaskCreate(void(*)(void*),const char*,unsigned,void*,unsigned,void*);
bool node_role_is_root(void);
bool node_role_is_leaf(void);
const char *node_role_id(void);
uint8_t node_role_fixed_level(void);
int64_t esp_timer_get_time(void);
void esp_fill_random(void*,size_t);
int esp_wifi_get_mac(int,uint8_t*);
int esp_wifi_sta_get_ap_info(wifi_ap_record_t*);
int esp_wifi_ap_get_sta_list(wifi_sta_list_t*);
bool mesh_access_connected(void);
bool mesh_access_retry_selection(bool);
int esp_now_get_peer(const uint8_t*,esp_now_peer_info_t*);
int esp_now_add_peer(const esp_now_peer_info_t*);
int esp_now_send(const uint8_t*,const uint8_t*,size_t);
int esp_mesh_lite_disconnect(void);
void esp_mesh_lite_connect(void);
int esp_mesh_lite_espnow_recv_cb_register(int,int(*)(const esp_now_recv_info_t*,const uint8_t*,int));
int psa_crypto_init(void);
void psa_set_key_type(psa_key_attributes_t*,int);
void psa_set_key_bits(psa_key_attributes_t*,int);
void psa_set_key_usage_flags(psa_key_attributes_t*,int);
void psa_set_key_algorithm(psa_key_attributes_t*,int);
void psa_reset_key_attributes(psa_key_attributes_t*);
int psa_hash_compute(int,const void*,size_t,uint8_t*,size_t,size_t*);
int psa_import_key(const psa_key_attributes_t*,const uint8_t*,size_t,psa_key_id_t*);
int psa_verify_hash(psa_key_id_t,int,const uint8_t*,size_t,const uint8_t*,size_t);
int psa_sign_hash(psa_key_id_t,int,const uint8_t*,size_t,uint8_t*,size_t,size_t*);
int psa_export_public_key(psa_key_id_t,uint8_t*,size_t,size_t*);
void psa_destroy_key(psa_key_id_t);
cJSON *cJSON_AddObjectToObject(cJSON*,const char*);
void cJSON_AddStringToObject(cJSON*,const char*,const char*);
void cJSON_AddBoolToObject(cJSON*,const char*,bool);
void cJSON_AddNumberToObject(cJSON*,const char*,double);
'''

SHIM=r'''
static int level=4;
static int64_t clock_ms=1000;
static int connected,selection_count;
static int64_t last_selection;
static unsigned key_counter;
typedef int(*crypto_fn)(int,unsigned,const uint8_t*,size_t,uint8_t*,size_t,size_t*);
static crypto_fn crypto;
typedef struct {unsigned size,count,read,used;uint8_t *data;} fake_queue;
static fake_queue *queues[4];static int nqueues;
QueueHandle_t xQueueCreate(unsigned count,unsigned size) {
 fake_queue *q=calloc(1,sizeof(*q));q->size=size;q->count=count;q->data=calloc(count,size);queues[nqueues++]=q;return q;
}
int xQueueSend(QueueHandle_t handle,const void *item,unsigned wait) {
 fake_queue *q=handle;if(q->used==q->count)return 0;
 memcpy(q->data+((q->read+q->used)%q->count)*q->size,item,q->size);q->used++;return 1;
}
int xQueueReceive(QueueHandle_t handle,void *item,unsigned wait) {
 fake_queue *q=handle;if(!q->used)return 0;memcpy(item,q->data+q->read*q->size,q->size);
 q->read=(q->read+1)%q->count;q->used--;return 1;
}
void xQueueReset(QueueHandle_t handle) {fake_queue *q=handle;q->read=q->used=0;}
SemaphoreHandle_t xSemaphoreCreateMutex(void) {return (void*)1;}
int xSemaphoreTake(SemaphoreHandle_t h,unsigned t) {return 1;}
void xSemaphoreGive(SemaphoreHandle_t h) {}
void vTaskDelay(unsigned t) {clock_ms+=t;}
int xTaskCreate(void(*fn)(void*),const char*n,unsigned s,void*a,unsigned p,void*h) {return 1;}
bool node_role_is_root(void) {return level==1;}
bool node_role_is_leaf(void) {return level==4;}
const char *node_role_id(void) {return level==1?"ugv-root":level==2?"ugv-001":level==3?"uav-001":"micro-001";}
uint8_t node_role_fixed_level(void) {return level;}
int64_t esp_timer_get_time(void) {return clock_ms*1000;}
void esp_fill_random(void *out,size_t n) {static uint8_t counter=1;uint8_t*p=out;while(n--)*p++=counter++;}
int esp_wifi_get_mac(int interface,uint8_t *out) {
 const uint8_t sta[6]={2,0x66,0x77,0x88,0x99,0xaa},ap[6]={2,0,0x11,0x22,0x33,0x44};
 memcpy(out,interface==WIFI_IF_STA?sta:ap,6);return 0;
}
int esp_wifi_sta_get_ap_info(wifi_ap_record_t *ap) {return connected?0:-1;}
int esp_wifi_ap_get_sta_list(wifi_sta_list_t *list) {list->num=0;return 0;}
bool mesh_access_connected(void) {return connected;}
bool mesh_access_retry_selection(bool proof) {
 if(connected) {last_selection=clock_ms;return false;}
 if(level==1 || clock_ms-last_selection<(proof?500:2000))return false;
 last_selection=clock_ms;selection_count++;return true;
}
int esp_now_get_peer(const uint8_t*m,esp_now_peer_info_t*p) {return -1;}
int esp_now_add_peer(const esp_now_peer_info_t*p) {return 0;}
int esp_now_send(const uint8_t*m,const uint8_t*d,size_t s) {return 0;}
int esp_mesh_lite_disconnect(void) {return 0;}
void esp_mesh_lite_connect(void) {selection_count++;}
int esp_mesh_lite_espnow_recv_cb_register(int t,int(*f)(const esp_now_recv_info_t*,const uint8_t*,int)) {return 0;}
int psa_crypto_init(void) {return 0;}
void psa_set_key_type(psa_key_attributes_t*a,int v) {}
void psa_set_key_bits(psa_key_attributes_t*a,int v) {}
void psa_set_key_usage_flags(psa_key_attributes_t*a,int v) {}
void psa_set_key_algorithm(psa_key_attributes_t*a,int v) {}
void psa_reset_key_attributes(psa_key_attributes_t*a) {}
int psa_hash_compute(int alg,const void*d,size_t n,uint8_t*out,size_t cap,size_t*size) {return crypto(1,0,d,n,out,cap,size);}
int psa_import_key(const psa_key_attributes_t*a,const uint8_t*d,size_t n,psa_key_id_t*id) {
 *id=++key_counter;size_t z=0;return crypto(2,*id,d,n,0,0,&z);
}
int psa_verify_hash(psa_key_id_t id,int alg,const uint8_t*h,size_t hn,const uint8_t*s,size_t sn) {
 uint8_t data[96];if(hn!=32||sn!=64)return -1;memcpy(data,h,32);memcpy(data+32,s,64);size_t z=0;
 return crypto(3,id,data,96,0,0,&z);
}
int psa_sign_hash(psa_key_id_t id,int alg,const uint8_t*h,size_t n,uint8_t*out,size_t cap,size_t*size) {return crypto(4,id,h,n,out,cap,size);}
int psa_export_public_key(psa_key_id_t id,uint8_t*out,size_t cap,size_t*size) {return crypto(5,id,0,0,out,cap,size);}
void psa_destroy_key(psa_key_id_t id) {size_t z=0;crypto(6,id,0,0,0,0,&z);}
cJSON *cJSON_AddObjectToObject(cJSON*p,const char*k) {return p;}
void cJSON_AddStringToObject(cJSON*p,const char*k,const char*v) {}
void cJSON_AddBoolToObject(cJSON*p,const char*k,bool v) {}
void cJSON_AddNumberToObject(cJSON*p,const char*k,double v) {}
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif
API int reset_probe(crypto_fn fn,int desired_level) {
 for(int i=0;i<nqueues;i++){free(queues[i]->data);free(queues[i]);}nqueues=0;
 inbox=requests=0;lock=0;memset(candidates,0,sizeof(candidates));memset(forwards,0,sizeof(forwards));
 memset(local_node,0,32);memset(local_root,0,32);memset(own_nonce,0,16);
 own_asked=own_sent=own_until=0;online=false;radio_count=0;radio_window=0;
 connected=selection_count=0;selection_ready=false;last_selection=0;
 crypto=fn;level=desired_level;clock_ms=1000;return parent_auth_init();
}
API void time_probe(int64_t t) {clock_ms=t;}
API void challenge_probe(const uint8_t *mac,const uint8_t *nonce) {
 const uint8_t required[32]={0};discover(mac,required);for(int i=0;i<SLOTS;i++)if(!memcmp(candidates[i].mac,mac,6)){
 candidates[i].asked=clock_ms;memcpy(candidates[i].nonce,nonce,16);candidates[i].parts=0;}
}
API int allowed_probe(const uint8_t*mac) {return parent_auth_candidate(mac,NULL);}
API int expected_probe(const uint8_t*mac,const char*node) {return parent_auth_candidate(mac,node);}
API void radio_probe(const uint8_t*src,const uint8_t*dst,const uint8_t*data,unsigned n) {
 event_t e={.kind=RADIO};if(n>sizeof(e.data))return;e.size=n;
 memcpy(e.src,src,6);memcpy(e.dst,dst,6);memcpy(e.data,data,n);handle_radio(&e);
}
API void disconnect_probe(void) {parent_auth_disconnected();}
API void process_discover_probe(void) {
 event_t event;while(xQueueReceive(inbox,&event,0))if(event.kind==DISCOVER)discover(event.src,event.required);
}
API int recover_probe(int associated) {connected=associated;recover_selection(clock_ms);return selection_count;}
API void online_probe(int v) {parent_auth_online(v);}
API int own_probe(uint8_t *out) {
 parent_auth_online(true);esp_fill_random(own_nonce,16);own_asked=clock_ms;
 return request_grant(0,own_nonce,local_sta)&&parent_auth_take_request((pa_request_t*)out);
}
API void grant_probe(const uint8_t*data) {pa_grant_t grant;memcpy(&grant,data,sizeof(grant));handle_grant(&grant);}
API int relay_probe(void) {return online && own_until>clock_ms;}
'''


class FirmwareParentAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc=os.environ.get('MESH_HOST_CC') or shutil.which('cc')
        portable=ROOT/'build/host-test-tools/native-cc.cmd'
        if not cc and portable.is_file():cc=str(portable)
        if not cc:raise unittest.SkipTest('Set MESH_HOST_CC to run native firmware-decision tests')
        cls.authority=ec.generate_private_key(ec.SECP256R1())
        cls.parent=ec.generate_private_key(ec.SECP256R1())
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        directory=Path(cls.temp.name)
        (directory/'fake_sdk.h').write_text(SDK)
        headers=('esp_err.h','cJSON.h','node_role.h','mesh_access.h','freertos/FreeRTOS.h','freertos/task.h',
                 'freertos/queue.h','freertos/semphr.h','esp_mesh_lite.h','esp_wifi.h',
                 'esp_random.h','esp_timer.h','esp_log.h','psa/crypto.h')
        for name in headers:
            p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#include "fake_sdk.h"\n')
        (directory/'sdkconfig.h').write_text('#define CONFIG_APP_UGV_NODE_ID "ugv-root"\n')
        public=','.join(str(b) for b in public_bytes(cls.authority.public_key()))
        production=(ROOT/'firmware/components/parent_auth/parent_auth.c').as_posix()
        source=('#include <stdlib.h>\n#include <string.h>\n#include "fake_sdk.h"\n'
                'const uint8_t private_fixture[32] __asm__("_binary_auth_key_start")={1};\n'
                f'const uint8_t public_fixture[65] __asm__("_binary_authority_pub_start")={{{public}}};\n'
                f'#include "{production}"\n'+SHIM)
        (directory/'probe.c').write_text(source)
        library=directory/('probe.dll' if os.name=='nt' else 'probe.so')
        command=[cc,'-shared','-I',str(directory),'-I',str(ROOT/'firmware/components/parent_auth/include')]
        if os.name!='nt':command.append('-fPIC')
        result=subprocess.run(command+[str(directory/'probe.c'),'-o',str(library)],capture_output=True,text=True,timeout=90)
        if result.returncode:raise RuntimeError('Native probe compile failed: '+result.stderr)
        cls.lib=ctypes.CDLL(str(library));cls.addClassCleanup(cls.unload)
        cls.callback_type=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,
            ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t))
        cls.lib.reset_probe.argtypes=[cls.callback_type,ctypes.c_int]
        cls.lib.time_probe.argtypes=[ctypes.c_int64]
        cls.lib.radio_probe.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint]
        cls.lib.challenge_probe.argtypes=[ctypes.c_char_p,ctypes.c_char_p]
        cls.lib.allowed_probe.argtypes=[ctypes.c_char_p]
        cls.lib.expected_probe.argtypes=[ctypes.c_char_p,ctypes.c_char_p]
        cls.lib.grant_probe.argtypes=[ctypes.c_char_p]

    @classmethod
    def unload(cls):
        if os.name=='nt':
            import _ctypes
            _ctypes.FreeLibrary(cls.lib._handle)

    def setUp(self):
        self.keys={};self.crypto_errors=[]
        def crypto(op,key,data,size,out,cap,out_size):
            try:
                raw=ctypes.string_at(data,size) if size else b'';answer=b''
                if op==1:answer=hashlib.sha256(raw).digest()
                elif op==2:
                    self.keys[key]=(ec.derive_private_key(int.from_bytes(raw,'big'),ec.SECP256R1()) if size==32
                                    else ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),raw))
                elif op==3:
                    public=self.keys[key]
                    if hasattr(public,'public_key'):public=public.public_key()
                    signature=utils.encode_dss_signature(int.from_bytes(raw[32:64],'big'),int.from_bytes(raw[64:],'big'))
                    public.verify(signature,raw[:32],ec.ECDSA(utils.Prehashed(hashes.SHA256())))
                elif op==4:
                    r,s=utils.decode_dss_signature(self.keys[key].sign(raw,ec.ECDSA(utils.Prehashed(hashes.SHA256()))))
                    answer=r.to_bytes(32,'big')+s.to_bytes(32,'big')
                elif op==5:answer=public_bytes(self.keys[key].public_key())
                elif op==6:self.keys.pop(key,None)
                if len(answer)>cap:return -1
                if answer:ctypes.memmove(out,answer,len(answer))
                out_size[0]=len(answer)
                return 0
            except Exception:
                return -1
        self.callback=self.callback_type(crypto)
        self.assertEqual(0,self.lib.reset_probe(self.callback,4))
        self.ap=bytes.fromhex('021122334455');self.child=bytes.fromhex('0266778899aa');self.nonce=b'Q'*16
        self.lib.challenge_probe(self.ap,self.nonce)

    def grant(self,nonce=None,child=None,ap=None,level=3,key=None):
        key=key or self.parent
        body=REQUEST.pack(b'PAR1',1,field('uav-001'),field('ugv-root'),b'B'*16,
                          ap or self.ap,nonce or self.nonce,child or self.child)
        unsigned=body+sign(key,body)+public_bytes(key.public_key())+bytes([level,20])+b'\0'*4
        return unsigned+sign(self.authority,unsigned)

    def deliver(self,grant,order=(0,1)):
        for part in order:
            packet=b'PAF1'+self.nonce+bytes([part])+grant[part*156:(part+1)*156]
            self.lib.radio_probe(self.ap,self.child,packet,len(packet))

    def test_candidate_denied_until_both_valid_fragments_and_out_of_order_supported(self):
        self.assertFalse(self.lib.allowed_probe(self.ap))
        grant=self.grant();self.deliver(grant,(1,))
        self.assertFalse(self.lib.allowed_probe(self.ap))
        self.deliver(grant,(0,));self.assertTrue(self.lib.allowed_probe(self.ap))

    def test_corruption_and_wrong_parent_private_key_signature_do_not_admit(self):
        grant=bytearray(self.grant());grant[120]^=1
        # Re-sign authority layer to ensure the inner key-possession proof is tested.
        grant=bytes(grant[:-64])+sign(self.authority,bytes(grant[:-64]))
        self.deliver(grant);self.assertFalse(self.lib.allowed_probe(self.ap))

    def test_nonce_child_ap_and_role_binding_reject_otherwise_valid_signatures(self):
        for changes in (dict(nonce=b'N'*16),dict(child=b'Z'*6),dict(ap=b'X'*6),dict(level=2)):
            with self.subTest(changes=changes):
                self.deliver(self.grant(**changes));self.assertFalse(self.lib.allowed_probe(self.ap))

    def test_cache_expires_and_old_response_cannot_refresh_it(self):
        grant=self.grant();self.deliver(grant);self.assertTrue(self.lib.allowed_probe(self.ap))
        self.lib.time_probe(21000)
        self.assertFalse(self.lib.allowed_probe(self.ap))
        self.deliver(grant);self.assertFalse(self.lib.allowed_probe(self.ap))

    def test_disconnect_requires_new_challenge_even_with_old_lease_remaining(self):
        grant=self.grant();self.deliver(grant);self.assertTrue(self.lib.allowed_probe(self.ap))
        self.lib.disconnect_probe();self.assertFalse(self.lib.allowed_probe(self.ap))
        self.deliver(grant);self.assertFalse(self.lib.allowed_probe(self.ap))

    def test_fixed_parent_requires_signed_identity_in_addition_to_same_bssid(self):
        self.assertFalse(self.lib.expected_probe(self.ap,b'uav-other'))
        self.deliver(self.grant());self.assertFalse(self.lib.allowed_probe(self.ap))
        self.assertFalse(self.lib.expected_probe(self.ap,b'uav-001'))
        self.deliver(self.grant());self.assertTrue(self.lib.allowed_probe(self.ap))

    def test_first_discovery_keeps_fixed_identity_before_next_scan(self):
        self.assertEqual(0,self.lib.reset_probe(self.callback,4))
        self.assertFalse(self.lib.expected_probe(self.ap,b'uav-other'))
        self.lib.process_discover_probe()
        self.lib.challenge_probe(self.ap,self.nonce)
        self.deliver(self.grant())
        self.assertFalse(self.lib.allowed_probe(self.ap))
        self.lib.time_probe(1000)
        self.assertEqual(0,self.lib.recover_probe(0))

    def test_offline_selection_retries_without_disconnect_event_and_is_throttled(self):
        self.assertEqual(0,self.lib.recover_probe(0))
        self.lib.time_probe(1999)
        self.assertEqual(0,self.lib.recover_probe(0))
        self.lib.time_probe(2000)
        self.assertEqual(1,self.lib.recover_probe(0))
        self.assertEqual(1,self.lib.recover_probe(0))
        self.lib.time_probe(3999)
        self.assertEqual(1,self.lib.recover_probe(0))
        self.lib.time_probe(4000)
        self.assertEqual(2,self.lib.recover_probe(0))
        self.lib.time_probe(6000)
        self.assertEqual(2,self.lib.recover_probe(1))
        self.lib.time_probe(7999)
        self.assertEqual(2,self.lib.recover_probe(0))
        self.lib.time_probe(8000)
        self.assertEqual(3,self.lib.recover_probe(0))

    def test_restored_fixed_parent_proof_accelerates_rescan_and_survives_it(self):
        self.assertFalse(self.lib.expected_probe(self.ap,b'uav-001'))
        self.lib.time_probe(2000)
        self.assertEqual(1,self.lib.recover_probe(0))
        self.assertFalse(self.lib.allowed_probe(self.ap))
        self.lib.time_probe(2499)
        self.lib.challenge_probe(self.ap,self.nonce)
        self.deliver(self.grant())
        self.assertTrue(self.lib.allowed_probe(self.ap))
        self.assertEqual(1,self.lib.recover_probe(0))
        self.lib.time_probe(2500)
        self.assertEqual(2,self.lib.recover_probe(0))
        self.assertTrue(self.lib.allowed_probe(self.ap))
        self.assertEqual(2,self.lib.recover_probe(0))

    def test_connected_nodes_and_root_do_not_retry_but_offline_relays_do(self):
        self.deliver(self.grant())
        self.lib.time_probe(2000)
        self.assertEqual(0,self.lib.recover_probe(1))
        for level in (1,2,3):
            with self.subTest(level=level):
                self.assertEqual(0,self.lib.reset_probe(self.callback,level))
                self.lib.time_probe(10000)
                self.assertEqual(0,self.lib.recover_probe(1))
                self.lib.time_probe(12000)
                self.assertEqual(0 if level==1 else 1,self.lib.recover_probe(0))

    def test_late_response_and_invalid_fragment_size_are_denied(self):
        self.lib.time_probe(6000);self.deliver(self.grant());self.assertFalse(self.lib.allowed_probe(self.ap))
        self.lib.radio_probe(self.ap,self.child,b'PAF1',4)
        self.assertFalse(self.lib.allowed_probe(self.ap))

    def test_fresh_root_grant_binds_boot_nonce_key_and_live_usb_session(self):
        self.assertEqual(0,self.lib.reset_probe(self.callback,1))
        request=ctypes.create_string_buffer(177)
        self.assertTrue(self.lib.own_probe(request))
        raw=request.raw
        device=ec.derive_private_key(1<<248,ec.SECP256R1())
        verify(public_bytes(device.public_key()),raw[-64:],raw[:-64])
        unsigned=raw+public_bytes(device.public_key())+bytes([1,20])+b'\0'*4
        grant=unsigned+sign(self.authority,unsigned)
        self.lib.grant_probe(grant);self.assertTrue(self.lib.relay_probe())
        self.lib.online_probe(0);self.assertFalse(self.lib.relay_probe())
        self.lib.online_probe(1);self.lib.grant_probe(grant)
        self.assertFalse(self.lib.relay_probe())


if __name__=='__main__':unittest.main()
