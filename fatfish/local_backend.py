"""Start or reuse the companion's local backend without exposing it remotely."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from app_identity import compatible

ROOT = Path(__file__).resolve().parent


class Backend:
    def __init__(self):
        self.base = ''
        self.token = ''
        self.process = None
        # Local app calls should not go through a network proxy.
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, path, data=None, timeout=70):
        raw = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.base + '/api/' + path, data=raw, headers={
            'Content-Type': 'application/json', 'X-Fish-Token': self.token})
        try:
            with self.http.open(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                message = json.load(e).get('error', '本机服务请求失败')
            except (ValueError, UnicodeError):
                message = '本机服务请求失败'
            raise ValueError(message) from None

    def connect(self):
        for port in range(8765, 8780):
            self.base = f'http://127.0.0.1:{port}'
            try:
                health = self.request('health', timeout=.2)
                if compatible(health):
                    self.token = self.request('bootstrap', timeout=2)['token']
                    return self.base
            except Exception:
                pass
        port = None
        for candidate in range(8765, 8780):
            with socket.socket() as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind(('127.0.0.1', candidate))
                    port = candidate
                    break
                except OSError:
                    continue
        if port is None:
            raise ValueError('本机端口繁忙，请关闭一个旧版大肥鱼')
        self.base = f'http://127.0.0.1:{port}'
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        self.process = subprocess.Popen([sys.executable, str(ROOT / 'app.py'), '--port', str(port)],
                                        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        creationflags=flags)
        for _ in range(60):
            if self.process.poll() is not None:
                raise ValueError('本机服务启动失败，请双击“启动大肥鱼”查看原因')
            try:
                if not compatible(self.request('health', timeout=.2)):
                    time.sleep(.1)
                    continue
                self.token = self.request('bootstrap', timeout=.2)['token']
                return self.base
            except Exception:
                time.sleep(.1)
        raise ValueError('本机服务启动超时')

    def close_owned(self):
        # A reused controller belongs to its existing session and stays running.
        if self.process and self.process.poll() is None:
            try:
                self.request('pause', {}, timeout=2)
            except Exception:
                pass
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
