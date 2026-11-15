# 原始实验与兼容材料

本目录保留硬件记录、实验数据等原始材料，不承载当前固件或 UGV 运行时代码。材料中的版本、命令和绝对路径只描述当时环境；当前入口统一见 [文档索引](../docs/README.md)。

legacy TCP 固件保留在 `firmware/components/transport_tcp/`。`lab.py` 默认 transport 仍是 legacy，当前 TLS/MQTT 操作必须明确指定 `--transport mqtt_serial`。旧三节点角色或 TCP 9000/9001 教程不作为当前系统的启动依据。
