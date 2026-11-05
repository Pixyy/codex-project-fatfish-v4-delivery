"""Provider onboarding through real local HTTP fixtures; no paid credential needed."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,brain,provider,store
from local_backend import Backend
from app_identity import compatible,instance_id

class ProviderFixture(BaseHTTPRequestHandler):
 calls=[]
 def log_message(self,*_):pass
 def respond(self,body,status=200):
  self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(body).encode())
 def do_GET(self):
  key=self.headers.get('Authorization','').removeprefix('Bearer ')
  self.calls.append(('GET',self.path,key,None))
  if key=='invalid':return self.respond({'error':{'message':'do not echo candidate '+key}},401)
  if self.path=='/models':return self.respond({'data':[{'id':'deepseek-flash','name':'DeepSeek Flash'},{'id':'deepseek-v4-pro'}]})
  if self.path=='/user/balance':return self.respond({'is_available':key!='zero','balance_infos':[{'currency':'CNY','total_balance':'0.00' if key=='zero' else '8.00'}]})
  return self.respond({},404)
 def do_POST(self):
  key=self.headers.get('Authorization','').removeprefix('Bearer ')
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  self.calls.append(('POST',self.path,key,body))
  if key=='chat-fails':return self.respond({'error':{'message':'sensitive upstream body'}},402)
  content='' if key=='empty' else 'fixture-connected'
  return self.respond({'choices':[{'message':{'role':'assistant','content':content}}]})

class DeepSeekOnboarding(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old_data=store.DATA;store.DATA=Path(self.temp.name)
  self.env=patch.dict(os.environ,{k:'' for k in ('FISH_MODEL_KEY','FISH_ONEBOT_URL','FISH_ONEBOT_TOKEN','FISH_WECOM_WEBHOOK')});self.env.start();store.init()
  ProviderFixture.calls=[]
  self.up=ThreadingHTTPServer(('127.0.0.1',0),ProviderFixture);self.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  for server in (self.up,self.server):threading.Thread(target=server.serve_forever,daemon=True).start()
  self.base='http://127.0.0.1:'+str(self.up.server_port)
  self.patches=[patch.object(provider,'DEEPSEEK_BASE',self.base),patch.object(provider,'is_official',lambda url:url.rstrip('/')==self.base)]
  for p in self.patches:p.start()
  self.client=Backend();self.client.base='http://127.0.0.1:'+str(self.server.server_port);self.client.token=app.TOKEN
 def tearDown(self):
  for s in (self.server,self.up):s.shutdown();s.server_close()
  for p in self.patches:p.stop()
  self.env.stop();store.DATA=self.old_data;self.temp.cleanup()
 def test_inspect_is_read_only_and_connect_validates_real_request(self):
  d=self.client.request('deepseek/inspect',{'api_key':' good '})
  self.assertTrue(d['account_verified']);self.assertTrue(d['can_chat']);self.assertEqual(d['recommended'],'deepseek-flash')
  self.assertFalse(store.public_config()['model_key_set']);self.assertFalse(any(c[0]=='POST' for c in ProviderFixture.calls))
  d=self.client.request('deepseek/connect',{'api_key':' good '})
  self.assertTrue(d['connected']);self.assertEqual(store.config()['engine'],'model');self.assertEqual(store.config()['model_key'],'good')
  payload=next(c[3] for c in ProviderFixture.calls if c[0]=='POST')
  self.assertEqual(payload['thinking'],{'type':'disabled'});self.assertEqual(payload['max_tokens'],64)
  public=json.dumps(self.client.request('state'));self.assertNotIn('"model_key":',public)
  self.assertNotIn('"good"',public);self.assertTrue(store.checks()['model']['ok'])
 def test_invalid_key_and_zero_balance_do_not_overwrite_working_settings(self):
  store.save_config({'model_key':'original','model':'original-model'})
  for key in ('invalid','zero','chat-fails','empty'):
   with self.subTest(key=key),self.assertRaises(ValueError):self.client.request('deepseek/connect',{'api_key':key})
   self.assertEqual(store.config()['model_key'],'original');self.assertEqual(store.config()['model'],'original-model')
  self.assertFalse(any(c[0]=='POST' and c[2]=='zero' for c in ProviderFixture.calls))
 def test_error_messages_separate_auth_balance_and_rate_limit(self):
  from net import RemoteError
  self.assertIn('Key',str(RemoteError(401)));self.assertIn('余额',str(RemoteError(402)));self.assertIn('速率',str(RemoteError(429)))
  self.assertNotIn('余额',str(RemoteError(429)))
 def test_disconnect_forgets_key_and_preserves_conversation(self):
  self.client.request('deepseek/connect',{'api_key':'good'})
  brain.chat('hello')
  self.client.request('deepseek/disconnect',{})
  self.assertFalse(store.public_config()['model_key_set']);self.assertEqual(store.config()['engine'],'demo');self.assertEqual(len(store.messages()),2)
 def test_pet_preferences_never_persist_environment_credentials(self):
  with patch.dict(os.environ,{'FISH_MODEL_KEY':'environment-fixture','FISH_ONEBOT_URL':'http://127.0.0.1:9999'}):
   store.save_config({'pet_form':'mature'})
   self.assertEqual(store.config()['model_key'],'environment-fixture')
   self.assertNotIn('environment-fixture',json.dumps(store.load_secrets()))
   with store.db() as c:body=c.execute('SELECT body FROM config_v2').fetchone()[0]
   self.assertNotIn('9999',body)
   with self.assertRaises(ValueError):provider.disconnect()
 def test_legacy_official_model_migrates_without_rewriting_custom_provider(self):
  store.save_config({'base_url':'https://api.deepseek.com/v1','model':'deepseek-chat'})
  self.assertEqual(store.config()['model'],'deepseek-flash')
  store.save_config({'base_url':self.base,'model':'deepseek-chat'})
  self.assertEqual(store.config()['model'],'deepseek-chat')
 def test_demo_turns_are_not_sent_to_real_model(self):
  brain.chat('demo-only-turn')
  self.client.request('deepseek/connect',{'api_key':'good'})
  brain.chat('real-turn')
  payload=[c[3] for c in ProviderFixture.calls if c[0]=='POST'][-1]
  self.assertNotIn('demo-only-turn',json.dumps(payload));self.assertEqual(store.messages()[0]['mode'],'demo')
 def test_connection_check_cannot_certify_changed_configuration(self):
  store.save_config({'model_key':'good','base_url':self.base})
  def response(*_,**__):
   store.save_config({'model':'changed-model'})
   return {'choices':[{'message':{'role':'assistant','content':'old reply'}}]}
  with patch.object(brain,'json_request',side_effect=response),self.assertRaisesRegex(ValueError,'配置已变化'):brain.test_model()
  self.assertNotIn('model',store.checks())
 def test_copy_identity_and_bootstrap_official_links(self):
  self.assertTrue(compatible({'app':'fatfish','version':'4.0.0','instance':instance_id()}))
  self.assertFalse(compatible({'app':'fatfish','version':'4.0.0','instance':'another-copy'}))
  links=self.client.request('bootstrap')['deepseek_links']
  self.assertEqual(links['login'],'https://platform.deepseek.com/')

if __name__=='__main__':unittest.main(verbosity=2)
