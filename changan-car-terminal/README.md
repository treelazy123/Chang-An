# 长安车机终端

独立HTTP/WebSocket终端，不加入Mesh，不持有节点证书，不占用C6串口。
GUI和CLI通过版本化协议访问UGV Service，不导入主仓库业务源码。

```powershell
uv sync --locked
uv run --locked python -m car_terminal.gui --base-url http://127.0.0.1:8080
uv run --locked python -m car_terminal --command list
```

GUI打开后手动连接。HTTP提交节点查询和任务操作，WebSocket推送状态并按游标重连补查。
GUI 与 CLI 的常用操作现通过 `/api/v1/mci/call`，通知使用 `format=mci`。
“能力服务 → 查看 MCI 方法”通过 listMethod 显示完整方法与 Schema。
底部“MCI 原始报文”记录实际 HTTP 请求/响应和单向通知；导出 JSONL 中 operation=wire 的 result 保留原始 MCI JSON。
普通操作结果仍转换为界面原有视图，字段可能为下划线；查看协议请以原始报文为准。
旧后台缺少 MCI 接口时连接明确失败，请更新依赖并重启 UGV Service，再重新打开终端。
网络结构页可设置Micro的上游UAV：刷新节点，查询Micro配置后选择自动、优先指定或固定指定并应用。
结果显示期望与实际父节点；配置接收后需等待重连确认。固定模式离线后的恢复见
[父节点选择说明](../changan-mesh-system/docs/operations.md#parent-selection)。
检查/基础诊断节点支持输入或下拉选择；后台快照刷新不会覆盖正在编辑的节点。
网络表中Micro的AP和关联客户端显示“不适用（STA）”，STA地址由所连接的UAV分配。
任务变更不自动重发；超时后按任务ID查询。关闭终端后后台继续执行。

“能力公告验收”页通过新增本机HTTP v1诊断接口管理测试批次，普通操作仍沿用MCI。
输入逗号分隔的在线节点ID，默认每节点30条、间隔1000ms；点击开始新测试后自动刷新，
展示每条公告的智能体类型、基础能力、任务状态，以及平均/P95/最大接收确认耗时。
指标标注为“接收确认耗时（单向延迟上界）”：≤800ms证明已在时限内接收，
上界超800ms不能直接认定精确单向延迟超标。超时和中断保留，不计为0ms成功。
“历史批次”加载最近50个批次ID，选择后点击查询；提交超时后先按已保留的批次ID查询。
“导出 CSV / JSONL”从后台导出整批原始公告、回执结果和失败样本，不受底部最近2000条日志限制。
后台需为新版，节点需刷入`cap_measure_v=1`固件；旧节点或未就绪节点会明确拒绝测试。
记录由后台SQLite保存，关闭车机后测试继续，后台重启则未完成记录标为中断且不自动重跑。
部署及判读见[能力公告验收](../changan-mesh-system/docs/operations.md#能力公告接收确认测量)。
节点页显示准入状态、授权版本，可授权接入或撤销授权。CLI：
`node admit NODE_ID REVISION`、`node revoke NODE_ID REVISION`。
Broker ACL尚待加载时，回执不表示连接已被踢掉。

根节点主机和四层网络启动见[运行说明](../changan-mesh-system/docs/operations.md)，
接口见[HTTP/WS合同](../changan-mesh-system/protocols/http/v1/README.md)。
未来终端经真实云端与Jetson交互，当前阶段直接连接本机后台，不设置模拟云端。

```powershell
uv run --locked python -m unittest discover -s tests
```
