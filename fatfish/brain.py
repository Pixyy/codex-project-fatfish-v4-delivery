import threading
from collections import defaultdict
import store
from net import json_request

_scope_locks = defaultdict(threading.Lock)


def clear_chat(scope='web'):
    with _scope_locks[scope], store.db() as c:
        c.execute('DELETE FROM chat_v2 WHERE scope=?', (scope,))


def completion(messages, *, tools=None, snapshot=None):
    s = snapshot or store.config()
    if not s['model_key']:
        raise ValueError('还没有 API Key，请在设置中填入并检测连接')
    payload = {'model': s['model'], 'messages': messages, 'max_tokens': 1000, 'stream': False}
    from provider import is_official
    if is_official(s['base_url']):
        payload['thinking'] = {'type': 'disabled'}
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'
    try:
        result = json_request(s['base_url'].rstrip('/') + '/chat/completions', payload, s['model_key'])
    except Exception as e:
        if same_model(s):
            store.check('model', False, store.public_error(e))
        raise
    try:
        return result['choices'][0]['message']
    except (KeyError, IndexError, TypeError):
        raise ValueError('模型响应缺少 choices[0].message，请检查兼容性') from None


def same_model(snapshot):
    current = store.config()
    return all(snapshot[k] == current[k] for k in ('base_url', 'model', 'model_key'))


def test_model():
    s = store.config()
    try:
        m = completion([{'role': 'user', 'content': '请只回复：连接成功'}], snapshot=s)
        if not isinstance(m.get('content'), str) or not m['content'].strip():
            raise ValueError('模型未返回文字')
        if not same_model(s):
            raise ValueError('检测期间配置已变化，请按当前配置重新检测')
        store.check('model', True, '已收到模型真实回复')
        return {'ok': True, 'detail': '模型连接成功', 'reply': m['content'][:200]}
    except Exception as e:
        if same_model(s):
            store.check('model', False, store.public_error(e))
        raise


def demo_reply(text):
    if any(w in text for w in ('饭', '饿', '吃')):
        return '白饭？我先把碗拿来……咳，工作做完再吃！🍚'
    if any(w in text for w in ('肥', '胖')):
        return '才、才不是大肥鱼！这是鲸鱼娘的正常发量。'
    if any(w in text for w in ('累', '困', '休息')):
        return '那就陪你歇一小会儿。我负责安静，你负责放松。'
    return '我在这儿呢。现在是互动体验，只有几句预设回应；到设置里接上模型，我就能认真陪你聊啦。'


def chat(text, scope='web'):
    text = str(text).strip()
    if not text or len(text) > 8000:
        raise ValueError('请填写 1–8000 字的消息')
    with _scope_locks[scope]:
        s = store.config()
        if s['engine'] == 'demo':
            answer = demo_reply(text)
            mode = 'demo'
        else:
            history = [{'role': r['role'], 'content': r['content']} for r in store.messages(scope, 60) if r['mode'] != 'demo'][-20:]
            answer = completion([{'role': 'system', 'content': s['personality'] or store.SYSTEM}] + history + [{'role': 'user', 'content': text}], snapshot=s).get('content')
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('模型没有返回可显示的文字')
            mode = 'model'
            if same_model(s):
                store.check('model', True, '已收到当前模型的真实回复')
        store.add_message(scope, 'user', text, mode)
        store.add_message(scope, 'assistant', answer, mode)
        return {'answer': answer, 'mode': mode}
