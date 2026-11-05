"""No-package launcher; browser extras install only when explicitly requested."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from app_identity import compatible

ROOT = Path(__file__).resolve().parent


def install_browser():
    target = ROOT / 'data' / 'python'
    target.mkdir(parents=True, exist_ok=True)
    print('正在安装浏览组件，仅写入本项目 data 文件夹……', flush=True)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', '--target', str(target), '-r', str(ROOT / 'requirements.txt')], check=True)
    env = {**os.environ, 'PYTHONPATH': str(target), 'PLAYWRIGHT_BROWSERS_PATH': str(ROOT / 'data' / 'browsers')}
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], env=env, check=True)
    print('浏览器安装完成，重新打开大肥鱼即可。', flush=True)


def main():
    if sys.version_info < (3, 10):
        raise SystemExit('请先安装 Python 3.10 或更新版本。')
    p = argparse.ArgumentParser()
    p.add_argument('--install-browser', action='store_true')
    p.add_argument('--no-open', action='store_true')
    p.add_argument('--desktop', action='store_true')
    p.add_argument('--install-desktop', action='store_true')
    args = p.parse_args()
    if args.install_browser:
        return install_browser()
    if args.install_desktop or args.desktop:
        target = ROOT / 'data' / 'desktop-python'
        sys.path.insert(0, str(target))
        import importlib.util
        if args.install_desktop or importlib.util.find_spec('PySide6') is None:
            print('首次安装桌宠组件（仅写入本项目），请稍候……', flush=True)
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--target', str(target),
                            '-r', str(ROOT / 'requirements-desktop.txt')], check=True)
            importlib.invalidate_caches()
        if args.desktop:
            import desktop
            return desktop.main()
        return
    for port in range(8765, 8780):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=.3) as r:
                health = json.load(r)
            if compatible(health):
                if not args.no_open:
                    webbrowser.open(f'http://127.0.0.1:{port}')
                print('大肥鱼已经在运行。')
                return
        except Exception:
            pass
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('127.0.0.1', port))
                break
            except OSError:
                continue
    else:
        raise SystemExit('本机端口繁忙，请关闭一个旧实例。')
    if not args.no_open:
        threading.Timer(1, lambda: webbrowser.open(f'http://127.0.0.1:{port}')).start()
    import app
    app.run(port)


if __name__ == '__main__':
    main()
