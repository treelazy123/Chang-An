set(parent_auth_requires node_role mesh_access mesh_lite esp_wifi esp_netif esp_timer esp_hw_support freertos mbedtls cjson log)
# ESP-IDF scans dependencies in a separate CMake script before sdkconfig and
# project-local variables are available. Report the same dependency graph there;
# identity validation and binary embedding belong to the normal configure pass.
if(CMAKE_BUILD_EARLY_EXPANSION)
    idf_component_register(SRCS "parent_auth.c" INCLUDE_DIRS "include"
        REQUIRES ${parent_auth_requires})
    return()
endif()

set(auth_dir "${MESH_SYSTEM_ROOT}/secrets/parent-auth")
set(auth_key "${auth_dir}/nodes/${CONFIG_APP_NODE_ID}/auth.key")
set(auth_public "${auth_dir}/authority.pub")
foreach(file "${auth_key}" "${auth_public}")
    if(NOT EXISTS "${file}")
        message(FATAL_ERROR "Missing parent-auth enrollment for ${CONFIG_APP_NODE_ID}: ${file}. Run uv run --locked python tools/provision_parent_auth.py")
    endif()
endforeach()
file(SIZE "${auth_key}" auth_key_size)
file(SIZE "${auth_public}" auth_public_size)
if(NOT auth_key_size EQUAL 32 OR NOT auth_public_size EQUAL 65)
    message(FATAL_ERROR "Invalid raw P-256 parent-auth enrollment sizes; inspect existing files without overwriting")
endif()
idf_component_register(SRCS "parent_auth.c" INCLUDE_DIRS "include"
    REQUIRES ${parent_auth_requires}
    EMBED_FILES "${auth_key}" "${auth_public}")
