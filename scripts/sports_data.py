"""Derive complete athletics grounds without changing the original OSM topology."""
import json
import math
from shapely.geometry import Polygon, shape
from shapely.ops import transform


def prepare_sports(root, features, project):
    records = json.loads((root / 'data/sports.json').read_text())
    for record in records:
        feature = next(f for f in features if f['id'] == record['osmId'])
        mapped = transform(project, shape(feature['geometry']))
        # A track relation's hole is its playing field, not a vacant planting area.
        ground = Polygon(mapped.exterior)
        rect = ground.minimum_rotated_rectangle
        corners = list(rect.exterior.coords)
        a, b = max(zip(corners, corners[1:]), key=lambda pair: math.dist(*pair))
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dy < 0:
            dx, dy = -dx, -dy
        record.update(center=list(rect.centroid.coords)[0], rotation=math.atan2(-dx, dy),
                      ground=list(ground.exterior.coords), bounds=list(ground.bounds),
                      osmEditedAt=feature['properties']['osmEditedAt'],
                      osmVersion=feature['properties']['osmVersion'])
        record.update(category='culture',placeKind='sports',height=0,distance=235,
                      cameraOffset=[-.35,1.25,1],zone='west' if record['id']=='west-track' else 'east',
                      sourceUrl=feature['properties']['sourceUrl'],
                      reference='westTrack2025' if record['id']=='west-track' else 'eastTrack2026',
                      description='红色环形跑道环绕足球内场，西侧为篮球场区，可近看场线、篮板与篮网。' if record['id']=='east-track' else '红色环形跑道环绕绿色足球内场，支持近景查看分道线、球场标线与球门。',
                      detail=record['precision'])
    return records
