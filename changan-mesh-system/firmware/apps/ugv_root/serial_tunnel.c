#include "sdkconfig.h"
#if CONFIG_APP_TRANSPORT_MQTT_SERIAL && CONFIG_APP_ROOT_GATEWAY
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include "lwip/sockets.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/usb_serial_jtag.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "app_protocol.h"
#include "mqtt_serial.h"
#define CHUNK 512
#define HEADER 20
#define RESET 1
#define READY 2
#define OPEN 3
#define OPEN_OK 4
#define DATA 5
#define ACK 6
#define CLOSE 7
#define PING 8
#define PONG 9
#define NETWORK 10
static const char *TAG="mqtt_tunnel";
typedef struct {
    int fd;
    uint32_t token;
    uint16_t tx_seq, rx_seq;
    bool open, waiting;
    int64_t deadline;
    size_t used, sent;
    uint8_t pending[CHUNK];
} channel_t;
static channel_t channels[CONFIG_APP_MQTT_MAX_CHANNELS];
static uint32_t epoch, next_token;
static bool ready, failed;
static bool network_enabled;
static int64_t last_network;
static int64_t last_host, last_hello;
static uint8_t decoder[HEADER+CHUNK];
static size_t decoded;
static int64_t now_ms(void) { return esp_timer_get_time()/1000; }
static void wr16(uint8_t *p,uint16_t n) { p[0]=n>>8;p[1]=n; }
static void wr32(uint8_t *p,uint32_t n) { p[0]=n>>24;p[1]=n>>16;p[2]=n>>8;p[3]=n; }
static uint16_t rd16(const uint8_t *p) { return ((uint16_t)p[0]<<8)|p[1]; }
static uint32_t rd32(const uint8_t *p) { return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3]; }
static void close_channel(int i) {
    if(channels[i].fd>=0) { close(channels[i].fd); }
    memset(&channels[i],0,sizeof(channels[i]));channels[i].fd=-1;
}
static bool frame(uint8_t type,int i,uint32_t token,uint16_t seq,const void *data,size_t size) {
    uint8_t out[HEADER+CHUNK];
    if(size>CHUNK) { failed=true;return false; }
    memcpy(out,"MUX1",4);out[4]=type;out[5]=i;wr32(out+6,epoch);wr32(out+10,token);
    wr16(out+14,seq);wr16(out+16,size);
    if(size) { memcpy(out+HEADER,data,size); }
    /* CRC covers the routing header as well as payload. */
    uint8_t check[16+CHUNK];memcpy(check,out+4,14);
    if(size) { memcpy(check+14,data,size); }
    wr16(out+18,app_crc16(check,14+size));
    size_t sent=0;
    while(sent<HEADER+size) {
        int n=usb_serial_jtag_write_bytes(out+sent,HEADER+size-sent,pdMS_TO_TICKS(100));
        if(n<=0) { failed=true;return false; } sent+=(size_t)n;
    }
    return true;
}
static void reset_session(void) {
    for(int i=0;i<CONFIG_APP_MQTT_MAX_CHANNELS;i++) { close_channel(i); }
    epoch=esp_random();if(!epoch) { epoch=1; }
    decoded=0;ready=false;failed=false;network_enabled=false;last_network=0;last_hello=0;last_host=now_ms();
    ESP_LOGW(TAG,"USB session reset epoch=%lu",(unsigned long)epoch);
}
static void receive_frame(void) {
    uint8_t type=decoder[4],i=decoder[5];uint32_t session=rd32(decoder+6),token=rd32(decoder+10);
    uint16_t seq=rd16(decoder+14),size=rd16(decoder+16);
    if(type==RESET) { failed=true;return; }
    if(session!=epoch) { return; }
    last_host=now_ms();
    if(type==READY && i==255 && !token && !size) { ready=true;network_enabled=(seq==1);return; }
    if(type==PONG && i==255 && !size) { return; }
    if(!ready || i>=CONFIG_APP_MQTT_MAX_CHANNELS || channels[i].fd<0 || token!=channels[i].token) { return; }
    channel_t *c=&channels[i];
    if(type==CLOSE && !size) { close_channel(i); }
    else if(type==OPEN_OK && !size && !c->open) { c->open=true;c->deadline=now_ms()+15000; }
    else if(type==ACK && !size && c->waiting && seq==c->tx_seq) { c->waiting=false;c->tx_seq++; }
    else if(type==DATA && c->open && size && seq==c->rx_seq && !c->used) {
        memcpy(c->pending,decoder+HEADER,size);c->used=size;c->sent=0;c->deadline=now_ms()+15000;
    } else { frame(CLOSE,i,c->token,0,NULL,0);close_channel(i); }
}
static void feed(uint8_t b) {
    if(decoded==sizeof(decoder)) { failed=true;decoded=0; }
    decoder[decoded++]=b;
    while(decoded>=4 && memcmp(decoder,"MUX1",4)) {
        memmove(decoder,decoder+1,--decoded);
    }
    if(decoded<HEADER) { return; }
    uint16_t size=rd16(decoder+16);
    if(size>CHUNK) { failed=true;decoded=0;return; }
    if(decoded<HEADER+size) { return; }
    uint8_t check[14+CHUNK];memcpy(check,decoder+4,14);memcpy(check+14,decoder+HEADER,size);
    if(rd16(decoder+18)!=app_crc16(check,14+size)) { failed=true; }
    else { receive_frame(); }
    decoded=0;
}
static bool would_block(void) { return errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR; }
static void report_network(void) {
    cJSON *message=app_message_new("network");
    cJSON *status=app_status_payload();
    if(message && status) {
        /* Keep the optional diagnostic control frame within the 512-byte MUX budget. */
        const char *omit[]={"heap","heap_min","uptime_ms","topology"};
        for(unsigned k=0;k<sizeof(omit)/sizeof(omit[0]);k++) { cJSON_DeleteItemFromObjectCaseSensitive(status,omit[k]); }
        cJSON_AddItemToObject(message,"payload",status);status=NULL;
        char *json=cJSON_PrintUnformatted(message);
        if(json && strlen(json)<=CHUNK) { frame(NETWORK,255,0,0,json,strlen(json)); }
        cJSON_free(json);
    }
    cJSON_Delete(status);cJSON_Delete(message);
}
static void tunnel_task(void *arg) {
    (void)arg;for(int i=0;i<CONFIG_APP_MQTT_MAX_CHANNELS;i++) { channels[i].fd=-1; }
    int listener=socket(AF_INET,SOCK_STREAM,IPPROTO_IP),one=1;
    if(listener<0) { ESP_LOGE(TAG,"socket failed");vTaskDelete(NULL);return; }
    setsockopt(listener,SOL_SOCKET,SO_REUSEADDR,&one,sizeof(one));
    struct sockaddr_in a={.sin_family=AF_INET,.sin_port=htons(CONFIG_APP_MQTT_PORT),.sin_addr.s_addr=htonl(INADDR_ANY)};
    if(bind(listener,(struct sockaddr*)&a,sizeof(a))<0 || listen(listener,CONFIG_APP_MQTT_MAX_CHANNELS)<0 || fcntl(listener,F_SETFL,O_NONBLOCK)<0) {
        close(listener);ESP_LOGE(TAG,"listener failed");vTaskDelete(NULL);return;
    }
    reset_session();ESP_LOGI(TAG,"TCP TLS byte tunnel listening port=%d",CONFIG_APP_MQTT_PORT);
    for(;;) {
        if(failed || now_ms()-last_host>5000) { reset_session(); }
        if(now_ms()-last_hello>1000) { frame(ready?PING:RESET,255,0,0,NULL,0);last_hello=now_ms(); }
        uint8_t input[CHUNK];int n=usb_serial_jtag_read_bytes(input,sizeof(input),0);
        for(int k=0;k<n;k++) { feed(input[k]);if(failed) { break; } }
        if(ready && network_enabled && !failed && now_ms()-last_network>5000) {
            report_network();last_network=now_ms();
        }
        int fd=accept(listener,NULL,NULL);
        if(fd>=0) {
            int slot=-1;for(int i=0;i<CONFIG_APP_MQTT_MAX_CHANNELS;i++) { if(channels[i].fd<0) { slot=i;break; } }
            if(!ready || slot<0 || fcntl(fd,F_SETFL,O_NONBLOCK)<0) { close(fd); }
            else {
                channel_t *c=&channels[slot];c->fd=fd;c->token=++next_token;if(!c->token) { c->token=++next_token; }
                c->deadline=now_ms()+15000;frame(OPEN,slot,c->token,0,NULL,0);
                ESP_LOGI(TAG,"OPEN channel=%d token=%lu",slot,(unsigned long)c->token);
            }
        }
        for(int i=0;i<CONFIG_APP_MQTT_MAX_CHANNELS;i++) {
            channel_t *c=&channels[i];if(c->fd<0) { continue; }
            bool drop=false;
            if(c->used) {
                n=send(c->fd,c->pending+c->sent,c->used-c->sent,0);
                if(n>0) { c->sent+=n;if(c->sent==c->used) { frame(ACK,i,c->token,c->rx_seq++,NULL,0);c->used=c->sent=0; } }
                else if(n==0 || !would_block()) { drop=true; }
            }
            if(c->open && !c->waiting) {
                n=recv(c->fd,input,sizeof(input),0);
                if(n>0) { frame(DATA,i,c->token,c->tx_seq,input,n);c->waiting=true;c->deadline=now_ms()+15000; }
                else if(n==0 || !would_block()) { drop=true; }
            }
            if((!c->open || c->waiting || c->used) && now_ms()>c->deadline) { drop=true; }
            if(drop) { frame(CLOSE,i,c->token,0,NULL,0);close_channel(i); }
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}
esp_err_t serial_tunnel_start(void) {
    usb_serial_jtag_driver_config_t c={.rx_buffer_size=4096,.tx_buffer_size=4096};
    esp_err_t err=usb_serial_jtag_driver_install(&c);if(err!=ESP_OK) { return err; }
    return xTaskCreate(tunnel_task,"usb_tls_tunnel",6144,NULL,4,NULL)==pdPASS?ESP_OK:ESP_ERR_NO_MEM;
}
#endif
