"""Isolated real-browser smoke test. --live-browser also reads a public HTTPS page."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import json
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(Path(__file__).parent/'data/browsers'))
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).parent
with tempfile.TemporaryDirectory() as data:
 env={**os.environ,'FISH_DATA_DIR':data,'FISH_MODEL_KEY':'','FISH_ONEBOT_URL':'','FISH_ONEBOT_TOKEN':'','FISH_WECOM_WEBHOOK':''}
 server=subprocess.Popen([sys.executable,str(ROOT/'app.py'),'--port','0'],env=env,stdout=subprocess.PIPE,text=True)
 try:
  base=server.stdout.readline().strip().split()[-1]
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True)
   page=b.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base);expect(page.locator('#mode-badge')).to_contain_text('互动体验')
   expect(page.locator('#pet-canvas')).to_have_attribute('data-form','chibi')
   page.locator('#form-mature').click();expect(page.locator('#pet-canvas')).to_have_attribute('data-form','mature')
   page.wait_for_timeout(500);page.screenshot(path=str(ROOT/'preview-mature.png'),full_page=True)
   page.reload();expect(page.locator('#pet-canvas')).to_have_attribute('data-form','mature')
   page.locator('#pet-wave').click();expect(page.locator('#pet-canvas')).to_have_attribute('data-action','wave')
   page.locator('#pet-sleep').click();expect(page.locator('#pet-canvas')).to_have_attribute('data-action','sleep')
   page.locator('#pet-sleep').click();page.locator('#pet-motion').click()
   before=page.locator('#pet-canvas').get_attribute('data-frame');page.wait_for_timeout(400);assert page.locator('#pet-canvas').get_attribute('data-frame')==before
   page.locator('#pet-motion').click();page.locator('#form-chibi').click();expect(page.locator('#pet-canvas')).to_have_attribute('data-form','chibi')
   page.locator('#feed').click();assert '白饭' in page.locator('#pet-speech').inner_text()
   page.locator('#message').fill('开饭啦');page.locator('#chat-submit').click()
   expect(page.locator('#messages')).to_contain_text('我先把碗拿来')
   page.locator('[data-tab=settings]').click()
   assert page.locator('#base-url').input_value()=='https://api.deepseek.com'
   assert page.locator('#model').input_value()=='deepseek-flash'
   page.locator('#test-model').click();expect(page.locator('#model-result')).to_contain_text('API Key')
   page.locator('#settings [data-connect]').click();expect(page.locator('#deepseek-dialog')).to_be_visible()
   assert page.locator('#deepseek-login-link').get_attribute('href')=='https://platform.deepseek.com/'
   page.locator('#deepseek-inspect').click();expect(page.locator('#deepseek-result')).to_contain_text('API Key')
   page.locator('#deepseek-close').click()
   page.locator('[data-tab=channels]').click();page.get_by_text('如何让 QQ 消息传进来？').click();page.locator('#qq-setup').click()
   expect(page.locator('#qq-setup-text')).to_be_visible();assert '/api/qq/event' in page.locator('#qq-setup-text').inner_text()
   page.locator('[data-tab=character]').click();assert page.locator('.sheet-image').first.evaluate('e=>e.naturalWidth')>0
   if '--live-browser' in sys.argv:
    page.locator('[data-tab=explore]').click()
    page.locator('#task-form button[type=submit],#task-form .full').click()
    expect(page.locator('#task-result')).to_contain_text('任务已排队',timeout=15000)
    expect(page.locator('#jobs')).to_contain_text('Example Domain',timeout=60000)
    expect(page.locator('#jobs .badge').first).to_have_text('已完成',timeout=20000)
    expect(page.locator('.job-shot')).to_be_visible()
    page.screenshot(path=str(ROOT/'preview-browser.png'),full_page=True)
    print('PASS: real HTTPS browser task, text extraction, screenshot and UI completion state')
   page.locator('[data-tab=phone]').click();page.locator('#scan-devices').click()
   expect(page.locator('#phone-result')).not_to_have_text('正在处理……')
   page.locator('[data-tab=home]').click();page.locator('#toast').evaluate('(e)=>e.hidden=true')
   page.evaluate('()=>window.fish.play("idle")');page.wait_for_timeout(80)
   page.screenshot(path=str(ROOT/'preview.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(ROOT/'preview-mobile.png'),full_page=True)
   assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
   assert not errors, errors
   print('PASS: real UI, both sprite forms, form persistence, wave/sleep/pause, feed, demo chat, missing-key error, QQ setup, device detection, mobile layout; no JS errors')
   b.close()
 finally:
  server.terminate();server.wait(timeout=15)
