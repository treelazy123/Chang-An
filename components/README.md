# 本地依赖与 IDF 6.1 适配

Component Manager 关闭，CMake 通过 `REQUIRES` 解析工程内和 SDK 组件。版本、来源和摘要见 [vendor-lock.json](vendor-lock.json)。

| 目录 | 版本 | 用途 |
| --- | --- | --- |
| mesh_lite | 1.0.2 | Mesh-Lite 公开源码和预编译核心 |
| iot_bridge | 1.0.1 | Wi-Fi STA/AP 桥接 |
| cmake_utilities | 0.5.3 | 组件版本宏 |
| cjson | 1.7.19 | 从固定 upstream tag 保存的 JSON 实现 |
| esp_modem | 1.4.3 | 原项目来源副本，当前不构建 |
| qrcode | 0.1.0~2 | 原项目来源副本，当前不构建 |

Mesh-Lite 的 CMake 依赖从旧 `json` 改为本地 `cjson`，移除默认未使用的旧配网依赖。`src/esp_mesh_lite_idf61.c` 为预编译核心保留 `esp_netif_next` 符号，每次遍历在 TCP/IP 上下文执行。当前 STA/AP 在启动阶段创建，整个运行期不销毁；未来若引入动态接口生命周期，应同步更新核心及遍历设计。

IoT-Bridge 使用 `WIFI_IF_STA/AP`，显式声明新驱动组件，modem 仅在选择相应功能时成为依赖。修正 SoftAP SSID 的 33 字节越界读取，并在发布 Mesh-Lite SoftAP 元数据时使用实际应用的 Wi-Fi SSID。NAPT 清理在 TCP/IP 上下文执行。

`cmake/mesh_lite_idf61.cmake` 在构建目录生成 `compat/ip4_napt.c`，加入原 `patch/ip4_napt.patch` 中的表清理和表满回调。SDK 源文件保持不变；来源与生成文件 SHA-256 写入相邻 JSON。遇到不匹配源码或半套补丁会停止配置。保留上游许可与原始补丁。

当前仅验证 ESP-IDF 6.1.x / ESP32-C6 / Wi-Fi 无路由器路径，不宣称这些上游版本已全面兼容其他 6.x 芯片或功能。详细说明见 [迁移记录](../docs/migration-idf61.md)。
