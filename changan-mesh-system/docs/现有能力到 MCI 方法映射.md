# 现有能力到 MCI 方法映射草案

更新日期：2026-11-24。用途：供企业评审服务命名、参数边界与第一阶段实现范围，并规划露营、园区中期演示的任务扩展。

依据[企业 MCI 草案](MCI方法描述与发现接口规范-v1.0草案.md)。现有能力已增加[本机 MCI 适配](../protocols/mci/v1/README.md)，名称及企业权限模型仍需企业评审；第8章新增场景任务尚未实现。
保持现有四层网络、终端 HTTP/WebSocket 及节点 MQTT/TLS，首先在 UGV Service 增加适配层。

## 1 方法目录与实例目录

方法目录描述服务和方法的统一契约；实例目录描述哪台设备提供方法、角色、在线及可用状态。
`uav-001` 与 `uav-002` 不是两个服务名。同一 `(service, method)` 只发布一份一致定义，实例列表另行维护。

| 建议服务 | 职责 | 执行位置 |
| --- | --- | --- |
| Mesh_Node | 节点清单、状态及通信检查 | 后台查询，必要时请求目标节点 |
| Mesh_Admission | 节点可信授权与撤销 | UGV Service |
| Mesh_Parent | Micro 上游父节点策略 | 后台校验并下发，Micro 保存和执行 |
| Mesh_Task | 通用任务生命周期、历史及事件 | 后台调度和持久化，主机或 C6 执行 |

网络诊断、监视、基础诊断及已有 ESP32 测试流程先作为 Mesh_Task 的任务类型，避免为每种类型重复定义全部生命周期方法。
诊断类型间参数和结果不相同，应在 Schema 中按任务类型建立明确分支，不能用无约束 config/result 混合所有定义。

## 2 参数与权限约定

- 实例路由放在调用外壳中：对单个设备执行状态查询、Ping、准入变更或父节点策略时，外壳选择目标实例。`service`、`method`、请求编号、鉴权凭据和请求有效期不进入业务 Schema；外壳字段名及格式待协议绑定确定。
- 业务中引用的其他实体仍是业务参数：诊断的 `probeNodeId`、监视的 `watchTaskId`、父节点策略的 `parentNodeId`、后台创建任务时的 `executorNodeId`。它们不是把当前 MCI 请求发给谁的路由头。
- `taskId` 是任务业务标识；`expectedRevision` 是并发控制的业务前置条件，两者属于业务 Schema。父节点版本、任务版本和准入版本互不替代。
- 表中字段均使用小驼峰，适配层映射到现有下划线字段；结果内嵌对象也须递归适配并补充 Schema。未知值的缺省、null 与不适用含义应逐字段定义。
- 权限为拟定分级：读（可见范围内查询）、操作（已授权实例上的诊断及配置）、任务（本人任务及关联资源）、管理（准入及撤销）。现有 HTTP 绑定单一本机身份 http-local，并未实现这四类独立角色；不能将本表视为已经存在的权限系统。
- listMethod 的发现权限与各方法的调用权限独立检查。发现目录不得以节点短时离线为由伪造方法定义变化，实例可用性单独返回。

以下 `{}` 表示无业务参数；字段列表是待确认的契约摘要，不是完整 JSON Schema。错误由调用外壳承载，表中输出只指业务成功结果。

## 3 节点与准入方法

| 建议方法全名 | 现有接口或来源 | 业务输入 | 业务输出摘要 | 成功语义及建议权限 |
| --- | --- | --- | --- | --- |
| Mesh_Node.Get_NodeList | list，scope=nodes | `{}` | nodes：身份、角色、信任状态、在线、就绪、遥测年龄及状态 | 查询当前快照，不证明物理连接实时有效；读 |
| Mesh_Node.Get_RegisteredNodes | GET /api/v1/nodes/catalog | `{}` | nodes：已登记信息及历史观测 | 登记和历史，不是在线证据；管理 |
| Mesh_Node.Get_ServiceInstances | list，scope=services | `{}` | instances：实例、任务类型、执行模式、公告及可用状态 | 运行实例目录，不等同 listMethod；读 |
| Mesh_Node.Get_Status | command，op=status；外壳选目标节点 | `{}` | role、level、staIp、gateway、apEnabled 等实际状态 | 已获得匹配命令的节点状态；操作 |
| Mesh_Node.Cnr_Ping | command，op=ping；外壳选目标节点 | `{}` | acknowledged | 匹配的应用 ACK 成功，不等于业务任务成功；操作 |
| Mesh_Node.Cnr_Echo | command，op=echo；外壳选目标节点 | text | text | 节点回显成功，用于通信诊断；操作 |
| Mesh_Admission.Cnr_SetTrustStatus | node.admission；外壳选被管理节点 | trustStatus、expectedRevision | trustStatus、admissionRevision、brokerAclApplied、brokerAclReloadRequired | 清单及审计已保存；当前 ACL 尚待受控加载，不表示连接已踢除；管理 |

`trustStatus` 沿用 pending/trusted/revoked。准入不等于证书签发，不通过这个方法生成或更换设备密钥。
Ping、Echo 作为主动诊断采用 Cnr；Get_Status 可触发设备查询，但不得改变业务配置。
根 C6 是透明网关，没有上述节点 MQTT 命令客户端；根无线状态来自 USB NETWORK 快照，首期通过 Get_NodeList 返回，不假定根板支持 Ping/Status 命令。

## 4 父节点策略方法

| 建议方法全名 | 现有接口 | 业务输入 | 业务输出摘要 | 成功语义及建议权限 |
| --- | --- | --- | --- | --- |
| Mesh_Parent.Get_Policy | node.parent.get；外壳选 Micro | `{}` | mode、parentNodeId、revision、state；有观测时 actualBssid 等 | 返回已保存意图及可获得的执行观测，未配置用 unconfigured；操作 |
| Mesh_Parent.Cnr_SetPolicy | node.parent；外壳选 Micro | mode、parentNodeId、expectedRevision | revision、mode、parentNodeId、state；有观测时 actualBssid 等 | ACK 仅表示接收；applied 才表示新鲜遥测证实生效；操作 |

mode 为 auto/prefer/fixed；auto 时 parentNodeId 为 null。父 UAV 必须同 root、已授权、就绪且第3层 AP 可用。
Micro 必须就绪并公布 parent 能力。后台解析真实 BSSID/SSID，不要求调用方填写任意 MAC。
查询中的状态可为 unconfigured、pending、accepted、applied、fallback、waiting、uncertain、unconfirmed、rejected。
uncertain/rejected 是策略执行状态，不能把 HTTP/方法返回成功解释为切换成功；对外如何关联拒绝状态与统一调用错误，应在绑定中确定。
固定策略可能使 Micro 离线；保存后不自动重发，离线恢复步骤见[运行手册](operations.md#parent-selection)。

## 5 任务生命周期方法

这些方法的 MCI 接收方为后台任务服务，executorNodeId 是业务执行对象；控制已有任务时由 taskId 定位，不能由调用方篡改 owner。

| 建议方法全名 | 现有请求 | 业务输入摘要 | 业务输出摘要 | 成功语义 |
| --- | --- | --- | --- | --- |
| Mesh_Task.Cnr_CreateTask | task.create | taskId、executorNodeId、kind、config；可选 priority、executeBefore | task：taskId、state、revision 等 | 已创建持久任务，初始 CREATED，不自动开始；本机绑定要求稳定 taskId |
| Mesh_Task.Get_Task | task.get | taskId | task：配置、状态、进度、版本、结果等 | 当前后台已知状态，不保证设备当前实时状态 |
| Mesh_Task.Get_TaskList | task.list | cursor | items、cursor、more | 当前一页本人任务 |
| Mesh_Task.Cnr_UpdateTask | task.update | taskId、expectedRevision；config、priority、executeBefore 按现有规则选择 | task | CREATED 配置更新已保存，运行后不允许热更新 |
| Mesh_Task.Cnr_StartTask | task.control，op=start | taskId、expectedRevision | task、stage 等现有业务回执信息 | 开始意图已受理或入队，后续反馈决定实际执行状态 |
| Mesh_Task.Cnr_PauseTask | task.control，op=pause | taskId、expectedRevision | task、stage 等 | 暂停意图已受理，以后续状态确认 PAUSED |
| Mesh_Task.Cnr_ResumeTask | task.control，op=resume | taskId、expectedRevision | task、stage 等 | 恢复意图已受理，以后续状态确认 RUNNING |
| Mesh_Task.Cnr_CancelTask | task.control，op=cancel | taskId、expectedRevision | task、stage 等 | 取消意图已受理，需确认最终状态 |
| Mesh_Task.Cnr_DeleteTaskHistory | task.control，op=delete | taskId、expectedRevision | deleted、taskId、stateSeq | 允许删除的终态历史已删除；不擦除设备 NVS |
| Mesh_Task.Get_TaskEvents | task.events，默认 scope | cursor；可选 taskId | items、cursor、more | 本人持久状态事件补查 |
| Mesh_Task.Get_TestIncidents | task.events，scope=incidents | cursor；可选来源 taskId | items、cursor、more | 本人 ESP32 测试异常事件补查，不表示真实识别结果 |

上述方法执行任务权限检查：本人任务、允许的执行节点、授权及能力、版本与状态前置条件；保留现有管理员维护例外。
任务分页保持现有 cursor/more 语义；这是业务查询分页，不是 listMethod 分页。
多节点并行、同类服务排队、执行器活动任务上限继续由现有调度器处理，不由 MCI 目录代替。

### 创建任务的类型分支

| kind | 执行者 | config 的建议业务字段及现有约束 | 结果含义 |
| --- | --- | --- | --- |
| diagnostics | 主机或已公告能力的 C6 | durationSeconds：1～3600；periodMs：200～10000 | 主机就绪采样或 C6 RSSI/堆/样本，须明确结果来源和不同结构 |
| network_diagnostics | ugv-root 主机 | 上述时长/周期，另加 probeNodeId | 成功/失败数及主机到节点应用往返时间；不是无线空口时延 |
| task_monitor | ugv-root 主机 | 时长/周期、watchTaskId、staleAfterSeconds：1～3600，默认10 | 被监视任务状态、有效反馈年龄及健康判断 |
| patrol | Micro C6 | executionMode=esp32_test、areaId、pointIds、pointDurationSeconds、anomalyPoint | 既有点位流程验证；不控制真实运动 |
| anomaly_review | UAV C6 | executionMode=esp32_test、eventId、testVerdict、durationSeconds | 关联测试事件和预设复核结果；不执行真实识别 |

通用诊断时长默认30秒、周期默认1000毫秒。patrol 的 areaId/点位标识为1～12个合法 ASCII 标识字符，pointIds 为1～3个不重复点位，单点1～60秒（默认3），异常点序号0～点位数（默认0）。
anomaly_review 时长1～60秒（默认5），testVerdict 为 confirmed/cleared/inconclusive（默认 inconclusive）；eventId 必须关联本人可访问的测试事件。
完整字段与状态机见[任务手册](tasks.md)。这些测试能力仅映射现有程序，不扩展导航、飞控、相机、媒体或 UWB 接口。

## 6 通知与数据消息

| 建议方法全名 | 现有来源 | inputSchema 所描述的载荷摘要 | outputSchema | 首期处理 |
| --- | --- | --- | --- | --- |
| Mesh_Task.Ntf_TaskChanged | WebSocket task.event / 持久任务事件 | taskId、state、revision、stateSeq、progress；可选 result 等 | null | 映射后台对调用者可见的状态事件；可补查，不等同原始设备 task_events |
| Mesh_Node.Ntf_NodeSnapshot | WebSocket nodes.snapshot | nodes、brokerConnected | null | 描述现有周期快照，不承诺只在状态变化时发送或持久重放 |
| Mesh_Task.Et_TestIncident | 节点测试事件经后台验证并持久化 | eventId、sourceTaskId、nodeId、areaId、pointId、test 等 | null | MCI WebSocket 增加独立 incidentCursor 推送与补查，仍只表示 ESP32 测试事件 |

单向消息的 inputSchema 是发布载荷，发现后不能作为请求—响应方法任意调用。
通知的订阅、事件游标、断线补查及发生时间/接收时间，应在传输绑定中分别定义。设备身份等字段用于表示事件主体时属于业务数据；鉴权仍由外壳完成。
节点原始 telemetry 目前作为后台输入及节点快照来源，暂不另设 Dat 方法；独立大数据通道仍为后续工作。

## 7 内建发现操作

listMethod 为内建操作，不放入上述业务服务的 methods。
输入为 `{}` 或 service/method 精确筛选；输出为 specVersion=1.0.0 及 services[].methods[]，包含完整 inputSchema/outputSchema。
服务及方法按 ASCII 升序，重复实例合并且定义必须一致；完整单次返回，不能沿用现有服务实例目录逐条分页报文。
无匹配项返回成功空数组；无效描述、冲突或超大目录返回相应错误。目录生成不能将授权不足和无匹配方法混为一类。
首期建议由后台维护有效描述，通过现有本机 HTTP 增加独立绑定承载，不将完整 Schema 塞进节点512字节命令。

## 8 中期演示场景任务扩展

本章为待开发建议，与前文现有能力映射分开。新增任务仍使用 `Mesh_Task.Cnr_CreateTask`，通过 `kind` 区分类型，每个类型定义独立的 config 和结果 Schema；不新增按任务类型命名的服务。
现有代码只接受前述五类任务，不能直接用本章 kind 发起调用。真实飞行、移动、采集、定位及通道切换，需要对应执行器接入后才能验收。
`patrol`、`anomaly_review` 继续保留为 esp32_test 流程验证，不直接改变为真实巡检或复核任务。

### 8.1 场景总任务和设备子任务

后台增加场景编排层，一个总任务关联多个子任务，支持按阶段触发、并行执行、等待结果和处理失败。
总任务执行于 UGV Service；飞行器、无人车和其他组执行器分别执行自己的子任务。依赖和聚合规则由后台维护，不由终端重复下发实现。

| 建议业务字段 | 用途 |
| --- | --- |
| parentTaskId | 子任务关联的场景总任务 |
| dependsOnTaskIds | 启动前需要满足条件的前置任务 |
| eventId | 串联发现线索、空中复核及地面核验的同一事件 |
| evidenceIds | 当前任务产生或引用的证据 |
| areaId、planId | 指定区域及已确认的航线/路径计划 |

以上是新增业务字段建议，尚未加入现有 Schema。依赖成功、部分结果可用、人工确认、超时、取消及子任务失败时总任务如何处理，须逐场景定义。
总任务不能仅因所有子任务已派发就报告完成；应达到约定的结果、证据及人工确认条件。

### 8.2 共用基础和验收任务

| 建议 kind | 执行方 | 输入 config 摘要 | 输出及验收点 |
| --- | --- | --- | --- |
| admission_test | 后台验收执行器 | 预期身份、授权/未授权测试节点、观察时长 | 身份认证、授权决策、可否领取任务、拒绝层级/原因及时间记录 |
| topology_recovery_test | 后台验收执行器 | 观察节点、基线、观察窗口、通信探测配置 | 父节点变化、通信中断、重新就绪、反馈恢复时间及原任务关联 |
| acceptance_export | 后台导出执行器 | 演示/任务范围、时间范围、导出格式 | 发现、接入、定位来源、拓扑变化、通信和任务记录及文件引用 |

准入测试不自动批准陌生节点、不改正式证书或清单。TLS 拒绝发生在业务连接建立之前时，应从 Broker 日志或受控测试采集器取得记录；现有后台不保证能直接观察被拒绝客户端。界面展示“认证拒绝”“未授权派发”“能力不足”等具体原因，不能笼统解释为 Wi-Fi 拒接。
拓扑测试由现场人员按约定移动或关闭中继；测试任务负责观测，不自动切断现场网络。第4层 Micro 应存在可用的第3层 UAV 候选，且父节点策略允许切换；fixed 模式不能要求自动改连另一 UAV。
记录导出只包含实际采集到的测试项；缺失定位或路由测量时标为未采集，不能从任务成功推断测试通过。

### 8.3 露营勘察任务

| 建议 kind | 执行方 | 输入 config 摘要 | 结果与完成条件 |
| --- | --- | --- | --- |
| camp_survey | 后台场景编排器 | 区域、参与设备、计划、所需结果和确认规则 | 汇总子任务、候选点及证据；达到选址与确认条件后完成 |
| aerial_survey | 普通无人机执行器 | 区域、航点计划、采集要求 | 实际航点进度、带位置的照片记录和候选点线索 |
| ground_site_check | 无人车执行器 | 候选点位置、检查项目 | 候选点可达性、现场观察、证据及逐项核验状态 |
| site_assessment | 后台评价执行器 | 候选点、空地证据、评价规则 | 选址列表、评价依据、缺失项及人工确认状态 |

流程：开始勘察 → 等待所需设备就绪 → 空中勘察产生候选点 → 地面核验 → 后台汇总 → 操作员确认。
首次联调可使用明确标记的人工候选点和评价规则；只有实际接入识别算法后，才能展示对应的自动识别结论。

| 演示环节 | 对应能力与新增工作 |
| --- | --- |
| 点击开始、上电入网、设备清单 | camp_survey 进入设备等待阶段；复用节点清单。设备上电后自主入网；远程上电需要额外电源控制硬件 |
| 邻居距离和方位 | 接入定位/测距数据，约定坐标系、时间戳、精度、邻居身份和有效期。RSSI 和父子关系不能当作实测距离及方位 |
| 授权与未授权节点加入 | admission_test 配合现有准入、能力及任务状态展示，分别记录认证与授权结果 |
| 航线、照片、候选点及初步选址 | 规划展示、飞控执行反馈、aerial_survey、ground_site_check、site_assessment 及证据管理 |
| 中继改变、反馈恢复和记录导出 | topology_recovery_test、原任务对账、acceptance_export；只按实际观测展示父子拓扑，不推断完整底层路由表 |

### 8.4 园区巡检任务

| 建议 kind | 执行方 | 输入 config 摘要 | 结果与完成条件 |
| --- | --- | --- | --- |
| park_inspection | 后台场景编排器 | 区域、角色分工、计划、触发和确认规则 | 巡查、复核、外部核验、证据及告警的整体进度 |
| area_patrol | 微型无人机执行器 | 区域及巡查计划、采集要求 | 疑似异常 eventId、位置、初始图像、发现时间和待复核状态 |
| aerial_review | 普通无人机执行器 | 原 eventId、目标位置、高清采集要求 | 高清证据、复核结论及依据；证据不足时保留待确认 |
| ground_verification | 其他项目组无人车执行器 | 原 eventId、位置、所需身份核验证据 | 车牌/可见 VIN 图像引用、身份候选、执行状态及失败原因 |
| perimeter_review | 指定复核节点 | 周界线索、位置、核验要求 | 核验结果、关联证据及告警建议 |
| alarm_handling | 后台与操作员 | 告警事件、关联证据、处置要求 | 接收、确认和处置阶段及对应主体、时间 |

流程：区域巡查 → 疑似异常标为待复核 → 根据事件触发空中复核 → 按规则交给其他组地面核验 → 汇总空地证据 → 人工确认。
自动派发属于新增编排规则，应检查节点角色、实际能力、授权、就绪和资源占用；现有 anomaly_review 测试任务不能证明已实现真实飞行或识别。
位置数据应标明测量来源和坐标系；初始图像、高清图像、身份候选及人工结论分别存储，不能将检测到车辆等同于已确认违规或身份。

其他组交接至少约定：eventId、关联总/子任务、目标位置、所需证据、接收回执、进度、结果、失败和超时处理。对方完成移动、采集或识别，我们管理交接与展示。
尚未接通对方执行器时，应明确显示模拟交接或人工回填。任务接收、复核完成、人工确认、告警回执是不同阶段，分别关联并记录。

### 8.5 证据管理和传输验收

| 新增能力或建议 kind | 职责 | 结果与依赖 |
| --- | --- | --- |
| 证据管理模块 | 保存 evidenceId、taskId、eventId、采集设备、采集时间、位置来源、文件类型/大小、存储引用和完整性信息 | 区分采集时间与接收时间，按任务/事件关联空地证据；受权限控制 |
| evidence_upload | 通过独立数据通道上传照片或视频文件，处理重试、完整性和失败状态 | 文件可访问且完整性校验通过才报告上传完成；重试不得重复触发设备采集 |
| transport_test | 在约定负载和衰减条件下观测控制与数据传输、通道切换 | 控制 ACK 时延、超时/丢失、数据吞吐、切换时间及任务反馈连续性；依赖真实采集和通道状态接口 |

控制、任务状态和轻量证据引用继续通过 MQTT/TLS；照片/视频文件通过另行设计的数据通道传输，不塞入现有512字节节点命令。
Dat_ 消息若以后需要发布，应先确认实际采样或数据消息契约；不会因为增加 evidence_upload 就自动拥有视频流服务。
视频并发控制优先需要流量调度、带宽管理及压力测试；MQTT QoS 不等于全链路带宽优先保障。
备用切换必须有第二条实际可用链路及切换适配，不能仅靠添加任务类型实现；备用通道的技术方案、切换条件和验收阈值待共同确定。

### 8.6 网络恢复和任务恢复

1. 记录中断前的 taskId、执行阶段、反馈序号及父节点关系。
2. 连接恢复后先确认身份、能力和新鲜状态，再按原 taskId 对账并恢复显示。
3. 区分任务继续运行、已暂停、已结束和状态不确定；按执行器及场景规则决定继续、取消或人工处理。
4. 不能把重连当成新的开始命令；不自动重复起飞、移动或采集。飞行期间失联行为由实际飞控及执行器定义。

创建成功、指令受理、实际开始、证据完整上传及人工确认应分别展示。航线可视化不代表设备已经沿航线执行；拓扑恢复也不证明任务已完成恢复。

### 8.7 建议实施顺序

| 阶段 | 交付内容 | 验证方式 |
| --- | --- | --- |
| 1 | 场景总任务/子任务关联、依赖编排、事件与证据关联、验收记录 | 先用明确标记的测试执行器验证状态和权限，保留原 ESP32 测试能力 |
| 2 | 园区巡查 → 待复核事件 → 普通无人机复核 → 人工确认 | 先验证流程，再逐项替换为真实采集和执行反馈 |
| 3 | 露营空中勘察 → 候选点 → 地面核验 → 选址汇总 | 记录实际计划、位置来源、证据和评价依据 |
| 4 | 其他组地面核验、定位、飞控及图像模块联调 | 按接口合同验证回执、失败、证据与事件关联 |
| 5 | 视频负载、控制优先、主通道衰减和备用切换 | 使用实物链路与约定测试条件，独立保存传输验收记录 |

现有任务状态机、持久化、去重、版本检查和事件补查可复用。新增 kind 还需扩展校验、角色和能力公告、执行器、调度资源规则及终端表单；场景编排与长时人工等待也需设计恢复语义，不能只在配置中添加名称。
待确认：各组执行器接口、坐标和定位方案、航线/路径来源、数据通道及存储、自动派发规则、人工确认责任，以及中期实物验收范围和阈值。

## 9 实施顺序与待确认事项

1. 企业确认四个服务名、实例路由规则、调用外壳、错误映射以及发现/调用权限模型。现有 v1 通信字段继续由适配层使用，不直接混入新业务 Schema。
2. 首批交付 listMethod，加 Mesh_Task 的 Create/Get/Start/Cancel 和 Ntf_TaskChanged，打通一个 network_diagnostics 闭环；再覆盖其余查询、任务操作、准入及父节点策略。
3. 为确认的方法补全 Draft 2020-12 Schema。每个业务字段写“用户描述&详细描述”；递归检查命名、required、显式对象及扩展策略、引用、单位和空值。
4. 描述发布前执行草案第10章符合性检查；运行时校验输入和成功输出。新目录校验失败时保留上一有效版本。
5. 在独立终端增加方法目录查看；验证不同实例共用定义、任务所有权、过期/重复请求、版本冲突、受理与完成区分及离线恢复。

待确认：网络诊断/监视是否要求独立业务服务；离线实例的方法是否仍可发现；实例目录采用何种标准；单向消息订阅与补查外壳；后台静态描述是否满足首期交付或必须节点动态注册。
前文映射对应现有程序；第8章扩展仅用于后续设计，真实硬件动作需执行器及接口另行实现。现有本机单身份接口不等于已完成企业多用户鉴权。

## 10 实现依据

- [请求分发](../host/src/changan_ugv/service/requests.py)：节点查询、命令、准入、父节点及任务入口。
- [任务存储](../host/src/changan_ugv/tasks/store.py)与[运行时](../host/src/changan_ugv/tasks/runtime.py)：配置、状态、权限、持久化及服务实例。
- [父节点策略](../host/src/changan_ugv/nodes/parent_policy.py)与[准入](../host/src/changan_ugv/nodes/admission.py)：版本及实际生效边界。
- [HTTP/WS 合同](../protocols/http/v1/README.md)与[节点合同](../protocols/v1/README.md)：现有外壳、消息方向与报文预算。
