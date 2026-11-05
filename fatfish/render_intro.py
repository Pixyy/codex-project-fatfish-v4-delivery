"""Render the standalone introduction to PDF and validate its offline interactions."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'data/python'))
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(ROOT/'data/browsers'))
from playwright.sync_api import sync_playwright,expect
OUT=ROOT.parent/'library-files'
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1300,'height':1250})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto((OUT/'大肥鱼-介绍与离线预览-v4.html').as_uri())
 expect(page.locator('#preview')).to_have_attribute('data-form','chibi')
 page.locator('#mature').click();expect(page.locator('#preview')).to_have_attribute('data-form','mature')
 page.get_by_role('button',name='喂白饭').click();expect(page.locator('#preview')).to_have_attribute('data-action','feed')
 page.locator('#chibi').click();page.wait_for_timeout(500);page.evaluate('()=>{window.previewPet.play("idle");window.previewPet.setMotion(false)}');page.wait_for_timeout(80)
 page.screenshot(path=str(ROOT/'preview-intro.png'),full_page=True)
 page.pdf(path=str(OUT/'大肥鱼-介绍与演示指南-v4.pdf'),format='A4',print_background=True,prefer_css_page_size=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(ROOT/'preview-intro-mobile.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 browser.close()
 print('PASS: standalone offline HTML, both forms, action playback, mobile layout, PDF output')
