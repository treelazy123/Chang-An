"""Topology tests use only reported v1 fields, never live COM or MQTT."""
from pathlib import Path
import sys
import tkinter as tk
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from car_terminal.gui import DebugWindow, SessionWorker
from car_terminal.network import network_snapshot


def node(identity, level, ap, parent=None, **extra):
    status = dict(role="micro_uav", level=level, ap_mac=ap, **extra)
    if parent:
        status.update(parent_connected=True, parent_bssid=parent)
    return dict(node_id=identity, ready=True, status=status)


class TopologyTests(unittest.TestCase):
    def test_branching_mesh_and_external_uplink_use_mac_not_role_or_subnet(self):
        rows = [
            node("bridge", 1, "aa:bb:cc:00:00:01", "ff:ee:dd:cc:bb:aa"),
            node("car", 2, "aa:bb:cc:00:00:02", "AA:BB:CC:00:00:01", sta_ip="10.1.1.2"),
            node("uav", 2, "aa:bb:cc:00:00:03", "aa-bb-cc-00-00-01", sta_ip="10.2.2.2"),
            node("micro", 3, "aa:bb:cc:00:00:04", "aa:bb:cc:00:00:03")]
        result = network_snapshot(rows)
        self.assertEqual("external", result["bridge"]["group"])
        self.assertEqual("bridge", result["car"]["parent"])
        self.assertEqual("bridge", result["uav"]["parent"])
        self.assertEqual("uav", result["micro"]["parent"])

    def test_old_firmware_levels_do_not_invent_parent_or_ip(self):
        result = network_snapshot([dict(node_id="root", ready=True, status=dict(role="pc_root",level=1)),
                                   dict(node_id="micro", ready=False, status=dict(role="micro_uav",level=2))])
        self.assertIsNone(result["micro"]["parent"])
        self.assertEqual("unknown", result["micro"]["group"])
        self.assertNotIn("sta_ip", result["micro"]["status"])

    def test_duplicate_mac_self_parent_cycles_and_old_boot_are_separated(self):
        first, second = "aa:bb:cc:00:00:01", "aa:bb:cc:00:00:02"
        rows = [node("a", 1, first, second), node("b", 2, second, first)]
        result = network_snapshot(rows)
        self.assertTrue(all(row["group"] == "conflict" for row in result.values()))
        rows = [node("a", 1, first), node("b", 1, first), node("c", 2, second, first)]
        self.assertEqual("conflict", network_snapshot(rows)["c"]["group"])
        self.assertEqual("conflict", network_snapshot([node("a", 1, first, first)])["a"]["group"])
        old = node("old", 2, first, second)
        old["status_current_boot"] = False
        self.assertEqual("history", network_snapshot([old])["old"]["group"])

    def test_local_ugv_service_and_physical_usb_network_are_distinct_statuses(self):
        host = dict(node_id="ugv-001", ready=True, status=dict(role="ugv", execution_host="local"))
        self.assertEqual("host", network_snapshot([host])["ugv-001"]["group"])
        host["status"]["network_status"] = dict(fresh=False, age_s=20,
            status=dict(role="ugv", level=1, ap_mac="aa:bb:cc:00:00:01"))
        result = network_snapshot([host])["ugv-001"]
        self.assertTrue(result["service_ready"])
        self.assertFalse(result["ready"])
        self.assertEqual(1, result["status"]["level"])

    def test_bad_or_duplicate_node_rows_fail_explicitly(self):
        for rows in [[dict(node_id="bad/id")], [dict(node_id="a",status="bad")],
                     [dict(node_id="a"), dict(node_id="a")]]:
            with self.assertRaises(ValueError):
                network_snapshot(rows)


class NetworkWindowTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.worker = SessionWorker(factory=lambda _: (_ for _ in ()).throw(AssertionError("No devices")))
        self.window = DebugWindow(self.root, worker=self.worker)
        self.root.update_idletasks()

    def tearDown(self):
        self.window.close()
        self.worker.thread.join(2)

    def test_tree_parent_ip_rssi_details_and_target_selection(self):
        rows = [node("root", 1, "aa:bb:cc:00:00:01"),
                node("micro", 2, "aa:bb:cc:00:00:02", "aa:bb:cc:00:00:01",
                     sta_ip="192.168.5.2", ap_ip="192.168.6.1", gateway="192.168.5.1", rssi=-61)]
        self.window._apply("nodes", rows)
        panel = self.window.network
        self.assertEqual("root", panel.tree.parent("micro"))
        self.assertEqual("192.168.5.2", panel.tree.set("micro", "sta_ip"))
        self.assertEqual("-61", panel.tree.set("micro", "rssi"))
        panel.tree.selection_set("micro")
        panel._selected()
        self.assertEqual("micro", self.window.values["target"].get())
        self.assertIn("aa:bb:cc:00:00:01", panel.detail.get())
        panel.mark_stale("连接已断开")
        self.assertIn("快照", panel.summary.get())
        self.assertIn("stale", panel.tree.item("micro", "tags"))

    def test_status_reply_updates_network_fields(self):
        self.window._apply("nodes", [dict(node_id="micro", ready=True, status=dict(level=2))])
        self.window._apply("status", dict(node_id="micro", payload=dict(level=3, sta_ip="10.0.1.2")))
        self.assertEqual("3", self.window.network.tree.set("micro", "level"))
        self.assertEqual("10.0.1.2", self.window.network.tree.set("micro", "sta_ip"))

    def test_old_firmware_and_minimum_window_render_without_clipping(self):
        self.window._apply("nodes", [dict(node_id="old", ready=False, status=dict(level=0))])
        self.assertEqual("未上报", self.window.network.tree.set("old", "sta_ip"))
        self.root.deiconify()
        self.root.geometry("980x720")
        panel = self.window.network
        notebook = panel.tree.master.master.master
        notebook.select(panel.tree.master.master)
        self.root.update()
        self.assertLessEqual(panel.tree.winfo_x() + panel.tree.winfo_width(), panel.tree.master.winfo_width())
        self.assertGreater(panel.tree.winfo_width(), 500)

if __name__ == "__main__":
    unittest.main()
