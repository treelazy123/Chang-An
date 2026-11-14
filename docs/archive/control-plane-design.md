# 当前控制面：UGV 汇聚 + root USB 网关

当前按用户确认的连接关系实现：

```text
UAV ─TCP→ UGV ─TCP→ PC端root C6 ─原生USB串口→ PC程序
Micro ─TCP→ UGV
```

无线 chain 仍为 root(1)→UGV(2)→UAV(3)→Micro(4)。TCP 连接端点不等于每一跳无线父子关系。

PC 以 node_id 为目标发送测试命令，root 将非本机命令交给 UGV，UGV 处理自己的命令或通过对应下游 TCP 会话转发。目标生成 ACK，原始 msg_id 跨代理保留。设备定期上报状态，UGV 汇聚消息时保留内部设备身份，root 解包后输出到 PC。

当前协议及异常处理见 [protocol.md](protocol.md)，实际启动步骤见 [bringup.md](bringup.md)。当前已实现通信骨架与 ping/status/echo，不包含 MQTT Broker、服务注册中心、生产认证、真实车辆任务、媒体传输或 UWB 驱动。

2026-11-10 的 PC 热点/MQTT 设计保存在 [历史设计](archive/three-node-2026-11-10/control-plane-design.md)，该文件是历史提案，不代表当前部署方式。后续加入实际任务时应在现有两级代理链路上明确任务 ID、去重、执行状态与断线恢复规则。
