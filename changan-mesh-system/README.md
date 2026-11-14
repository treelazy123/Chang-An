# Changan Mesh System

一个 ESP-IDF 6.1 固件工程，按 root / UGV / UAV / Micro UAV 分离角色；UGV 主机程序独立成 Python 包。当前业务范围是 M1 基础任务管理，执行类型只有真实资源/链路采样 `diagnostics`。

车机终端保留在相邻的独立仓库 `../changan-car-terminal`。两个仓库通过版本化协议交互，不互相导入业务源码。

| 目录 | 内容 |
| --- | --- |
| `firmware/apps/` | 四种角色的启动与角色专属代码 |
| `firmware/components/` | 自研共享组网、MQTT、任务、协议组件 |
| `firmware/configs/` | 角色和拓扑默认配置 |
| `host/src/changan_ugv/` | UGV 服务、节点管理、任务管理、主机执行器和传输 |
| `host/tests/` | 主机业务及隔离 Broker 测试 |
| `tools/` | 构建、身份管理、验收工具及旧命令兼容入口 |
| `protocols/v1/` | 当前线协议合同与固定样例 |
| `third_party/` | 本地第三方组件、许可证、版本及历史补丁信息 |
| `config/nodes.json` | 受控设备登记，禁止从网络公告自动授予权限 |
| `docs/architecture/` | 当前边界与接口说明 |
| `docs/bringup/` | 当前启动步骤 |
| `docs/acceptance/` | 验收报告与原始证据 |
| `docs/archive/`、`legacy/` | 历史设计、实验和硬件记录 |
| `runtime/`、`secrets/`、`build/` | 忽略提交的状态、密钥和生成文件 |

在仓库根目录执行：

```powershell
uv sync --locked
uv run --locked python tools/run_tests.py
```

启动与迁移交接见 [运行说明](docs/bringup/host.md)，代码边界见 [仓库结构](docs/architecture/repository.md)，本次变更见 [迁移记录](docs/acceptance/repository-migration-2026-11-14.md)。旧的 `tools/ugv_service.py`、`tools/serial_tcp_bridge.py`、`tools/mqtt_terminal.py` 命令继续可用。

本次未运行固件编译或烧录，也未切换正在运行的硬件服务。Micro-001 曾出现的无操作重启仍需单独排查。
