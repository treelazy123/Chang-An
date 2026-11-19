# 通用启动方案

两端各一套后台：Jetson 根节点后台（Mosquitto + UGV Service + USB 桥接），笔记本车机终端。
根 C6 通过 USB 接入 Jetson，叶子 C6 经 Mesh 上行；叶子图片最终写入 Jetson 仓库下的
`runtime/ugv-root/received/<节点ID>/`。

## 组件与部署位置

| 组件 | 位置 | 作用 |
| --- | --- | --- |
| Mosquitto | Jetson | 消息中转 |
| UGV Service | Jetson | 节点管理、任务调度、图片落盘 |
| USB 桥接 | Jetson | 根 C6 与 Jetson 之间的串口隧道 |
| 车机终端 | 笔记本 | 查看节点、下发任务 |
| 根 C6（`ugv-root`） | 车上 | Mesh 网关 |
| 叶子 C6（如 `ugv-001`） | 车上 | 第 2 层执行节点与图片上传 |

部署文件：

| 内容 | 路径 |
| --- | --- |
| 根节点配置 | `/etc/changan/ugv-root.toml` |
| 凭据 | 仓库 `secrets/`（禁止重新生成或覆盖） |
| 运行数据 | 仓库 `runtime/ugv-root/` |
| 开机服务 | `mosquitto.service`、`changan-ugv.service`、`changan-bridge.service` |

## 一、Jetson 后台

### 配置

编辑 `/etc/changan/ugv-root.toml`，确认：

```toml
http_host = "<JETSON_IP>"
http_allowed_peers = ["<LAPTOP_IP>", "127.0.0.1", "::1"]
image_dir = "<REPO>/runtime/ugv-root/received"
```

`<REPO>` 为 Jetson 上仓库的绝对路径。热点或路由器重新分配地址后，同步修改
`http_host`、`http_allowed_peers` 和车机终端的 `--base-url`。

### 启动

顺序固定：Broker → 后台 → 桥接。

```bash
sudo systemctl start mosquitto
sudo systemctl start changan-ugv
sudo systemctl start changan-bridge
```

重启：

```bash
sudo systemctl restart mosquitto
sudo systemctl restart changan-ugv
sudo systemctl restart changan-bridge
```

状态与日志：

```bash
sudo systemctl status mosquitto changan-ugv changan-bridge --no-pager
journalctl -u changan-ugv -f
journalctl -u changan-bridge -f
```

### 前台运行（未安装服务时）

```bash
cd <REPO>
uv sync --locked
uv run --locked ugv-service --config /etc/changan/ugv-root.toml
uv run --locked ugv-serial-bridge --port <ROOT_PORT> --ugv-id ugv-root
```

## 二、笔记本车机终端

```bash
cd <CAR_TERMINAL>
uv sync --locked
DISPLAY=:0 LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtk8.6.so /usr/lib/x86_64-linux-gnu/libtcl8.6.so" \
    uv run --locked python -m car_terminal.gui --base-url http://<JETSON_IP>:8080
```

- WSL 必须带 `DISPLAY` 和 `LD_PRELOAD`，否则中文显示为方块；原生 Linux 可省略。
- 窗口打开后点击“连接”。
- 不要填 `127.0.0.1`，那是笔记本本机，不是 Jetson 后台。

命令行方式：

```bash
uv run --locked python -m car_terminal --base-url http://<JETSON_IP>:8080 --command list
uv run --locked python -m car_terminal --base-url http://<JETSON_IP>:8080 --command "ping ugv-001"
```

后台常驻（已安装用户单元时）：

```bash
systemctl --user start car-terminal.service
systemctl --user status car-terminal.service
systemctl --user restart car-terminal.service
```

## 三、固件编译与烧录

根 C6 与叶子 C6 角色不同，必须分别构建、分别烧录。已有证书和 NVS 保持原样。

### 准备

激活 ESP-IDF 6.1，并在仓库根目录同步依赖：

```bash
source <ESP_IDF>/export.sh        # 或本机 ESP-IDF 激活脚本
cd <REPO>
uv sync --locked
```

### 构建

```bash
.venv/bin/python tools/lab.py --role ugv_root --node-id ugv-root --dry-run
.venv/bin/python tools/lab.py --role ugv --node-id ugv-001 --dry-run

.venv/bin/python tools/lab.py --role ugv_root --node-id ugv-root build
.venv/bin/python tools/lab.py --role ugv --node-id ugv-001 build
```

每个节点使用独立构建目录；角色、节点 ID 或架构版本不匹配时工具会拒绝复用缓存。

### 烧录

烧录根板前先停止桥接，释放串口：

```bash
sudo systemctl stop changan-bridge
.venv/bin/python tools/lab.py --role ugv_root --node-id ugv-root --port <ROOT_PORT> flash
sudo systemctl start changan-bridge
```

烧录叶子：

```bash
.venv/bin/python tools/lab.py --role ugv --node-id ugv-001 --port <LEAF_PORT> flash
```

- Linux 端口形如 `/dev/ttyACM0`，Windows 形如 `COM5`，以实物为准。
- 可用 `ls /dev/serial/by-id/` 或插拔设备确认端口。
- 从旧架构升级时，首次构建该节点加一次 `--reset-config`；不要擦除 NVS，不要重新签发证书。

## 四、完整启动顺序

1. 烧录根 C6，USB 接入 Jetson。
2. 启动 Jetson 三个服务。
3. 烧录或上电叶子 C6。
4. 确认叶子上线（第 2 层，`online`、`ready`）。
5. 打开车机终端，填写 `http://<JETSON_IP>:8080` 并点击“连接”。

## 五、验证

```bash
curl -s http://<JETSON_IP>:8080/api/v1/health
cd <REPO>
uv run --locked ugv-console --command list
ls -lt runtime/ugv-root/received/ugv-001/
```

预期：

- 健康接口返回 `broker_connected: true`。
- `ugv-001` 显示第 2 层、`online=True`、`ready=True`。
- 叶子有图片帧时，`received/ugv-001/` 下文件持续更新；目录总大小超过 256 MiB 时自动删除最旧文件。

## 六、停止

按启动的逆序：

```bash
systemctl --user stop car-terminal.service
sudo systemctl stop changan-bridge
sudo systemctl stop changan-ugv
sudo systemctl stop mosquitto
```
