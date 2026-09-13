"""Reapply existing model-space crown reservations after every tree source.

An explicit no-plant reservation is not a 3D collision claim. Ordinary streets,
unreviewed entrances and lake shores do not acquire new blanket crown buffers.
"""
from collections import Counter
from dataclasses import dataclass
import math
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree
from architecture_data import entrance_tree_masks
from infrastructure_footprints import strip_shape

INPUT_NAMES = ('infrastructure', 'buildings', 'landmarks', 'sports', 'basketball', 'shores')


@dataclass(frozen=True)
class CrownReservation:
    kind: str
    id: str
    geometry: object
    radius: float = 0


def crown_reservations(data):
    masks = []

    def add(kind, ident, geometry, radius=0):
        if geometry.is_empty or not geometry.is_valid or not math.isfinite(radius) or radius < 0:
            raise ValueError(f'Invalid vegetation reservation: {kind}/{ident}')
        masks.append(CrownReservation(kind, ident, geometry, radius))

    infrastructure = data['infrastructure']
    corridor = infrastructure['corridor']
    add('public-road', corridor['id'], strip_shape(corridor['path'], corridor['frames'], corridor['sections'], extra=1))
    for bridge in infrastructure['bridges']:
        # Reserve the final displayed approach, including both raised walks.
        # Its sampled path can differ slightly from the unsampled OSM line
        # used by early preparation; the early reservation remains in force.
        add('underpass',bridge['id'],LineString([p[:2] for p in bridge['underpass']]).buffer(
            bridge['pedestrian']['cutHalfWidth'],cap_style=2,join_style=2))
        add('bridge-deck',bridge['id'],LineString(bridge['upper']).buffer(
            bridge['deckWidth']/2-.1,cap_style=2,join_style=2))
    for bridge in infrastructure['lakeBridges']:
        add('lake-bridge',bridge['id'],LineString([p[:2] for p in bridge['path']]).buffer(bridge['width']/2))
    for ident,geometry in entrance_tree_masks(data['buildings']):
        add('entrance',ident,geometry)
    for landmark in data['landmarks']:
        if landmark.get('placeKind') == 'gate':
            add('gate',landmark['id'],box(*landmark['bounds']).buffer(2))
        elif landmark.get('placeKind') == 'sculpture':
            # Exact radial distance matches the existing sculpture rule;
            # a tessellated disk would introduce corner/boundary errors.
            add('sculpture',landmark['id'],Point(landmark['center']),landmark['radius'])
    for sport in data['sports']:
        add('sports',sport['id'],Polygon(sport['ground']))
    for bank in data['basketball']['banks']:
        add('basketball',bank['id'],Polygon(bank['ground']))
    stand = next((b for b in data['buildings'] if b['id']=='way/948683815'),None)
    if stand:
        x,y=stand['center']
        add('stand',stand['id'],box(x-11,y-40,x+11,y+40))
    for shore in data['shores']['shores']:
        for i,rings in enumerate(shore['capPolygons']):
            add('shore-cap',f"{shore['id']}:{i}",Polygon(rings[0],rings[1:]))
    return masks


def filter_reservations(trees,masks):
    index=STRtree([m.geometry for m in masks])
    extra=max((m.radius for m in masks),default=0)
    kept,removed=[],[]
    for i,row in enumerate(trees):
        if len(row)<4 or not all(math.isfinite(v) for v in row) or row[2]<=0:
            raise ValueError('Crown reservations require finite trees with positive height')
        point=Point(row[:2]);radius=4*row[2]/9+1
        extent=radius+extra
        nearby=index.query(box(row[0]-extent,row[1]-extent,row[0]+extent,row[1]+extent))
        hits=[]
        for j in sorted(int(j) for j in nearby):
            mask=masks[j];distance=mask.geometry.distance(point)
            if distance<=radius+mask.radius:
                hits.append({'kind':mask.kind,'id':mask.id,'distanceMeters':distance,
                             'thresholdMeters':radius+mask.radius})
        if hits:removed.append({'treeIndex':i,'tree':row,'masks':hits})
        else:kept.append(row)
    return kept,removed


def final_crown_reservations(trees,data):
    masks=crown_reservations(data)
    kept,removed=filter_reservations(trees,masks)
    return kept,{
        'method':'Existing model-space crown reservations, reapplied to all final upstream candidates; conservative radius 4 * height / 9 + 1 m.',
        'inputTrees':len(trees),'retainedTrees':len(kept),'removed':removed,
        'maskCounts':dict(sorted(Counter(m.kind for m in masks).items())),
        'limitations':[
            'Model planting reservations, not surveyed tree positions, actual canopy silhouettes or a full 3D clearance audit.',
            'Only existing modeled reservations are included; ordinary street shade and unsourced landscape areas are not cleared.',
            'Final underpass buffers follow the displayed sampled path; original upstream source-line exclusions remain additional constraints.',
        ],
    }
