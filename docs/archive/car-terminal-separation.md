# 车机交互与UGV后台分离（0.6.0）

## 位置与职责

- 独立Git仓库 D:/changan/changan-car-terminal：车机CLI及串口/MQTT传输适配。无CA私钥、无设备登记、无时钟服务，无跨仓库代码导入。
- mesh_lite_node/tools/mqtt_controller.py：原有MQTT设备登记、校时、命令与ACK处理共享核心。
- mesh_lite_node/tools/ugv_service.py：无人车常驻后台，当前在模拟Jetson的电脑运行。关闭车机界面后继续校时和管理设备。
- mesh_lite_node/tools/mqtt_terminal.py：保留原list/ping/status/echo。发现本地后台后自动复用127.0.0.1:8787服务；没有后台时保持原来的组合式运行。--standalone显式请求旧模式，但后台已经运行则拒绝重复管理员身份。
- Broker与serial_tcp_bridge.py职责不变。根节点MQTT模式新增USB车机请求转发。

## 用户升级步骤

先退出旧mqtt_terminal，避免0.5.0及更早进程继续占用controller-001。新代码使用自动随进程释放的OS锁阻止两个管理员实例；旧进程没有这个锁，首次升级必须人工退出。不要重新生成证书。

1. 更新磁盘ACL：

```powershell
cd D:\esp\mesh_lite_node
uv run --locked python tools/provision_mqtt.py --sync-acl
```

2. 在维护窗口重载或重启项目8883 Broker。原1883/9883服务不用修改。自动代码没有重启在线服务。

3. 用户在ESP-IDF环境更新root C6（COM7）：

```powershell
python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --port COM7 flash
```

新root启动serial_gateway，并把USB请求与MQTT终端主题连接。不要让旧pc_terminal或其他程序同时占用COM7。该次新增只要求更新root；UAV/Micro及已升级八通道的UGV可继续使用现有固件。固件在本轮未编译，具体链接/容量需用户build验证。

4. 保持项目Broker与UGV COM4隧道运行；启动无UI后台：

```powershell
uv run --locked python tools/ugv_service.py --broker-port 8883
```

后台默认预留127.0.0.1:8787后再连接Broker，避免第二个后台抢占管理员MQTT身份；--rpc-port可配置，旧终端的--service-port需一致。该回环接口是实验电脑上的本地维护入口，只允许list及三个安全测试操作；不应作为远程车机网络接口，不具备远程用户认证层。

5. 在独立仓库启动车机CLI：

```powershell
cd D:\changan\changan-car-terminal
uv sync --locked
uv run --locked python -m car_terminal --port COM7
```

6. 需要保留原终端时，在固件工程运行原命令：

```powershell
uv run --locked python tools/mqtt_terminal.py --broker-port 8883
```

它会复用后台，不再创建第二个controller-001连接。没有后台时仍可单独使用旧功能。关闭该终端不停止已运行的后台。

## MQTT权限与协议

只有登记role=pc_root且enabled的设备得到：

- write mesh/v1/terminals/<id>/requests
- read mesh/v1/terminals/<id>/responses

controller-001负责读取请求并发布回复。UAV/Micro没有车机请求权限。后台再次核对消息源topic、node_id、角色清单、截止时间、命令操作、目标就绪与能力。

请求沿用MLT1/JSON格式：type=list或command、msg_id、deadline_unix；根节点覆盖node_id为自身身份，不能信任USB传来的源ID。后台将同一请求ID用于目标命令和实际ACK关联；按来源/ID缓存最近64个完成请求，重复返回原结果，相同ID不同内容拒绝，缓存不跨后台重启。仍仅执行幂等测试操作，无飞控或车辆执行器。

list逐节点发布nodes帧，more=true表示后续仍有帧，最终more=false；避免大列表超出C6的1024字节JSON限制。新车机CLI会汇总完整列表。旧legacy pc_terminal.py不支持此分页协议，应使用独立车机仓库。

后台请求队列16，逐条执行，排队后过期的请求拒绝。USB/MQTT缓冲有限，超时或队列满明确记录/由客户端报错，不自动重发，不宣称实际任务恰好执行一次。

## 验证范围

主机测试覆盖源身份拒绝、请求去重/截止时间、100+节点列表分页、兼容维护终端复用及退出不停止后台、单管理员OS锁。独立车机测试覆盖协议向量、串口分片、多页合并、错误节点ACK忽略。

本轮没有运行固件build、烧录、在线Broker重载或真实COM7连接。S31 USB网卡/IP可达路径和真实车机部署仍待硬件阶段。根节点的新C源码仅做静态结构检查，不能代替编译。
