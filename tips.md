# 车机终端本地部署：环境配置与启动指令

- **终端目录**：`/home/kkcjy/workstation/Chang-An/changan-car-terminal`
- **适用环境**：WSL2（WSLg，`DISPLAY=:0`），Python 3.11
- **范围**：仅车机终端。Mesh 网络与后台服务在另一台机器部署。

## 一、环境配置（首次执行一次）

### 1. 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# 安装到 /home/kkcjy/.local/bin/uv，确保该目录在 PATH 中
```

### 2. 创建终端专用虚拟环境

```bash
cd /home/kkcjy/workstation/Chang-An/changan-car-terminal
uv sync --locked
```

该命令生成 `changan-car-terminal/.venv`，不污染系统或 base Python。

### 3. 中文字体配置

否则界面中文显示为方块。

**a) 用户级字体别名**，写入 `~/.config/fontconfig/fonts.conf`：

```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <alias binding="same"><family>Microsoft YaHei UI</family><prefer><family>Noto Sans CJK SC</family></prefer></alias>
  <alias binding="same"><family>Microsoft YaHei</family><prefer><family>Noto Sans CJK SC</family></prefer></alias>
  <alias binding="same"><family>Consolas</family><prefer><family>Noto Sans Mono CJK SC</family></prefer></alias>
</fontconfig>
```

**b) 验证**：

```bash
fc-match "Microsoft YaHei UI"
# 期望输出 Noto Sans CJK SC
```

**c)** 终端代码使用 Windows 字体名，而 Python 自带的 Tk 未启用 Xft，
因此启动时需预加载系统 Tk 库（见下方 `LD_PRELOAD`）。

## 二、启动指令

Jetson 后台监听 `172.20.10.2:8080`，只允许笔记本来源 `172.20.10.4`。
笔记本和 Jetson 必须在同一局域网（热点）内。

### 图形界面

```bash
cd /home/kkcjy/workstation/Chang-An/changan-car-terminal
DISPLAY=:0 LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtk8.6.so /usr/lib/x86_64-linux-gnu/libtcl8.6.so" \
    uv run --locked python -m car_terminal.gui --base-url http://172.20.10.2:8080
```

说明：

- `LD_PRELOAD` 必填，缺失时中文为方块。
- 窗口打开后不会自动连接，需点击“连接”。
- 不要填 `127.0.0.1:8080`：那是本机自己的后台，没有 mesh 节点数据。
- Jetson 或笔记本的热点 IP 变化时，需要同步修改 Jetson 的
  `/etc/changan/ugv-root.toml` 中的 `http_host` 和 `http_allowed_peers`。

### 命令行方式（不需要图形界面）

```bash
cd /home/kkcjy/workstation/Chang-An/changan-car-terminal
uv run --locked python -m car_terminal --base-url http://172.20.10.2:8080 --command list
uv run --locked python -m car_terminal --base-url http://172.20.10.2:8080 --command "ping micro-001"
```

### 后台常驻启动（可选）

```bash
cd /home/kkcjy/workstation/Chang-An/changan-car-terminal
setsid nohup env DISPLAY=:0 \
    LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtk8.6.so /usr/lib/x86_64-linux-gnu/libtcl8.6.so" \
    uv run --locked python -m car_terminal.gui --base-url http://172.20.10.2:8080 \
    > /tmp/car_terminal.log 2>&1 < /dev/null &
```

### 停止

```bash
pgrep -af car_terminal.gui     # 查看进程
kill <pid>
```
