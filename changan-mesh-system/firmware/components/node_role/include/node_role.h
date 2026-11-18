#pragma once
#include <stdbool.h>
#include <stdint.h>

const char *node_role_name(void);
const char *node_role_id(void);
const char *node_topology_name(void);
bool node_role_is_root(void);
bool node_role_is_leaf(void);
/* Fixed role levels: root=1, UGV=2, UAV=3, Micro=4. */
uint8_t node_role_fixed_level(void);
