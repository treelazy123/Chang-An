idf_component_register(SRCS "parent_policy.c" INCLUDE_DIRS "include"
    REQUIRES cjson node_role mesh_lite nvs_flash freertos esp_timer esp_wifi log)
