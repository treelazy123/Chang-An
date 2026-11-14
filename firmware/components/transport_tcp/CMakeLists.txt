idf_component_register(SRCS "transport_tcp.c" INCLUDE_DIRS "include"
    REQUIRES app_protocol service_discovery serial_gateway node_role mesh_lite esp_netif
             esp_timer lwip freertos log)
