# TCP 与原生 USB 通信协议 v1

## 字节帧

三段通信（UAV/Micro→UGV、UGV→root、root→PC）共用：

```text
偏移  字节数  内容
0     4       ASCII "MLT1"
4     2       JSON UTF-8 字节长度，网络大端
6     2       JSON 负载的 CRC-16/CCITT-FALSE，网络大端
8     N       紧凑 UTF-8 JSON，不附加 NUL 或换行
```

CRC 初值 0xffff、多项式 0x1021，无反射、无最终异或；`123456789` 的结果为 0x29b1。N 为 2～1024；PC 请求最多 512 字节，给两级代理信封与回执留出空间。串口接收器在部分帧闲置超过 1 秒后清空；坏魔术字、无效长度或 CRC 错误后重新找帧头。CRC 用于发现传输错误，不是认证机制。

所有消息为 JSON 对象，含 `v:1` 和 `type`。拒绝顶层重复键、嵌入 NUL、无效版本、超长帧。PC 解码器还检查 UTF-8 与非有限 JSON 数字。node_id 使用 1～32 个 ASCII 字母、数字、连字符或下划线；msg_id 最长 64 字符。

## 注册、心跳和转发

```json
{"v":1,"type":"hello","node_id":"micro-001","role":"micro_uav"}
{"v":1,"type":"hello_ack","node_id":"ugv-001","target":"micro-001"}
{"v":1,"type":"telemetry","node_id":"micro-001","seq":1,"payload":{"role":"micro_uav","topology":"chain","level":4,"heap":120000,"uptime_ms":5000}}
{"v":1,"type":"telemetry_ack","node_id":"ugv-001","target":"micro-001"}
```

UGV 连接 root 时 hello 的角色为 ugv；root 只允许配置的 UGV ID。UGV 下游只允许 uav 和 micro_uav。UGV 到 root 的下游转发形式如下，内部身份保持原样：

```json
{"v":1,"type":"relay","node_id":"ugv-001","message":{"v":1,"type":"ack","node_id":"micro-001","msg_id":"example-1","op":"ping","ok":true,"payload":{"level":4}}}
```

root 解包后通过 USB 输出内部消息。遥测 ACK 只用于连接保活，不是业务命令执行回执。

## PC 请求和目标回执

```json
{"v":1,"type":"list","msg_id":"example-list"}
{"v":1,"type":"command","target":"micro-001","msg_id":"example-1","op":"ping"}
{"v":1,"type":"command","target":"uav-001","msg_id":"example-2","op":"status"}
{"v":1,"type":"command","target":"micro-001","msg_id":"example-3","op":"echo","payload":"你好"}
```

ping/status 回执含角色、拓扑、层级、heap 和 uptime_ms，echo 返回原 payload。不执行重启、飞控或车机硬件操作。成功 ACK 由目标节点生成；未知操作返回 `ok:false`。每次 PC 请求使用新的 msg_id，不自动重试。

```json
{"v":1,"type":"ack","node_id":"micro-001","msg_id":"example-3","op":"echo","ok":true,"payload":"你好"}
{"v":1,"type":"error","node_id":"ugv-001","msg_id":"example-4","target":"micro-001","error":"node_offline"}
```

list 经 root 请求 UGV，UGV 返回自己及已注册下游会话，root 再加入自己；UGV 不在线时只返回 root。在线列表是应用会话快照，实际网络拓扑仍需比较各板 STATUS/ADDR 日志。在线/离线事件包含 `peer_id`；root 报告 UGV 离线时，下游通过该 UGV 的 PC 访问也不可用，即使下游与 UGV 的本地 TCP 尚未断开。

队列满或链路断开可能丢失消息，PC 必须处理超时；本阶段没有离线消息持久化、重放和恰好一次保证。
