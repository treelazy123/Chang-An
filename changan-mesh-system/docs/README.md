# 文档索引

维护日期：2026-11-15。当前平台为 ESP32-C6 / ESP-IDF 6.1.x，业务范围为 M1 通用 `diagnostics` 任务管理。

| 文档 | 内容 |
| --- | --- |
| [系统架构](architecture.md) | 仓库职责、无线与业务链路、主机接口、运行数据 |
| [运行与排障](operations.md) | Broker、USB 桥接、后台、车机 GUI/CLI、网络结构与常见故障 |
| [固件与设备身份](firmware.md) | SDK、角色、增量登记、独立构建、用户烧录、兼容层 |
| [任务操作](tasks.md) | diagnostics、CLI、任务接口、版本、排队、暂停与故障恢复 |
| [部署与交接](deployment.md) | 配置文件、状态迁移、ACL、Jetson 与 S31 交付边界 |
| [Jetson / S31 同学交接任务](handoff/README.md) | 电脑车机 C6—Jetson S31—UAV C6、部署步骤、服务发现兼容点和 H0–H7 验收 |
| [验收与部署状态](status.md) | 已有验证、原始记录和待部署/验收边界 |
| [协议 v1](../protocols/v1/README.md) | MLT1、MQTT 主题、网络字段、MUX1 网络报告及任务合同 |

线协议只在 `protocols/v1/` 维护。原始验收 JSON 位于 `legacy/verification/`，源文件摘要在 [迁移清单](migration-source-manifest.json)；它们是带日期的证据，不是当前启动指南。第三方版本与许可证保留在 `third_party/`，实验原始材料保留在 `legacy/`。

旧版本 README、三节点说明、旧 TCP 启动教程、分散的迁移记录和重复设计稿已合并删除。当前命令以本索引链接的文档为准；各项验收的适用版本和范围见状态页。
