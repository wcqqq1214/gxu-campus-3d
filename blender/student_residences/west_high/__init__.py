"""West campus student residences 16–28, including the shared 24/25 footprint."""

_BUILDINGS = {
    'way/759140880': 16,
    'way/759129517': 17,
    'way/759140881': 18,
    'way/759129518': 19,
    'way/759129519': 20,
    'way/759140892': 21,
    'way/759140893': 22,
    'way/759140894': 23,
    'way/759140884': 24,
    'way/880036344': 26,
    'way/759129520': 27,
    'relation/11970576': 28,
}
IDS = set(_BUILDINGS)


def refine(b, z, C, detail, baseline):
    """Build the residence on its existing scene mesh and elevation datum."""
    from .walls import _attic, exterior_palette

    number = _BUILDINGS[b['id']]
    mats = exterior_palette(C)
    if number <= 20:
        from .brick_blocks import gallery_block

        return gallery_block(b, z, C, mats, detail, baseline)
    if number in (21, 27):
        from .brick_blocks import brick_block

        return brick_block(b, z, C, mats, detail, baseline, number)
    if number == 22:
        _attic(
            baseline, z + b['height'] - b['height'] / b['levels'] + 0.1, mats['chalk']
        )
        return baseline
    if number == 23:
        from .west23 import west23

        return west23(b, z, C, detail, baseline, mats)
    from .courtyards import pale_residence

    return pale_residence(number, b, z, C, detail, baseline, mats)
