"""Durable parent-selection intent. ACK means accepted; fresh telemetry proves outcome."""
import json
import re
import threading
import time
from changan_ugv.nodes.inventory import authorized,root_of,valid_id

MAC=re.compile(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}')

class ParentPolicies:
    def __init__(self,store,controller,inventory_loader,root_id):
        self.store,self.controller,self.inventory_loader,self.root_id=store,controller,inventory_loader,root_id
        self.lock=threading.RLock()
        with store.lock,store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS parent_policies (
                revision INTEGER PRIMARY KEY AUTOINCREMENT, msg_id TEXT UNIQUE NOT NULL,
                canonical TEXT NOT NULL, node_id TEXT NOT NULL, policy TEXT NOT NULL,
                state TEXT NOT NULL, error TEXT, created REAL NOT NULL)''')

    def get(self,node):
        valid_id(node)
        with self.store.lock:
            row=self.store.db.execute('SELECT * FROM parent_policies WHERE node_id=? ORDER BY revision DESC LIMIT 1',(node,)).fetchone()
        if row is None:return dict(target=node,revision=0,mode='auto',parent=None,state='unconfigured')
        result=dict(target=node,revision=row['revision'],**json.loads(row['policy']),state=row['state'],error=row['error'])
        with self.controller.condition:
            snapshot=next((r for r in self.controller.registry.snapshot() if r['node_id']==node),{})
        status=snapshot.get('status') or {};observed=status.get('parent_policy') or {}
        result['actual_bssid']=status.get('parent_bssid')
        if snapshot.get('ready') and observed.get('revision')==row['revision'] and observed.get('mode')==result['mode']:
            if observed.get('stage')=='fallback':result['state']='fallback'
            elif observed.get('stage')=='active' and status.get('parent_connected') and (result['mode']=='auto' or
                 status.get('parent_bssid','').lower()==result.get('bssid')):result['state']='applied'
            else:result['state']='waiting'
        elif time.time()-row['created']>60 and result['state'] in ('pending','accepted'):
            result['state']='unconfirmed'
        return result

    def change(self,request):
        allowed={'v','type','node_id','msg_id','deadline_unix','target','mode','parent','expected_revision'}
        if set(request)-allowed:raise ValueError('unknown_parent_policy_fields')
        node=valid_id(request.get('target'));mode=request.get('mode');parent=request.get('parent')
        if mode not in ('auto','prefer','fixed'):raise ValueError('invalid_parent_mode')
        revision=request.get('expected_revision')
        if type(revision) is not int or revision<0:raise ValueError('invalid_parent_revision')
        canonical=json.dumps(request,sort_keys=True,separators=(',',':'))
        with self.lock:
            with self.store.lock:
                old=self.store.db.execute('SELECT * FROM parent_policies WHERE msg_id=?',(request['msg_id'],)).fetchone()
            if old:
                if old['canonical']!=canonical:raise ValueError('msg_id_conflict')
                return self.get(node)
            entries={e['node_id']:e for e in self.inventory_loader()['nodes']}
            child=entries.get(node,{})
            if child.get('role')!='micro_uav' or root_of(child)!=self.root_id or not authorized(child):
                raise ValueError('child_not_authorized_micro')
            with self.controller.condition:
                current=next((r for r in self.controller.registry.snapshot() if r['node_id']==node),{})
            if not current.get('ready') or 'parent' not in current.get('operations',[]):
                raise ValueError('child_not_ready_or_parent_operation_missing_update_firmware')
            if self.get(node)['revision']!=revision:raise ValueError('parent_revision_conflict')
            policy=dict(mode=mode,parent=None)
            if mode!='auto':
                valid_id(parent);entry=entries.get(parent,{})
                if entry.get('role')!='uav' or root_of(entry)!=self.root_id or not authorized(entry):
                    raise ValueError('parent_not_authorized_uav')
                with self.controller.condition:
                    observed=next((r for r in self.controller.registry.snapshot() if r['node_id']==parent),{})
                status=observed.get('status') or {};bssid=status.get('ap_mac','').lower();ssid=status.get('ap_ssid')
                if not observed.get('ready') or status.get('level')!=3 or status.get('ap_enabled') is not True:
                    raise ValueError('parent_not_ready_level3')
                if (status.get('parent_auth') or {}).get('relay_authorized') is not True:
                    raise ValueError('parent_relay_not_authorized_update_firmware_or_wait_for_grant')
                if not MAC.fullmatch(bssid) or bssid=='00:00:00:00:00:00' or int(bssid[:2],16)&1 or not isinstance(ssid,str) or '\0' in ssid or not 1<=len(ssid.encode())<=32:
                    raise ValueError('parent_radio_identity_missing_update_firmware')
                policy.update(parent=parent,bssid=bssid,ssid=ssid)
            elif parent not in (None,''):raise ValueError('auto_mode_has_no_parent')
            with self.store.lock,self.store.db:
                cursor=self.store.db.execute('INSERT INTO parent_policies(msg_id,canonical,node_id,policy,state,created) VALUES(?,?,?,?,?,?)',
                    (request['msg_id'],canonical,node,json.dumps(policy),'pending',time.time()))
                new_revision=cursor.lastrowid
            # Persist before sending. Never replay a pending command on restart or timeout.
            try:
                reply=self.controller.command(node,'parent',dict(policy,revision=new_revision),
                    msg_id=request['msg_id'],deadline_unix=request['deadline_unix'],timeout=8)
                state='accepted' if reply.get('ok') is True else 'rejected'
                error=reply.get('error')
            except ValueError as exc:state,error='rejected',str(exc)
            except (OSError,TimeoutError) as exc:state,error='uncertain',str(exc)
            with self.store.lock,self.store.db:
                self.store.db.execute('UPDATE parent_policies SET state=?,error=? WHERE revision=?',(state,error,new_revision))
            return self.get(node)
