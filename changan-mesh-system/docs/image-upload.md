# 图片帧上传对接（C6 → Jetson 落盘）

叶子节点（ESP32-C6 / `micro_uav`）经 mesh 树把图片帧上行到 root，Jetson 侧控制器按
分块重组并落盘。本文档定义两端对接契约，供视频截帧提供方与存储侧对接使用。

上传链路已从「一次性遍历静态资产表」改为**帧队列 + 事件触发**：生产者（未来视频截帧
任务）把一帧压入队列，传输端（`mqtt_serial`）自动取走、分块上传，发完即释放并取下一帧。

## 传输链路

树状上行无需任何中继代码：MQTT 是节点↔broker 的端到端连接；mesh 已开启 IP 转发
（`IP_FORWARD`），root C6 经 USB 隧道把 TCP 字节转发到 host 的 Mosquitto（:8883）。
多个叶子各自独立上传、互不干扰。

```
帧源(视频截帧/自测) → image_upload_enqueue() → 帧队列(image_upload, 4槽丢最旧)
  → mqtt_serial 分块(512B→base64) → mesh/v1/nodes/<id>/image
  → mesh IP 转发 → root C6 USB 隧道 → host ugv-serial-bridge → Mosquitto:8883
  → Controller → ImageSink → <image_dir>/<node_id>/<name>
```

## 接口契约

### Topic

```
mesh/v1/nodes/<node_id>/image
```

QoS 1，retain = false。`<node_id>` 即节点在 inventory 中的 ID（如 `micro-001`）。

### 消息体（每块一条）

一帧被切成 N 块，每块一条消息：

```json
{
  "v": 1,
  "type": "image",
  "node_id": "micro-001",
  "image_id": "fig-001.jpg",
  "name": "fig-001.jpg",
  "seq": 0,
  "count": 23,
  "total_bytes": 11417,
  "data": "<base64 of this 512-byte chunk>"
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `v` | int | 协议版本，固定 `1` |
| `type` | string | 固定 `"image"` |
| `node_id` | string | 发送节点 ID，须等于 topic 中的 node_id |
| `image_id` | string | 帧唯一标识，分块重组的主键之一 |
| `name` | string | 落盘文件名（可缺省，缺省取 `image_id`） |
| `seq` | int | 块序号，0 起，满足 `0 ≤ seq < count` |
| `count` | int | 本帧总块数（≥1） |
| `total_bytes` | int | 整帧字节数（信息性字段） |
| `data` | string | 本块二进制经标准 base64 编码后的文本 |

### 分块规则

- 每块原始二进制 **512 字节** → base64 ≈ 684 字符 → 整条 JSON ≈ 800 字节。
- 上限来源：broker `max_packet_size 2048`、节点 MQTT `buffer.out_size 1024`，留有余量。
- 最后一帧不足 512 字节按实际长度编码；单帧 ≤512 字节则 `count=1`。

### 重组规则（host 侧）

- 以 `(node_id, image_id)` 为主键缓冲各块，**乱序到达也正确**。
- 集齐 `count` 块后按 `seq` 拼接写盘。
- 丢弃条件：`retain` 消息、`seq`/`count` 非法、`data` 非合法 base64、`count > 100000`。
- 内存有界：未完成的半成品在 10 分钟无新块后丢弃；同时最多保留 64 个、合计 64MB
  的半成品，超限时按最后到达时间淘汰最旧者（`image_sink.py` 常量）。

## 生产者 API（固件侧）

帧源（未来视频截帧任务）只对接 `image_upload_enqueue()` 一个入口。
头文件 `firmware/components/image_upload/include/image_upload.h`：

```c
void   image_upload_init(void);
bool   image_upload_enqueue(const char *id, const uint8_t *data, size_t len);
void   image_upload_prime(void);      // 灌入嵌入式自测图片

image_frame_t *image_upload_pop(void);           // 消费端：非阻塞取帧
void   image_upload_release(image_frame_t *frame);
size_t image_upload_queued(void);

typedef struct {
    char id[33];       // 帧标识 = 重组主键 = 落盘文件名（须带扩展名）
    uint8_t *data;     // 帧字节（组件内拷贝）
    size_t   len;
} image_frame_t;
```

| 约束项 | 取值 / 规则 |
| --- | --- |
| `id` | ≤32 字符，仅 `A-Za-z0-9 . _ -`，建议带扩展名（如 `frame-0001.jpg`） |
| `len` | `0 < len ≤ IMAGE_FRAME_MAX`（32768） |
| 拷贝语义 | 数据被拷贝入队，调用后可释放入参 buffer |
| 队列长度 | 4 槽；队满时**丢最旧帧**（视频「最新帧优先」语义） |
| 线程安全 | 基于 FreeRTOS 队列，任意任务可调用 |

### 截帧任务调用示例

```c
// 拿到一帧 JPEG 后（任意任务上下文）：
uint8_t jpeg[FRAME_BUF]; size_t n = capture_frame(jpeg);
if (n > 0) image_upload_enqueue("frame-0001.jpg", jpeg, n);
```

**自测种子**：`image_upload_prime()` 在节点上线就绪后调用一次，把 `firmware/figs/`
内嵌的静态图片灌入队列——没有真实视频源时也能端到端验证上传与落盘。非叶子构建下无
内嵌图片，该调用为空操作。

## 消费与落盘（Jetson / host）

控制器订阅 `mesh/v1/nodes/+/image`，收到消息交给 `ImageSink` 重组落盘：

```
<image_dir>/<node_id>/<name>
例：runtime/ugv-root/received/micro-001/fig-001.jpg
```

`image_dir` 由配置指定；`node_id` 取自 topic，`name` 取自消息 `name`（缺省用 `image_id`）。

安全校验（图片按不可信字节处理）：

- 文件名只接受 `^[A-Za-z0-9._-]{1,64}$`，杜绝路径穿越（`../` 等被拒）。
- `node_id` 同样经安全名校验后才作为目录名。
- 坏 base64、非法 seq/count、retain 消息均静默丢弃。

### 清理与容量上限（磁盘）

落盘不是无限增长：每次写盘后扫描 `image_dir`，总大小超过 `MAX_TOTAL_BYTES`
（默认 **256 MiB**）时按 mtime 从旧到新删除，刚写入的文件始终保留。同名帧沿用同名
文件覆盖，不会重复累积。阈值是 `image_sink.py` 模块常量，`ImageSink(max_bytes=...)`
可在部署侧覆盖；如需按节点/按天保留，可在该目录上另加 cron 清理，互不冲突。

示例人工检查：

```bash
du -sh runtime/ugv-root/received
find runtime/ugv-root/received -type f | wc -l
```

## 配置与部署

### image_dir

| 配置 | image_dir 默认值 |
| --- | --- |
| `config/ugv-root.dev.toml` | `../runtime/ugv-root/received` |
| `config/ugv.example.toml` | `../runtime/ugv-root/received` |
| `config/ugv.jetson.example.toml` | `/var/lib/changan/received` |
| 当前 Jetson 部署（`/etc/changan/ugv-root.toml`） | `<repo>/runtime/ugv-root/received` |

### ACL 授权

每个节点已授权写 `mesh/v1/nodes/<id>/image`，控制器读 `mesh/v1/nodes/+/image`。部署前
需从 `config/nodes.json` 重新渲染 `runtime/ugv-root/acl.conf`。

### 部署步骤

1. 重新生成 ACL：`python tools/provision_mqtt.py`（或 `configure_broker.py`）。
2. 编译并烧录叶子固件（由使用者执行）：
   `python tools/lab.py --role micro_uav --node-id micro-001 build`。
3. 启动 broker 与 UGV Service，叶子入网上线后自动上传自测图片并落盘。

## 改动文件清单

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `firmware/components/image_upload/include/image_upload.h` | 新增 | 帧队列组件头（生产者/消费者 API） |
| `firmware/components/image_upload/image_upload.c` | 新增 | FreeRTOS 队列实现，4 槽丢最旧 |
| `firmware/components/image_upload/CMakeLists.txt` | 新增 | 嵌入 figs + 生成 image_assets.gen.h |
| `firmware/components/mqtt_serial/mqtt_serial.c` | 修改 | 消费端分块上传、base64、init/prime |
| `firmware/components/mqtt_serial/CMakeLists.txt` | 修改 | 依赖加入 image_upload |
| `firmware/figs/*.jpg` | 新增 | 3 张自测图片 |
| `host/src/changan_ugv/nodes/image_sink.py` | 新增 | 分块重组 + 落盘 + 安全校验 + 容量/内存上限 |
| `host/src/changan_ugv/nodes/controller.py` | 修改 | 订阅 image 主题并转发 |
| `host/src/changan_ugv/service/server.py` | 修改 | 注入 ImageSink(image_dir) |
| `host/src/changan_ugv/config.py` | 修改 | 新增 image_dir 路径 |
| `host/src/changan_ugv/nodes/inventory.py` | 修改 | ACL 增加 image 主题 |
| `host/tests/test_image_upload.py` | 新增 | 9 项单测（重组/安全/清理） |
| `config/*.toml` | 修改 | `[paths]` 增加 image_dir |
| `changan-runtime/acl.conf` | 重生成 | image 主题授权 |

## 约束与注意

- **已验证链路**：`ugv`（L2 叶子）固件已在 ESP-IDF 6.1 下编译、烧录并端到端验证：
  `image_upload_prime()` 发出 3 张内嵌图，Jetson 侧落盘字节与 `firmware/figs/` SHA256 一致。
  自测嵌图对 `ugv` 与 `micro_uav` 角色均启用。
- **内存预算**：队列满载 4 帧 × 32KB = 128KB 堆上限，仅当 4 个满尺寸帧同时排队才发生；
  当前 7–11KB 自测图无压力。视频帧更大更密时下调 `IMAGE_FRAME_MAX` 或队列长度。
- **吞吐**：当前每 50ms 循环发一个 512B 块 ≈ **10 KB/s**；11KB 图片约 1.1s。真实视频流
  需提速率（加大块、缩短间隔或改独立上传任务）。

## 后续

- 接入真实视频截帧：截帧任务调用 `image_upload_enqueue()` 即可。
- 统一帧 `id` 命名规范（含扩展名、时间戳/序号）。
- 按需提升上行速率以满足视频帧频。

本文档随代码同步维护；接口字段以 `image_upload.h` 与 `image_sink.py` 为准。
