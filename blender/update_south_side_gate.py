"""Build a bounded south-side-gate candidate; --publish installs it after validation."""

import argparse
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
sys.path.insert(0, str(ROOT / 'scripts'))
from campus_gates import campus_gate
from detail_export import export_detail
from geometry import MATERIALS
from incremental_glb import splice_nodes, validate_retained
from incremental_update import (
    copy_inputs,
    publication_lock,
    publish,
    require_recovered,
    run_checked,
    snapshot,
)
from initial_model_budget import check_initial_model_budget
from low_planting_contract import load_prepared
from terrain_elevation import make_elevation
from vegetation_layout import tree_rotation, tree_scale
from vegetation_priorities import priority_positions


def replace_gate_entry(rows, entry, *, after=None):
    """Replace all copies of this stable ID while keeping unrelated order."""
    key = entry['id']
    previous = next((i for i, item in enumerate(rows) if item.get('id') == key), None)
    rows[:] = [item for item in rows if item.get('id') != key]
    if previous is None and after is not None:
        previous = next(i for i, item in enumerate(rows) if item.get('id') == after) + 1
    rows.insert(previous if previous is not None else len(rows), entry)


def prepare_gate_vegetation(target, gis_python, gate_id):
    data = target / 'public/data'
    tree_path = data / 'vegetation.json'
    zones_path = data / 'vegetation-zones.json'
    original = json.loads(tree_path.read_text())
    clearance = json.loads(zones_path.read_text()).get('modelBuildingClearance')
    if clearance is not None and clearance['retainedTrees'] != len(original):
        raise ValueError('Baseline tree count disagrees with model clearance')

    command = [gis_python, '-B', str(target / 'scripts/vegetation_data.py')]
    run_checked(command, target, 'prepare-vegetation')
    trees = json.loads(tree_path.read_text())
    zones = json.loads(zones_path.read_text())
    hits = zones['finalCrownReservations']['removed']
    if any(
        not hit['masks']
        or any((mask['kind'], mask['id']) != ('gate', gate_id) for mask in hit['masks'])
        for hit in hits
    ):
        raise ValueError('Tree removal outside the south-side gate reservation')
    removed = {tuple(hit['tree']) for hit in hits}
    if (
        len(removed) != len(hits)
        or len(original) != len(trees) + len(removed)
        or [row for row in original if tuple(row) not in removed] != trees
    ):
        raise ValueError('Unrelated vegetation changed during gate preparation')

    # The standard report describes this pass's input. Publish the report for
    # the final layout so a repeat build produces the same public bytes.
    if hits:
        run_checked(command, target, 'verify-vegetation-fixed-point')
        zones = json.loads(zones_path.read_text())
        if (
            json.loads(tree_path.read_text()) != trees
            or zones['finalCrownReservations']['removed']
        ):
            raise ValueError('Prepared vegetation is not a fixed point')
    if (
        not zones['passed']
        or zones['trees'] != len(trees)
        or json.loads((data / 'overview.json').read_text())['trees'] != len(trees)
    ):
        raise ValueError('Final vegetation statistics disagree with retained rows')
    if clearance is not None:
        zones['modelBuildingClearance'] = {**clearance, 'retainedTrees': len(trees)}
        zones_path.write_text(
            json.dumps(zones, ensure_ascii=False, separators=(',', ':')) + '\n'
        )
    return (
        trees,
        zones,
        {
            'originalTrees': len(original),
            'retainedTrees': len(trees),
            'removed': hits,
        },
    )


def remove_reserved_instances(hits, target):
    if not hits:
        return ROOT, []
    scene = bpy.context.scene
    prior = {obj.name for obj in scene.objects}
    templates = {
        obj.get('template'): obj.data
        for obj in scene.objects
        if obj.get('template') is not None
    }
    rows = {tuple(hit['tree'][:2]): hit['tree'] for hit in hits}
    names = []
    for obj in list(scene.objects):
        if not obj.name.startswith('树木示意-'):
            continue
        position = (round(obj.location.x, 1), round(obj.location.y, 1))
        if position not in rows:
            continue
        x, y, height, kind, z = rows[position]
        if (
            obj.data != templates[kind]
            or any(abs(a - b) > 1e-4 for a, b in zip(obj.location, (x, y, z)))
            or any(
                abs(a - b) > 1e-5 for a, b in zip(obj.scale, tree_scale(x, y, height))
            )
            or abs(math.remainder(obj.rotation_euler.z - tree_rotation(x, y), math.tau))
            > 1e-6
        ):
            raise ValueError(f'Tree instance disagrees with prepared row: {obj.name}')
        rows.pop(position)
        names.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
    if (
        rows
        or len(names) != len(hits)
        or {obj.name for obj in scene.objects} != prior.difference(names)
    ):
        raise ValueError('Editable tree removals disagree with reservation witnesses')
    # Give the unmodified shared signature validator a reference with exactly
    # these verified deletions, before any gate, material or export edits.
    reference = target / 'work/tree-retention-reference'
    (reference / 'blender').mkdir(parents=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(reference / 'blender/gxu-campus.blend'),
        copy=True,
        compress=True,
        relative_remap=False,
    )
    return reference, names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(
        sys.argv[sys.argv.index('--') + 1 :] if '--' in sys.argv else []
    )
    target = args.output_root.resolve()
    with publication_lock(ROOT):
        require_recovered(ROOT)
        before = snapshot(ROOT)
        copy_inputs(ROOT, target)
        for folder in ['app', 'components', 'hooks']:
            shutil.copytree(ROOT / folder, target / folder, dirs_exist_ok=True)
        for name in ['index.html', 'vite.config.ts', 'tsconfig.json']:
            shutil.copy2(ROOT / name, target / name)
        if snapshot(ROOT) != before:
            raise RuntimeError('Inputs changed during candidate copy')
    (target / 'work/baseline.json').write_text(json.dumps(before))

    # Validate the copied inputs before changing any landmark context. A stale
    # baseline must never acquire a fresh revision through this update.
    low_path = target / 'public/data/low-planting.json'
    load_prepared(target)
    previous_low = json.loads(low_path.read_text())

    source = next(
        x
        for x in json.loads((target / 'data/landmarks.json').read_text())
        if x['id'] == 'south-side-gate'
    )
    record = dict(source)
    lon, lat = record['lonLat']
    record['center'] = [
        (lon - 108.2882) * 111320 * math.cos(math.radians(22.84715)),
        (lat - 22.84715) * 111320,
    ]
    x, y = record['center']
    w, d = record['gateWidth'], record['gateDepth']
    record['bounds'] = [x - w / 2, y - d / 2, x + w / 2, y + d / 2]
    snapshot_data = json.loads(
        gzip.decompress((target / 'data/snapshots/osm-2026-09-09.json.gz').read_bytes())
    )
    osm = next(
        e
        for e in snapshot_data['elements']
        if e['type'] == 'node' and e['id'] == 7090009149
    )
    record['osmEditedAt'] = osm['timestamp']
    record['osmVersion'] = osm['version']
    record['sourceRefs'] = [
        'osm',
        record['reference'],
        *record['additionalReferences'],
    ]
    terrain = json.loads((target / 'public/data/terrain.json').read_text())
    record['elevation'] = round(make_elevation(terrain)(x, y), 2)
    record['zone'] = 'west'

    catalog = json.loads((target / 'public/data/landmarks.json').read_text())
    replace_gate_entry(catalog, record, after='west-gate')
    (target / 'public/data/landmarks.json').write_text(
        json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))
    )

    references = json.loads((target / 'public/data/sources.json').read_text())
    fresh = {
        s['id']: s
        for s in json.loads((target / 'data/sources.json').read_text())
        if s['id'] in record['sourceRefs']
    }
    references['sources'] = [
        fresh.pop(s['id'], s) for s in references['sources']
    ] + list(fresh.values())
    (target / 'public/data/sources.json').write_text(
        json.dumps(references, ensure_ascii=False, indent=2) + '\n'
    )

    geography_path = target / 'public/data/geography.geojson'
    geography = json.loads(geography_path.read_text())
    replace_gate_entry(
        geography['features'],
        {
            'type': 'Feature',
            'id': record['id'],
            'properties': {
                'kind': 'entrances',
                'name': record['name'],
                'landmark': record['id'],
                'sourceUrl': record['sourceUrl'],
                'osmEditedAt': record['osmEditedAt'],
                'osmVersion': record['osmVersion'],
                'positionBasis': record['positionBasis'],
            },
            'geometry': {'type': 'Point', 'coordinates': record['lonLat']},
        },
    )
    geography_path.write_text(
        json.dumps(geography, ensure_ascii=False, separators=(',', ':'))
    )
    overview_path = target / 'public/data/overview.json'
    overview = json.loads(overview_path.read_text())
    overview['landmarks'] = len(catalog)
    overview['layers']['entrances'] = sum(
        f['properties'].get('kind') == 'entrances' for f in geography['features']
    )
    overview_path.write_text(
        json.dumps(overview, ensure_ascii=False, separators=(',', ':')) + '\n'
    )

    project_python = ROOT / 'work/venv/bin/python'
    gis_python = os.environ.get('GIS_PYTHON') or (
        str(project_python) if project_python.is_file() else 'python3'
    )
    trees, zones, tree_check = prepare_gate_vegetation(target, gis_python, record['id'])
    plantings = load_prepared(target)
    new_low = json.loads(low_path.read_text())
    old_revision = previous_low.pop('contextRevision')
    new_revision = new_low.pop('contextRevision')
    if previous_low != new_low:
        raise ValueError('South-side gate update changed existing low planting')
    planting_check = {
        'previousContextRevision': old_revision,
        'contextRevision': new_revision,
        'configRevision': new_low['configRevision'],
        'validatedPlantings': len(plantings),
        'placementPassed': new_low['placementPassed'],
    }

    bpy.ops.wm.open_mainfile(filepath=str(target / 'blender/gxu-campus.blend'))
    bpy.context.preferences.filepaths.file_preview_type = 'NONE'
    bpy.context.preferences.filepaths.save_version = 0
    retention_root, tree_check['removedSourceObjects'] = remove_reserved_instances(
        tree_check['removed'], target
    )
    for obj in list(bpy.context.scene.objects):
        if obj.get('landmark') == record['id']:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(mesh, bpy.types.Mesh) and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
    # Register this gate's materials in palette order on every export, including
    # when the .blend already contains those materials from an earlier release.
    MATERIALS[:] = [m for m in bpy.data.materials if not m.name.startswith('southSide')]
    C = {m.name: i for i, m in enumerate(MATERIALS)}
    collection = bpy.data.collections.get('校园建筑 · 可编辑')
    assert collection is not None
    unchanged = {
        o.name: (o.as_pointer(), o.data.as_pointer() if o.data else None)
        for o in bpy.context.scene.objects
    }
    high = campus_gate(record, record['elevation'], C, True)
    low = campus_gate(record, record['elevation'], C, False)
    key = 'landmark-south-side-gate'
    original = (target / 'public/models/base.glb').read_bytes()
    export_props = {'landmark': record['id'], 'layer': 'buildings', 'zone': 'west'}
    for mesh, path in [
        (high, target / 'public/models/south-side-gate.glb'),
        (low, target / 'work/south-side-base.glb'),
    ]:
        obj = mesh.object(key, collection, export_props)
        export_detail(obj, path)
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(data)
    updated = splice_nodes(
        original, (target / 'work/south-side-base.glb').read_bytes(), {key}
    )
    validate_retained(original, updated, {key})
    (target / 'public/models/base.glb').write_bytes(updated)
    high.object(
        record['name'],
        collection,
        {
            'featureId': record['osmId'],
            'landmark': record['id'],
            'layer': 'buildings',
            'sourceUrl': record['sourceUrl'],
            'modelingBasis': 'photo',
            'reference': record['reference'],
        },
    )
    assert all(
        (
            bpy.data.objects[k].as_pointer(),
            bpy.data.objects[k].data.as_pointer() if bpy.data.objects[k].data else None,
        )
        == v
        for k, v in unchanged.items()
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(target / 'blender/gxu-campus.blend'), compress=True
    )

    # Validation opens the two source files in a separate Blender process.
    MATERIALS.clear()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    manifest = json.loads((target / 'public/data/models.json').read_text())
    manifest['treePriorityPositions'] = priority_positions(zones, trees)
    entry = {'id': record['id'], 'url': 'models/south-side-gate.glb'}
    replace_gate_entry(manifest['landmarks'], entry, after='west-gate')
    for asset in [manifest['base'], entry]:
        raw = (target / 'public' / asset['url']).read_bytes()
        asset.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    budget = check_initial_model_budget(
        manifest['base']['bytes'] + manifest['trees']['bytes']
    )
    (target / 'public/data/models.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )

    for label, script, extra in [
        (
            'source-retention',
            'validate_incremental_source.py',
            [f'--baseline-root={retention_root}', '--update-kind=south-side-gate'],
        ),
        (
            'south-side-geometry',
            'validate_south_side_gate.py',
            [f'--tree-baseline-root={ROOT}'],
        ),
    ]:
        run_checked(
            [
                bpy.app.binary_path,
                '-b',
                '--factory-startup',
                '--disable-autoexec',
                '--python-exit-code',
                '1',
                '--python',
                str(target / 'blender' / script),
                '--',
                *extra,
            ],
            target,
            label,
        )
    run_checked(
        [
            os.environ.get('NODE_BIN', 'node'),
            '--experimental-strip-types',
            '--test',
            'scripts/test-campus.mjs',
            'scripts/test-sources.mjs',
            'scripts/test-i18n.mjs',
            'scripts/test-share.mjs',
            'scripts/test-camera.mjs',
        ],
        target,
        'catalog-and-assets',
    )
    changed = [p for p, h in snapshot(target).items() if before.get(p) != h]
    allowed = {
        'blender/gxu-campus.blend',
        'public/models/base.glb',
        'public/models/south-side-gate.glb',
        'public/data/models.json',
        'public/data/landmarks.json',
        'public/data/sources.json',
        'public/data/geography.geojson',
        'public/data/overview.json',
        'public/data/low-planting.json',
        'public/data/vegetation.json',
        'public/data/vegetation-zones.json',
    }
    assert set(changed) <= allowed, changed
    report = {
        'passed': True,
        'changedFiles': changed,
        'retainedSourceObjects': len(unchanged),
        'lowPlanting': planting_check,
        'vegetation': tree_check,
        'elevation': record['elevation'],
        **budget,
    }
    (target / 'work/south-side-update.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    if args.publish:
        publish(ROOT, target, before)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
