#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_mesh_lite.h"
#include "lwip/sockets.h"
#include "lwip/inet.h"
#include "node_role.h"
#include "app_protocol.h"
#include "serial_gateway.h"
#include "transport_tcp.h"
#include "service_discovery.h"


#if CONFIG_APP_ROLE_UGV
static QueueHandle_t s_uplink;
static QueueHandle_t s_downlink;
#endif

static const char *TAG = "transport_tcp";
static int64_t now_ms(void) { return esp_timer_get_time() / 1000; }

static void socket_timeouts(int fd)
{
    struct timeval timeout = {.tv_sec = 1};
    (void)setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    int on = 1;
    (void)setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &on, sizeof(on));
}
static bool send_message(int fd, const cJSON *message)
{
    char *json = cJSON_PrintUnformatted(message);
    if (!json) { return false; }
    uint8_t frame[APP_FRAME_MAX];
    size_t total = app_frame_encode(json, strlen(json), frame);
    cJSON_free(json);
    if (!total) { return false; }
    int64_t deadline = now_ms() + 2000;
    size_t sent = 0;
    while (sent < total && now_ms() < deadline) {
        int size = send(fd, frame + sent, total - sent, 0);
        if (size < 0 && errno == EINTR) { continue; }
        if (size <= 0) { return false; }
        sent += (size_t)size;
    }
    return sent == total;
}

#if CONFIG_APP_ROLE_PC_ROOT || CONFIG_APP_ROLE_UGV

typedef struct {
    int fd;
    char node_id[APP_NODE_ID_MAX + 1];
    char role[16];
    int64_t last_rx_ms;
    bool drop;
    app_frame_decoder_t decoder;
} peer_t;
static peer_t s_peers[CONFIG_APP_TCP_MAX_CLIENTS];
static serial_message_t s_pc_message;

static bool publish(const cJSON *message)
{
    if (!message) { return false; }
#if CONFIG_APP_ROLE_PC_ROOT
    char *json = cJSON_PrintUnformatted(message);
    if (!json) { return false; }
    bool sent = serial_gateway_publish(json, strlen(json));
    cJSON_free(json);
    return sent;
#else
    cJSON *wrapper = app_message_new("relay");
    if (!wrapper) { return false; }
    cJSON *copy = cJSON_Duplicate(message, true);
    if (!copy) { cJSON_Delete(wrapper); return false; }
    cJSON_AddItemToObject(wrapper, "message", copy);
    char *json = cJSON_PrintUnformatted(wrapper);
    cJSON_Delete(wrapper);
    if (!json) { return false; }
    serial_message_t packet = {.size = strlen(json)};
    bool sent = false;
    if (packet.size <= APP_JSON_MAX) {
        memcpy(packet.json, json, packet.size + 1);
        sent = xQueueSend(s_uplink, &packet, 0) == pdTRUE;
    }
    if (!sent) { ESP_LOGW(TAG, "UGV uplink queue full or message too large; message discarded"); }
    cJSON_free(json);
    return sent;
#endif
}
static bool next_command(serial_message_t *packet)
{
#if CONFIG_APP_ROLE_PC_ROOT
    return serial_gateway_receive(packet);
#else
    return xQueueReceive(s_downlink, packet, 0) == pdTRUE;
#endif
}
static void pc_error(const cJSON *request, const char *error)
{
    cJSON *message = app_message_new("error");
    if (!message) { return; }
    const char *id = app_json_string(request, "msg_id");
    const char *target = app_json_string(request, "target");
    if (id) { cJSON_AddStringToObject(message, "msg_id", id); }
    if (target) { cJSON_AddStringToObject(message, "target", target); }
    cJSON_AddStringToObject(message, "error", error);
    publish(message);
    cJSON_Delete(message);
}
static void peer_event(const peer_t *peer, const char *event)
{
    cJSON *message = app_message_new("event");
    if (!message) { return; }
    cJSON_AddStringToObject(message, "event", event);
    cJSON_AddStringToObject(message, "peer_id", peer->node_id);
    cJSON_AddStringToObject(message, "role", peer->role);
    publish(message);
    cJSON_Delete(message);
}
static void close_peer(peer_t *peer)
{
    if (peer->node_id[0]) { peer_event(peer, "offline"); }
    if (peer->fd >= 0) { shutdown(peer->fd, SHUT_RDWR); close(peer->fd); }
    memset(peer, 0, sizeof(*peer));
    peer->fd = -1;
}
static bool role_valid(const char *role)
{
#if CONFIG_APP_ROLE_PC_ROOT
    return role && !strcmp(role, "ugv");
#else
    return role && (!strcmp(role, "uav") || !strcmp(role, "micro_uav"));
#endif
}
static void peer_received(const char *json, size_t size, void *ctx)
{
    peer_t *peer = ctx;
    cJSON *message = app_message_parse(json, size);
    if (!message) { peer->drop = true; return; }
    const char *type = app_json_string(message, "type");
    const char *id = app_json_string(message, "node_id");
    if (!peer->node_id[0]) {
        const char *role = app_json_string(message, "role");
        bool valid = !strcmp(type, "hello") && app_node_id_valid(id) &&
                     strcmp(id, node_role_id()) && role_valid(role);
#if CONFIG_APP_ROLE_PC_ROOT
        valid = valid && !strcmp(id, CONFIG_APP_UGV_NODE_ID);
#endif
        for (int i = 0; valid && i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) {
            if (&s_peers[i] != peer && s_peers[i].fd >= 0 &&
                !strcmp(s_peers[i].node_id, id)) { valid = false; }
        }
        if (!valid) {
            ESP_LOGW(TAG, "TCP_HELLO_REJECTED server=%s peer=%s role=%s", node_role_id(),
                     id ? id : "(missing)", role ? role : "(missing)");
            cJSON *reply = app_message_new("hello_reject");
            if (reply) {
                cJSON_AddStringToObject(reply, "error", "invalid_or_duplicate_identity");
                (void)send_message(peer->fd, reply);
                cJSON_Delete(reply);
            }
            peer->drop = true;
        } else {
            snprintf(peer->node_id, sizeof(peer->node_id), "%s", id);
            snprintf(peer->role, sizeof(peer->role), "%s", role);
            cJSON *reply = app_message_new("hello_ack");
            if (reply) {
                cJSON_AddStringToObject(reply, "target", id);
                peer->drop = !send_message(peer->fd, reply);
                cJSON_Delete(reply);
            } else { peer->drop = true; }
            if (!peer->drop) {
                peer_event(peer, "online");
                ESP_LOGI(TAG, "Registered node=%s role=%s", peer->node_id, peer->role);
            }
        }
    } else if (!id || strcmp(id, peer->node_id)) {
        peer->drop = true;
#if CONFIG_APP_ROLE_PC_ROOT
    } else if (!strcmp(type, "relay")) {
        const cJSON *inner = cJSON_GetObjectItemCaseSensitive(message, "message");
        char *text = cJSON_PrintUnformatted(inner);
        cJSON *validated = text ? app_message_parse(text, strlen(text)) : NULL;
        cJSON_free(text);
        const char *kind = app_json_string(validated, "type");
        const char *source = app_json_string(validated, "node_id");
        if (!kind || !app_node_id_valid(source) || !strcmp(source, node_role_id()) ||
            (strcmp(kind, "telemetry") && strcmp(kind, "ack") && strcmp(kind, "event") &&
             strcmp(kind, "nodes") && strcmp(kind, "error"))) { peer->drop = true; }
        else {
            if (!strcmp(kind, "nodes")) {
                cJSON *nodes = cJSON_GetObjectItemCaseSensitive(validated, "nodes");
                if (cJSON_IsArray(nodes)) {
                    cJSON *root = app_status_payload();
                    if (root) {
                        cJSON_AddStringToObject(root, "node_id", node_role_id());
                        cJSON_AddBoolToObject(root, "online", true);
                        cJSON_AddItemToArray(nodes, root);
                    }
                }
            }
            publish(validated);
        }
        cJSON_Delete(validated);
#endif
    } else if (strcmp(type, "telemetry") && strcmp(type, "ack") && strcmp(type, "error")) {
        peer->drop = true;
    } else {
        publish(message);
        if (!strcmp(type, "telemetry")) {
            cJSON *reply = app_message_new("telemetry_ack");
            if (reply) {
                cJSON_AddStringToObject(reply, "target", peer->node_id);
                if (!send_message(peer->fd, reply)) { peer->drop = true; }
                cJSON_Delete(reply);
            } else { peer->drop = true; }
        }
    }
    peer->last_rx_ms = now_ms();
    cJSON_Delete(message);
}
static void pc_received(const serial_message_t *packet)
{
    if (packet->size > 512) { pc_error(NULL, "command_too_large"); return; }
    cJSON *message = app_message_parse(packet->json, packet->size);
    if (!message) { pc_error(NULL, "invalid_message"); return; }
    const char *type = app_json_string(message, "type");
#if CONFIG_APP_ROLE_PC_ROOT
    if (!strcmp(type, "list")) {
        for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) {
            if (s_peers[i].fd >= 0 && !s_peers[i].drop && s_peers[i].node_id[0]) {
                if (!send_message(s_peers[i].fd, message)) {
                    s_peers[i].drop = true; pc_error(message, "tcp_send_failed");
                }
                cJSON_Delete(message); return;
            }
        }
    }
#endif
    if (!strcmp(type, "list")) {
        const char *id = app_json_string(message, "msg_id");
        if (!id || !id[0] || strlen(id) > APP_MSG_ID_MAX) {
            pc_error(message, "invalid_msg_id");
        } else {
            cJSON *reply = app_message_new("nodes");
            cJSON *nodes = cJSON_CreateArray();
            if (reply && nodes) {
                cJSON_AddStringToObject(reply, "msg_id", id);
                cJSON_AddItemToObject(reply, "nodes", nodes);
                cJSON *root = app_status_payload();
                if (root) {
                    cJSON_AddStringToObject(root, "node_id", node_role_id());
                    cJSON_AddBoolToObject(root, "online", true);
                    cJSON_AddItemToArray(nodes, root);
                }
                for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) {
                    if (s_peers[i].fd < 0 || !s_peers[i].node_id[0] || s_peers[i].drop) { continue; }
                    cJSON *item = cJSON_CreateObject();
                    if (item) {
                        cJSON_AddStringToObject(item, "node_id", s_peers[i].node_id);
                        cJSON_AddStringToObject(item, "role", s_peers[i].role);
                        cJSON_AddBoolToObject(item, "online", true);
                        cJSON_AddItemToArray(nodes, item);
                    }
                }
                publish(reply);
            } else { cJSON_Delete(nodes); }
            cJSON_Delete(reply);
        }
    } else if (!app_command_valid(message)) {
        pc_error(message, "invalid_command");
    } else {
        const char *target = app_json_string(message, "target");
        if (!strcmp(target, node_role_id())) {
            cJSON *reply = app_command_reply(message);
            publish(reply);
            cJSON_Delete(reply);
        } else {
            peer_t *peer = NULL;
            for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) {
                if (s_peers[i].fd < 0 || s_peers[i].drop || !s_peers[i].node_id[0]) { continue; }
#if CONFIG_APP_ROLE_PC_ROOT
                peer = &s_peers[i]; break;
#else
                if (!strcmp(s_peers[i].node_id, target)) { peer = &s_peers[i]; break; }
#endif
            }
            if (!peer) { pc_error(message, "node_offline"); }
            else if (!send_message(peer->fd, message)) {
                peer->drop = true;
                pc_error(message, "tcp_send_failed");
            }
            // An ACK is generated by the target, never fabricated by the gateway.
        }
    }
    cJSON_Delete(message);
}
static void server_task(void *arg)
{
    (void)arg;
    for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) { s_peers[i].fd = -1; }
    uint8_t input[256];
    int64_t last_status = 0;
    for (;;) {
        int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
        if (listener < 0) { vTaskDelay(pdMS_TO_TICKS(1000)); continue; }
        int on = 1;
        (void)setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));
        struct sockaddr_in address = {.sin_family = AF_INET, .sin_port = htons(node_role_is_root() ? CONFIG_APP_TCP_PORT : CONFIG_APP_UGV_TCP_PORT),
                                      .sin_addr.s_addr = htonl(INADDR_ANY)};
        if (bind(listener, (struct sockaddr *)&address, sizeof(address)) < 0 ||
            listen(listener, CONFIG_APP_TCP_MAX_CLIENTS) < 0) {
            close(listener); vTaskDelay(pdMS_TO_TICKS(1000)); continue;
        }
        ESP_LOGI(TAG, "TCP server listening on port %d", node_role_is_root() ? CONFIG_APP_TCP_PORT : CONFIG_APP_UGV_TCP_PORT);
        bool active = true;
        while (active) {
            // Bound work per pass so a busy serial host cannot starve network I/O.
            for (int n = 0; n < CONFIG_APP_SERIAL_QUEUE_LENGTH && next_command(&s_pc_message); ++n) {
                pc_received(&s_pc_message);
            }
            if (node_role_is_root() && now_ms() - last_status >= CONFIG_APP_STATUS_PERIOD_MS) {
                cJSON *status = app_message_new("telemetry");
                if (status) {
                    cJSON *payload = app_status_payload();
                    if (payload) { cJSON_AddItemToObject(status, "payload", payload); }
                    publish(status); cJSON_Delete(status);
                }
                last_status = now_ms();
            }
            fd_set reads;
            FD_ZERO(&reads); FD_SET(listener, &reads);
            int maximum = listener;
            for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) {
                peer_t *peer = &s_peers[i];
                if (peer->fd >= 0 && (peer->drop || now_ms() - peer->last_rx_ms >
                    (peer->node_id[0] ? CONFIG_APP_TCP_IDLE_TIMEOUT_MS : 5000))) { close_peer(peer); }
                if (peer->fd >= 0) { FD_SET(peer->fd, &reads); if (peer->fd > maximum) { maximum = peer->fd; } }
            }
            struct timeval wait = {.tv_usec = 100000};
            int ready = select(maximum + 1, &reads, NULL, NULL, &wait);
            if (ready < 0) { if (errno == EINTR) { continue; } active = false; continue; }
            if (FD_ISSET(listener, &reads)) {
                int fd = accept(listener, NULL, NULL);
                if (fd >= 0) {
                    peer_t *slot = NULL;
                    for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) {
                        if (s_peers[i].fd < 0) { slot = &s_peers[i]; break; }
                    }
                    if (!slot) {
                        ESP_LOGW(TAG, "TCP_ACCEPT_REJECTED node=%s reason=no_free_slot", node_role_id());
                        close(fd);
                    } else {
                        ESP_LOGI(TAG, "TCP_ACCEPT node=%s fd=%d", node_role_id(), fd);
                        memset(slot, 0, sizeof(*slot));
                        slot->fd = fd; slot->last_rx_ms = now_ms(); socket_timeouts(fd);
                        // The new fd was not in select()'s input set. Read it on the next pass.
                        FD_CLR(fd, &reads);
                    }
                }
            }
            for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) {
                peer_t *peer = &s_peers[i];
                if (peer->fd < 0 || peer->drop || !FD_ISSET(peer->fd, &reads)) { continue; }
                int size = recv(peer->fd, input, sizeof(input), 0);
                if (size <= 0) { peer->drop = true; continue; }
                for (int n = 0; n < size && !peer->drop; ++n) {
                    app_frame_feed(&peer->decoder, input[n], peer_received, peer);
                }
            }
        }
        close(listener);
        for (int i = 0; i < CONFIG_APP_TCP_MAX_CLIENTS; ++i) { close_peer(&s_peers[i]); }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

#endif

#if !CONFIG_APP_ROLE_PC_ROOT

typedef struct {
    int fd;
    bool registered;
    bool drop;
    int64_t last_rx_ms;
    app_frame_decoder_t decoder;
} client_t;
static client_t s_client;

static const char *s_address_reason = "waiting_network";
static const char *s_address_source = "unresolved";

static bool root_address(struct sockaddr_in *address)
{
    esp_netif_t *sta = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_ip_info_t local = {0};
    uint8_t level = esp_mesh_lite_get_level();
    if (level < 2) { s_address_reason = "waiting_mesh_level"; return false; }
    if (!sta || esp_netif_get_ip_info(sta, &local) != ESP_OK || !local.ip.addr) {
        s_address_reason = "waiting_station_ip"; return false;
    }
    address->sin_family = AF_INET;
#if CONFIG_APP_ROLE_UGV
    address->sin_port = htons(CONFIG_APP_TCP_PORT);
    if (CONFIG_APP_ROOT_IP_OVERRIDE[0]) {
        s_address_source = "root_ip_override";
        s_address_reason = "invalid_root_ip_override";
        return inet_pton(AF_INET, CONFIG_APP_ROOT_IP_OVERRIDE, &address->sin_addr) == 1 &&
               address->sin_addr.s_addr != INADDR_ANY && address->sin_addr.s_addr != INADDR_BROADCAST;
    }
    // At level 2 the DHCP gateway is the root SoftAP itself. This remains
    // valid in no-router mode even when the core's broadcast root record is not ready.
    if (level == 2 && local.gw.addr) {
        address->sin_addr.s_addr = local.gw.addr;
        s_address_source = "level2_dhcp_gateway";
        return true;
    }
    esp_ip_addr_t root = {0};
    if (esp_mesh_lite_get_root_ip(ESP_IPADDR_TYPE_V4, &root) != ESP_OK ||
        root.type != ESP_IPADDR_TYPE_V4 || !root.u_addr.ip4.addr) {
        s_address_reason = "waiting_mesh_root_ip"; return false;
    }
    // Vendored Mesh-Lite 1.0.2 returns host-order IPv4 for non-root nodes:
    // level 2 calls get_parent_ip() (byte-swaps DHCP gw), and deeper levels
    // construct 0xc0a8XX01. sockaddr_in always requires network byte order.
    address->sin_addr.s_addr = htonl(root.u_addr.ip4.addr);
    s_address_source = "mesh_root_ip_host_to_network";
#else
    address->sin_port = htons(CONFIG_APP_UGV_TCP_PORT);
    if (CONFIG_APP_UGV_IP_OVERRIDE[0]) {
        s_address_source = "ugv_ip_override";
        s_address_reason = "invalid_ugv_ip_override";
        return inet_pton(AF_INET, CONFIG_APP_UGV_IP_OVERRIDE, &address->sin_addr) == 1 &&
               address->sin_addr.s_addr != INADDR_ANY && address->sin_addr.s_addr != INADDR_BROADCAST;
    }
#if CONFIG_APP_ROLE_UAV && CONFIG_APP_TOPOLOGY_CHAIN
    // Only in the fixed four-node chain is UAV's level-2 parent the UGV.
    // Never apply this fallback to Micro: its immediate gateway is UAV.
    if (level == 3 && local.gw.addr) {
        address->sin_addr.s_addr = local.gw.addr;
        s_address_source = "chain_ugv_parent_gateway";
        return true;
    }
#endif
    uint32_t ugv;
    if (!service_discovery_ugv(&ugv)) {
        s_address_reason = "waiting_ugv_service_announcement"; return false;
    }
    address->sin_addr.s_addr = ugv;
    s_address_source = "ugv_service_announcement";
#endif
    return true;
}
static bool connect_with_timeout(int fd, const struct sockaddr_in *address)
{
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) { return false; }
    int result = connect(fd, (const struct sockaddr *)address, sizeof(*address));
    if (result < 0 && errno != EINPROGRESS) { return false; }
    if (result < 0) {
        fd_set writes; FD_ZERO(&writes); FD_SET(fd, &writes);
        struct timeval timeout = {.tv_sec = 3};
        int ready = select(fd + 1, NULL, &writes, NULL, &timeout);
        if (ready <= 0) { if (!ready) { errno = ETIMEDOUT; } return false; }
        int error = 0; socklen_t length = sizeof(error);
        if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &length) < 0) { return false; }
        if (error) { errno = error; return false; }
    }
    return fcntl(fd, F_SETFL, flags) == 0;
}
static void client_received(const char *json, size_t size, void *ctx)
{
    client_t *client = ctx;
    cJSON *message = app_message_parse(json, size);
    if (!message) { client->drop = true; return; }
    const char *type = app_json_string(message, "type");
    const char *target = app_json_string(message, "target");
    if (!client->registered) {
        if (!strcmp(type, "hello_ack") && target && !strcmp(target, node_role_id())) {
            client->registered = true;
            ESP_LOGI(TAG, "Registered with upstream as %s", node_role_id());
        } else {
            ESP_LOGW(TAG, "TCP_REGISTER_REJECTED node=%s type=%s error=%s", node_role_id(),
                     type, app_json_string(message, "error") ? app_json_string(message, "error") : "unexpected_reply");
            client->drop = true;
        }
    } else if (!strcmp(type, "telemetry_ack") && target && !strcmp(target, node_role_id())) {
        // Application heartbeat confirms the upstream server is receiving frames.
#if CONFIG_APP_ROLE_UGV
    } else if (app_command_valid(message) || !strcmp(type, "list")) {
        serial_message_t packet = {.size = size};
        memcpy(packet.json, json, size + 1);
        if (xQueueSend(s_downlink, &packet, 0) != pdTRUE) {
            cJSON *error = app_message_new("error");
            if (error) {
                const char *id = app_json_string(message, "msg_id");
                if (id) { cJSON_AddStringToObject(error, "msg_id", id); }
                cJSON_AddStringToObject(error, "error", "ugv_command_queue_full");
                if (!send_message(client->fd, error)) { client->drop = true; }
                cJSON_Delete(error);
            }
        }
#else
    } else if (app_command_valid(message) && target && !strcmp(target, node_role_id())) {
        cJSON *reply = app_command_reply(message);
        if (!reply || !send_message(client->fd, reply)) { client->drop = true; }
        cJSON_Delete(reply);
#endif
    } else { client->drop = true; }
    client->last_rx_ms = now_ms();
    cJSON_Delete(message);
}
static void client_task(void *arg)
{
    (void)arg;
    uint8_t input[256];
    uint32_t sequence = 0;
    uint32_t backoff_ms = 1000;
    int64_t last_wait_log = -5000;
    for (;;) {
        struct sockaddr_in address = {0};
        if (!root_address(&address)) {
            if (now_ms() - last_wait_log >= 5000) {
                ESP_LOGW(TAG, "TCP_WAIT node=%s reason=%s level=%u", node_role_id(),
                         s_address_reason, (unsigned)esp_mesh_lite_get_level());
                last_wait_log = now_ms();
            }
            vTaskDelay(pdMS_TO_TICKS(1000)); continue;
        }
        char host[16] = {0};
        (void)inet_ntop(AF_INET, &address.sin_addr, host, sizeof(host));
        ESP_LOGI(TAG, "TCP_CONNECT node=%s target=%s:%u source=%s", node_role_id(),
                 host, (unsigned)ntohs(address.sin_port), s_address_source);
        int fd = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
        if (fd < 0) {
            ESP_LOGW(TAG, "TCP_SOCKET_FAILED node=%s errno=%d", node_role_id(), errno);
            vTaskDelay(pdMS_TO_TICKS(backoff_ms)); continue;
        }
        socket_timeouts(fd);
        if (!connect_with_timeout(fd, &address)) {
            int error = errno;
            ESP_LOGW(TAG, "TCP_CONNECT_FAILED node=%s target=%s:%u errno=%d (%s)",
                     node_role_id(), host, (unsigned)ntohs(address.sin_port), error, strerror(error));
            close(fd); vTaskDelay(pdMS_TO_TICKS(backoff_ms));
            if (backoff_ms < 8000) { backoff_ms *= 2; }
            continue;
        }
        memset(&s_client, 0, sizeof(s_client));
        s_client.fd = fd; s_client.last_rx_ms = now_ms();
        cJSON *hello = app_message_new("hello");
        if (hello) { cJSON_AddStringToObject(hello, "role", node_role_name()); }
        s_client.drop = !hello || !send_message(fd, hello);
        cJSON_Delete(hello);
        ESP_LOGI(TAG, "TCP_HELLO node=%s target=%s:%u sent=%u", node_role_id(), host,
                 (unsigned)ntohs(address.sin_port), (unsigned)!s_client.drop);
        int64_t connected_at = now_ms();
        int64_t last_report = 0;
        while (!s_client.drop) {
            struct sockaddr_in current = {0};
            if (!root_address(&current) || current.sin_addr.s_addr != address.sin_addr.s_addr ||
                (!s_client.registered && now_ms() - connected_at > 5000) ||
                (s_client.registered && now_ms() - s_client.last_rx_ms > CONFIG_APP_TCP_IDLE_TIMEOUT_MS)) { break; }
            if (s_client.registered && now_ms() - last_report >= CONFIG_APP_STATUS_PERIOD_MS) {
                cJSON *status = app_message_new("telemetry");
                if (status) {
                    cJSON_AddNumberToObject(status, "seq", ++sequence);
                    cJSON *payload = app_status_payload();
                    if (payload) { cJSON_AddItemToObject(status, "payload", payload); }
                }
                s_client.drop = !status || !send_message(fd, status);
                cJSON_Delete(status);
                if (s_client.drop) { break; }
                last_report = now_ms(); backoff_ms = 1000;
            }
#if CONFIG_APP_ROLE_UGV
            for (int n = 0; s_client.registered && n < 2; ++n) {
                serial_message_t packet;
                if (xQueueReceive(s_uplink, &packet, 0) != pdTRUE) { break; }
                cJSON *queued = app_message_parse(packet.json, packet.size);
                bool sent = queued && send_message(fd, queued);
                cJSON_Delete(queued);
                if (!sent) { s_client.drop = true; break; }
            }
            if (s_client.drop) { break; }
#endif
            fd_set reads; FD_ZERO(&reads); FD_SET(fd, &reads);
            struct timeval wait = {.tv_usec = 200000};
            int ready = select(fd + 1, &reads, NULL, NULL, &wait);
            if (ready < 0) { if (errno == EINTR) { continue; } break; }
            if (!ready) { continue; }
            int size = recv(fd, input, sizeof(input), 0);
            if (size <= 0) { break; }
            for (int n = 0; n < size && !s_client.drop; ++n) {
                app_frame_feed(&s_client.decoder, input[n], client_received, &s_client);
            }
        }
        shutdown(fd, SHUT_RDWR); close(fd);
#if CONFIG_APP_ROLE_UGV
        xQueueReset(s_uplink);
        xQueueReset(s_downlink);
#endif
        ESP_LOGW(TAG, "Upstream session closed; rediscovering and reconnecting");
        vTaskDelay(pdMS_TO_TICKS(backoff_ms));
        if (backoff_ms < 8000) { backoff_ms *= 2; }
    }
}
#endif

esp_err_t transport_tcp_start(void)
{
    if (!app_node_id_valid(node_role_id())) { return ESP_ERR_INVALID_ARG; }
    esp_err_t result = service_discovery_start();
    if (result != ESP_OK) { return result; }
#if CONFIG_APP_ROLE_PC_ROOT
    result = serial_gateway_start();
    if (result != ESP_OK) { return result; }
#elif CONFIG_APP_ROLE_UGV
    s_uplink = xQueueCreate(CONFIG_APP_SERIAL_QUEUE_LENGTH, sizeof(serial_message_t));
    s_downlink = xQueueCreate(CONFIG_APP_SERIAL_QUEUE_LENGTH, sizeof(serial_message_t));
    if (!s_uplink || !s_downlink) { return ESP_ERR_NO_MEM; }
#endif
#if CONFIG_APP_ROLE_PC_ROOT || CONFIG_APP_ROLE_UGV
    if (xTaskCreate(server_task, "gateway_tcp", 10240, NULL, 4, NULL) != pdPASS) { return ESP_ERR_NO_MEM; }
#endif
#if !CONFIG_APP_ROLE_PC_ROOT
    if (xTaskCreate(client_task, "upstream_tcp", 10240, NULL, 4, NULL) != pdPASS) { return ESP_ERR_NO_MEM; }
#endif
    return ESP_OK;
}
