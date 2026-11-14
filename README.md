> 0.7.0：新增 M1 基础任务管理、SQLite 持久化、诊断任务代理和角色模块分离。独立车机支持 task/watch，原诊断接口保留。升级与验收见 [M1 说明](docs/m1-task-management.md)。新固件尚未由代理编译/烧录。

> 0.6.0：新增UGV无界面后台 `tools/ugv_service.py`，独立车机仓库位于 `D:/changan/changan-car-terminal`，旧mqtt_terminal兼容保留。启动及用户root固件升级见 [车机与后台分离](docs/car-terminal-separation.md)。未自动build/烧录或重启服务。

> 0.5.0：所有角色支持显式 `--node-id`、独立证书和按设备隔离构建；新增设备由受控清单管理，详见 [通用设备身份与烧录](docs/device-identity.md)。MQTT真实操作现在必须明确指定编号。UGV隧道默认8通道，新版需要用户编译/烧录与重启主机程序。

> 主机 Python 环境使用 **uv**：在项目目录执行 `uv sync --locked`，然后用 `uv run --locked python tools/mqtt_terminal.py` 等命令运行主机工具。依赖锁定于 `uv.lock`，环境位于 `.venv`；固件构建继续使用 ESP-IDF 自身环境。

> 2026-11-13 新增 MQTT 双向 TLS 实验模式：电脑通过 UGV C6 原生 USB 串口透明隧道运行 Broker，root 使用 UGV STA，UAV/Micro 使用 UGV SoftAP。构建与启动步骤见 [MQTT 串口实验](docs/mqtt-serial-bringup.md)。旧模式仍为默认。此轮未 build／烧录，硬件与 Mosquitto 集成待验收。

# 长安四节点 Mesh-Lite：UGV 汇聚与 PC 串口终端

目标平台：**ESP32-C6 / ESP-IDF 6.1.x**。四块 C6 共用一套固件源码，版本 `0.3.0`。PC 与 root C6 通过 **原生 USB Serial/JTAG** 通信。

无线拓扑与 TCP 连接分别配置：

```text
无线链式拓扑：
PC ←原生 USB→ pc_root C6（1层）↔ UGV C6（2层）↔ UAV C6（3层）↔ Micro C6（4层）

应用连接：
UAV   ──TCP :9001──→ UGV ──TCP :9000──→ pc_root C6 ←USB串口→ PC程序
Micro ──TCP :9001──→ UGV
```

Micro 的 TCP 终点是 UGV；在 chain 中无线数据仍经过 UAV。UGV 汇聚自己和两个下游节点的消息，root C6 再转给 PC。PC 命令按目标 `node_id` 经 root、UGV 返回对应节点。这里是两段 TCP 与一段串口业务链路。

| 构建角色 | 默认 node_id | chain 层级 | 应用职责 |
| --- | --- | --- | --- |
| `pc_root` | `pc-root-001` | 1 | 固定 Mesh root、TCP 9000 服务端、原生 USB 网关 |
| `ugv` | `ugv-001` | 2 | TCP 9001 服务端、连接 root 的客户端、业务汇聚 |
| `uav` | `uav-001` | 3 | 连接 UGV 的 TCP 客户端，同时做无线中继 |
| `micro_uav` | `micro-001` | 4 | 连接 UGV 的 TCP 客户端、无线叶子 |

## 构建与烧录

在 ESP-IDF 6.1 终端进入本目录后手动运行：

```powershell
python tools/lab.py --role pc_root --topology chain build
python tools/lab.py --role ugv --topology chain build
python tools/lab.py --role uav --topology chain build
python tools/lab.py --role micro_uav --topology chain build
```

本机普通 PowerShell 也可以使用安装器的 Python：

```powershell
& 'C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe' tools/lab.py --role pc_root --topology chain build
```

脚本只读取 EIM 的静态环境配置，不执行激活脚本，不需要改变 PowerShell 执行策略。其他安装位置可通过 `IDF_TOOLS_PATH` 指定 EIM 工具目录。

新配置和产物位于 `build/four-node/<角色>-<拓扑>/`，例如 `build/four-node/pc_root-chain/mesh_lite_node.bin`。旧三节点 `build/ugv_root-*` 等目录保留，仅作为历史产物。原 `ugv_root` 构建角色已由独立的 `pc_root` 与 `ugv` 取代。

使用实际板子的串口号分别烧录。COM7 只是占位示例：

```powershell
python tools/lab.py --role pc_root --topology chain --port COM7 flash
```

其他板更换 `--role` 和 `--port`。`--dry-run` 仅打印参数；`menuconfig` 修改独立配置。defaults 顺序为共用→角色→拓扑→可选 `sdkconfig.local.defaults`，已有 sdkconfig 优先，改 defaults 后需同步 menuconfig。新架构检查版本 2 与最大层数 4，避免混用旧缓存。

## PC 串口程序

root C6 的**原生 USB**口连接 PC。该接口专用于二进制业务帧；root 普通日志保留在 UART0，关闭 USB 副控制台。不要把板载 USB 转 UART 的接口当成此业务口，也不要让 monitor 与 PC 程序同时占用同一 COM 口。

```powershell
python -m pip install -r tools/requirements-pc.txt
python tools/pc_terminal.py --list-ports
python tools/pc_terminal.py --port COM7
```

交互命令：

```text
list
ping pc-root-001
ping ugv-001
ping uav-001
ping micro-001
status micro-001
echo micro-001 你好，链路测试
quit
```

也可单次查询：

```powershell
python tools/pc_terminal.py --port COM7 --command "ping micro-001"
```

交互模式输出在线/离线事件和目标节点回执，后台消息只在输入完成后显示，不打断正在输入的命令。连续查看遥测使用 `python tools/pc_terminal.py --port COM7 --monitor`（Ctrl+C 退出后再使用交互模式）。`list` 查询 UGV 当前真实 TCP 会话并加入 root；它不代表所有节点的无线关联表。超时默认 5 秒，不自动重发命令。`ping/status/echo` 是通信测试，不操作飞控、车机执行器或传感器。

## 地址发现与拓扑

UGV 通过 Mesh-Lite 公告自己的 **STA 地址**和 9001 端口，root 和中继向下分发，记录 15 秒失效时间。UAV/Micro 不使用各自的默认网关代替 UGV 地址。UGV 位于第 2 层时直接使用 DHCP 网关连接 root 的 9000；其他层级使用 `esp_mesh_lite_get_root_ip()`，并对本地 1.0.2 核心返回的主机字节序做转换。固定 chain 的第 3 层 UAV 可直接连接 UGV 网关的 9001，Micro 始终使用公告发现 UGV。

所有板共用 Mesh ID 77、信道 6、实验密码 `changan-lab-only`。默认没有外部路由器，PC 不需要开热点或连接 Wi-Fi。

`chain` 固定 1/2/3/4 层，便于证明路径。`star` 让三台车辆节点位于第 2 层；`auto` 允许非根节点自动选父，micro 始终为叶子。三种配置的应用连接都保持 UAV/Micro→UGV→root。若公告尚不可用，可在 menuconfig 设置 `APP_UGV_IP_OVERRIDE` 或 `APP_ROOT_IP_OVERRIDE`；地址须取自当前日志，不能照抄网关示例。

## 代码与验证

- `components/node_role/`：四种身份与拓扑层级。
- `components/network_mesh_lite/`：启动和组网状态日志。
- `components/app_protocol/`：长度、CRC、JSON 校验及测试命令。
- `components/service_discovery/`：UGV 地址公告与过期。
- `components/transport_tcp/`：两级 TCP 会话、注册、心跳和转发。
- `components/serial_gateway/`：root 原生 USB 收发和有界队列。
- `tools/pc_terminal.py`：PC 终端；`tools/mesh_protocol.py`：主机协议。

SDK 不会被修改，第三方依赖随工程保存，Component Manager 关闭。应用分区为 `0x1f0000` 字节，布局适合 2 MiB Flash，NVS/PHY 偏移保留。仍需用户编译后检查实际镜像与可用内存。

**本轮按用户要求未运行固件构建，也未烧录或上板验证。** 已运行 18 项纯主机测试（包含 12 组角色/拓扑参数的 dry-run）；这些结果不能替代固件编译和真实四板验收。旧版本编译结果不适用于当前源码。

详细操作见 [四板上电验证](docs/bringup.md)，协议见 [通信协议](docs/protocol.md)，架构见 [架构说明](docs/architecture.md)，6.1 兼容来源见 [迁移记录](docs/migration-idf61.md)。原三节点文档保存于 `docs/archive/three-node-2026-11-10/`。


## 2026-11-11 TCP 地址与终端修正

修正旧代码对 Mesh-Lite 1.0.2 非根 root IPv4 返回值的字节序处理，避免把 192.168.5.1 连接成 1.5.168.192。UGV 第2层直接使用当前 DHCP 网关，不硬编码地址；chain 下 UAV 第3层可使用 UGV 父网关，Micro 不使用其 UAV 网关代替 UGV。

新增 TCP_WAIT/TCP_CONNECT/TCP_CONNECT_FAILED/TCP_HELLO/TCP_ACCEPT 与注册拒绝日志，失败时保留 errno。PC 交互终端默认不刷遥测，--monitor 独立显示。纯主机回归测试更新为 21 项通过；本次仍未代跑固件构建或设备操作。
