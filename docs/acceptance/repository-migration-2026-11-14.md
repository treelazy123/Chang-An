# 仓库迁移与结构重构记录（2026-11-14）

## 结果

新主仓库：`D:changanchangan-mesh-system`；源工程 `D:espmesh_lite_node` 保留，723 个源文件逐一 SHA-256 核对未变。旧的 `D:changanchangan-mesh-lab` 没有作为迁移源或开发目标。独立车机仓库继续位于 `D:changanchangan-car-terminal`，未修改其源码。

新仓库先保存迁移前工作源码基线，提交 `44201f7`，随后完成结构迁移。源文件摘要在 `../migration-source-manifest.json`（从仓库根目录为 `docs/migration-source-manifest.json`）。

## 代码变化

- 一个 IDF 工程移至 `firmware/`；root、UGV、UAV、Micro 各有真正的应用启动入口。
- root 车机网关、UGV USB 隧道的实现分别放入对应 `apps/`。公共 MQTT 由角色传入 STA/SoftAP 入口选择。
- 诊断状态机和真实采样继续共享；删除只返回角色名的 task_agent 角色占位文件。
- 主机后台、节点管理、持久化任务、主机执行器、传输、维护界面进入 `host/src/changan_ugv/`，通过标准 editable Python 包安装。
- `tools/` 保留管理/验收工具和旧命令薄入口，原 `mqtt_terminal.py` 功能保留。
- 第三方依赖移至 `third_party/`，源码逐文件哈希保持，许可证与历史版本/补丁资料保留。
- 受控登记移至 `config/`，运行状态移至 `runtime/`；协议合同和固定样例放入 `protocols/v1/`。
- 历史文档/验收证据与实验资料分区保存。当前启动步骤见 [主机启动说明](../bringup/host.md)。

本次不增加勘察、巡防、媒体、飞控或其他具体场景接口。

## 验证

| 检查 | 结果 |
| --- | --- |
| 原有 95 项主机回归 | 通过 |
| 新增 7 项迁移、协议、状态交接回归 | 通过 |
| 独立车机原有 9 项测试 | 通过 |
| 四角色 × MQTT/legacy 的 CMake 声明路径检查 | 8 组通过 |
| 四个旧 CLI 的 --help | 通过 |
| root/UGV/UAV/Micro-001/Micro-002 配置 dry-run | 5 组通过 |
| 供应商源码字节保持、原源工程未变 | 通过 |
| 已迁移密钥/证书保持及 SQLite 完整性 | 通过 |

隔离 Broker 测试使用临时证书和端口，没有连接生产设备。CMake 检查仅以 stub 解析所声明的源码和证书文件路径，不是 IDF 配置或 C 语言编译验证。构建产物与 `.venv` 未从源工程复制，已在新目录建立 uv 环境。

日志位于忽略提交的 `build/migration-host-tests.log`、`build/migration-car-tests.log`，摘要随本文件旁的 JSON 保存。

## 运行状态与后续验证

已保留原证书及迁移时的 SQLite 一致快照，证书不重新签发。生产 Broker、UGV 后台、USB 桥接、COM7 车机程序均未切换或重启。源服务若在快照后继续处理任务，应退出旧服务后运行 `tools/sync_runtime.py --source D:espmesh_lite_node` 再启动新目录服务。该工具有源/目标 controller 排他检查、SQLite backup 和目标旧状态备份；不会自动停止任何服务。

未执行固件 build/flash，用户需在新目录编译后验证四角色固件。硬件 M1 稳定性没有因本次重构而重新判定；此前 Micro-001 在用户无操作时 uptime 回退的异常仍未定位，需下一轮读取 reset reason 与崩溃日志。
