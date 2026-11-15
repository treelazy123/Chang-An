idf_component_register(SRCS "app_protocol.c" INCLUDE_DIRS "include"
    REQUIRES cjson node_role mesh_lite esp_timer esp_system esp_netif esp_wifi)
