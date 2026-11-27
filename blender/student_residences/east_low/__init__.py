"""East campus student residences in campus world coordinates (metres)."""

COMB = 'way/759191492'
EAST1 = 'way/1474800690'
EAST7 = 'way/1474800689'
ROW = {f'way/{n}' for n in range(759191479, 759191483)}
NORTH = {'way/760176670', 'way/760176671', 'way/760176668'}
EAST16 = 'relation/11971048'
EAST18 = 'way/1474800688'
EAST12 = 'student-dorm/east-12'
BASELINE_IDS = frozenset(NORTH | {EAST16})
IDS = BASELINE_IDS | ROW | {COMB, EAST1, EAST7, EAST12, EAST18}


def seven_treatment(e):
    if e.length > 14 and e.ny < 0:
        return 'twoToneGallery'
    if e.length > 12:
        return 'twoTone'
    if e.length > 8 and abs(e.uy) > 0.94:
        return 'east7' if e.uy < 0 else 'west7'
    return 'return7'


def refine(b, z, C, detail, baseline):
    """Build a residence in campus metres, retaining the supplied mesh on unmodified sides."""
    key = b['id']
    if key not in IDS:
        raise KeyError(key)

    from geometry import Mesh

    from .blocks import comb, low_hipped_block, north_spine, shell
    from .north import dorm16, north_facade
    from .walls import Edge, colors

    P = colors(C)
    if key in NORTH:
        return north_facade(baseline, b, z, C, P, detail)
    if key == EAST16:
        return dorm16(baseline, b, z, P, detail)
    m = Mesh()
    ring = b['polygons'][0][0]
    if key == COMB:
        comb(m, b, z, P, detail)
    elif key == EAST18:
        shell(
            m,
            ring,
            z,
            18,
            3.05,
            lambda e: 'tower' if e.length >= 18 else 'towerEnd',
            P,
            detail,
        )
        north_spine(m, Edge(ring[-2], ring[0]), z, P)
    elif key in ROW:

        def face(e):
            if e.ny > 0.7:
                return 'balconies'
            if e.ny < -0.7:
                return 'gallery' if e.length > 14 else 'stair'
            return 'blank'

        shell(
            m,
            ring,
            z,
            6,
            b['height'] / 6,
            face,
            P,
            detail,
            coping=0.58 * b['height'] / 6 - 0.11,
        )
    elif key == EAST7:
        shell(m, ring, z, 6, b['height'] / 6, seven_treatment, P, detail)
    elif key == EAST1:
        shell(
            m,
            ring,
            z,
            6,
            b['height'] / 6,
            lambda e: (
                'slant'
                if e.length > 15 and e.ny < 0
                else 'plain'
                if e.length > 15
                else 'slantEnd'
            ),
            P,
            detail,
        )
    elif key == EAST12:
        low_hipped_block(m, ring, z, b, P, detail)
    return m
