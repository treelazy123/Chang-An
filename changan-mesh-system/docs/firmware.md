# 固件与设备身份

唯一固件工程位于firmware，使用ESP-IDF 6.1.x与ESP32-C6。角色是ugv_root、ugv、uav、
micro_uav，固定层级1/2/3/4。控制传输固定为mqtt_serial，构建配置版本为3。
根节点ID与后台ugv_id统一为ugv-root，设备清单位于config/nodes.json。

## 身份

根C6是透明网关，没有MQTT客户端证书。普通UGV/UAV/Micro各有独立证书，CN、Client ID、
node_id一致。后台身份controller-001，Broker服务名ugv-broker.lab；IP地址不代表身份。

已有secrets必须保留。查看登记：`uv run --locked python tools/provision_mqtt.py --list`。
新设备使用现有CA增量登记，例如：

```powershell
uv run --locked python tools/provision_mqtt.py --role ugv --node-id ugv-002 --ugv-id ugv-root
uv run --locked python tools/provision_mqtt.py --role uav --node-id uav-002 --ugv-id ugv-root
```

首次CA初始化仅用于空环境；有凭据时禁止重新初始化。登记不自动重启Broker。

## 用户构建与烧录

在仓库根目录执行配置预览，不启动IDF、不打开串口：

```powershell
uv run --locked python tools/lab.py --role ugv_root --node-id ugv-root --dry-run
uv run --locked python tools/lab.py --role ugv --node-id ugv-001 --dry-run
uv run --locked python tools/lab.py --role uav --node-id uav-001 --dry-run
uv run --locked python tools/lab.py --role micro_uav --node-id micro-001 --dry-run
uv run --locked python tools/verify_builds.py
```

实际编译和烧录由用户在ESP-IDF环境执行，例如：

```powershell
python tools/lab.py --role ugv_root --node-id ugv-root build
python tools/lab.py --role ugv_root --node-id ugv-root --port COM_ROOT flash
```

其他板将role/node-id/port替换为对应实物。每个node使用独立build/mqtt_serial/nodes目录。
缓存不符合架构版本3、角色、节点ID或管理root时明确拒绝，不能复用错误缓存烧录。

AP网段也属于设备构建配置：`config/nodes.json`的`ap_subnet`生成
`CONFIG_APP_SOFTAP_SUBNET`。中继节点的网段在同一清单中不得重复，STA地址继续由父AP的DHCP分配。
Micro是STA-only叶子，清单为`ap_subnet: null`，构建值为0，不占用AP网段。

| 节点 | 预留AP地址（/24） |
| --- | --- |
| ugv-root | 192.168.5.1 |
| ugv-001 | 192.168.6.1 |
| ugv-002 | 192.168.7.1（预留，待登记证书及授权） |
| uav-001 | 192.168.8.1 |
| uav-002 | 192.168.9.1 |
| micro-001 | 无AP，仅STA |
| micro-002 | 无AP，仅STA |

旧固件不执行该规划，需逐台重新构建、烧录（先根与UGV，再UAV，最后Micro）。
仅修改清单或重启后台不会改变板上的AP地址。首次更新为每台设备加`--reset-config`。
Micro连接uav-001时获取192.168.8.x，连接uav-002时获取192.168.9.x；默认由Mesh自动选择；指定父节点见[运行手册](operations.md#parent-selection)。
Micro启动日志应出现`AP_DISABLED`，工作模式为STA，关闭DHCP服务，遥测中`ap_enabled=false`，不报告AP地址。
车机网络表的AP地址与关联客户端显示“不适用（STA）”。
启动日志`AP_ADDRESS_PLAN`应与清单一致，`ADDR`及遥测应上报同一实际AP地址。
若出现`AP_SUBNET_OVERLAP`，修正父子节点的规划并重启，不能靠关闭检查维持连接。
手动重配后也不要擦除NVS或重新签发证书。ugv-002目前仅预留地址，未生成证书；
设备到位后运行`uv run --locked python tools/provision_mqtt.py --role ugv --node-id ugv-002 --ugv-id ugv-root`，
再通过后台授权接入。新增中继设备登记从192.168.10.0/24起保留未占用网段，Micro不分配AP网段；
禁用或撤销不会释放地址。旧自定义清单缺少`ap_subnet`时，用该设备的登记命令增量补齐，
复用现有证书和私钥；只读查询与dry-run不自动修改清单。

从旧架构升级时，同一设备的缓存可能仍是版本2，且管理节点仍为ugv-001。为该设备首次
重新构建时加一次`--reset-config`，例如：

```powershell
python tools/lab.py --role ugv --node-id ugv-001 --reset-config build
python tools/lab.py --role ugv --node-id ugv-001 --port COM5 flash
```

COM5仅为示例，必须按实物确认。工具将原sdkconfig备份为同目录的
sdkconfig.before-reset-时间戳，按当前默认配置重新生成，校验通过后执行请求的动作。
自定义menuconfig设置需要从备份核对后重新设置。节点ID或角色不一致仍拒绝重置；
证书、私钥、运行数据和设备NVS不受配置重置影响。可加`--dry-run`预览差异，不改文件。

根板原生USB保留给MUX1，UART0输出日志。用户编译后检查分区、Flash容量、堆/栈和NVS。
NVS记录包含已有格式读取，保持已记录任务不被擦除；固件升级不自动清空NVS。
