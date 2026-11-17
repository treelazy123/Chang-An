# 运行与排障

适用主仓库 `D:\changan\changan-mesh-system`，独立车机仓库 `D:\changan\changan-car-terminal`。固件与身份准备见 [固件说明](firmware.md)，跨目录切换见 [部署与交接](deployment.md)。

## 主机环境

```powershell
cd D:\changan\changan-mesh-system
uv sync --locked
uv run --locked python tools/run_tests.py
uv run --locked python tools/provision_mqtt.py --list
```

主机测试允许启动临时、隔离端口的 Broker，不连接生产 Broker 或 COM 口，不执行固件构建。`provision_mqtt.py` 不带参数是首次创建 CA；已有身份的环境应使用 `--list`、`--role ... --node-id ...` 或 `--sync-acl`，保留现有密钥。

固件编译/烧录使用独立的 ESP-IDF PowerShell 环境；环境启动脚本、五块板的烧录命令与只预览不执行的方法统一见 [固件与设备身份](firmware.md)。

## 三个主机进程

分别打开三个 PowerShell 窗口，均进入主仓库。先确认没有同一端口或身份的旧实例，再按顺序启动。现有其他 Mosquitto 服务不属于此项目的切换目标。

Broker：

```powershell
cd D:\changan\changan-mesh-system
& 'D:\Program Files (x86)\Mosquitto\mosquitto.exe' -c 'D:\changan\changan-mesh-system\runtime\mosquitto.conf' -v
```

UGV C6 原生 USB 桥接：

```powershell
cd D:\changan\changan-mesh-system
uv run --locked python tools/serial_tcp_bridge.py --port COM4 --broker-port 8883 --ugv-id ugv-001
```

UGV 常驻后台：

```powershell
cd D:\changan\changan-mesh-system
uv run --locked python tools/ugv_service.py --broker-port 8883 --ugv-id ugv-001
```

COM4 是此前 UGV 的端口，COM7 是此前 root 的端口，COM5 是此前 UAV 的端口；重新枚举后应核对实物。每个 COM 口只能由一个桥接、车机或串口监视程序占用。root 与 UGV 的原生 USB 用于二进制业务，UART0 输出日志。

主机包也提供 `uv run --locked ugv-service`、`ugv-serial-bridge`、`ugv-console` 入口。后台默认持久化 `runtime/tasks.sqlite3` 和 `runtime/ugv-task-agent.json`；关闭界面不停止后台任务。不要通过删除数据库或 journal 来重启服务。

## 车机图形界面与 CLI

```powershell
cd D:\changan\changan-car-terminal
uv sync --locked
uv run --locked python -m car_terminal.gui --port COM7
```

界面打开后手动点击“连接”，再点“刷新节点”。节点页提供 Ping、状态、Echo；任务页提供创建、查询、开始、暂停、恢复、取消和事件补查；结果区显示 JSON、错误、时间与耗时，可导出最近 2000 条结果为 JSONL。

同一个 root 串口不同时运行 GUI 和 CLI。需要命令行时先退出或断开 GUI：

```powershell
uv run --locked python -m car_terminal --port COM7
```

基本命令为 `list`、`ping NODE`、`status NODE`、`echo NODE TEXT`；任务操作见 [任务说明](tasks.md)。车机只使用自己的身份，不保存 CA 私钥或 `controller-001` 管理员私钥。当前车机实现和说明位于 [独立仓库](../../changan-car-terminal/README.md)。

主机本地维护终端优先复用已运行后台，避免重复使用 `controller-001`：

```powershell
cd D:\changan\changan-mesh-system
uv run --locked python tools/mqtt_terminal.py --broker-port 8883
```

## 网络结构页

连接后进入“网络结构”，点击“刷新网络结构”。与“刷新节点”使用同一个只读 list 请求，显示：

- 节点树、角色、Mesh 层级与就绪状态。
- STA/AP IP、网关、RSSI、信道、Wi-Fi 关联客户端数、遥测年龄。
- 选中节点后的 STA/AP MAC、父 BSSID、子网掩码，并同步调试目标。

横向滚动可查看全部列。父子关系只按实际父 BSSID 匹配唯一的 AP MAC；外部 AP、未知父节点、断开、旧启动、重复 MAC 和关系环分别显示。灰色数据为未就绪快照；查询结果不是持续探测，断开后保留的旧值不表示设备仍在线。

完整 IP/MAC 等数据需要用户编译、烧录带网络状态上报的新固件。旧固件已有层级仍可显示，其余字段标为“未上报”。UGV C6 通过经协商的 USB 只读报告提供自身无线状态；桥接程序保存 `runtime/ugv-network.json`，后台将其加入 list 响应。主机任务服务与 UGV C6 无线设备的就绪状态分别判断。

仓库默认桥接与后台使用同一运行根目录。桥接自定义 `--network-status` 时，该路径应对应后台运行根目录的 `runtime/ugv-network.json`。非默认 UGV 编号用 `--ugv-id` 指明。字段与协商规则见 [协议](../protocols/v1/README.md)。

## 常见故障

| 现象 | 检查与处理 |
| --- | --- |
| 无法打开 COM / Access denied | 退出占用同一口的 CLI、GUI、monitor 或旧桥接；确认端口重新枚举后的编号。不要启动多个实例反复抢占。 |
| Broker 地址连接拒绝 | 检查项目 Broker 是否监听配置的 8883，以及桥接与后台端口是否一致。不要把其他项目的 1883/9883 服务当成本项目实例。 |
| 节点出现在列表但 `ready=false` | 需要同一 boot 的 presence、能力及新鲜 telemetry；单个 retained 在线声明或 Wi-Fi 关联不足以证明业务就绪。 |
| 网络层级正常但任务失败 | 检查目标 diagnostics 能力、任务错误及版本；Wi-Fi 入网、MQTT 就绪、任务完成是不同阶段。 |
| IP/MAC 未上报 | 核对新固件是否真正烧录；UGV 还需要新版桥接及有效 USB 报告。不要填入示例 IP。 |
| `revision_conflict` | 重新查询当前任务再决定控制操作，不覆盖版本、不自动重发。 |
| ESP-IDF 面板无法启动 | 用 VS Code 单独打开 `D:\changan\changan-mesh-system\firmware`，执行 `Developer: Reload Window`。仓库根目录面向 uv，根目录的 `cmake.sourceDirectory` 不能替代 ESP-IDF 工程识别。 |

只枚举端口而不打开设备：

```powershell
uv run --locked python -m serial.tools.list_ports -v
```
