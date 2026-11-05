"""Local environment diagnostics. Never exports keys, tokens or conversation text."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
for folder in ('python', 'desktop-python'):
    sys.path.insert(0, str(ROOT / 'data' / folder))


def report():
    import store
    from app_identity import VERSION
    from pet_core import manifest
    items = []
    def item(name, status, detail):
        items.append({'name': name, 'status': status, 'detail': detail})
    item('Python', 'ok' if sys.version_info >= (3, 10) else 'error', platform.python_version() + ' · ' + platform.system() + ' ' + platform.machine())
    try:
        store.DATA.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=store.DATA):
            pass
        item('本机数据目录', 'ok', '可写；数据不随交付包分发')
    except OSError:
        item('本机数据目录', 'error', '不可写，请将整个解压文件夹移动到可写位置')
    try:
        spec = manifest()
        missing = [s['atlas'] for s in spec['forms'].values() if not (ROOT / 'static' / s['atlas'].lstrip('/')).is_file()]
    except (OSError, ValueError, KeyError):
        missing = ['manifest']
    item('两种形态与动画', 'error' if missing else 'ok', '请重新解压完整包' if missing else '素材和动作配置齐全')
    qt = importlib.util.find_spec('PySide6') is not None
    item('原生桌宠组件', 'ok' if qt else 'optional', '已安装' if qt else '未安装；首次启动桌宠会自动安装')
    display = sys.platform != 'linux' or bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
    item('桌面会话', 'ok' if display else 'optional', '系统提供桌面入口；实际窗口效果以运行结果为准' if display else '当前无图形会话；可用网页预览，原生桌宠请在本机运行')
    import tasks
    browser = tasks.browser_ready()
    item('浏览组件', 'ok' if browser else 'optional', '已安装；访问目标站点仍需网络' if browser else '可选；需要浏览网页时运行“安装浏览器”')
    try:
        s = store.config() if (store.DATA / 'fish.db').exists() else store.DEFAULTS
        item('聊天模式', 'ok', '真实模型 · ' + s['model'] if s['engine'] == 'model' else '预设互动体验，未调用模型')
        item('模型密钥', 'ok' if s.get('model_key') else 'optional', '已配置 · 来源 ' + store.key_source() if s.get('model_key') else '未配置；在“和她说说话”中点击“接入 DeepSeek”')
        item('模型地址', 'ok', urlsplit(s['base_url']).hostname or '未配置')
    except Exception:
        item('本机配置', 'error', '配置无法读取，请查看启动窗口提示；未导出配置内容')
    return {'version': VERSION, 'checks': items, 'note': '本报告不包含密钥、令牌、账号号码、聊天正文或完整本机路径。'}


if __name__ == '__main__':
    data = report()
    import store
    path = store.DATA / 'diagnostics.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    for entry in data['checks']:
        print(f"[{entry['status']}] {entry['name']}：{entry['detail']}")
    print('报告已保存至 data/diagnostics.json（不含密钥或聊天正文）。')
