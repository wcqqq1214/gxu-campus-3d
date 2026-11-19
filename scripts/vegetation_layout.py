"""Stable schematic tree orientation shared by data checks and Blender.

Matches lib/campus/vegetation.ts. Positions are stored at decimetre precision.
The angle is an aesthetic default, not a surveyed tree orientation.
"""

import json
import math
from functools import cache
from pathlib import Path


@cache
def _crown_widths():
    path = Path(__file__).resolve().parents[1] / 'data/west-dorm-crown-widths.json'
    return {(x, y): width for x, y, width in json.loads(path.read_text())}


def tree_scale(x, y, height):
    vertical = height / 9
    horizontal = vertical * _crown_widths().get((x, y), 1)
    return horizontal, horizontal, vertical


def tree_rotation(x, y):
    key = f'{round(x * 10)},{round(y * 10)}'
    value = 2166136261
    for byte in key.encode('ascii'):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value / 4294967296 * math.tau
