idf_component_register(SRCS "app_main.c" INCLUDE_DIRS "."
                       REQUIRES node_role network_mesh_lite transport_tcp mqtt_serial freertos)
