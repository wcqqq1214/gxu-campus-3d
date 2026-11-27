"""Build the surveyed campus residences on their original ordinary-building meshes."""

from generic_buildings import ordinary_building

from . import east_high, east_low, south, west_high, west_low

_BUILDERS = {
    building_id: group.refine
    for group in (west_low, west_high, south, east_low, east_high)
    for building_id in group.IDS
}
IDS = frozenset(_BUILDERS)
EAST_12 = east_low.EAST12
_BASELINE_IDS = (
    west_low.IDS
    | west_high.IDS
    | south.IDS
    | east_low.BASELINE_IDS
    | {'relation/12774256'}
)
# East 29–33 were modeled on the stone academic shell before their catalogue
# category changed to living. This affects which trim faces receive the repaint.
_STONE_SHELLS = {
    'relation/12874255',
    'relation/12874254',
    'relation/12874253',
    'way/760187414',
    'way/760187418',
}


def chunk_id(building_id):
    return 'chunk-dorm-' + building_id.replace('/', '-')


def build(b, z, colors, detail):
    if b['id'] in _STONE_SHELLS:
        b = dict(b, category='academic')
    baseline = (
        ordinary_building(b, z, colors, detail) if b['id'] in _BASELINE_IDS else None
    )
    return _BUILDERS[b['id']](b, z, colors, detail, baseline)
