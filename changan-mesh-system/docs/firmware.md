# 固件与设备身份

## 工程与角色

只有 `firmware/` 一个 ESP-IDF 6.1.x / ESP32-C6 工程。`pc_root`、`ugv`、`uav`、`micro_uav` 通过配置选择角色，应用代码位于 `firmware/apps/`，共享代码位于 `firmware/components/`。角色名 `pc_root` 对应源码目录 `apps/root/`。

当前业务使用 `--transport mqtt_serial`。`lab.py` 的默认值仍是 `legacy`，因此以下命令显式指定 MQTT 模式。legacy TCP 实现仅供兼容，不能混用它的 9000/9001 连接教程与当前 8883 MQTT 链路。

chain 配置预期 root=1、UGV=2、UAV=3、Micro=4。当前 `mqtt_serial` 仅支持已确认的 chain；star/auto 属于 legacy 配置，不能直接用于以下 MQTT 命令。所有板应使用相同 Mesh ID、信道、密码与拓扑。实际父子关系以 BSSID/AP MAC 和状态上报为准；level=0 或没有有效 IP 时不能认定入网完成。

## 现有身份与新设备

公开清单为 `config/nodes.json`。node_id 是固定资产身份，1–32 个 ASCII 字母、数字、横线或下划线；拒绝保留身份、路径、Windows 设备名和仅大小写不同的重复编号。MAC、IP、COM、boot_id 不替代 node_id。

```powershell
cd D:\changan\changan-mesh-system
uv sync --locked
uv run --locked python tools/provision_mqtt.py --list
```

只在增加新设备时增量登记，例如：

```powershell
uv run --locked python tools/provision_mqtt.py --role uav --node-id uav-017 --ugv-id ugv-001
```

证书与私钥保存在 `secrets/<node_id>/`，与该编号、角色及指纹绑定。重复登记复用原有身份，不重建 CA，不覆盖其他设备密钥。UGV 也保留自己的证书，但当前 UGV C6 是透明 USB 网关，不用自身身份登录 MQTT；USB 网络诊断报告不增加认证授权。

发证或修改清单后，需要由管理员部署生成的 ACL 才能接入；具体步骤见 [部署与交接](deployment.md)。清单数量不写死，实时容量仍受硬件限制。USB 隧道默认最多 8 通道，范围 1–8；超过现有上限需修改协议与资源配置并重新验收。

## 启动 ESP-IDF 环境

在准备编译或烧录的 PowerShell 窗口执行本机安装器提供的脚本，然后进入主仓库：

```powershell
& 'C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1'
cd D:\changan\changan-mesh-system
$env:PYTHONUTF8 = '1'
python --version
python "$env:IDF_PATH\tools\idf.py" --version
```

本机已验证输出 `ESP-IDF v6.1`；`IDF_PATH` 为 `D:\esp\v6.1\esp-idf`，Python 为 `C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe`。其他机器替换为自己的安装路径。

环境只对执行脚本的 PowerShell 进程及其子进程生效；新窗口需要重新加载。下面的固件命令使用此环境中的 `python`，主机程序继续按运行说明使用 `uv run --locked`。

如果提示“禁止运行脚本”，仅为当前窗口临时放行后重新加载：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& 'C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1'
```

关闭窗口后该执行策略设置失效，不修改 CurrentUser 或 LocalMachine 策略。若出现 Unicode 环境提示，在同一窗口设置 `$env:PYTHONUTF8 = '1'` 再运行命令即可。

## 配置预览

以下命令不构建、不连接设备，也不签发身份：

```powershell
uv run --locked python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-002 --dry-run
```

MQTT 固件按设备隔离在 `build/mqtt_serial/nodes/<node_id>/<role>-<topology>/`。不要跨编号复用 bin、sdkconfig 或 Ninja/CMake 缓存；已有配置优先于 defaults，更新 defaults 后应检查实际生效配置。

## 用户编译与烧录

新增巡检/复核测试需要分别更新UAV与每台Micro固件；按角色公告服务，任务参数和结果均标注esp32_test。task_agent将旧m1_task/journal记录迁移至journal_v2，保留旧键及设备身份。用户构建和上板检查步骤见 [流程验证说明](esp32-workflows.md)。

先按上节加载 IDF 环境，确保当前目录是主仓库根目录。刷写前退出占用目标板原生 USB 的桥接、车机 GUI/CLI 或串口监视器。用以下命令枚举端口（不打开设备）：

```powershell
python -m serial.tools.list_ports -v
```

核对实物与 node_id，不能只凭历史端口号选板。只编译、不烧录的示例：

```powershell
python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --topology chain build
```

以下是五块现有设备的烧录方法，按实际需要逐条执行。此前端口为 root=COM7、UGV=COM4、UAV=COM5；若重新枚举后发生变化，先修改命令。

root / 车机 C6：

```powershell
python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --topology chain --port COM7 flash
```

UGV C6：

```powershell
python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --topology chain --port COM4 flash
```

UAV C6：

```powershell
python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --topology chain --port COM5 flash
```

Micro-001 / Micro-002 的端口需分别确认；以下命令会先询问端口，再烧录对应设备，不自动猜测：

```powershell
$micro001Port = Read-Host '输入 micro-001 的实际串口，例如 COM6'
python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-001 --topology chain --port $micro001Port flash
```

```powershell
$micro002Port = Read-Host '输入 micro-002 的实际串口，例如 COM8'
python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-002 --topology chain --port $micro002Port flash
```

`flash` 会按 IDF 需要先编译，然后写入所选板。每块板使用自己的编号、证书和独立构建目录，不把其他板的 bin 当作本板固件，不擦除已登记身份和 NVS。`lab.py` 会在缺少必要 bootloader 配置元数据时先重新配置；不要手工拼造生成文件。

只核对某条烧录命令、暂不执行时，加入 `--dry-run`，例如：

```powershell
python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --topology chain --port COM4 --dry-run flash
```

确认烧录成功后，按 [运行说明](operations.md) 恢复对应桥接、后台与车机连接。

`tools/idf_env.py` 本身读取安装器的静态配置来准备子进程环境，不执行 PowerShell 激活脚本。身份检查缺少 cryptography 时调用主仓库 `.venv` 的身份工作进程，无需向 IDF Python 补装主机依赖。

容量检查使用已有产物：

```powershell
uv run --locked python tools/check_firmware_size.py --node-id ugv-001
```

新增完整网络显示需要更新 root/UAV/Micro 的状态上报固件，以及 UGV 的协商式 USB 网络报告固件；主机代码更新本身不会改变已经烧录的程序。

## SDK 与资源约束

- 本地第三方组件、版本和许可证位于 `third_party/`，组件管理器保持关闭；不自动替换预编译 Mesh-Lite 核心。
- 本地 Mesh-Lite 1.0.2 的旧 netif 兼容层在 TCP/IP 上下文调用新接口；STA/AP 在启动时创建且运行期不删除。成功链接不能证明全部私有 ABI 运行路径正确。
- NAPT 扩展由兼容脚本核对 SDK 输入后生成到构建目录，不修改 SDK 源文件。更换 SDK 或核心库后需重新核对接口、地址字节序与补丁输入。
- `firmware/partitions.csv` 保留 NVS/PHY 偏移，factory 从 `0x10000` 开始、大小 `0x1f0000`，对应现有 2 MiB 布局。实际镜像和板载容量由用户编译验收。
- 保留 FreeRTOS timer 4096 字节栈及水位日志；NVS 初始化失败不自动擦除。
- root 和 UGV 原生 USB 专用于二进制链路，主控制台为 UART0，USB 副控制台关闭。Wi-Fi AP 关联表只表示驱动记录，不等同于 MQTT 在线或诊断任务存活。

当前构建和真实硬件边界见 [验收状态](status.md)。
