"""Extract the customer ZIP and cold-start that copy, without developer data."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import urllib.request
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'data/python'))
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(ROOT/'data/browsers'))
from playwright.sync_api import sync_playwright,expect
archive=ROOT.parent/'library-files'/'大肥鱼-Codex演示交付-v4.zip'
with tempfile.TemporaryDirectory() as temp:
 with ZipFile(archive) as z:
  for name in z.namelist():
   target=(Path(temp)/name).resolve();assert target.is_relative_to(Path(temp).resolve())
   assert '/data/' not in name and 'credentials.json' not in name and '.env' not in name
  assert any(n.endswith('/文档/大肥鱼-介绍与演示指南-v4.pdf') for n in z.namelist())
  command=next(i for i in z.infolist() if i.filename.endswith('/启动桌宠.command') and '/项目/' not in i.filename)
  assert (command.external_attr>>16)&stat.S_IXUSR
  z.extractall(temp)
 bundle=next(Path(temp).iterdir());project=bundle/'项目'
 env={**os.environ,'FISH_DATA_DIR':str(project/'data')}
 for key in ('FISH_MODEL_KEY','FISH_ONEBOT_URL','FISH_ONEBOT_TOKEN','FISH_WECOM_WEBHOOK'):env.pop(key,None)
 report=subprocess.run([sys.executable,str(project/'doctor.py')],env=env,capture_output=True,text=True,check=True)
 assert '未配置' in report.stdout
 process=subprocess.Popen([sys.executable,str(project/'app.py'),'--port','0'],env=env,stdout=subprocess.PIPE,text=True)
 try:
  base=process.stdout.readline().strip().split()[-1]
  health=json.load(urllib.request.urlopen(base+'/api/health'));assert health['version']=='4.0.0'
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1100})
   page.goto((bundle/'先看这里.html').as_uri());expect(page.locator('#preview')).to_have_attribute('data-form','chibi')
   page.locator('#mature').click();expect(page.locator('#preview')).to_have_attribute('data-form','mature')
   page.goto(base);expect(page.locator('#mode-badge')).to_contain_text('互动体验')
   page.locator('#message').fill('开饭啦');page.locator('#chat-submit').click();expect(page.locator('#messages')).to_contain_text('我先把碗拿来')
   page.evaluate("()=>location.hash='connect'");expect(page.locator('#deepseek-dialog')).to_be_visible();page.locator('#deepseek-inspect').click();expect(page.locator('#deepseek-result')).to_contain_text('API Key');page.locator('#deepseek-close').click()
   browser.close()
  state=json.load(urllib.request.urlopen(base+'/api/state'));assert not state['config']['model_key_set'];assert state['config']['model']=='deepseek-flash'
  print('PASS: ZIP integrity, executable starter, no credentials/data, packaged PDF, extracted-copy diagnostics, offline preview, cold-started v4 service, demo chat and official onboarding')
 finally:
  process.terminate();process.wait(timeout=10)
