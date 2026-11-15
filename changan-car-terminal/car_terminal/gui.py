"""Local desktop debugger using the car terminal's existing v1 business API."""
import argparse
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .client import MQTTClient, SerialClient, request_line
from .protocol import NODE_ID
from .tasks import TaskClient
from .network import NetworkPanel


def open_transport(settings):
    if settings['transport'] == 'serial':
        if not settings['port'].strip():
            raise ValueError('请填写 root 车机串口，例如 COM7')
        return SerialClient(settings['port'].strip())
    if not settings['host'].strip() or not settings['cert_dir'].strip():
        raise ValueError('MQTT 需要 Broker 地址和车机证书目录')
    return MQTTClient(settings['host'].strip(), int(settings['broker_port']),
                      settings['node_id'].strip(), Path(settings['cert_dir']),
                      settings['server_name'].strip())


def run_operation(client, action, values):
    """One serialized operation; mutations are never retried automatically."""
    api = TaskClient(client)
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
    if action == 'create':
        node = values['target'].strip()
        if not NODE_ID.fullmatch(node):
            raise ValueError('请选择或填写有效节点 ID')
        duration, period = int(values['duration']), int(values['period'])
        if not 1 <= duration <= 3600 or not 200 <= period <= 10000:
            raise ValueError('持续时间应为 1–3600 秒，采样间隔为 200–10000 毫秒')
        return api.create(node, duration, period)
    if action in ('get', 'start', 'pause', 'resume', 'cancel'):
        task_id = values['task_id'].strip()
        if not task_id:
            raise ValueError('请先选择任务或填写任务 ID')
        if action == 'get':
            return api.get(task_id)
        revision = values.get('revision')
        if revision is None:
            raise ValueError('请先查询任务，取得当前版本再控制')
        return api.control(task_id, action, int(revision))
    if action in ('tasks', 'events'):
        cursor = values.get('cursor', 0) if action == 'events' else 0
        items = []
        # Bounded batches keep disconnect and user operations responsive.
        limit = 50 if action == 'events' else 512
        for _ in range(limit):
            result = api.events(cursor) if action == 'events' else api.list(cursor)
            items.extend(result['items'])
            next_cursor = result['cursor']
            if result.get('more') and next_cursor <= cursor:
                raise ValueError('后台分页游标未前进')
            cursor = next_cursor
            if not result.get('more'):
                break
        else:
            if action == 'tasks':
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
                        result = None
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
              status='节点状态', echo='Echo', create='创建诊断任务', tasks='刷新任务',
              get='查询任务', start='开始任务', pause='暂停任务', resume='恢复任务',
              cancel='取消任务', events='补查事件')


class DebugWindow:
    def __init__(self, root, defaults=None, worker=None):
        self.root = root
        self.worker = worker or SessionWorker()
        self.connected = False
        self.busy = False
        self.closed = False
        self.cursor = 0
        self.task_rows = {}
        self.records = deque(maxlen=2000)
        self.operation_buttons = []
        self.settings_widgets = []
        self.values = {}
        initial = dict(transport='serial', port='COM7', host='127.0.0.1', broker_port='8883',
                       node_id='pc-root-001', cert_dir='', server_name='ugv-broker.lab',
                       target='', echo='hello', duration='30', period='1000', task_id='')
        initial.update(defaults or {})
        for key, value in initial.items():
            self.values[key] = tk.StringVar(root, value=str(value))
        self.watch = tk.BooleanVar(root, value=False)
        self.state = tk.StringVar(root, value='未连接 · 选择传输方式后点击连接')
        self.summary = tk.StringVar(root, value='等待操作')
        self.revision = tk.StringVar(root, value='版本：—')
        root.title('长安车机 · M1 调试终端')
        root.geometry('1160x820')
        root.minsize(980, 720)
        style = ttk.Style(root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10))
        style.configure('Treeview', rowheight=27)
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 17, 'bold'))
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
        tabs.add(tasks, text='  诊断任务  ')
        tabs.add(network, text='  网络结构  ')
        self._nodes(nodes)
        self._tasks(tasks)
        self.network = NetworkPanel(network, lambda: self.dispatch('nodes'),
                                    lambda node: self.values['target'].set(node))
        self.operation_buttons.append(self.network.refresh_button)
        self._output(panes)
        self._states()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(80, self._drain)
        root.after(1500, self._watch_tick)

    def _field(self, frame, title, key, row, col, width=18, choices=None):
        ttk.Label(frame, text=title).grid(row=row, column=col, sticky='w', padx=(0, 6), pady=4)
        if choices:
            widget = ttk.Combobox(frame, textvariable=self.values[key], values=choices,
                                  state='readonly', width=width)
        else:
            widget = ttk.Entry(frame, textvariable=self.values[key], width=width)
        widget.grid(row=row, column=col + 1, sticky='ew', padx=(0, 14), pady=4)
        return widget

    def _connection(self, parent):
        box = ttk.LabelFrame(parent, text='连接设置', padding=10)
        box.pack(fill='x')
        definitions = [('传输', 'transport', 0, 0, 10, ('serial', 'mqtt')),
                       ('root 串口', 'port', 0, 2, 12, None),
                       ('Broker 地址', 'host', 0, 4, 18, None),
                       ('端口', 'broker_port', 0, 6, 7, None),
                       ('车机身份', 'node_id', 1, 0, 16, None),
                       ('TLS 服务名', 'server_name', 1, 2, 18, None),
                       ('证书目录', 'cert_dir', 1, 4, 22, None)]
        for definition in definitions:
            self.settings_widgets.append(self._field(box, *definition))
        self.browse_button = ttk.Button(box, text='选择…', command=self._browse)
        self.browse_button.grid(row=1, column=6, columnspan=2, sticky='w')
        self.settings_widgets.append(self.browse_button)
        actions = ttk.Frame(box)
        actions.grid(row=2, column=0, columnspan=8, sticky='ew', pady=(6, 0))
        self.connect_button = ttk.Button(actions, text='连接', style='Accent.TButton',
                                          command=lambda: self.dispatch('connect'))
        self.connect_button.pack(side='left')
        self.disconnect_button = ttk.Button(actions, text='断开', command=lambda: self.dispatch('disconnect'))
        self.disconnect_button.pack(side='left', padx=8)
        ttk.Label(actions, text='串口连接 root C6（通常 COM7）；MQTT 使用车机自身证书。').pack(side='left')
        self.values['transport'].trace_add('write', lambda *_: self._states())

    def _button(self, parent, text, action):
        button = ttk.Button(parent, text=text, command=lambda: self.dispatch(action))
        button.pack(side='left', padx=(0, 7), pady=4)
        self.operation_buttons.append(button)
        return button

    def _tree(self, parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, pady=6)
        tree = ttk.Treeview(frame, columns=[key for key, _, _ in columns], show='headings', selectmode='browse', height=6)
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=60)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
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
        self.nodes.bind('<<TreeviewSelect>>', self._select_node)
        echo = ttk.Frame(parent)
        echo.pack(fill='x')
        ttk.Label(echo, text='Echo 内容').pack(side='left', padx=(0, 8))
        ttk.Entry(echo, textvariable=self.values['echo']).pack(side='left', fill='x', expand=True, padx=(0, 10))
        self._button(echo, '发送 Echo', 'echo')
        ttk.Label(parent, text='节点状态来自手动刷新；详细响应显示在下方结果区。').pack(anchor='w')

    def _tasks(self, parent):
        create = ttk.Frame(parent)
        create.pack(fill='x')
        self._field(create, '持续时间 / 秒', 'duration', 0, 0, 8)
        self._field(create, '采样间隔 / ms', 'period', 0, 2, 8)
        buttons = ttk.Frame(create)
        buttons.grid(row=0, column=4)
        self._button(buttons, '为目标节点创建', 'create')
        self._button(buttons, '刷新任务', 'tasks')
        ttk.Checkbutton(buttons, text='持续补查事件', variable=self.watch).pack(side='left')
        ttk.Label(parent, textvariable=self.values['target']).pack(anchor='w')
        self.tasks = self._tree(parent, [('task_id', '任务 ID', 270), ('target', '目标', 145),
                                         ('state', '状态', 135), ('progress', '进度 %', 80),
                                         ('revision', '版本', 60), ('error', '错误', 160)])
        self.tasks.bind('<<TreeviewSelect>>', self._select_task)
        action = ttk.Frame(parent)
        action.pack(fill='x')
        ttk.Label(action, text='任务 ID').pack(side='left', padx=(0, 6))
        ttk.Entry(action, textvariable=self.values['task_id'], width=34).pack(side='left', padx=(0, 8))
        ttk.Label(action, textvariable=self.revision).pack(side='left', padx=(0, 10))
        for text, op in [('查询', 'get'), ('开始', 'start'), ('暂停', 'pause'), ('恢复', 'resume'), ('取消', 'cancel')]:
            self._button(action, text, op)
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
                                               font=('Consolas', 10), background='#152332', foreground='#e1eaf4')
        self.output.pack(fill='both', expand=True, pady=(6, 0))
        self.output.tag_configure('error', foreground='#ff9696')
        self.output.tag_configure('success', foreground='#8de0b2')

    def _states(self):
        available = self.connected and not self.busy
        for button in self.operation_buttons:
            button.configure(state='normal' if available else 'disabled')
        self.connect_button.configure(state='normal' if not self.connected and not self.busy else 'disabled')
        self.disconnect_button.configure(state='normal' if available else 'disabled')
        serial = self.values['transport'].get() == 'serial'
        for index, widget in enumerate(self.settings_widgets):
            enabled = not self.connected and not self.busy
            if index == 1:
                enabled = enabled and serial
            elif index >= 2:
                enabled = enabled and not serial
            widget.configure(state=('readonly' if index == 0 else 'normal') if enabled else 'disabled')

    def _browse(self):
        path = filedialog.askdirectory(parent=self.root, title='选择包含 ca.pem / client.pem / client.key 的目录')
        if path:
            self.values['cert_dir'].set(path)

    def _select_node(self, _=None):
        selected = self.nodes.selection()
        if selected:
            self.values['target'].set(self.nodes.item(selected[0], 'values')[0])

    def _select_task(self, _=None):
        selected = self.tasks.selection()
        if selected:
            task_id = self.tasks.item(selected[0], 'values')[0]
            self.values['task_id'].set(task_id)

    def _show_revision(self):
        row = self.task_rows.get(self.values['task_id'].get(), {})
        self.revision.set('版本：' + str(row.get('revision', '—')))

    def dispatch(self, action):
        if self.busy or (action != 'connect' and not self.connected):
            return
        values = {key: value.get() for key, value in self.values.items()}
        values['cursor'] = self.cursor
        values['revision'] = self.task_rows.get(values['task_id'], {}).get('revision')
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
                self.busy = False
                if action == 'connect' and ok:
                    self.connected = True
                    self.cursor = 0
                    self.task_rows.clear()
                    self.nodes.delete(*self.nodes.get_children())
                    self.network.clear()
                    self.tasks.delete(*self.tasks.get_children())
                    self.values['task_id'].set('')
                    self.target_box.configure(values=())
                    self.state.set('链路已打开 · 点击刷新节点验证后台响应')
                elif action == 'disconnect':
                    self.connected = False
                    self.watch.set(False)
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
                self._states()
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _apply(self, action, result):
        if action == 'nodes':
            self.network.update(result)
            self.nodes.delete(*self.nodes.get_children())
            ids = []
            for row in result:
                ids.append(row['node_id'])
                status = row.get('status') or {}
                self.nodes.insert('', 'end', values=(row['node_id'],
                    {True: '是', False: '否'}.get(row.get('ready'), '未知'),
                    row.get('role', status.get('role', '—')), ', '.join(row.get('operations', []))))
            self.target_box.configure(values=ids)
            if ids and self.values['target'].get() not in ids:
                self.values['target'].set(ids[0])
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

    def _upsert_task(self, task):
        task_id = task['task_id']
        previous = self.task_rows.get(task_id, {})
        if task.get('state_seq', 0) < previous.get('state_seq', 0):
            return
        row = dict(previous, **task)
        self.task_rows[task_id] = row
        values = tuple(row.get(key, '—') for key in ('task_id', 'target', 'state', 'progress', 'revision', 'error'))
        if self.tasks.exists(task_id):
            self.tasks.item(task_id, values=values)
        else:
            self.tasks.insert('', 'end', iid=task_id, values=values)
        self._show_revision()

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
        if self.watch.get() and self.connected and not self.busy:
            self.dispatch('events')
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
        self.worker.submit('stop')
        for callback in self.root.tk.splitlist(self.root.tk.call('after', 'info')):
            self.root.after_cancel(callback)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description='车机 M1 桌面调试界面；打开后手动连接')
    parser.add_argument('--transport', choices=('serial', 'mqtt'), default='serial')
    parser.add_argument('--port', default='COM7')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--broker-port', type=int, default=8883)
    parser.add_argument('--node-id', default='pc-root-001')
    parser.add_argument('--cert-dir', default='')
    parser.add_argument('--server-name', default='ugv-broker.lab')
    root = tk.Tk()
    DebugWindow(root, vars(parser.parse_args()))
    root.mainloop()


if __name__ == '__main__':
    main()
