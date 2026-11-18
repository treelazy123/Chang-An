# 系统架构

## 设备和无线结构

ugv-root 是第1层根节点；普通 ugv 第2层；uav 第3层；micro_uav 第4层且为叶子。
同层可有多个设备，设备类型不绑定某个固定编号。实际父子关系按 parent_bssid 匹配
唯一 ap_mac，不能根据角色、IP或层级猜测现场连接。汽车终端不加入自组网。

AP采用清单预留的独立`192.168.N.0/24`网段，AP及DHCP网关为`192.168.N.1`；
N由中继节点的`ap_subnet`指定，范围4..254，当前预留5/6/7/8/9给根、两台UGV和两台UAV。
Micro关闭AP与DHCP服务，清单中`ap_subnet=null`，仅STA从父UAV的DHCP获取地址。
兄弟分支不能复用AP网段，
禁用或撤销节点仍保留地址。该规划覆盖同一清单内的节点，不提供跨独立部署的地址协调。
Mesh-Lite的自动选择主要避开本机/上游网段，不承担全网唯一分配；应用启动时应用预留地址，
阻止默认分配器改写，并在STA/AP网段重叠时断开Mesh连接、要求修正规划后重启。
AP唯一不等于下级STA可以从其他分支直接寻址；当前业务仍使用节点到根的MQTT/TLS会话。

## 根节点程序

根节点由 C6 组网模块与主机组成，主机暂用电脑，后续为 Jetson。

| 程序 | 职责 |
| --- | --- |
| UGV Service | HTTP/WS入口、节点信息、准入/授权/撤销、服务目录、任务调度、SQLite与恢复对账 |
| Mosquitto | mTLS证书认证、客户端主题ACL、现场消息路由 |
| ugv-serial-bridge | MUX1 USB通道与本机Broker TCP连接之间的字节搬运 |
| ugv_root 固件 | 第1层组网、根AP服务公告、TCP/USB透明隧道、只读无线状态报告 |

普通 UGV、UAV 和 Micro 分别是独立 MQTT 客户端和执行节点；中继不终止其他节点的TLS。
根C6本身不作为MQTT客户端，不需要单独的客户端证书；主机用controller-001连接Broker。

## 业务调用

```text
临时车机终端 ↔ 本机 HTTP/WebSocket ↔ UGV Service
                                     ↕ 本地 MQTT/TLS
                                  Mosquitto
                                     ↕ TCP字节
                              USB桥接 ↔ 根C6
                                     ↕ 无线转发
                             普通UGV / UAV / Micro
```

现场MQTT会话的逻辑终点是根节点主机上的Broker。各层无线边是转发路径，不是逐层
重新发布任务。任务持久化与调度只在UGV Service中进行。HTTP操作只提交一次，事件按
SQLite游标补查。汽车关闭不终止任务，后台/节点重启先对账，不自动重放开始命令。

控制、状态、轻量任务反馈通过MQTT/TLS；业务数据通道协议和终点另行设计，当前不实现。
未来汽车与根节点各自连接真实云端，预计由公网/5G承载；当前不部署模拟云端。

## 代码边界

`service/server.py`装配后台，`api/`提供HTTP/WS，`nodes/`管理清单、准入与观测，
`tasks/`负责状态机和持久化，`agents/`提供主机执行能力，`transport/`适配节点和USB，
`protocol/`定义JSON与MUX1。`tools/`仅管理与启动，不承载业务调度。
独立车机通过HTTP合同访问后台，无运行时跨仓库导入。

## 身份与授权

清单只接受schema 2：node_id、role、root_id、enabled、ap_subnet，以及trust_status、admission_revision。
根节点为ugv-root，子节点root_id指向所属根节点。已登记、已授权、在线和业务就绪分别判断。
节点消息不能创建或批准自己的权限。后台准入管理校验证书签名、有效期、CN、用途及已记录
指纹；不签发密钥。撤销立即阻止后续任务派发，Broker ACL生成待加载文件，回执不宣称已踢掉连接。

`config/nodes.json`是权威清单；node_catalog保存登记与观测历史，admission_decisions保存
授权审计。观测不授予信任。现场数据、journal、数据库和凭据不得通过清空目录重建。
