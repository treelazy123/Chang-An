idf_component_register(SRCS "mesh_access.c" INCLUDE_DIRS "include"
    REQUIRES mesh_lite node_role esp_wifi esp_event esp_timer nvs_flash freertos log)
# Cover calls made inside the precompiled Mesh core, without editing it or IDF.
if(NOT CMAKE_BUILD_EARLY_EXPANSION)
    target_link_libraries(${COMPONENT_LIB} INTERFACE
        "-Wl,--wrap=esp_wifi_scan_start" "-Wl,--wrap=esp_wifi_connect" "-Wl,--wrap=esp_wifi_set_config"
        "-Wl,--wrap=esp_wifi_deauth_sta")
endif()
