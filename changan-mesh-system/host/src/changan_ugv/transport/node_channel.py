"""MQTT implementation of the task port; no scheduling or hardware logic."""
from changan_ugv.tasks.ports import NodeSnapshot,SendReceipt
from changan_ugv.tasks.store import dumps
from changan_ugv.protocol.messages import LEGACY_MAX_COMMAND

class MQTTNodeChannel:
    def __init__(self,controller):self.controller=controller
    def is_connected(self):return self.controller.connected.is_set()
    def snapshot(self,node_id):
        with self.controller.condition:
            registry=self.controller.registry;entry=registry.nodes.get(node_id,{})
            cap=entry.get('capabilities',{})
            return NodeSnapshot(registry.ready(node_id),entry.get('presence',{}).get('boot_id'),tuple(cap.get('task_types',[])),
                                cap.get('execution_mode'),tuple(cap.get('task_operations',[])),cap.get('task_id'),cap.get('task_status'),
                                registry.command_limit(node_id))
    def ready_count(self):
        with self.controller.condition:
            return sum(self.controller.registry.ready(node) for node in self.controller.registry.nodes)
    def send(self,node_id,packet):
        payload=dumps(packet).encode('utf-8')
        with self.controller.condition:
            if len(payload)>LEGACY_MAX_COMMAND:
                snapshot=self.snapshot(node_id)
                if len(payload)>snapshot.command_limit or not snapshot.ready or packet.get('boot_id')!=snapshot.boot_id:
                    return SendReceipt(False)
            return SendReceipt(self.controller.client.publish(f'mesh/v1/nodes/{node_id}/task_commands',payload,qos=1,retain=False).rc==0)
