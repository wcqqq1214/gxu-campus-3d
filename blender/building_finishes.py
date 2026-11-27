"""Shared building finishes, including unused colours omitted from saved scenes."""

from geometry import material


def rgb(h):
    v = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in v)


def ensure_building_finishes(C):
    for name, color in [
        ('stoneWarm', '#c6b69f'),
        ('stoneCool', '#c5c0b1'),
        ('livingWarm', '#d0b39f'),
        ('livingCool', '#c3b0a4'),
        ('shadeGlass', '#3b6573'),
    ]:
        if name in C:
            continue
        C[name] = material(
            name,
            rgb(color),
            0.28 if name.endswith('Glass') else 0.84,
            0.28 if name.endswith('Glass') else 0,
        )
