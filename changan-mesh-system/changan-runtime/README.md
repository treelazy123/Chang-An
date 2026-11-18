# 根节点部署交接文件

nodes.json与acl.conf描述ugv-root四层网络。现有CA和服务凭据保留，不重新生成。
主机运行UGV Service、Mosquitto、USB桥接，终端通过HTTP/WS访问后台。
部署前按主仓库docs/deployment.md核对配置路径与状态迁移，不直接覆盖目标密钥。
snapshot-status.json是带日期的交接记录，不是当前运行状态；Jetson实物验收仍须完成。
