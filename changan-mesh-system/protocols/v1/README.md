# 节点控制协议 v1

普通无人车、无人机、微型无人机各自建立到根节点Mosquitto的MQTT/TLS会话，
无线层级为2/3/4，根节点ugv-root为第1层。根C6是透明网关，不是MQTT客户端。
UGV Service是唯一任务管理后台；汽车终端只使用[HTTP/WebSocket](../http/v1/README.md)。

## MQTT/TLS

JSON为紧凑UTF-8，必须v=1，拒绝重复键和非有限数字。节点命令最大512字节，反馈/状态
最大1024字节。证书CN、MQTT Client ID和node_id一致；Broker必须验证客户端证书及ACL。

| 主题 | 方向和用途 |
| --- | --- |
| mesh/v1/nodes/NODE/commands | 后台到节点：ping/status/echo |
| mesh/v1/nodes/NODE/acks | 节点到后台：命令反馈 |
| mesh/v1/nodes/NODE/presence | 节点在线声明，可retained |
| mesh/v1/nodes/NODE/capabilities | 节点能力，可retained |
| mesh/v1/nodes/NODE/telemetry | 新鲜状态，不retained |
| mesh/v1/nodes/NODE/task_commands | 后台到节点的内部任务操作 |
| mesh/v1/nodes/NODE/task_events | 节点执行反馈 |
| mesh/v1/clock | 后台时间公告 |

节点只读写自己的主题，不能替其他节点发反馈或写控制命令。命令与任务消息不retained。
ready需同一boot的在线声明、能力及新鲜遥测。uptime_ms是本机单调时间，不是UTC。

## 任务

内部task.command带target、task_id、command_id对应的msg_id、revision、op_seq、boot_id及
短期deadline。执行器反馈必须匹配当前启动、任务版本及操作，seq不能倒退。
队列接收、后台入库和执行完成分别表示不同阶段。节点失联或后台重启先对账，不重放start。
事件和结果在后台持久化；控制/状态以外的业务数据另用独立通道，不在此合同中实现。

## 网络状态

状态包含role、level、sta_ip、ap_ip、gateway、netmask、sta_mac、ap_mac、ap_enabled、parent_connected、
parent_bssid、rssi、channel、associated_children等可选字段。未上报字段未知。
`ap_enabled=false`表示AP已关闭，该节点仅使用STA；AP地址、AP MAC和下级客户端数不适用。
父子边按parent_bssid匹配唯一ap_mac；重复、外部、旧启动与循环关系不能画成确定实时连接。
主机服务就绪和根C6无线状态分别判断。

## 根节点USB隧道 MUX1

根C6监听MQTT TCP入口，通过原生USB复用多路TLS字节流；主机桥接分别连接本机Broker。
TLS在节点与Broker间端到端完成，中继和USB桥接不解密。
MUX1头20字节，含type、channel、epoch、token、seq、size及CRC16-CCITT，数据块最多512字节。
RESET/READY协商会话，OPEN/OPEN_OK建立通道，DATA/ACK流控，CLOSE关闭，PING/PONG保活。
CRC覆盖路由头和数据，旧epoch/token不能触碰新连接；当前最多8个通道。

READY通道255、token0、空负载、seq1允许根板发NETWORK（类型10）只读报告。
NETWORK为当前epoch、通道255、token/seq0、最多512字节JSON，周期约5秒。
桥接核对node_id=ugv-root并写入runtime/ugv-network.json；重置时失效，后台新鲜度阈值12秒。
该快照不能授予任何身份或业务权限。
# 父节点策略扩展

Micro capabilities.operations可包含parent。只有UGV Service负责将已授权的父节点ID解析为无线身份。
command.op=parent的payload包含revision（1..2^32-1）、mode（auto/prefer/fixed）、parent、bssid、ssid；
auto模式parent为null，不需要bssid/ssid。命令不retain，不自动重发，沿用deadline_unix及可信时钟检查。
ACK只表示接收/持久化，实际效果通过遥测确认。Micro状态中的parent_policy包含revision、mode、parent及
stage（pending/active/fallback）；实际连接仍看parent_connected与parent_bssid。中继另上报真实ap_ssid。
