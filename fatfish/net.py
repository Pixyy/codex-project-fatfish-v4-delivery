"""Verified HTTPS transport, including per-redirect validation for browser resources."""
import ipaddress
import json
import socket
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class RemoteError(ValueError):
    def __init__(self, status):
        self.status = status
        hints = {
            400: '请求格式不被服务接受，请检查模型与 API 地址',
            401: 'API Key 或令牌无效，请重新复制完整密钥',
            402: 'API 账户余额不足，请到 DeepSeek 开放平台查看余额或充值',
            403: '服务拒绝访问，请检查账户权限或网络区域',
            404: '接口或模型不存在，请检查 API 地址并刷新模型列表',
            422: '模型参数不兼容，请检查当前模型与服务商',
            429: '请求速率达到上限，请稍后重试',
            500: '上游服务故障，请稍后重试',
            503: '上游服务繁忙，请稍后重试',
        }
        super().__init__(hints.get(status, '上游服务异常') + f'（HTTP {status}）')


def validate_endpoint(url, allow_local=False):
    u = urlsplit(url)
    if u.username or u.password or not u.hostname or u.fragment:
        raise ValueError('网址格式不正确，不支持网址中带用户名或密码')
    if u.scheme != 'https':
        if not (allow_local and u.scheme == 'http' and u.hostname in ('localhost', '127.0.0.1', '::1')):
            raise ValueError('远程服务必须使用 HTTPS；本机服务可用 http://127.0.0.1')
    return u


def public_url(url, domains=None):
    u = validate_endpoint(url)
    host = u.hostname.lower()
    if domains and not any(host == d or host.endswith('.' + d) for d in domains):
        raise ValueError('目标超出本次允许浏览的网站')
    addresses = socket.getaddrinfo(host, u.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('浏览任务只访问公开互联网地址')
    return u


class _Redirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, validator):
        self.validator = validator

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.validator(newurl)
        # API requests never follow redirects with an Authorization header.
        if req.has_header('Authorization'):
            raise ValueError('模型或消息接口发生重定向，请直接填写最终 API 地址')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, *, method='GET', data=None, headers=None, public=False, timeout=25, limit=8_000_000, domains=None):
    validator = (lambda u: public_url(u, domains)) if public else lambda u: validate_endpoint(u, allow_local=True)
    validator(url)
    opener = urllib.request.build_opener(_Redirect(validator), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    try:
        response = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        response = e
    except (TimeoutError, socket.timeout):
        raise ValueError('网络请求超时，请检查网络后重试') from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLError):
            raise ValueError('HTTPS 证书校验失败，请检查系统时间与网络代理证书') from None
        raise ValueError('无法连接服务，请检查网络、代理或服务地址') from None
    with response as r:
        content = r.read(limit + 1)
        if len(content) > limit:
            raise ValueError('资源过大，已停止下载')
        return r.status, dict(r.headers), content


def _json_call(url, payload=None, token='', timeout=60, method='POST'):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = json.dumps(payload).encode() if payload is not None else None
    status, _, body = fetch(url, method=method, data=data, headers=headers, timeout=timeout, limit=2_000_000)
    if status >= 400:
        raise RemoteError(status)
    try:
        result = json.loads(body)
    except (ValueError, UnicodeError):
        raise ValueError('上游服务返回了非 JSON 数据') from None
    if not isinstance(result, dict):
        raise ValueError('上游接口返回格式不正确')
    return result


def json_request(url, payload, token='', timeout=60):
    return _json_call(url, payload, token, timeout)


def json_get(url, token='', timeout=20):
    return _json_call(url, token=token, timeout=timeout, method='GET')
