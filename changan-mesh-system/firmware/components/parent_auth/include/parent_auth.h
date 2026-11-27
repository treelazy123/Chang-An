#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"
#include "cJSON.h"

#define PA_REQUEST_BODY 113
#define PA_REQUEST_SIZE 177
#define PA_GRANT_BODY 248
#define PA_GRANT_SIZE 312
#define PA_LEASE_MS 20000
#define PA_RESPONSE_MS 5000

typedef struct __attribute__((packed)) {
    uint8_t magic[4], purpose;
    uint8_t node[32], root[32], boot[16], ap[6], nonce[16], child[6], signature[64];
} pa_request_t;
typedef struct __attribute__((packed)) {
    pa_request_t request;
    uint8_t public_key[65], level, ttl, revision[4], signature[64];
} pa_grant_t;
_Static_assert(sizeof(pa_request_t)==PA_REQUEST_SIZE,"parent request wire layout");
_Static_assert(sizeof(pa_grant_t)==PA_GRANT_SIZE,"parent grant wire layout");

/* Call after Mesh initialization and before start/parent-policy registration. */
esp_err_t parent_auth_init(void);
/* Nonblocking fail-closed filter, shared by every non-root role. */
/* expected_id: "" selects any authorized role peer, a node ID pins identity,
 * NULL preserves the previous selection constraint for periodic revalidation. */
bool parent_auth_candidate(const uint8_t mac[6],const char *expected_id);
/* MQTT acceptance/subscription or negotiated root USB session, not a ready flag. */
void parent_auth_online(bool online);
/* Register before Mesh's Wi-Fi handlers: reconnects require a fresh challenge. */
void parent_auth_disconnected(void);
bool parent_auth_take_request(pa_request_t *request);
bool parent_auth_accept_grant(const void *data,size_t size);
void parent_auth_status(cJSON *payload);
