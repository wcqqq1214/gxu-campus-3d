"""Redistribute the two west-campus grade breaks within the existing road alignments."""

import json
from functools import lru_cache
from pathlib import Path

import v5_platform_bed

AREAS = {'materials': (-624, -882, -586, -866), 'platform': (-739, -834, -705, -752)}


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


@lru_cache(maxsize=1)
def _profiles():
    return json.loads(
        Path(__file__).with_name('v5_roads_west_offsets.json').read_text()
    )


@lru_cache(maxsize=30000)
def _offset(x, y):
    if -624 < x < -586 and -882 < y < -866:
        name = 'materials'
        along = x
        side = y - (-874.563 + 0.00869 * (x + 622.606))
        # End the southern verge at the already-reviewed faculty foundation.
        verge = 6.4 if side > 0 else 4.77 + 0.00869 * (x + 622.606)
        weight = _smooth((verge - abs(side)) / (verge - 4.02))
    elif -739 < x < -705 and -834 < y < -752:
        name = 'platform'
        along = y
        side = (x + 723.463 + 0.18574 * (y + 796.526)) / 1.0171
        weight = _smooth((6.0 - abs(side)) / 3.4)
        if side > 0:
            # Continue through the east branch rather than ending the change
            # across a tyre track at the three-way junction.
            arm_y = -801.604 + 0.014 * (x + 722.474)
            arm = _smooth((16 - side) / 13) * _smooth((6.5 - abs(y - arm_y)) / 3.5)
            weight = max(weight, arm)
    else:
        return 0.0
    p = _profiles()[name]
    t = along - p['start']
    if not weight or t <= 0 or t >= len(p['dz']) - 1:
        return 0.0
    i = int(t)
    a, b = p['dz'][i : i + 2]
    ca, cb = p['cross'][i : i + 2]
    # Correct the DEM tilt across the wheel tracks while fading into the
    # retained shoulders. Continue just the longitudinal offset on the spur.
    half_width = 4.02 if name == 'materials' else 2.55
    cross = (ca + (cb - ca) * (t - i)) * max(-half_width, min(half_width, side))
    offset = weight * (a + (b - a) * (t - i) - cross)
    # Retain the source triangles that span each endpoint, including
    # the coarse road/soil join just north of the platform ramp.
    if name == 'materials':
        offset *= _smooth((x + 621.0) / 2.0)
    return offset


def _west_edge_bed(x, y):
    # The unsplit soil triangles interpolate across two narrow west-edge road
    # strips. Seat these strips without moving the outer ground or either tie.
    side = (x + 723.463 + 0.18574 * (y + 796.526)) / 1.0171
    across = _smooth((side + 5.2) / 1.35) * _smooth((-0.45 - side) / 1.25)
    # The narrow edge continues between the crest and the side-road mouth.
    strip = _smooth((y + 829.0) / 2.5) * _smooth((-798.5 - y) / 2.5)
    east = _smooth((side - 0.65) / 1.25) * _smooth((5.1 - side) / 1.5)
    east_tie = _smooth((y + 813.0) / 2.0) * _smooth((-804.5 - y) / 2.0)
    return 0.245 * across * strip + 0.075 * east * east_tie


def apply(base, colors):
    """Apply on the complete V4 mesh, before the ordinary road-export split."""
    for name in ('roads', 'terrain'):
        mesh = base[name]
        if getattr(mesh, '_west_v5_graded', False):
            continue
        for i, (x, y, z) in enumerate(mesh.v):
            if -739 < x < -586 and -882 < y < -752:
                dz = _offset(x, y)
                if name == 'terrain' and -830 < y < -798 and x < -705:
                    dz -= _west_edge_bed(x, y)
                if dz:
                    mesh.v[i] = (x, y, z + dz)
        mesh._west_v5_graded = True
    v5_platform_bed.apply(base, colors)
