"""Identify this extracted copy, so two demo folders never share credentials."""
import hashlib
import os
from pathlib import Path

VERSION = '4.0.0'
ROOT = Path(__file__).resolve().parent


def instance_id():
    data = Path(os.environ.get('FISH_DATA_DIR', ROOT / 'data')).resolve()
    material = os.path.normcase(str(ROOT)) + '|' + os.path.normcase(str(data))
    return hashlib.sha256(material.encode()).hexdigest()[:16]


def compatible(health):
    return health.get('app') == 'fatfish' and health.get('version', '').startswith('4.') and health.get('instance') == instance_id()
