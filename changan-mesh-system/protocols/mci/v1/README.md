# MCI HTTP 绑定

完整返回和业务字段逐项说明见 [附录 A](appendix.md)，可直接查看 [listMethod JSON 原文件](listMethod-response.json)。

现有四个服务、23个方法描述，包含五类已有任务；中期场景新增 kind 未实现。
描述与发现版本1.0.0，使用显式 Draft 2020-12 校验器。
实现位于 [mci.py](../../../host/src/changan_ugv/mci.py)，复用现有后台、数据库、MQTT/TLS 和 USB，不要求修改固件。

## 访问与权限

默认监听 `127.0.0.1:8080`。Jetson 可按 [HTTP v1 约定](../../http/v1/README.md) 显式绑定局域网地址和配置来源白名单。MCI 请求与通知沿用 HTTP 的来源、Host 和 Origin 检查。
调用身份固定为 http-local，不接受报文自选 owner、用户或令牌，不提供公网或企业多用户认证。
本机可信操作员默认可发现和调用目录，实际任务所有权、节点授权、就绪及能力仍由后台检查。
装配前可设置 `service.mci_authorize(action, identity)` 分别限制 discover、visible、invoke、subscribe；False 拒绝。
discover 的 identity 为 None，其他检查使用 `(service, method)` 元组。这是本机策略钩子，不是企业账号管理。
隐藏的方法仍需独立检查 invoke，不能依靠隐藏代替授权。

## 发现

`POST /api/v1/mci/listMethod`，请求体为 `{}` 或仅含 service、method 的精确筛选。
成功返回仅含 specVersion 和 services，服务/方法按 ASCII 排序，每个方法完整返回输入/输出 Schema。
无匹配项成功返回空数组。静态目录不随实例上下线改变；超过1 MiB 返回 CATALOG_TOO_LARGE，不截断、不分页。
非法筛选返回 INVALID_ARGUMENT，描述或 Schema 无效返回 CATALOG_INVALID。
进程内 `MCI.publish` 验证后原子替换目录，失败保留原目录，不开放远程上传入口。

## 调用

`POST /api/v1/mci/call`，外壳示例：

```json
{
  "service": "Mesh_Task",
  "method": "Cnr_CreateTask",
  "requestId": "create-demo-001",
  "deadlineUnix": 1795500000,
  "params": {
    "taskId": "demo-001",
    "executorNodeId": "ugv-root",
    "kind": "network_diagnostics",
    "config": {
      "probeNodeId": "micro-001",
      "durationSeconds": 30,
      "periodMs": 1000
    }
  }
}
```

deadlineUnix 示例必须替换为当前 Unix 秒数加30，有效期最多60秒；requestId 为1～64个字母、数字、横线或下划线。
创建必须由调用方提供稳定 taskId（1～32个上述字符），便于提交超时后查询。这比最初映射中的可选字段更严格。
重试保留原 requestId、deadlineUnix、taskId 和参数，不能自动刷新编号或有效期；超时先查任务。
创建成功为 `{"result":{"stage":"UGV_RECEIVED","task":{...}}}`，task.state 为 CREATED，不自动开始。
用 Cnr_StartTask 传 taskId、expectedRevision 提交开始意图，执行状态以后续事件/查询为准。
去重、请求内容冲突、持久化及版本检查复用现有后台；普通命令缓存不承诺跨后台重启持久化。

单设备命令、准入及父节点方法必须在外壳传 target，不放入 params。
后台任务方法不允许外壳 target；executorNodeId 是任务业务执行对象。
内部 v/type/msg_id/node_id/deadline_unix、MQTT 主题及证书均不进入业务 Schema。
kind 与 config 使用 oneOf/const 绑定；更新 config 按本人已存任务的 kind 校验，不允许改变类型。
Schema 不替代跨字段、授权、角色、所有权及实际就绪检查。

成功响应按公开 Schema 投影业务字段并递归转换小驼峰；未列入契约的内部字段不公开。
输入及成功输出均校验。输出不合约返回 OUTPUT_INVALID；操作可能已执行，应先查状态。
业务拒绝为 `{"error":{"code":"BUSINESS_ERROR","message":"原后台原因"}}`；业务调用错误绑定不属于企业草案已经规定的发现错误模型。
其他调用错误为 INVALID_ARGUMENT、PERMISSION_DENIED、INTERNAL_ERROR。结构正确的业务错误使用 HTTP 200；非法 JSON 使用400，来源检查沿用403，请求上限16 KiB，超限413。
发现响应上限与节点命令预算独立，已升级节点为1024字节，旧节点为512字节。
节点主动能力公告见 [MQTT 节点绑定](node-capabilities.md)。JSON 重复键及非有限数字被拒绝。

## 单向消息

`GET /api/v1/events?format=mci&cursor=0&incidentCursor=0` 为只读 WebSocket。
消息包含 service、method、params；params 按目录 inputSchema 校验，outputSchema 为 null。

| 方法 | 来源 | 重连 |
| --- | --- | --- |
| Mesh_Task.Ntf_TaskChanged | 本人持久状态事件 | 外壳 cursor 用作 cursor，不混入业务载荷 |
| Mesh_Node.Ntf_NodeSnapshot | 周期观测与 Broker 状态 | 非持久快照，无任务游标 |
| Mesh_Task.Et_TestIncident | 本人可见的已校验 ESP32 测试事件 | 外壳 incidentCursor 用作 incidentCursor |

两个游标独立，通知可能重放，客户端须幂等处理；单向方法不能通过 call 调用，WebSocket 不接受控制指令。
父节点 accepted 不等于 applied；准入 brokerAclApplied=false 不表示旧连接已经被踢除。
原 `/api/v1/requests` 及不带 format=mci 的 WebSocket 保持原协议。

## 查询示例

独立车机 GUI/CLI 的节点、任务、准入及父节点操作现通过本绑定发送，内部表格继续使用原有视图模型。
GUI“能力服务 → 查看 MCI 方法”显示 listMethod 返回的目录及 Schema；底部“MCI 原始报文”显示实际请求、响应和通知。
导出 JSONL 中 operation=wire 的 result 含 protocol=MCI、path、request、response 或 notification。
普通操作记录是界面转换后的结果，可能仍有下划线字段；检查线协议应查看 wire 记录。
连接时会查询一个方法以确认后台支持 MCI；旧后台缺少入口时明确提示更新并重启，不自动回退旧协议。

```powershell
$catalog = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8080/api/v1/mci/listMethod -ContentType application/json -Body '{}'
$catalog.services | Select-Object service
```

更新依赖：`uv sync --locked`。部署方在合适窗口重启 UGV Service 后生效，无需重置证书、数据库、NVS 或重启 Broker。
