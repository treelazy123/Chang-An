idf_component_register(SRCS "service_discovery.c" INCLUDE_DIRS "include"
    REQUIRES app_protocol mesh_lite node_role esp_netif esp_timer esp_hw_support lwip freertos)
