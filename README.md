# Chang-An

长安项目代码仓库，包含两个相互独立、通过版本化协议通信的项目。

| 目录 | 内容 |
| --- | --- |
| [changan-car-terminal](changan-car-terminal/) | 独立 HTTP/WebSocket 车机终端、节点管理 GUI 与任务交互 CLI |
| [changan-mesh-system](changan-mesh-system/) | ESP32-C6 / ESP-IDF 固件、Mesh 网络与 UGV 主机服务 |

两个项目分别管理 Python 环境和依赖，请进入对应子目录，按照各自 README 执行。

当前拓扑为 ugv-root（第1层）→ ugv（第2层）→ uav（第3层）→ micro_uav（第4层）。
根节点主机暂用电脑，运行 UGV Service、Mosquitto 和 USB 桥接，后续迁移至 Jetson。
汽车终端不加入 Mesh，通过本机 HTTP/WebSocket 访问后台；节点控制与状态使用 MQTT/TLS。
真实云端、5G 和独立业务数据通道仍为后续工作。

从 [文档索引](changan-mesh-system/docs/README.md) 开始，
启动和父节点设置见 [运行手册](changan-mesh-system/docs/operations.md)，
任务见 [任务手册](changan-mesh-system/docs/tasks.md)，
硬件及 Jetson 交接见 [部署说明](changan-mesh-system/docs/deployment.md)。

本次同步来源：主系统 `89ccba5`，独立终端 `0dac917`。
主系统 160 项、独立终端 49 项回归通过；主机回归不替代实物验收。

下载的 Python 环境、运行缓存、本地 build 构建输出和 ZIP 不提交。已有第三方组件及其必要库/测试样例保留，用于复现现有工程；不包含本机新编译的固件。

`changan-mesh-system/secrets/` 包含现有 CA 和设备真实私钥
`changan-mesh-system/changan-runtime/` 包含 Jetson 部署所需凭据及配置。
