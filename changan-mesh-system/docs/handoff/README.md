# 电脑车机 C6 — Jetson S31 — UAV C6 交接说明

按这一份文档完成部署、开发和验收。目标是电脑运行车机，Jetson 运行消息中转站和业务后台，S31 把两块 C6 接入 Jetson。UAV C6 目前只是独立通信测试板，不连接真实无人机，不开发飞控、图像或视频接口。

阅读顺序：

1. [交接目标与复用范围](#1-交接目标与复用范围)
2. [S31 组网复用和 USB 重构](#2-s31-组网复用和-usb-重构)
3. [两块 C6 编译烧录](#3-两块-c6-编译烧录)
4. [Jetson 部署操作](#4-jetson-部署操作)
5. [电脑车机与端到端测试](#5-电脑车机与端到端测试)
6. [验收和交回记录](#6-验收和交回记录)
7. [排错与停止方法](#7-排错与停止方法)

可先按第 4 节启动 Jetson 本机服务，再完成 S31 接入并按第 5 节联调。命令中的 COM7、COM5 和 USB IP 都需要替换为实际值。

## 1 交接目标与复用范围


| 部分 | 接收方怎么做 |
| --- | --- |
| 电脑车机 GUI/CLI | 直接使用 changan-car-terminal，安装依赖后运行，不需要重写 |
| 车机侧 C6 | 直接复用现有 pc_root / mqtt_serial 固件源码，按 pc-root-001 的身份编译并烧入对应板 |
| UAV 侧 C6 | 直接复用现有 uav / mqtt_serial 源码，按 uav-001 编译并烧入独立 C6 测试板；无需无人机接口代码 |
| Jetson Broker | 安装 Linux 版 Mosquitto，重新生成 Linux 路径的配置，不改 Broker 源码 |
| Jetson 业务后台 | 直接复用 host/src/changan_ugv，安装 Linux 依赖并配置路径，不重写任务业务 |
| S31 | 复用组网流程、角色和公告协议，适配芯片依赖与 USB 网卡；本轮主要开发工作在这里 |

两块 C6 源码保持不改的条件是：S31 保留现有组网/服务公告，公告的两个入口都能到达 Jetson。两块板分别编译、分别烧录，不能共用同一份带身份的固件。仓库包含固件源码，不提交本地编译生成的 bin；具体步骤见 [第 3 节](#3-两块-c6-编译烧录)。

### 业务链路与固定身份


```text
电脑 GUI/CLI --USB/MLT1--> 车机 C6 (pc-root-001)
                             |
                       Mesh / S31 入口
                             |
                         USB IP 接口
                             |
Jetson: Mosquitto mTLS :8883 <--> UGV 后台 (controller-001)
                             |
                 MQTT/TLS 经 S31 / Mesh
                             |
                        UAV C6 (uav-001)
```

图示是业务路径；无线父子关系必须以实测父 BSSID/AP MAC 为准。当前 C6 chain 基线的预期层级为 root=1、UGV=2、UAV=3；本轮 S31 承担中间网络接入职责。S31 是否可承担相同 Mesh 角色和层级，必须单独验证。

| 项目 | 本轮约定 |
| --- | --- |
| 车机 USB | 历史端口 COM7，使用前枚举并核对实物 |
| 车机业务身份 | pc-root-001，由车机 C6 证书绑定；电脑串口客户端不自行持有管理员身份 |
| UAV 身份 | uav-001；替换设备时先确认登记及相应 ACL |
| UGV 逻辑身份 | ugv-001；Jetson 后台 MQTT 登录身份为 controller-001 |
| Broker | Jetson，MQTT 3.1.1 / 双向 TLS，端口默认 8883 |
| TLS 服务名 | ugv-broker.lab，连接 IP 可以不同，不能关闭服务名校验 |
| 维护 RPC | 仅 Jetson 回环接口 127.0.0.1:8787 |
| S31 | 默认承担网络职责；如新增管理 MQTT 客户端，单独分配身份与权限 |

同一个 controller-001 不得同时运行在旧电脑后台和 Jetson；切换由部署方安排。车机 GUI 与 CLI 不同时占用同一个串口。

## 2 S31 组网复用和 USB 重构

保留电脑到车机 C6 的 USB/MLT1 串口；把旧 UGV 的 USB/MUX1 字节隧道替换成 S31 USB 网卡。两块 C6 的通信和 diagnostics 代码继续使用。本节是接收方待实现的 S31 开发内容。

### 1 从这些现有文件开始复用

以下路径均相对 changan-mesh-system。

| 文件/目录 | 保留什么 | S31 上修改什么 |
| --- | --- | --- |
| firmware/components/network_mesh_lite/mesh_start.c | 初始化 NVS、网络、Wi-Fi STA/AP、组网启动和事件处理的流程 | 使用 S31 支持的 SDK/API/组件；增加 USB 网络接口；日志中的 esp32c6 改为实际芯片 |
| firmware/components/network_mesh_lite/mesh_status.c | 父节点、层级、IP/MAC、RSSI 等状态字段 | 调整 S31 API 差异，保留字段含义 |
| firmware/components/node_role/ | root=1、UGV=2、UAV=3 的 chain 角色与层级 | S31 选择 UGV 网络角色、node_id=ugv-001，不选择 root |
| firmware/components/service_discovery/ | 告诉两块 C6 “去哪个地址连接消息服务” | 保留现有消息类型、字段、周期与过期规则，让地址指向 S31 可转发的入口 |
| firmware/components/app_protocol/ | 公告辅助方法、状态与 JSON 字段规则 | 按依赖需要编入；这部分也依赖 Mesh/Wi-Fi，不是纯 JSON 独立库 |
| firmware/apps/ugv/app.c | 启动服务公告后再启动数据入口的装配顺序 | 把 serial_tunnel_start 换成 USB 网络和转发组件的启动 |
| firmware/apps/ugv/serial_tunnel.c | TCP 接收、缓冲、分段写入、连接超时与断开处理可参考 | 删除 S31 路径中的 MUX1/USB串口读写，改成 TCP↔TCP 转发，见本节第 3 步 |

组网参数对齐现有两块 C6：Mesh ID、信道、SoftAP 密码、拓扑、层级和 UGV 编号一致。参数来源为 `firmware/sdkconfig.defaults`、`firmware/configs/topologies/chain.defaults`、`firmware/main/Kconfig.projbuild` 和各角色配置；不要复制生成目录里的旧 sdkconfig 覆盖新板配置。

#### 不能直接复制构建的部分

现有 `firmware/CMakeLists.txt` 只允许 esp32c6 / IDF 6.1。`third_party/mesh_lite/CMakeLists.txt` 需要按芯片链接预编译库，但当前 `third_party/mesh_lite/lib/` 没有 S31 对应库；缺少的库需要从支持 S31 的组件实现获取，不能把 C6 库改名使用。

当前 `third_party/iot_bridge` 已有 `src/bridge_usb.c` 可参考 USB 网络接法，但 Kconfig 的 USB 选项只允许 S2/S3，构建依赖也只对 S2/S3添加 TinyUSB。S31 需要实际适配 USB 控制器、网络类和组件依赖，不能只打开该选项就当作完成。

`firmware/cmake/mesh_lite_idf61.cmake` 是当前 IDF 6.1 的 NAPT 补丁装配，不能直接套用到另一套 SDK。`tools/lab.py` 继续用于现有 C6；不把它的默认 target 改成 S31。

实施方式：在支持 S31 的 SDK 工程中引入上述可复用模块；后续如合回本仓库，可放在 `platform/s31/` 并写清启动入口。S31 的板级工程与 C6 的 `firmware/` 构建隔离，避免影响现有 C6 编译。此目录是建议结构，仓库中尚未实现。

### 2 先把 USB 做成网卡

在 S31 上增加 USB 网络组件，例如 `usb_network`（建议名称，不是现有函数）：

1. 初始化 USB 网络设备及相应网络接口，使 Jetson 能识别出网卡。
2. 配置 S31 的 USB 侧 IP 与 Jetson 对端 IP。可先用固定地址，两端同网段且不得与 Mesh 各层网段冲突。
3. 在 Jetson 用 `ip -br address` 确认网卡和地址；两端测试收发。
4. USB 拔插后重新建立接口，旧连接关闭；恢复后使用当前地址重连。

例如仅为说明，USB 两端可选 `S31=192.168.50.1/24`、`Jetson=192.168.50.2/24`；必须先排除实际网段冲突。这两个地址不替代 S31 自己的 Wi-Fi STA/AP 地址。

不要把 USB 当串口发送 JSON，也不要把 MLT1/MUX1 套在 USB 以太网数据外面。Jetson 使用系统网卡和普通 socket，不使用 pyserial 打开 S31 业务口。

### 3 用 TCP 透明转发保留 C6 代码

为尽量不改两块 C6，推荐在 S31 上保留两个 Wi-Fi 侧的 8883 入口，转发到 Jetson USB IP 的 8883：

```text
车机 C6 --> S31 STA_IP:8883 --TCP字节转发--> Jetson USB_IP:8883
UAV C6  --> S31 AP_IP:8883  --TCP字节转发--> Jetson USB_IP:8883
```

TLS 的两端仍是 C6 与 Jetson。S31 不解密、不重新组织 MQTT 消息、不替 C6 返回任务 ACK。

建议新增 `broker_proxy` 组件；从旧 `serial_tunnel.c` 中复用 socket 生命周期的处理思路，按以下步骤重构：

1. 在 Wi-Fi STA/AP 入口监听 8883。接到每一条 C6 连接后，为它单独创建到 Jetson USB_IP:8883 的连接。
2. 用 select/poll 或等效事件循环双向搬运字节，处理 read/write 分段返回和未发完的数据。
3. 设置有界缓冲。目标 socket 暂时写不动时暂停继续读取，避免无限堆积。
4. 任一端 EOF、错误、连接超时或 USB 断开，都关闭这一对 socket 并回收缓冲；不能把新旧连接的数据混在一起。
5. 删除该 S31 路径中的 MUX1 帧头、OPEN/DATA/ACK、channel/token/epoch 封包及 `usb_serial_jtag_*` 调用。TCP 已负责字节流传输，连接管理仍需保留。
6. S31 侧的组网日志走独立调试输出；业务 USB 网卡不承载原串口日志帧。

`firmware/apps/ugv/app.c` 的新装配顺序建议为：组网启动 → USB 网卡初始化 → Jetson 对端地址可用 → TCP 转发入口启动 → 开始公告服务入口。USB/代理不可用时停止发新公告并关闭旧连接，避免节点持续连接空入口。

这条方案是“Wi-Fi 侧 TCP 连接 → USB 网络上的另一条 TCP 连接”。USB 上确实使用网卡/IP；它没有自动实现所有 IP 协议的透明路由。后续需要 HTTPS、UDP/SRT 等，再增加相应路由/转发，不能把本轮 8883 可用写成全协议网关已完成。

### 4 保留服务公告

S31 继续使用 Mesh-Lite 公告 `changan_ugv_mqtt_v1`，保持以下字段：

```text
node_id    ugv-001
ip         S31 的 Wi-Fi STA 地址，车机 C6 连接这个入口
ap_ip      S31 的 Wi-Fi AP 地址，UAV C6 连接这个入口
port       8883
broker     ugv-broker.lab
epoch      本次启动/服务会话标识，沿用现有约束
generation 递增的公告序号
```

复用 `service_discovery.c` 的约 3 秒公告、15 秒过期和上下行转发规则。IP 要写实际监听的 Wi-Fi 地址，不能填 USB_IP 冒充 STA/AP。公告不是授权，最后仍由 Jetson 检查证书。

如果改用纯 IP 路由到 Jetson，也可以，但必须同步修改服务入口选择与公告；不能保证现有两块 C6 完全不改。本轮优先上面的兼容方案。

原 MUX1 的 NETWORK 状态报告不会随 USB 网卡自动出现。先使用 S31 调试日志查看无线状态；后续车机显示如需接入 S31 数据，再适配 `nodes/network.py`，不能把旧 `ugv-network.json` 当作实时状态。

## 3 两块 C6 编译烧录


结论：源码可以复用，电脑车机不重写；两块 C6 只承担通信和诊断测试，没有真实无人机适配工作。S31 保持上述组网与公告兼容后，C6 不需要为 USB 网卡改业务代码。

先在 Windows 打开 PowerShell，执行以下命令，启动 ESP-IDF 6.1 的 Python 虚拟环境并加载编译工具：

```powershell
& 'C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1'
cd D:\changan\changan-mesh-system
$env:PYTHONUTF8 = '1'
python --version
python "$env:IDF_PATH\tools\idf.py" --version
```

脚本和项目路径按本机实际安装位置替换。最后一条应输出 `ESP-IDF v6.1` 或对应的 6.1.x 版本；加载失败时先处理环境问题。环境只对当前窗口生效，新开 PowerShell 后需重新执行启动命令，下面的端口枚举和烧录都在同一窗口继续操作。

再按 [固件说明](../firmware.md) 准备这两块板各自的身份文件；设备私钥由维护方单独提供，本地编译生成的固件不提交仓库。

先枚举端口并核对两块实物：

```powershell
python -m serial.tools.list_ports -v
```

退出占用串口的 GUI/CLI/monitor，以下 COM7、COM5 替换为对应板实际端口，再分别执行：

```powershell
python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --topology chain --port COM7 flash
python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --topology chain --port COM5 flash
```

`flash` 会先按需要编译再烧入，不在不同板之间复用带身份的 bin。保留现有登记和 NVS，不执行整片擦除。完成后启动电脑车机，使用 `ping uav-001` 和 diagnostics 测试，无需连接无人机。

## 4 Jetson 部署操作

### 1 先分清要启动的程序

| 名称 | 可以怎样理解 | 以后在哪里运行 | 怎么处理现有代码 |
| --- | --- | --- | --- |
| 车机 GUI/CLI | 人操作的窗口 | Windows 电脑 | 继续使用，电脑仍通过 USB 串口连接车机 C6 |
| Mosquitto / Broker | 消息中转站，负责在 C6 和后台之间传消息 | Jetson | 安装 Linux 程序，重新写本机配置；不用改它的源码 |
| UGV 后台 | 接收车机请求、管理任务、通知测试 C6 执行 | Jetson | 直接运行现有 Python 代码，只调整配置和数据路径 |
| 原 serial_tcp_bridge.py | 旧 UGV C6 与电脑之间的串口搬运程序 | 本轮不启动 | S31 改用 USB 网卡后，由系统网络和 S31 转发替代 |

MQTT 是这些程序收发消息的约定；TLS 是连接时的加密和身份检查。接收方只需按下面步骤放好凭据并启动程序，不必重新实现 MQTT/TLS。

本轮主要是“安装 Linux 程序 + 搬配置和任务数据 + 替换 USB 链路”，不把 MQTT 业务重写一遍。`host/src/changan_ugv/nodes/controller.py`、`service/`、`tasks/` 和车机代码继续复用。

### 2 先向代码维护方拿这些文件

从 [GitHub 仓库](https://github.com/treelazy123/Chang-An) 获取两个项目。电脑 PowerShell 中执行以下命令（已有工作目录时先确认并保留本地修改，不重复克隆覆盖）：

```powershell
cd D:\
git clone https://github.com/treelazy123/Chang-An.git changan
```

得到 `D:\changan\changan-car-terminal` 和 `D:\changan\changan-mesh-system`。另外通过双方约定的私密方式拿一个 `changan-runtime` 文件夹，内容应为：

```text
changan-runtime/
  ca.pem                         现有系统的公开信任证书
  nodes.json                     允许接入的设备清单
  acl.conf                       每台设备允许收发哪些消息的规则
  ugv-broker.lab/
    client.pem                   消息中转站的身份证明
    client.key                   消息中转站的配套私钥
  controller-001/
    client.pem                   业务后台的身份证明
    client.key                   业务后台的配套私钥
  tasks.sqlite3                  旧后台已有任务数据（如存在）
  ugv-task-agent.json             与任务数据配套的执行记录（如存在）
```

维护方从当前主仓库提供：`secrets/ca.pem`、`secrets/ugv-broker.lab/client.*`、`secrets/controller-001/client.*`、`config/nodes.json`、`runtime/acl.conf`。不要提供 CA 私钥 `ca.key`；两块 C6 的自身私钥只用于对应板编译，Jetson 不需要它们。

维护方可在电脑主仓库执行 `uv run --locked python tools/provision_mqtt.py --sync-acl`，按当前清单重新生成 `runtime/acl.conf`；该命令不会换证书，也不会重启服务。

#### 旧任务数据如何取出

先由维护方停止旧 UGV 后台和独立维护客户端，再一致导出数据库与 journal。不要直接复制正在写入的数据库主文件。以下在电脑主仓库下执行，只导出任务数据，不导出私钥：

```powershell
@'
from pathlib import Path
import shutil
import sqlite3

root = Path.cwd()
source = root / 'runtime/tasks.sqlite3'
if not source.is_file():
    raise SystemExit('No existing task database; report this and agree on a new deployment.')
target = root / 'runtime/handoff-state'
target.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(source) as src:
    with sqlite3.connect(target / 'tasks.sqlite3') as dst:
        src.backup(dst)
journal = root / 'runtime/ugv-task-agent.json'
if journal.is_file():
    shutil.copy2(journal, target / journal.name)
print(target)
'@ | python -
```

将导出的文件放入私密交付目录。保持旧后台停止直到切换完成；存在任务数据库但缺失原本应有的 journal 时，先报告维护方，不能伪造记录。新设备没有历史数据时，由维护方确认使用全新状态再启动；不删除旧电脑数据。

旧的 `tools/sync_runtime.py` 是同机仓库间迁移工具，会复制整套 secrets；本轮跨电脑/Jetson 按上述文件清单交付，不直接用它搬整套私钥。

### 3 Jetson 安装程序与源码

在 Jetson 打开终端，从 GitHub 克隆代码。以下命令用于首次部署，若 `/opt/changan` 已有项目则先保留已有配置和修改，再由维护方安排更新：

```bash
sudo apt update
sudo apt install -y git
sudo install -d -o "$(id -un)" -g "$(id -gn)" /opt/changan
git clone https://github.com/treelazy123/Chang-An.git /opt/changan
```

得到两个相邻目录：

```text
/opt/changan/changan-car-terminal/
/opt/changan/changan-mesh-system/
```

源码目录要让当前登录账户可读写，项目依赖通过该账户安装，不使用 `sudo uv`。安装消息服务和辅助工具：

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients openssl pipx
```

如果还没有 uv，按 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/) 的 pipx 方式执行：

```bash
pipx install uv
export PATH="$HOME/.local/bin:$PATH"
```

进入源码，安装项目使用的 Python 和依赖：

```bash
cd /opt/changan/changan-mesh-system
uv python install 3.11
uv sync --locked --python 3.11
uv run --locked python tools/run_tests.py
```

看到测试末尾 `OK` 后继续；失败或跳过项保存输出。本命令验证主机程序，不构建固件、不连接真实 C6。原 Windows `.venv` 不复制到 Jetson。

### 4 把文件放到固定位置

以下按第一次部署安装。如果 Jetson 已有任务数据或证书，先备份并比较，不覆盖已有不同身份或数据库。将步骤 2 的私密目录放到当前账户的 `Downloads/changan-runtime`，然后执行：

```bash
export CHANGAN_FILES="$HOME/Downloads/changan-runtime"
sudo install -d -m 755 /etc/changan/pki/ugv-broker.lab /etc/changan/pki/controller-001
sudo install -m 644 "$CHANGAN_FILES/ca.pem" /etc/changan/pki/ca.pem
sudo install -m 644 "$CHANGAN_FILES/nodes.json" /etc/changan/nodes.json
sudo install -m 644 "$CHANGAN_FILES/acl.conf" /etc/changan/acl.conf
sudo install -m 644 "$CHANGAN_FILES/ugv-broker.lab/client.pem" /etc/changan/pki/ugv-broker.lab/client.pem
sudo install -m 640 -o root -g mosquitto "$CHANGAN_FILES/ugv-broker.lab/client.key" /etc/changan/pki/ugv-broker.lab/client.key
sudo install -m 644 "$CHANGAN_FILES/controller-001/client.pem" /etc/changan/pki/controller-001/client.pem
sudo install -m 600 -o "$(id -un)" -g "$(id -gn)" "$CHANGAN_FILES/controller-001/client.key" /etc/changan/pki/controller-001/client.key
sudo install -d -m 750 -o "$(id -un)" -g "$(id -gn)" /var/lib/changan
sudo install -m 644 config/ugv.jetson.example.toml /etc/changan/ugv.toml
```

GitHub 仓库里没有这些私密文件，找不到文件就请维护方补齐，不在 Jetson 运行不带参数的 `provision_mqtt.py` 新建另一套证书。

如果维护方提供了旧任务数据库和 journal，先确认后台尚未运行且目标文件不存在，再执行存在的那两条复制命令：

```bash
cp -n "$CHANGAN_FILES/tasks.sqlite3" /var/lib/changan/tasks.sqlite3
cp -n "$CHANGAN_FILES/ugv-task-agent.json" /var/lib/changan/ugv-task-agent.json
```

缺哪个文件先核对步骤 2，不补空文件。`cp -n` 不覆盖目标旧文件；若跳过复制，先比较并处理已有状态，不直接启动。

`/etc/changan/ugv.toml` 是仓库提供的可直接使用模板：后台连接本机 `127.0.0.1:8883`，任务数据库写入 `/var/lib/changan`。S31 的外部 IP 不填进这个后台连接地址；外部监听在下一步配置。

### 5 先用本机地址启动消息中转站

生成本机测试配置：

```bash
cd /opt/changan/changan-mesh-system
uv run --locked python tools/configure_broker.py \
  --listen-address 127.0.0.1 \
  --ca-file /etc/changan/pki/ca.pem \
  --server-cert /etc/changan/pki/ugv-broker.lab/client.pem \
  --server-key /etc/changan/pki/ugv-broker.lab/client.key \
  --acl-file /etc/changan/acl.conf \
  --output /tmp/changan-mosquitto.conf
```

看到 `Broker configuration written` 后，将配置设为可读，在“终端 A”以 mosquitto 账户启动（该账户拥有读取服务端私钥的权限）：

```bash
chmod 644 /tmp/changan-mosquitto.conf
sudo -u mosquitto mosquitto -c /tmp/changan-mosquitto.conf -v
```

保持这个终端打开。应看到 8883 监听和 `mosquitto ... running`，没有文件/端口错误。配置中的身份检查不要删除；允许匿名或关闭加密会与 C6 现有程序不匹配。

如果显示端口占用，先查：

```bash
sudo ss -ltnp 'sport = :8883'
```

只停止确认属于本项目的重复实例。系统可能另有默认 1883 服务，不用它替代本项目 8883，也不停止其他项目服务。

### 6 再启动任务后台

打开“终端 B”：

```bash
cd /opt/changan/changan-mesh-system
uv run --locked python tools/ugv_service.py --config /etc/changan/ugv.toml
```

保持运行。日志中应出现 `UGV M1 service active`；同时终端 A 应出现 `controller-001` 的连接记录。只看到后台启动提示还不够，要确认它确实连接了中转站。

打开“终端 C”：

```bash
cd /opt/changan/changan-mesh-system
uv run --locked python tools/mqtt_terminal.py --config /etc/changan/ugv.toml
```

进入后输入 `list`。未接 S31/C6 时节点未就绪是正常的，此处先检查请求有返回、没有连接或证书报错。该维护终端复用已有后台，不另开一份 controller 登录。

### 7 接上 S31，开放它能访问的地址

先完成本文第 2 节的 S31 USB 网卡及转发。Jetson 执行：

```bash
ip -br address
```

找到 S31 对应网卡上的 Jetson IP。不要用 S31 的 STA/AP 地址代替它。例如 USB 方案选定 Jetson=192.168.50.2、S31=192.168.50.1 时，下面填 `192.168.50.2`；先确认实际配置及网段无冲突。

退出终端 C，在终端 B 按 Ctrl+C 停后台，再在终端 A 按 Ctrl+C 停本次手动启动的 Broker。重新生成带两个监听地址的配置：

```bash
cd /opt/changan/changan-mesh-system
export JETSON_USB_IP='替换成Jetson上S31_USB网卡的实际IPv4地址'
uv run --locked python tools/configure_broker.py \
  --listen-address 127.0.0.1 --listen-address "$JETSON_USB_IP" \
  --ca-file /etc/changan/pki/ca.pem \
  --server-cert /etc/changan/pki/ugv-broker.lab/client.pem \
  --server-key /etc/changan/pki/ugv-broker.lab/client.key \
  --acl-file /etc/changan/acl.conf \
  --output /tmp/changan-mosquitto.conf
```

按步骤 5、6 的顺序重新启动 A、B。现在消息服务既能接收本机后台，也能接收 S31 转发过来的连接。后续 USB IP 变化，要同步更新监听和 S31 的 Jetson 目标地址；USB 断开时显式监听的地址是否需要重启，也纳入恢复测试。

如果启用了防火墙，只放行 S31 USB 接口所需的 TCP 8883。维护端口 8787 保持本机使用。

## 5 电脑车机与端到端测试


按本文第 3 节给两块 C6 分别烧入 pc_root、uav 现有固件。S31 应让车机 C6 在第一层、自己在第二层、UAV C6 在第三层，并公告兼容的服务入口。

终端 A 应看到 `pc-root-001`、`uav-001` 的客户端连接，终端 C 的 `list` 最终应显示相应节点 `ready=true`。Wi-Fi 连上但没有这两条消息连接，优先检查服务公告和 S31 转发。

Windows 电脑进入 `changan-car-terminal`：

```powershell
uv sync --locked
uv run --locked python -m serial.tools.list_ports -v
uv run --locked python -m car_terminal --port COM7
```

COM7 替换为车机 C6 实际端口。进入 `car>` 后：

```text
list
ping uav-001
status uav-001
echo uav-001 hello-from-car
task create uav-001 60 1000
```

记下创建返回的 task_id，用它替换下面的 TASK_ID：

```text
task start TASK_ID
task get TASK_ID
task events 0 TASK_ID
```

看到 UAV C6 的真实回复，以及任务从运行到完成，即跑通基础闭环。这只是 C6 的采样诊断，不涉及无人机起飞或动作。

需要图形界面时，先退出 CLI，再在电脑的 changan-car-terminal 目录执行：

```powershell
uv run --locked python -m car_terminal.gui --port COM7
```

手动点击“连接”并刷新节点。GUI、CLI 和串口监视器不能同时占用车机串口。

## 6 验收和交回记录

将本节表格复制到 `runtime/handoff/联调记录.md` 中填写即可，不另设模板文档。下面均为待接收方实机测试，当前没有 Jetson/S31 实机通过结论。

### 网络表


| 设备 | node_id/职责 | USB/串口 | STA / AP / USB IP及掩码 | 父 BSSID/AP MAC | 路由/转发 |
| --- | --- | --- | --- | --- | --- |
| 电脑 | 车机串口客户端 | 待核对 | 待填写 | 不适用 | 待填写 |
| root C6 | pc-root-001 | 待核对 | 待填写 | 待填写 | 待填写 |
| S31 | UGV 网络接入 | 待填写 | 待填写 | 待填写 | 待填写 |
| Jetson | ugv-001；后台 controller-001 | 待填写 | 待填写 | 不适用 | 待填写 |
| UAV C6 | uav-001 | 待核对 | 待填写 | 待填写 | 待填写 |

| 服务项 | 实际值 |
| --- | --- |
| Jetson Broker 的本地及对外监听 | 待填写，默认端口 8883 |
| TLS 服务名及凭据签发方 | 待填写；默认 ugv-broker.lab；不填私钥 |
| root 的发现 ip:port → Jetson 路径 | 待填写 |
| UAV 的发现 ap_ip:port → Jetson 路径 | 待填写 |
| 服务发现方式/TTL/地址变化恢复方式 | 待填写 |
| 后台配置路径、DB/journal/锁路径 | 待填写 |
| Broker、后台启停与日志命令 | 待填写 |
| 旧 controller 已退出、身份无并发复用 | 待核对 |

### 验收表


状态填写：未测 / 通过 / 失败 / 阻塞。每项提供相应日志位置或脱敏附件。

| 检查点 | 状态 | 复现步骤、时间、实际结果、证据 |
| --- | --- | --- |
| H0 网络接法及服务入口 | 未测 | |
| H1 电脑车机启动 | 未测 | |
| H2 Jetson Broker/后台 | 未测 | |
| H3 S31 USB/Mesh/端点发现 | 未测 | |
| H4 root、UAV mTLS及ready | 未测 | |
| H5 list/ping/status/echo | 未测 | |
| H6 diagnostics 完成/暂停恢复/取消 | 未测 | |
| H7a 车机断开/重连 | 未测 | |
| H7b S31 断链/恢复 | 未测 | |
| H7c 后台重启/对账 | 未测 | |

任务记录：node_id、task_id、msg_id/command_id、revision、boot_id、状态顺序、进度与最终结果。恢复记录分别保存故障前、故障中和恢复后的状态，检查旧 start 未重复执行。

除任务创建/完成外，另测暂停、恢复和取消；操作超时先按原 task_id 查询，不盲目重发。失联后任务可能暂停或进入对账状态，不要求无条件恢复 RUNNING；核对旧 start 没有重复执行。

交回：实际网络表、完成的验收表、S31 源码/构建方法、部署与启停命令、相关 msg_id/task_id 及三端日志、未完成问题。日志不包含私钥；未测性能明确写未测。

交接准备阶段已有主机 116 项、车机 29 项回归通过及 C6 配置 dry-run 记录；这些是 Windows 本机检查，不代替本表实机验收。本次合并仅整理文档，未重新运行业务回归。

## 7 排错与停止方法


| 看到的现象 | 先做什么 |
| --- | --- |
| Missing existing deployment file | 按报错路径补文件，核对第 4 节的步骤 2、4；不要新建另一套证书 |
| Permission denied / 无法读取 key | 检查 Broker 的 key 是否给 mosquitto 组读取；controller key 是否属于运行后台的账户 |
| TLS、certificate、证书校验错误 | 先看 `date -u`；执行 `openssl x509 -in /etc/changan/pki/ugv-broker.lab/client.pem -noout -dates -subject` 核对时间与身份，联系维护方核对信任链，不关闭校验 |
| Another UGV manager owns controller-001 | 退出重复后台/独立维护程序，保留一份服务；不要删除锁文件试图绕过 |
| Broker 中看不到两块 C6 | 检查 C6 的 UGV_SERVICE / CONNECT 日志、S31 的 STA/AP 入口及到 Jetson 的转发 |
| 已连接但 ready=false | 检查能力及新鲜状态是否齐全、是否属于同一 boot；继续对照 C6 和后台日志 |
| gateway_not_ready | 车机 C6 尚未完成消息连接/订阅，先处理上述网络和认证问题 |
| 后台可用，车机打不开 COM | 退出占用相同端口的 GUI、CLI 或监视器，重新枚举端口 |

### 停止和回退


按本文第 6 节的验收表测试暂停/恢复、取消、车机重连、S31 断链和后台重启，保存实际输出。正常停止顺序：退出维护终端 → Ctrl+C 停后台 → Ctrl+C 停 Broker。保留数据库和 journal。

失败需回到旧电脑时，先停 Jetson 的后台/Broker，由维护方确认旧电脑数据是否需要同步，再启动旧系统；不能在两个地方同时使用 controller-001。Jetson 产生的新任务记录不能被旧快照覆盖。

首次交接以前台三个终端完成。后台常驻、开机启动再按已跑通的命令交付服务配置，数据继续放在 `/var/lib/changan`，不放进源码或 /tmp。

### 后续代码更新

交接以 [GitHub main 分支](https://github.com/treelazy123/Chang-An/tree/main) 为入口，部署时记录 `git rev-parse HEAD` 的提交号。已有检出的修改和运行数据先保留，再由维护方安排拉取更新。

仅提交两个项目的源码、配置模板、依赖锁文件、文档及必要的供应商组件。下载的 Python 环境、build 构建输出、运行数据、私钥和 ZIP 不提交；每台机器自行安装依赖并编译。凭据与旧任务数据按第 4 节单独交付。
