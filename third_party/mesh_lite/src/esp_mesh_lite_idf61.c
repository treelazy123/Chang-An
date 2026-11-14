/* IDF 6.1 adapter for the Mesh-Lite 1.0.2 precompiled core. */
#include "esp_netif.h"

typedef struct {
    esp_netif_t *current;
    esp_netif_t *next;
} mesh_netif_cursor_t;

static esp_err_t mesh_netif_next_in_tcpip(void *arg)
{
    mesh_netif_cursor_t *cursor = arg;
    cursor->next = esp_netif_next_unsafe(cursor->current);
    return ESP_OK;
}

/* Retained binary ABI: each step executes in the TCP/IP context. The lab
 * creates its STA/AP interfaces before Mesh-Lite starts and never deletes
 * them. Dynamic interface destruction requires an upstream core update. */
esp_netif_t *esp_netif_next(esp_netif_t *current)
{
    mesh_netif_cursor_t cursor = {.current = current};
    if (esp_netif_tcpip_exec(mesh_netif_next_in_tcpip, &cursor) != ESP_OK) {
        return NULL;
    }
    return cursor.next;
}
