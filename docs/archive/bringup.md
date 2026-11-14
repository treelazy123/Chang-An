# 四块 C6 上电与验收

## 1. 标记与烧录

标记 pc-root-001、ugv-001、uav-001、micro-001，将真实 STA/AP MAC、板型与串口填入 `hardware/nodes.csv`。根节点使用板子连接到 C6 原生 USB Serial/JTAG 的接口；有双 USB 的板子需区分原生 USB 与 USB-UART。

按 README 手动构建四种角色，拓扑统一 chain，分别烧录。构建路径为 `build/four-node/<角色>-chain/`。本轮没有代用户编译或烧录，不能把旧三节点 bin 当作新版本。

## 2. 接入 PC

root 原生 USB 为业务端口，日志在 UART0；root profile 已设置主控制台 UART0、副控制台 None。若用 menuconfig 改过这些值，恢复配置后再编译。ESP-IDF monitor/串口助手与 PC 程序不能同时打开业务 COM 口。

运行 `python tools/pc_terminal.py --list-ports` 找到根板原生 USB 端口，然后 `python tools/pc_terminal.py --port COM7`（替换 COM7）。波特率参数只满足主机串口 API，原生 USB 不按 UART 波特率传输。

## 3. 顺序上电并验证无线

按 root→UGV→UAV→Micro 顺序启动。核对 root=1、UGV=2、UAV=3、Micro=4；UGV.parent=root.ap_mac，UAV.parent=UGV.ap_mac，Micro.parent=UAV.ap_mac。所有信道一致。level=0 或未拿到 IP 时不能认定组网完成。

保留 FreeRTOS timer 栈 4096 字节，观察 `STACK` 的 timer_min_free。NVS 初始化失败时不自动擦除，需另行确认错误和恢复操作。

## 4. 验证业务连接

UGV 的 UART 日志应出现 TCP 9001 监听、连接上游并注册；UAV 和 Micro 应注册到 UGV。UGV 以 STA IP 发布服务，不要让 Micro 误连直接父节点 UAV。若地址公告失败，先查看三端 IP，临时用 APP_UGV_IP_OVERRIDE 指定 UGV 当前 STA IP 排查，三板不可使用相互重叠的网段。

PC 输入 list，预期出现 root、UGV、UAV、Micro 四个身份。分别执行：

```text
ping pc-root-001
ping ugv-001
ping uav-001
ping micro-001
status micro-001
echo micro-001 四节点测试
```

回执应匹配目标 node_id 和本次 msg_id。Micro 的回执来自 Micro，经 UGV 代理；收到 UGV 的遥测或网关保活不能代替 Micro 的命令回执。

## 5. 断连和恢复

断开 Micro，确认查询 Micro 出现 node_offline 或超时，其他连接继续工作。恢复后等待无线、服务发现和 TCP 注册恢复。断开 UGV，确认 PC 无法访问所有下游节点；恢复后用新的 list 与新的 msg_id 复查。断开 root USB，其他无线/TCP 不应因等待 PC 无限占用内存；队列满会丢弃消息，恢复 USB 后重新查询。

固定 chain 下 UAV 失效会切断 Micro 的无线父节点，不能回退到第 2 层。验证自动改父节点需四板统一切换 auto，再记录真实路径。重连后不保证旧命令或离线数据重放。

记录固件版本、实际构建日志、每板 sdkconfig、四端组网日志和 PC 请求/回执。纯主机测试不能替代这些实测证据。


## TCP 未注册时的诊断

无线 STATUS 的 level 和 parent_connected 正常，只证明关联和地址配置完成，不代表业务 TCP 已注册。PC list 只有 root 或 ping 返回 node_offline 时，查看 UGV UART 的 transport_tcp 行。

- TCP_WAIT：reason 给出等待 Mesh 层级、STA IP、root IP 或 UGV 公告。
- TCP_CONNECT：包含实际目标 IP:端口与地址来源。UGV 当前第2层应连接其 DHCP 网关，例如 192.168.5.1:9000；固定 chain 下 UAV 可连接其 UGV 网关，例如 192.168.4.1:9001。
- TCP_CONNECT_FAILED：errno 和错误文本用于区分拒绝、超时或无路由。
- TCP_HELLO：连接已建立并发送注册帧；Registered with upstream 才代表注册完成。
- TCP_REGISTER_REJECTED / TCP_HELLO_REJECTED：检查角色、node_id 和重复连接。

Micro 的网关是 UAV，不能套用第3层 UAV 的直接父网关策略。它等待 UGV_SERVICE 公告，使用 UGV 的 STA 地址。

PC 程序交互模式不再后台刷遥测，避免破坏输入行。查看连续遥测请退出交互模式后用 --monitor；同一业务 COM 口只能打开一次。


## AP 关联表与 TCP 离线时间

children 来自 esp_wifi_ap_get_sta_list，是驱动的关联记录，不代表目标业务在线。新增 AP_TRACKING 每个状态周期读取实际 AP inactive_s，并保留 API 返回码；AP_ASSOC 列出记录中的 MAC、AID 和驱动保留的 RSSI；AP_JOIN/AP_LEAVE 记录真实关联事件和离开原因。同一 UGV 日志中的时间戳可用于比较断电前最后活动、超时和重新关联时间。

实际 inactive_s 未读取前不能把“默认300秒”当作该设备的测量值。断电不到1分钟时，关联记录未清除不足以判定超时异常。若连续完全断电超过打印的 inactive_s，仍保留相同 UAV MAC，再提供 AP_TRACKING、AP_ASSOC 与 AP_LEAVE 附近的日志进一步定位。RSSI 是关联记录中的值，不证明已掉电设备仍在发射。

本次只增加诊断，不修改 AP 超时、不主动踢站，也不因 TCP 离线修改 Wi-Fi 计数。若读取 API 失败，children/wifi_assoc 显示 -1，并打印错误码，避免将读表失败当作零个关联。
