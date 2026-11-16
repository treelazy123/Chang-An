# 系统架构

当前主仓库为 `D:\changan\changan-mesh-system`，车机仓库为相邻的 `D:\changan\changan-car-terminal`。固件、UGV 主机和车机通过 [v1 协议](../protocols/v1/README.md) 交互，生产程序不跨仓库导入业务源码。

## 无线结构与业务链路

chain 配置的预期无线层级为 root C6 → UGV C6 → UAV C6 → Micro C6。层级与父节点应从实际状态上报验证；业务连接的终点不必是无线直接父节点。

当前 `mqtt_serial` 业务路径为：

```text
车机 GUI/CLI ↔ root C6 原生 USB / MLT1
                     ↕ root MQTT/TLS 客户端
               UGV C6 TCP/USB 透明字节隧道
                     ↕ UGV 主机串口桥接
                 Mosquitto mTLS Broker
                     ↕
                 UGV 主机常驻后台
                     ↕ 节点 MQTT/TLS
                 UAV / Micro 执行器
```

root 使用发现到的 UGV STA 入口，UAV/Micro 使用 UGV SoftAP 入口；实际地址由服务发现或部署配置提供，不把 Micro 的直接父网关当成 Broker。UGV C6 不运行 Broker，不终止 TLS，也不执行 UGV 主机的 diagnostics 任务。

root 把车机请求来源绑定为自身证书身份；后台校验来源、清单权限、请求期限、目标及能力。证书 CN、MQTT Client ID 与 node_id 对应，不用来源 IP 代替身份。`controller-001` 只允许一个后台或独立维护客户端，本地 RPC 只在回环接口提供维护服务。

## 固件职责

`firmware/main/app_main.c` 启动组网、调用选中角色并打印状态。只有一个 IDF 工程，按 Kconfig 选一个角色入口。

| 路径（相对 firmware） | 职责 |
| --- | --- |
| `apps/root/app.c`、`apps/root/car_gateway.c` | root 串口网关、来源绑定、MQTT 请求/回复与任务事件转发 |
| `apps/ugv/app.c`、`apps/ugv/serial_tunnel.c` | UGV 服务发现、TCP/USB 字节隧道、协商式只读网络报告 |
| `apps/uav/app.c`、`apps/micro_uav/app.c` | 启动各自 MQTT 客户端并选择入口 |
| `components/network_mesh_lite/`、`components/node_role/` | Mesh 启动、角色/拓扑与无线状态 |
| `components/app_protocol/` | MLT1、消息校验和共享状态 payload |
| `components/mqtt_serial/`、`components/car_gateway/` | 公共 MQTT/TLS 接口和角色实现的装配 |
| `components/task_agent/` | C6 diagnostics、状态机、NVS 关键记录 |
| `components/transport_tcp/` | 保留的 legacy TCP 兼容实现 |

`pc_root` 仍是 CLI/Kconfig 角色名，目录采用 `apps/root/`，不改变已有身份与 topic。UAV/Micro 当前复用诊断能力；不提供飞控、媒体、UWB 或其他场景接口。

## UGV 主机职责

运行时代码通过 `changan_ugv.*` 导入；`tools/` 保留管理工具和兼容启动入口。

| 模块（相对 host/src/changan_ugv） | 职责 |
| --- | --- |
| `service/server.py`、`service/requests.py` | 启停、请求/反馈队列、来源权限与请求路由 |
| `nodes/controller.py`、`nodes/inventory.py`、`nodes/lease.py` | MQTT、受控清单、就绪判断、管理员排他锁 |
| `nodes/network.py` | 校验/读取 UGV USB 网络快照，不授予设备或 MQTT 权限 |
| `tasks/store.py`、`tasks/runtime.py`、`tasks/ports.py` | 持久化、调度、对账、任务通信接口 |
| `agents/ugv.py` | UGV 电脑/Jetson 本地主机诊断执行器 |
| `transport/serial_bridge.py`、`transport/node_channel.py` | USB 字节转发和节点 MQTT 适配 |
| `transport/rpc.py`、`cli.py` | 本地维护入口及旧终端功能 |
| `protocol/frames.py`、`protocol/tunnel.py` | MLT1 与 MUX1 |
| `config.py`、`deployment.py`、`paths.py` | 显式配置、Broker 配置生成与仓库默认路径 |

## 配置与适配接口

`config.py` 定义 `BrokerEndpoint(host, port, server_name)`、`BrokerConfig`、`ServicePaths` 和 `ServiceConfig`。连接地址与 TLS 服务名分别配置；TOML 相对路径按配置文件所在目录解析。显式配置缺少必填字段或 inventory 文件时拒绝启动，不悄悄回退到源码目录。

`tasks/ports.py` 的 `NodeChannel` 提供：

```python
is_connected() -> bool
snapshot(node_id) -> NodeSnapshot
ready_count() -> int
send(node_id, packet) -> SendReceipt
notify(terminal_id, packet) -> SendReceipt
```

`NodeSnapshot` 是含 ready、boot_id、task_types 的冻结数据。`SendReceipt.queued` 只表示传输接收发送请求，不表示节点接受或任务完成。`MQTTNodeChannel` 包装 Controller，任务调度不直接持有 Paho、不构造 topic。

`LocalExecutor` 提供 `boot`、`handle(packet)`、`tick(connected)`、`close()`。Runtime 由启动层显式注入 executor_factory；工厂接收 emit/snapshot 回调。执行器应构造完再发事件，不能另开线程无同步地访问 SQLite。反馈经服务队列进入 `Runtime.receive()`，继续验证 boot、op_seq、期限和命令对应关系。

Broker 配置生成器只读取现有证书并生成配置，不签发、不改清单、不重启服务。部署方式见 [部署与交接](deployment.md)。

## 车机与网络可视化

独立车机的 `RequestTransport.request(packet)` / `close()` 屏蔽串口和 MQTT 差异；`client.py`、`tasks.py` 提供业务 API，`gui.py`、`network.py` 提供调试与网络结构显示。

网络树按子节点 `parent_bssid` 匹配唯一父节点 `ap_mac`。未知、重复、循环或旧启动数据不会被画成确定的实时连接。UGV 的主机服务就绪与 C6 无线状态分别表示，不能把主机 IP 当成 UGV C6 的无线地址。详细字段和 USB 协商只在 [协议](../protocols/v1/README.md) 定义。

## 数据与兼容边界

公开登记在 `config/nodes.json`；证书/私钥在 `secrets/`；Jetson 部署副本在 `changan-runtime/`；数据库、journal、Broker 配置和 UGV 网络快照在 `runtime/`；构建产物在 `build/`；依赖环境在 `.venv/`。项目所有者已明确要求提交现有 secrets 和 changan-runtime；现场 runtime、build、.venv、身份构建缓存和控制器锁保持不跟踪，不随文档整理或服务重启删除。

本地供应商源码和许可证保留于 `third_party/`。legacy TCP 源码与原始实验材料保留用于兼容和证据核对，不作为当前 MQTT 的启动依据。
