"""Explicit Python protocol test double, NOT an execution test of the C firmware."""
from changan_ugv.agents.ugv import HostDiagnostics


class WorkflowReference(HostDiagnostics):
    def handle(self, packet):
        if packet['op']=='start' and packet.get('kind') in ('patrol','anomaly_review'):
            config=dict(packet['config'],_test_kind=packet['kind'],period_ms=1000)
            if packet['kind']=='patrol':config['duration_s']=len(config['point_ids'])*config['point_duration_s']
            packet=dict(packet,config=config)
        return super().handle(packet)

    def report(self,msg_id=None,task_id=None,revision=1):
        if not self.row or (task_id is not None and task_id!=self.row['task_id']) or '_test_kind' not in self.row['config']:
            return super().report(msg_id,task_id,revision)
        row=self.row;config=row['config'];finished=row['state']=='SUCCEEDED'
        self.sequence+=1
        result=dict(mode='esp32_test',stage='test_done' if finished else 'point_check')
        if config['_test_kind']=='patrol':
            count=len(config['point_ids']);done=min(count,int(row['elapsed']//(config['point_duration_s']*1000)))
            result.update(point=config['point_ids'][min(done,count-1)],done=done,total=count)
            if config['anomaly_point'] and done>=config['anomaly_point']:result['event_id']=row['task_id']
        else:
            result.update(event_id=config['event_id'],verdict=config['test_verdict'] if finished else 'pending')
            if not finished:result['stage']='receive_event'
        self.emit(dict(v=1,type='task.event',node_id=self.node,task_id=row['task_id'],msg_id=msg_id or row['command_id'],
            revision=row['revision'],boot_id=self.boot,seq=self.sequence,state=row['state'],
            progress=min(100,int(row['elapsed']*100/(config['duration_s']*1000))),result=result))
