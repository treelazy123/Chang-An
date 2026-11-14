# Replace this build's NAPT translation unit; never modify the shared SDK.
idf_build_get_property(_mesh_python PYTHON)
idf_component_get_property(_mesh_lwip_lib lwip COMPONENT_LIB)
set(_mesh_napt "$ENV{IDF_PATH}/components/lwip/lwip/src/core/ipv4/ip4_napt.c")
set(_mesh_ip4 "$ENV{IDF_PATH}/components/lwip/lwip/src/core/ipv4/ip4.c")
set(_mesh_generated "${CMAKE_BINARY_DIR}/compat/ip4_napt.c")
execute_process(
    COMMAND "${_mesh_python}" "${MESH_SYSTEM_ROOT}/tools/prepare_napt.py"
            --source "${_mesh_napt}" --ip4 "${_mesh_ip4}"
            --patch "${MESH_SYSTEM_ROOT}/third_party/iot_bridge/patch/ip4_napt.patch"
            --output "${_mesh_generated}"
    RESULT_VARIABLE _mesh_result)
if(NOT _mesh_result EQUAL 0)
    message(FATAL_ERROR "Could not prepare the build-local IDF 6.1 NAPT compatibility source.")
endif()
get_target_property(_mesh_lwip_sources ${_mesh_lwip_lib} SOURCES)
set(_mesh_napt_found FALSE)
set(_mesh_new_sources "")
foreach(_mesh_source IN LISTS _mesh_lwip_sources)
    if(_mesh_source MATCHES "(^|/)ip4_napt\\.c$")
        list(APPEND _mesh_new_sources "${_mesh_generated}")
        set(_mesh_napt_found TRUE)
    else()
        list(APPEND _mesh_new_sources "${_mesh_source}")
    endif()
endforeach()
if(NOT _mesh_napt_found)
    message(FATAL_ERROR "Cannot locate the SDK NAPT translation unit in lwip.")
endif()
set_property(TARGET ${_mesh_lwip_lib} PROPERTY SOURCES "${_mesh_new_sources}")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${_mesh_napt}" "${_mesh_ip4}" "${MESH_SYSTEM_ROOT}/tools/prepare_napt.py"
    "${MESH_SYSTEM_ROOT}/third_party/iot_bridge/patch/ip4_napt.patch")
message(STATUS "Mesh-Lite: IDF 6.1 NAPT compatibility from ${_mesh_generated}")
