"""Shared manifest and deterministic sprite timing, independent of GUI libraries."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / 'static' / 'pets' / 'manifest.json'


def manifest():
    return json.loads(MANIFEST_PATH.read_text('utf-8'))


class Animation:
    def __init__(self, form='chibi', spec=None):
        self.spec = spec or manifest()
        self.form = form if form in self.spec['forms'] else 'chibi'
        self.action = 'idle'
        self.index = 0
        self.elapsed = 0
        self.motion = True

    @property
    def form_spec(self):
        return self.spec['forms'][self.form]

    @property
    def clip(self):
        return self.form_spec['animations'][self.action]

    @property
    def frame(self):
        return tuple(self.clip['frames'][self.index])

    def set_form(self, form):
        if form not in self.spec['forms']:
            raise ValueError('未知形态')
        self.form = form
        self.play(self.action)

    def play(self, action):
        if action not in self.form_spec['animations']:
            raise ValueError('未知动作')
        self.action = action
        self.index = 0
        self.elapsed = 0

    def advance(self, milliseconds):
        if not self.motion:
            return self.frame
        self.elapsed += max(0, min(1000, milliseconds))
        while self.elapsed >= self.clip['durations'][self.index]:
            self.elapsed -= self.clip['durations'][self.index]
            self.index += 1
            if self.index >= len(self.clip['frames']):
                if self.clip.get('loop'):
                    self.index = 0
                else:
                    self.play('idle')
                    break
        return self.frame

    def look_frame(self, dx, dy):
        directions = self.form_spec.get('lookDirections', [])
        if not directions or self.action != 'idle' or not self.motion:
            return self.frame
        # The upstream directions start at up, then rotate clockwise.
        degrees = math.degrees(math.atan2(dx, -dy)) % 360
        direction = min(directions, key=lambda d: abs((d['degrees'] - degrees + 180) % 360 - 180))
        return direction['column'], direction['row']
