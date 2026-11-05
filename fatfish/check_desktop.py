"""Qt render + event + real local HTTP checks in an isolated offscreen session."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
with tempfile.TemporaryDirectory() as data:
 os.environ['FISH_DATA_DIR']=data
 for key in ('FISH_MODEL_KEY','FISH_ONEBOT_URL','FISH_ONEBOT_TOKEN','FISH_WECOM_WEBHOOK'):os.environ.pop(key,None)
 import desktop
 from PySide6.QtCore import Qt,QPoint
 from PySide6.QtTest import QTest
 from PySide6.QtWidgets import QApplication
 from http.server import ThreadingHTTPServer
 import app as server_app
 import store
 from local_backend import Backend
 store.init()
 server=ThreadingHTTPServer(('127.0.0.1',0),server_app.Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 gui=QApplication([])
 backend=Backend();backend.base='http://127.0.0.1:'+str(server.server_port);backend.token=server_app.TOKEN
 pet=desktop.PetWindow(backend,auto_connect=False);pet.ready=True;pet.prefs['follow']=False;pet.show()
 try:
  assert pet.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
  assert pet.windowFlags() & Qt.WindowType.FramelessWindowHint
  assert pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
  before=pet.player.frame;QTest.qWait(440);assert pet.player.frame!=before
  pet.say('透明桌宠 · 拖动 / 双击聊天 / 右键变身')
  pet.grab().save(str(ROOT/'preview-desktop-chibi.png'))
  pet.set_form('mature');QTest.qWait(700)
  assert pet.player.form=='mature' and store.config()['pet_form']=='mature'
  pet.feed();QTest.qWait(80);assert pet.player.frame==(1,1)
  atlas,source,target=pet.sprite('mature',pet.player.frame);assert target.top()>pet.speech.geometry().bottom()
  from PySide6.QtGui import QBitmap,QRegion
  alpha=atlas.copy(source.toRect()).toImage().createAlphaMask(Qt.ImageConversionFlag.ThresholdAlphaDither)
  assert not QRegion(QBitmap.fromImage(alpha)).isEmpty()
  pet.grab().save(str(ROOT/'preview-desktop-mature.png'))
  menu=pet.make_menu();size=next(a.menu() for a in menu.actions() if a.text()=='大小');size.actions()[0].trigger()
  assert pet.scale==.75 and pet.width()>200
  _,_,target=pet.sprite('mature',pet.player.frame);assert target.top()>pet.speech.geometry().bottom()
  pet.set_scale(1.0)
  pet.move(100,20)
  QTest.mousePress(pet,Qt.MouseButton.LeftButton,pos=QPoint(150,250))
  QTest.mouseMove(pet,QPoint(180,255),40)
  QTest.mouseRelease(pet,Qt.MouseButton.LeftButton,pos=QPoint(180,255))
  assert pet.x()!=100 or pet.y()!=20,'drag did not move window'
  pet.sleep();assert pet.player.action=='sleep';pet.touch();assert not pet.sleeping
  pet.open_chat();pet.chat_dialog.input.setText('开饭啦');pet.chat_dialog.submit()
  deadline=time.monotonic()+5
  while pet.chat_pending and time.monotonic()<deadline:QTest.qWait(50)
  assert not pet.chat_pending
  assert '我先把碗拿来' in pet.chat_dialog.output.toPlainText()
  assert store.messages()[-1]['role']=='assistant'
  pet.toggle_motion();frame=pet.player.frame;QTest.qWait(300);assert pet.player.frame==frame
  assert pet.clamp(QPoint(-9000,-9000)).x()>=0
  print('PASS: native transparent window flags, real sprite frames, form persistence via HTTP, feed/sleep, scale menu, drag, real demo chat request, motion pause and screen bounds')
 finally:
  pet.close();gui.processEvents();server.shutdown();server.server_close()
