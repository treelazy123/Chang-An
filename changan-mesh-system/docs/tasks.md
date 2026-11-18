# M1 任务操作

支持 diagnostics、UGV主机 network_diagnostics/task_monitor，以及Micro的patrol、UAV的anomaly_review。后两项仅为显式esp32_test模式的业务流程验证，见 [ESP32巡检与复核说明](#esp32-workflows)。主机服务的计时和步骤见 [主机服务说明](#host-services)。C6 diagnostics采集真实Wi-Fi RSSI、空闲堆及样本数；根节点主机 diagnostics标明source=ugv_host。

支持创建、查询、列表、开始前配置更新、开始、暂停、恢复、取消、进度与事件补查、持久化及失联/重启对账。保留基础list/ping/status/echo。task.events默认查询任务状态日志，scope=incidents查询巡检测试异常事件；不控制飞行、主控、相机、UWB或真实运动，不支持运行中配置热更新。

启动车机与后台见 [运行说明](operations.md)，身份/固件准备见 [固件说明](firmware.md)，权限与部署切换见 [部署说明](deployment.md)。代码职责见 [系统架构](architecture.md)，线协议以 [v1 合同](../protocols/v1/README.md) 为准，实物结论见 [验收状态](status.md)。

GUI 的任务页提供常用控制，CLI/API 可更新 CREATED 配置。GUI 控制使用已查询版本；CLI 未显式指定版本时先查询，再提交一次控制。两者都不自动覆盖版本冲突或重发超时操作。

## 阅读导航

- [基础命令](#车机基础命令)：创建、控制、删除及补查。
- [主机诊断与运行监视](#host-services)：计时含义、GUI 和 CLI。
- [ESP32 流程验证](#esp32-workflows)：Micro 巡检与 UAV 复核测试。

## 车机基础命令

```text
help
list
ping micro-001

task create micro-001 30 1000
task list
task get TASK_ID
task update TASK_ID 1 60 500
task start TASK_ID
task pause TASK_ID
task resume TASK_ID
task cancel TASK_ID
task delete TASK_ID

task events 0 TASK_ID
watch TASK_ID
```

create 返回 task_id，任务初始为 CREATED，不自动开始。示例命令中的 TASK_ID 要替换成返回值。update 示例将 revision=1 的未开始任务修改为 60 秒、500 毫秒采样周期，成功后 revision=2。

start/pause/resume/cancel 可选显式 REVISION；省略时车机先查当前版本，再提交一次控制请求。版本冲突会明确拒绝，不自动覆盖或重试。update 仅允许 CREATED 状态，开始后要使用新的任务配置，不能假装已热更新。

`task delete TASK_ID [REVISION]` 删除单条已结束的历史任务；API 为 `TaskClient.delete(task_id, revision=None)`。GUI 在“服务任务”页选择并查询历史任务后，点击“删除所选历史任务”。仅 SUCCEEDED/FAILED/CANCELLED/REJECTED/EXPIRED 允许删除，CREATED/QUEUED/RUNNING/PAUSED/UNKNOWN 等任务应先取消并确认终态。仍被未结束的 task_monitor 引用时返回 task_in_use_by_monitor，应先结束该监视任务。

删除通过既有 `task.control`、`op=delete`、`expected_revision` 实现，不需要更新 root/C6 固件；需要更新后台与车机。返回 `task.reply`，携带 `stage=DELETED, deleted=true, task_id, state_seq`。只能删除本人任务，本地维护入口保留管理员范围；旧节点从清单移除后仍可清理本人终态历史。未知任务返回 task_not_found。

删除在一个事务中清除 tasks 主记录、对应 operations 和原 task_events；插入一条最小 DELETED 游标事件，其他车机补查时移除列表项。保留任务ID删除标记及请求内容指纹，原创建/控制缓存响应被替换为删除结果，避免旧请求返回已删除任务；同一删除请求可幂等重放，已删除ID不可重用（task_id_deleted），新任务使用新ID。保留列表游标单调递增，删除最高序号后新任务仍可被分页发现。

这不是清空存储：不会删除其他任务、已结束监视任务的历史摘要、车机已经导出的日志或设备NVS最近任务摘要；无需在线擦除设备NVS。终态执行器迟到的反馈不会恢复已删除任务。

task list [CURSOR] 每次返回一条任务及 cursor/more；task events [CURSOR] [TASK_ID] 每次返回一条任务状态记录。more=true 时携带返回游标继续查询。watch 自动补查，按 Ctrl+C 返回提示符，后台任务继续运行；游标可用于断线后续查。

独立代码调用：TaskClient.create/get/list/control/update/events/watch。create 可由调用方预先指定 task_id；提交超时时按该编号查询，不盲目重复创建。

基础 list 在新后台中会额外展示 UGV 本地主机执行能力。C6 就绪且 task_types 包含 diagnostics，才表明已刷入支持任务的新固件；旧固件依然可以 ping/status/echo。对通信就绪但没有新任务能力的节点开始任务，会返回 node_task_firmware_required。

## 接口契约

所有公开请求沿用 v=1，带 type、msg_id、deadline_unix。HTTP接入层将调用者绑定为本机操作员 http-local；节点身份由现场mTLS与清单校验。命令 TTL 最多 60 秒，任务采样时长单独由 config.duration_s 表示。

| type | 业务字段 |
| --- | --- |
| task.create | task_id、target、kind=diagnostics/network_diagnostics/task_monitor/patrol/anomaly_review、config，可选priority、execute_before |
| task.get | task_id |
| task.list | cursor，默认 0 |
| task.control | task_id、op=start/pause/resume/cancel/delete、expected_revision |
| task.update | task_id、expected_revision、config，可选 priority、execute_before |
| task.events | cursor，可选task_id；scope默认tasks，可选incidents（独立游标） |

diagnostics 的 config 仅允许 duration_s（1～3600）和 period_ms（200～10000），默认 30 秒/1000 毫秒。其他类型的专有字段见主机服务说明。priority 为 0～9，高者先排队；execute_before 是允许开始的 UTC 秒截止时间，不是执行完成期限。运行状态包括 CREATED、QUEUED、DISPATCHING、ACCEPTED、RUNNING、暂停/恢复/取消请求中、PAUSED、RECONCILING、UNKNOWN 及终态。

公开接口统一返回 task.reply，错误仍返回 error。提交入库返回 stage=UGV_RECEIVED；这不是执行完成。task.get 返回 last_operation，指明最近一次控制操作及其派发/核对状态，执行结果以 task.state/result 为准。

任务标识、节点标识最多 32 个 ASCII 字符；公开请求最多 512 UTF-8 字节、回复最多 1024 字节。结果与列表分页，未经声明的业务字段/场景类型明确拒绝。

任务事件以 task.event 通过 WebSocket 推送，携带 cursor、task_id、state_seq。断线后按 SQLite 游标补查，HTTP task.events 是恢复依据。

内部节点使用 task_commands/task_events；内部 msg_id 就是持久化 command_id，带目标、配置版本、持久化递增操作序号 op_seq、启动标识和短期有效时间。执行器回报带 boot_id 和 seq，旧启动、旧版本和旧序号不能回滚当前任务；迟到的旧暂停/恢复不能再次执行。车机仅通过HTTP业务入口提交操作，由后台向节点派发。

## 故障语义

- 每个物理节点最多一个活动任务；同节点后续任务等待，两个 Micro 可以并行执行。UGV 主机的 network_diagnostics、task_monitor 各有独立执行槽，可与旧 diagnostics 并行；同类型后续任务等待。
- 相同来源/msg_id/内容的提交返回原响应；内容冲突拒绝，服务重启后规则保留。
- 开始前已过 execute_before 的排队任务变为 EXPIRED。
- 暂停/取消以执行器实际反馈为准；旧操作的进度不能确认新操作。
- C6 失去 MQTT 就绪状态后暂停诊断采样，恢复后不自动继续，需明确 resume。
- 节点重启保留关键任务摘要，非终态进入 UNKNOWN。不会假装恢复了丢失的采样数据，也不会自动重新开始。
- UGV 重启保留任务和操作，先核对执行器状态，不重放开始命令；未确认控制操作可显示 uncertain/reconciled，用户按核对结果重新决定。
- 没有运行记录的任务取消会保存取消标记，阻止迟到的同任务开始命令复活。
- live 通知不自动重放全部历史，重连客户端使用游标补查；任务终态不会被后来的旧状态覆盖。

## 用户验收清单

1. 新固件节点在 list 中出现 diagnostics 能力；UGV 本地主机也可创建诊断任务。
2. 给 micro-001、micro-002 分别创建不同采样时长的任务，开始后各自进度/结果不串。
3. 测试 CREATED 配置更新与 revision 冲突；运行中更新必须明确拒绝。
4. 测试暂停期间采样不增长、恢复后继续；取消最终得到执行器 CANCELLED。
5. 对同一请求重复发送，数据库只产生一个任务；超时后按 task_id 查询。
6. 拔节点或 UGV USB、重启 Broker/后台/节点，观察 offline/RECONCILING/UNKNOWN/PAUSED 的真实恢复语义，不出现自动重复开始或虚假完成。
7. 使用 task.events 游标补查，核对所有阶段；验证新主题按设备和车机隔离。
8. 用户编译后检查 app 分区、运行堆和 NVS；主机测试不能替代新固件编译及板上验收。

主机测试包括临时 SQLite 故障/幂等/并发测试、独立车机HTTP/WebSocket测试，以及随机本地端口的实际 Mosquitto mTLS/ACL/生命周期/服务重启测试。集成测试中的节点是明确的主机测试执行器，不代表 C6 固件已上板验证。测试不连接现有 Broker 或 COM 端口。

<a id="host-services"></a>

## 网络诊断与任务运行监视

这两项服务运行在无人车主机（电脑或 Jetson）上，复用既有任务创建、开始、暂停、恢复、取消、查询及事件补查接口。需要更新无人车后台与独立车机程序，不增加节点固件指令，不构建或烧录固件。

| 服务 | 执行节点 | 检查对象 | 输出 |
| --- | --- | --- | --- |
| network_diagnostics | ugv-root（实际配置的 UGV ID） | probe_node：一个已授权的远程节点 | 完成采样数、成功数、失败数、最近/平均/最大往返耗时、最近就绪判断及错误 |
| task_monitor | 同上 | watch_task_id：当前车机有权查询的一项既有任务 | 被监视任务的执行节点、状态、进度、有效反馈年龄、反馈超时或节点未就绪、任务错误摘要 |

旧 diagnostics 保持兼容：C6 诊断采样或 UGV 原有就绪节点数采样。新服务不冒充巡检、飞控、媒体或定位执行能力。

### 网络诊断计时

每次采样检查远程节点是否就绪，只有就绪时才发送一次 ping。使用匹配的应用 ACK 确认，单次探测等待上限为 1 秒，不自动重发。探测在独立工作线程中执行，不阻塞任务控制和运行监视。

往返计时在 UGV 主机调用节点命令之前开始，在收到成功应用 ACK 后结束，包含 MQTT/TLS、Broker、转发、节点处理和主机命令处理，不含车机与无人车之间的传输，不是无线空口时延。平均值与最大值只统计成功的探测。未就绪、超时、负 ACK 和其他请求错误计入失败数；失败采样的 last_ms 为 null，不能当作 0ms 成功。

一次最多一个探测在途；采样周期小于探测耗时时不堆积请求。duration_s 是执行采样时长，最后一个在途探测处理完后才报告完成。任务完成表示诊断流程结束，是否存在网络故障应查看 failed/error，不能只看 SUCCEEDED。暂停后不发新探测；暂停前的在途结果可在暂停期间收尾计入，取消后的迟到结果丢弃。

### 任务运行监视

监视服务读取后台已接收、校验并保存的任务反馈，不重新启动被监视任务，也不向设备发送额外的控制指令。被监视任务正常的 task_events 就是数据来源。

feedback_at 专门记录有效执行器反馈的主机接收时间，不使用管理员修改任务产生的 updated 代替。数据库自动增加该可空列；升级前没有接收时间的历史记录显示未知，等待新反馈。age_s 为主机采样时与该时间的差值，非跨设备单向时延。

| health | 含义 |
| --- | --- |
| waiting | 被监视任务尚在 CREATED/QUEUED，或监视服务等待首次采样 |
| reporting | 收到有效反馈，未超过阈值 |
| feedback_stale | 没有有效反馈时间或反馈年龄超过 stale_after_s |
| node_not_ready | 被监视远程节点未就绪，保留原任务状态作为已知状态 |
| finished | 被监视任务已结束，结合 state 判断完成、失败或取消 |
| not_authorized | 相关授权已失效 |

同一车机只能监视有权查询的任务；不允许监视另一项监视任务。错误摘要限制为 48 UTF-8 字节，完整错误可查询被监视任务。监视按配置时长运行，即使对象提前结束也保留最终状态；监视任务 SUCCEEDED 不代表被监视任务成功。

### GUI 展示与现场步骤

1. 更新并由部署方重启后台，打开新版车机，连接后先刷新节点。
2. “能力服务”页点击刷新服务，查看 ugv-root/network_diagnostics 与 ugv-root/task_monitor。每条信息包含服务 ID、节点 ID、智能体类型、基础能力、控制操作、可用状态、当前任务状态和 boot_id。选择服务可带入执行主机及服务类型。
3. “服务任务”页选择网络诊断，执行主机填写实际 UGV ID，被检查节点填写例如 micro-001。填写时长30秒、周期1000ms，创建后再开始，勾选持续补查事件。
4. 查看任务下方的成功/失败与 RTT 统计；原始结果和车机操作总耗时可导出 JSONL。二者不是同一计时指标。
5. 为远程节点创建并开始基础诊断任务，取得该任务 ID。再选择“任务运行监视”，填写该 ID、时长60秒、周期1000ms、反馈超时阈值10秒，创建并开始。
6. 暂停/恢复/取消被监视任务，观察监视结果中的状态及进度更新。网络诊断与运行监视可以同时运行；同类主机服务最多一个活动任务，同类后续任务排队；物理 C6 仍最多一个活动任务。
7. 在约定的硬件测试窗口中，使目标节点失去连接，记录网络诊断失败、运行监视的未就绪/反馈超时及恢复过程。节点就绪有自己的新鲜度窗口，不能要求物理断链瞬间状态立即改变。

服务目录使用现有 list 请求增加 scope=services，并沿用 nodes 分页回复；每帧一条服务。普通 list 仍返回节点，UGV 行 task_types 增加两种服务。该目录是车机主动查询，不宣称已实现跨节点自动公告接收或 ≤800ms 公告验收测量。

目录现同时按管理员清单汇总每台UAV/Micro的 [ESP32巡检／复核测试服务](#esp32-workflows)，显示执行节点、模式及公告/就绪状态。节点通过现有MQTT capabilities主动上报，车机通过后台查询汇总。

两个服务各有独立 journal 文件（在既有 agent_journal 后追加 .network_diagnostics / .task_monitor）。后台重启后活动任务对账为 UNKNOWN，不自动重启探测或监视；数据及历史任务保留，按核对结果取消或新建任务。

### CLI

```text
services
task network ugv-root micro-001 30 1000
task start 返回的网络诊断任务ID
task get 返回的网络诊断任务ID

task create micro-001 60 1000
task start 返回的节点任务ID
task monitor ugv-root 返回的节点任务ID 60 1000 10
task start 返回的监视任务ID
watch 返回的监视任务ID
```

公共 config：duration_s 1–3600、period_ms 200–10000。network_diagnostics 额外要求 probe_node；task_monitor 额外要求 watch_task_id，stale_after_s 默认10，范围1–3600。仅 CREATED 可更新配置，车机更新时保留类型专有字段并携带原 expected_revision。

本地回归使用临时 SQLite、假的节点通道及隔离 Mosquitto；不连接生产 Broker 或 COM 口。实际 Mesh 的 RTT、断链恢复和两个验收时延阈值仍需保存现场实测记录。

<a id="esp32-workflows"></a>

## ESP32 巡检与异常复核流程验证

本版运行到 ESP32，不接无人机主控，不控制飞行、定位、相机或识别算法。新任务的配置必须显式携带 execution_mode=esp32_test；公告、车机表单、进度与结果均标注测试模式。SUCCEEDED 表示流程验证结束，不表示真实巡检、到点或异常识别成功。

### 服务按角色提供

| 清单角色 | 公告任务类型 | 服务ID | 基础能力 |
| --- | --- | --- | --- |
| uav | anomaly_review | 实际node_id/anomaly-review | 巡检异常事件关联、复核流程、预设测试结论 |
| micro_uav | patrol | 实际node_id/patrol | 测试区域及点位、逐点流程、测试异常事件 |

不按 uav-001/micro-001 写死。例如 uav-017、micro-017、micro-018 分别有独立服务实例。管理员清单决定角色和授权；ESP32 根据固件角色公告能力，后台检查角色、任务能力和测试模式。诊断任务仍可使用，物理节点一次仅执行一个任务；不同节点可以并行。

“能力服务”页现在逐实例展示服务ID、执行节点、智能体类型、基础能力、执行模式、可用状态、当前任务状态。主机网络诊断和任务运行监视保留。配置了角色但尚未收到新版能力公告的节点显示“未公告／需更新固件”，不会显示可用；新固件公告过能力但失去就绪条件时显示“节点未就绪”。选择服务可带入执行节点及任务类型。

固件的 capabilities 包含 task_role、task_types、task_operations、execution_mode、task_status 和活动任务 task_id。连接时主动公告，任务状态或任务身份变化后更新 retained 公告；原 task_events 仍负责进度和结果。目录结合本轮公告、在线/遥测新鲜度与后台任务记录给出状态，ESP32在线不代表真实主控能力已接入。

### 测试任务配置

patrol：

```json
{"execution_mode":"esp32_test","area_id":"A01","point_ids":["P01","P02","P03"],"point_duration_s":3,"anomaly_point":2}
```

- area_id、每个点位为1–12个ASCII字母、数字、横线或下划线。
- 一次1–3个不重复点位；每点1–60秒，默认3秒。
- anomaly_point 为1起始的点位序号，0表示不生成异常，默认0。
- ESP32按时间依次验证点位记录，不解释为实际移动或到点。开始前可修改配置，运行后通过暂停/恢复/取消控制。

anomaly_review：

```json
{"execution_mode":"esp32_test","event_id":"实际测试事件ID","test_verdict":"inconclusive","duration_s":5}
```

- event_id 必须是本人有权访问的、已由巡检任务产生的测试事件。
- test_verdict 为 confirmed/cleared/inconclusive，含义分别为预设“确认异常／解除误报／待进一步核验”。默认 inconclusive。
- duration_s 为1–60秒，默认5秒。测试阶段依次为接收事件、校验输入、生成测试结果；完成前 verdict=pending，完成后返回预设结论。
- 一个测试事件可以建立多项复核任务，结果各自保存在对应任务中。

配置以公共 task.create/task.update 传递，控制与查询使用既有 task.control/task.get/task.events。后台在创建或更新前检查最坏情况下的512字节节点命令预算；回复继续受1024字节限制。不增加 root 网关请求类型或放宽 ACL。

### 测试异常事件

每个巡检任务最多产生一条测试异常事件，完成配置的异常点后上报。event_id 与来源巡检 task_id 相同，二者属于不同实体类型；这个规则保证断线后重复上报不会创建第二条事件。

后台先验证来源、操作、启动ID、序号及模式，再将事件持久化到 tasks.sqlite3 的 incidents 表。事件包含 event_id、source_task_id、node_id、area_id、point_id、created、test=true、execution_mode=esp32_test。

查询接口复用 task.events，增加 scope=incidents，支持 cursor 分页和可选 task_id（按来源巡检任务过滤）。省略 scope 保持原任务事件行为。不同车机仍按 owner 隔离；原 task.events 游标与测试事件游标不能混用。

“测试异常事件”页刷新后选择事件，会填入复核配置；已刷新能力服务时优先带入一个可用UAV。操作员仍需明确创建并开始复核任务。

删除来源巡检历史时，未结束的关联复核任务会阻止删除（task_in_use_by_review），包括尚未开始的复核任务。先取消或完成复核再删历史。独立测试事件快照和已完成复核结果保留，不随来源任务历史级联删除。

### 持久化与恢复

- 后台保存任务、控制、反馈、测试事件及复核关联。
- ESP32仍使用 m1_task 命名空间，新结构保存到 journal_v2；首次升级读取旧 journal 的v1结构，迁移为 diagnostics，保留旧键，不清空NVS或设备身份。
- 开始、控制、巡检点位边界、复核阶段变化与完成时保存关键记录。每秒反馈进度，不每50ms写Flash。
- ESP32重启后的未结束任务进入 UNKNOWN，后台查询对账，不自动重放开始，也不自动继续测试；可取消后创建新任务。
- 断开业务连接后测试流程暂停；重连后明确恢复。任务监视服务读取已验证反馈，额外显示测试模式及阶段。

### 使用步骤

1. 由用户按 [固件说明](firmware.md) 分别编译、烧录所有需要新能力的UAV/Micro；每块板使用自己的node_id与既有证书，不共用带身份的镜像。本次新增任务不要求为转发功能重刷root或UGV网关。
2. 重启新版UGV后台并打开新版车机。仅替换源码或重启GUI不会更新已运行后台。
3. 刷新节点和能力服务，确认每个新版节点公告相应服务且执行模式为ESP32测试。
4. 选择一个Micro巡检服务，切到服务任务，配置A01、P01/P02/P03、每点3秒、异常点2。创建后开始，并勾选持续补查事件。
5. 观察测试点位、已验证数量及测试事件ID；可暂停并确认进度停止，再恢复。
6. 刷新测试异常事件，选择P02产生的事件；选择一个UAV执行节点和预设测试结论，创建并开始复核。
7. 查看复核阶段、测试结论，同时可由任务运行监视服务监视巡检或复核任务。
8. 导出JSONL，保存实际源码版本、节点公告、任务ID、事件ID及原始反馈，记录当前仅为ESP32流程验证。

CLI示例（替换所有返回ID；GUI 与 CLI 均通过 HTTP 访问后台，不占用串口）：

```text
services
task patrol-test micro-001 A01 P01,P02,P03 3 2
task start 返回的巡检任务ID
task incidents
task review-test uav-001 返回的测试事件ID cleared 5
task start 返回的复核任务ID
task monitor ugv-root 返回的复核任务ID 30 1000 10
task start 返回的监视任务ID
```

Python接口：TaskClient.patrol_test / review_test / incidents / update_config，以及既有control/get/events/delete。update_config需要完整的对应类型配置与已查询revision，只允许CREATED。

### 验证范围

主机回归覆盖角色与能力公告、任意登记编号、未升级固件、配置及帧长度、事件来源校验/去重/权限、复核关联、监视、并行/排队、重启持久化、删除引用保护。隔离Mosquitto端到端测试使用明确的Python协议测试替身，不代表C固件运行结果。

本次不执行ESP-IDF编译或烧录。C源码的实际编译、镜像容量、NVS迁移、Flash/堆栈使用及板上流程仍需用户构建和实机验收。5秒接入与800ms公告指标需要另存实际硬件测量，不能用测试替身或车机请求总耗时替代。
