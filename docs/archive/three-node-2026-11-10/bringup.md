# 三板上电与验证步骤

## 1. 先标记实物

三块板贴上 `ugv-001`、`uav-001`、`micro-001`，一次连接一块，读取串口与启动日志中的STA/AP MAC后填写 `hardware/nodes.csv`。串口号可能随USB位置变化，不作为设备身份。

## 2. 使用已有IDF环境

从 ESP-IDF 6.1 终端或 IDE 已激活环境运行 `idf.py --version`，记录完整版本；当前基线为 ESP-IDF 6.1.x。若普通PowerShell找不到idf.py或脚本提示IDF_PATH未设置，先激活已安装SDK；不需要因此重新安装一套。第三方组件已保存在 `components`，构建不再联网解析这些依赖。

## 3. 直连基线star

按README构建三种角色，分别烧录到对应实物。先启动ugv，再启动uav和micro。等待网络稳定，核对：ugv的level为1；uav和micro均为2；两者parent等于ugv的AP MAC；共用信道相同；STA IP有效。初始化阶段level为0或parent为全零不能当作最终拓扑。

此阶段只证明关联、层级与地址配置。还没有业务Socket，不能据此宣称完成端到端可靠传输或达到吞吐指标。

## 4. 两跳基线chain

三种角色均改用 `--topology chain` 构建并分别烧录。启动顺序为ugv、uav、micro。核对：ugv=1，uav=2，micro=3；uav.parent等于ugv.ap_mac，micro.parent等于uav.ap_mac。记录每块板的日志，而非只看root的一份节点列表。

角色／拓扑切换后需考虑SDK保留的连接信息。先观察是否收敛到预期层级；如需清理NVS，应明确记录并手动执行对应操作，不把每次启动都擦除NVS写入正常流程。当前程序遇到NVS初始化错误会报错停止，不自动擦除。

## 5. 自愈实验auto

使用三板一致的auto配置，记录稳定后的真实路径，再手动断开中继供电或改变覆盖条件。原始记录区分“关联恢复”“到root可用”“业务恢复”；业务层尚未实现时，后两项标记未测。不要将固定chain下无法回退第2层误判为自动自愈缺陷。

## 6. 定时器任务栈越界排查

若出现 `Detected in task "Tmr Svc"` 和 `Stack protection fault`，先检查该构建目录的 `CONFIG_FREERTOS_TIMER_TASK_STACK_DEPTH`。2026-11-09 的 chain 日志中，uav 和 micro 均出现此异常，原配置为2048字节；官方 no_router 示例为3072字节，本工程现设为4096字节，供定时器回调及恢复路径留出余量。这是针对已观察到的栈越界调整，仍需上板验证，不能据编译成功判断已彻底修复。

已有 `build/<角色>-<拓扑>/sdkconfig` 会覆盖 defaults 中的同名默认值。6.1 重构从 defaults 重新生成配置；以后手动改 defaults 时，可通过对应角色的 `menuconfig` 设置 FreeRTOS 的 `configTIMER_TASK_STACK_DEPTH`，重编译并重新烧录。不要修改 `CONFIG_ESP_TIMER_TASK_STACK_SIZE` 来代替它，二者是不同任务。

状态日志新增 `STACK node=... timer_size=4096 timer_min_free=...`。`timer_min_free` 是该任务启动以来栈剩余空间的历史最小值，单位为字节；它不同于总空闲堆 `heap`，也不是对最大栈需求的保证。三板重烧后持续运行，观察是否再次重启，以及断连恢复时的栈余量。

原 uav ELF 摘要前缀为 `8f3741f86`，micro 为 `cfc1f8c73`，均已与故障日志匹配。uav 的 ROM 故障地址可解析到 `_dtoa_r`，返回地址在 `_svfprintf_r`，提示当时正执行数值格式化；其寄存器中的格式字符串地址对应 `%1.15g`，与 SDK cJSON 的数字序列化格式吻合，强烈指向该格式化路径。cJSON 对部分整数也会走浮点数格式化，因此业务没有显式使用小数并不能排除此路径。micro 的已解析地址涉及 UART/VFS 输出及锁。原始日志只有寄存器和部分栈内存，不构成完整调用链，不能据此指定某个 Mesh-Lite 内部回调为唯一根因。调整后的固件仍需运行和断连恢复复测。

断连原因209表示父AP未回应SA Query。若父节点同时发生崩溃，它可能是下游断连的原因；需用实际时刻对齐三端日志，不能直接比较不同板子的开机毫秒数。`netif network segment conflict check` 只说明执行了网段检查，不能单凭此行判断发现冲突。

## 7. 下一步里程碑

| 阶段 | 可验收结果 |
| --- | --- |
| M0 环境与构建 | 三种角色成功编译，记录SDK、vendor-lock.json与串口映射 |
| M1 组网 | star与chain均有三端日志证明真实拓扑 |
| M2 双向业务 | root本地TCP服务；两节点注册和心跳；带task_id的测试指令与回执 |
| M3 文件 | 已知内容分块传输，校验完整性，测断线续传与并发 |
| M4 流量实验 | 发送节奏、队列上限、负载／跳数对时延吞吐的影响 |
| M5 UWB协同 | 接入实际模块，做与Wi-Fi原生恢复机制的对照实验 |

本阶段终点是无人车root，车载其他终端业务另行处理。root通信节点内存有限，文件验证可先选小数据并流式计算校验，不预设能够在RAM中保存完整大图像。
