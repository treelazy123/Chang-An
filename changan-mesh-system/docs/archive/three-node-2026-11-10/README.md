# 长安三节点 Mesh-Lite：ESP-IDF 6.1

本工程从 `D:/changan/changan-mesh-lab` 重构到 `D:/esp/mesh_lite_node`，目标为 **ESP32-C6 / ESP-IDF 6.1.x**。三种设备身份共用一套代码，通过独立配置生成固件。

| 角色 | 节点 ID | 网络职责 |
| --- | --- | --- |
| `ugv_root` | `ugv-001` | 无人车，固定第 1 层 root |
| `uav` | `uav-001` | 正常无人机，非根，可接纳下游 |
| `micro_uav` | `micro-001` | 微型无人机，非根叶子 |

| 拓扑 | ugv_root | uav | micro_uav |
| --- | --- | --- | --- |
| `star` | 1 层 | 2 层 | 2 层 |
| `chain` | 1 层 | 2 层 | 3 层 |
| `auto` | 1 层 | 非根自动选父 | 非根叶子自动选父 |

三块板必须使用同一拓扑、Mesh ID、信道与密码。默认无外部路由器，Mesh ID 77、信道 6，实验密码 `changan-lab-only`。

## 构建

在本目录运行。已激活 ESP-IDF 6.1 时：

```powershell
python tools/lab.py --role ugv_root --topology star build
python tools/lab.py --role uav --topology star build
python tools/lab.py --role micro_uav --topology star build
```

本机普通 PowerShell 也可直接运行，无需修改执行策略：

```powershell
cd D:\esp\mesh_lite_node
& 'C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe' tools/lab.py --role ugv_root --topology chain build
```

`tools/idf_env.py` 从 EIM 的 `eim_idf.json` 和激活脚本中的静态配置读取工具链环境，不执行 PowerShell 脚本。默认安装记录位于 `C:/Espressif/tools`；其他位置可用 `IDF_TOOLS_PATH` 指定。已有激活环境优先，版本检查会拒绝 5.x 或其他 6.x。

每组配置隔离在 `build/<角色>-<拓扑>/`，例如：

```text
build/ugv_root-star/mesh_lite_node.bin
build/uav-chain/mesh_lite_node.elf
build/micro_uav-auto/sdkconfig
```

`--dry-run` 只输出参数；`menuconfig` 修改对应构建的独立配置。共用、角色、拓扑 defaults 按顺序加载，最后可选加载未跟踪的 `sdkconfig.local.defaults`。已有 sdkconfig 优先于 defaults；改默认值后应同步相应 menuconfig。脚本会拒绝与角色／拓扑不符的缓存配置。

## 烧录和串口

先确认实物标签并填写 `hardware/nodes.csv`。下面的 COM7 只是示例：

```powershell
python tools/lab.py --role ugv_root --topology star --port COM7 flash
python tools/lab.py --role ugv_root --topology star --port COM7 monitor
```

按 ugv → uav → micro 顺序上电。用三端 `STATUS` 的层级和父 BSSID 对照 `ADDR` 的 AP MAC 验证拓扑；`STACK` 记录 FreeRTOS 定时器任务栈的历史最小余量。保留 4096 字节定时器栈配置。固件遇到 NVS 错误会停止，不自动擦除持久化状态。

## 代码结构

```text
main/                           应用入口、角色与拓扑 Kconfig
components/node_role/           设备身份与层级约束
components/network_mesh_lite/
  mesh_start.c                  NVS、桥接、Wi-Fi、Mesh-Lite 启动
  mesh_status.c                 状态、地址、栈余量日志
components/mesh_lite/           1.0.2 核心及 IDF 6.1 ABI 适配
components/iot_bridge/          1.0.1 桥接及 API 适配
components/cjson/               固定 cJSON 1.7.19 源码及 MIT 许可证
cmake/mesh_lite_idf61.cmake      只替换构建内的 NAPT 翻译单元
tools/prepare_napt.py           生成 NAPT 兼容源码与 SHA-256 记录
tools/lab.py                    构建／烧录／串口入口
profiles/、topologies/          角色与拓扑默认值
```

第三方组件随工程保存，Component Manager 关闭，构建不自动下载依赖。保留未启用的 modem、二维码源码作为来源副本，不加入当前应用依赖图。Wi-Fi 配网、以太网、4G、OTA 不在此迁移的验证范围；旧版 Mesh-Lite 配网选项若启用会给出明确配置错误。

## 迁移与验证

详见 [6.1 迁移记录](docs/migration-idf61.md)、[本地组件](components/README.md) 和 [上板步骤](docs/bringup.md)。编译验证结果记录在 `build/verification.json`。编译通过不代表三板组网、断线恢复或长时间运行已经通过；本次不自动烧录设备。

当前保留无路由器三节点实验功能。业务 Socket、MQTT 控制面、照片传输、实时视频和 UWB 仍待实现；[控制面设计](docs/control-plane-design.md) 是后续设计。

应用分区使用工程内 `partitions.csv`：保持 NVS 和 PHY 原偏移，factory 从 `0x10000` 开始、大小 `0x1f0000`，总布局适合现有 2 MiB Flash 配置。6.1 镜像超过旧 1 MiB 槽位，因此不复用旧分区表。
