"""Peijiayuan and Xingjian student residences in campus world coordinates."""

_NUMBERS = {
    'way/1076517223': 19,
    'way/1076517222': 20,
    'relation/20510974': 22,
    'way/1501460952': 25,
    'relation/12774256': 27,
    'relation/12874255': 29,
    'relation/12874254': 30,
    'relation/12874253': 31,
    'way/760187414': 32,
    'way/760187418': 33,
    'way/760187417': 34,
    'way/760187416': 35,
}
IDS = frozenset(_NUMBERS)


def refine(b, z, C, detail, baseline):
    """Build the residence specified by its full campus building ID."""
    from .buildings import residence
    from .elevations import finish_elevations

    n = _NUMBERS[b['id']]
    mesh = residence(b, z, C, detail, baseline, n)
    if n == 25:
        return mesh
    return finish_elevations(b, z, C, detail, mesh, n)
