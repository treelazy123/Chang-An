# Changan Mesh System

无人车根节点自组网与任务管理系统。唯一当前拓扑为：ugv-root（第1层）→ 普通无人车
（第2层）→ 无人机（第3层）→ 微型无人机（第4层）。汽车终端不参与 Mesh。

开发阶段，独立车机终端通过本机 HTTP/WebSocket 直接连接 UGV Service。后台、Mosquitto
和 USB 桥接运行在电脑上，后续迁移至根节点无人车的 Jetson。控制/状态采用 MQTT/TLS；
业务数据另设通道。真实云端与 5G 接入尚未实施，不增加模拟云端服务。

| 路径 | 职责 |
| --- | --- |
| firmware/apps/ | ugv_root、ugv、uav、micro_uav 的角色入口 |
| firmware/components/ | 组网、服务发现、JSON控制协议、MQTT、执行器 |
| host/src/changan_ugv/ | HTTP/WS、节点准入与管理、任务调度和持久化 |
| config/nodes.json | 唯一受控节点清单，schema 2 |
| config/ugv-root.dev.toml | 电脑开发部署配置 |
| protocols/ | 节点控制与 HTTP/WebSocket 协议合同 |
| tools/ | 构建、身份与部署管理工具 |
| third_party/ | 固件依赖、版本和许可证 |
| secrets/ | 已登记凭据；不得重新生成或覆盖已有密钥 |
| changan-runtime/ | 根节点部署交接配置与已保留凭据 |
| legacy/verification/ | 带日期的原始验收证据，不是运行入口 |

```powershell
uv sync --locked
uv run --locked python tools/run_tests.py
```

从 [文档索引](docs/README.md) 开始，启动见 [运行说明](docs/operations.md)，
编译与用户烧录见 [固件说明](docs/firmware.md)，源码边界见 [系统架构](docs/architecture.md)。
独立车机代码在 `../changan-car-terminal`；两个程序只通过协议交互，不跨仓库导入源码。
现场状态保存在未跟踪的 `runtime/ugv-root/`，构建产物在 `build/`。
