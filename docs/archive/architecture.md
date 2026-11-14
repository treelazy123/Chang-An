# 四节点架构

PC 原生 USB ↔ pc_root C6（1层）↔ UGV（2层）↔ UAV（3层）↔ Micro（4层），上述为 chain 的无线与物理布局。

## Mesh 与业务职责

pc_root 运行 Mesh-Lite root 和 TCP 9000 服务端，原生 USB 提供业务串口。UGV 运行 TCP 9001 服务端，接收 UAV 和 Micro 两条独立连接；另外主动连接 pc_root 的 9000。UAV 在网络层转发 Micro 数据，但 Micro 的应用 TCP 连接终止在 UGV。

UGV 将下游消息放入 `relay` 信封，信封 `node_id=ugv-001`，内部消息保留原 `node_id` 和 `msg_id`。root 只接受配置的 UGV 会话，验证信封后将内部消息转给 PC。PC 命令经 root 的 UGV 会话下发，UGV 再按目标会话路由。UGV 自己的测试命令在 UGV 处理，root 自己的命令在 root 处理，目标节点生成 ACK。

这是一种应用代理架构：下游到 UGV、UGV 到 root 是不同 TCP 连接；PC 与 root 之间是原生 USB 字节流。当前不实现 PPP、SLIP、MQTT、照片传输或飞控接口。

## 身份、地址和发现

设备身份独立于串口、IP 和 Mesh 层级。TCP 接受端在 hello 后把 `node_id` 绑定到该 Socket，后续帧必须匹配；重复在线 ID 拒绝新连接。NAPT 后的来源 IP 不用于设备身份。这里只是实验身份绑定，没有实现生产环境身份认证。

UGV 每 3 秒公告自己当前 STA IP 和 TCP 服务端口；向 root 上报并向子节点广播。root 和其他中继缓存、向下分发；相同 epoch/generation 的转发副本不刷新 TTL，15 秒无新公告则失效。回调只校验、复制固定大小数据，JSON 构建和发送在普通任务中进行。链式和自动改父节点后客户端重新发现地址，禁止把 Micro 的直接父网关当作 UGV。

默认 `APP_UGV_NODE_ID=ugv-001` 必须与 UGV 的身份相同。提供地址覆盖选项用于公告联调，但默认自动发现。所有板必须使用相同 Mesh ID、信道、密码和拓扑。

## 并发、断连与背压

每个 TCP Socket 由单个任务读写和关闭。UGV 服务端与上游客户端通过两个有界队列通信，root USB 接收、发送也使用独立任务与有界队列。队列满丢弃并记录 UART 日志；不无限缓存数据。断开上游后清理旧命令和待转发队列。

连接超时 3 秒，注册超时 5 秒，正常遥测间隔 5 秒，遥测 ACK 用于确认对端收包，20 秒未收到有效帧关闭连接。重连采用 1/2/4/8 秒退避，地址变化也触发重连。注册 Socket 失联时，服务端等待读到关闭或空闲超时后释放身份。

PC 通过 `msg_id` 匹配 ACK，超时不自动重发，也不声称消息恰好执行一次。当前 ping/status/echo 是幂等测试；后续加入实际任务必须增加持久化去重和任务状态机。

## 构建与 SDK

四节点构建在 `build/four-node/` 下隔离，默认 chain。旧三节点镜像只是历史数据。ESP-IDF 6.1 兼容层继续仅生成构建内 NAPT 源码，不修改 SDK；STA/AP 在启动时创建且运行期不删除，符合旧预编译核心的适配约束。固件尚未在本轮编译和上板验证。


## 本地 1.0.2 核心的 root 地址字节序

只读反汇编本地 esp_mesh_lite_get_root_ip/get_parent_ip 确认：非根第2层把 DHCP 网关字节交换后返回，更深层按 0xc0a8XX01 组装。应用以前将该主机字节序值直接写入 sockaddr，导致目标 IP 颠倒。现在 UGV 第2层直接使用 DHCP gw（已是网络字节序），更深层的核心 API 结果通过 htonl 转换。该适配绑定本地 Mesh-Lite 1.0.2；替换核心库时须重新核对返回约定。
