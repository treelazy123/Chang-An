# Chang-An

长安项目代码仓库，包含两个相互独立、通过版本化协议通信的项目。

| 目录 | 内容 |
| --- | --- |
| [changan-car-terminal](changan-car-terminal/) | 车机终端、串口及 MQTT 传输、任务交互 CLI |
| [changan-mesh-system](changan-mesh-system/) | ESP32-C6 / ESP-IDF 固件、Mesh 网络与 UGV 主机服务 |

两个项目分别管理 Python 环境和依赖，请进入对应子目录，按照各自 README 执行。

Jetson / S31 同学从 [交接说明](changan-mesh-system/docs/handoff/README.md) 开始，按步骤完成 S31 组网与 USB 网卡改造、两块 C6 烧录、Jetson 部署和端到端验收。UAV C6 当前仅为独立通信测试板。

下载的 Python 环境、运行缓存、本地 build 构建输出和 ZIP 不提交。已有第三方组件及其必要库/测试样例保留，用于复现现有工程；不包含本机新编译的固件。
