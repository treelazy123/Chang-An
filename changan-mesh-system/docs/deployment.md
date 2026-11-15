# 部署与交接

当前平台、职责与接口见 [系统架构](architecture.md)，日常启动命令见 [运行说明](operations.md)。Jetson ARM/Linux、S31 SDK/USB 网络及真实新拓扑仍待硬件验收。

本轮已确认的电脑车机 C6—Jetson S31—UAV C6 交接任务、实际部署步骤和验收记录见 [交接入口](handoff/README.md)。

## 配置文件部署

仓库布局示例为 [ugv.example.toml](../config/ugv.example.toml)，Jetson 示例为 [ugv.jetson.example.toml](../config/ugv.jetson.example.toml)。配置包括 Broker host/port/TLS server_name、CA/客户端证书、设备清单、任务数据库、agent journal 和排他锁路径。

```powershell
uv run --locked python tools/ugv_service.py --config config/ugv.example.toml
uv run --locked python tools/mqtt_terminal.py --config config/ugv.example.toml
```

实际部署先由用户停止原后台，再切换配置；所有后台/维护入口使用同一个 controller 锁文件。维护终端优先复用现有后台，自己的 `--config` 不动态修改已运行后台。`--config` 与 `--secrets` 不能同时指定；CLI 可覆盖 Broker 入口或 inventory。

## 既有环境迁移与升级

原保留工程 `D:\esp\mesh_lite_node` 不是当前开发目录。不要覆盖它，也不要在 `D:\changan\changan-mesh-lab` 开发。迁移时保留了原证书和 SQLite 一致快照；如果源服务在快照后继续处理任务，应由用户停止旧后台/独立维护终端后再同步：

```powershell
cd D:\changan\changan-mesh-system
uv run --locked python tools/sync_runtime.py --source D:\esp\mesh_lite_node
```

工具检查源/目标 controller 排他状态，通过 SQLite backup 复制数据库，保留密钥，备份目标旧状态，并重写 Broker 路径；不会停止进程。不要只复制运行中的 SQLite 主文件，也不要遗漏对应执行器 journal。已有已切换环境不需要日常重复运行此迁移命令。

角色或主题权限更新后，使用现有 CA/身份生成 ACL：

```powershell
uv sync --locked
uv run --locked python tools/provision_mqtt.py --sync-acl
```

命令只重建 ACL，不重签证书。由用户在维护窗口重载或切换本项目 Broker，使新权限生效；修改磁盘清单不表示 Broker 已加载权限。保持其他项目的 1883/9883 服务独立。撤销设备时先禁用受控清单，再同步并部署 ACL；自动证书吊销、续期与可信生产时钟不在当前实现范围。

新增车机/任务主题需要对应新版 root 和节点固件；完整网络显示还需更新 UGV C6。固件、桥接和后台源码的变化不会自动应用到已运行实例。切换后重新验证节点能力、任务状态和网络快照；用户烧录步骤见 [固件说明](firmware.md)。

## Jetson 部署

1. 使用 Python 3.11 或 3.12 与 uv，执行 `uv sync --locked` 重建环境，不复制 Windows `.venv`。
2. 安装 Mosquitto，准备主机所需证书和受控节点清单。开发使用隔离测试 CA，CA 私钥由签发方保管。
3. 按 Jetson 示例配置文件填写实际路径，让服务账户能读证书/清单并写数据库、journal、锁与运行目录。
4. 如保留任务历史，先停止旧后台，再一致交接数据库与 journal；主机执行器路径要与新配置一致。
5. 启动 `uv run --locked python tools/ugv_service.py --config /etc/changan/ugv.toml`。
6. 先保留 C6 字节桥验证现有任务，再替换 S31 IP 网络路径。

主机/Jetson 开发负责 config 与启动装配，执行器开发遵守 `LocalExecutor`，公共任务维护负责生命周期/持久化/对账，网络维护负责 `NodeChannel`、TLS 和节点状态。新任务种类必须同步能力、校验、协议和测试，不能仅更换执行器就宣称支持了新业务。

## Broker 外部监听

后台连接位置与 Broker 对外监听分别配置。可使用已有证书先生成供审核的配置：

```text
uv run --locked python tools/configure_broker.py --root /opt/changan/changan-mesh-system --listen-address 127.0.0.1 --listen-address 192.0.2.10 --output /tmp/mosquitto-review.conf
```

`192.0.2.10` 是示例，替换为 Jetson 能绑定、各节点能到达的真实地址。非仓库布局时显式提供 `--ca-file`、`--server-cert`、`--server-key`、`--acl-file`。每个监听入口均强制 TLS、客户端证书和 ACL；生成器不签发证书或重启服务。核对后再由部署方切换配置。

## S31 网卡交付边界

现有固件只针对 ESP32-C6，不能只修改 IDF_TARGET 就当作完成 S31 移植。S31 开发侧需交付并验收 USB 网卡枚举、地址分配、链路恢复、Mesh 拓扑、必要路由/转发及车机/UAV/Micro 到 Broker 的双向 TCP 路径。

服务入口由 host、port、TLS server_name 组成；上层不假定父网关等于 Broker，也不固定使用某个 C6 STA/AP 示例地址。服务发现兼容及版本协商需由 S31 与客户端共同确认。先验收 TLS 连通性，再接 MQTT 业务；IP 路径验收完成后才移除当前串口字节桥。

车机 MQTT 入口已实现，例如：

```text
uv run --locked python -m car_terminal.gui --transport mqtt --host 实际Broker入口 --broker-port 8883 --node-id pc-root-001 --cert-dir 车机证书目录 --server-name ugv-broker.lab
```

`pc-root-001` 表示哪一个业务会话需在移交中明确；网卡管理客户端不能与 C6 或车机同时复用同一身份。网卡诊断与车机任务会话的职责分别定义，不能因改成 IP 网卡就宣称原节点执行器已经迁移。

## 联调清单

- 节点 list/ready、Ping/状态/Echo 与目标 ACK 身份关联正确。
- diagnostics 创建、配置更新、同节点排队、开始、暂停、恢复、取消、完成与游标补查保持。
- 后台重启或 USB/Wi-Fi/Broker 恢复后对账，不重复执行旧 start。
- 各 TLS 入口拒绝错误服务名、不可信/缺失证书和跨节点主题访问。
- 源码移动后按显式配置启动，数据库、journal、锁实际落在指定路径。
- 新网络状态包含真实 IP、Mesh 层级与父 BSSID；过期、未知及 USB 断开正确呈现。

主机测试与迁移检查不能替代这些真实硬件验收，具体证据与待验收范围见 [验收状态](status.md)。
