"""OneBot 11 private/group replies and WeCom robot outbound messaging."""
import hashlib
import hmac
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import brain
import store
from net import json_request

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='fish-qq')
_last_reply = {}
_lock = threading.Lock()


def onebot(action, payload):
    s = store.config()
    if not s['onebot_url']:
        raise ValueError('请先配置 QQ OneBot 服务地址')
    result = json_request(s['onebot_url'].rstrip('/') + '/' + action, payload, s['onebot_token'], timeout=20)
    if result.get('status') != 'ok' or result.get('retcode') != 0:
        raise ValueError('QQ 服务返回失败，请检查登录状态和接口配置')
    return result.get('data')


def test_qq():
    try:
        info = onebot('get_login_info', {})
        if not isinstance(info, dict) or not info.get('user_id'):
            raise ValueError('QQ 服务未返回已登录账号')
        store.check('qq', True, '已验证登录账号 ' + str(info['user_id']))
        return {'ok': True, 'detail': '已连接 QQ ' + str(info['user_id'])}
    except Exception as e:
        store.check('qq', False, store.public_error(e))
        raise


def send(channel, target, message, group=False):
    if not isinstance(message, str) or not 0 < len(message.strip()) <= 2000:
        raise ValueError('请输入 1–2000 字的消息')
    if channel == 'qq':
        target = str(target)
        if not target.isdigit() or len(target) > 20:
            raise ValueError('请填写正确的 QQ 号或群号')
        # Text segments prevent CQ-code injection from model or UI text.
        return onebot('send_group_msg' if group else 'send_private_msg',
                      {'group_id' if group else 'user_id': int(target), 'message': [{'type': 'text', 'data': {'text': message}}]})
    if channel == 'wechat':
        url = store.config()['wecom_webhook']
        if not url:
            raise ValueError('请先填写企业微信群机器人 Webhook')
        result = json_request(url, {'msgtype': 'text', 'text': {'content': message}}, timeout=20)
        if result.get('errcode') != 0:
            raise ValueError('企业微信发送失败，错误码：' + str(result.get('errcode', '缺失')))
        store.check('wechat', True, '已向企业微信群成功发送一条消息')
        return result
    raise ValueError('不支持的渠道')


def authorized_signature(raw, signature):
    secret = store.config()['qq_secret']
    expected = 'sha1=' + hmac.new(secret.encode(), raw, hashlib.sha1).hexdigest()
    return bool(secret and signature and hmac.compare_digest(expected, signature))


def ids(value):
    return {x for x in re.split(r'[,，\s]+', value.strip()) if x.isdigit()}


def receive(event):
    s = store.config()
    if not s['qq_auto'] or s['engine'] != 'model':
        return {'accepted': False, 'reason': '自动回复未开启'}
    if event.get('post_type') != 'message' or str(event.get('user_id')) == str(event.get('self_id')):
        return {'accepted': False, 'reason': '忽略非消息或自身消息'}
    kind = event.get('message_type')
    uid = str(event.get('user_id', ''))
    if kind == 'private':
        if uid not in ids(s['qq_users']):
            return {'accepted': False, 'reason': '好友不在允许列表'}
        scope = 'qq:private:' + uid
        target = uid
    elif kind == 'group':
        target = str(event.get('group_id', ''))
        if target not in ids(s['qq_groups']):
            return {'accepted': False, 'reason': '群不在允许列表'}
        segments = event.get('message')
        if not isinstance(segments, list) or not any(x.get('type') == 'at' and str(x.get('data', {}).get('qq')) == str(event.get('self_id')) for x in segments):
            return {'accepted': False, 'reason': '群内需要 @ 机器人'}
        # Don't share one member's conversation with another member.
        scope = 'qq:group:' + target + ':user:' + uid
    else:
        return {'accepted': False, 'reason': '不支持的消息类型'}
    segments = event.get('message')
    text = ''.join(x.get('data', {}).get('text', '') for x in segments if x.get('type') == 'text') if isinstance(segments, list) else str(event.get('raw_message', ''))
    if not text.strip() or not event.get('message_id'):
        return {'accepted': False, 'reason': '缺少文字或消息编号'}
    event_id = str(event.get('self_id')) + ':' + str(event['message_id'])
    with _lock, store.db() as c:
        # Bounded pending queue and per-conversation cooldown prevent reply storms.
        count = c.execute("SELECT count(*) FROM events_v2 WHERE status='pending'").fetchone()[0]
        if count >= 8:
            return {'accepted': False, 'reason': '正在处理其他消息'}
        if c.execute('SELECT 1 FROM events_v2 WHERE id=?', (event_id,)).fetchone():
            return {'accepted': False, 'reason': '重复消息'}
        if time.monotonic() - _last_reply.get(scope, 0) < 3:
            return {'accepted': False, 'reason': '回复冷却中'}
        c.execute('INSERT INTO events_v2(id,status) VALUES(?,?)', (event_id, 'pending'))
        _last_reply[scope] = time.monotonic()
    _pool.submit(reply, event_id, scope, target, kind, text[:8000])
    return {'accepted': True}


def reply(event_id, scope, target, kind, text):
    status = 'failed'
    try:
        if not store.config()['qq_auto']:
            status = 'disabled'
            return
        answer = brain.chat(text, scope)['answer']
        if not store.config()['qq_auto']:
            status = 'disabled'
            return
        send('qq', target, answer[:2000], group=kind == 'group')
        store.check('qq-reply', True, '已完成一条授权范围内的自动回复')
        status = 'done'
    except Exception as e:
        store.check('qq-reply', False, store.public_error(e))
    finally:
        with store.db() as c:
            c.execute('UPDATE events_v2 SET status=? WHERE id=?', (status, event_id))
