# 架构与版本管理

## 身份和拓扑分开

`node_id` 是稳定业务身份，不等于当前 IP、串口号或网络层级。当前以三份角色 defaults 生成固件；更多同类设备接入后，身份可转入单独的出厂／NVS配置，设备角色继续独立管理。

| 实验 | ugv_root | uav | micro_uav |
| --- | --- | --- | --- |
| star | 固定1层 | 固定2层，可带子节点 | 固定2层，叶子 |
| chain | 固定1层 | 固定2层，中继候选 | 固定3层，叶子 |
| auto | 固定1层 | 非根，自动选父 | 非根叶子，自动选父 |

同一实验三板统一使用一种拓扑配置。在受控chain实验且只有这三块板时，目标路径为 micro → uav → ugv；以微型无人机父BSSID等于正常无人机AP MAC为直接证据。若环境有其他同Mesh ID节点，仅凭第3层不能证明指定中继。

链式配置会牺牲一部分自愈弹性：uav失效后，micro必须找到可用第2层父节点，否则保持未入网。auto配置允许重新选择父节点，但只有两块非根板时，中继掉电后的替代路径也受实际覆盖限制。root固定，不自动把无人机改成root。

## 按层扩展组件

当前已实现 `node_role` 与 `network_mesh_lite`，组网适配与业务入口分离。后续按实际里程碑增加组件：

| 后续组件 | 负责内容 | 与当前中继的关系 |
| --- | --- | --- |
| control_client | 各节点主动连接电脑的 MQTT 5.0 over TCP 服务，管理长连接、收发队列与重连 | IP 中继负责转发 |
| service_agent / task_agent | 注册、公告、能力/状态更新、task_id与业务确认 | 不能只用NAPT后的源IP识别业务节点 |
| media_source | 先生成已知测试字节，再接图像来源 | 不预设C6已经能采集／编码目标视频 |
| uwb_adapter | 测距与自定义状态接口 | 尚未确定模块和引脚，不虚构驱动 |
| link_policy | Wi-Fi/UWB信息融合、预警与恢复决策 | 需核对Mesh-Lite公开接口的控制边界 |

三块板只有通信模组角色，不等于已经接入飞控或车载主机。普通中继不能直接靠一个本地TCP接收窗口控制过路TCP流；后续如果研究逐跳代理或转发队列，应建立单独实验配置，避免混淆端到端连接模型。

电脑开热点，UGV 接入电脑，链路为电脑 → UGV → UAV → micro。首阶段各节点主动建立到电脑的明文 MQTT 5.0 over TCP 长连接，电脑维护账号授权、注册中心及任务管理。现有固件已提供组网能力，车机业务按提案实施。[车机终端与机群通信设计](control-plane-design.md)

## 固定依赖与Git管理

自有代码、六个本地第三方组件、profiles、topologies、文档和结果摘要进入Git。第三方来源版本与迁移前摘要保存在 `components/vendor-lock.json`，本地修改见 `components/README.md`。组件管理器已关闭，CMake 直接解析 `components` 和 SDK 组件；Project Components 显示解析后的索引。SDK与工具链安装在仓库外，记录 `idf.py --version`、SDK commit及已有补丁；构建输出与本地参数不提交。

一个main分支维护共享代码；功能分支可用 `feat/tcp-heartbeat`、`feat/image-transfer`、`feat/uwb-status`，不按三种设备建立长期分支。每个里程碑记录固件commit、完整配置与实测结果。只有通过相应验证才标记里程碑完成。

若将来需要改lwIP，单独记录其与IDF匹配的基准commit及patch；不要用随意下载的另一个esp-lwip分支直接替换现有SDK。Mesh-Lite含预编译组网核心，不能把公开API当成可随意修改的内部算法源码。

## ESP-IDF 6.1 实现

启动流程与状态日志分别位于 `mesh_start.c` 和 `mesh_status.c`。SDK 兼容层只替换构建目录内的 NAPT 翻译单元，共享 SDK 保持不变。来源、适配约束与验证说明见 [迁移记录](migration-idf61.md)。
