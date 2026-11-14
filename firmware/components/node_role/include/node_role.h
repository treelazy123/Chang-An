#pragma once
#include <stdbool.h>
#include <stdint.h>

const char *node_role_name(void);
const char *node_role_id(void);
const char *node_topology_name(void);
bool node_role_is_root(void);
bool node_role_is_leaf(void);
/* Zero means no fixed level; non-root nodes still cannot become root. */
uint8_t node_role_fixed_level(void);
