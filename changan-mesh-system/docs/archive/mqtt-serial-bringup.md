> 0.5.0 更新：MQTT构建/烧录必须添加 `--node-id`，新增设备不再修改源码名单。参考 [通用设备身份](device-identity.md)。下文三客户端验收是0.4.0历史记录，新增多实例/8通道功能尚待用户上板验收。

# C6 串口隧道上的 MQTT 双向 TLS 实验

本轮实现于 2026-11-13，目录 `D:/esp/mesh_lite_node`。仅支持已确认的 chain：root=1、UGV=2、UAV=3、Micro=4。旧 JSON TCP 模式仍为默认。固件 build、烧录由用户执行；已通过 UGV COM4 启动电脑串口隧道。最新硬件验收结果见下文。

## 网络与认证边界

- root C6 通过服务公告获得 UGV STA，例如 192.168.5.2:8883。
- UAV 和 Micro C6 都使用公告中的 UGV SoftAP，例如 192.168.4.1:8883。
- Micro 的默认网关是 UAV，不能把它当成 UGV。Micro 的 TCP 连接经过 UAV 网络转发后终止于 UGV C6。
- UGV C6 监听三个 TCP 连接，不运行 MQTT Broker，不解密 TLS。通过原生 USB 串口复用三路字节。
- 电脑串口转发程序为每路建立独立的 127.0.0.1:8883 TCP 连接。TCP 分段，TLS 从节点直达电脑 Mosquitto。Broker 的日志看到本地代理 IP，身份依赖每个节点的客户端证书。
- 原来 UGV 到 root 的 9000 上行与 root 服务端在此模式不启动；现在 root 主动连接 UGV。9001 旧消息监听同样不启动。
- root、UAV 的 USB 可以继续供电/烧录；新模式的业务串口只有 UGV。旧 pc_terminal.py 仅用于 legacy 模式。

## 1. 电脑依赖与证书

主机工具使用 uv 管理的独立 `.venv`，不修改 ESP-IDF 的 Python 环境。依赖以 `pyproject.toml` 和 `uv.lock` 为准：

```powershell
uv sync --locked
uv run --locked python tools/provision_mqtt.py
```

本次已经生成 secrets/ 和 host/runtime/，只需同步环境，不需要重复初始化。`requirements-*.txt` 保留供兼容使用。初始化工具拒绝覆盖既有私钥。测试使用独立临时目录，不会替换实际身份。

secrets/ 中有实验 CA、Broker、三个节点和 controller-001 的独立身份；host/runtime/mosquitto.conf 与 acl.conf 是具体的本地配置。目录已加入 .gitignore。终端输出不显示私钥。Windows 上应通过目录 ACL 限制私钥访问；Python chmod 并不能替代 Windows ACL。

需要安装官方 Mosquitto 2.x（含可执行文件及 OpenSSL 运行库）：https://mosquitto.org/download/ 。本机当前未发现 Mosquitto，代码没有安装系统服务。

Broker 配置仅监听回环 8883，要求客户端证书，使用证书 CN 作为授权身份，并绑定 MQTT client ID。三个设备仅能写自己的 presence/capabilities/telemetry/acks、读取自己的 commands 和 clock。controller-001 可读上述设备信息、发布三个固定节点的 commands 以及 clock。无明文监听。ACL 使用 Mosquitto 2.x 支持的 acl_file 配置。

实验 Broker 固定证书名称为 ugv-broker.lab。节点与终端均校验此名称，连接入口 IP 可以变化；不需要更改 Windows hosts，也不关闭证书校验。

## 2. 用户构建与烧录

这段由用户运行；实现期间未执行：

固件构建仍使用 ESP-IDF Python 环境；不要把主机 `.venv` 当作 ESP-IDF 工具环境。

```powershell
python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --topology chain
python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --topology chain
python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --topology chain
python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-001 --topology chain
```

构建目录为 build/mqtt_serial/<role>-chain，与 build/four-node 的旧镜像隔离。证书按 CONFIG_APP_NODE_ID 嵌入；修改 ID 时必须另行签发匹配身份并更新 ACL。APP_ARCHITECTURE_VERSION 仍为 Mesh 四节点版本 2，传输模式另行校验。

```powershell
python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --port COM实际端口 flash
```

其他角色同理。不要复制占位端口。UGV 原生 USB 专用于隧道，控制台 UART0、secondary None。监视 UGV Wi-Fi 日志请使用 UART0，不能与转发程序争用原生 USB COM。

## 3. 运行电脑上的三个程序

终端 A，运行本地 Broker：

```powershell
mosquitto -c host/runtime/mosquitto.conf -v
```

终端 B，连接 **UGV C6** 的原生 USB 串口：

```powershell
uv run --locked python tools/serial_tcp_bridge.py --port COM实际UGV端口
```

终端 C，启动带独立证书的本地 UGV 管理终端：

```powershell
uv run --locked python tools/mqtt_terminal.py
```

该终端同时维护可信时钟公告和固定设备登记。保持运行，节点才会取得本轮 clock 并进入 READY。等待三节点出现 READY 日志和至少一次遥测后：

```text
mqtt> list
mqtt> ping pc-root-001
mqtt> status uav-001
mqtt> echo micro-001 hello
```

同一电脑可同时承担车机终端与 Jetson 仿真职责。它只需通过 UGV USB 参与 Broker 实验；root/UAV 的 USB 供电和烧录连接独立。

## 4. 实验时钟与任务约束

初始化生成 secrets/clock.defaults 中的实验部署 UTC 下限。C6 没有断电保持的可信时钟，首次 TLS 校验先使用这个下限；认证连接后从 ACL 限定仅 controller-001 可发布的 clock 更新时钟。有效证书仍校验链、用途、服务名和基于当前本机时间的有效期。

这不是生产环境的实时证书过期/撤销保证。正式版主机应有可信 RTC/时间来源，Micro 需另行实现可信启动时间与撤销策略。部署日期改变可运行 `python tools/provision_mqtt.py --refresh-clock` 更新默认值；已有缓存 sdkconfig 不会自动覆盖，需要用户在 menuconfig 中同步 APP_TLS_BOOTSTRAP_UNIX，或采用新的构建配置。

控制终端仅接受固定三节点以及 ping/status/echo 的能力声明。ready 必须同时满足：在线公告、同一 boot_id 的能力和非 retained 遥测、20 秒内心跳。没有自动授权任意新角色或执行任意操作。

命令带 msg_id 和 deadline_unix，限制 512 UTF-8 字节、有效期 20 秒。客户端只接受自己的非 retained commands，校验截止时间（不超过当前时间 60 秒），返回目标节点生成的 ACK。QoS 1 可能重复投递，节点缓存最近 8 条请求/ACK，重复请求返回原结果，相同 ID 不同请求拒绝。缓存不跨重启；本轮仅支持幂等测试操作，不接入执行器。ACK 在第一版同时表示测试操作结果，尚无多阶段实际任务状态机。

## 5. USB 隧道协议

网络序 MUX1 + type(u8) + channel(u8) + epoch(u32) + token(u32) + seq(u16) + len(u16) + crc(u16) + payload。头共20字节，payload最多512字节。CRC16-CCITT-FALSE 覆盖 type 到 len（14字节）及 payload，防止通道头损坏。

RESET/READY 建立 epoch；OPEN/OPEN_OK 建立通道；每个方向一次只允许一个 DATA，接收方写完对应 Socket 后才 ACK。顺序号16位循环，token32位区分重开的通道。三路公平轮询，固定缓冲；序号异常、CRC错误、写超时、USB心跳5秒超时会关闭通道或整条会话。帧未确认15秒关闭，不重放旧字节。USB重连使旧 epoch 失效，TLS/MQTT 重新建立。

UGV 自身网络状态仍从 UART 日志读取；此轮未实现 UGV 管理遥测的串口 MGMT 扩展。CRC 只检测串口损坏，身份与保密由 TLS 提供。

## 6. 验证状态与验收

```powershell
uv run --locked python -m unittest discover -s tests -v
```

主机测试包含三份独立证书同时完成真实 mTLS 握手并通过隧道传输二进制数据，错误服务名、错误 CA、无客户端证书拒绝，以及背压、超时、旧通道隔离、retained 状态不误判 ready 等。它们使用标准库 TLS 测试服务端和 Python 隧道实现，不等于验证 C6 固件或 Mosquitto 的实际 ACL。

硬件验收（2026-11-13，第1～6项均由用户确认通过；资源数值证据范围见最新结论）：
1. 【用户验收通过】root 连接 STA 入口，UAV/Micro 连接 UGV SoftAP 入口，三者同时 online/ready。
2. 【用户验收通过】三个节点各完成 ping/status/echo；ACK node_id/msg_id 匹配。
3. 【用户验收通过】拔 UGV USB 后所有通道关闭，恢复后重新认证，不继承旧命令。
4. 【用户确认通过】关闭 Broker、重启节点、UAV 掉电时，心跳/遗嘱使登记离线，恢复后重新就绪。
5. 【用户验收通过】实际 Broker 上测试缺失/错误证书与跨节点主题权限。
6. 【用户确认通过，资源数值证据部分提供】记录用户构建产物的 app 分区占用及 TLS 最小空闲堆；2MiB Flash 的剩余容量与最低堆尚未记录实测值。

正式 S31：删除二进制串口隧道，接入 USB NCM/ECM 网口及服务路由/映射；保留证书身份、MQTT主题和控制终端。UDP/SRT 不在此轮范围。


## bootloader-cfgcmd.txt 缺失与模式选择

当 build.ninja 存在而 bootloader-prefix/tmp/bootloader-cfgcmd.txt 缺失时，说明生成缓存不完整。tools/lab.py 在用户执行 build/flash 前会先 reconfigure，失败则停止，不删除 sdkconfig。不应手工创建空 cfgcmd 文件。

MQTT 模式必须显式指定 `--transport mqtt_serial`；省略时仍是旧 legacy 模式。当前 root COM7 的 MQTT 操作示例（由用户执行）：

```powershell
python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --topology chain reconfigure
python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --topology chain --port COM7 flash
```

第一条重新生成 CMake 配置，第二条 flash 按 ESP-IDF 默认行为会先编译。固件仍使用 ESP-IDF Python 环境；uv 管理的 .venv 用于主机工具。


## 2026-11-13 现场接入记录

初次接入记录的端口：root COM7、UGV COM4、UAV COM5，当时 Micro 暂未连接；后续用户已确认三客户端验收通过，Micro 端口未提供。项目 Broker 已单独启动于 127.0.0.1:8883；现有 Windows Mosquitto 服务监听 1883/9883，保留运行。端口不一致曾导致 WinError 10061。

Windows 上 select([], [], [], timeout) 会报 WinError 10022，现已在 USB 已就绪、尚无 TCP 通道时跳过 select；新增回归测试。修复仅涉及电脑转发程序，无需重刷固件。

现场 Broker 日志确认 pc-root-001 已通过认证，经 COM4 隧道上报 capabilities、presence 与周期 telemetry；控制终端已收到转发。后续用户已确认 UAV/Micro 同时就绪以及三个节点的 ping/status/echo、ACK 匹配和 USB 断开恢复通过验收。现有后台转发占用 COM4，不能同时启动第二个转发进程或串口监视器。


## 最新用户验收结论（2026-11-13）

用户确认第 1～3 项通过，属于现场验收结果，独立于 45 项主机自动测试。不将这些结果扩展为第 4～6 项已经完成。后续依次验证 Broker/节点故障恢复、真实 Broker 的证书与跨节点主题权限，以及固件容量和 TLS 最低空闲堆。本次仅更新记录，不触发设备重启、Broker 停止、串口操作或构建。


第4～6项的详细步骤、真实 Broker 权限工具及内存/分区检查，见 [后续验收指南](mqtt-acceptance-4-6.md)。新增 heap_min 需用户重新编译烧录；主机检查工具不运行固件构建。


用户补充实际 Broker 安全工具完整输出：10 项 PASS，第5项验收通过。包括正向权限对照、跨节点发布与订阅隔离、缺失及不可信客户端证书拒绝。当前第1、2、3、5项通过，第4、6项仍待验收。


## 用户确认六项验收全部完成

用户确认第1～6项全部完成，记录为用户现场验收结论。所附容量输出确认 root 1194416/2031616、UGV 1077408/2031616、UAV 1194560/2031616 字节均通过；默认路径 build/mqtt_serial/micro_uav-chain 未找到构建产物，因此该次工具输出没有验证 Micro 的镜像容量，不代表节点离线。各节点 heap_min 数值尚未附入记录，不补造测量值。实际 Broker 的 mTLS/ACL 十项检查已有完整 PASS 输出。此前“待验收”段落保留为历史过程，以本结论及 verification-mqtt-serial.json 为准。
