> 0.2.0：增加通用任务 API 与 task/watch CLI，保留 list/ping/status/echo。任务管理需要 UGV 0.7.0 及更新后的 root 固件和 Broker ACL。详见 [M1 升级与接口](D:/esp/mesh_lite_node/docs/m1-task-management.md)。

# 长安汽车车机终端

独立仓库，只包含车机侧 list / ping / status / echo 交互与请求传输。不依赖 ESP-IDF，不导入 mesh_lite_node 的 Python 文件，不管理CA/设备登记，不发布校时时钟。无人车后台位于固件工程的 tools/ugv_service.py。

## 当前 C6 串口使用

```powershell
cd D:\changan\changan-car-terminal
uv sync --locked
uv run --locked python -m car_terminal --port COM7
```

COM7 是 root/汽车 C6；UGV COM4 的 serial_tcp_bridge 是另一条独立USB链路，不要把车机CLI连到COM4。

```text
car> list
car> ping micro-002
car> status uav-001
car> echo micro-001 hello
car> quit
```

单次命令：`uv run --locked python -m car_terminal --port COM7 --command "status uav-001"`。

链路：车机CLI → root C6原生USB应用帧 → root MQTT/TLS → UGV C6转发 → COM4隧道 → Broker → UGV后台 → 目标节点；结果沿反向路径返回。root使用自身证书身份绑定请求，CLI不能通过消息字段冒用其他车机。车机电脑无需存放CA私钥或controller-001管理员证书。

先在固件工程按 docs/car-terminal-separation.md 更新ACL、用户重刷root并启动UGV后台。当前已运行的旧root固件不会自动获得MQTT模式的车机USB接口。此仓库没有运行过真实COM7验收；主机测试使用假串口。

## S31 网卡阶段的传输适配

```powershell
uv run --locked python -m car_terminal --transport mqtt --host UGV可达地址 --node-id pc-root-001 --cert-dir 设备证书目录
```

证书目录只包含车机自身client.pem/client.key/ca.pem；CA私钥和UGV管理员证书留在管理端。MQTT适配验证固定Broker服务名 ugv-broker.lab，可用 --server-name 指定管理员配置的服务身份，不关闭证书验证。S31作为纯IP网卡时，MQTT客户端转移到车机主机；不要同时让C6客户端与主机使用同一证书身份登录，否则会互相替换。S31 USB网卡、IP路由及车机节点代理状态仍需正式硬件联调，本轮只提供传输适配。

## 协议与错误处理

请求：v=1，type=list或command，msg_id唯一，deadline_unix为UTC截止时间；command携带target/op/payload。允许ping/status/echo。串口MLT1头+大端长度/CRC16-CCITT-FALSE+UTF8 JSON，帧内JSON最多1024字节，请求最多512字节。列表逐节点分页，more=false结束；命令只接受目标匹配的ACK。超时不自动重发。

关闭本CLI不会关闭UGV后台、Broker或校时。设备登记、权限、在线状态和命令审核由UGV后台执行；本CLI只显示结果，不将消息中的未知身份自行授权。

```powershell
uv run --locked python -m unittest discover -s tests -v
```

尚未执行固件build/烧录或连接真实串口；本地Git仓库已初始化，无自动提交或推送。
