"""End-to-end onboarding UI with an explicit local DeepSeek-shaped HTTP fixture."""
import json,os,sys,tempfile,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(ROOT/'data/browsers'))
from playwright.sync_api import sync_playwright,expect
with tempfile.TemporaryDirectory() as data:
 os.environ['FISH_DATA_DIR']=data
 for k in ('FISH_MODEL_KEY','FISH_ONEBOT_URL','FISH_ONEBOT_TOKEN','FISH_WECOM_WEBHOOK'):os.environ.pop(k,None)
 import app,store,provider
 store.init()
 hold=threading.Event();chat_calls=[]
 class Fixture(BaseHTTPRequestHandler):
  def log_message(self,*_):pass
  def reply(self,d,status=200):
   self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(d).encode())
  def do_GET(self):
   key=self.headers.get('Authorization','').removeprefix('Bearer ')
   if key=='invalid':return self.reply({},401)
   if self.path=='/models':return self.reply({'data':[{'id':'deepseek-flash','name':'DeepSeek Flash'},{'id':'deepseek-v4-pro'}]})
   return self.reply({'is_available':key!='zero','balance_infos':[{'currency':'CNY','total_balance':'0.00' if key=='zero' else '8.00'}]})
  def do_POST(self):
   body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   text=body['messages'][-1]['content']
   if '连接成功' not in text:
    chat_calls.append(body);hold.wait(timeout=8)
   self.reply({'choices':[{'message':{'role':'assistant','content':'fixture-ui-reply'}}]})
 upstream=ThreadingHTTPServer(('127.0.0.1',0),Fixture);server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
 for s in (upstream,server):threading.Thread(target=s.serve_forever,daemon=True).start()
 upstream_url='http://127.0.0.1:'+str(upstream.server_port)
 with patch.object(provider,'DEEPSEEK_BASE',upstream_url),patch.object(provider,'is_official',lambda u:u.rstrip('/')==upstream_url):
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1100})
    page.goto('http://127.0.0.1:'+str(server.server_port));expect(page.locator('#mode-badge')).to_contain_text('互动体验')
    page.locator('[data-connect]').first.click();expect(page.locator('#deepseek-dialog')).to_be_visible()
    page.screenshot(path=str(ROOT/'preview-deepseek.png'),full_page=True)
    page.locator('#deepseek-key').fill('invalid');page.locator('#deepseek-connect').click();expect(page.locator('#deepseek-result')).to_contain_text('HTTP 401')
    assert not store.public_config()['model_key_set']
    page.locator('#deepseek-key').fill('zero');page.locator('#deepseek-inspect').click();expect(page.locator('#deepseek-account')).to_contain_text('余额不足')
    page.locator('#deepseek-connect').click();expect(page.locator('#deepseek-result')).to_contain_text('余额不足');assert not store.public_config()['model_key_set']
    page.locator('#deepseek-key').fill('fixture-valid-key');page.locator('#deepseek-inspect').click();expect(page.locator('#deepseek-account')).to_contain_text('8.00')
    page.locator('#deepseek-connect').click();expect(page.locator('#deepseek-success')).to_be_visible();assert not page.locator('#deepseek-key').input_value()
    page.locator('#deepseek-return').click();expect(page.locator('#mode-badge')).to_contain_text('真实 AI')
    page.locator('#message').fill('first request');page.locator('#chat-submit').click();expect(page.locator('#typing')).to_be_visible()
    page.locator('#message').press('Control+Enter');page.locator('#message').press('Control+Enter');page.locator('#message').fill('下一句话保留')
    hold.set();expect(page.locator('#messages')).to_contain_text('fixture-ui-reply');expect(page.locator('#typing')).to_be_hidden()
    assert page.locator('#message').input_value()=='下一句话保留';assert len(chat_calls)==1
    page.locator('[data-tab=settings]').click();page.once('dialog',lambda d:d.accept());page.locator('#forget-model').click();expect(page.locator('#model-result')).to_contain_text('已忘记')
    assert not store.public_config()['model_key_set'];expect(page.locator('#mode-badge')).to_contain_text('互动体验')
    browser.close()
    print('PASS: official login links, empty/invalid/zero-balance handling, model selection, verified connection, write-only key, typing indicator, duplicate-send guard, draft preservation, disconnect')
  finally:
   hold.set()
   for s in (server,upstream):s.shutdown();s.server_close()
