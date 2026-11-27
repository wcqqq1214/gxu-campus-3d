"""Building-specific campus office geometry, in east/north/up world metres."""

from . import (
    agriculture,
    alumni,
    civic,
    entrances,
    faculty,
    graduate,
    junwu,
    masonry,
    network_tower,
    north,
    security,
    south,
)

IDS = frozenset(
    (
        *civic.MODEL_IDS,
        *faculty.MODEL_IDS,
        *agriculture.MODEL_IDS,
        'way/671978896',
        'way/759132929',
        south.ID,
    )
)


def build(b, z, C, detail, ordinary):
    fid = b['id']
    if fid == south.ID:
        return ordinary(south.prepare(b, C), z, C, detail)
    if fid == 'way/671978896':
        return north.north_office_model(b, z, C, detail, ordinary)
    if fid in faculty.MODEL_IDS:
        return faculty.build(b, z, C, detail, ordinary)
    if fid == 'way/759096561':
        return ordinary(b, z, C, detail)
    if fid == 'way/759185166':
        return agriculture.agriculture_end(b, z, C, ordinary(b, z, C, detail))
    if fid == 'way/759132929':
        return network_tower.tower(b, z, masonry.finishes(C), detail)
    if fid == 'way/1501460942':
        return graduate.graduate_school(
            b, z, C, detail, ordinary, civic.build, masonry.finishes(C)
        )
    if fid == 'way/759096563':
        return security.refine_security(
            civic.build(b, z, C, detail, ordinary), z, C, detail
        )
    if fid == 'way/759147086':
        return alumni.build(b, z, C, detail, ordinary)
    if fid == 'way/759337787':
        return junwu.build(b, z, C, detail, ordinary)
    if fid == 'way/957503108':
        return entrances.build(b, z, C, detail, ordinary)
    return civic.build(b, z, C, detail, ordinary)
