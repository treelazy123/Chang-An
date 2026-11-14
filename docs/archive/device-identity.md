# 通用设备编号、发证与烧录（0.5.0）

目标：任意新设备只增加受控登记，不修改节点名单源码；每种现有角色均可有多个独立实例。固件仍针对 ESP32-C6。本轮未运行固件 build/烧录，也未自动重启 Broker、串口隧道或在线节点。0.4.0 的六项现场验收属于旧版本结果，新身份/扩容功能需要用户上板验收。

## 身份与角色

- role 选择 pc_root / ugv / uav / micro_uav，决定职责与链式层级。
- node_id 是管理员在烧录时明确指定的全局唯一设备编号，1～32个 ASCII 字母、数字、横线或下划线，不自动按接入顺序编号。拒绝路径、保留控制身份、Windows 设备文件名，以及仅大小写不同的重复编号。
- 同一编号重复操作复用相同证书/私钥；不重建CA、不覆盖旧设备身份。编号绑定角色，不能把已登记的 Micro 编号再当 UAV 烧录。
- 每个设备目录为 secrets/<node_id>/，包含独立 client.pem、client.key、ca.pem、identity.json 和该设备的配置默认文件。构建前验证CN、CA签名、证书有效期、用途、私钥匹配与登记指纹。
- UGV 也签发/保留独立身份证书，但当前UGV是透明USB网关，不作为MQTT客户端，证书不参与网关自身MQTT登录；不能据此声称USB网关另有认证协议。
- MAC、IP、COM端口和boot_id都不替代永久node_id。不要给两块同时在线的板使用同一个编号/证书。

## 任意新设备的统一流程

以新UAV uav-017为例，管理员先登记（可在无IDF环境的电脑上做）：

```powershell
uv run --locked python tools/provision_mqtt.py --role uav --node-id uav-017 --ugv-id ugv-001
```

该命令使用现有CA增量发证、更新公开清单 host/config/nodes.json 和生成的 host/runtime/acl.conf，不重置任何已有密钥。重复执行同一身份只验证并复用，不换证书。换成任何现有role和合法新编号，流程相同。全新角色/全新硬件目标仍需固件实现，不能仅修改名称。

用户在ESP-IDF环境烧录：

```powershell
python tools/lab.py --transport mqtt_serial --role uav --node-id uav-017 --ugv-id ugv-001 --topology chain --port COM实际端口 flash
```

lab.py 也会自动执行登记/校验，因此单条烧录命令可为新编号准备证书，但需要先初始化过CA。MQTT的实际构建、配置、监视、烧录操作现在必须明确传 --node-id，防止误用默认身份给多块板烧相同编号。旧命令省略ID仅允许 --dry-run 兼容预览；legacy模式保留原入口。

每个实例隔离在：

```text
build/mqtt_serial/nodes/uav-017/uav-chain/
secrets/uav-017/build/mqtt_serial-chain.defaults
```

生成的实例默认文件放在最后，覆盖共享角色配置中的默认编号。缓存中的角色、编号、拓扑、传输模式及UGV目标不匹配时拒绝操作，不复用其他设备镜像。不要手工复制sdkconfig或私钥目录到另一个编号。

## 当前五块板的用户烧录命令

root COM7、UGV COM4、UAV COM5按用户此前提供；两块Micro的端口需替换为各自实际值。烧录UGV前先关闭占用COM4的串口转发，完成后重开。

```powershell
python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --port COM7 flash
python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --port COM4 flash
python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --port COM5 flash
python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-001 --port COM_MICRO1 flash
python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-002 --port COM_MICRO2 flash
```

以上五块的身份材料已经准备好；原有17个证书/密钥文件哈希保持不变，ugv-001和micro-002是新增身份材料。命令不会由代理自动执行。

## 其他编号的UGV/root同样支持

```powershell
uv run --locked python tools/provision_mqtt.py --role ugv --node-id ugv-002
uv run --locked python tools/provision_mqtt.py --role uav --node-id inspection_017 --ugv-id ugv-002
python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-002 --port COM实际端口 flash
python tools/lab.py --transport mqtt_serial --role uav --node-id inspection_017 --ugv-id ugv-002 --port COM实际端口 flash
```

先登记目标UGV，再登记它的客户端。UGV的服务ID自动等于自身编号；客户端根据 --ugv-id 或已登记关联选择服务，不能只改UGV编号而保留客户端目标为旧值。UGV目标仍须在实际物理链路中可达；当前固定链式拓扑要求配置与部署一致。每个 Mesh 保持一个活动root；“所有角色支持不同编号”不表示同一Mesh支持多个同时活动的固定root。

## 新设备加入结果与权限生效

管理员登记/发证 → 独立镜像烧录 → Mesh接入/IP → 发现指定UGV → 独立TLS会话 → 按证书身份执行主题ACL → 上报本轮能力/在线/遥测 → ready → 可执行测试命令。

终端已移除三设备硬编码，运行中新版每次接收消息及周期任务都会检查管理员清单，添加新ID并恢复其retained能力/在线公告，禁用项移出可控清单。新设备必须收到新鲜遥测才ready，不根据任意MQTT消息自行授权。

ACL仍采用明确逐设备授权。新增登记后需要用户重载或重启项目8883 Broker，使磁盘ACL生效；修改清单不等于运行中的Broker已加载权限。此步骤不会由发证工具自动执行，避免突然断开现有节点。新版控制终端无需为后续新增编号改源码或重启；从旧版本升级时先重启一次。

```powershell
# 用户安排维护窗口，重启项目Broker后保持运行
& 'D:\Program Files (x86)\Mosquitto\mosquitto.exe' -c D:\esp\mesh_lite_node\host\runtime\mosquitto.conf -v
# UGV刷好后重新开启一个COM4转发实例
uv run --locked python tools/serial_tcp_bridge.py --port COM4 --broker-port 8883
# 升级到本版后重开一次终端；以后清单可自动重载
uv run --locked python tools/mqtt_terminal.py --broker-port 8883
```

如果已有8883 Broker在运行，应先按项目进程停止/重载，不能并行重复绑定8883；原有1883/9883服务保持独立。控制终端只列MQTT客户端，UGV网关本身仍从UART0查看网络状态。

```text
mqtt> list
mqtt> ping uav-017
mqtt> status micro-002
mqtt> echo micro-002 hello
```

新增角色实例不限制必须使用uav-/micro-前缀，inspection_017等合法资产编号也可以。

## 并发容量与清单数量

登记清单可以持续增加，UGV的实时USB隧道容量由 APP_MQTT_MAX_CHANNELS 配置，当前默认8，范围1～8；电脑转发程序同样支持8通道。增加设备不需要为每个编号加数组项，但同时在线仍受Socket、Wi-Fi关联、RAM和带宽约束。三类TCP关系不变，实例连接数可增加。用户需重新编译/烧录UGV才能把旧3通道网关升级；同时重启电脑转发程序以加载新版8通道解析。

未来超过8个并发客户端需做资源评估并扩展网关/主机协议上限，不能把有限硬件描述为无限接入。本轮主机测试验证四客户端同时完成真实TLS；八客户端和新增五板部署尚未上板验收。

## 清单与产物查询

```powershell
uv run --locked python tools/provision_mqtt.py --list
uv run --locked python tools/check_firmware_size.py --node-id micro-002
uv run --locked python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-002 --port COM实际端口 --dry-run flash
```

容量工具按清单检查每个实例目录；默认身份在隔离目录不存在时兼容查找旧build/mqtt_serial/<role>-chain。新编号绝不借用其他编号的产物。dry-run不发证、不写配置、不下载、不构建、不连接串口。

host/config/nodes.json包含可公开的角色/身份/目标关联，应由管理员控制；secrets/已忽略提交。撤销设备时先禁用清单，再执行 `uv run --locked python tools/provision_mqtt.py --sync-acl` 并重载项目Broker；证书吊销、续期与资产退役属于独立管理流程，本轮没有实现自动换证。现有实验时钟下限也不是生产可信RTC或吊销机制。


节点清单数量不写死；终端热加载管理员登记，Broker保留逐设备ACL，因此新设备首次接入前仍需部署新增权限。该步骤不是自动信任任何邻近设备。legacy保持原四角色配置；按设备发证/隔离烧录使用mqtt_serial模式。


## IDF Python 没有 cryptography

lab.py 现在把证书操作与IDF构建环境分离：当前Python可用cryptography时直接验证；否则调用项目 `.venv` 的 identity_worker.py。子进程移除继承的 PYTHONHOME/PYTHONPATH，证书结果只返回身份元数据，不返回私钥。IDF工具依然由 idf_env.py 选择自己的环境。

若主机环境尚未同步，先运行 `uv sync --locked`；无需向IDF Python安装cryptography。之后原 `python tools/lab.py ... flash` 命令不变。此修复已用缺失cryptography的Python验证只读UGV身份，未运行build/flash。
