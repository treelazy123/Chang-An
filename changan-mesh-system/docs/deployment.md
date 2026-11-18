# 根节点部署与交接

当前电脑承担根节点无人车主机，运行UGV Service、Mosquitto和USB桥接。后续迁移至
Jetson时保持相同程序边界，通过显式TOML配置提供路径，不能靠源码目录推断部署位置。
电脑示例config/ugv-root.dev.toml，Jetson示例config/ugv.jetson.example.toml。

移交清单：config/nodes.json、Broker配置及ACL、现有CA与所需设备/服务凭据、
runtime/ugv-root中的SQLite和journal、源码版本、依赖锁、每块板的角色/身份/端口记录。
凭据保持原值；目标存在不同密钥或CA时拒绝覆盖。根C6没有MQTT客户端证书。

状态迁移使用SQLite backup包含WAL，先正常停止相关后台并取得控制器锁，不复制运行中
数据库的单个主文件。`tools/sync_runtime.py --source SOURCE_ROOT`用于受控迁移，目标旧状态
先备份，不签发证书、不切换生产服务。现场执行前核对源和目标的root归属与任务目标。

Jetson需另外验收Python/系统依赖、Mosquitto、USB驱动、端口权限和开机服务顺序。
S31或其他网卡属于后续传输适配，不应改变节点身份、可信清单或任务恢复语义。

未来汽车和Jetson各自通过公网/5G连接真实云端。当前车机只在本机通过HTTP/WS访问后台，
不增加模拟云端，也不直接把本机HTTP端口暴露到公网。云端身份、授权与补传协议待实施。

<a id="hardware-handoff"></a>

## 根节点无人车硬件交接

根节点无人车由主机和组网模块组成：主机暂为电脑，后续Jetson；组网模块当前C6。
主机运行UGV Service、Mosquitto、USB桥接。根C6使用ugv_root角色、node_id=ugv-root，
下级UGV/UAV/Micro依次为第2/3/4层。汽车终端不在Mesh中。

交接时记录每块板node_id、role、root_id、固件版本、STA/AP MAC、实际COM口及供电。
固定层级不证明实际父节点；按parent_bssid与唯一ap_mac核对，未知关系保持未知。

验收顺序：主机HTTP与后台任务持久化；独立节点mTLS与ACL；根板USB/MUX1；
普通无人车第2层；无人机第3层；微型无人机第4层；跨层控制/状态；逐环节断连恢复。
业务数据通道、S31驱动/USB网卡、Jetson实机性能、云端与5G分别验收，不能用电脑测试代替。

运行命令见[运行说明](operations.md)，烧录由用户按[固件说明](firmware.md)执行。
保留现有密钥、NVS和SQLite，不通过擦除状态构造成功结果。
