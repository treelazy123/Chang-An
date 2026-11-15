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
| `docs/` | 当前架构、运行、固件、任务、部署与验收说明 |
| `legacy/verification/` | 保留原内容的验证 JSON 记录 |
| `legacy/` | 原始实验与硬件材料，兼容模式仅供历史核对 |
| `runtime/`、`secrets/`、`build/` | 忽略提交的状态、密钥和生成文件 |

在仓库根目录执行：

```powershell
uv sync --locked
uv run --locked python tools/run_tests.py
```

从 [文档索引](docs/README.md) 开始；日常启动见 [运行与排障](docs/operations.md)，代码边界见 [系统架构](docs/architecture.md)。

ESP-IDF PowerShell 环境启动及各角色烧录命令见 [固件与设备身份](docs/firmware.md)。

车机桌面界面在独立仓库运行：

```powershell
cd D:\changan\changan-car-terminal
uv sync --locked
uv run --locked python -m car_terminal.gui --port COM7
```

提供节点调试、诊断任务、结果导出和网络结构显示。完整 IP/MAC/父子关系依赖新增固件状态上报；固件编译与烧录由用户执行。已有验证与部署边界见 [验收状态](docs/status.md)。
