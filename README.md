# Chang-An

长安项目代码仓库，包含两个相互独立、通过版本化协议通信的项目。

| 目录 | 内容 |
| --- | --- |
| [changan-car-terminal](changan-car-terminal/) | 独立 HTTP/WebSocket 车机终端、节点管理 GUI 与任务交互 CLI |
| [changan-mesh-system](changan-mesh-system/) | ESP32-C6 / ESP-IDF 固件、Mesh 网络与 UGV 主机服务 |

两个项目分别管理 Python 环境和依赖，请进入对应子目录，按照各自 README 执行。

当前拓扑为 ugv-root（第1层）→ ugv（第2层）→ uav（第3层）→ micro_uav（第4层）。
Jetson 根节点主机运行 UGV Service、Mosquitto 和 USB 桥接。车机通过 HTTP/WebSocket 访问后台，远程车机使用显式配置的受信局域网地址。节点控制与状态使用 MQTT/TLS，经根板 USB 隧道接入。
真实云端、5G 和独立业务数据通道仍为后续工作。

从 [文档索引](changan-mesh-system/docs/README.md) 开始，
Jetson 启动见 [启动指南](changan-mesh-system/docs/startup.md)，父节点设置见 [运行手册](changan-mesh-system/docs/operations.md)，
任务见 [任务手册](changan-mesh-system/docs/tasks.md)，
硬件及 Jetson 交接见 [部署说明](changan-mesh-system/docs/deployment.md)。

## 同步来源与验收

- Chang-An 集成基线为 `5239528`。主系统来源为 `89ccba5` 加本次工作区改动，独立终端来源为 `0dac917` 加本次工作区改动。
- 两端按 [HTTP/WebSocket v1](changan-mesh-system/protocols/http/v1/README.md)、[MCI v1](changan-mesh-system/protocols/mci/v1/README.md) 和 [能力公告测量 v1](changan-mesh-system/protocols/capability-measure/v1/README.md) 同步。
- 集成主机回归结果待填。Jetson 实机复验、固件构建与烧录、C6/S31 混合组网待验收。当前固件构建目标为 ESP32-C6。

下载的 Python 环境、运行缓存、本地 build 构建输出和 ZIP 不提交。已有第三方组件及其必要库/测试样例保留，用于复现现有工程；不包含本机新编译的固件。

仓库既有的 `changan-mesh-system/secrets/` 和 `changan-mesh-system/changan-runtime/` 含凭据与部署配置。本次新增的父节点认证登记文件通过受控部署渠道交接。
