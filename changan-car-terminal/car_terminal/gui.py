"""Local desktop debugger using the car terminal's existing v1 business API."""
import argparse
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import queue
import threading
import time
import uuid
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, scrolledtext, ttk

from .client import HTTPClient, request_line
from .protocol import NODE_ID
from .tasks import TaskClient
from .network import NetworkPanel

TASK_KINDS = {'网络诊断': 'network_diagnostics', '任务运行监视': 'task_monitor',
              '区域巡检（ESP32测试）':'patrol','异常复核（ESP32测试）':'anomaly_review','基础诊断（兼容）': 'diagnostics'}
SERVICE_NAMES = {'network_diagnostics':'网络诊断','task_monitor':'任务运行监视','patrol':'区域巡检流程验证','anomaly_review':'巡检异常复核流程验证'}
STAGES={'point_check':'测试点位验证','receive_event':'接收测试事件','validate_input':'校验测试输入','test_result':'生成测试结果','test_done':'测试流程完成'}
TASK_STATES={'IDLE':'空闲','CREATED':'已创建','QUEUED':'排队中','DISPATCHING':'下发中','ACCEPTED':'已受理','RUNNING':'执行中','PAUSED':'已暂停','UNKNOWN':'待确认','RECONCILING':'对账中'}
HEALTH = {'waiting':'等待执行', 'reporting':'反馈正常', 'feedback_stale':'反馈超时',
          'node_not_ready':'节点未就绪', 'finished':'任务已结束', 'not_authorized':'授权已失效', 'not_found':'任务不存在'}
UI_FONTS = ('Microsoft YaHei UI', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans')
MONO_FONTS = ('Consolas', 'Noto Sans Mono CJK SC', 'DejaVu Sans Mono')

def ui_font(widget, size, bold=False, mono=False):
    installed = set(tkfont.families(widget))
    family = next((name for name in (MONO_FONTS if mono else UI_FONTS) if name in installed), 'TkDefaultFont')
    return (family, size, 'bold') if bold else (family, size)

def service_result_text(row):
    result = row.get('result') or {}
    stage=STAGES.get(result.get('stage'),result.get('stage') or '等待反馈')
    if row.get('kind') in ('patrol','anomaly_review') or result.get('mode') == 'esp32_test' and 'health' not in result:
        if row.get('kind') == 'patrol' or 'done' in result:
            return (f"ESP32 测试流程 · 阶段：{stage}  测试点位：{result.get('point','—')}  "
                    f"已验证：{result.get('done',0)}/{result.get('total','—')}  测试事件：{result.get('event_id') or '无'}")
        verdict={'confirmed':'确认异常（测试）','cleared':'解除误报（测试）','inconclusive':'待进一步核验（测试）','pending':'等待测试结果'}
        return f"ESP32 测试复核 · 阶段：{stage}  事件：{result.get('event_id','—')}  结论：{verdict.get(result.get('verdict'),'等待反馈')}"
    value = lambda key: '—' if result.get(key) is None else result[key]
    if row.get('kind') == 'network_diagnostics' or 'avg_ms' in result:
        return (f"检查节点：{result.get('node_id', '—')}  已完成采样：{result.get('samples', 0)}  "
                f"成功：{result.get('ok', 0)}  失败：{result.get('failed', 0)}\n"
                f"主机↔节点往返耗时（ms）  最近：{value('last_ms')}  平均：{value('avg_ms')}  最大：{value('max_ms')}  "
                f"最近错误：{result.get('error') or '无'}")
    if row.get('kind') == 'task_monitor' or 'health' in result:
        return (f"被监视任务：{result.get('task_id', '—')}  执行节点：{result.get('target', '—')}\n"
                f"状态：{result.get('state', '—')}  进度：{result.get('progress', '—')}%  "
                f"距有效反馈：{value('age_s')} 秒  监视结果：{HEALTH.get(result.get('health'), '等待采样')}  "
                f"任务错误：{result.get('error') or '无'}  执行模式：{result.get('mode','—')}  阶段：{stage}")
    return '选择任务后查询，或勾选持续补查事件，查看服务运行结果。'


def open_transport(settings):
    return HTTPClient(settings.get('base_url','http://127.0.0.1:8080').strip())


def run_operation(client, action, values):
    """One serialized operation; mutations are never retried automatically."""
    api = TaskClient(client)
    if action.startswith('cap_'):
        batch=values.get('cap_batch','').strip()
        if action=='cap_start':
            nodes=[n.strip() for n in values.get('cap_nodes','').split(',') if n.strip()]
            if not nodes or len(nodes)>16 or len(set(nodes))!=len(nodes) or any(not NODE_ID.fullmatch(n) for n in nodes):
                raise ValueError('请填写1～16个不同节点ID，以逗号分隔')
            count=int(values.get('cap_count','30'));period=int(values.get('cap_period','1000'))
            if not 1<=count<=100 or not 200<=period<=10000:raise ValueError('每节点1～100条，间隔200～10000ms')
            return client.capability_test('start',dict(batch_id=batch,nodes=nodes,count=count,period_ms=period))
        if action=='cap_get':return client.capability_test('get',dict(batch_id=batch))
        if action=='cap_history':return client.capability_test('list')
        if action=='cap_export':
            path=Path(values['cap_export_path']);format='csv' if path.suffix.lower()=='.csv' else 'jsonl'
            content=client.capability_test('export',dict(batch_id=batch,format=format))
            path.write_text(content,encoding='utf-8-sig' if format=='csv' else 'utf-8')
            return dict(path=str(path),batch_id=batch,format=format)
    if action=='mci_methods':return client.discover()
    if action in ('parent_get','parent_apply'):
        node=values['parent_child'].strip()
        if not NODE_ID.fullmatch(node):raise ValueError('请选择Micro节点')
        packet=dict(v=1,type='node.parent.get' if action=='parent_get' else 'node.parent',
                    msg_id=uuid.uuid4().hex,deadline_unix=int(time.time())+20,target=node)
        if action=='parent_apply':
            revision=values.get('parent_revision','')
            if revision=='':raise ValueError('先查询该Micro的连接配置版本')
            mode={'自动':'auto','优先指定':'prefer','固定指定':'fixed'}[values['parent_mode']]
            packet.update(mode=mode,parent=values['parent_uav'].strip() if mode!='auto' else None,expected_revision=int(revision))
        reply=client.request(packet)
        if reply.get('type')=='error':raise ValueError(reply.get('error'))
        return reply
    if action in ('admit','revoke'):
        revision=values.get('admission_revision','')
        if revision=='':raise ValueError('请刷新节点并选择目标，确认授权版本')
        reply=client.request(dict(v=1,type='node.admission',msg_id=uuid.uuid4().hex,
            deadline_unix=int(time.time())+20,target=values['target'],expected_revision=int(revision),
            trust_status='trusted' if action=='admit' else 'revoked'))
        if reply.get('type')=='error':raise ValueError(reply.get('error'))
        return reply
    if action == 'services':
        return api.services()
    if action == 'nodes':
        return request_line(client, 'list')
    if action in ('ping', 'status', 'echo'):
        node = values['target'].strip()
        if not NODE_ID.fullmatch(node):
            raise ValueError('请选择或填写有效节点 ID')
        line = f'{action} {node}'
        if action == 'echo':
            line += ' ' + values['echo']
        result = request_line(client, line)
        if result.get('ok') is False:
            raise ValueError(json.dumps(result, ensure_ascii=False))
        return result
    if action in ('create','update'):
        kind = TASK_KINDS.get(values.get('task_kind'), 'diagnostics')
        node = values['target'].strip() if kind == 'diagnostics' else values['executor'].strip()
        if not NODE_ID.fullmatch(node):
            raise ValueError('请选择或填写有效节点 ID')
        if kind in ('patrol','anomaly_review'):
            if kind == 'patrol':
                points=[p.strip() for p in values['points'].split(',')]
                config=dict(execution_mode='esp32_test',area_id=values['area_id'].strip(),point_ids=points,
                            point_duration_s=int(values['point_seconds']),anomaly_point=int(values['anomaly_point']))
                if (not 1<=len(points)<=3 or len(set(points))!=len(points) or
                    any(not NODE_ID.fullmatch(p) or len(p)>12 for p in [config['area_id'],*points]) or
                    not 1<=config['point_duration_s']<=60 or not 0<=config['anomaly_point']<=len(points)):
                    raise ValueError('测试区域/点位 ID 最多12字符；点位1–3个且不重复，每点1–60秒，异常点序号0–点位数')
            else:
                config=dict(execution_mode='esp32_test',event_id=values['event_id'].strip(),test_verdict=values['test_verdict'],duration_s=int(values['duration']))
                if not NODE_ID.fullmatch(config['event_id']) or config['test_verdict'] not in ('confirmed','cleared','inconclusive') or not 1<=config['duration_s']<=60:
                    raise ValueError('请填写测试事件 ID、预设结论及1–60秒测试时长')
            if action=='update':
                if values.get('revision') is None:raise ValueError('请先查询任务版本')
                return api.update_config(values['task_id'],int(values['revision']),config)
            return api.create_config(node,kind,config)
        duration, period = int(values['duration']), int(values['period'])
        if not 1 <= duration <= 3600 or not 200 <= period <= 10000:
            raise ValueError('持续时间应为 1–3600 秒，采样间隔为 200–10000 毫秒')
        if action=='update':
            if values.get('revision') is None:raise ValueError('请先查询任务版本')
            config=dict(duration_s=duration,period_ms=period)
            if kind=='network_diagnostics':config['probe_node']=values['target'].strip()
            if kind=='task_monitor':config.update(watch_task_id=values['watch_task_id'].strip(),stale_after_s=int(values['stale_after']))
            return api.update_config(values['task_id'],int(values['revision']),config)
        if action=='update':
            if values.get('revision') is None:raise ValueError('请先查询任务版本')
            return api.update(values['task_id'],int(values['revision']),duration,period)
        if kind == 'network_diagnostics':
            subject = values['target'].strip()
            if not NODE_ID.fullmatch(subject):raise ValueError('请选择被检查节点')
            return api.network(node, subject, duration, period)
        if kind == 'task_monitor':
            subject = values['watch_task_id'].strip()
            if not NODE_ID.fullmatch(subject):raise ValueError('请填写被监视任务 ID')
            stale = int(values['stale_after'])
            if not 1 <= stale <= 3600:raise ValueError('反馈超时阈值应为 1–3600 秒')
            return api.monitor(node, subject, duration, period, stale)
        return api.create(node, duration, period)
    if action in ('get', 'start', 'pause', 'resume', 'cancel', 'delete'):
        task_id = values['task_id'].strip()
        if not task_id:
            raise ValueError('请先选择任务或填写任务 ID')
        if action == 'get':
            return api.get(task_id)
        revision = values.get('revision')
        if revision is None:
            raise ValueError('请先查询任务，取得当前版本再控制')
        if action == 'delete':
            if values.get('task_state') not in ('SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED'):
                raise ValueError('只能删除已结束的历史任务；请先查询任务状态')
            return api.delete(task_id, int(revision))
        return api.control(task_id, action, int(revision))
    if action in ('tasks', 'events','incidents'):
        cursor = values.get('cursor', 0) if action == 'events' else 0
        items = []
        # Bounded batches keep disconnect and user operations responsive.
        limit = 50 if action == 'events' else 512
        for _ in range(limit):
            result = api.events(cursor) if action == 'events' else (api.incidents(cursor) if action=='incidents' else api.list(cursor))
            items.extend(result['items'])
            next_cursor = result['cursor']
            if result.get('more') and next_cursor <= cursor:
                raise ValueError('后台分页游标未前进')
            cursor = next_cursor
            if not result.get('more'):
                break
        else:
            if action in ('tasks','incidents'):
                raise ValueError('任务超过 512 条，请使用 CLI 分页查询')
        return dict(result, items=items, cursor=cursor)
    raise ValueError('不支持的调试操作')


class SessionWorker:
    """Owns the transport on a single thread; never touches Tk widgets."""
    def __init__(self, factory=open_transport):
        self.factory = factory
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        self.thread = threading.Thread(target=self._run, name='car-debug', daemon=True)
        self.thread.start()

    def submit(self, action, values=None):
        self.jobs.put((action, values or {}))

    def _run(self):
        client = None
        try:
            while True:
                action, values = self.jobs.get()
                started = time.monotonic()
                try:
                    if action in ('disconnect', 'stop'):
                        if client is not None:
                            old, client = client, None
                            old.close()
                        if action == 'stop':
                            return
                        result = None
                    elif action == 'connect':
                        if client is not None:
                            raise ValueError('请先断开当前连接')
                        client = self.factory(values)
                        if isinstance(client,HTTPClient):
                            client.on_event=lambda body:self.results.put(('push',True,body,0))
                            client.on_wire=lambda body:self.results.put(('wire',True,body,0))
                        result=dict(root_id=getattr(client,'root_id',None))
                    else:
                        if client is None:
                            raise ConnectionError('尚未连接')
                        result = run_operation(client, action, values)
                    self.results.put((action, True, result, time.monotonic() - started))
                except Exception as exc:
                    self.results.put((action, False, str(exc), time.monotonic() - started))
                    if action == 'stop':
                        return
        finally:
            if client is not None:
                client.close()


LABELS = dict(connect='连接', disconnect='断开', nodes='刷新节点', ping='Ping',
              cap_start='开始能力公告测试',cap_get='查询公告测试',cap_history='公告测试历史',cap_export='导出公告测试',
              wire='MCI 原始报文',mci_methods='查看 MCI 方法',
              admit='授权接入',revoke='撤销授权',
              parent_get='查询连接配置',parent_apply='应用连接配置',
              status='节点状态', echo='Echo', create='创建服务任务', tasks='刷新任务', services='刷新服务',
              get='查询任务', start='开始任务', pause='暂停任务', resume='恢复任务',
              cancel='取消任务', events='补查事件', delete='删除历史任务',incidents='刷新测试事件',update='更新任务配置')


class DebugWindow:
    def __init__(self, root, defaults=None, worker=None):
        self.root = root
        self.worker = worker or SessionWorker()
        self.connected = False
        self.busy = False
        self.closed = False
        self.cursor = 0
        self.task_rows = {}
        self.node_rows = {}
        self.deleted_tasks = set()
        self.service_rows = {}
        self.records = deque(maxlen=2000)
        self.operation_buttons = []
        self.admission_buttons = []
        self.settings_widgets = []
        self.values = {}
        self._target_initialized = False
        initial = dict(parent_child='',parent_uav='',parent_mode='自动',parent_revision='',base_url='http://127.0.0.1:8080',
                       cap_nodes='',cap_count='30',cap_period='1000',cap_batch='',
                       target='', admission_revision='', echo='hello', duration='30', period='1000', task_id='',
                       executor='ugv-root', task_kind='网络诊断', watch_task_id='', stale_after='10',
                       area_id='A01',points='P01,P02,P03',point_seconds='3',anomaly_point='2',event_id='',test_verdict='inconclusive')
        initial.update(defaults or {})
        for key, value in initial.items():
            self.values[key] = tk.StringVar(root, value=str(value))
        self.watch = tk.BooleanVar(root, value=False)
        self.cap_watch=tk.BooleanVar(root,value=False)
        self.cap_summary=tk.StringVar(root,value='尚未测试；记录接收确认耗时，作为单向接收延迟上界。')
        self._cap_poll_turn=False
        self.cap_running=False
        self.state = tk.StringVar(root, value='未连接 · 选择传输方式后点击连接')
        self.summary = tk.StringVar(root, value='等待操作')
        self.revision = tk.StringVar(root, value='版本：—')
        self.metrics = tk.StringVar(root, value='选择任务以查看运行结果')
        root.title('长安车机 · M1 调试终端')
        root.geometry('1160x820')
        root.minsize(980, 720)
        style = ttk.Style(root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('.', font=ui_font(root, 10))
        style.configure('Treeview', rowheight=27)
        style.configure('Title.TLabel', font=ui_font(root, 17, bold=True))
        style.configure('Accent.TButton', padding=(13, 6))
        outer = ttk.Frame(root, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='车机调试台', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, textvariable=self.state).pack(anchor='w', pady=(4, 10))
        self._connection(outer)
        panes = ttk.Panedwindow(outer, orient='vertical')
        panes.pack(fill='both', expand=True, pady=(10, 0))
        top = ttk.Frame(panes)
        panes.add(top, weight=3)
        tabs = ttk.Notebook(top)
        tabs.pack(fill='both', expand=True)
        nodes = ttk.Frame(tabs, padding=10)
        tasks = ttk.Frame(tabs, padding=10)
        network = ttk.Frame(tabs, padding=10)
        tabs.add(nodes, text='  节点调试  ')
        tabs.add(tasks, text='  服务任务  ')
        tabs.add(network, text='  网络结构  ')
        self._nodes(nodes)
        self.task_page=tasks
        task_canvas=tk.Canvas(tasks,highlightthickness=0)
        task_scroll=ttk.Scrollbar(tasks,orient='vertical',command=task_canvas.yview)
        task_canvas.configure(yscrollcommand=task_scroll.set)
        task_scroll.pack(side='right',fill='y');task_canvas.pack(side='left',fill='both',expand=True)
        task_content=ttk.Frame(task_canvas)
        task_window=task_canvas.create_window((0,0),window=task_content,anchor='nw')
        task_content.bind('<Configure>',lambda _:task_canvas.configure(scrollregion=task_canvas.bbox('all')))
        task_canvas.bind('<Configure>',lambda e:task_canvas.itemconfigure(task_window,width=e.width))
        self._tasks(task_content)
        services = ttk.Frame(tabs, padding=10)
        tabs.add(services, text='  能力服务  ')
        cap_page=ttk.Frame(tabs,padding=10)
        tabs.add(cap_page,text='  能力公告验收  ')
        self._capabilities(cap_page)
        self._button(services, '刷新服务', 'services')
        self._button(services, '查看 MCI 方法', 'mci_methods')
        self.services = self._tree(services, [('service_id','服务 ID',260),('node_id','执行节点',130), ('agent_type','智能体类型',110),
            ('service_name','基础能力',190),('execution_mode','执行模式',130), ('availability','可用状态',170), ('task_status','当前任务状态',140)])
        self.services.bind('<<TreeviewSelect>>', self._select_service)
        self.services.bind('<Double-1>',lambda _:tabs.select(tasks))
        ttk.Label(services, text='选择服务带入执行节点和任务类型；双击切换到服务任务。列表由后台查询汇总。').pack(anchor='w')
        incidents=ttk.Frame(tabs,padding=10)
        tabs.add(incidents,text='  测试异常事件  ')
        self._button(incidents,'刷新测试事件','incidents')
        self.incidents=self._tree(incidents,[('event_id','测试事件 ID',260),('source_task_id','来源巡检任务',260),('node_id','来源节点',130),('area_id','测试区域',100),('point_id','测试点位',100)])
        self.incidents.bind('<<TreeviewSelect>>',self._select_incident)
        self.incidents.bind('<Double-1>',lambda _:tabs.select(tasks))
        ttk.Label(incidents,text='选择事件后可创建 UAV 异常复核测试任务；事件与结论均为 ESP32 流程验证数据。').pack(anchor='w')
        self.network = NetworkPanel(network, lambda: self.dispatch('nodes'),
                                    lambda node: self.values['target'].set(node))
        parent_box=ttk.LabelFrame(network,text='Micro 上游连接设置',padding=8)
        self.parent_controls=parent_box
        parent_box.pack(fill='x',before=self.network.tree.master)
        self.parent_child_box=self._field(parent_box,'Micro节点','parent_child',0,0,16,(),editable=True)
        self.parent_uav_box=self._field(parent_box,'父UAV','parent_uav',0,2,16,(),editable=True)
        self._field(parent_box,'模式','parent_mode',1,0,12,('自动','优先指定','固定指定'))
        buttons=ttk.Frame(parent_box);buttons.grid(row=1,column=2,columnspan=2,sticky='w')
        self._button(buttons,'查询配置','parent_get');self._button(buttons,'应用配置','parent_apply')
        self.parent_summary=tk.StringVar(root,value='先刷新节点，再查询Micro配置。固定模式不自动改连其他UAV。')
        ttk.Label(parent_box,textvariable=self.parent_summary,wraplength=950).grid(row=2,column=0,columnspan=4,sticky='w')
        self.values['parent_child'].trace_add('write',lambda *_:self.values['parent_revision'].set(''))
        self.operation_buttons.append(self.network.refresh_button)
        self._output(panes)
        self._states()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(80, self._drain)
        root.after(1500, self._watch_tick)

    def _field(self, frame, title, key, row, col, width=18, choices=None, editable=False):
        ttk.Label(frame, text=title).grid(row=row, column=col, sticky='w', padx=(0, 6), pady=4)
        if choices is not None:
            widget = ttk.Combobox(frame, textvariable=self.values[key], values=choices,
                                  state='normal' if editable else 'readonly', width=width)
        else:
            widget = ttk.Entry(frame, textvariable=self.values[key], width=width)
        widget.grid(row=row, column=col + 1, sticky='ew', padx=(0, 14), pady=4)
        return widget

    def _connection(self, parent):
        box=ttk.LabelFrame(parent,text='连接后台',padding=10)
        box.pack(fill='x')
        self.settings_widgets.append(self._field(box,'后台 HTTP 地址','base_url',0,0,42))
        self.connect_button=ttk.Button(box,text='连接',command=lambda:self.dispatch('connect'))
        self.connect_button.grid(row=0,column=2,padx=8)
        self.disconnect_button=ttk.Button(box,text='断开',command=lambda:self.dispatch('disconnect'))
        self.disconnect_button.grid(row=0,column=3)

    def _capabilities(self,parent):
        form=ttk.Frame(parent);form.pack(fill='x')
        self._field(form,'节点ID（逗号分隔）','cap_nodes',0,0,60)
        self._field(form,'每节点公告数','cap_count',1,0,8)
        self._field(form,'间隔 / ms','cap_period',1,2,9)
        self.cap_batch_box=self._field(form,'批次ID','cap_batch',2,0,42,(),editable=True)
        bar=ttk.Frame(parent);bar.pack(fill='x')
        start=ttk.Button(bar,text='开始新测试',command=self._start_capability_test)
        start.pack(side='left',padx=(0,7));self.operation_buttons.append(start)
        for label,action in [('查询批次','cap_get'),('历史批次','cap_history')]:self._button(bar,label,action)
        ttk.Checkbutton(bar,text='自动刷新',variable=self.cap_watch).pack(side='left')
        export=ttk.Button(bar,text='导出 CSV / JSONL',command=self._export_capability_test)
        export.pack(side='right');self.operation_buttons.append(export)
        ttk.Label(parent,text='指标：接收确认耗时（单向接收延迟上界）≤800ms；超出上界不能直接认定单向延迟超标。',wraplength=1050).pack(anchor='w',pady=5)
        ttk.Label(parent,textvariable=self.cap_summary,wraplength=1050).pack(anchor='w')
        self.cap_table=self._tree(parent,[('node','节点',110),('seq','轮次',55),('cap_id','公告ID',240),
            ('agent','智能体类型',95),('capabilities','基础能力',160),('task','任务状态',95),
            ('elapsed','确认耗时 ms',105),('state','结果',170),('error','详情',180)])

    def _start_capability_test(self):
        if not self.connected or self.busy:return
        if self.cap_running:
            self.cap_summary.set('当前批次尚未结束，请先查询该批次或等待测量完成。');return
        self.values['cap_batch'].set(uuid.uuid4().hex)
        self.cap_watch.set(True)
        self.dispatch('cap_start')

    def _export_capability_test(self):
        if not self.connected or self.busy:return
        if not self.values['cap_batch'].get():
            messagebox.showerror('请选择批次','先查询要导出的测试批次',parent=self.root);return
        path=filedialog.asksaveasfilename(parent=self.root,title='导出后台持久化的完整批次记录',
            initialfile='capability-'+self.values['cap_batch'].get()+'.jsonl',defaultextension='.jsonl',
            filetypes=[('JSON Lines','*.jsonl'),('CSV','*.csv')])
        if path:
            values={key:value.get() for key,value in self.values.items()};values['cap_export_path']=path
            self.busy=True;self._states();self.worker.submit('cap_export',values)

    def _button(self, parent, text, action):
        button = ttk.Button(parent, text=text, command=lambda: self.dispatch(action))
        button.pack(side='left', padx=(0, 7), pady=4)
        self.operation_buttons.append(button)
        if action in ("admit","revoke"):self.admission_buttons.append(button)
        return button

    def _tree(self, parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, pady=6)
        tree = ttk.Treeview(frame, columns=[key for key, _, _ in columns], show='headings', selectmode='browse', height=6)
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=60)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set)
        tree.grid(row=0,column=0,sticky='nsew');scroll.grid(row=0,column=1,sticky='ns')
        horizontal.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        return tree

    def _nodes(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill='x')
        self._button(bar, '刷新节点', 'nodes')
        # The target entry also accepts manually entered enrolled identities.
        ttk.Label(bar, text='目标节点').pack(side='left', padx=(12, 6))
        self.target_box = ttk.Combobox(bar, textvariable=self.values['target'], width=22)
        self.target_box.pack(side='left', padx=(0, 12))
        self._button(bar, 'Ping', 'ping')
        self._button(bar, '读取状态', 'status')
        self.nodes = self._tree(parent, [('node_id', '节点 ID', 200), ('ready', '就绪', 95),
                                         ('role', '角色', 120), ('operations', '支持操作', 260)])
        self.nodes.configure(columns=('node_id','ready','role','operations','trust','admission_revision'))
        for key,label in (('trust','准入状态'),('admission_revision','授权版本')):
            self.nodes.heading(key,text=label)
            self.nodes.column(key,width=100,minwidth=80)
        self.nodes.bind('<<TreeviewSelect>>', self._select_node)
        echo = ttk.Frame(parent)
        echo.pack(fill='x')
        ttk.Label(echo, text='Echo 内容').pack(side='left', padx=(0, 8))
        ttk.Entry(echo, textvariable=self.values['echo']).pack(side='left', fill='x', expand=True, padx=(0, 10))
        self._button(echo, '发送 Echo', 'echo')
        self._button(echo, '授权接入', 'admit')
        self._button(echo, '撤销授权', 'revoke')
        ttk.Label(parent, text='节点状态来自手动刷新；详细响应显示在下方结果区。').pack(anchor='w')

    def _tasks(self, parent):
        create = ttk.Frame(parent)
        self.task_common=create
        create.pack(fill='x')
        self._field(create, '服务类型', 'task_kind', 0, 0, 18, tuple(TASK_KINDS))
        self._field(create, '执行节点', 'executor', 0, 2, 16)
        self.diagnostic_target_box = self._field(create, '检查/基础诊断节点', 'target', 1, 0, 18, (), editable=True)
        self._field(create, '被监视任务 ID', 'watch_task_id', 1, 2, 34)
        self._field(create, '反馈超时 / 秒', 'stale_after', 0, 4, 8)
        self._field(create, '持续时间 / 秒', 'duration', 2, 0, 8)
        self._field(create, '采样间隔 / ms', 'period', 2, 2, 8)
        buttons = ttk.Frame(create)
        buttons.grid(row=3, column=0, columnspan=6, sticky='w')
        self._button(buttons, '创建任务', 'create')
        self._button(buttons, '刷新任务', 'tasks')
        ttk.Checkbutton(buttons, text='持续补查事件', variable=self.watch).pack(side='left')
        self.tasks = self._tree(parent, [('task_id', '任务 ID', 240), ('target', '执行节点', 120), ('kind','类型',160),
                                         ('state', '状态', 135), ('progress', '进度 %', 80),
                                         ('revision', '版本', 60), ('error', '错误', 160)])
        self.tasks.bind('<<TreeviewSelect>>', self._select_task)
        self.patrol_form=ttk.LabelFrame(parent,text='ESP32 区域巡检测试配置',padding=4)
        self._field(self.patrol_form,'测试区域','area_id',0,0,12)
        self._field(self.patrol_form,'点位（逗号分隔）','points',0,2,24)
        self._field(self.patrol_form,'每点/秒','point_seconds',1,0,8)
        self._field(self.patrol_form,'测试异常点序号（0为无）','anomaly_point',1,2,6)
        self.review_form=ttk.LabelFrame(parent,text='ESP32 异常复核测试配置',padding=4)
        self._field(self.review_form,'测试事件 ID','event_id',0,0,34)
        self._field(self.review_form,'预设测试结论','test_verdict',0,2,16,('confirmed','cleared','inconclusive'))
        self.values['task_kind'].trace_add('write',lambda *_:self._kind_options())
        self._kind_options()
        ttk.Label(parent, textvariable=self.metrics, wraplength=1040, justify='left').pack(anchor='w')
        action = ttk.Frame(parent)
        action.pack(fill='x')
        ttk.Label(action, text='任务 ID').pack(side='left', padx=(0, 6))
        ttk.Entry(action, textvariable=self.values['task_id'], width=34).pack(side='left', padx=(0, 8))
        ttk.Label(action, textvariable=self.revision).pack(side='left', padx=(0, 10))
        for text, op in [('查询', 'get'), ('开始', 'start'), ('暂停', 'pause'), ('恢复', 'resume'), ('取消', 'cancel')]:
            self._button(action, text, op)
        history = ttk.Frame(parent)
        history.pack(fill='x')
        self._button(history, '删除所选历史任务', 'delete')
        self._button(history,'更新所选配置','update')
        ttk.Label(history, text='仅删除已结束任务及其历史；运行中、暂停和未确认任务需先取消。').pack(side='left')
        ttk.Label(parent, text='控制携带已查询的任务版本；冲突或超时显示错误，不自动重发。').pack(anchor='w')
        self.values['task_id'].trace_add('write', lambda *_: self._show_revision())

    def _output(self, panes):
        frame = ttk.LabelFrame(panes, text='调试结果', padding=10)
        panes.add(frame, weight=2)
        bar = ttk.Frame(frame)
        bar.pack(fill='x')
        ttk.Label(bar, textvariable=self.summary).pack(side='left', fill='x', expand=True)
        ttk.Button(bar, text='导出 JSONL', command=self.export).pack(side='right')
        ttk.Button(bar, text='清空', command=self.clear).pack(side='right', padx=8)
        self.output = scrolledtext.ScrolledText(frame, height=12, wrap='word', state='disabled',
                                               font=ui_font(frame, 10, mono=True), background='#152332', foreground='#e1eaf4')
        self.output.pack(fill='both', expand=True, pady=(6, 0))
        self.output.tag_configure('error', foreground='#ff9696')
        self.output.tag_configure('success', foreground='#8de0b2')

    def _states(self):
        available = self.connected and not self.busy
        for button in self.operation_buttons:button.configure(state='normal' if available else 'disabled')
        self.connect_button.configure(state='normal' if not self.connected and not self.busy else 'disabled')
        self.disconnect_button.configure(state='normal' if available else 'disabled')
        for widget in self.settings_widgets:widget.configure(state='normal' if not self.connected and not self.busy else 'disabled')

    def _select_node(self, _=None):
        selected = self.nodes.selection()
        if selected:
            self.values['target'].set(self.nodes.item(selected[0], 'values')[0])
            row=self.node_rows.get(self.values['target'].get(),{})
            self.values['admission_revision'].set(str(row.get('admission_revision','')))

    def _select_task(self, _=None):
        selected = self.tasks.selection()
        if selected:
            task_id = self.tasks.item(selected[0], 'values')[0]
            self.values['task_id'].set(task_id)
            self._load_task_config(self.task_rows.get(task_id,{}))

    def _load_task_config(self, row):
        for title,kind in TASK_KINDS.items():
            if row.get('kind')==kind:self.values['task_kind'].set(title)
        if row.get('target'):self.values['executor'].set(row['target'])
        config=row.get('config')
        if not isinstance(config,dict):return
        kind=row.get('kind')
        for title,value in TASK_KINDS.items():
            if value==kind:self.values['task_kind'].set(title)
        self.values['executor'].set(row['target'])
        mapping={'area_id':'area_id','point_duration_s':'point_seconds','anomaly_point':'anomaly_point',
                 'event_id':'event_id','test_verdict':'test_verdict','duration_s':'duration','period_ms':'period',
                 'watch_task_id':'watch_task_id','stale_after_s':'stale_after','probe_node':'target'}
        for key,value in mapping.items():
            if key in config:self.values[value].set(str(config[key]))
        if 'point_ids' in config:self.values['points'].set(','.join(config['point_ids']))
        if kind=='diagnostics':self.values['target'].set(row['target'])

    def _kind_options(self):
        kind=TASK_KINDS.get(self.values['task_kind'].get())
        for form in (self.patrol_form,self.review_form):form.pack_forget()
        form=self.patrol_form if kind=='patrol' else (self.review_form if kind=='anomaly_review' else None)
        if form:form.pack(fill='x',before=self.tasks.master)
        for widget in self.task_common.winfo_children():
            info=widget.grid_info()
            # grid_remove retains the position, grid_info does not; use remembered positions.
            if info:widget._task_grid=(int(info['row']),int(info['column']))
            row,col=getattr(widget,'_task_grid',(-1,-1))
            hidden=(row==1 and kind in ('patrol','anomaly_review')) or (row==2 and (kind=='patrol' or kind=='anomaly_review' and col in (2,3)))
            if hidden:widget.grid_remove()
            else:widget.grid()

    def _show_revision(self):
        row = self.task_rows.get(self.values['task_id'].get(), {})
        self.revision.set('版本：' + str(row.get('revision', '—')))
        self.metrics.set(service_result_text(row))

    def _select_service(self, _=None):
        selected = self.services.selection()
        if selected:
            service_id = self.services.item(selected[0], 'values')[0]
            row=self.service_rows.get(service_id,{})
            node=row.get('node_id',service_id.rsplit('/',1)[0])
            kind=row.get('service_type',service_id.rsplit('/',1)[1])
            self.values['executor'].set(node)
            for title, value in TASK_KINDS.items():
                if value == kind:self.values['task_kind'].set(title)

    def _select_incident(self, _=None):
        selected=self.incidents.selection()
        if selected:
            self.values['event_id'].set(self.incidents.item(selected[0],'values')[0])
            self.values['task_kind'].set('异常复核（ESP32测试）')
            candidates=[r for r in self.service_rows.values() if r.get('service_type')=='anomaly_review' and r.get('availability')=='available']
            if candidates:self.values['executor'].set(candidates[0]['node_id'])

    def dispatch(self, action):
        if self.busy or (action != 'connect' and not self.connected):
            return
        values = {key: value.get() for key, value in self.values.items()}
        values['cursor'] = self.cursor
        values['revision'] = self.task_rows.get(values['task_id'], {}).get('revision')
        values['task_state'] = self.task_rows.get(values['task_id'], {}).get('state')
        self.busy = True
        self.summary.set(LABELS[action] + '…')
        self._states()
        self.worker.submit(action, values)

    def _drain(self):
        if self.closed:
            return
        try:
            while True:
                action, ok, result, elapsed = self.worker.results.get_nowait()
                if action=='wire':
                    self.record(action,'error' not in result.get('response',{}),result,elapsed)
                    continue
                if action=='push':
                    if self.connected:
                        if result.get('type')=='task.event':
                            self._apply('events',dict(items=[result],cursor=result['cursor']))
                        elif result.get('type')=='nodes.snapshot':
                            self._apply('nodes',result['nodes'])
                    continue
                self.busy = False
                if action == 'connect' and ok:
                    self.connected = True
                    if isinstance(result,dict) and result.get('root_id'):
                        self.values['executor'].set(result['root_id'])
                    self.cursor = 0
                    self.task_rows.clear()
                    self.node_rows.clear()
                    self.deleted_tasks.clear()
                    self.nodes.delete(*self.nodes.get_children())
                    self.network.clear()
                    self.tasks.delete(*self.tasks.get_children())
                    self.services.delete(*self.services.get_children())
                    self.service_rows.clear()
                    self.incidents.delete(*self.incidents.get_children())
                    self.values['task_id'].set('')
                    self.target_box.configure(values=())
                    self.diagnostic_target_box.configure(values=())
                    self._target_initialized = False
                    self.state.set('链路已打开 · 点击刷新节点验证后台响应')
                elif action == 'disconnect':
                    self.connected = False
                    self.watch.set(False)
                    self.cap_watch.set(False)
                    self.state.set('已断开 · 列表保留为历史快照')
                    self.network.mark_stale('连接已断开')
                elif ok:
                    self.state.set('最近响应：' + datetime.now().strftime('%H:%M:%S') + ' · 连接未持续探测')
                    try:
                        self._apply(action, result)
                    except (KeyError, TypeError, ValueError, tk.TclError) as exc:
                        ok, result = False, '响应格式错误：' + str(exc)
                        self.watch.set(False)
                        self.state.set('响应格式异常 · 检查后台协议版本')
                elif action != 'connect':
                    self.watch.set(False)
                    self.state.set('请求失败 · 检查链路及后台；列表为历史快照')
                    self.network.mark_stale('请求失败')
                self.record(action, ok, result, elapsed)
                if not ok and action.startswith('cap_'):self.cap_watch.set(False)
                self._states()
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _apply(self, action, result):
        if action=='cap_history':
            self.cap_batch_box.configure(values=[r['batch_id'] for r in result['items']])
            return
        if action in ('cap_get','cap_start'):
            self.values['cap_batch'].set(result['batch_id'])
            summary=result['summary'];states=summary['states']
            self.cap_running=not summary['complete']
            def number(key):return '—' if summary[key] is None else f'{summary[key]:.2f}'
            percentage=summary.get('proved_percent',100*summary['proved_within_800ms']/max(1,summary['total']))
            self.cap_summary.set(f"计划 {summary['total']} 条 · 已登记 {summary.get('registered',summary['confirmed'])} · 已确认 {summary['confirmed']} · 证明≤800ms {summary['proved_within_800ms']}（{percentage:.1f}%） · "
                f"超时 {states['TIMEOUT']} · 中断 {states['INTERRUPTED']} · 平均/P95/最大 {number('avg_ms')}/{number('p95_ms')}/{number('max_ms')} ms · "
                +(('全部证明≤800ms' if summary.get('all_proved') else '测试结束，证据未全部满足') if summary['complete'] else '测量中'))
            if summary['complete']:self.cap_watch.set(False)
            self.cap_table.delete(*self.cap_table.get_children())
            names={'WAIT':'等待','SENT':'请求已发送','RECEIVED':'公告已登记','PASS':'证明≤800ms',
                   'UPPER_BOUND_EXCEEDED':'上界超过800ms','TIMEOUT':'超时','ERROR':'错误','NOT_READY':'节点未就绪','INTERRUPTED':'重启中断'}
            for row in result['items']:
                self.cap_table.insert('', 'end',values=(row['node_id'],row['ordinal']+1,row.get('cap_id') or '—',row.get('agent_type') or '—',
                    ', '.join(row['basic_capabilities']),row.get('task_status') or '—',
                    '—' if row['elapsed_ms'] is None else f"{row['elapsed_ms']:.3f}",names.get(row['state'],row['state']),row.get('error') or ''))
            return
        if action in ('admit','revoke'):
            self.values['admission_revision'].set(str(result['admission_revision']))
            self.state.set('后台准入状态已保存；Broker ACL 待受控加载')
            self.worker.submit('nodes')
            return
        if isinstance(result, dict) and result.get('deleted') is True:
            self._remove_task(result['task_id'])
        elif action == 'services':
            self.services.delete(*self.services.get_children())
            self.service_rows={row['service_id']:row for row in result}
            for row in result:
                title = {'ugv':'无人车','uav':'无人机','micro_uav':'微型无人机'}.get(row['agent_type'],row['agent_type'])
                mode={'host':'主机执行','esp32_test':'ESP32 测试','not_reported':'未公告'}.get(row.get('execution_mode'),'—')
                availability={'available':'可用','busy':'忙碌','unavailable':'不可用'}.get(row['availability'],row['availability'])
                reason={'firmware_required':'需更新固件/等待公告','node_not_ready':'节点未就绪'}.get(row.get('reason'))
                if reason:availability+=' · '+reason
                self.services.insert('', 'end', values=(row['service_id'],row.get('node_id',row['service_id'].split('/')[0]),title,
                    SERVICE_NAMES.get(row['service_type'],row['service_type']),mode,availability,TASK_STATES.get(row['task_status'],row['task_status'])))
        elif action=='incidents':
            self.incidents.delete(*self.incidents.get_children())
            for row in result['items']:
                self.incidents.insert('', 'end',values=tuple(row.get(key,'—') for key in ('event_id','source_task_id','node_id','area_id','point_id')))
        elif action in ('parent_get','parent_apply','parent_snapshot'):
            if result.get('target')==self.values['parent_child'].get():
                if action!='parent_snapshot':self.values['parent_revision'].set(str(result['revision']))
                if action=='parent_get':
                    self.values['parent_mode'].set({'auto':'自动','prefer':'优先指定','fixed':'固定指定'}[result['mode']])
                    self.values['parent_uav'].set(result.get('parent') or '')
                state={'unconfigured':'尚未配置','pending':'待下发','accepted':'已接收，等待重连确认','applied':'已生效',
                       'fallback':'已回退自动选择','waiting':'等待指定父节点','uncertain':'下发结果待确认',
                       'unconfirmed':'重连结果未确认','rejected':'节点拒绝'}.get(result['state'],result['state'])
                bssid=result.get('actual_bssid')
                actual=next((r['node_id'] for r in self.node_rows.values() if bssid and
                    (r.get('status') or {}).get('ap_mac','').lower()==bssid.lower()),bssid or '未上报')
                self.parent_summary.set(f"版本 {result['revision']} · 期望 {result.get('parent') or '自动'} · {state} · 实际父节点 {actual} · {result.get('error') or ''}")
        elif action == 'nodes':
            self.node_rows={row['node_id']:row for row in result}
            self.parent_child_box.configure(values=[r['node_id'] for r in result if r.get('role',(r.get('status') or {}).get('role'))=='micro_uav'])
            self.parent_uav_box.configure(values=[r['node_id'] for r in result if r.get('role',(r.get('status') or {}).get('role'))=='uav' and r.get('trust_status','trusted')=='trusted'])
            current=self.node_rows.get(self.values['parent_child'].get(),{}).get('parent_policy')
            if current:self._apply('parent_snapshot',current)
            self.network.update(result)
            ids = []
            for row in result:
                identity = row['node_id']
                ids.append(identity)
                status = row.get('status') or {}
                values = (identity,
                    {True: '是', False: '否'}.get(row.get('ready'), '未知'),
                    row.get('role', status.get('role', '—')), ', '.join(row.get('operations', [])), {'trusted':'可信','pending':'待授权','revoked':'已撤销'}.get(row.get('trust_status'),'—'), row.get('admission_revision','—'))
                if self.nodes.exists(identity):
                    self.nodes.item(identity, values=values)
                else:
                    self.nodes.insert('', 'end', iid=identity, values=values)
                self.nodes.move(identity, '', len(ids)-1)
            removed = set(self.nodes.get_children())-set(ids)
            if removed:self.nodes.delete(*removed)
            self.target_box.configure(values=ids)
            self.diagnostic_target_box.configure(values=ids)
            if ids and not self._target_initialized:
                self._target_initialized = True
                if not self.values['target'].get():self.values['target'].set(ids[0])
            row=self.node_rows.get(self.values['target'].get(),{})
            self.values['admission_revision'].set(str(row.get('admission_revision','')))
        elif action == 'status' and isinstance(result.get('payload'), dict):
            identity = result.get('node_id')
            rows = list(self.network.nodes.values())
            for row in rows:
                if row['node_id'] == identity:
                    row['status'] = result['payload']
                    row['status_age_s'] = 0
                    row['status_current_boot'] = True
                    break
            else:
                if identity:
                    rows.append(dict(node_id=identity, status=result['payload']))
            self.network.update(rows)
        elif action == 'tasks':
            self.tasks.delete(*self.tasks.get_children())
            self.task_rows.clear()
            for task in result['items']:
                self._upsert_task(task)
            self._show_revision()
        elif action == 'events':
            self.cursor = result['cursor']
            for event in result['items']:
                if event.get('task_id'):
                    self._upsert_task(event)
        elif isinstance(result, dict) and isinstance(result.get('task'), dict):
            self._upsert_task(result['task'])
            self.values['task_id'].set(result['task']['task_id'])
            if action=='get':self._load_task_config(result['task'])

    def _upsert_task(self, task):
        task_id = task['task_id']
        if task.get('state') == 'DELETED':
            self._remove_task(task_id)
            return
        if task_id in self.deleted_tasks:
            return
        previous = self.task_rows.get(task_id, {})
        if task.get('state_seq', 0) < previous.get('state_seq', 0):
            return
        row = dict(previous, **task)
        self.task_rows[task_id] = row
        values = tuple(row.get(key, '—') for key in ('task_id', 'target', 'kind', 'state', 'progress', 'revision', 'error'))
        if self.tasks.exists(task_id):
            self.tasks.item(task_id, values=values)
        else:
            self.tasks.insert('', 'end', iid=task_id, values=values)
        if self.values['task_id'].get() == task_id:self.metrics.set(service_result_text(row))
        self._show_revision()

    def _remove_task(self, task_id):
        self.deleted_tasks.add(task_id)
        self.task_rows.pop(task_id, None)
        if self.tasks.exists(task_id):
            self.tasks.delete(task_id)
        if self.values['task_id'].get() == task_id:
            self.values['task_id'].set('')

    def record(self, action, ok, result, elapsed):
        stamp = datetime.now().astimezone().isoformat(timespec='seconds')
        record = dict(time=stamp, operation=action, ok=ok, elapsed_ms=round(elapsed * 1000), result=result)
        self.records.append(record)
        title = f"{LABELS[action]} · {'成功' if ok else '失败'} · {record['elapsed_ms']} ms"
        self.summary.set(title)
        text = json.dumps(result, ensure_ascii=False, indent=2) if result is not None else ('链路已打开' if action == 'connect' else '连接已关闭')
        self.output.configure(state='normal')
        self.output.insert('end', f'[{stamp}] {title}\n', 'success' if ok else 'error')
        self.output.insert('end', text + '\n\n')
        # Bound the visible log as well as the export buffer.
        lines = int(self.output.index('end-1c').split('.')[0])
        if lines > 12000:
            self.output.delete('1.0', f'{lines - 10000}.0')
        self.output.see('end')
        self.output.configure(state='disabled')

    def _watch_tick(self):
        if self.closed:
            return
        if self.connected and not self.busy:
            self._cap_poll_turn=not self._cap_poll_turn
            if self.cap_watch.get() and self.values['cap_batch'].get() and (self._cap_poll_turn or not self.watch.get()):
                self.dispatch('cap_get')
            elif self.watch.get():self.dispatch('events')
        self.root.after(1500, self._watch_tick)

    def clear(self):
        self.records.clear()
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.configure(state='disabled')
        self.summary.set('结果已清空')

    def export(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='导出最近 2000 条操作结果',
            defaultextension='.jsonl', initialfile='car-debug-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.jsonl',
            filetypes=[('JSON Lines', '*.jsonl')])
        if path:
            try:
                Path(path).write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in self.records), encoding='utf-8')
                self.summary.set('已导出：' + path)
            except OSError as exc:
                messagebox.showerror('导出失败', str(exc), parent=self.root)

    def close(self):
        self.closed = True
        self.watch.set(False)
        self.cap_watch.set(False)
        self.worker.submit('stop')
        for callback in self.root.tk.splitlist(self.root.tk.call('after', 'info')):
            self.root.after_cancel(callback)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description='车机 M1 桌面调试界面；打开后手动连接')
    parser.add_argument('--base-url',default='http://127.0.0.1:8080')
    root = tk.Tk()
    DebugWindow(root, vars(parser.parse_args()))
    root.mainloop()


if __name__ == '__main__':
    main()
