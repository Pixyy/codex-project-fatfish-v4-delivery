"""Local-only companion application. Run with launcher.py for browser auto-open."""
import argparse
import hmac
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'data' / 'python'))
import brain
import channels
import store
import tasks
import provider
from app_identity import VERSION, instance_id

TOKEN = secrets.token_urlsafe(32)


class Handler(BaseHTTPRequestHandler):
    server_version = 'FatFish/4'

    def log_message(self, *_):
        pass

    def local_request(self):
        try:
            host = urlsplit('http://' + self.headers.get('Host', '')).hostname
            return host in ('127.0.0.1', 'localhost', '::1')
        except ValueError:
            return False

    def reply(self, body, status=200):
        content = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.local_request():
            return self.reply({'error': '仅允许本机访问'}, 403)
        path = urlsplit(self.path).path
        if path == '/api/health':
            return self.reply({'app': 'fatfish', 'version': VERSION, 'instance': instance_id()})
        if path == '/api/bootstrap':
            return self.reply({'token': TOKEN, 'version': VERSION, 'deepseek_links': provider.LINKS})
        if path == '/api/state':
            return self.reply({'config': store.public_config(), 'messages': store.messages(),
                               'jobs': store.jobs(), 'checks': store.checks(),
                               'browser_installed': tasks.browser_ready()})
        if path == '/api/devices':
            try:
                return self.reply({'devices': tasks.devices()})
            except Exception as e:
                return self.reply({'error': store.public_error(e)}, 400)
        if path == '/api/export':
            return self.reply({'messages': store.messages(limit=10000), 'jobs': store.jobs()})
        if path.startswith('/api/'):
            return self.reply({'error': '接口不存在'}, 404)
        if path.startswith('/artifacts/'):
            base = store.DATA / 'artifacts'
            target = base / unquote(path[len('/artifacts/'):])
        else:
            base = ROOT / 'static'
            target = base / ('index.html' if path == '/' else unquote(path.lstrip('/')))
        if not target.resolve().is_relative_to(base.resolve()) or not target.is_file():
            return self.reply({'error': '文件不存在'}, 404)
        content = target.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(target)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if not self.local_request():
            return self.reply({'error': '仅允许本机访问'}, 403)
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.reply({'error': '来源校验失败'}, 403)
        path = urlsplit(self.path).path
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 100000:
                return self.reply({'error': '请求大小不正确'}, 413)
            raw = self.rfile.read(size)
            if path == '/api/qq/event':
                if not channels.authorized_signature(raw, self.headers.get('X-Signature', '')):
                    return self.reply({'error': 'QQ 回调签名校验失败'}, 403)
                return self.reply(channels.receive(json.loads(raw)))
            if not hmac.compare_digest(self.headers.get('X-Fish-Token', ''), TOKEN):
                return self.reply({'error': '会话已变化，请刷新页面'}, 403)
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError('请求必须是 JSON 对象')
            if path == '/api/settings':
                if any(not isinstance(v, (str, int, bool, type(None))) or (isinstance(v, str) and len(v) > 8000) for v in data.values()):
                    raise ValueError('配置格式不正确')
                return self.reply({'config': store.save_config(data)})
            if path == '/api/chat':
                return self.reply(brain.chat(data.get('message', '')))
            if path == '/api/desktop/start':
                if sys.platform.startswith('linux') and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
                    raise ValueError('当前运行环境没有桌面会话。请下载完整启动包，在自己的电脑双击“启动桌宠”；首次会自动安装桌宠组件。')
                import importlib.util
                if not (ROOT / 'data' / 'desktop-python' / 'PySide6').is_dir() and importlib.util.find_spec('PySide6') is None:
                    raise ValueError('首次请双击下载包里的“启动桌宠”，自动安装一次组件，之后可以在这里打开。')
                flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.Popen([sys.executable, str(ROOT / 'desktop.py')], cwd=ROOT,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
                return self.reply({'detail': '已发出桌宠启动请求。左键拖动、双击聊天、右键切换形态；如未出现，请双击“启动桌宠”查看提示。'})
            if path == '/api/model/test':
                return self.reply(brain.test_model())
            if path == '/api/deepseek/inspect':
                return self.reply(provider.inspect(data.get('api_key', '')))
            if path == '/api/deepseek/connect':
                return self.reply(provider.connect(data.get('api_key', ''), data.get('model', '')))
            if path == '/api/deepseek/disconnect':
                return self.reply(provider.disconnect())
            if path == '/api/diagnostics':
                import doctor
                return self.reply(doctor.report())
            if path == '/api/qq/test':
                return self.reply(channels.test_qq())
            if path == '/api/qq/setup':
                return self.reply({'url': 'http://127.0.0.1:' + str(self.server.server_port) + '/api/qq/event',
                                   'secret': store.config()['qq_secret']})
            if path == '/api/send':
                channels.send(data.get('channel'), data.get('target'), data.get('message'), bool(data.get('group')))
                return self.reply({'ok': True})
            if path == '/api/tasks':
                return self.reply({'id': tasks.submit(data.get('kind', 'read'), data)})
            if path == '/api/tasks/cancel':
                return self.reply({'stopping': tasks.cancel(str(data.get('id', '')))})
            if path == '/api/pause':
                store.save_config({'qq_auto': False})
                tasks.cancel_all()
                store.check('activity-pause', True, str(time.time_ns()))
                return self.reply({'ok': True})
            if path == '/api/chat/clear':
                brain.clear_chat()
                return self.reply({'ok': True})
            return self.reply({'error': '接口不存在'}, 404)
        except Exception as e:
            self.reply({'error': store.public_error(e)}, 400)


def run(port=8765):
    store.init()
    with store.db() as c:
        c.execute("UPDATE events_v2 SET status='interrupted' WHERE status='pending'")
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    print(f'大肥鱼 v{VERSION}  http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        tasks.cancel_all()
    finally:
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    run(parser.parse_args().port)
