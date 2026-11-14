# Chang-An

长安项目代码仓库，包含两个相互独立、通过版本化协议通信的项目。

| 目录 | 内容 |
| --- | --- |
| [changan-car-terminal](changan-car-terminal/) | 车机终端、串口及 MQTT 传输、任务交互 CLI |
| [changan-mesh-system](changan-mesh-system/) | ESP32-C6 / ESP-IDF 固件、Mesh 网络与 UGV 主机服务 |

两个项目分别管理 Python 环境和依赖，请进入对应子目录，按照各自 README 执行。

本仓库不包含设备私钥、`secrets/`、`runtime/`、虚拟环境及本地构建输出。设备证书和本地配置需按各项目文档单独准备。
