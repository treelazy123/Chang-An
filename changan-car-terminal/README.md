# 长安车机终端

独立车机程序，提供桌面调试界面、CLI、串口与 MQTT 传输。只实现版本化业务协议，不导入主仓库运行时代码，不管理 CA、设备登记或管理员会话。

电脑车机 C6—Jetson S31—UAV C6 的部署交接从 [Jetson / S31 交接任务](../changan-mesh-system/docs/handoff/README.md) 开始。

## 桌面调试界面

~~~powershell
cd D:\changan\changan-car-terminal
uv sync --locked
uv run --locked python -m car_terminal.gui --port COM7
~~~

窗口打开后手动点击“连接”，再刷新节点。COM7 是此前 root C6 的端口，实际以设备枚举为准；COM4 是此前 UGV 桥接口，不作为车机串口。同一 root 端口不同时打开 GUI、CLI 或串口监视器。

| 页面 | 功能 |
| --- | --- |
| 节点调试 | 节点列表、目标选择、Ping、状态、Echo |
| 诊断任务 | 创建、查询、开始、暂停、恢复、取消及游标事件补查 |
| 网络结构 | Mesh 父子树、层级、STA/AP IP、网关、RSSI、信道、关联客户端数和遥测年龄 |
| 调试结果 | 响应 JSON、错误、时间、请求耗时；导出最近 2000 条结果为 UTF-8 JSONL |

任务控制携带已查询版本；冲突后重新查询，不自动覆盖或重发。创建超时会提供可查询的任务 ID，先查询再决定是否重新创建。请求受理不等于执行完成，最终结果以任务状态和事件为准。关闭窗口只关闭本车机连接，不取消后台任务。

## 网络结构

点击“刷新网络结构”，与刷新节点使用同一个只读 list 请求。表格底部可横向滚动；选中节点查看 MAC、父 BSSID、子网掩码，并同步调试目标。

父子关系按父 BSSID 匹配唯一的节点 AP MAC，不根据角色、层级或 IP 猜测。外部 AP、未上报、未关联、旧启动、重复 MAC 和关系环分别显示；灰色为未就绪快照，断开后的旧数据不表示仍在线。

完整网络字段需要节点固件上报；旧固件已有层级可显示，缺失字段标为“未上报”。UGV C6 通过协商式 USB 报告提供无线信息，主机后台把它加入 list 响应；主机任务服务和 C6 无线状态分别判断。没有报告时只显示主机服务，不虚构无线地址。

## CLI 与任务

新增“区域巡检（ESP32测试）”“异常复核（ESP32测试）”两种服务任务，以及“测试异常事件”页。能力服务页逐节点列出每台UAV的复核服务、每台Micro的巡检服务，显示执行模式、公告状态和当前任务；旧固件显示需更新。需要更新后台、车机及对应UAV/Micro固件，步骤见 [ESP32流程验证说明](../changan-mesh-system/docs/esp32-workflows.md)。

删除已结束历史任务：在“服务任务”页选择并查询任务后，点击“删除所选历史任务”，或使用 `task delete TASK_ID [REVISION]`。运行中、暂停或未确认任务需先取消并确认终态；被未结束的监视任务引用时需先结束监视。删除清理该任务及后台关联历史，不影响其他任务。接口复用现有网关通道，无需更新节点固件。

新版“服务任务”页增加网络诊断与任务运行监视，并在“能力服务”页查看两项主机服务。网络诊断选择执行主机与被检查节点，显示成功/失败和主机到节点的往返耗时；任务运行监视选择已有任务 ID，显示状态、进度及反馈超时。两项服务可并行运行，需要更新 UGV 后台，无需修改节点固件。操作步骤及测量边界见 [主机服务说明](../changan-mesh-system/docs/host-services.md)。

~~~powershell
uv run --locked python -m car_terminal --port COM7
~~~

~~~text
list
ping micro-002
status uav-001
echo micro-002 hello
task create micro-002 30 1000
task list
task get TASK_ID
task start TASK_ID
task pause TASK_ID
task resume TASK_ID
task cancel TASK_ID
task events 0 TASK_ID
watch TASK_ID
quit
~~~

TASK_ID 替换为返回的编号。create 不自动开始，watch 用 Ctrl+C 返回提示符，后台任务继续。CLI/API 支持 CREATED 状态的配置更新；完整参数、版本规则和故障语义见 [任务操作](../changan-mesh-system/docs/tasks.md)。

单次命令：

~~~powershell
uv run --locked python -m car_terminal --port COM7 --command "status uav-001"
~~~

## MQTT 直连

~~~powershell
uv run --locked python -m car_terminal.gui --transport mqtt --host 实际Broker地址 --broker-port 8883 --node-id pc-root-001 --cert-dir 'D:\实际车机证书目录' --server-name ugv-broker.lab
~~~

CLI 使用同样的连接参数。证书目录只包含本车机所需的 ca.pem、client.pem、client.key；CA 私钥与管理员证书留在管理端。始终校验 TLS 服务名。不要让 C6、车机或网卡管理客户端同时复用同一证书身份与 MQTT Client ID。S31 实际网卡/IP 路径仍需硬件验收。

## 协议与测试

MLT1 为 magic、网络序长度、CRC16-CCITT-FALSE 与 UTF-8 JSON；帧 JSON 最大 1024 字节，请求最大 512 字节。列表分页汇总，ACK 必须匹配请求与目标；超时不自动重发。

界面使用 Python 自带 Tkinter，不增加第三方 GUI 依赖。回归使用假传输，不连接真实 COM 或生产 Broker：

~~~powershell
uv run --locked python -m unittest discover -s tests -v
~~~

主仓库先启动 Broker、UGV 桥接与常驻后台，再连接车机。完整说明统一在：

- [文档索引](../changan-mesh-system/docs/README.md)
- [运行与排障](../changan-mesh-system/docs/operations.md)
- [系统架构](../changan-mesh-system/docs/architecture.md)
- [部署与交接](../changan-mesh-system/docs/deployment.md)
- [协议 v1](../changan-mesh-system/protocols/v1/README.md)
- [验收与部署状态](../changan-mesh-system/docs/status.md)
