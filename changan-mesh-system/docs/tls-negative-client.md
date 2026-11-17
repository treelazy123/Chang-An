# UAV 不可信客户端证书抓包测试

原身份目录 secrets/uav-001 包含登记证书、私钥及 identity.json 指纹，不直接覆盖。新工具仅在 runtime/tls-negative/uav-001 生成另一套 CA 签发的匹配 client.pem/client.key；ca.pem 复制原受信 CA，保持 UAV 验证 Broker 的能力。没有修改 Broker CA、ACL、节点登记或正常证书。测试 CA 私钥不保存。

测试文件已生成。也可幂等重新检查：

```powershell
cd D:\changan\changan-mesh-system
uv run --locked python tools/tls_negative_identity.py --node-id uav-001
```

测试证书保留 CN=uav-001、clientAuth 用途和原证书有效期，以隔离“不可信签发者”这个失败因素。其私钥与证书匹配，因此不会因键值不匹配在客户端本地提前失败。Broker 不信任这套测试 CA；不要把 untrusted-ca.pem 导入 Broker。

## 用户运行：烧录失败测试固件

先启动 Wireshark，选择回环接口，捕获过滤器 tcp port 8883。保持 UGV USB 转发和实际 Broker 的 require_certificate true。UAV 串口按当前实际设备填写，以下沿用已知 COM5。

```powershell
uv run --locked python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --topology chain --tls-test-untrusted-client --port COM5 flash
```

lab.py 仍校验并复用正常登记身份，只在 CMake 嵌入阶段切换测试凭据。测试目录为 build/mqtt_serial/tls-negative/uav-001/uav-chain；正常目录为 build/mqtt_serial/nodes/uav-001/uav-chain。无需删除 sdkconfig、修改 identity.json 或手工改 PEM。非 UAV 角色不能使用此选项。

烧录及构建仅由用户执行；实现期间没有运行 reconfigure/build/flash 或连接串口。

## 预期结果与抓包

新的临时源端口和 TCP stream 会变化，不能继续沿用旧的64338/194。按 Broker 日志和新的握手定位连接。

预期客户端收到服务端证书及 Certificate Request；随后无法完成客户端认证，Broker 出现证书/认证错误，连接关闭或 TLS 告警，没有成功 MQTT 登录及 ready。具体客户端证书是否发送、告警名称取决于证书选择和 TLS 实现，不将某个固定告警文本作为唯一条件。对照证据包括 Broker 日志、证书Issuer、公钥/签名及成功/失败流量。

TLS失败不等于Mesh Wi-Fi断开。UAV仍可能维持第3层网络中继。只看到TCP三次握手不算认证成功，客户端自动重试产生多个失败连接属预期。

## 恢复正常身份

不带测试选项重新烧录同一块 UAV：

```powershell
uv run --locked python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --topology chain --port COM5 flash
```

正常路径始终使用原 secrets/uav-001/client.pem 和 client.key。恢复后确认 ready 与 ping/status。运行目录中的测试凭据可以保留供复测，不能用于部署或更新正式登记。
