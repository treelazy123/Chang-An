# M1 COM7 实物验收记录（2026-11-14）

使用用户指定的 `uv run --locked python -m car_terminal --port COM7`，通过既有物理 Mesh-Lite 网络执行。仅启动/退出测试用车机 CLI；没有编译、烧录、重启 Broker 或 UGV 后台，也未拔插或控制硬件供电。未修改应用程序。

## 已通过

- 常规实物验收 16 项：五节点就绪、既有取消与自然完成记录、配置版本/冲突、双 Micro 并行、运行中更新拒绝、暂停采样冻结与另一节点独立推进、恢复采样、独立取消、root/UAV/UGV 自然完成、终态控制拒绝、任务事件游标与列表分页。
- Micro-002 追加复测 4 项：同节点单活动任务、车机退出重连任务继续且不重复开始、两任务依次完成（20/5 样本）、uptime 连续。
- Micro-001 追加复测 4 项：相同排队和车机重连流程通过，20/5 个样本，复测期间 uptime 连续。
- 本次创建的所有任务均已完成或取消；测试 CLI 已退出，COM7 已释放。

## 稳定性异常：仍未关闭

Micro-001 首次排队验收中，第一任务 SUCCEEDED，第二任务经历 DISPATCHING → RECONCILING/node_offline → UNKNOWN，最后由测试清理取消。不能将该轮记为通过。

已观测到 Micro-001 uptime 回退；用户明确表示未断电、复位或拔插。该异常暂不能归因于用户操作，也不能仅凭后续复测通过认定消失。节点重启和排队任务未执行的准确先后/因果尚未确定。

现有车机状态没有复位原因和崩溃回溯，仅凭 CLI 不能确定具体原因。下一步应优先获得该节点启动日志/复位原因，再做针对性修复；不直接假设为看门狗、供电或任务逻辑问题。

## 本轮未执行

- 人工节点断电/上电。
- UGV USB 物理拔插。
- Broker 停止/重启。
- UGV 后台服务重启。
- 原始重复包/证书/跨主题权限探测（此前已有独立验收，本轮 CLI 不提供原始报文接口）。

这些项目不能用车机退出/重连代替，本轮也没有以节点意外重启替代受控故障验收。

## 证据

- [verification-m1-hardware-com7.json](verification-m1-hardware-com7.json)：16 项 PASS，0 项 FAIL；时间 2026-11-14T20:11:58.388283+08:00。
- [verification-m1-hardware-car-reconnect.json](verification-m1-hardware-car-reconnect.json)：2 项 PASS，1 项 FAIL；时间 2026-11-14T20:16:39.159913+08:00。
- [verification-m1-hardware-car-reconnect-micro002.json](verification-m1-hardware-car-reconnect-micro002.json)：4 项 PASS，0 项 FAIL；时间 2026-11-14T20:25:51.691183+08:00。
- [verification-m1-hardware-car-reconnect-micro001-retest.json](verification-m1-hardware-car-reconnect-micro001-retest.json)：4 项 PASS，0 项 FAIL；时间 2026-11-14T20:35:36.014469+08:00。

## 重启时间线补充

综合直接 CLI 和脚本报告中的状态快照，Micro-001 有多次非人工重启迹象，而非仅一次偶发。root uptime 持续增长，Micro-001 则多次回退，或相对于 root 的同期增长出现数百秒缺口。各节点遥测不是同一瞬间采样，不据此给出精确重启次数或时间。

| 快照顺序 | root uptime_ms | Micro-001 uptime_ms |
| --- | ---: | ---: |
| 1 | 1424786 | 1130541 |
| 2 | 2119352 | 263149 |
| 3 | 2685636 | 323349 |
| 4 | 2996103 | 271704 |
| 5 | 3031243 | 306912 |
| 6 | 3582058 | 355879 |
| 7 | 3612186 | 390979 |

完整来源见 [uptime 异常记录](verification-m1-hardware-uptime-anomaly.json)。基础功能通过，M1 稳定性验收仍未通过；优先获得 Micro-001 复位原因/启动日志，之后再进行修复和受控故障验收。
