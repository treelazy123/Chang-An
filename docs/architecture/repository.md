# 仓库结构与职责

主仓库：`D:changanchangan-mesh-system`。车机仓库：`D:changanchangan-car-terminal`。

## 固件：一个工程，四个角色入口

`firmware/main/app_main.c` 只启动网络、调用所选角色、周期打印状态。`main/CMakeLists.txt` 根据现有 Kconfig 选择且只选择一个 `apps/<role>/app.c`。

| 入口/模块 | 职责 |
| --- | --- |
| `apps/root/app.c` | 启动车机 USB 端口，选择 UGV STA MQTT 入口 |
| `apps/root/car_gateway.c` | 车机请求身份绑定、MQTT 转发、回复/任务事件转串口 |
| `apps/ugv/app.c` | 启动 UGV 服务发现和 USB TCP 字节隧道 |
| `apps/ugv/serial_tunnel.c` | Wi-Fi TCP 会话与 USB 多路通道的字节传输，不终止 TLS |
| `apps/uav/app.c` | 选择 UGV SoftAP 入口，启动 UAV MQTT 客户端 |
| `apps/micro_uav/app.c` | 选择 UGV SoftAP 入口，启动 Micro MQTT 客户端 |
| `components/mqtt_serial/` | 公共 TLS/MQTT、时钟、命令与遥测；入口地址由角色传入 |
| `components/task_agent/` | 共用 diagnostics 采样、状态机和 NVS 记录 |
| `components/network_mesh_lite/` | Mesh-Lite 启动、角色拓扑与链路状态 |
| `components/node_role/` | Kconfig 的角色、编号和层级查询 |
| `components/transport_tcp/` | 保留的旧 TCP 业务兼容实现 |

UAV 与 Micro 目前运行同一诊断能力，因此共享任务执行器。已移除原先只返回角色名称的四个 task_agent 角色文件；以后真正的摄像头、飞控、底盘适配应落在对应应用/适配组件中。

`pc_root` 仍是命令和 Kconfig 中的角色名，代码目录采用 `apps/root`，不改变已有设备 ID、证书 CN 或 MQTT topic。

## UGV 主机

```text
host/src/changan_ugv/
  service/server.py       后台进程、队列、启动和关闭
  service/requests.py     车机来源/权限检查和请求路由
  nodes/controller.py    MQTT 会话、在线登记、基础命令
  nodes/inventory.py     受控设备清单与 ACL 生成
  nodes/lease.py         controller-001 排他锁
  tasks/store.py         SQLite 任务、操作、幂等及事件
  tasks/runtime.py       异步派发、占用、对账与进度通知
  agents/ugv.py          电脑/Jetson 本地诊断执行器
  transport/serial_bridge.py  UGV USB 字节隧道到固定本地 Broker
  transport/rpc.py       回环维护接口
  protocol/frames.py     MLT1 帧和基础命令
  protocol/tunnel.py     USB 隧道帧
  cli.py                 保留的 mqtt_terminal 维护界面
  paths.py               仓库默认路径
```

运行时代码通过 `changan_ugv.*` 导入，不从 `tools/` 导入实现。旧入口是薄转发层，不保留第二份业务逻辑。构建工具在 IDF Python 下也能通过引导找到包，证书操作依然在 uv 环境完成。

## 依赖和数据

- `firmware/CMakeLists.txt` 载入 `third_party/`，组件管理器继续关闭，SDK 不变。
- `tools/lab.py` 以 `firmware/` 为 IDF 工程路径，构建仍隔离到根目录 `build/.../nodes/<node_id>/`。
- 设备登记在 `config/nodes.json`；证书在 `secrets/<node_id>/`；独立编号和证书规则保持。
- SQLite、主机执行器日志、Broker 配置在 `runtime/`。这些状态与密钥均不进入 Git。
- 协议的规范和固定样例在 `protocols/v1/`；车机保有自己的实现，通过合同验证兼容。
- 历史验收材料保留原内容，历史绝对路径只表示当时环境。当前命令以 `docs/bringup/host.md` 为准。

迁移不增加具体场景接口，不改变业务协议，不声称解决 Micro-001 重启，也不表示新目录的固件已通过编译/硬件验收。
