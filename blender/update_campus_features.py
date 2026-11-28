"""Build a bounded campus candidate using the published scene and streaming manifest.

blender -b -P blender/update_campus_features.py -- --output-root work/candidate
Pass --building and --landmark for each changed ID, and --fields for field meshes.
Add --publish to install the validated candidate.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.geometry import convex_hull_2d
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'blender'), str(ROOT / 'scripts')]
from building_finishes import ensure_building_finishes
from building_models import SURVEYED, building_mesh
from college_chunk_budget import optimize_export
from detail_export import export_detail, geometry_bytes
from generic_buildings import compact_form_source
from geometry import MATERIALS, Mesh
from incremental_building_chunks import inside_hull, replace_in_chunk
from incremental_glb import splice_nodes, validate_retained
from incremental_update import copy_inputs, publish, run_checked, snapshot
from initial_model_budget import check_initial_model_budget
from landmarks import landmark
from terrain_elevation import make_elevation


def remove(obj):
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if not data.users:
        bpy.data.meshes.remove(data)


def reorder_material_slots(obj, slots, ordered):
    if slots != ordered:
        remap = {mat: i for i, mat in enumerate(ordered)}
        indices = [remap[slots[p.material_index]] for p in obj.data.polygons]
        for i, mat in enumerate(ordered):
            obj.data.materials[i] = mat
        obj.data.polygons.foreach_set('material_index', indices)


def export(mesh, key, path, props, far=False):
    obj = mesh.object(key, bpy.context.scene.collection, props)
    # Export primitive order must be independent of palette registration order.
    slots = list(obj.data.materials)
    reorder_material_slots(
        obj, slots, sorted(slots, key=lambda material: material.name)
    )
    export_detail(obj, path, base_chunk=far)
    remove(obj)
    return path.read_bytes()


def attributes(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def outline(obj):
    points = [(obj.matrix_world @ v.co).to_2d() for v in obj.data.vertices]
    return np.array([points[i] for i in convex_hull_2d(points)])


def sync_tree_instances(rows, excluded, obstacles, colors):
    from tree_clearance import filter_building_collisions
    from vegetation import tree_templates
    from vegetation_layout import tree_rotation, tree_scale

    retained = {tuple(t[:2]): t for t in rows}
    if len(retained) != len(rows):
        raise ValueError('Duplicate prepared tree coordinates')
    removed = []
    missing = []
    templates = [bpy.data.objects[f'Tree-template-{kind}'] for kind in range(4)]
    for obj in list(bpy.context.scene.objects):
        if not obj.name.startswith('树木示意-'):
            continue
        xy = tuple(round(v, 1) for v in obj.location[:2])
        row = retained.pop(xy, None)
        if row is None:
            removed.append(dict(name=obj.name, xy=xy))
            if xy not in excluded:
                kind = next(i for i, t in enumerate(templates) if t.data == obj.data)
                missing.append([*xy, round(obj.scale.z * 9, 1), kind, obj.location.z])
            continue
        x, y, h, kind, z = row
        if (
            obj.data != bpy.data.objects[f'Tree-template-{kind}'].data
            or abs(obj.location.z - z) > 0.001
            or any(abs(a - b) > 0.0001 for a, b in zip(obj.scale, tree_scale(x, y, h)))
            or abs(math.remainder(obj.rotation_euler.z - tree_rotation(x, y), math.tau))
            > 0.00001
        ):
            raise ValueError(f'Prepared tree differs from editable instance at {xy}')
    if retained:
        raise ValueError(f'Prepared trees missing in baseline: {list(retained)[:5]}')
    if obstacles:
        far = tree_templates(colors, bpy.context.scene.collection, False)
        survivors, _ = filter_building_collisions(
            rows + missing, {'near': templates, 'base': far}, obstacles
        )
        for obj in far:
            remove(obj)
    else:
        survivors = rows + missing
    if survivors != rows:
        survived = {tuple(t[:2]) for t in survivors}
        wanted = {tuple(t[:2]) for t in rows}
        raise ValueError(
            f'Tree differences exceed selected field and building geometry: prepared conflicts {sorted(wanted - survived)}, unverified deletions {sorted(survived - wanted)}'
        )
    for row in removed:
        bpy.data.objects.remove(bpy.data.objects[row['name']], do_unlink=True)
    return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--building', action='append', default=[])
    parser.add_argument('--landmark', action='append', default=[])
    parser.add_argument('--fields', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1 :])
    args.landmark = list(dict.fromkeys(args.landmark))
    args.building = list(dict.fromkeys(args.building))
    supported_buildings = SURVEYED.keys() | {
        'way/759337787',
        'way/759147086',
        'way/759140894',
        'way/759132929',
    }
    supported_places = {
        'library',
        'donggao-gate',
        'north-public-gate',
        'quanxue-island',
        'veterinary-hospital',
    }
    if (
        set(args.building) - supported_buildings
        or set(args.landmark) - supported_places
    ):
        parser.error('Unsupported campus building or landmark for incremental export')
    if not (args.building or args.landmark or args.fields):
        parser.error('Select a surveyed building, landmark or fields')
    target = args.output_root.resolve()
    from incremental_update import publication_lock, require_recovered

    with publication_lock(ROOT):
        require_recovered(ROOT)
        data = ROOT / 'public/data'
        latest = json.loads((data / 'landmarks.json').read_text())
        prior = json.loads((data / 'models.json').read_text())
        places = {l['id'] for l in latest}
        previously = {l['id'] for l in prior['landmarks']}
        missing = places - previously - set(args.landmark)
        if missing or previously - places or set(args.landmark) - places:
            parser.error(
                f'Catalogue and model release must include all landmark changes: {sorted(missing)}'
            )
        catalog = json.loads((data / 'buildings.json').read_text())
        previous_zones = {
            fid: z['id'] for z in prior['zones'] for fid in z['featureIds']
        }
        current_zones = {
            b['id']: b.get('chunk')
            for b in catalog
            if b['insideCampus'] and not b['landmark']
        }
        changed = {
            fid
            for fid in previous_zones.keys() | current_zones.keys()
            if previous_zones.get(fid) != current_zones.get(fid)
        }
        mapped = {l.get('osmId') for l in latest if l['id'] in args.landmark}
        omitted = changed - set(args.building) - mapped
        if omitted or set(args.building) - current_zones.keys():
            parser.error(
                f'Catalogue and model release must include all changed building assignments: {sorted(omitted)}'
            )
        before = snapshot(ROOT)
        copy_inputs(ROOT, target)
        if snapshot(ROOT) != before:
            raise RuntimeError('Formal inputs changed while staging')
    data = target / 'public/data'
    models = target / 'public/models'
    work = target / 'work'
    read = lambda key: json.loads((data / (key + '.json')).read_text())
    manifest = read('models')
    buildings = {b['id']: b for b in read('buildings')}
    places = {l['id']: l for l in read('landmarks')}
    terrain = make_elevation(read('terrain'))
    path = target / 'blender/gxu-campus.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.preferences.filepaths.save_version = 0
    MATERIALS[:] = list(bpy.data.materials)
    colors = {m.name: i for i, m in enumerate(MATERIALS)}
    ensure_building_finishes(colors)
    source = bpy.data.collections['校园建筑 · 可编辑']
    objects = {o['featureId']: o for o in source.objects if o.get('featureId')}
    base_path = models / 'base.glb'
    original = current = base_path.read_bytes()
    updated = set()
    diagnostics = {}
    obstacles = []
    updates = set(args.building)
    for key in args.landmark:
        if places[key].get('osmId') in buildings:
            updates.add(places[key]['osmId'])
    old_zones = {z['id']: z for z in manifest['zones']}
    zones = {
        z['id'] for z in old_zones.values() if updates.intersection(z['featureIds'])
    }
    ordinary = {fid for fid in updates if not buildings[fid]['landmark']}
    zones.update(buildings[fid]['chunk'] for fid in ordinary)
    for zone in sorted(zones):
        z = old_zones.get(
            zone, {'id': zone, 'url': f'models/{zone}.glb', 'featureIds': []}
        )
        old_ids = set(z['featureIds'])
        members = [
            b
            for b in buildings.values()
            if b.get('chunk') == zone and not b['landmark']
        ]
        if (old_ids ^ {b['id'] for b in members}) - updates or not members:
            raise ValueError(f'Unexpected zone membership change: {zone}')
        dedicated = zone.startswith('chunk-dorm-')
        shared = old_ids and not dedicated
        boxes = (
            {fid: outline(objects[fid]) for fid in updates & old_ids} if shared else {}
        )
        for fid, hull in list(boxes.items()):
            overlapping = [
                other
                for other in old_ids - {fid}
                if inside_hull(outline(objects[other]), hull).any()
                or inside_hull(hull, outline(objects[other])).any()
            ]
            tree = None
            if overlapping:
                tree = KDTree(
                    sum(len(objects[i].data.vertices) for i in [fid, *overlapping])
                )
                for i in [fid, *overlapping]:
                    obj = objects[i]
                    for v in obj.data.vertices:
                        tree.insert(obj.matrix_world @ v.co, int(i == fid))
                tree.balance()
            boxes[fid] = (hull, tree)
        for far in [True, False]:
            addition = Mesh()
            for b in members:
                if b['id'] not in ordinary:
                    continue
                mesh = building_mesh(b, terrain(*b['center']), colors, not far)
                if not mesh.f:
                    raise ValueError(f'Empty building mesh: {b["id"]}')
                obstacles.append((b['id'], 'base' if far else 'near', mesh))
                addition.extend(mesh)
                if not far:
                    old = objects.get(b['id'])
                    props = dict(old.items()) if old else {}
                    prior_slots = list(old.data.materials) if old else []
                    if old:
                        remove(old)
                    obj = mesh.object(
                        b['name'],
                        source,
                        dict(
                            props,
                            featureId=b['id'],
                            chunk=zone,
                            layer='buildings',
                            sourceUrl=b['sourceUrl'],
                        ),
                    )
                    slots = list(obj.data.materials)
                    # Preserve editable slot numbers when rebuilding the same palette.
                    if set(slots) == set(prior_slots):
                        reorder_material_slots(obj, slots, prior_slots)
                    if b.get('form') or b['id'] in SURVEYED:
                        compact_form_source(obj)
            props = dict(layer='buildings', zone=zone, landmark='', sportsId='')
            if dedicated:
                (props['buildingId'],) = [b['id'] for b in members]
            near_path = models / (zone + '.glb')
            patch = (
                export(
                    addition,
                    'building-addition' if shared else zone,
                    work / 'patch.glb',
                    props,
                    far,
                )
                if addition.f
                else None
            )
            if shared:
                patch, stats = replace_in_chunk(
                    original if far else near_path.read_bytes(),
                    zone,
                    boxes,
                    patch,
                    far=far,
                )
                diagnostics[f'{zone}-{"far" if far else "near"}'] = stats
            if far:
                current = splice_nodes(current, patch, {zone})
                updated.add(zone)
            else:
                near_path.write_bytes(patch)
                if optimize_export(near_path):
                    patch = near_path.read_bytes()
                z.update(attributes(patch), geometryBytes=geometry_bytes(patch))
        member_ids = [b['id'] for b in members]
        bounds = [
            op(b['bounds'][i] for b in members) + (0 if dedicated else offset)
            for i, op, offset in [(0, min, -2), (1, min, -2), (2, max, 2), (3, max, 2)]
        ]
        if set(member_ids) == old_ids:
            # Existing streaming envelopes can include facade projections beyond the footprint.
            bounds = [
                op(a, b) for op, a, b in zip((min, min, max, max), z['bounds'], bounds)
            ]
        z.update(featureIds=member_ids, bounds=bounds)
        if zone not in old_zones:
            manifest['zones'].append(z)
    entries = {l['id']: l for l in manifest['landmarks']}
    for key in args.landmark:
        l = places[key]
        fid = l.get('osmId') or key
        b = buildings.get(fid)
        z = terrain(*(b or l)['center'])
        old = objects.get(fid)
        editable_props = dict(old.items()) if old else {}
        editable_props.pop('chunk', None)
        editable_props.update(
            landmark=key,
            layer='buildings',
            zone='',
            featureId=fid,
            sourceUrl=l['sourceUrl'],
        )
        if old:
            remove(old)
        props = dict(landmark=key, layer='buildings', zone='')
        node = 'landmark-' + key
        high = landmark(l, b, z, colors, True)
        low_mesh = landmark(l, b, z, colors, False)
        if not high.f or not low_mesh.f:
            raise ValueError(f'Empty landmark mesh: {key}')
        obstacles.extend([(key, 'near', high), (key, 'base', low_mesh)])
        high.object(l['name'], source, editable_props)
        raw = export(high, node, models / (key + '.glb'), props)
        entries[key] = dict(id=key, url=f'models/{key}.glb', **attributes(raw))
        low = export(low_mesh, node, work / 'patch.glb', props, True)
        current = splice_nodes(current, low, {node})
        updated.add(node)
    if args.fields:
        from east_north_fields import site_meshes

        for key, mesh in site_meshes(terrain, colors).items():
            if not key.startswith('east-field-') or not mesh.f:
                raise ValueError(key)
            props = dict(layer='vegetation')
            if obj := bpy.data.collections['道路水体与地形'].objects.get(key):
                remove(obj)
            raw = export(mesh, key, work / 'patch.glb', props, True)
            mesh.object(key, bpy.data.collections['道路水体与地形'], props)
            current = splice_nodes(current, raw, {key})
            updated.add(key)
    from vegetation_priorities import priority_positions

    trees = read('vegetation')
    from field_tree_review import reviewed_field_positions

    excluded, kept = reviewed_field_positions(ROOT)
    positions = {tuple(row[:2]) for row in trees}
    if positions & excluded or not kept <= positions:
        raise ValueError(
            'Prepared tree rows disagree with reviewed field tree positions'
        )
    removed_trees = sync_tree_instances(
        trees, excluded if args.fields else set(), obstacles, colors
    )
    for key in args.landmark:
        if sum(o.get('landmark') == key for o in source.objects) != 1:
            raise ValueError(f'Expected one editable landmark: {key}')
    manifest['treePriorityPositions'] = priority_positions(
        read('vegetation-zones'), trees
    )
    base_path.write_bytes(current)
    if optimize_export(base_path):
        current = base_path.read_bytes()
    retained = validate_retained(original, current, updated)
    manifest['landmarks'] = [entries[k] for k in places]
    manifest['base'].update(attributes(current))
    budget = check_initial_model_budget(len(current) + manifest['trees']['bytes'])
    (data / 'models.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    selection = work / 'source-selection.json'
    selection.write_text(
        json.dumps(
            dict(
                features=sorted(updates),
                landmarks=args.landmark,
                sites=sorted(k for k in updated if k.startswith('east-field-'))
                + [t['name'] for t in removed_trees],
            )
        )
    )
    run_checked(
        [
            bpy.app.binary_path,
            '-b',
            '--factory-startup',
            '--python-exit-code',
            '1',
            '-P',
            str(target / 'blender/validate_incremental_source.py'),
            '--',
            f'--baseline-root={ROOT}',
            '--update-kind=campus-features',
            f'--selection={selection}',
        ],
        target,
        'source-retention',
    )
    run_checked(
        [
            'node',
            '--experimental-strip-types',
            '--test',
            'scripts/test-campus.mjs',
            'scripts/test-streaming.mjs',
        ],
        target,
        'catalog-assets',
    )
    if ordinary:
        run_checked(
            [
                bpy.app.binary_path,
                '-b',
                '-t',
                '3',
                '--factory-startup',
                '--python-exit-code',
                '1',
                '-P',
                str(target / 'blender/validate_generic.py'),
                '--',
                *[f'--building={fid}' for fid in sorted(ordinary)],
            ],
            target,
            'ordinary-shipping',
        )
    report = dict(
        updatedNodes=sorted(updated),
        retainedBaseNodes=retained,
        chunks=diagnostics,
        removedTrees=removed_trees,
        retainedTrees=len(trees),
        **budget,
    )
    (work / 'feature-update.json').write_text(json.dumps(report, indent=2))
    (work / 'before.json').write_text(json.dumps(before))
    if args.publish:
        publish(ROOT, target, before)


if __name__ == '__main__':
    main()
