"""Real local HTTP integration. Model/QQ providers are explicit test fixtures."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TEMP = tempfile.TemporaryDirectory()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import channels
import store
from net import public_url

CALLS = []
class Upstream(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        CALLS.append((self.path,body,self.headers.get('Authorization')))
        if self.path=='/v1/chat/completions':
            # A fixture answer proves the complete HTTP path; not a real AI call.
            answer={'choices':[{'message':{'role':'assistant','content':'fixture-reply:'+body['messages'][-1]['content'][:30]}}]}
        elif self.path=='/get_login_info': answer={'status':'ok','retcode':0,'data':{'user_id':888,'nickname':'test-bot'}}
        elif self.path in ('/send_private_msg','/send_group_msg'):answer={'status':'ok','retcode':0,'data':{'message_id':123}}
        else:answer={'error':'unknown'}
        raw=json.dumps(answer).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_data = store.DATA
        store.DATA = Path(TEMP.name)
        cls.env_patch = patch.dict(os.environ, {k: '' for k in ('FISH_MODEL_KEY','FISH_ONEBOT_URL','FISH_ONEBOT_TOKEN','FISH_WECOM_WEBHOOK')})
        cls.env_patch.start()
        store.init()
        cls.up=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        for s in (cls.up,cls.server):threading.Thread(target=s.serve_forever,daemon=True).start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
        cls.upbase='http://127.0.0.1:'+str(cls.up.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.up.shutdown();cls.server.server_close();cls.up.server_close()
        store.DATA = cls.original_data
        cls.env_patch.stop()
    def request(self,path,data=None,headers=None):
        h={'Content-Type':'application/json','X-Fish-Token':app.TOKEN,**(headers or {})}
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=h)
        with urllib.request.urlopen(req) as r:return json.load(r)
    def test_01_demo_and_secrets(self):
        answer=self.request('/api/chat',{'message':'吃饭啦'})
        self.assertEqual(answer['mode'],'demo');self.assertIn('碗',answer['answer'])
        self.request('/api/settings',{'model_key':'fixture-secret','base_url':self.upbase+'/v1'})
        s=self.request('/api/state');self.assertTrue(s['config']['model_key_set']);self.assertNotIn('fixture-secret',json.dumps(s))
        
        if os.name!='nt':self.assertEqual(os.stat(Path(TEMP.name)/'credentials.json').st_mode & 0o777,0o600)
    def test_02_model_and_scope_isolation(self):
        self.request('/api/settings',{'engine':'model','model':'fixture-model','base_url':self.upbase+'/v1','model_key':'fixture-secret'})
        d=self.request('/api/model/test',{});self.assertTrue(d['ok'])
        d=self.request('/api/chat',{'message':'web-only-message'});self.assertEqual(d['mode'],'model')
        import brain
        brain.chat('private-message','qq:private:42')
        last=next(c for c in reversed(CALLS) if c[0]=='/v1/chat/completions')
        self.assertNotIn('web-only-message',json.dumps(last[1]));self.assertEqual(last[2],'Bearer fixture-secret')
    def test_03_qq_signed_auto_reply_and_dedup(self):
        self.request('/api/settings',{'onebot_url':self.upbase,'qq_users':'42','qq_groups':'100','qq_auto':True})
        self.assertTrue(self.request('/api/qq/test',{})['ok'])
        event={'post_type':'message','message_type':'private','self_id':888,'user_id':42,'message_id':999,'message':[{'type':'text','data':{'text':'hello from qq'}}]}
        raw=json.dumps(event).encode();signature='sha1='+hmac.new(store.config()['qq_secret'].encode(),raw,hashlib.sha1).hexdigest()
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/qq/event',event)
        self.assertEqual(e.exception.code,403)
        d=self.request('/api/qq/event',event,{'X-Signature':signature});self.assertTrue(d['accepted'])
        d=self.request('/api/qq/event',event,{'X-Signature':signature});self.assertFalse(d['accepted'])
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            sends=[c for c in CALLS if c[0]=='/send_private_msg']
            if sends:break
            time.sleep(.05)
        self.assertEqual(len(sends),1);self.assertEqual(sends[0][1]['user_id'],42)
        self.assertEqual(sends[0][1]['message'][0]['type'],'text')
    def test_04_permissions_and_group_mention(self):
        event={'post_type':'message','message_type':'private','self_id':888,'user_id':77,'message_id':1000,'raw_message':'hello'}
        self.assertFalse(channels.receive(event)['accepted'])
        event.update(message_type='group',group_id=100,user_id=42,message=[{'type':'text','data':{'text':'hello'}}])
        self.assertFalse(channels.receive(event)['accepted'])
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/chat',{'message':'x'},{'X-Fish-Token':'wrong'})
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/chat',{'message':'x'},{'Origin':'https://untrusted.example'})
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(ValueError):public_url('https://127.0.0.1')
    def test_05_pause_and_key_change_invalidates_check(self):
        self.request('/api/pause',{});self.assertFalse(store.config()['qq_auto'])
        self.request('/api/settings',{'model_key':'replacement-secret'})
        self.assertNotIn('model',self.request('/api/state')['checks'])
        with self.assertRaises(urllib.error.HTTPError):self.request('/api/send',{'channel':'qq','target':'bad','message':'x'})

if __name__=='__main__':unittest.main(verbosity=2)
