"""Audit actual terrain and service-road intrusion into a building footprint.

This does not certify as-built elevations. A building's adopted datum is used
to detect coarse terrain crossing its closed ground-floor volumes. Near LODs
reuse base terrain, so source and base are the relevant ground representations.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from site_geometry import inside


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def covers(point, polygons):
    return any(inside(point, p[0]) and not any(inside(point, h) for h in p[1:]) for p in polygons)


def building_parts(building):
    return building.get('form', {}).get('parts') or [
        {'id':'mapped-closed-body', 'polygons':building['polygons'], 'height':building['height']}]


def sample_parts(building, spacing):
    """Interior lattice plus an inward perimeter band, independent of the DEM."""
    samples = []
    parts = building_parts(building)
    for part in parts:
        if part.get('openBelow'):
            continue
        polygons = part['polygons']
        points = {}

        def add(x, y, kind):
            if covers((x, y), polygons):
                points.setdefault((round(x, 7), round(y, 7)), kind)

        for polygon in polygons:
            ring = polygon[0]
            for a, b in zip(ring, ring[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                length = math.hypot(dx, dy)
                if length < 1e-8:
                    continue
                count = max(1, math.ceil(length / spacing))
                for i in range(count):
                    t = (i + .5) / count
                    x, y = a[0] + dx * t, a[1] + dy * t
                    # Test both normals rather than assuming ring orientation.
                    for sign in (-1, 1):
                        add(x - sign * dy / length * .25, y + sign * dx / length * .25, 'perimeter-inset')
            xs, ys = [p[0] for p in ring], [p[1] for p in ring]
            for ix in range(math.floor(min(xs) / spacing), math.ceil(max(xs) / spacing) + 1):
                for iy in range(math.floor(min(ys) / spacing), math.ceil(max(ys) / spacing) + 1):
                    add(ix * spacing, iy * spacing, 'interior-grid')
        if not points:
            raise ValueError('No interior samples for ' + part['id'])
        samples.extend((part['id'], x, y, kind) for (x, y), kind in sorted(points.items()))
    return samples


def top_tree(objects):
    vertices, triangles, labels = [], [], []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles()
        # Only upward surfaces; vertical road sides are not ground levels.
        for tri in obj.data.loop_triangles:
            ids = tuple(offset + i for i in tri.vertices)
            a, b, c = (vertices[i] for i in ids)
            if (b - a).cross(c - a).z > 1e-9:
                triangles.append(ids)
                material = obj.data.materials[tri.material_index]
                labels.append({'object': obj.name, 'material': material.name if material else None})
    if not triangles:
        raise ValueError('Missing terrain or road top triangles')
    return BVHTree.FromPolygons(vertices, triangles, all_triangles=True), labels


def layer(obj):
    while obj.parent:
        obj = obj.parent
    return obj.get('layer')


def measure(building, samples, tolerance, name):
    objects = list(bpy.context.scene.objects)
    ground, _ = top_tree([o for o in objects if layer(o) == 'terrain'])
    roads, road_labels = top_tree([o for o in objects if layer(o) == 'roads'])
    datum = building['elevation']
    heights = {p['id']: p['height'] for p in building_parts(building)}
    rows = []
    for part, x, y, kind in samples:
        origin = Vector((x, y, datum + 150))
        direction = Vector((0, 0, -1))
        g = ground.ray_cast(origin, direction, 300)[0]
        if g is None:
            raise ValueError(f'Missing ground: {name}, {part}, {x}, {y}')
        # Ignore an elevated road wholly above the adopted closed body; start
        # below its roof so a bridge cannot hide a lower intrusive surface.
        road_origin = Vector((x, y, datum + heights[part] - .01))
        r, _, road_index, _ = roads.ray_cast(road_origin, direction, heights[part] + 150)
        rows.append({'part': part, 'xy': [x, y], 'kind': kind,
                     'terrainAboveDatum': g.z - datum,
                     'roadAboveDatum': None if r is None else r.z - datum,
                     'roadHit': None if r is None else road_labels[road_index]})
    summaries = []
    for part in sorted({r['part'] for r in rows}):
        selected = [r for r in rows if r['part'] == part]
        ground_fail = [r for r in selected if r['terrainAboveDatum'] > tolerance]
        road_fail = [r for r in selected if r['roadAboveDatum'] is not None and r['roadAboveDatum'] > tolerance]
        summaries.append({'part': part, 'samples': len(selected),
                          'terrainIntrusionSamples': len(ground_fail),
                          'roadIntrusionSamples': len(road_fail),
                          'maximumTerrainAboveDatum': max(r['terrainAboveDatum'] for r in selected),
                          'worstGroundSamples': sorted(ground_fail, key=lambda r: r['terrainAboveDatum'], reverse=True)[:5],
                          'worstRoadSamples': sorted(road_fail, key=lambda r: r['roadAboveDatum'], reverse=True)[:5]})
    return {'representation': name, 'samples': len(rows), 'parts': summaries,
            'passed': all(p['terrainIntrusionSamples'] == 0 and p['roadIntrusionSamples'] == 0 for p in summaries)}, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--building-id', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--samples-output', type=Path)
    parser.add_argument('--spacing', type=float, default=2)
    parser.add_argument('--tolerance', type=float, default=.3)
    parser.add_argument('--fail-on-intrusion', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if not math.isfinite(args.spacing) or not .5 <= args.spacing <= 5:
        parser.error('spacing must be 0.5–5 metres')
    if not math.isfinite(args.tolerance) or not 0 <= args.tolerance <= .5:
        parser.error('tolerance must be 0–0.5 metres')
    data = ROOT / 'public/data/buildings.json'
    building = next((b for b in json.loads(data.read_text()) if b['id'] == args.building_id), None)
    if building is None:
        parser.error('unknown building id')
    samples = sample_parts(building, args.spacing)
    representations, full_samples = [], {}
    files = {'source': ROOT / 'blender/gxu-campus.blend', 'base': ROOT / 'public/models/base.glb'}
    for name, path in files.items():
        if name == 'source':
            bpy.ops.wm.open_mainfile(filepath=str(path))
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=str(path))
        bpy.context.view_layer.update()
        summary, rows = measure(building, samples, args.tolerance, name)
        representations.append(summary)
        full_samples[name] = rows
    report = {'buildingId': building['id'], 'adoptedDatum': building['elevation'],
              'datumMeaning': 'Current model elevation, not surveyed ground-floor elevation',
              'sampling': {'spacingMeters': args.spacing, 'perimeterInsetMeters': .25,
                           'allowedIntrusionMeters': args.tolerance, 'openPorticosExcluded': True,
                           'scope': 'Closed part interiors; road layers include ordinary service roads; near buildings reuse base terrain'},
              'fingerprints': {'buildings': fingerprint(data), **{k: fingerprint(v) for k, v in files.items()}},
              'representations': representations,
              'passed': all(r['passed'] for r in representations)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if args.samples_output:
        args.samples_output.parent.mkdir(parents=True, exist_ok=True)
        args.samples_output.write_text(json.dumps(full_samples, separators=(',', ':')) + '\n')
    print('FOUNDATION_AUDIT', json.dumps({'buildingId': building['id'], 'passed': report['passed'],
                                        'samplesPerRepresentation': len(samples), 'report': str(args.report)}), flush=True)
    if args.fail_on_intrusion and not report['passed']:
        raise AssertionError('Terrain or road surfaces intrude above the adopted building datum; see report')


if __name__ == '__main__':
    main()
