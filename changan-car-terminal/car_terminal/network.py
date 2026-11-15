"""Network status and Mesh parent relationships from the versioned v1 list payload."""
from collections import defaultdict
import re
import tkinter as tk
from tkinter import ttk

from .protocol import NODE_ID

MAC = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$")
UNKNOWN = "未上报"


def mac_address(value):
    value = str(value or "").lower().replace("-", ":")
    return value if MAC.fullmatch(value) and value != "00:00:00:00:00:00" else None


def network_snapshot(rows):
    """Resolve only reported parent BSSID -> unique AP MAC; never infer by role/IP."""
    if not isinstance(rows, list):
        raise ValueError("节点列表格式错误")
    nodes, ap_owners = {}, defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or not NODE_ID.fullmatch(str(row.get("node_id", ""))):
            raise ValueError("节点 ID 格式错误")
        identity = row["node_id"]
        if identity in nodes:
            raise ValueError("节点 ID 重复：" + identity)
        status = row.get("status") or {}
        if not isinstance(status, dict):
            raise ValueError("节点状态格式错误：" + identity)
        node = dict(row, status=dict(status), parent=None, group="unknown", relation="父节点未上报")
        radio = status.get("network_status")
        if status.get("execution_host") == "local" and isinstance(radio, dict):
            if not isinstance(radio.get("status"), dict):
                raise ValueError("UGV 网络状态格式错误")
            node["status"].update(radio["status"])
            node["service_ready"] = row.get("service_ready", row.get("ready"))
            node["ready"] = radio.get("fresh") is True
            node["online"] = None
            node["status_age_s"] = radio.get("age_s")
            node["status_current_boot"] = True
        nodes[identity] = node
        ap = mac_address(status.get("ap_mac"))
        if ap:
            ap_owners[ap].append(identity)
    for identity, node in nodes.items():
        status = node["status"]
        if status.get("execution_host") == "local" and not isinstance(status.get("network_status"), dict):
            node.update(group="host", relation="主机服务，不属于 Mesh 无线拓扑")
            continue
        if node.get("status_current_boot") is False and status:
            node.update(group="history", relation="状态来自旧启动，仅保留历史数据")
            continue
        if status.get("parent_connected") is False:
            node.update(group="detached", relation="未关联上游 AP")
            continue
        parent = mac_address(status.get("parent_bssid"))
        if not parent:
            continue
        owners = ap_owners[parent]
        if len(owners) == 1 and owners[0] != identity:
            node.update(parent=owners[0], relation="父节点：" + owners[0])
        elif owners:
            node.update(group="conflict", relation="父节点 MAC 重复或指向自身")
        else:
            node.update(group="external", relation="上游 AP 未在节点列表中：" + parent)
    cycles = set()
    for identity in nodes:
        chain, positions = [], {}
        current = identity
        while current is not None:
            if current in positions:
                cycles.update(chain[positions[current]:])
                break
            positions[current] = len(chain)
            chain.append(current)
            current = nodes[current]["parent"]
    for identity in cycles:
        nodes[identity].update(parent=None, group="conflict", relation="父节点关系存在环，请检查上报数据")
    return nodes


def readiness(node):
    if node.get("ready") is True:
        return "就绪"
    if node.get("online") is False:
        return "离线"
    return "未就绪"


GROUPS = dict(external="外部 / 未登记的上游 AP", unknown="父节点未上报",
              detached="未关联上游", history="旧启动的历史状态", conflict="关系待确认",
              host="主机服务（非 Mesh 无线节点）")


class NetworkPanel:
    def __init__(self, parent, refresh, select_target):
        self.nodes = {}
        self.select_target = select_target
        self.summary = tk.StringVar(parent, value="等待刷新网络结构")
        self.detail = tk.StringVar(parent, value="选择节点查看 MAC、网关和连接详情。")
        bar = ttk.Frame(parent)
        bar.pack(fill="x")
        self.refresh_button = ttk.Button(bar, text="刷新网络结构", command=refresh)
        self.refresh_button.pack(side="left", padx=(0, 12))
        ttk.Label(bar, textvariable=self.summary).pack(side="left")
        table = ttk.Frame(parent)
        table.pack(fill="both", expand=True, pady=8)
        columns = [("ready", "状态", 85), ("role", "角色", 100), ("level", "Mesh 层级", 80),
                   ("sta_ip", "STA IP", 125), ("ap_ip", "AP IP", 125),
                   ("gateway", "网关", 125), ("rssi", "RSSI / dBm", 95),
                   ("channel", "信道", 65), ("associated_children", "关联客户端", 100),
                   ("age", "遥测年龄 / 秒", 110)]
        self.tree = ttk.Treeview(table, columns=[key for key, _, _ in columns],
                                show="tree headings", selectmode="browse", height=6)
        self.tree.heading("#0", text="节点 / 父子结构")
        self.tree.column("#0", width=240, minwidth=150, stretch=False)
        for key, title, width in columns:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=width, stretch=False)
        yscroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree.tag_configure("ready", foreground="#147047")
        self.tree.tag_configure("stale", foreground="#777777")
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        ttk.Label(parent, textvariable=self.detail, wraplength=900, justify="left").pack(anchor="w")
        ttk.Label(parent, text="按父 BSSID 匹配节点 AP MAC；灰色为未就绪快照。未知字段不推测，底部可横向滚动。").pack(anchor="w", pady=(5, 0))

    def clear(self):
        self.nodes.clear()
        self.tree.delete(*self.tree.get_children())
        self.summary.set("等待刷新网络结构")
        self.detail.set("选择节点查看 MAC、网关和连接详情。")

    def mark_stale(self, reason):
        for identity in self.nodes:
            if self.tree.exists(identity):
                self.tree.item(identity, tags=("stale",))
        self.summary.set(reason + " · 以下为上次查询快照")

    def update(self, rows):
        nodes = network_snapshot(rows)
        selected = self.tree.selection()
        expanded = {key: self.tree.item(key, "open") for key in self.nodes if self.tree.exists(key)}
        self.tree.delete(*self.tree.get_children())
        self.nodes = nodes
        for group, title in GROUPS.items():
            if any(node["parent"] is None and node["group"] == group for node in nodes.values()):
                self.tree.insert("", "end", iid="group:" + group, text=title, open=True)
        # Every parent is inserted before its children without recursive Python calls.
        pending = set(nodes)
        while pending:
            for identity in sorted(pending):
                node = nodes[identity]
                parent = node["parent"]
                if parent and parent in pending:
                    continue
                status = node["status"]
                values = [readiness(node), status.get("role", UNKNOWN),
                          status.get("level", UNKNOWN)]
                values.extend(status.get(key, UNKNOWN) for key in
                              ("sta_ip", "ap_ip", "gateway", "rssi", "channel", "associated_children"))
                values.append(node.get("status_age_s") if node.get("status_age_s") is not None else UNKNOWN)
                self.tree.insert(parent or "group:" + node["group"], "end", iid=identity,
                                 text=identity, values=values, open=expanded.get(identity, True),
                                 tags=("ready" if node.get("ready") else "stale",))
                pending.remove(identity)
        count = sum(node.get("ready") is True for node in nodes.values())
        self.summary.set(f"{len(nodes)} 个节点 / {count} 个就绪 · 手动刷新快照")
        if selected and selected[0] in nodes:
            self.tree.selection_set(selected[0])
            self._selected()
        else:
            self.detail.set("选择节点查看 MAC、网关和连接详情。")

    def _selected(self, _=None):
        selected = self.tree.selection()
        if not selected or selected[0] not in self.nodes:
            return
        identity = selected[0]
        node = self.nodes[identity]
        status = node["status"]
        fields = [identity, node["relation"]]
        if "service_ready" in node:
            fields.append("UGV USB 网络设备；主机任务服务：" + ("就绪" if node["service_ready"] else "未就绪"))
        fields += [f"{label}: {status.get(key, UNKNOWN)}" for key, label in
                   (("parent_bssid", "父 BSSID"), ("sta_mac", "STA MAC"),
                    ("ap_mac", "AP MAC"), ("netmask", "子网掩码"))]
        self.detail.set("  |  ".join(fields))
        self.select_target(identity)
