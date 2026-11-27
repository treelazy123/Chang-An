"""MCI 1.0 discovery and local-only business adapters. No device protocol changes."""
import copy
import json
import re
import threading
from jsonschema import Draft202012Validator, ValidationError, SchemaError

VERSION = '1.0.0'
SERVICE = re.compile(r'[A-Z][A-Za-z0-9]*(?:_[A-Z][A-Za-z0-9]*)+')
METHOD = re.compile(r'(?:Cnr|Get|Ntf|Et|Dat)_[A-Z][A-Za-z0-9]*(?:_[A-Z][A-Za-z0-9]*)*')
RENAMES = {'durationSeconds':'duration_s', 'staleAfterSeconds':'stale_after_s',
           'pointDurationSeconds':'point_duration_s', 'probeNodeId':'probe_node',
           'parentNodeId':'parent', 'executorNodeId':'target', 'text':'payload'}
def snake(key):
    return RENAMES.get(key, re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower())
def camel(key):
    inverse = {v:k for k,v in RENAMES.items() if v not in ('target','payload')}
    return inverse.get(key, re.sub(r'_([a-z])',lambda m:m[1].upper(),key))
def convert(value):
    if isinstance(value,dict):return {snake(k):convert(v) for k,v in value.items()}
    if isinstance(value,list):return [convert(v) for v in value]
    return value
def field(kind='string', **constraints):
    return dict(type=kind,description='Business value&See the method contract for meaning and constraints.',**constraints)
MEANINGS={
 'enabled':'Whether the administrator enabled the inventory entry.',
 'apSubnet':'Reserved 192.168.N.0/24 AP subnet index; null for STA-only leaves.',
 'taskId':'Stable task identity; supplied by the caller on creation to support querying uncertain submissions.',
 'executorNodeId':'Device or host selected to execute the created task.',
 'kind':'Task type; selects the corresponding config and result contract.',
 'config':'Task configuration; validated against kind or the stored task kind when updating.',
 'durationSeconds':'Sampling duration in seconds; omission uses 30 for diagnostics, 5 for anomaly review.',
 'periodMs':'Sampling period in milliseconds; omission uses 1000.',
 'probeNodeId':'Authorized remote node to probe; cannot be the local root host.',
 'watchTaskId':'Caller-accessible task to monitor; monitoring another monitor is prohibited.',
 'staleAfterSeconds':'Feedback freshness threshold in seconds; omission uses 10.',
 'executionMode':'Execution mode; esp32_test indicates a workflow test, not physical motion or recognition.',
 'areaId':'Logical test area identifier.', 'pointIds':'Ordered distinct test point identifiers; no physical flight coordinates.',
 'pointDurationSeconds':'Time spent on each test point in seconds; omission uses 3.',
 'anomalyPoint':'One-based test point producing an incident; zero disables incidents; omission uses zero.',
 'eventId':'Incident identity used to correlate the original test and review.',
 'testVerdict':'Preset test review outcome; omission uses inconclusive.',
 'expectedRevision':'Optimistic concurrency precondition; must match the current task, admission or policy revision.',
 'revision':'Current task or parent policy revision; these revision domains are independent.',
 'priority':'Queue priority from 0 through 9; omission uses zero.',
 'executeBefore':'Latest allowed execution start as Unix seconds; null means no such deadline.',
 'cursor':'Durable pagination or replay cursor; zero starts from the beginning.',
 'more':'Whether another page is available after this cursor.',
 'items':'Current page of tasks, state events or test incidents.',
 'nodes':'Registered or observed nodes; historical entries do not prove current connectivity.',
 'instances':'Runtime capability instances and their availability, separate from method definitions.',
 'nodeId':'Identity of the node described by this record.', 'rootId':'Managing root node identity.',
 'role':'Configured device role in the four-level mesh.',
 'trustStatus':'pending, trusted or revoked admission decision.',
 'admissionRevision':'Admission decision revision, distinct from task or parent policy revision.',
 'brokerAclApplied':'Whether broker enforcement has been applied; current adapter returns false.',
 'brokerAclReloadRequired':'Whether the generated pending broker ACL still needs controlled loading.',
 'registered':'Whether this historical catalog entry is still in the administrator inventory.',
 'registration':'Administrator registration snapshot; observations cannot grant trust.',
 'lastObservation':'Last stored node snapshot or null when none has been recorded.',
 'observedAt':'Host observation time as Unix seconds or null if unknown.',
 'ready':'Whether current boot, capabilities, authorization and telemetry satisfy business readiness; null in probe results means no measurement yet.',
 'online':'Last MQTT presence claim, or null if unreported; not by itself a freshness guarantee.',
 'statusAgeS':'Telemetry age in seconds, or null if unreported.',
 'statusCurrentBoot':'Whether telemetry belongs to the currently observed boot.',
 'operations':'Announced supported operations.', 'taskTypes':'Announced supported task types.',
 'status':'Observed device state or null if no observation exists.',
 'mode':'Parent selection mode: auto, prefer or fixed; task result mode identifies its execution mode.',
 'parentNodeId':'Desired parent UAV identity; null for automatic selection.',
 'parentPolicy':'Saved or device-reported parent selection policy.',
 'actualBssid':'Last observed upstream AP MAC; does not alone confirm the requested policy.',
 'state':'Known task or policy state; accepted does not mean physical execution completed.',
 'error':'Known operation or execution error; null means no recorded error.',
 'stage':'Processing stage, including acceptance versus final application or test progress.',
 'task':'Persisted task view; includes state and revision, not a physical-completion promise.',
 'result':'Recorded metrics or ESP32 workflow result; absent until reported.',
 'lastOperation':'Last persisted control operation and dispatch state.',
 'commandId':'Internal task operation identity returned as business tracking information.',
 'op':'Task control operation.', 'opSeq':'Monotonic task operation sequence.',
 'target':'Task executor identity, or monitored task executor in a result.',
 'created':'Creation time as Unix seconds.', 'updated':'Last persisted change as Unix seconds.',
 'stateSeq':'Monotonic state-change sequence for replay ordering.',
 'progress':'Reported execution progress in percent.',
 'feedbackAt':'Host receive time of valid executor feedback as Unix seconds.',
 'deleted':'Whether eligible terminal task history has been removed; device NVS is not erased.',
 'source':'Metrics source: c6 or ugv_host.', 'samples':'Number of collected diagnostic samples.',
 'readyNodes':'Number of ready nodes observed by host diagnostics.',
 'ok':'Successful network probe count.', 'failed':'Failed network probe count.',
 'lastMs':'Latest application round-trip milliseconds; null on failure or before a successful measurement.',
 'avgMs':'Mean successful probe round-trip milliseconds, or null when none succeeded.',
 'maxMs':'Maximum successful probe round-trip milliseconds, or null when none succeeded.',
 'ageS':'Valid feedback or snapshot age in seconds.', 'health':'Monitor health classification, distinct from task execution state.',
 'done':'Completed ESP32 test point count.', 'total':'Total ESP32 test point count.',
 'point':'Current ESP32 test point identity.', 'verdict':'Reported test review conclusion, not actual recognition.',
 'rssi':'Reported Wi-Fi received signal strength in dBm.', 'rssiMin':'Minimum sampled RSSI in dBm.', 'rssiMax':'Maximum sampled RSSI in dBm.',
 'heap':'Current free heap in bytes.', 'heapMin':'Minimum free heap in bytes.',
 'level':'Observed Mesh level.', 'topology':'Configured Mesh topology.',
 'staIp':'Observed station IPv4 address.', 'apIp':'Observed AP IPv4 address; absent for STA-only leaves.',
 'gateway':'Observed station default gateway IPv4 address.', 'netmask':'Observed IPv4 netmask.',
 'staMac':'Station MAC address.', 'apMac':'AP MAC address; absent when AP is disabled.',
 'apSsid':'Advertised AP SSID.', 'parentBssid':'Observed parent AP MAC, not an inferred parent identity.',
 'apEnabled':'Whether this device actually has AP mode enabled.',
 'parentConnected':'Whether the device reports association to an upstream AP.',
 'uptimeMs':'Device monotonic uptime in milliseconds; not UTC.',
 'channel':'Wi-Fi channel number.', 'associatedChildren':'Associated AP client count; absent for STA-only leaves.',
 'executionHost':'local identifies the host task service rather than a physical radio.',
 'networkStatus':'Root radio snapshot received over USB, separate from host service readiness.',
 'fresh':'Whether the root USB network snapshot is within its freshness window.',
 'serviceId':'Legacy runtime instance identifier, not a stable MCI service name.',
 'agentType':'Execution agent role.', 'serviceType':'Legacy instance task type.',
 'capabilities':'Announced instance capability labels.',
 'availability':'Instance availability: available, busy or unavailable.',
 'taskStatus':'Last known instance execution state.', 'bootId':'Executor boot identity.',
 'announced':'Whether the required runtime capability has been announced.',
 'reason':'Instance unavailability reason, or null when none.',
 'sourceTaskId':'Task that generated this test incident.', 'pointId':'Test point that generated the incident.',
 'test':'True for ESP32 test incidents; not evidence of real-world detection.',
 'brokerConnected':'Whether the local host is connected to Mosquitto.',
 'acknowledged':'True only after a matching successful application ACK.',
 'text':'Text sent to or returned by the diagnostic echo operation.'}
def obj(properties, required=()):
    labels={'taskId':'任务编号','kind':'任务类型','config':'任务配置','executorNodeId':'执行节点',
        'durationSeconds':'持续时间','periodMs':'采样周期','probeNodeId':'被检查节点','watchTaskId':'被监视任务',
        'expectedRevision':'预期版本','parentNodeId':'指定父节点','mode':'选择模式','state':'当前状态',
        'result':'业务结果','nodes':'节点清单','instances':'服务实例','trustStatus':'信任状态',
        'text':'回显文本','cursor':'查询游标','items':'本页记录','more':'是否还有下一页'}
    properties={k:dict(v,description=labels.get(k,re.sub(r'(?<!^)(?=[A-Z])',' ',k).capitalize())+'&'+MEANINGS[k]) for k,v in properties.items()}
    return dict(type='object',description='Business record&Fields follow the published method contract.',properties=properties,required=list(required),additionalProperties=False)
def array(item):return field('array',items=item)
ID=field(pattern=r'^[A-Za-z0-9_-]{1,32}$',minLength=1,maxLength=32)
REV=field('integer',minimum=0)
CURSOR=field('integer',minimum=0,maximum=9223372036854775807)
TEXT=field(maxLength=256)
NULLTEXT=field(['string','null'])
NUM=field(['number','null'])
BOOL=field('boolean')
EMPTY=obj({})
COMMON={'durationSeconds':field('integer',minimum=1,maximum=3600),
        'periodMs':field('integer',minimum=200,maximum=10000)}
CONFIGS={
 'diagnostics':obj(COMMON),
 'network_diagnostics':obj(dict(COMMON,probeNodeId=ID),['probeNodeId']),
 'task_monitor':obj(dict(COMMON,watchTaskId=ID,staleAfterSeconds=field('integer',minimum=1,maximum=3600)),['watchTaskId']),
 'patrol':obj(dict(executionMode=field(const='esp32_test'),areaId=field(pattern=r'^[A-Za-z0-9_-]{1,12}$'),
     pointIds=field('array',items=field(pattern=r'^[A-Za-z0-9_-]{1,12}$'),minItems=1,maxItems=3,uniqueItems=True),
     pointDurationSeconds=field('integer',minimum=1,maximum=60),anomalyPoint=field('integer',minimum=0,maximum=3)),
     ['executionMode','areaId','pointIds']),
 'anomaly_review':obj(dict(executionMode=field(const='esp32_test'),eventId=ID,
     testVerdict=field(enum=['confirmed','cleared','inconclusive']),durationSeconds=field('integer',minimum=1,maximum=60)),['executionMode','eventId'])}
CONFIG=obj({k:v for config in CONFIGS.values() for k,v in config['properties'].items()})
CONFIG['properties']['durationSeconds']=COMMON['durationSeconds']
# Updates are resolved against the stored kind, not ambiguous shape matching.
CONFIG['anyOf']=list(CONFIGS.values())
RESULT=obj({**{k:NULLTEXT for k in ('source','nodeId','taskId','target','state','health','error','mode','stage','point','eventId','verdict')},
 **{k:NUM for k in ('samples','readyNodes','ok','failed','lastMs','avgMs','maxMs','ageS','progress','done','total','rssi','rssiMin','rssiMax','heap','heapMin')},'ready':field(['boolean','null'])})
TASK_PROPERTIES={**{k:NULLTEXT for k in ('taskId','target','kind','state','error')},
 **{k:NUM for k in ('revision','priority','executeBefore','created','updated','stateSeq','progress','feedbackAt')},
 'config':CONFIG,'result':RESULT,
 'lastOperation':obj(dict(commandId=TEXT,op=TEXT,status=TEXT,opSeq=REV))}
TASK=obj(TASK_PROPERTIES,['taskId','kind','state','revision'])
STATUS=obj({**{k:NULLTEXT for k in ('role','topology','staIp','apIp','gateway','netmask','staMac','apMac','apSsid','parentBssid','executionHost')},
 **{k:NUM for k in ('level','heap','heapMin','uptimeMs','rssi','channel','associatedChildren')},
 'apEnabled':BOOL,'parentConnected':BOOL})
NODE=obj(dict(nodeId=TEXT,role=NULLTEXT,rootId=NULLTEXT,trustStatus=NULLTEXT,ready=BOOL,
 enabled=BOOL,admissionRevision=REV,
 online=field(['boolean','null']),statusAgeS=NUM,statusCurrentBoot=BOOL,
 operations=array(TEXT),taskTypes=array(TEXT),status=dict(STATUS,type=['object','null'])))
REGISTRATION=obj(dict(nodeId=TEXT,rootId=TEXT,role=TEXT,enabled=BOOL,apSubnet=NUM,
    trustStatus=TEXT,admissionRevision=REV))
REGISTERED=obj(dict(nodeId=TEXT,rootId=TEXT,registered=BOOL,observedAt=NUM,
    registration=REGISTRATION,lastObservation=dict(NODE,type=['object','null'])))
INSTANCE=obj({**{k:NULLTEXT for k in ('serviceId','nodeId','agentType','serviceType','availability','taskStatus','taskId','bootId','executionMode','reason')},
 'capabilities':array(TEXT),'operations':array(TEXT),'announced':BOOL})
PARENT=obj(dict(mode=TEXT,parentNodeId=NULLTEXT,revision=REV,state=TEXT,error=NULLTEXT,actualBssid=NULLTEXT))
STATUS['properties']['parentPolicy']=obj(dict(mode=TEXT,revision=REV,parentNodeId=NULLTEXT,stage=TEXT))
STATUS['properties']['networkStatus']=obj(dict(status=copy.deepcopy(STATUS),ageS=NUM,fresh=BOOL))
NODE['properties']['parentPolicy']=PARENT
EVENT=obj({k:v for k,v in TASK_PROPERTIES.items() if k not in ('config','lastOperation','target','kind')})
INCIDENT=obj(dict(eventId=TEXT,sourceTaskId=TEXT,nodeId=TEXT,areaId=TEXT,pointId=TEXT,created=NUM,test=BOOL,executionMode=TEXT))
PAGE=lambda item:obj(dict(items=array(item),cursor=CURSOR,more=BOOL),['items','cursor','more'])
def project(value,schema):
    """Explicit stable MCI view; legacy transport fields never leak into results."""
    if value is None:return None
    if isinstance(value,list):return [project(v,schema['items']) for v in value]
    if isinstance(value,dict):
        properties=schema.get('properties')
        if properties is None:return {camel(k):v for k,v in value.items()}
        result={}
        for key,val in value.items():
            key=camel(key)
            if key in properties:result[key]=project(val,properties[key])
        return result
    return value

def definitions():
    rows={}
    def add(service,method,inputs,outputs,description,operation=None,extra=None):
        rows[service,method]=(dict(method=method,description=description,inputSchema=inputs,outputSchema=outputs),operation,extra or {})
    node='Mesh_Node';task='Mesh_Task'
    add(node,'Get_NodeList',EMPTY,obj(dict(nodes=array(NODE)),['nodes']),'List nodes&Returns observed readiness and radio snapshots.', 'list')
    add(node,'Get_RegisteredNodes',EMPTY,obj(dict(nodes=array(REGISTERED)),['nodes']),
        'Registration history&Does not establish live connectivity.','catalog')
    add(node,'Get_ServiceInstances',EMPTY,obj(dict(instances=array(INSTANCE)),['instances']),'List instances&Availability is separate from method discovery.','list',dict(scope='services'))
    add(node,'Get_Status',EMPTY,STATUS,'Read device status&Requires a ready authorized MQTT device.','command',dict(op='status'))
    add(node,'Cnr_Ping',EMPTY,obj(dict(acknowledged=field('boolean',const=True)),['acknowledged']),'Probe device&Success means a matching application acknowledgement.','command',dict(op='ping'))
    add(node,'Cnr_Echo',obj(dict(text=TEXT),['text']),obj(dict(text=TEXT),['text']),'Echo text&Success means the device returned the input text.','command',dict(op='echo'))
    add('Mesh_Admission','Cnr_SetTrustStatus',obj(dict(trustStatus=field(enum=['pending','trusted','revoked']),expectedRevision=REV),['trustStatus','expectedRevision']),
        obj(dict(trustStatus=TEXT,admissionRevision=REV,brokerAclApplied=BOOL,brokerAclReloadRequired=BOOL)),
        'Manage trust&Success persists admission; broker ACL still requires controlled reload.','node.admission')
    add('Mesh_Parent','Get_Policy',EMPTY,PARENT,'Read parent policy&Returns saved intent and available observation.','node.parent.get')
    add('Mesh_Parent','Cnr_SetPolicy',obj(dict(mode=field(enum=['auto','prefer','fixed']),parentNodeId=field(['string','null']),expectedRevision=REV),['mode','parentNodeId','expectedRevision']),PARENT,
        'Set parent policy&Accepted is not applied; fresh matching telemetry confirms application.','node.parent')
    createprops=dict(executorNodeId=ID,kind=field(enum=list(CONFIGS)),config=CONFIG,taskId=ID,priority=field('integer',minimum=0,maximum=9),executeBefore=field(['integer','null']))
    create=obj(createprops,['executorNodeId','kind','config','taskId'])
    create['oneOf']=[obj(dict(createprops,kind=field(const=k),config=v),create['required']) for k,v in CONFIGS.items()]
    receipt=obj(dict(task=TASK,stage=TEXT,commandId=TEXT),['task'])
    add(task,'Cnr_CreateTask',create,receipt,'Create task&Persists CREATED; does not start execution.','task.create')
    add(task,'Get_Task',obj(dict(taskId=ID),['taskId']),receipt,'Read task&Returns last known persisted state.','task.get')
    add(task,'Get_TaskList',obj(dict(cursor=CURSOR)),PAGE(TASK),'List tasks&Returns caller-owned tasks using cursor pagination.','task.list')
    add(task,'Cnr_UpdateTask',obj(dict(taskId=ID,expectedRevision=REV,config=CONFIG,priority=field('integer',minimum=0,maximum=9),executeBefore=field(['integer','null'])),['taskId','expectedRevision']),receipt,
        'Update task&Only CREATED tasks; config is checked against stored kind.','task.update')
    for title,op in [('Start','start'),('Pause','pause'),('Resume','resume'),('Cancel','cancel'),('DeleteTaskHistory','delete')]:
        method='Cnr_'+(title+'Task' if op!='delete' else title)
        output=obj(dict(deleted=BOOL,taskId=TEXT,stateSeq=REV,stage=TEXT)) if op=='delete' else receipt
        add(task,method,obj(dict(taskId=ID,expectedRevision=REV),['taskId','expectedRevision']),output,
            {'start':'开始任务&成功表示开始意图已入队，不表示开始执行或执行完成。',
             'pause':'暂停任务&成功表示暂停意图已受理；后续状态为 PAUSED 才确认暂停。',
             'resume':'恢复任务&成功表示恢复意图已受理；后续状态为 RUNNING 才确认恢复。',
             'cancel':'取消任务&成功表示取消意图已受理；应查询并确认最终任务状态。',
             'delete':'删除任务历史&成功表示符合删除条件的终态历史已删除，不清除设备 NVS。'}[op],
            'task.control',dict(op=op))
    for method,scope,item in [('Get_TaskEvents','tasks',obj(dict(EVENT['properties'],cursor=CURSOR))),('Get_TestIncidents','incidents',INCIDENT)]:
        add(task,method,obj(dict(cursor=CURSOR,taskId=ID)),PAGE(item),'Read events&Caller-owned durable history; incident results are ESP32 test data.','task.events',dict(scope=scope))
    add(task,'Ntf_TaskChanged',EVENT,None,'Task change&One-way persisted state notification, not a control request.')
    add(node,'Ntf_NodeSnapshot',obj(dict(nodes=array(NODE),brokerConnected=BOOL),['nodes','brokerConnected']),None,'Node snapshot&One-way periodic observation; not durable history.')
    add(task,'Et_TestIncident',INCIDENT,None,'Test incident&One-way validated ESP32 test event; no physical recognition claim.')
    return rows

def validate_catalog(rows):
    from urllib.parse import unquote
    def description(value):
        if not isinstance(value,str) or '&' not in value or not all(x.strip() for x in value.split('&',1)):
            raise ValueError('Description must contain nonempty user and detailed text')
    def walk(schema,root):
        if isinstance(schema,bool):return
        if not isinstance(schema,dict):raise ValueError('Invalid subschema')
        if '$ref' in schema:
            ref=schema['$ref']
            if not isinstance(ref,str) or (ref!='#' and not ref.startswith('#/')):raise ValueError('Only local JSON Pointers allowed')
            resolved=root
            try:
                for part in ([] if ref=='#' else unquote(ref[2:]).split('/')):
                    if re.search(r'~(?![01])',part):raise ValueError('Invalid pointer escape')
                    part=part.replace('~1','/').replace('~0','~')
                    resolved=resolved[int(part)] if isinstance(resolved,list) and re.fullmatch(r'0|[1-9][0-9]*',part) else resolved[part]
                if not isinstance(resolved,(dict,bool)):raise ValueError('Reference is not a schema')
            except (KeyError,TypeError,IndexError):raise ValueError('Unresolved local reference') from None
        if any(k in schema for k in ('$id','$anchor','$dynamicRef','$dynamicAnchor')):raise ValueError('Unsupported reference keyword')
        types=schema.get('type',[]);types=[types] if isinstance(types,str) else types
        if 'object' in types or 'properties' in schema or 'required' in schema or 'additionalProperties' in schema:
            if 'properties' not in schema or type(schema.get('additionalProperties')) is not bool:raise ValueError('Explicit objects required')
            if set(schema.get('required',[]))-schema['properties'].keys():raise ValueError('Unknown required field')
        if 'array' in types and 'items' not in schema:raise ValueError('Array items required')
        for key,definition in schema.get('properties',{}).items():
            if not re.fullmatch(r'[a-z][A-Za-z0-9]{0,63}',key):raise ValueError('Invalid business field')
            if not isinstance(definition,dict):raise ValueError('Field descriptions required')
            description(definition.get('description'))
            if 'type' not in definition and '$ref' not in definition:raise ValueError('Explicit field type required')
        for keyword in ('properties','$defs','patternProperties','dependentSchemas'):
            for child in schema.get(keyword,{}).values():walk(child,root)
        for keyword in ('allOf','anyOf','oneOf','prefixItems'):
            for child in schema.get(keyword,[]):walk(child,root)
        for keyword in ('items','contains','not','if','then','else','propertyNames','unevaluatedProperties','unevaluatedItems'):
            if keyword in schema:walk(schema[keyword],root)
    if not isinstance(rows,dict):raise ValueError('Expected catalog mapping')
    for identity,binding in rows.items():
        if not isinstance(identity,tuple) or len(identity)!=2 or not isinstance(binding,tuple) or len(binding)!=3:raise ValueError('Invalid catalog entry')
        service,method=identity;desc,_,_=binding
        if not isinstance(service,str) or not isinstance(method,str) or not isinstance(desc,dict):raise ValueError('Invalid catalog identity')
        if set(desc)!={'method','description','inputSchema','outputSchema'} or desc['method']!=method:raise ValueError('Invalid descriptor fields')
        if not SERVICE.fullmatch(service) or len(service)>64 or not METHOD.fullmatch(method) or len(method)>128:raise ValueError('Invalid name')
        description(desc['description'])
        if not 1<=len(desc['description'])<=2048:raise ValueError('Invalid description length')
        if desc['inputSchema'] is None:raise ValueError('Input schema required for every message')
        if (desc['outputSchema'] is None)!=(method.startswith(('Ntf_','Et_','Dat_'))):raise ValueError('Invalid output mode')
        for schema in (desc['inputSchema'],desc['outputSchema']):
            if schema is not None:
                if not isinstance(schema,dict) or schema.get('type')!='object':raise ValueError('Root must be an object schema')
                Draft202012Validator.check_schema(schema);walk(schema,schema)

class MCI:
    def __init__(self,service,authorize=None):
        self.service=service
        # Trusted native loopback operator only; caller cannot select an identity.
        self.authorize=authorize or (lambda action,identity:True)
        self.rows=definitions();validate_catalog(self.rows)
        self.lock=threading.RLock()
    def publish(self,rows):
        candidate=copy.deepcopy(rows)
        validate_catalog(candidate)
        with self.lock:self.rows=candidate
    @staticmethod
    def error(code,message):return dict(error=dict(code=code,message=str(message)))
    def discover(self,params):
        if not self.authorize('discover',None):return self.error('PERMISSION_DENIED','Discovery denied')
        if not isinstance(params,dict) or set(params)-{'service','method'}:return self.error('INVALID_ARGUMENT','Unknown discovery parameters')
        for key,pattern in [('service',SERVICE),('method',METHOD)]:
            if key in params and (not isinstance(params[key],str) or not pattern.fullmatch(params[key]) or len(params[key])>(64 if key=='service' else 128)):
                return self.error('INVALID_ARGUMENT','Invalid '+key)
        try:
            with self.lock:
                validate_catalog(self.rows)
                services={}
                for (service,method),(desc,_,_) in sorted(self.rows.items()):
                    if any(params.get(k,v)!=v for k,v in [('service',service),('method',method)]):continue
                    if self.authorize('visible',(service,method)):services.setdefault(service,[]).append(copy.deepcopy(desc))
                result=dict(specVersion=VERSION,services=[dict(service=k,methods=v) for k,v in services.items()])
            if len(json.dumps(result).encode())>1024*1024:return self.error('CATALOG_TOO_LARGE','Catalog exceeds 1 MiB')
            return result
        except (ValueError,ValidationError,SchemaError):return self.error('CATALOG_INVALID','Invalid method catalog')
    def call(self,packet):
        try:
            if not isinstance(packet,dict) or set(packet)-{'service','method','params','target','requestId','deadlineUnix'}:raise ValueError('Invalid call envelope')
            key=(packet.get('service'),packet.get('method'))
            if any(not isinstance(x,str) for x in key):raise ValueError('Invalid method identity')
            if key not in self.rows:raise ValueError('Unknown method')
            if not self.authorize('invoke',key):return self.error('PERMISSION_DENIED','Invocation denied')
            desc,operation,extra=self.rows[key]
            if operation is None:raise ValueError('One-way messages cannot be invoked')
            params=packet.get('params');Draft202012Validator(desc['inputSchema']).validate(params)
            if not isinstance(packet.get('requestId'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',packet['requestId']):raise ValueError('Invalid requestId')
            import time
            deadline=packet.get('deadlineUnix')
            if type(deadline) not in (int,float) or not time.time()<=deadline<=time.time()+60:raise ValueError('Invalid deadlineUnix')
            target=packet.get('target')
            device=key[0] in ('Mesh_Admission','Mesh_Parent') or operation=='command'
            if device and (not isinstance(target,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',target)):raise ValueError('Device target required')
            if not device and target is not None:raise ValueError('This method is routed to the local backend')
            request=dict(v=1,type=operation,msg_id=packet['requestId'],deadline_unix=deadline,**convert(params),**extra)
            if device:request['target']=target
            if operation=='task.update' and 'config' in params:
                with self.service.tasks.store.lock:
                    task=self.service.tasks.store._row(params['taskId'],'http-local')
                Draft202012Validator(CONFIGS[task['kind']]).validate(params['config'])
            if operation=='catalog':business=dict(nodes=self.service.catalog.records())
            else:
                replies=self.service.submit_local(request)
                error=next((r for r in replies if r.get('type')=='error' or r.get('ok') is False),None)
                if error:return self.error('BUSINESS_ERROR',error.get('error','Operation rejected'))
                reply=replies[0]
                if operation=='list':business={('instances' if extra else 'nodes'):[n for row in replies for n in row.get('nodes',[])]}
                elif operation=='command':business=dict(acknowledged=True) if extra['op']=='ping' else (dict(text=reply.get('payload')) if extra['op']=='echo' else reply.get('payload'))
                else:business=reply
            result=project(business,desc['outputSchema'])
            try:
                Draft202012Validator(desc['outputSchema']).validate(result)
                if 'task' in result:
                    task=result['task']
                    Draft202012Validator(CONFIGS[task['kind']]).validate(task['config'])
            except ValidationError:return self.error('OUTPUT_INVALID','Executor output violates the published contract; query state before retrying')
            return dict(result=result)
        except (ValueError,ValidationError,TypeError) as exc:return self.error('INVALID_ARGUMENT',str(exc))
        except (OSError,TimeoutError):return self.error('INTERNAL_ERROR','Operation uncertain; query existing state before retrying')
    def notification(self,service,method,payload):
        cursor=payload.get('cursor') if method=='Ntf_TaskChanged' else None
        schema=self.rows[service,method][0]['inputSchema'];payload=project(payload,schema)
        Draft202012Validator(schema).validate(payload)
        result=dict(service=service,method=method,params=payload)
        if cursor is not None:result['cursor']=cursor
        return result
