"""MQTT implementation of the task port; no scheduling or hardware logic."""
from changan_ugv.tasks.ports import NodeSnapshot,SendReceipt
from changan_ugv.tasks.store import dumps

class MQTTNodeChannel:
    def __init__(self,controller):self.controller=controller
    def is_connected(self):return self.controller.connected.is_set()
    def snapshot(self,node_id):
        with self.controller.condition:
            registry=self.controller.registry;entry=registry.nodes.get(node_id,{})
            cap=entry.get('capabilities',{})
            return NodeSnapshot(registry.ready(node_id),entry.get('presence',{}).get('boot_id'),tuple(cap.get('task_types',[])),
                                cap.get('execution_mode'),tuple(cap.get('task_operations',[])),cap.get('task_id'),cap.get('task_status'))
    def ready_count(self):
        with self.controller.condition:
            return sum(self.controller.registry.ready(node) for node in self.controller.registry.nodes)
    def send(self,node_id,packet):
        return SendReceipt(self.controller.client.publish(f'mesh/v1/nodes/{node_id}/task_commands',dumps(packet),qos=1,retain=False).rc==0)
