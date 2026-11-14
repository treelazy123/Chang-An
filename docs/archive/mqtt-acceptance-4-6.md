# 第4～6项现场验收步骤

用户已确认第1～6项全部完成。第5项已有实际 Broker 的完整10项 PASS 输出；第6项附有 root/UGV/UAV 容量 PASS 输出，Micro 默认目录产物 MISSING，各节点最低堆具体数值尚未附入记录。以下保留操作步骤用于复测。当前 root COM7、UGV COM4、UAV COM5；Micro 端口未记录。正式验收前保存现有 list/status，保留 Broker 与串口隧道日志。每种故障单独测试，恢复三节点 ready 后再进行下一种。

## 4. 离线检测与恢复

### A. 关闭项目 Broker

此测试操作由用户执行。项目 8883 Broker 与原有 1883/9883 服务不同。确认需要停止的进程后，只停止 8883 对应进程：

```powershell
Get-NetTCPConnection -LocalPort 8883 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
```

根据输出确认项目进程，再 `Stop-Process -Id 实际项目进程ID`，不要停止其他 Mosquitto 服务。前台启动的 Broker 可直接 Ctrl+C。

预期：控制终端检测 Broker 断连，list 的三个节点 ready 都变 false，命令被拒绝或明确失败。Broker 整体停止时无法发布遗嘱，不能要求此时仍收到 LWT；终端依靠连接断开清空登记。

恢复（另开终端保持运行）：

```powershell
& 'D:\Program Files (x86)\Mosquitto\mosquitto.exe' -c D:\esp\mesh_lite_node\host\runtime\mosquitto.conf -v
```

保留 COM4 隧道。终端 Paho 会退避重连，长时间断开后可能要等待约两分钟；也可以退出后重开 `uv run --locked python tools/mqtt_terminal.py --broker-port 8883`。确认三节点重新认证、重新上报能力/在线/新遥测，再逐个 ping/status/echo，旧命令没有重新执行。建议观察窗口180秒，并记录实际重连耗时；超时后查日志，不直接假定网络永久失联。

### B. 单节点重启

先对 root、再 UAV、再 Micro 分别复位/断电重启，每次恢复后再测试下一个。不要同时拔 UGV USB，避免混入第3项故障。

预期：目标先变未就绪；恢复后 uptime_ms 从较小值开始，重新收到本轮能力与遥测并 ready，ping/status/echo 正常。root 重启可能让全链重建；UAV 重启或掉电可能使下挂 Micro 同时离线，这符合链式拓扑。

### C. UAV 突然掉电

拔 UAV 的全部供电并保持至少30秒；若另有电池/供电线，单拔 USB 不代表掉电。保持 root、UGV、Broker 与控制终端工作。

每5秒 list 一次。ready 依据最后有效遥测20秒失效；Broker 存活时还应能在日志看到 UAV 遗嘱 presence 的 offline 消息。keepalive=15秒，MQTT3.1.1 规范要求1.5倍间隔无控制包时断开，实际还有TCP/隧道检测，因此30秒作为首轮观察窗口，超过则保留日志继续定位。

root 应保持可用；Micro 若仍下挂 UAV，也应失联。UAV 恢复供电后重新认证/ready，再分别 ping。记录故障时刻、首次 ready=false 时刻、恢复供电时刻和首次恢复 ready 时刻。一次 list 看见 false 并不能单独证明 LWT 已送达。

## 5. 实际 Broker 的证书与主题权限

新增手动工具 `tools/verify_broker_security.py`。它会使用 controller-001 和 micro-001 的真实证书连接同一 Broker；配置绑定证书身份和 client ID，因此会替换同身份在线会话。测试前必须在 mqtt_terminal 输入 quit，并让 Micro 断电；其余节点可保持在线。保持 Broker 和 COM4 隧道运行。

```powershell
uv run --locked python tools/verify_broker_security.py --broker-port 8883 --clients-stopped
```

逐条 PASS 才算通过：
- 合法 controller/Micro 证书可以认证。
- Micro 发布自己的 ACK 主题，controller 实际能收到，作为正向对照。
- Micro 发布 UAV 的 ACK 主题，被 MQTT5 PUBACK 拒绝，controller 没有收到探针。
- Micro 收到自己 commands 主题的探针，收不到 UAV commands 的探针；不能仅凭 SUBACK 成功判定越权成功。
- 缺失客户端证书被真实 Broker 拒绝。
- 临时自签的不可信客户端证书被真实 Broker 拒绝。

探针为 acceptance_probe，不是有效 command，不触发 ping/status/echo 或执行器。消息不 retained，测试不更换现有证书、不修改 ACL；临时错误证书随测试清理。工具使用 MQTT5 取得明确的拒绝原因，现有固件仍使用 MQTT3.1.1，不需要改协议版本。超时或网络错误判失败，不当作权限拒绝成功。

保存完整 PASS/FAIL 输出和同一时间的 Broker 日志。结束后重新启动 mqtt_terminal，给 Micro 上电，确认三节点恢复 ready。用户已执行该工具并提供实际项目 Broker 的完整10项 PASS 输出，第5项已标记通过。

## 6. 分区大小与 TLS 最低空闲堆

### A. 只读现有构建产物

```powershell
uv run --locked python tools/check_firmware_size.py
```

读取每个角色已有 mesh_lite_node.bin 和编译生成的 partition_table/partition-table.bin，不触发构建或串口操作。PASS 表示镜像实际字节数不超过 factory app 分区；MISSING 不能算通过。若 Micro 在其他目录构建：

```powershell
uv run --locked python tools/check_firmware_size.py --build-dir 实际构建目录 --json
```

本次读取到的历史产物（尚不包含新加 heap_min 指标）：

| 角色 | app镜像字节 | app分区字节 | app剩余字节 | 占比 |
|---|---:|---:|---:|---:|
| root | 1194416 | 2031616 | 837200 | 58.79% |
| UGV | 1077408 | 2031616 | 954208 | 53.03% |
| UAV | 1194560 | 2031616 | 837056 | 58.80% |
| Micro | 当前目录未找到 | — | — | 未测 |

这表示 app 分区余量，不是整片 Flash 的可用空间。改变固件后重新读取新产物。

### B. 最低空闲堆

本次给 app_protocol 的 status/telemetry 和 UART STATUS 增加 heap_min=esp_get_minimum_free_heap_size()，需要用户重新编译烧录后才能读到。heap 是当前值，heap_min 是本次启动以来全系统的最低值，覆盖启动、TLS握手及重连的内存峰值，不是专属TLS分配计数。

为避免 COM4 被占用，重刷 UGV 前先关闭其后台串口转发进程，刷完再启动一次。不要重新生成证书。

```text
mqtt> status pc-root-001
mqtt> status uav-001
mqtt> status micro-001
```

UGV 自身无 MQTT 客户端，最低堆从 UART0 的 STATUS heap_min 读取；原生 USB COM4 是业务隧道，不是 UART0 控制台。

推荐验收负载：三节点同时 ready，依次发送 ping/status/echo，持续至少30分钟；再做10轮USB/网络重连。每轮恢复后记录 heap、heap_min、uptime_ms。

通过标准：无内存分配失败、TLS失败、栈溢出/看门狗重启；稳定空闲堆在预热后没有持续下降趋势；最低堆留有后续功能所需余量。heap_min 只降不升是统计定义，不能把这一个字段的下降直接判作泄漏。此阶段尚无经实测确认的统一字节门槛，不用随意阈值代替实际峰值/稳定性测试。

记录每个角色最终镜像占用、首次握手后heap_min、重复重连后的heap/heap_min、运行时长、是否发生重启。四个角色的容量与内存数据齐全后再标第6项通过。
