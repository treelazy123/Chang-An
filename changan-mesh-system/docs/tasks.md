# M1 任务操作

支持 diagnostics、UGV主机 network_diagnostics/task_monitor，以及Micro的patrol、UAV的anomaly_review。后两项仅为显式esp32_test模式的业务流程验证，见 [ESP32巡检与复核说明](esp32-workflows.md)。主机服务的计时和步骤见 [主机服务说明](host-services.md)。C6 diagnostics采集真实Wi-Fi RSSI、空闲堆及样本数；旧UGV diagnostics标明source=ugv_host。

支持创建、查询、列表、开始前配置更新、开始、暂停、恢复、取消、进度与事件补查、持久化及失联/重启对账。保留基础list/ping/status/echo。task.events默认查询任务状态日志，scope=incidents查询巡检测试异常事件；不控制飞行、主控、相机、UWB或真实运动，不支持运行中配置热更新。

启动车机与后台见 [运行说明](operations.md)，身份/固件准备见 [固件说明](firmware.md)，权限与部署切换见 [部署说明](deployment.md)。代码职责见 [系统架构](architecture.md)，线协议以 [v1 合同](../protocols/v1/README.md) 为准，实物结论见 [验收状态](status.md)。

GUI 的任务页提供常用控制，CLI/API 可更新 CREATED 配置。GUI 控制使用已查询版本；CLI 未显式指定版本时先查询，再提交一次控制。两者都不自动覆盖版本冲突或重发超时操作。

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

所有公开请求沿用 v=1，带 type、msg_id、deadline_unix。root 将 node_id 绑定为实际证书身份。命令 TTL 最多 60 秒，任务采样时长单独由 config.duration_s 表示。

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

任务事件以 task.event 发布到车机 events 主题，携带 cursor、task_id、state_seq。串口拥塞时实时通知可以丢失，数据库中的 task.events 游标补查是恢复依据。

内部节点使用 task_commands/task_events；内部 msg_id 就是持久化 command_id，带目标、配置版本、持久化递增操作序号 op_seq、启动标识和短期有效时间。执行器回报带 boot_id 和 seq，旧启动、旧版本和旧序号不能回滚当前任务；迟到的旧暂停/恢复不能再次执行。车机不能直接向节点任务主题写命令。

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

主机测试包括临时 SQLite 故障/幂等/并发测试、独立车机串口帧测试，以及随机本地端口的实际 Mosquitto mTLS/ACL/生命周期/服务重启测试。集成测试中的节点是明确的主机测试执行器，不代表 C6 固件已上板验证。测试不连接现有 Broker 或 COM 端口。
