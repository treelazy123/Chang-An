# Jetson 部署文件

本目录包含 Jetson 所需的 CA 公钥证书、Broker 和后台的真实证书/私钥、设备清单及访问规则。项目所有者已明确要求将本目录与现有 secrets/ 一并提交 GitHub；完整 CA 和各设备身份位于相邻 secrets/。

按 [交接说明](../docs/handoff/README.md) 的 Jetson 步骤安装这些文件，不新建另一套 CA 替换已有设备信任。目录中的文件是交接副本，Jetson 实际任务数据放到 `/var/lib/changan`，不回写这里。

本次整理时旧后台仍在运行，未停止服务，未导出任务数据库和执行 journal；具体状态见 `snapshot-status.json`。Jetson 基础联调使用新任务库，旧电脑的数据保持原样。如需保留旧任务历史，由维护方在切换时停止旧后台，再按交接说明一致导出数据库和 journal 后安装。
