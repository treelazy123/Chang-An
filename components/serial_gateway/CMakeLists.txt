idf_component_register(SRCS "serial_gateway.c" INCLUDE_DIRS "include"
    REQUIRES app_protocol esp_driver_usb_serial_jtag freertos log)
if(CONFIG_APP_ROLE_PC_ROOT AND
   (CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG OR CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG))
    message(FATAL_ERROR "pc_root reserves native USB for messages. Set console to UART0 and secondary console to None.")
endif()
