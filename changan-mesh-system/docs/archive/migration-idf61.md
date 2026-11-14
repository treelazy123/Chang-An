# ESP-IDF 6.1 重构记录

日期：2026-11-10。源目录 `D:/changan/changan-mesh-lab`，目标目录 `D:/esp/mesh_lite_node`。保留原项目，排除其构建缓存和旧 sdkconfig，从 defaults 重新配置。

## 构建与依赖

- SDK：本机 `D:/esp/v6.1/esp-idf`，`idf.py --version` 为 `ESP-IDF v6.1`。
- 编译器：`riscv32-esp-elf` GCC 15.2.0，安装器的 6.1 Python 环境。
- 工程名／镜像名：`mesh_lite_node`，应用版本 `0.2.0`。
- 根 CMake 和 Python 入口均限制为 6.1.x、ESP32-C6；不复用旧项目缓存。
- 角色、拓扑、节点 ID、Mesh ID、信道、密码和定时器栈约定保留。
- 只构建应用依赖图。关闭当前未使用的 Ethernet，避免引入已迁移出 SDK 的旧驱动。
- 本地 cJSON 1.7.19 替代 SDK 旧 json；不再无条件依赖 wifi_provisioning。旧配网功能不在当前无路由器实验内，显式启用会报错。

## SDK 兼容层

1. Mesh-Lite 1.0.2 的预编译 C6 核心保留不变。其旧 `esp_netif_next` 引用由本地适配函数转入 TCP/IP 上下文，然后调用新 `esp_netif_next_unsafe`。接口在启动前创建且运行期不删除。该约束不能用于任意动态网络接口应用。
2. IoT-Bridge 切换到新 Wi-Fi 接口常量和明确组件依赖。SoftAP SSID 读取补上边界，Mesh-Lite 读取实际应用的 AP 配置，避免广播元数据和真实 SSID 不一致。
3. 将组网启动与状态采集拆为 `mesh_start.c` 和 `mesh_status.c`，保留日志字段。
4. SDK 自身的 `ip4.c` 已包含 NAPT 转发保护。`prepare_napt.py` 核对后，把原上游补丁中的表清理和表满回调加入构建副本 `build/<角色>-<拓扑>/compat/ip4_napt.c`，由 lwip 目标编译该副本。
5. SDK 源文件不会被修改，不执行 git apply。兼容脚本记录输入 SDK、补丁和输出文件摘要，并将这些输入加入 CMake 重新配置依赖。NAPT 表清理通过 TCP/IP 上下文执行。

## 验证与边界

完整构建和九种角色／拓扑配置的结果见 `build/verification.json`，每组构建日志位于 `build/validation/`。`tests/test_migration.py` 检查补丁拒绝不匹配源码、生成内容幂等、原 SDK 文件未改和配置隔离等迁移约束。

保留 4096 字节 FreeRTOS 定时器任务栈。原 5.5.5 上板故障和实验日志只作为历史参考，不能作为 6.1 运行证据。新固件尚未自动烧录，仍需按 bringup 文档验证 star、chain、auto 实际拓扑、断线重连和栈余量。

预编译核心的内部实现不公开；成功链接不能证明所有运行时 ABI 路径均兼容。后续硬件验证若暴露结构体或私有 API 差异，需使用上游面向 IDF 6.1 构建的核心库继续排查。

## 官方依据

- [6.0 网络接口迁移](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32c6/migration-guides/release-6.x/6.0/networking.html)
- [JSON 组件迁移](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32c6/migration-guides/release-6.x/6.0/protocols.html)
- [配网组件迁移](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32c6/migration-guides/release-6.x/6.0/provisioning.html)
- [cJSON v1.7.19 源码](https://github.com/DaveGamble/cJSON/tree/v1.7.19)

应用分区使用工程内 `partitions.csv`：保持 NVS 和 PHY 原偏移，factory 从 `0x10000` 开始、大小 `0x1f0000`，总布局适合现有 2 MiB Flash 配置。6.1 镜像超过旧 1 MiB 槽位，因此不复用旧分区表。

????????????????????????????? `build/verification.json` ?????????????????????? 7 ???????????


## 2026-11-11 四节点更新（应用版本 0.3.0）

新增独立 pc_root，UGV 变为非根中继；chain 层级为 root1/UGV2/UAV3/Micro4。TCP 应用连接按最新要求为 UAV/Micro→UGV→root C6，PC 经原生 USB Serial/JTAG 连接 root。新增 app_protocol、service_discovery、transport_tcp、serial_gateway 及 PC 终端。

新构建路径 `build/four-node/` 与旧产物隔离。旧文档保存于 docs/archive/three-node-2026-11-10/。本轮运行 18 项纯主机测试通过；按用户要求未运行固件构建或硬件测试。上文旧版本编译记录仅属于旧源码，不作为当前版本通过证据。


## DHCP 分配事件弃用警告修复

已将 Mesh-Lite 与 IoT-Bridge 以太网适配中的 `IP_EVENT_AP_STAIPASSIGNED` 更新为 IDF 6.1 的 `IP_EVENT_ASSIGNED_IP_TO_CLIENT`，相关事件参数类型改为 `ip_event_assigned_ip_to_client_t`，注册与注销保持一致。本地 IDF 头文件将旧事件直接定义为新事件的兼容别名，旧参数类型也是新类型的 typedef；因此该修改保留原事件行为。Mesh-Lite 回调只触发信息上报，不解析事件参数。未修改 SDK，未运行 build。
