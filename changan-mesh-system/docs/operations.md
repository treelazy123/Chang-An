# 运行与排障

## 准备

在主仓库执行，配置生成不重启服务、不签发凭据：

```powershell
cd D:\changan\changan-mesh-system
uv sync --locked
uv run --locked python tools/run_tests.py
uv run --locked python tools/configure_broker.py --inventory config/nodes.json --acl-file runtime/ugv-root/acl.conf --output runtime/ugv-root/mosquitto.conf
```

切换前由用户正常退出占用同一身份、端口或COM口的实例。下列程序分别启动，不重复启动。

## 根节点主机

```powershell
& 'D:\Program Files (x86)\Mosquitto\mosquitto.exe' -c 'D:\changan\changan-mesh-system\runtime\ugv-root\mosquitto.conf' -v
```

```powershell
uv run --locked ugv-service --config config/ugv-root.dev.toml
```

用户完成新固件烧录后，以实物端口替换COM_ROOT：

```powershell
uv run --locked ugv-serial-bridge --port COM_ROOT --broker-port 8883 --ugv-id ugv-root
```

根节点原生USB用于MUX1，日志用UART0。后台默认只监听127.0.0.1:8080；它不是公网入口。
任务与主机journal位于runtime/ugv-root。controller-001由排他锁保护，不能同时开多个后台。

## 终端

```powershell
cd D:\changan\changan-car-terminal
uv sync --locked
uv run --locked python -m car_terminal.gui --base-url http://127.0.0.1:8080
```

GUI打开后手动连接。CLI：`uv run --locked python -m car_terminal --command list`。
主仓库维护查询可用`uv run --locked ugv-console --command "ping ugv-001"`，同样走HTTP。
终端不需要COM口或节点证书。关闭终端后后台继续管理任务。

## 准入管理与排障

节点页显示信任状态和授权版本，选择后可授权接入或撤销。CLI支持
`node admit NODE_ID REVISION`、`node revoke NODE_ID REVISION`、`node pending NODE_ID REVISION`。
版本按实际查询填写，不自动覆盖冲突。授权仅限已登记且归当前root管理的节点。
后台写入清单和审计，生成runtime/ugv-root/acl.pending.conf；Broker ACL加载由用户受控执行。

HTTP无法连接时检查后台及8080端口；Broker离线不等于无线设备断开。ready需要当前boot的
presence、capabilities和新鲜telemetry。根C6状态还依赖有效USB NETWORK报告。
2026-11-25已移除认证失败主动退网和重启解锁机制，TLS失败后恢复重试。
新增[ESP-NOW逐层父节点认证](逐层父节点认证.md)源码：各中继AP可保持广播，子节点验签后才允许选择。
部署须准备独立签名身份、更新根桥接和Service以及参与测试的全部C6；当前尚未完成固件构建和无线实物验收。
授权撤销不会证明既有物理任务停止。请求超时先按task_id查询，不盲目重发。
不得删除数据库、journal、证书或私钥来修复连接。

### 能力公告接收确认测量

本项接收端为UGV Service，车机为记录展示端。新固件对每条实际发布的`capabilities`
增加boot_id/序号组成的唯一cap_id及节点单调时间；后台经现有注册表校验和清单授权，
持久化原文后返回随机令牌的应用回执，节点用同一本机时钟计算确认耗时并上报。
它包含公告构造、入队、现有MQTT/TLS/Mesh/root USB链路、后台校验入库、回程及节点处理，
不包含结果上传或车机显示时间。不使用跨设备时间相减，也不使用MQTT PUBACK作为应用接收证据。

指标名称固定为“接收确认耗时（单向接收延迟上界）”，阈值800ms。
≤800ms证明公告已在时限内被接收；超过800ms仅表示不能用本次上界证明达标，
不能直接宣称精确单向延迟超标。节点回执等待上限2秒，后台从请求发出等待完整结果5秒。
过期缓存、错误来源、启动/序号/令牌不匹配和不完整的智能体类型/基础能力/任务状态不计成功。
相同公告重复到达只累计重复次数；同ID不同内容拒绝，结果重复上报不覆盖首次有效记录。

部署与演示：

1. 部署方更新UGV Service与独立车机，在维护窗口重启后台；用户构建/烧录参与测试的普通节点。
   根节点仍是透明USB隧道，沿用Broker ACL与节点身份，不需要重新签发证书。
2. 打开车机连接后台、刷新节点，确认测试目标就绪并已公告`cap_measure_v=1`。
   进入“能力公告验收”，填写例如`ugv-001,uav-001,uav-002,micro-001,micro-002`。
   `ugv-root`本地服务不冒充远程节点测量样本。
3. 默认每节点30条、间隔1000ms，点击“开始新测试”。一批最多16节点×100条，
   同一时间一批测试、每节点最多一个请求在途；间隔表示最短派发间隔，不能当作实际发送频率。
4. 查看计划数、实际登记数、已确认数、证明≤800ms数量/比例，以及平均/P95/最大值。
   “实际登记”才是有效接收的公告条数，不能用计划数替代≥3条公告的证据。
   表格逐条展示智能体类型、基础能力、任务状态和超时/错误/未就绪/中断。
   平均/P95/最大只统计有效确认样本；证明比例分母为全部计划样本，失败不会显示成0ms。
5. 点击页内“导出 CSV / JSONL”，从后台导出完整批次，包括原始公告、结果和缺失样本。
   JSONL首行保存配置及汇总，后续每行一条计划记录；CSV为UTF-8 BOM，便于Excel查看。
   此导出不受下方调试结果“最近2000条”的限制，CSV/JSONL均保留公告ID与批次ID用于核对。
6. “历史批次”加载最近50个批次编号，选择后查询；提交超时后查询当前保留的批次ID，
   不盲目创建新批次。关闭车机后后台继续测试；后台重启将未完成样本记为INTERRUPTED，不自动重跑。

全部记录保存在配置中现有task_database的`cap_batches`、`cap_probes`和`cap_announcements`表，
新增表不删除既有任务/身份；普通非测试公告也自动记录在cap_announcements。
本功能的诊断批次使用新增本机HTTP v1路径，不改变既有MCI任务操作或WebSocket格式。
线格式和安全边界见[能力公告测量v1](../protocols/capability-measure/v1/README.md)。
主机测试可验证真实应用回执链路和实际C计时状态机，但不能代替ESP32无线实测。
代理未构建/烧录固件、未操作现场服务或COM口；实机≤800ms需导出本轮现场记录后判断。

### 接入时延优化与复测

2026-11-24源码优化：每次TLS/MQTT连接、命令/任务订阅及可信时钟准备完成后，
立即发送本轮首条非retained遥测（QoS 1），其后恢复原配置的遥测周期。
入队失败会继续尝试，不把失败当成已发送。后台仍要求同boot的presence、合法capabilities
和新鲜的实时telemetry，不提前放宽ready条件。

服务发现启动后及下游STA加入后的8秒内每500ms公告，稳定后恢复3000ms；
中继收到新一代公告时立即唤醒转发任务。重复公告不刷新原记录的15秒有效期。
收到有效发现或STA取得IP会唤醒MQTT连接任务，保留1秒有界等待作为兜底。
后台收到有效节点观测或Broker连接状态变化后唤醒已有WebSocket，仍保留2秒周期校正。
车机无需更改协议或更新程序。该轮未修改扫描；后续扫描与关联优化见下节。

部署需由用户构建/烧录：至少更新ugv-root和ugv-001，其他中继和叶节点更新后也会受益；
由部署方在维护窗口重启更新后的UGV Service。不要为此重新签发身份或清除NVS。
单节点接入复测时，先保持根节点、Broker和USB桥稳定运行，再给ugv-001上电；
若验收要求全网同时上电，需另测该条件，不能用单节点结果替代。

UART0日志包含ACCESS_PHASE的NETWORK_START、STA_CONNECTED、GOT_IP、
MQTT_TASK_STARTED、MQTT_CONNECT_START、MQTT_CONNECTED、COMMAND_SUBSCRIBED、
TASK_SUBSCRIBED、CLOCK_RECEIVED、APPLICATION_READY、FIRST_TELEMETRY_ENQUEUED。
UGV_SERVICE标记发现地址；ESP日志前缀及uptime_ms用于本节点内分段。
FIRST_TELEMETRY_ENQUEUED仅表示入队，后台NODE_READY日志才表示已收齐就绪材料。
主机host_monotonic_ms与节点uptime_ms不是同一时钟，不能直接相减。
上电到车机显示就绪仍需用同一外部计时基准（如连续录像）复测；固件阶段日志
不包含上电到应用启动之前的全部时间，也不能据源码优化宣称已满足5秒。

### 2026-11-25 扫描、关联和发现补发

新增`firmware/components/mesh_access`，在工程链接阶段包装Wi-Fi扫描、连接及STA配置入口，
覆盖预编译Mesh核心的调用。共享SDK、第三方源码及原TLS/父认证身份不改动。
扫描配置只读取Mesh 1.0.2与当前SDK的公共前缀，重新构造IDF 6.1配置，清零位图等扩展字段；
ESP32-C6构建含前缀偏移静态断言，SDK布局变化时应审查适配，不能删除断言绕过。

所有非根节点离线时，前三次扫描优先使用上次成功信道，无缓存则用配置的Mesh信道；
仅第一次可附带上次成功BSSID提示，第四次全信道回退，循环直到成功。
主动扫描每信道40～60ms为本轮调优起点；扫描范围、耗时、ESP-NOW证明收发和漏扫率需板上检查。
父证明触发一次安全的选父重试时，重新分配三次优先信道扫描机会；认证前的扫描次数
不消耗这段机会。证明后的第一次扫描不再绑定旧BSSID缓存，仍由认证白名单决定候选。
这修正了现场日志中第三次快速扫描后收到证明、下一次立即落入约2秒全扫描的情况。
`mesh_access` NVS命名空间只保存信道/BSSID提示，不保存或恢复认证结果；
已有身份、任务及父策略NVS不删除，父节点每次仍需本轮nonce验证和合法层级/身份检查。

UGV、UAV、Micro共用有界选父调度：优先扫描阶段离线重试最短500ms，
全扫后的离线重试2秒；新证明可请求更快重评估，但扫描结束后至少留100ms给Mesh处理结果。
扫描和关联中不发起重复扫描/连接，不在关联中改STA配置；关联10秒未结束时先请求断开，
收到断开事件后才允许重新选父。此10秒为异常恢复界限，不表示成功接入的达标时延。
父证明到达不再仅加速叶节点，缓存连接事件也避免了每50ms查询未连接STA产生的Wi-Fi告警。

节点取到IP后若没有仍有效的根服务缓存，立即经现有Mesh JSON控制消息请求公告，
500ms重试、单次窗口8秒。父节点收到查询后补发当前有效公告，没有缓存则向上游请求；
中继不延长同一代公告的15秒有效期。IP就绪和查询事件也开启8秒快公告，
广播最短间隔100ms用于合并并发请求，稳定态仍为3秒公告。
新消息格式见[发现控制协议](../protocols/discovery/v1/README.md)。

本轮不自动踢除STA，不更改PMF。ugv-001作为父节点时，`PARENT_ASSOC_CHECK`记录
挑战中的子MAC当前是否仍在AP关联表。`already_associated=1`只是旧关联排查线索，
不是身份核验或允许踢站的依据；现有挑战本身不证明子设备持钥。
针对日志中约1.6秒的临时拒绝关联，需同时保存父/子日志，比较正常断开与直接断电后的重连，
确认原因后再修复，不能据此降低认证要求或广播断开其他STA。

由用户更新至少`ugv-root`、`ugv-001`及被测`uav-001`固件。旧父节点不识别查询时，
原周期公告仍为回退，但无法获得本轮补发收益；其他参与节点应随后更新。
本轮无后台/车机协议变更，继续使用已有逐层认证版UGV Service和USB桥。
无需重新登记密钥、擦除NVS或修改分区。代理未执行固件构建/烧录、现场服务重启或串口访问。

复测先保持上游稳定，给uav-001单独冷启动至少20次，保留失败样本；
然后验证父节点不可用、信道变化、父证明错误/过期、正常断开和突然断电的恢复。
日志重点：`SCAN_START mode=preferred/fallback channel=... bitmap=0`、`SCAN_DONE elapsed_ms`、
`SELECT_RETRY`、`ASSOC_START`、`ASSOC_TIMEOUT`、`PARENT_VERIFIED`、`SERVICE_QUERY`、
`UGV_SERVICE`、各`ACCESS_PHASE`及后台`NODE_READY`。优先验证无效位图错误是否消失、
关联中是否停止重扫、IP到MQTT连接是否免等周期公告，再评估最大上电到车机就绪时间。
本机C函数回归使用假RTOS、Wi-Fi、NVS，不能验证真实链接、射频、回调并发或≤5秒。

2026-11-25现场反馈：uav-001本轮首条遥测在日志前缀8.843秒入队；取得IP至MQTT连接开始
为38ms，服务发现等待已显著缩短。父证明在2.319秒通过，但随后全扫用了2.022秒，
属于上述调度缺陷，已在源码修正，尚待新固件复测。父AP约1.6秒关联延后仍存在。
新增限频`AP_DEAUTH_REQUEST node=... aid=... count=... caller=...`追踪公开Wi-Fi
deauth入口，原驱动调用及返回值保持不变；`caller`需结合该板实际ELF解析。
驱动内部的deauth路径不一定经过此入口，因此没有该日志不能证明没有内部deauth。
排查uav-001向上游重连应采集ugv-001上的`PARENT_ASSOC_CHECK`，子MAC为
`ac:eb:e6:d9:d5:5c`；uav-001自身输出的此日志描述其下游候选，不能替代上游证据。

<a id="parent-selection"></a>

## Micro父节点选择

终端“网络结构”页提供“Micro上游连接设置”。先刷新节点，填写或选择Micro，点击查询配置，
再选择父UAV和模式，点击应用。期望父节点与实际父节点分别显示，已接收不代表切换成功。

| 模式 | 行为 |
| --- | --- |
| 自动 | 允许所有符合原Mesh ID、角色层级等条件的候选父节点 |
| 优先指定 | 先限制到指定UAV；启动、切换或目标断开后等待30秒，未连接目标则允许自动选择 |
| 固定指定 | 只允许指定UAV，目标不可用时保持离线 |

优先模式回退后保持自动候选，直到重新应用配置或节点重启，不主动反复抢回目标。
Micro仍固定第4层，父UAV必须为同root下已授权、在线的第3层节点。
父UAV还须报告parent_auth.relay_authorized=true；候选选择及自动回退均受固件的ESP-NOW验签约束。
固定/优先模式同时核对签名中的父节点ID和所选BSSID。
父节点必须上报真实AP MAC、AP SSID及AP启用状态；旧固件缺少这些字段时拒绝配置。
Micro本身必须已授权、就绪，并公布parent操作能力。

### 调用与状态

车机通过本机HTTP/WS访问UGV Service。后台检查清单和新鲜观测，将父节点ID解析为BSSID及SSID，
通过现有MQTT/TLS commands主题下发op=parent。用户不能绕过后台直接指定任意BSSID。
SQLite parent_policies表先记录意图、请求ID和版本，再下发；服务重启与请求超时均不自动重发。
再次提交必须先查询配置版本。相同请求ID及相同内容不会重复派发，不同内容返回冲突。

Micro验证命令有效期、可信时钟和版本后，将策略保存在独立NVS命名空间parent_policy。
命令接收后约2秒触发Mesh重新连接，给ACK入队留出时间，不保证ACK必然在断线前到达。
MAC白名单使用当前Mesh-Lite的esp_mesh_lite_get_ssid_by_mac_cb_register接口，
所有自动候选SSID按本项目公共前缀（前20字符）加AP MAC后缀的约定生成；不要对个别节点使用不同SSID前缀。
仍由Mesh-Lite完成合法Mesh候选筛选、层级约束与连接，不单独用Wi-Fi连接替代组网。

仅当Micro以当前启动的新鲜遥测报告相同策略版本、模式及匹配的实际父BSSID时，后台显示已生效。
遥测中pending阶段不算生效；prefer模式报告fallback时显示已回退。60秒未收到确认显示未确认，
不能据此断言未执行。没有重连时通过查询观察状态，不自动创建新请求重试。
STA地址及网关仍从所连接UAV的DHCP获取，Micro不启用AP。

### 部署与固定模式恢复

实际编译、烧录由用户执行。先更新UAV固件，使其上报AP SSID，再更新Micro固件。
重启后台加载新代码，重新打开终端；不需要重新签发已有证书或擦除NVS。
若Micro遥测持续更新、父链路已连接，但显示“在线·未就绪”，请先核对后台是否已更新并重启。
旧后台不识别新增的parent操作，会拒收新能力公告，使业务就绪检查无法通过；遥测年龄小只表示遥测新鲜，不能替代能力校验。
开发环境在原UGV Service窗口停止旧进程后，从项目根目录重新运行：

```powershell
uv run --locked ugv-service --config config/ugv-root.dev.toml
```

现有构建缓存如果提示不匹配，按固件说明为该设备使用一次--reset-config。

固定模式离线后，远程“自动”命令无法送达。需先恢复目标UAV，或使用维护固件：
在该Micro的menuconfig打开APP_PARENT_POLICY_RECOVERY_AUTO后由用户构建、烧录。
维护固件暂时忽略已保存的绑定并自动联网，不清空其他NVS数据；连上后在终端查询并应用自动模式，
保存新的策略。随后关闭维护选项，恢复正常固件。注意--reset-config会重建SDK配置，
维护选项应在重建配置之后设置。不要通过擦除NVS、删除任务数据库或重建密钥恢复连接。

Micro离线期间每2秒请求Mesh-Lite重新扫描；收到新的有效父节点证明后可提前触发，
认证触发的请求与上次请求至少间隔500毫秒。该恢复路径只请求选父，不先断线清空刚收到的证明，
也不改写保存的固定绑定。固定模式仍不会连接其他UAV，目标恢复授权后须重新验签才能连接。
日志`PARENT_RESCAN`表示已请求重扫，`PARENT_VERIFIED`表示候选验签通过，
仍须以Micro的新鲜遥测及就绪状态确认实际恢复。如果只有重扫而无验签成功，
需保留Micro和目标UAV现有日志，核对ESP-NOW通信及目标中继授权。
`PARENT_RADIO_SEND_FAILED`记录认证无线发送错误，`STA_DISCONNECTED`记录Wi-Fi断线原因。
Micro启动时的`PARENT_POLICY`日志给出该次启动实际生效的模式、版本和绑定。
普通固件更新保留NVS中的固定模式；仅更新重扫逻辑不会将固定模式改成自动。
Micro无当前遥测时，终端查询到的模式来自后台保存的配置，不能据此确认新固件实际模式。
本地构建配置中`CONFIG_APP_PARENT_POLICY_RECOVERY_AUTO=y`才会启用本次启动的维护自动选父；
`# CONFIG_APP_PARENT_POLICY_RECOVERY_AUTO is not set`表示未启用。维护模式也必须通过父节点认证。

后台任务数据库与Micro的策略版本必须一并保留。若恢复了过旧的后台数据库，节点可能拒绝旧版本，
应恢复正确的数据库备份并核对节点遥测，不得绕过版本检查盲目重发。

## 常见故障速查

| 现象 | 检查与处理 |
| --- | --- |
| 终端无法连接 | 检查后台、HTTP 地址及 8080 端口；终端打开后需手动连接 |
| 遥测很新但显示未就绪 | 核对当前启动的 presence、capabilities、telemetry；旧后台拒收新增 parent 能力时，停止原后台并按上方命令重启 |
| 父节点应用出现 parent_apply KeyError | 更新并重新打开终端；新版已补齐按钮标签 |
| 节点选中后跳掉、输入被覆盖 | 更新并重新打开终端；新版刷新保留选中行、焦点和编辑内容 |
| 中继 AP 地址重复 | 按固件手册核对清单并逐台更新固件；重启后台不改变设备地址 |
| Cached sdkconfig does not match | 按固件手册为该设备使用一次 --reset-config，核对实物身份和端口 |
| 固定父节点后离线 | 恢复目标 UAV，或按本页维护步骤恢复；离线节点收不到远程命令 |

“在线·未就绪”表示 MQTT 在线但业务校验未通过，不能仅凭遥测年龄小跳过能力和授权校验。
