# ESP32 巡检与异常复核流程验证

本版运行到 ESP32，不接无人机主控，不控制飞行、定位、相机或识别算法。新任务的配置必须显式携带 execution_mode=esp32_test；公告、车机表单、进度与结果均标注测试模式。SUCCEEDED 表示流程验证结束，不表示真实巡检、到点或异常识别成功。

## 服务按角色提供

| 清单角色 | 公告任务类型 | 服务ID | 基础能力 |
| --- | --- | --- | --- |
| uav | anomaly_review | 实际node_id/anomaly-review | 巡检异常事件关联、复核流程、预设测试结论 |
| micro_uav | patrol | 实际node_id/patrol | 测试区域及点位、逐点流程、测试异常事件 |

不按 uav-001/micro-001 写死。例如 uav-017、micro-017、micro-018 分别有独立服务实例。管理员清单决定角色和授权；ESP32 根据固件角色公告能力，后台检查角色、任务能力和测试模式。诊断任务仍可使用，物理节点一次仅执行一个任务；不同节点可以并行。

“能力服务”页现在逐实例展示服务ID、执行节点、智能体类型、基础能力、执行模式、可用状态、当前任务状态。主机网络诊断和任务运行监视保留。配置了角色但尚未收到新版能力公告的节点显示“未公告／需更新固件”，不会显示可用；新固件公告过能力但失去就绪条件时显示“节点未就绪”。选择服务可带入执行节点及任务类型。

固件的 capabilities 包含 task_role、task_types、task_operations、execution_mode、task_status 和活动任务 task_id。连接时主动公告，任务状态或任务身份变化后更新 retained 公告；原 task_events 仍负责进度和结果。目录结合本轮公告、在线/遥测新鲜度与后台任务记录给出状态，ESP32在线不代表真实主控能力已接入。

## 测试任务配置

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

## 测试异常事件

每个巡检任务最多产生一条测试异常事件，完成配置的异常点后上报。event_id 与来源巡检 task_id 相同，二者属于不同实体类型；这个规则保证断线后重复上报不会创建第二条事件。

后台先验证来源、操作、启动ID、序号及模式，再将事件持久化到 tasks.sqlite3 的 incidents 表。事件包含 event_id、source_task_id、node_id、area_id、point_id、created、test=true、execution_mode=esp32_test。

查询接口复用 task.events，增加 scope=incidents，支持 cursor 分页和可选 task_id（按来源巡检任务过滤）。省略 scope 保持原任务事件行为。不同车机仍按 owner 隔离；原 task.events 游标与测试事件游标不能混用。

“测试异常事件”页刷新后选择事件，会填入复核配置；已刷新能力服务时优先带入一个可用UAV。操作员仍需明确创建并开始复核任务。

删除来源巡检历史时，未结束的关联复核任务会阻止删除（task_in_use_by_review），包括尚未开始的复核任务。先取消或完成复核再删历史。独立测试事件快照和已完成复核结果保留，不随来源任务历史级联删除。

## 持久化与恢复

- 后台保存任务、控制、反馈、测试事件及复核关联。
- ESP32仍使用 m1_task 命名空间，新结构保存到 journal_v2；首次升级读取旧 journal 的v1结构，迁移为 diagnostics，保留旧键，不清空NVS或设备身份。
- 开始、控制、巡检点位边界、复核阶段变化与完成时保存关键记录。每秒反馈进度，不每50ms写Flash。
- ESP32重启后的未结束任务进入 UNKNOWN，后台查询对账，不自动重放开始，也不自动继续测试；可取消后创建新任务。
- 断开业务连接后测试流程暂停；重连后明确恢复。任务监视服务读取已验证反馈，额外显示测试模式及阶段。

## 使用步骤

1. 由用户按 [固件说明](firmware.md) 分别编译、烧录所有需要新能力的UAV/Micro；每块板使用自己的node_id与既有证书，不共用带身份的镜像。本次新增任务不要求为转发功能重刷root或UGV网关。
2. 重启新版UGV后台并打开新版车机。仅替换源码或重启GUI不会更新已运行后台。
3. 刷新节点和能力服务，确认每个新版节点公告相应服务且执行模式为ESP32测试。
4. 选择一个Micro巡检服务，切到服务任务，配置A01、P01/P02/P03、每点3秒、异常点2。创建后开始，并勾选持续补查事件。
5. 观察测试点位、已验证数量及测试事件ID；可暂停并确认进度停止，再恢复。
6. 刷新测试异常事件，选择P02产生的事件；选择一个UAV执行节点和预设测试结论，创建并开始复核。
7. 查看复核阶段、测试结论，同时可由任务运行监视服务监视巡检或复核任务。
8. 导出JSONL，保存实际源码版本、节点公告、任务ID、事件ID及原始反馈，记录当前仅为ESP32流程验证。

CLI示例（替换所有返回ID，保持GUI与CLI不同时占用COM7）：

```text
services
task patrol-test micro-001 A01 P01,P02,P03 3 2
task start 返回的巡检任务ID
task incidents
task review-test uav-001 返回的测试事件ID cleared 5
task start 返回的复核任务ID
task monitor ugv-001 返回的复核任务ID 30 1000 10
task start 返回的监视任务ID
```

Python接口：TaskClient.patrol_test / review_test / incidents / update_config，以及既有control/get/events/delete。update_config需要完整的对应类型配置与已查询revision，只允许CREATED。

## 验证范围

主机回归覆盖角色与能力公告、任意登记编号、未升级固件、配置及帧长度、事件来源校验/去重/权限、复核关联、监视、并行/排队、重启持久化、删除引用保护。隔离Mosquitto端到端测试使用明确的Python协议测试替身，不代表C固件运行结果。

本次不执行ESP-IDF编译或烧录。C源码的实际编译、镜像容量、NVS迁移、Flash/堆栈使用及板上流程仍需用户构建和实机验收。5秒接入与800ms公告指标需要另存实际硬件测量，不能用测试替身或车机请求总耗时替代。
