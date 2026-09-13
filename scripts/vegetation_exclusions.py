"""Final ground-placement constraints shared by all upstream tree sources.

These masks prohibit planting a tree centre on occupied ground. They do not
classify canopy overhang as a collision or infer solid buildings from footprints.
Explicit no-tree zones and final 3D building checks remain additional passes.
"""
from collections import Counter
from dataclasses import dataclass
from shapely.geometry import Point, Polygon
from shapely.prepared import prep
from shapely.strtree import STRtree
from shore_data import effective_surfaces
from surroundings_data import surface_shape

INPUT_NAMES = ('surfaces', 'infrastructure', 'surroundings', 'campus-roads',
               'sites', 'pavings', 'shores', 'sports', 'buildings')


@dataclass(frozen=True)
class GroundMask:
    kind: str
    id: str
    geometry: object


def ground_masks(data):
    """Resolve the final displayed planar geometry, including courtyard holes."""
    masks, deferred = [], []

    def add(kind, ident, geometry):
        if geometry.is_empty:
            return  # Fully clipped/replaced surfaces are intentionally empty.
        if not geometry.is_valid or geometry.geom_type not in ('Polygon', 'MultiPolygon'):
            raise ValueError(f'Invalid final vegetation mask: {kind}/{ident}')
        masks.append(GroundMask(kind, ident, geometry))

    infra, surroundings, roads, sites = (data[n] for n in
                                       ('infrastructure', 'surroundings', 'campus-roads', 'sites'))
    final = effective_surfaces(data['surfaces'], [infra['surfaceOverrides'],
        surroundings['surfaceOverrides'], roads['surfaceOverrides'], sites['surfaceOverrides']],
        set(infra['replaceSurfaceIds']))
    for surface in final:
        kind = surface['kind']
        if surface.get('suppressed') or kind not in ('roads', 'water', 'sports'):
            continue
        tags = surface.get('tags', {})
        flag = lambda key: str(tags.get(key, 'no')).lower() not in ('no', 'false', '0', '')
        if kind == 'roads' and (flag('bridge') or flag('tunnel') or str(tags.get('layer', '0')) != '0'):
            deferred.append(surface['id'])
            continue
        add(kind, surface['id'], surface_shape(surface))
    for layers in (roads['layers'], surroundings['layers']):
        for layer in layers:
            add('roads', layer['id'], surface_shape(layer))
    for building in data['buildings']:
        for index, rings in enumerate(building['polygons']):
            add('buildings', f"{building['id']}:{index}", Polygon(rings[0], rings[1:]))
        for facade in building.get('form', {}).get('facades', []):
            if 'attachedGallery' in facade:
                add('attached-gallery', f"{building['id']}:{facade['polygon']}:{facade['ring']}:{facade['edge']}:{facade['part']}",
                    Polygon(facade['attachedGallery']['footprint']))
        for entrance in building.get('form', {}).get('entrances', []):
            for kind in ('attachedPortico','stairFlight'):
                if kind in entrance:
                    add('entrance-platform', f"{building['id']}:{entrance['id']}",
                        Polygon(entrance[kind]['footprint']))
    for sport in data['sports']:
        add('sports', sport['id'], Polygon(sport['ground']))
    for site in sites['sites']:
        add('sites', site['id'], Polygon(site['pavingPolygon']))
    for paving in data['pavings']['pavings']:
        add('pavings', paving['id'], surface_shape(paving))
    for shore in data['shores']['shores']:
        for index, rings in enumerate(shore['capPolygons']):
            add('shore-cap', f"{shore['id']}:{index}", Polygon(rings[0], rings[1:]))
    return masks, deferred


def filter_ground(trees, masks):
    """Boundary-inclusive centre exclusion; preserve survivor values and order."""
    index = STRtree([mask.geometry for mask in masks])
    prepared = [prep(mask.geometry) for mask in masks]
    kept, removed = [], []
    for row_index, row in enumerate(trees):
        point = Point(row[:2])
        hits = sorted(int(i) for i in index.query(point)
                      if prepared[int(i)].covers(point))
        if hits:
            removed.append({'treeIndex': row_index, 'tree': row,
                            'masks': [{'kind': masks[i].kind, 'id': masks[i].id} for i in hits]})
        else:
            kept.append(row)
    return kept, removed


def final_ground_exclusions(trees, data):
    masks, deferred = ground_masks(data)
    kept, removed = filter_ground(trees, masks)
    return kept, {
        'method': 'Final derived planar footprints; tree centres including boundaries; courtyard holes retained.',
        'inputTrees': len(trees), 'retainedTrees': len(kept), 'removed': removed,
        'maskCounts': dict(sorted(Counter(m.kind for m in masks).items())),
        'deferredLayeredSurfaceIds': deferred,
        'limitations': [
            'Centre placement only; canopy/trunk volumes require the final model checks.',
            'Ground-centre pass only; explicit infrastructure/entrance/sculpture crown reservations are applied by the next final pass, separately from actual 3D constraints.',
            'Footprints are planting exclusions, not evidence of solid interiors; mapped courtyard holes remain available.',
        ],
    }
