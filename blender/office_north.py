"""North elevation, GXU donation projects booklet, PDF p.35 (printed p.31)."""

from facade_bands import frame
from geometry import Mesh
from south_gate import inscription


def north_office_sign(building, datum, colors):
    # Edge 1 runs west to east. On its north face the reader's right is west.
    front = next(
        f
        for f in building['form']['facades']
        if f['part'] == 'central-four' and f['edge'] == 1
    )
    panel = next(p for p in front['rule']['panels'] if p['id'] == 'top-sign-wall')
    length, _, _, _, point = frame(front)
    seat = 0.025 + panel['depth'] / 2
    mesh = Mesh()
    for char, fraction, width in [
        ('办', 0.69, 1.22),
        ('公', 0.52, 1.22),
        ('楼', 0.35, 1.32),
    ]:
        glyph = inscription(
            char, 0, 0, 0, 1, 1, colors['timeLetter'], False, curve_resolution=2
        )
        span = [
            max(p[i] for p in glyph.v) - min(p[i] for p in glyph.v) for i in range(3)
        ]
        rear = max(p[1] for p in glyph.v)
        glyph.v = [
            (
                *point(
                    fraction - x * width / (span[0] * length),
                    seat - 0.002 + (rear - y) * 0.038 / span[1],
                ),
                datum + 11.45 + h * 1.05 / span[2],
            )
            for x, y, h in glyph.v
        ]
        mesh.extend(glyph)
    return mesh
