"""Display exclusions matched to the user's marked overview on 2026-09-12.

Keep the archived OSM snapshot intact. IDs identify the selected features, not
a blanket rule excluding every road or landscape outside the campus boundary.
"""
from shapely.geometry import box

GROUPS = {
    '北侧公园及外围支路': [
        476889357, 839763091, 839763092, 839763096, 839763097,
        839763098, 839763099, 839763100, 839763101, 839763104,
        1079901366, 1079901367, 1379222481,
    ],
    '西侧湖岸色块及校外支路': [
        1132535205, 1132535208, 1132535209, 1132535210, 1132535211,
        388982230, 388826386, 388826387, 388826388, 388826389,
        388826390, 839607569, 839607570, 808580060, 808580061,
        808580062, 808580063, 808580065,
    ],
    '西北空地零散球场及断头路': [1379222486, 1379222487, 1379222488, 956330025],
    '东侧校外支路': [839763111, 1546535666, 388863458, 770011119, 770011146, 977846122],
    '南侧色块及零散支路': [
        839711957, 808580069, 808580071, 808580072, 359276545,
        385985910, 388974683, 1492215397, 1492215398,
        1492215412, 1492215422, 1492215423, 1501460939,
    ],
}
EXCLUSIONS = {f'way/{i}': reason for reason, ids in GROUPS.items() for i in ids}
EXCLUSIONS['relation/6695830'] = '西侧明月湖色块'

# Stop dangling extensions at existing junctions. Coordinates are projected
# meters, shared with prepare_geodata; the adjoining main road stays continuous.
TRIMS = {
    'way/956330026': box(-5000, 410, 5000, 5000),
    'way/388863457': box(-5000, -109.216052, 5000, 5000),
    'way/1155152195': box(-5000, -965.03308, 5000, 5000),
}


def trim_corridor_chunk(chunk):
    """Shorten the detailed southern road chunk at its existing junction."""
    if chunk['id'] != 'infra-road-00':
        return
    cutoff = -965.03308
    path = chunk['path']
    if path[0][1] >= cutoff:
        return
    i = next(i for i, p in enumerate(path) if p[1] >= cutoff)
    t = (cutoff - path[i-1][1]) / (path[i][1] - path[i-1][1])
    for key in ('path', 'frames', 'sections'):
        values = chunk[key]
        first = [a + (b-a)*t for a,b in zip(values[i-1],values[i])]
        if key == 'path':
            first[1] = cutoff
        elif key == 'frames':
            length = sum(v*v for v in first)**.5
            first = [v/length for v in first]
        chunk[key] = [first] + values[i:]
    chunk['fence'] = [[False,False]] + chunk['fence'][i:]
    xs,ys = zip(*(p[:2] for p in chunk['path']))
    chunk['bounds'] = [min(xs)-10,min(ys)-10,max(xs)+10,max(ys)+10]
    chunk['displayTrim'] = '2026-09-12：在火炬路路口收束校外南端，保留其北侧农院路及桥梁。'
