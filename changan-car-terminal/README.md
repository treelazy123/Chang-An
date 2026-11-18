# 长安车机终端

独立HTTP/WebSocket终端，不加入Mesh，不持有节点证书，不占用C6串口。
GUI和CLI通过版本化协议访问UGV Service，不导入主仓库业务源码。

```powershell
uv sync --locked
uv run --locked python -m car_terminal.gui --base-url http://127.0.0.1:8080
uv run --locked python -m car_terminal --command list
```

GUI打开后手动连接。HTTP提交节点查询和任务操作，WebSocket推送状态并按游标重连补查。
网络结构页可设置Micro的上游UAV：刷新节点，查询Micro配置后选择自动、优先指定或固定指定并应用。
结果显示期望与实际父节点；配置接收后需等待重连确认。固定模式离线后的恢复见
[父节点选择说明](../changan-mesh-system/docs/operations.md#parent-selection)。
检查/基础诊断节点支持输入或下拉选择；后台快照刷新不会覆盖正在编辑的节点。
网络表中Micro的AP和关联客户端显示“不适用（STA）”，STA地址由所连接的UAV分配。
任务变更不自动重发；超时后按任务ID查询。关闭终端后后台继续执行。
节点页显示准入状态、授权版本，可授权接入或撤销授权。CLI：
`node admit NODE_ID REVISION`、`node revoke NODE_ID REVISION`。
Broker ACL尚待加载时，回执不表示连接已被踢掉。

根节点主机和四层网络启动见[运行说明](../changan-mesh-system/docs/operations.md)，
接口见[HTTP/WS合同](../changan-mesh-system/protocols/http/v1/README.md)。
未来终端经真实云端与Jetson交互，当前阶段直接连接本机后台，不设置模拟云端。

```powershell
uv run --locked python -m unittest discover -s tests
```
