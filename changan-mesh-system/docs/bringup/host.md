# 当前启动与迁移交接

## Python 环境与检查

```powershell
cd D:changanchangan-mesh-system
uv sync --locked
uv run --locked python tools/run_tests.py
uv run --locked python tools/provision_mqtt.py --list
```

已保留原设备证书，迁移后不需要重新签发或重新烧录来连接新主机程序。`provision_mqtt.py` 不带参数是首次建 CA，不用于已迁移的 secrets。

## 切换主机服务

迁移期间旧服务继续运行，新目录没有启动生产服务。切换时先退出旧目录的 UGV 后台/独立 mqtt_terminal、COM4 桥接和 Broker，避免端口及身份冲突。复制过来的数据库是迁移时的一致快照；如果旧服务之后继续处理了任务，应在退出旧服务后再次同步状态：

```powershell
uv run --locked python tools/sync_runtime.py --source D:espmesh_lite_node
```

该工具要求旧后台已退出（检查 controller-001 的 OS 锁），以 SQLite backup 复制数据库，保留原密钥，并重写新目录 Broker 路径。它不会停止任何进程。

然后在三个独立 PowerShell 窗口、均以新仓库为当前目录运行：

```powershell
& 'D:Program Files (x86)Mosquittomosquitto.exe' -c D:changanchangan-mesh-system
untimemosquitto.conf -v
```

```powershell
uv run --locked python tools/serial_tcp_bridge.py --port COM4 --broker-port 8883
```

```powershell
uv run --locked python tools/ugv_service.py --broker-port 8883 --ugv-id ugv-001
```

新包也提供 `uv run --locked ugv-service`、`ugv-serial-bridge`、`ugv-console` 入口；原 tools 命令保留。

车机仓库和入口保持：

```powershell
cd D:changanchangan-car-terminal
uv run --locked python -m car_terminal --port COM7
```

UGV 本地维护仍可运行 `uv run --locked python tools/mqtt_terminal.py --broker-port 8883`，它优先使用后台，避免另开 controller-001。

## 固件配置预览（不编译、不连接设备）

```powershell
uv run --locked python tools/lab.py --transport mqtt_serial --role pc_root --node-id pc-root-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role ugv --node-id ugv-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role uav --node-id uav-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-001 --dry-run
uv run --locked python tools/lab.py --transport mqtt_serial --role micro_uav --node-id micro-002 --dry-run
```

旧 build/CMake cache 和虚拟环境没有迁移。后续由用户在新目录重新编译；原 COM7/COM4/COM5 分别对应 root/UGV/UAV，Micro 端口按实际指定。不要直接复用旧目录的 Ninja 缓存。

VS Code 的 ESP-IDF 工程目录是 `firmware/`；可单独打开该目录。仓库根目录负责 uv 与管理工具，不直接运行裸 `idf.py`。默认 IDE 配置仅定位 root 缓存，实际每块板仍以带 `--node-id` 的 lab 命令为准。
