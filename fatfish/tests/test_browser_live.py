"""Opt-in network/browser tests. The agent model is a deterministic test fixture."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import store
import tasks

@unittest.skipUnless(os.environ.get('FISH_LIVE_TESTS')=='1','set FISH_LIVE_TESTS=1 to run public HTTPS browser checks')
class LiveBrowser(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.saved_data=store.DATA;store.DATA=Path(self.temp.name);store.init()
 def tearDown(self):
  store.DATA=self.saved_data;self.temp.cleanup()
 def test_read_public_page_with_verified_tls(self):
  t=tasks.Task('read',{'url':'https://example.com','goal':'','seconds':5,'steps':2});t.run()
  self.assertEqual(t.status,'done',t.body['summary']);self.assertIn('Example Domain',t.body['summary'])
  self.assertTrue((store.DATA/'artifacts'/f'{t.id}.png').read_bytes().startswith(b'\x89PNG'))
 def test_tool_loop_and_stop(self):
  calls=[]
  def fixture(messages,tools=None):
   calls.append(messages)
   if len(calls)==1:return {'role':'assistant','content':None,'tool_calls':[{'id':'fixture-scroll','type':'function','function':{'name':'scroll','arguments':'{}'}}]}
   return {'role':'assistant','content':'测试接口已收到滚动后的页面内容。'}
  with patch('brain.completion',side_effect=fixture):
   t=tasks.Task('agent',{'url':'https://example.com','goal':'读取','seconds':5,'steps':2});t.run()
  self.assertEqual(t.status,'done',t.body['summary']);self.assertEqual(len(calls),2)
  self.assertTrue(any(s['message']=='模型选择：向下滚动' for s in t.body['steps']))
  self.assertTrue(any(m['role']=='tool' for m in calls[1]))
  t=tasks.Task('read',{'url':'https://example.com','goal':'','seconds':5,'steps':2});t.stop.set();t.run();self.assertEqual(t.status,'cancelled')

if __name__=='__main__':unittest.main(verbosity=2)
