# 项目文档

当前拓扑：ugv-root（第1层）→ ugv（第2层）→ uav（第3层）→ micro_uav（第4层）。
独立终端通过本机 HTTP/WebSocket 连接 UGV Service，不加入 Mesh。

## 按工作查找

| 要做什么 | 统一入口 |
| --- | --- |
| 理解硬件、无线拓扑、程序职责和调用链 | [系统架构](architecture.md) |
| 启动程序、管理准入、指定 Micro 父节点、排障 | [运行手册](operations.md) |
| 登记身份、规划 AP 子网、构建烧录、处理旧缓存 | [固件与身份](firmware.md) |
| 创建和控制任务、诊断、验证 ESP32 测试流程 | [任务手册](tasks.md) |
| 硬件交接、迁移 Jetson、保留数据和凭据 | [部署与交接](deployment.md) |
| 查看回归结果及待完成的实物验收 | [验收状态](status.md) |
| 专门的不可信证书测试 | [TLS 负向测试](tls-negative-client.md) |

首次使用按“架构 → 固件准备 → 运行 → 任务”阅读；负向测试不用于正常部署。

## 协议与证据

- [HTTP/WebSocket v1](../protocols/http/v1/README.md)：终端与后台的版本化合同。
- [节点协议 v1](../protocols/v1/README.md)：MQTT/TLS、MUX1 与任务消息。
- [历史验证证据](../legacy/verification/)：带日期的原始记录，不是当前运行入口。

启动与排障集中在运行手册，构建与子网表集中在固件手册，任务参数与结果语义集中在任务手册。
协议目录保留线格式，各手册通过链接引用。
