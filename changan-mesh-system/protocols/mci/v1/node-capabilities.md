# 节点侧 MCI 能力公告

普通 UGV、UAV 和 Micro UAV 在 MQTT 应用会话就绪后主动发布完整能力。MQTT 重连、任务状态或活动任务 ID 变化时重新发布。主题为 `mesh/v1/nodes/<nodeId>/capabilities`，QoS 1，retain。

```json
{
  "v": 1,
  "service": "Mesh_Node",
  "method": "Ntf_Capabilities",
  "nodeId": "uav-001",
  "bootId": "0123456789abcdef",
  "params": {
    "operations": ["ping", "status", "echo"],
    "taskRole": "uav",
    "taskTypes": ["diagnostics", "anomaly_review"],
    "taskOperations": ["start", "pause", "resume", "cancel", "query"],
    "executionMode": "esp32_test",
    "taskStatus": "RUNNING",
    "taskId": "diag-001",
    "capMeasureV": 1,
    "capId": "0123456789abcdef-00000002",
    "capSeq": 2,
    "sentUs": 9123456
  }
}
```

`nodeId` 必须与已认证 MQTT 主题一致，`bootId` 是16位小写十六进制启动标识。后台结合相同启动周期的在线声明、能力公告和实时遥测判断就绪。新版能力公告标识节点支持1024字节下行命令，后台仅在该公告与当前在线声明的启动标识匹配时启用这一上限。

`params` 必填 `operations`、`taskRole`、`taskTypes`、`taskOperations`、`taskStatus` 和 `capMeasureV`。`taskRole` 为 `ugv`、`uav` 或 `micro_uav`。在 `IDLE` 时省略 `taskId`，活动任务存在时填入任务标识。`executionMode` 在 UAV 与 Micro UAV 的能力中为 `esp32_test`。

`capId`、`capSeq` 和 `sentUs` 是同组测量字段，使用与 [能力公告测量 v1](../../capability-measure/v1/README.md) 相同的启动标识、序号和单调时钟。序号耗尽时省略该组字段。后台保留线报文，回执仍使用 `cap.receipt`，节点测量结果仍使用 `cap.result`。

后台主动发送 `cap.request` 时，新节点继续以原有 v1 `capabilities` 格式回复，附 `batch_id` 与 `probe_id`，QoS 1，非 retained。该探针回复单独计入验收批次，并保留 Broker 上的最新 MCI 能力公告。

车机通过现有 `Ntf_NodeSnapshot`、`Ntf_TaskChanged` 和 `Get_ServiceInstances` 查看节点和实例状态。此 MQTT 消息属于节点绑定，车机 HTTP 方法目录继续描述车机侧的接口。
