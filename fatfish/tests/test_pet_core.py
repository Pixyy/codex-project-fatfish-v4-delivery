import json
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pet_core import Animation,manifest

class PetAnimations(unittest.TestCase):
 def test_atlas_dimensions_and_every_referenced_frame(self):
  spec=manifest()
  for key,form in spec['forms'].items():
   path=ROOT/'static'/form['atlas'].lstrip('/')
   with path.open('rb') as f:header=f.read(24)
   self.assertEqual(header[:8],b'\x89PNG\r\n\x1a\n')
   width,height=struct.unpack('>II',header[16:24])
   self.assertEqual(width%form['columns'],0);self.assertEqual(height%form['rows'],0)
   for action,clip in form['animations'].items():
    self.assertEqual(len(clip['frames']),len(clip['durations']))
    self.assertTrue(all(d>0 for d in clip['durations']))
    for col,row in clip['frames']:
     self.assertTrue(0<=col<form['columns'] and 0<=row<form['rows'],(key,action,col,row))
 def test_blink_and_pause(self):
  p=Animation();self.assertEqual(p.frame,(0,0));p.advance(400);self.assertEqual(p.frame,(2,0))
  p.motion=False;before=p.frame;p.advance(1000);self.assertEqual(p.frame,before)
 def test_action_returns_to_idle_and_sleep_stays(self):
  for form in ('chibi','mature'):
   p=Animation(form);p.play('wave')
   for _ in range(8):p.advance(500)
   self.assertEqual(p.action,'idle')
   p.play('sleep')
   for _ in range(8):p.advance(500)
   self.assertEqual(p.action,'sleep')
 def test_switch_during_action_resets_valid_frame(self):
  p=Animation();p.play('jump');p.advance(600);p.set_form('mature')
  self.assertEqual(p.index,0);self.assertEqual(p.action,'jump');self.assertEqual(p.frame,(2,0))
 def test_pointer_directions(self):
  p=Animation();self.assertEqual(p.look_frame(0,-100),(0,9));self.assertEqual(p.look_frame(100,0),(4,9));self.assertEqual(p.look_frame(0,100),(0,10));self.assertEqual(p.look_frame(-100,0),(4,10))
  p.set_form('mature');self.assertEqual(p.look_frame(100,0),p.frame)

if __name__=='__main__':unittest.main(verbosity=2)
