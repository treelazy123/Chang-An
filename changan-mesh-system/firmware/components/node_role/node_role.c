#include "sdkconfig.h"
#include "node_role.h"
const char *node_role_name(void) {
#if CONFIG_APP_ROLE_UGV_ROOT
    return "ugv_root";
#elif CONFIG_APP_ROLE_UGV
    return "ugv";
#elif CONFIG_APP_ROLE_UAV
    return "uav";
#else
    return "micro_uav";
#endif
}
const char *node_role_id(void) { return CONFIG_APP_NODE_ID; }
bool node_role_is_root(void) {
#if CONFIG_APP_ROLE_UGV_ROOT
    return true;
#else
    return false;
#endif
}
bool node_role_is_leaf(void) {
#if CONFIG_APP_ROLE_MICRO_UAV
    return true;
#else
    return false;
#endif
}
const char *node_topology_name(void) { return "chain"; }
uint8_t node_role_fixed_level(void) {
#if CONFIG_APP_ROLE_UGV_ROOT
    return 1;
#elif CONFIG_APP_ROLE_UGV
    return 2;
#elif CONFIG_APP_ROLE_UAV
    return 3;
#else
    return 4;
#endif
}
