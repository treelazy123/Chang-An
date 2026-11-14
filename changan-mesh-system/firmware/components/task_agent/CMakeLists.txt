idf_component_register(SRCS "task_agent.c" INCLUDE_DIRS "include"
    REQUIRES app_protocol node_role nvs_flash esp_wifi esp_timer esp_system mesh_lite)
