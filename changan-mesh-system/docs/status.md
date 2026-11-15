# 验收与部署状态

整理日期：2026-11-15。本页汇总已有验证和后续部署边界；历史测试数量、源码版本与日志路径只对应各自日期。

## 已有验证

| 项目 | 已有记录 |
| --- | --- |
| M1 基础任务 | 2026-11-14 通过 COM7、既有 Mesh-Lite 网络完成实物功能测试，覆盖配置版本、双 Micro 并行、排队、暂停/恢复、取消、完成和事件分页。 |
| 车机重连与排队 | 已有 Micro-001、Micro-002 追加复测记录，覆盖单节点单活动任务、车机退出重连继续执行、任务依次完成与样本统计。 |
| 车机 GUI / 网络结构 | 独立车机实现完成；界面、MAC 拓扑与模拟传输回归通过。 |
| 主机接口与部署配置 | 已有隔离 Broker、mTLS、逐节点 ACL、任务持久化及重启对账测试。 |

2026-11-15 网络显示实现阶段，主仓库 113 项回归通过，随后网络专项 7 项通过（其中 3 项为新增 USB 报告测试）；独立车机 29 项通过。测试使用模拟传输或临时 Broker，没有访问生产 COM 口，不构建或烧录固件。

## 待部署或另行验收

- 完整网络上报需要用户更新节点固件、桥接及后台；没有本次新增固件的编译、烧录或实物网络显示验收结论。
- 实际镜像分区、板载 Flash、运行堆/栈与 NVS 由用户编译和上板检查。
- 节点/USB/Broker/后台受控故障恢复需要记录对应源码、配置、日志、请求及实际结果；普通界面退出重连不能代替全部故障场景。
- Jetson ARM/Linux 实机、S31 驱动、USB 网络和实际 IP 路径仍待交付验收。
- 未测业务吞吐或单向时延写“未测”；单向时间比较需要明确同步方法和误差。

当前运行流程见 [运行说明](operations.md)，部署交接见 [部署说明](deployment.md)，验收操作见 [任务说明](tasks.md)。

## 原始验证记录

原始 JSON 统一保留于 legacy/verification，不作为当前启动指南，不因文档整理改写历史测试数据。

| 记录 | 范围 |
| --- | --- |
| [COM7 功能](../legacy/verification/verification-m1-hardware-com7.json) | 2026-11-14 常规功能测试 |
| [排队与车机重连](../legacy/verification/verification-m1-hardware-car-reconnect.json) | 当次原始结果 |
| [Micro-002 追加复测](../legacy/verification/verification-m1-hardware-car-reconnect-micro002.json) | 单节点任务与重连 |
| [Micro-001 追加复测](../legacy/verification/verification-m1-hardware-car-reconnect-micro001-retest.json) | 单节点任务与重连 |
| [仓库迁移](../legacy/verification/repository-migration-2026-11-14.json) | 源文件、身份、SQLite 与当时回归 |
| [平台解耦](../legacy/verification/platform-decoupling-2026-11-15.json) | 配置、接口及硬件验收边界 |
| [MQTT 串口阶段](../legacy/verification/verification-mqtt-serial.json) | 历史 MQTT/TLS 验证 |
| [身份阶段](../legacy/verification/verification-node-identity.json) | 受控身份验证 |
| [车机分离阶段](../legacy/verification/verification-car-separation.json) | 后台与车机职责分离 |
| [M1 主机阶段](../legacy/verification/verification-m1-tasks.json) | 任务管理验证 |
| [四节点阶段](../legacy/verification/verification-four-node.json) | 当时的四节点配置与检查 |

## 仓库迁移记录

2026-11-14 从保留源 D:/esp/mesh_lite_node 迁入当前主仓库，迁移前工作基线提交为 44201f7。当时核对 723 个源文件摘要、供应商源码、23 个已迁移密钥/证书及 SQLite 完整性；主机 102 项、车机 9 项及 8 组角色/传输声明检查通过。CMake 检查只解析路径，不执行 IDF 配置或 C 编译。

[源文件 SHA-256 清单](migration-source-manifest.json) 保留原内容，供应商字节保持检查继续引用它。原源工程保留，D:/changan/changan-mesh-lab 未用作迁移源或开发目标。迁移当时未切换生产服务、未构建/烧录固件；这些是当时的操作记录，不代表服务今天仍未运行。
