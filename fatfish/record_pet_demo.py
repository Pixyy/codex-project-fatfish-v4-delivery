"""Record actual web sprite interactions; native Qt uses the same manifest."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(ROOT/'data/browsers'))
from playwright.sync_api import sync_playwright,expect
with tempfile.TemporaryDirectory() as data:
 env={**os.environ,'FISH_DATA_DIR':data,'FISH_MODEL_KEY':'','FISH_ONEBOT_URL':'','FISH_ONEBOT_TOKEN':'','FISH_WECOM_WEBHOOK':''}
 server=subprocess.Popen([sys.executable,str(ROOT/'app.py'),'--port','0'],env=env,stdout=subprocess.PIPE,text=True)
 try:
  base=server.stdout.readline().strip().split()[-1]
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True)
   context=b.new_context(viewport={'width':1400,'height':1100},record_video_dir=data,record_video_size={'width':1400,'height':1100})
   page=context.new_page();page.goto(base);expect(page.locator('#pet-canvas')).to_have_attribute('data-form','chibi')
   page.mouse.move(1250,170);page.wait_for_timeout(1800)
   page.locator('#pet-wave').click();page.wait_for_timeout(1500)
   page.locator('#pet-jump').click();page.wait_for_timeout(1300)
   page.locator('#feed').click();page.wait_for_timeout(1500)
   page.locator('#form-mature').click();page.wait_for_timeout(1800)
   page.locator('#pet-wave').click();page.wait_for_timeout(1700)
   page.locator('#feed').click();page.wait_for_timeout(2200)
   page.locator('#pet-sleep').click();page.wait_for_timeout(1600)
   page.locator('#pet-sleep').click();page.locator('#form-chibi').click();page.wait_for_timeout(1500)
   page.locator('#message').fill('大肥鱼，开饭啦');page.locator('#chat-submit').click();expect(page.locator('#messages')).to_contain_text('我先把碗拿来');page.wait_for_timeout(2000)
   video=page.video;context.close()
   dest=ROOT.parent/'library-files'/'fatfish-v4-demo.webm';video.save_as(dest);b.close();print(dest,round(dest.stat().st_size/1024),'KiB')
 finally:
  server.terminate();server.wait(timeout=10)
