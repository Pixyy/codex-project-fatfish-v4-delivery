"""Official DeepSeek onboarding. Login stays on DeepSeek; this app uses API keys."""
from urllib.parse import urlsplit

import store
from net import json_get, json_request

DEEPSEEK_BASE = 'https://api.deepseek.com'
DEFAULT_MODEL = 'deepseek-flash'
LEGACY_MODELS = {'deepseek-chat', 'deepseek-reasoner', 'deepseek-v4-flash', 'deepseek-v4-flash-vision-exp'}
LINKS = {
    'login': 'https://platform.deepseek.com/',
    'keys': 'https://platform.deepseek.com/api_keys',
    'balance': 'https://platform.deepseek.com/balance',
    'chat': 'https://chat.deepseek.com/',
    'docs': 'https://api-docs.deepseek.com/zh-cn/',
}


def is_official(url):
    u = urlsplit(url)
    return u.scheme == 'https' and u.hostname == 'api.deepseek.com' and u.port in (None, 443) and u.path.rstrip('/') in ('', '/v1')


def normalize_key(key):
    if not isinstance(key, str):
        raise ValueError('API Key 应为文字')
    key = key.strip()
    if not key or len(key) > 1024 or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError('请粘贴完整 API Key；它不是 DeepSeek 登录密码')
    return key


def candidate_key(value=''):
    if value:
        return normalize_key(value)
    s = store.config()
    if not is_official(s['base_url']):
        raise ValueError('请先粘贴 DeepSeek API Key，当前保存的是其他服务的配置')
    if not s['model_key']:
        raise ValueError('请先粘贴 API Key。可点击上方链接登录 DeepSeek 开放平台创建。')
    return normalize_key(s['model_key'])


def inspect(key=''):
    token = candidate_key(key)
    result = json_get(DEEPSEEK_BASE + '/models', token, timeout=12)
    data = result.get('data')
    if not isinstance(data, list):
        raise ValueError('DeepSeek 模型列表格式不正确，请稍后重试')
    models = []
    for model in data[:100]:
        if isinstance(model, dict) and isinstance(model.get('id'), str) and 0 < len(model['id']) <= 128:
            models.append({'id': model['id'], 'name': str(model.get('name') or model['id'])[:128]})
    if not models:
        raise ValueError('当前 API Key 未返回可用模型，请检查账户权限')
    balance = json_get(DEEPSEEK_BASE + '/user/balance', token, timeout=12)
    if not isinstance(balance.get('is_available'), bool) or not isinstance(balance.get('balance_infos'), list):
        raise ValueError('DeepSeek 余额响应格式不正确，请稍后重试')
    # Only selected public fields leave the backend; never upstream request data.
    balances = [{'currency': str(x.get('currency', ''))[:8], 'total_balance': str(x.get('total_balance', ''))[:32]}
                for x in balance['balance_infos'][:5] if isinstance(x, dict)]
    ids = [m['id'] for m in models]
    recommended = next((m for m in (DEFAULT_MODEL, 'deepseek-v4-pro') if m in ids), ids[0])
    return {'account_verified': True, 'can_chat': balance['is_available'], 'models': models,
            'recommended': recommended, 'balances': balances,
            'detail': 'Key 已验证，可选择模型并接入' if balance['is_available'] else 'Key 有效，但 API 余额不足，请查看开放平台余额后重试'}


def connect(key='', model=''):
    token = candidate_key(key)
    if store.key_source() == 'environment' and token != store.config()['model_key']:
        raise ValueError('当前模型密钥来自 FISH_MODEL_KEY 环境变量。请先移除该变量，再在界面更换账号。')
    info = inspect(token)
    if not info['can_chat']:
        raise ValueError(info['detail'])
    chosen = model or info['recommended']
    if chosen not in {m['id'] for m in info['models']}:
        raise ValueError('这个模型不在当前账号的可用列表中，请重新检测')
    payload = {'model': chosen, 'messages': [{'role': 'user', 'content': '请只回复：连接成功'}],
               'thinking': {'type': 'disabled'}, 'max_tokens': 64, 'stream': False}
    response = json_request(DEEPSEEK_BASE + '/chat/completions', payload, token, timeout=35)
    try:
        answer = response['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise ValueError('DeepSeek 未返回有效回复；未更改原有配置') from None
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError('DeepSeek 回复为空；未更改原有配置')
    store.save_config({'base_url': DEEPSEEK_BASE, 'model': chosen, 'model_key': token, 'engine': 'model'})
    store.check('model', True, 'DeepSeek 真实请求成功 · ' + chosen)
    return {**info, 'connected': True, 'model': chosen, 'reply': answer[:200], 'detail': '已接入 DeepSeek，现在可以直接聊天'}


def disconnect():
    if store.key_source() == 'environment':
        raise ValueError('密钥来自 FISH_MODEL_KEY 环境变量，请先移除该变量再断开。当前未修改环境。')
    store.save_config({'engine': 'demo', 'model_key': None, 'qq_auto': False})
    store.invalidate_check('model')
    return {'detail': '已忘记本机模型密钥并关闭 QQ 自动回复，现为预设体验。远程 Key 仍可在 DeepSeek 官网管理。'}
