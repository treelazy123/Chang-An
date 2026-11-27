idf_component_register(SRCS "mesh_start.c" "mesh_status.c" "mesh_address.c" INCLUDE_DIRS "include"
                       REQUIRES node_role parent_policy parent_auth mesh_access mesh_lite iot_bridge esp_wifi esp_netif esp_event esp_timer nvs_flash esp_system log freertos)
