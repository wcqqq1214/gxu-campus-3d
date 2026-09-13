"""Stable schematic tree orientation shared by data checks and Blender.

Matches lib/campus/vegetation.ts. Positions are stored at decimetre precision.
The angle is an aesthetic default, not a surveyed tree orientation.
"""
import math


def tree_rotation(x, y):
    key = f'{round(x * 10)},{round(y * 10)}'
    value = 2166136261
    for byte in key.encode('ascii'):
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value / 4294967296 * math.tau
