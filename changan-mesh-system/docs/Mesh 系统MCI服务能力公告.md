# Mesh 系统 MCI 服务能力公告

**公告日期** 2026 年 11 月 26 日　**MCI 描述版本** `1.0.0`

UGV Service 面向独立车机发布 4 个 MCI 服务、23 个方法描述，其中 20 个可通过 HTTP 调用，3 个通过 WebSocket 单向发布，默认地址为 `127.0.0.1:8080`。Mesh 内部的 UGV、UAV 和 Micro UAV 通过 MQTT/TLS 和根节点 USB 隧道向 UGV Service 发布 `Mesh_Node.Ntf_Capabilities`。

接入时先用 `listMethod` 获取方法定义及 JSON Schema，再用 `Mesh_Node.Get_ServiceInstances` 查询当前服务实例。车机可订阅节点快照和任务变更，收到变化后查询实例的可用性和任务状态。节点基础诊断能力可在 `Mesh_Node.Get_NodeList` 的 `taskTypes` 中查看。

## 已发布的服务和方法

### 车机与 UGV Service 的 MCI 接口

以下 4 个服务和 23 个方法是车机调用 UGV Service 时通过 `listMethod` 获取的目录。部分方法由后台转发给网络内的普通节点执行。例如 `Mesh_Node.Cnr_Ping` 到达后台后，由后台通过 MQTT 向目标节点发出 v1 `ping` 命令。

| 服务 | HTTP 调用 | WebSocket 单向消息 |
| --- | --- | --- |
| `Mesh_Node` | `Get_NodeList` 查询节点状态与观测，`Get_RegisteredNodes` 查询登记，`Get_ServiceInstances` 查询实例，`Get_Status` 读取设备状态，`Cnr_Ping` 探测设备，`Cnr_Echo` 回显 | `Ntf_NodeSnapshot` 节点快照 |
| `Mesh_Task` | `Cnr_CreateTask`、`Cnr_UpdateTask`、`Cnr_StartTask`、`Cnr_PauseTask`、`Cnr_ResumeTask`、`Cnr_CancelTask`、`Cnr_DeleteTaskHistory`、`Get_Task`、`Get_TaskList`、`Get_TaskEvents`、`Get_TestIncidents` | `Ntf_TaskChanged` 任务状态变更，`Et_TestIncident` ESP32 测试事件 |
| `Mesh_Admission` | `Cnr_SetTrustStatus` 设置节点准入状态 | |
| `Mesh_Parent` | `Get_Policy` 查询父节点策略，`Cnr_SetPolicy` 设置父节点策略 | |

### Mesh 内部节点与 UGV Service 的 MCI 消息

| 服务与方法 | 发布方向 | 主题 | 触发时机 |
| --- | --- | --- | --- |
| `Mesh_Node.Ntf_Capabilities` | UGV、UAV 或 Micro UAV → UGV Service | `mesh/v1/nodes/<nodeId>/capabilities`，QoS 1，保留最新公告 | 接入、重连、任务状态或活动任务 ID 变化 |

这是节点侧 MQTT 绑定。车机的 `listMethod` 统计按 HTTP/WebSocket 目录计算。节点侧的 `ping/status/echo`、任务下行和反馈、在线声明、遥测，以及后台发起的能力验收继续使用节点 v1 报文。完整字段与示例见 [节点侧 MCI 能力公告](../protocols/mci/v1/node-capabilities.md)。

### 当前任务类型与执行位置

`kind` 是 `Mesh_Task.Cnr_CreateTask` 的任务类型字段。调用方用它选择任务行为，并按该类型的 Schema 填写 `config`。当前目录支持以下五种取值。

| `Mesh_Task` 的 `kind` | 执行位置 | 能力 |
| --- | --- | --- |
| `diagnostics` | UGV 主机或已公告该能力的授权节点 | 两端均记录样本数。主机采样就绪节点数，远程节点采样 Wi-Fi RSSI 和空闲堆 |
| `network_diagnostics` | UGV 主机 | 探测目标节点，记录可达性、成功与失败次数及往返耗时 |
| `task_monitor` | UGV 主机 | 查看指定任务的状态、进度及反馈距今时长 |
| `patrol` | Micro UAV 的 ESP32 | 点位和异常事件流程验证，执行模式为 `esp32_test` |
| `anomaly_review` | UAV 的 ESP32 | 关联测试事件并验证复核流程，执行模式为 `esp32_test` |

两项 `esp32_test` 能力仅覆盖板端流程验证。调用时，后台仍检查当前节点授权、就绪状态、任务所有权和版本。

### 后续按具体场景扩展任务类型

后续将围绕选定的几个具体应用场景细化 `Mesh_Task.kind`。每个场景先明确业务目标、参与节点和执行流程，再确定可复用的任务类型及需要新增的 `kind`。一个场景可组合多个任务类型，同一任务类型也可在多个场景中复用。

新增任务类型将明确执行角色、`config` 参数、结果字段和完成判定。涉及多节点协作时，还需定义任务依赖、超时和失败处理。任务类型及其 Schema 将随对应版本发布，通过 `listMethod` 查询 `Mesh_Task.Cnr_CreateTask` 的输入契约。远程节点具备对应执行能力后，在 `Mesh_Node.Ntf_Capabilities` 的 `taskTypes` 中公告。

具体场景和新增 `kind` 取值以确认后的方案为准。已有设计建议见 [MCI 方法映射中的场景扩展草案](<现有能力到 MCI 方法映射.md>)。

## 方法发现报文

向 `POST /api/v1/mci/listMethod` 发送 `{}` 可获取完整目录。以下请求精确筛选 `Mesh_Node.Cnr_Ping`。

```json
{
  "service": "Mesh_Node",
  "method": "Cnr_Ping"
}
```

以下为该筛选对应的完整返回，方法对象来自仓库实际导出的目录。这个方法的业务入参为空对象，只有收到匹配的设备应用层确认时才返回 `acknowledged: true`。

```json
{
  "specVersion": "1.0.0",
  "services": [
    {
      "service": "Mesh_Node",
      "methods": [
        {
          "method": "Cnr_Ping",
          "description": "Probe device&Success means a matching application acknowledgement.",
          "inputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {},
            "required": [],
            "additionalProperties": false
          },
          "outputSchema": {
            "type": "object",
            "description": "Business record&Fields follow the published method contract.",
            "properties": {
              "acknowledged": {
                "type": "boolean",
                "description": "Acknowledged&True only after a matching successful application ACK.",
                "const": true
              }
            },
            "required": ["acknowledged"],
            "additionalProperties": false
          }
        }
      ]
    }
  ]
}
```

车机侧完整的 4 个服务及 23 个方法参见 [listMethod 原始 JSON](../protocols/mci/v1/listMethod-response.json) 和 [业务字段说明](../protocols/mci/v1/appendix.md)。

## 节点接入与状态变化时的能力公告

| 触发条件 | 节点上报 | MCI 侧如何观察 |
| --- | --- | --- |
| 第一次接入或重连，应用会话就绪 | 在能力主题主动发布完整 `Mesh_Node.Ntf_Capabilities`，同时上报在线声明和首条实时遥测 | `Mesh_Node.Ntf_NodeSnapshot` 可见就绪状态和任务类型，再查询 `Get_ServiceInstances` 查看可用性 |
| 任务状态或活动任务 ID 变化 | 在同一能力主题重新发布完整公告，更新 `taskStatus` 和 `taskId`。任务结果和进度走 `task_events` | `Mesh_Task.Ntf_TaskChanged` 发布任务状态，按需用 `Get_ServiceInstances` 查看实例的 `taskStatus` 和 `availability` |
| 断链或实时遥测过期 | 后台根据在线声明与遥测年龄更新就绪判断 | 节点快照可见 `ready: false`。已公告的远程实例可显示 `availability: "unavailable"`、`reason: "node_not_ready"` |

### 接入时发布完整能力

节点在 MQTT/TLS 连接、命令和任务订阅、时钟同步均就绪后，以 QoS 1 在 `mesh/v1/nodes/uav-001/capabilities` 发布保留消息。以下按固件格式构造，演示 `uav-001` 接入后空闲时的公告。启动标识、公告序号和单调时间为示例值。

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
    "taskStatus": "IDLE",
    "capMeasureV": 1,
    "capId": "0123456789abcdef-00000001",
    "capSeq": 1,
    "sentUs": 1234567
  }
}
```

后台校验节点身份及能力，等同一启动周期的在线声明、能力公告和新鲜遥测齐备后，才将已授权节点标为 `ready: true`。节点快照可能合并多次变化。以下两条是车机原始记录中同一节点的 WebSocket 报文节选，分别采集于 12:12:04 和 12:12:34（UTC+8）。

```json
{
  "service": "Mesh_Node",
  "method": "Ntf_NodeSnapshot",
  "params": {
    "brokerConnected": true,
    "nodes": [
      {
        "nodeId": "uav-001",
        "ready": false,
        "online": null,
        "statusCurrentBoot": false,
        "taskTypes": []
      }
    ]
  }
}
```

```json
{
  "service": "Mesh_Node",
  "method": "Ntf_NodeSnapshot",
  "params": {
    "brokerConnected": true,
    "nodes": [
      {
        "nodeId": "uav-001",
        "ready": true,
        "online": true,
        "statusCurrentBoot": true,
        "taskTypes": ["diagnostics", "anomaly_review"]
      }
    ]
  }
}
```

### 任务状态变化时更新能力公告

以下延续上面的固件格式示例。假设同一节点随后执行基础诊断，进入 `RUNNING`，则在原主题重新发布完整公告。支持的任务类型和操作继续随报文携带，活动任务 ID 随状态一起报告，测量字段使用新的公告 ID。

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
    "taskId": "node-diag-demo-001",
    "capMeasureV": 1,
    "capId": "0123456789abcdef-00000002",
    "capSeq": 2,
    "sentUs": 9123456
  }
}
```

后台收到有效任务反馈后，通过 `Mesh_Task.Ntf_TaskChanged` 向任务调用方发布状态。下面是与该演示任务对应的通知节选。

```json
{
  "service": "Mesh_Task",
  "method": "Ntf_TaskChanged",
  "params": {
    "taskId": "node-diag-demo-001",
    "state": "RUNNING"
  },
  "cursor": 420
}
```

车机可在收到通知后调用 `Get_ServiceInstances` 刷新实例状态。下例为此时任务所有者查询到的实例响应节选。基础诊断占用同一物理节点，因此该节点上的复核测试实例也显示 `busy`。

```json
{
  "result": {
    "instances": [
      {
        "serviceId": "uav-001/anomaly-review",
        "nodeId": "uav-001",
        "announced": true,
        "availability": "busy",
        "taskStatus": "RUNNING",
        "taskId": "node-diag-demo-001"
      }
    ]
  }
}
```

任务结束并释放节点时，固件将下一条能力公告的 `taskStatus` 更新为 `IDLE`，省略 `taskId`。节点仍就绪且后台无活动任务时，实例查询返回 `available`。仅进度变化且状态与任务 ID 均相同时，继续通过任务事件反馈。

后台发起能力验收时，节点仍用原有 v1 格式返回带批次和探针 ID 的公告。该回复不替换 Broker 缓存中的最新 MCI 公告。字段与兼容规则见 [节点侧 MCI 能力公告](../protocols/mci/v1/node-capabilities.md)。

## 服务实例公告报文

向 `POST /api/v1/mci/call` 发送 `Mesh_Node.Get_ServiceInstances` 查询运行实例。以下请求来自车机 2026 年 11 月 26 日 12:12:36（UTC+8）的记录。实际调用请生成新的 `requestId`，并填写当前 Unix 秒数加 30 作为 `deadlineUnix`，服务端允许的有效期最长为 60 秒。

```json
{
  "service": "Mesh_Node",
  "method": "Get_ServiceInstances",
  "params": {},
  "requestId": "ae0b5392887b4559b94140a4b483a49e",
  "deadlineUnix": 1795666376
}
```

以下响应节选保留四种服务类型各一个实例及其字段，状态取自当次查询。

```json
{
  "result": {
    "instances": [
      {
        "serviceId": "ugv-root/network_diagnostics",
        "nodeId": "ugv-root",
        "agentType": "ugv",
        "serviceType": "network_diagnostics",
        "capabilities": ["ping", "rtt", "availability"],
        "operations": ["start", "pause", "resume", "cancel", "query"],
        "executionMode": "host",
        "announced": true,
        "availability": "available",
        "taskStatus": "IDLE",
        "taskId": null,
        "bootId": "7c70208934ac4842",
        "reason": null
      },
      {
        "serviceId": "ugv-root/task_monitor",
        "nodeId": "ugv-root",
        "agentType": "ugv",
        "serviceType": "task_monitor",
        "capabilities": ["state", "progress", "feedback_age"],
        "operations": ["start", "pause", "resume", "cancel", "query"],
        "executionMode": "host",
        "announced": true,
        "availability": "available",
        "taskStatus": "IDLE",
        "taskId": null,
        "bootId": "7c70208934ac4842",
        "reason": null
      },
      {
        "serviceId": "uav-001/anomaly-review",
        "nodeId": "uav-001",
        "agentType": "uav",
        "serviceType": "anomaly_review",
        "capabilities": ["test_event_review", "test_verdict"],
        "operations": ["start", "pause", "resume", "cancel", "query"],
        "executionMode": "esp32_test",
        "announced": true,
        "availability": "available",
        "taskStatus": "IDLE",
        "taskId": null,
        "bootId": "3b713f6d68bf7de1",
        "reason": null
      },
      {
        "serviceId": "micro-002/patrol",
        "nodeId": "micro-002",
        "agentType": "micro_uav",
        "serviceType": "patrol",
        "capabilities": ["test_points", "test_incident"],
        "operations": ["start", "pause", "resume", "cancel", "query"],
        "executionMode": "esp32_test",
        "announced": true,
        "availability": "unavailable",
        "taskStatus": "IDLE",
        "taskId": null,
        "bootId": null,
        "reason": "node_not_ready"
      }
    ]
  }
}
```

| 字段 | 如何读取 |
| --- | --- |
| `serviceId`、`nodeId`、`agentType` | 服务实例标识、执行节点和智能体类型 |
| `serviceType`、`capabilities`、`operations` | 任务类型、基础能力和实例支持的操作。如需启动服务任务，调用对应的 `Mesh_Task` 方法 |
| `executionMode` | `host` 表示主机执行，`esp32_test` 表示板端测试，`not_reported` 表示远程执行模式尚未公告 |
| `announced`、`availability`、`reason` | 主机实例由后台登记为 `announced: true`，远程实例依据节点上报。示例的 `micro-002/patrol` 已公告能力，查询时因 `node_not_ready` 不可用。远程实例尚无所需公告时可出现 `firmware_required` |
| `taskStatus`、`taskId`、`bootId` | 当前任务状态、调用方可见的活动任务标识和启动标识。当前能否使用服务以 `availability` 为准 |

## 节点基础诊断能力

基础诊断在 `Mesh_Node.Get_NodeList` 的节点记录中列为 `taskTypes: ["diagnostics"]`。下面的响应节选来自同次记录中 12:12:43（UTC+8）的查询。该节点当时已就绪，并公告了探测、状态查询和回显操作。

```json
{
  "result": {
    "nodes": [
      {
        "nodeId": "ugv-001",
        "role": "ugv",
        "rootId": "ugv-root",
        "ready": true,
        "online": true,
        "statusCurrentBoot": true,
        "operations": ["ping", "status", "echo"],
        "taskTypes": ["diagnostics"]
      }
    ]
  }
}
```

## 使用服务的调用和通知报文

以下为同次车机记录中的网络诊断任务。请求发往 `POST /api/v1/mci/call`，由 `ugv-root` 探测 `ugv-001`。

```json
{
  "service": "Mesh_Task",
  "method": "Cnr_CreateTask",
  "params": {
    "taskId": "87b582d92eb3478fb5de8d3016360bf7",
    "executorNodeId": "ugv-root",
    "kind": "network_diagnostics",
    "config": {
      "durationSeconds": 30,
      "periodMs": 1000,
      "probeNodeId": "ugv-001"
    }
  },
  "requestId": "6a9e84554a174b9e8ef424ea322700a7",
  "deadlineUnix": 1795666402
}
```

响应的 `stage: "UGV_RECEIVED"` 和 `task.state: "CREATED"` 表示后台已受理并保存任务。以下为响应字段节选。

```json
{
  "result": {
    "stage": "UGV_RECEIVED",
    "task": {
      "taskId": "87b582d92eb3478fb5de8d3016360bf7",
      "target": "ugv-root",
      "kind": "network_diagnostics",
      "state": "CREATED",
      "revision": 1
    }
  }
}
```

车机随后用该 `taskId` 和 `expectedRevision: 1` 调用 `Cnr_StartTask`。只读 WebSocket `/api/v1/events?format=mci&cursor=0&incidentCursor=0` 推送以下任务变更。此时任务为 `QUEUED`，后续执行状态可通过通知、`Get_Task` 或 `Get_TaskEvents` 确认。

```json
{
  "service": "Mesh_Task",
  "method": "Ntf_TaskChanged",
  "params": {
    "error": null,
    "progress": 0,
    "revision": 1,
    "state": "QUEUED",
    "stateSeq": 1,
    "taskId": "87b582d92eb3478fb5de8d3016360bf7",
    "updated": 1795666384
  },
  "cursor": 411
}
```

车机“能力服务”页可刷新实例，并通过“查看 MCI 方法”查看方法目录。调试时可在“MCI 原始报文”查看请求、响应及通知。协议细节和报文来源见 [MCI 本机接口](../protocols/mci/v1/README.md)和本文节选。
