# 运行与排障

## 准备

在主仓库执行，配置生成不重启服务、不签发凭据：

```powershell
cd D:\changan\changan-mesh-system
uv sync --locked
uv run --locked python tools/run_tests.py
uv run --locked python tools/configure_broker.py --inventory config/nodes.json --acl-file runtime/ugv-root/acl.conf --output runtime/ugv-root/mosquitto.conf
```

切换前由用户正常退出占用同一身份、端口或COM口的实例。下列程序分别启动，不重复启动。

## 根节点主机

```powershell
& 'D:\Program Files (x86)\Mosquitto\mosquitto.exe' -c 'D:\changan\changan-mesh-system\runtime\ugv-root\mosquitto.conf' -v
```

```powershell
uv run --locked ugv-service --config config/ugv-root.dev.toml
```

用户完成新固件烧录后，以实物端口替换COM_ROOT：

```powershell
uv run --locked ugv-serial-bridge --port COM_ROOT --broker-port 8883 --ugv-id ugv-root
```

根节点原生USB用于MUX1，日志用UART0。后台默认只监听127.0.0.1:8080；它不是公网入口。
任务与主机journal位于runtime/ugv-root。controller-001由排他锁保护，不能同时开多个后台。

## 终端

```powershell
cd D:\changan\changan-car-terminal
uv sync --locked
uv run --locked python -m car_terminal.gui --base-url http://127.0.0.1:8080
```

GUI打开后手动连接。CLI：`uv run --locked python -m car_terminal --command list`。
主仓库维护查询可用`uv run --locked ugv-console --command "ping ugv-001"`，同样走HTTP。
终端不需要COM口或节点证书。关闭终端后后台继续管理任务。

## 准入管理与排障

节点页显示信任状态和授权版本，选择后可授权接入或撤销。CLI支持
`node admit NODE_ID REVISION`、`node revoke NODE_ID REVISION`、`node pending NODE_ID REVISION`。
版本按实际查询填写，不自动覆盖冲突。授权仅限已登记且归当前root管理的节点。
后台写入清单和审计，生成runtime/ugv-root/acl.pending.conf；Broker ACL加载由用户受控执行。

HTTP无法连接时检查后台及8080端口；Broker离线不等于无线设备断开。ready需要当前boot的
presence、capabilities和新鲜telemetry。根C6状态还依赖有效USB NETWORK报告。
授权撤销不会证明既有物理任务停止。请求超时先按task_id查询，不盲目重发。
不得删除数据库、journal、证书或私钥来修复连接。

<a id="parent-selection"></a>

## Micro父节点选择

终端“网络结构”页提供“Micro上游连接设置”。先刷新节点，填写或选择Micro，点击查询配置，
再选择父UAV和模式，点击应用。期望父节点与实际父节点分别显示，已接收不代表切换成功。

| 模式 | 行为 |
| --- | --- |
| 自动 | 允许所有符合原Mesh ID、角色层级等条件的候选父节点 |
| 优先指定 | 先限制到指定UAV；启动、切换或目标断开后等待30秒，未连接目标则允许自动选择 |
| 固定指定 | 只允许指定UAV，目标不可用时保持离线 |

优先模式回退后保持自动候选，直到重新应用配置或节点重启，不主动反复抢回目标。
Micro仍固定第4层，父UAV必须为同root下已授权、在线的第3层节点。
父节点必须上报真实AP MAC、AP SSID及AP启用状态；旧固件缺少这些字段时拒绝配置。
Micro本身必须已授权、就绪，并公布parent操作能力。

### 调用与状态

车机通过本机HTTP/WS访问UGV Service。后台检查清单和新鲜观测，将父节点ID解析为BSSID及SSID，
通过现有MQTT/TLS commands主题下发op=parent。用户不能绕过后台直接指定任意BSSID。
SQLite parent_policies表先记录意图、请求ID和版本，再下发；服务重启与请求超时均不自动重发。
再次提交必须先查询配置版本。相同请求ID及相同内容不会重复派发，不同内容返回冲突。

Micro验证命令有效期、可信时钟和版本后，将策略保存在独立NVS命名空间parent_policy。
命令接收后约2秒触发Mesh重新连接，给ACK入队留出时间，不保证ACK必然在断线前到达。
MAC白名单使用当前Mesh-Lite的esp_mesh_lite_get_ssid_by_mac_cb_register接口，
所有自动候选SSID按本项目公共前缀（前20字符）加AP MAC后缀的约定生成；不要对个别节点使用不同SSID前缀。
仍由Mesh-Lite完成合法Mesh候选筛选、层级约束与连接，不单独用Wi-Fi连接替代组网。

仅当Micro以当前启动的新鲜遥测报告相同策略版本、模式及匹配的实际父BSSID时，后台显示已生效。
遥测中pending阶段不算生效；prefer模式报告fallback时显示已回退。60秒未收到确认显示未确认，
不能据此断言未执行。没有重连时通过查询观察状态，不自动创建新请求重试。
STA地址及网关仍从所连接UAV的DHCP获取，Micro不启用AP。

### 部署与固定模式恢复

实际编译、烧录由用户执行。先更新UAV固件，使其上报AP SSID，再更新Micro固件。
重启后台加载新代码，重新打开终端；不需要重新签发已有证书或擦除NVS。
若Micro遥测持续更新、父链路已连接，但显示“在线·未就绪”，请先核对后台是否已更新并重启。
旧后台不识别新增的parent操作，会拒收新能力公告，使业务就绪检查无法通过；遥测年龄小只表示遥测新鲜，不能替代能力校验。
开发环境在原UGV Service窗口停止旧进程后，从项目根目录重新运行：

```powershell
uv run --locked ugv-service --config config/ugv-root.dev.toml
```

现有构建缓存如果提示不匹配，按固件说明为该设备使用一次--reset-config。

固定模式离线后，远程“自动”命令无法送达。需先恢复目标UAV，或使用维护固件：
在该Micro的menuconfig打开APP_PARENT_POLICY_RECOVERY_AUTO后由用户构建、烧录。
维护固件暂时忽略已保存的绑定并自动联网，不清空其他NVS数据；连上后在终端查询并应用自动模式，
保存新的策略。随后关闭维护选项，恢复正常固件。注意--reset-config会重建SDK配置，
维护选项应在重建配置之后设置。不要通过擦除NVS、删除任务数据库或重建密钥恢复连接。

后台任务数据库与Micro的策略版本必须一并保留。若恢复了过旧的后台数据库，节点可能拒绝旧版本，
应恢复正确的数据库备份并核对节点遥测，不得绕过版本检查盲目重发。

## 常见故障速查

| 现象 | 检查与处理 |
| --- | --- |
| 终端无法连接 | 检查后台、HTTP 地址及 8080 端口；终端打开后需手动连接 |
| 遥测很新但显示未就绪 | 核对当前启动的 presence、capabilities、telemetry；旧后台拒收新增 parent 能力时，停止原后台并按上方命令重启 |
| 父节点应用出现 parent_apply KeyError | 更新并重新打开终端；新版已补齐按钮标签 |
| 节点选中后跳掉、输入被覆盖 | 更新并重新打开终端；新版刷新保留选中行、焦点和编辑内容 |
| 中继 AP 地址重复 | 按固件手册核对清单并逐台更新固件；重启后台不改变设备地址 |
| Cached sdkconfig does not match | 按固件手册为该设备使用一次 --reset-config，核对实物身份和端口 |
| 固定父节点后离线 | 恢复目标 UAV，或按本页维护步骤恢复；离线节点收不到远程命令 |

“在线·未就绪”表示 MQTT 在线但业务校验未通过，不能仅凭遥测年龄小跳过能力和授权校验。
