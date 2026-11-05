"""Native transparent desktop companion, using the same backend as the web UI."""
import json
import math
import os
from pathlib import Path
import random
import sys
import threading
import time
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'data' / 'desktop-python'))
DATA = Path(os.environ.get('FISH_DATA_DIR', ROOT / 'data'))
os.environ.setdefault('XDG_CACHE_HOME', str(DATA / 'desktop-cache'))

from PySide6.QtCore import Qt, QPoint, QRectF, QTimer, QObject, QRunnable, Signal, Slot, QLockFile
from PySide6.QtGui import QActionGroup, QBitmap, QColor, QCursor, QIcon, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QPushButton, QSystemTrayIcon
from local_backend import Backend
from pet_core import Animation


class WorkerSignals(QObject):
    done = Signal(str, object)
    failed = Signal(str, str)


class Worker(QRunnable):
    def __init__(self, kind, function):
        super().__init__()
        self.kind = kind
        self.function = function
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.done.emit(self.kind, self.function())
        except Exception as e:
            self.signals.failed.emit(self.kind, str(e)[:400])


class ChatDialog(QDialog):
    def __init__(self, pet):
        super().__init__(pet, Qt.WindowType.Window)
        self.pet = pet
        self.setWindowTitle('和大肥鱼聊天')
        self.resize(410, 470)
        self.setStyleSheet('QDialog{background:#fafbff} QPlainTextEdit,QLineEdit{background:white;border:1px solid #dce4f0;border-radius:8px;padding:9px;color:#324a6d} QPushButton{background:#365a91;color:white;border:0;border-radius:7px;padding:9px 16px} QLabel{color:#71839c}')
        layout = QVBoxLayout(self)
        self.notice = QLabel('正在检查运行方式……')
        self.connect_button = QPushButton('接入 / 管理 DeepSeek ↗')
        self.connect_button.clicked.connect(self.pet.open_connection)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText('想和她说点什么？')
        self.input.setMaxLength(8000)
        self.send = QPushButton('发送')
        row = QHBoxLayout()
        row.addWidget(self.input)
        row.addWidget(self.send)
        layout.addWidget(self.notice)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.output)
        layout.addLayout(row)
        self.send.clicked.connect(self.submit)
        self.input.returnPressed.connect(self.submit)

    def submit(self):
        text = self.input.text().strip()
        if not text or self.pet.chat_pending:
            return
        if not self.pet.ready:
            self.pet.say('正在连接本机服务，消息还在输入框里，请稍后发送。')
            self.pet.work('connect', self.pet.backend.connect)
            return
        self.retry_text = text
        self.input.clear()
        self.output.setPlainText(self.output.toPlainText() + '\n你：' + text + '\n')
        self.pet.send_chat(text)

    def append(self, text):
        self.output.setPlainText(self.output.toPlainText() + text + '\n')
        bar = self.output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def sync_messages(self, messages):
        text = '\n\n'.join(('你：' if m['role'] == 'user' else '大肥鱼（预设）：' if m.get('mode') == 'demo' else '大肥鱼：') + m['content'] for m in messages)
        if text != self.output.toPlainText().strip():
            self.output.setPlainText(text)
            self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())


class PetWindow(QWidget):
    def __init__(self, backend=None, auto_connect=True):
        super().__init__()
        self.backend = backend or Backend()
        self.ready = False
        self.chat_pending = False
        self.chat_generation = 0
        self.poll_pending = False
        self.pref_dirty = False
        self.pref_generation = 0
        self.pref_inflight = 0
        self.workers = {}
        self.prefs = self.load_prefs()
        self.player = Animation(self.prefs.get('form', 'chibi'))
        self.player.motion = self.prefs['motion']
        self.atlases = {}
        for form, spec in self.player.spec['forms'].items():
            pix = QPixmap(str(ROOT / 'static' / spec['atlas'].lstrip('/')))
            if pix.isNull():
                raise ValueError('缺少形态素材：' + form)
            self.atlases[form] = pix
        self.scale = self.prefs['scale']
        self.sleeping = False
        self.old_sprite = None
        self.transition_until = 0.0
        self.drag_offset = None
        self.drag_moved = False
        self.double_clicked = False
        self.last_tick = time.monotonic()
        self.started = self.last_tick
        self.walk_until = 0.0
        self.next_walk = self.started + random.uniform(15, 25)
        self.walk_direction = 1
        self.seen_jobs = None
        self.last_pause = None
        self.chat_dialog = None
        self.tray = None
        self.last_cursor = QCursor.pos()
        self.look_until = 0.0
        self.last_mask_key = None
        self.setWindowTitle('大肥鱼桌宠')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setAcceptDrops(False)
        self.setFixedSize(round(350*self.scale), round(525*self.scale))
        self.speech = QLabel(self)
        self.speech.setWordWrap(True)
        self.speech.setTextFormat(Qt.TextFormat.PlainText)
        self.speech.setStyleSheet('background:rgba(250,252,255,240);color:#496587;border:1px solid #d8e3f2;border-radius:14px;padding:11px;font-size:12px')
        self.speech.setGeometry(round(20*self.scale), 8, self.width()-round(40*self.scale), 75)
        self.speech.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.speech.hide()
        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self.speech.hide)
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.touch)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.sync_preferences)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(4000)
        self.restore_position()
        self.set_top(self.prefs['top'], save=False)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(QIcon(str(ROOT / 'static' / 'character.png')), self)
            self.tray.setToolTip('大肥鱼 · 双击唤回，右键切换形态')
            self.tray.activated.connect(self.tray_activate)
            self.tray.setContextMenu(self.make_menu())
            self.tray.show()
        self.say('左键拖动我，双击聊天。\n右键可以切换 Q 版 / 成熟版。', 9000)
        if auto_connect:
            self.work('connect', self.backend.connect)

    def load_prefs(self):
        defaults = {'form': 'chibi', 'motion': True, 'scale': 1.0, 'top': True, 'wander': False, 'follow': True}
        try:
            saved = json.loads((DATA / 'desktop.json').read_text('utf-8'))
            defaults.update({k: saved[k] for k in defaults if k in saved})
            for k in ('x', 'y'):
                if isinstance(saved.get(k), int):
                    defaults[k] = saved[k]
        except (OSError, ValueError, TypeError):
            pass
        if defaults['scale'] not in (.75, 1.0, 1.25):
            defaults['scale'] = 1.0
        return defaults

    def save_prefs(self):
        DATA.mkdir(parents=True, exist_ok=True)
        self.prefs.update(form=self.player.form, motion=self.player.motion, scale=self.scale, x=self.x(), y=self.y())
        temp = DATA / 'desktop.tmp'
        temp.write_text(json.dumps(self.prefs), 'utf-8')
        temp.replace(DATA / 'desktop.json')

    def restore_position(self):
        work = QApplication.primaryScreen().availableGeometry()
        pos = QPoint(self.prefs.get('x', work.right()-self.width()-35), self.prefs.get('y', work.bottom()-self.height()-15))
        self.move(self.clamp(pos))

    def clamp(self, pos):
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        r = screen.availableGeometry()
        return QPoint(max(r.left(), min(pos.x(), r.right()-self.width()+1)), max(r.top(), min(pos.y(), r.bottom()-self.height()+1)))

    def work(self, kind, function):
        if kind in self.workers:
            return
        worker = Worker(kind, function)
        self.workers[kind] = worker
        worker.signals.done.connect(self.worker_done)
        worker.signals.failed.connect(self.worker_failed)
        # Daemon I/O threads don't hold the pet open on exit during a slow model call.
        threading.Thread(target=worker.run, daemon=True, name='pet-' + kind).start()

    @Slot(str, object)
    def worker_done(self, kind, result):
        self.workers.pop(kind, None)
        if kind == 'connect':
            self.ready = True
            self.poll()
        elif kind == 'state':
            self.poll_pending = False
            cfg = result['config']
            pause = result.get('checks', {}).get('activity-pause', {}).get('detail', '')
            if self.last_pause is not None and pause != self.last_pause:
                self.prefs['wander'] = False
                self.walk_until = 0
                self.play('idle')
                self.save_prefs()
            self.last_pause = pause
            if not self.pref_dirty and result.get('_pet_generation') == self.pref_generation:
                if cfg.get('pet_form', 'chibi') != self.player.form:
                    self.set_form(cfg['pet_form'], persist=False)
                self.player.motion = cfg.get('pet_motion', True)
            if self.chat_dialog:
                self.chat_dialog.notice.setText('真实 AI · ' + cfg['model'] if cfg['engine'] == 'model' else '互动体验 · 预设回应，未调用 AI')
                if not self.chat_pending and not result.get('_chat_pending') and result.get('_chat_generation') == self.chat_generation:
                    self.chat_dialog.sync_messages(result.get('messages', []))
            jobs = result.get('jobs', [])
            done = {j['id'] for j in jobs if j['status'] in ('done', 'failed', 'cancelled')}
            if self.seen_jobs is not None:
                new = done-self.seen_jobs
                if new and not self.sleeping and not self.chat_pending:
                    failed = any(j['id'] in new and j['status'] == 'failed' for j in jobs)
                    self.play('failed' if failed else 'jump')
                    self.say('任务遇到点问题，去控制台看看原因吧。' if failed else '任务结束啦！结果和截图放在探索日记里了。')
            self.seen_jobs = done
            busy = any(j['status'] in ('queued', 'running') for j in jobs)
            if busy and not self.chat_pending and not self.sleeping and self.player.action == 'idle':
                self.play('work')
            elif not busy and self.player.action == 'work':
                self.play('idle')
        elif kind == 'chat':
            self.chat_pending = False
            if self.chat_dialog:
                self.chat_dialog.send.setEnabled(True)
                self.chat_dialog.append('大肥鱼：' + result['answer'])
            self.play('wave')
            self.say(result['answer'][:150], 12000)
        elif kind == 'prefs':
            self.pref_dirty = self.pref_inflight != self.pref_generation
            if self.pref_dirty:
                self.save_timer.start(0)
        elif kind == 'pause':
            self.say('已暂停自动活动。我安静陪你待着。')

    @Slot(str, str)
    def worker_failed(self, kind, message):
        self.workers.pop(kind, None)
        if kind == 'state':
            self.poll_pending = False
            self.ready = False
        if kind == 'prefs':
            self.pref_dirty = False
        if kind == 'chat':
            self.chat_pending = False
            if self.chat_dialog:
                self.chat_dialog.send.setEnabled(True)
                self.chat_dialog.append('提示：' + message)
                if not self.chat_dialog.input.text():
                    self.chat_dialog.input.setText(getattr(self.chat_dialog, 'retry_text', ''))
        self.play('failed')
        self.say(message, 10000)

    def poll(self):
        if self.ready and not self.poll_pending:
            self.poll_pending = True
            generation = self.pref_generation
            chat_generation, chat_pending = self.chat_generation, self.chat_pending
            def fetch_state():
                result = self.backend.request('state', timeout=5)
                return {**result, '_pet_generation': generation, '_chat_generation': chat_generation, '_chat_pending': chat_pending}
            self.work('state', fetch_state)

    def sync_preferences(self):
        if self.ready:
            if 'prefs' in self.workers:
                self.save_timer.start(150)
                return
            form, motion = self.player.form, self.player.motion
            self.pref_inflight = self.pref_generation
            self.work('prefs', lambda: self.backend.request('settings', {'pet_form': form, 'pet_motion': motion}, timeout=5))

    def set_form(self, form, persist=True):
        if form == self.player.form:
            return
        self.old_sprite = (self.player.form, self.player.frame)
        self.transition_until = time.monotonic()+.4
        self.player.set_form(form)
        self.last_mask_key = None
        self.say('变成 Q 版啦，小小一只也能认真工作。' if form == 'chibi' else '换成成熟版。白饭的份量可不会减少哦。')
        if persist:
            self.pref_dirty = True
            self.pref_generation += 1
            self.save_timer.start(250)
        self.save_prefs()
        self.update()

    def play(self, action):
        self.player.play(action)
        self.walk_until = 0.0
        self.last_mask_key = None
        self.update()

    def say(self, text, milliseconds=7000):
        limit = max(35, int((self.speech.width()-24)/12*3))
        self.speech.setText(text if len(text) <= limit else text[:limit-1]+'…')
        self.speech.show()
        self.bubble_timer.start(milliseconds)
        self.last_mask_key = None

    def touch(self):
        self.sleeping = False
        self.play('wave')
        self.say(random.choice(['你来啦，我才没有偷懒。', '才不是大肥鱼，是鲸鱼娘。', '今天也一起慢慢来吧。']))

    def feed(self):
        self.sleeping = False
        self.play('feed')
        self.say('白饭！谢谢投喂，今天也会好好陪你。')

    def sleep(self):
        self.sleeping = not self.sleeping
        self.play('sleep' if self.sleeping else 'idle')
        self.say('我眯一小会儿，点我就醒。' if self.sleeping else '醒啦！有什么想和我说的吗？')

    def open_chat(self):
        self.sleeping = False
        self.play('idle')
        if not self.chat_dialog:
            self.chat_dialog = ChatDialog(self)
        self.chat_dialog.show()
        self.chat_dialog.raise_()
        self.chat_dialog.activateWindow()
        self.chat_dialog.input.setFocus()
        self.poll()

    def open_connection(self):
        if self.ready:
            webbrowser.open(self.backend.base + '/#connect')
        else:
            self.say('正在连接本机服务，请稍后再打开接入引导。')
            self.work('connect', self.backend.connect)

    def send_chat(self, text):
        if not self.ready:
            self.say('正在连接本机服务，请稍等。')
            self.work('connect', self.backend.connect)
            return
        self.chat_pending = True
        self.chat_generation += 1
        self.sleeping = False
        self.play('think')
        self.chat_dialog.send.setEnabled(False)
        self.say('在认真想了……')
        self.work('chat', lambda: self.backend.request('chat', {'message': text}))

    def toggle_motion(self):
        self.player.motion = not self.player.motion
        self.pref_dirty = True
        self.pref_generation += 1
        self.save_prefs()
        self.save_timer.start(250)
        self.update()

    def set_top(self, enabled, save=True):
        self.prefs['top'] = bool(enabled)
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(enabled))
        if visible:
            self.show()
        if save:
            self.save_prefs()

    def set_scale(self, scale):
        bottom = self.y()+self.height()
        self.scale = scale
        self.setFixedSize(round(350*scale), round(525*scale))
        self.speech.setGeometry(round(20*scale), 8, self.width()-round(40*scale), 75)
        self.move(self.clamp(QPoint(self.x(), bottom-self.height())))
        self.last_mask_key = None
        self.save_prefs()

    def toggle_wander(self):
        self.prefs['wander'] = not self.prefs['wander']
        self.walk_until = 0
        self.next_walk = time.monotonic()+2
        if self.player.action.startswith('walk'):
            self.play('idle')
        self.save_prefs()

    def make_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet('QMenu{background:#fbfcff;color:#405b81;border:1px solid #d7e3f3;padding:6px;border-radius:9px} QMenu::item{padding:7px 23px} QMenu::item:selected{background:#eaf1fb}')
        group = QActionGroup(menu)
        for key, text in [('chibi', 'Q 版'), ('mature', '成熟版')]:
            action = menu.addAction(text)
            action.setCheckable(True)
            action.setChecked(self.player.form == key)
            group.addAction(action)
            action.triggered.connect(lambda _, k=key: self.set_form(k))
        menu.addSeparator()
        for text, fn in [('挥挥手', lambda: self.play('wave')), ('跳一下', lambda: self.play('jump')), ('喂白饭', self.feed), ('睡觉 / 叫醒', self.sleep), ('和她聊天…', self.open_chat)]:
            menu.addAction(text, fn)
        menu.addSeparator()
        a = menu.addAction('动画开启')
        a.setCheckable(True)
        a.setChecked(self.player.motion)
        a.triggered.connect(self.toggle_motion)
        a = menu.addAction('偶尔在桌面散步')
        a.setCheckable(True)
        a.setChecked(self.prefs['wander'])
        a.triggered.connect(self.toggle_wander)
        a = menu.addAction('看向鼠标（Q 版）')
        a.setCheckable(True)
        a.setChecked(self.prefs['follow'])
        a.triggered.connect(self.toggle_follow)
        a = menu.addAction('保持置顶')
        a.setCheckable(True)
        a.setChecked(self.prefs['top'])
        a.triggered.connect(self.set_top)
        size = QMenu('大小', menu)
        menu.addMenu(size)
        # Keep Python wrappers alive for Qt-owned submenu/group objects.
        menu._owned_objects = [size, group]
        for scale in (.75, 1.0, 1.25):
            size.addAction(f'{round(scale*100)}%', lambda checked=False, s=scale: self.set_scale(s))
        menu.addAction('移回屏幕右下角', self.reset_position)
        menu.addSeparator()
        menu.addAction('打开养成台…', lambda: webbrowser.open(self.backend.base) if self.ready else self.say('本机服务还未就绪。'))
        if not self.ready:
            menu.addAction('重新连接养成台', lambda: self.work('connect', self.backend.connect))
        menu.addAction('暂停全部自动活动', self.pause_all)
        if self.tray:
            menu.addAction('隐藏到托盘', self.hide)
        menu.addAction('退出桌宠', self.close)
        def refresh_checks():
            values = {'Q 版': self.player.form == 'chibi', '成熟版': self.player.form == 'mature',
                      '动画开启': self.player.motion, '偶尔在桌面散步': self.prefs['wander'],
                      '看向鼠标（Q 版）': self.prefs['follow'], '保持置顶': self.prefs['top']}
            for action in menu.actions():
                if action.text() in values:
                    action.setChecked(values[action.text()])
        menu.aboutToShow.connect(refresh_checks)
        return menu

    def toggle_follow(self):
        self.prefs['follow'] = not self.prefs['follow']
        self.save_prefs()

    def pause_all(self):
        self.prefs['wander'] = False
        self.walk_until = 0
        self.play('idle')
        if self.ready:
            self.work('pause', lambda: self.backend.request('pause', {}))
        self.save_prefs()

    def reset_position(self):
        self.prefs.pop('x', None)
        self.prefs.pop('y', None)
        self.restore_position()
        self.save_prefs()

    def tray_activate(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show()
            self.raise_()

    def contextMenuEvent(self, event):
        menu = self.make_menu()
        try:
            menu.exec(event.globalPos())
        finally:
            menu.deleteLater()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint()-self.pos()
            self.drag_moved = False

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()-self.drag_offset
            if (pos-self.pos()).manhattanLength() > 3:
                self.drag_moved = True
                self.move(self.clamp(pos))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.drag_moved:
                self.save_prefs()
            elif not self.double_clicked:
                self.click_timer.start(240)
            self.drag_offset = None
            self.double_clicked = False

    def mouseDoubleClickEvent(self, event):
        self.click_timer.stop()
        self.double_clicked = True
        self.open_chat()

    def tick(self):
        now = time.monotonic()
        dt = min(100, (now-self.last_tick)*1000)
        self.last_tick = now
        self.player.advance(dt)
        cursor = QCursor.pos()
        if cursor != self.last_cursor:
            self.look_until = now+1.2
            self.last_cursor = cursor
        if self.prefs['wander'] and self.player.motion and not self.sleeping and not self.chat_pending and self.drag_offset is None:
            if now > self.next_walk and self.player.action == 'idle':
                self.walk_until = now+random.uniform(2, 4)
                self.walk_direction = random.choice([-1, 1])
                self.player.play('walk-left' if self.walk_direction < 0 else 'walk-right')
            if self.walk_until:
                if now < self.walk_until:
                    before = self.pos()
                    self.move(self.clamp(before+QPoint(round(self.walk_direction*dt*.05), 0)))
                    if self.pos() == before:
                        self.walk_direction *= -1
                        self.player.play('walk-left' if self.walk_direction < 0 else 'walk-right')
                else:
                    self.walk_until = 0
                    self.next_walk = now+random.uniform(18, 35)
                    self.player.play('idle')
                    self.save_prefs()
        self.update()

    def sprite(self, form, frame):
        spec = self.player.spec['forms'][form]
        atlas = self.atlases[form]
        cw, ch = atlas.width()/spec['columns'], atlas.height()/spec['rows']
        crop = spec.get('crop', [0, 0, cw, ch])
        source = QRectF(frame[0]*cw+crop[0], frame[1]*ch+crop[1], crop[2], crop[3])
        height = min(spec['height']*self.scale, self.height()-self.speech.geometry().bottom()-30*self.scale)
        width = height*crop[2]/crop[3]
        target = QRectF((self.width()-width)/2, self.height()-25*self.scale-height, width, height)
        return atlas, source, target

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        now = time.monotonic()
        frame = self.player.frame
        if self.prefs['follow'] and now < self.look_until:
            center = self.mapToGlobal(QPoint(self.width()//2, self.height()//2))
            cursor = QCursor.pos()-center
            if abs(cursor.x())+abs(cursor.y()) > 50:
                frame = self.player.look_frame(cursor.x(), cursor.y())
        atlas, source, target = self.sprite(self.player.form, frame)
        t = now-self.started
        if self.player.motion:
            if self.player.form == 'mature':
                target.translate(0, math.sin(t*2)*1.8)
            if self.player.action == 'jump' and self.player.form == 'mature':
                target.translate(0, -abs(math.sin(self.player.elapsed/900*math.pi))*24)
        progress = 1.0
        if self.old_sprite and now < self.transition_until:
            progress = 1-(self.transition_until-now)/.4
            old_atlas, old_source, old_target = self.sprite(*self.old_sprite)
            painter.setOpacity(1-progress)
            painter.drawPixmap(old_target, old_atlas, old_source)
        painter.setOpacity(progress)
        painter.drawPixmap(target, atlas, source)
        painter.setOpacity(1)
        if progress < 1:
            painter.setPen(QColor('#a3bfee'))
            for i in range(7):
                a = i*math.tau/7+t
                painter.drawEllipse(QPoint(round(self.width()/2+math.cos(a)*100), round(self.height()/2+math.sin(a)*140)), 2, 2)
        painter.setPen(QColor('#8499b7'))
        painter.drawText(QRectF(0, self.height()-22*self.scale, self.width(), 20*self.scale), Qt.AlignmentFlag.AlignCenter,
                         self.player.form_spec['name']+' · '+self.player.spec['actions'][self.player.action])
        painter.end()
        # Don't let the large transparent rectangle consume clicks on the desktop.
        # Real desktop platforms support QWidget masks; the offscreen test plugin doesn't.
        if QApplication.platformName() != 'offscreen':
            key = (self.player.form, frame, round(target.y()), self.speech.isVisible(), self.speech.text(), round(progress, 1), self.scale)
            if key != self.last_mask_key:
                self.last_mask_key = key
                cropped = atlas.copy(source.toRect()).scaled(target.size().toSize(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                alpha = cropped.toImage().createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)
                region = QRegion(QBitmap.fromImage(alpha)).translated(target.topLeft().toPoint())
                if progress < 1 and self.old_sprite:
                    _, _, old_target = self.sprite(*self.old_sprite)
                    region |= QRegion(old_target.toRect())
                region |= QRegion(0, self.height()-round(24*self.scale), self.width(), round(24*self.scale))
                if self.speech.isVisible():
                    region |= QRegion(self.speech.geometry())
                self.setMask(region)

    def closeEvent(self, event):
        self.timer.stop()
        self.poll_timer.stop()
        self.save_prefs()
        if self.chat_dialog:
            self.chat_dialog.close()
        if self.tray:
            self.tray.hide()
        self.backend.close_owned()
        event.accept()
        QApplication.instance().quit()


def main():
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    DATA.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(DATA / 'desktop.lock'))
    if not lock.tryLock(0):
        print('大肥鱼桌宠已在运行，请从系统托盘唤回。', flush=True)
        return 0
    window = PetWindow()
    window.show()
    try:
        return app.exec()
    finally:
        lock.unlock()


if __name__ == '__main__':
    raise SystemExit(main())
