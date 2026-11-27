"""Rebuild the gate's neighbours and their streamed chunks, then validate/publish."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'blender'), str(ROOT / 'scripts')]
from mathutils.kdtree import KDTree

from building_models import building_mesh
from college_chunk_budget import optimize_export
from detail_export import export_detail, geometry_bytes
from generic_buildings import compact_form_source
from geometry import MATERIALS, Mesh
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
from new_east_neighbours import BUILDING_IDS, EAST_25, WEST_SHOPS, ensure_materials
from preserve_glb_geometry import mesh_nodes_by_name, unpack
from terrain_elevation import make_elevation
from validate_generic import component_vertices


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
        if snapshot(ROOT) != before:
            raise RuntimeError('Inputs changed during candidate copy')
    (target / 'work/baseline.json').write_text(json.dumps(before))
    buildings = {
        b['id']: b
        for b in json.loads((target / 'public/data/buildings.json').read_text())
    }
    manifest = json.loads((target / 'public/data/models.json').read_text())
    zones = [z for z in manifest['zones'] if BUILDING_IDS.intersection(z['featureIds'])]
    bpy.ops.wm.open_mainfile(filepath=str(target / 'blender/gxu-campus.blend'))
    MATERIALS[:] = list(bpy.data.materials)
    C = {m.name: i for i, m in enumerate(MATERIALS)}
    ensure_materials(C, refresh=True)
    objects = {
        o.get('featureId'): o for o in bpy.context.scene.objects if o.get('featureId')
    }
    elevation = make_elevation(
        json.loads((target / 'public/data/terrain.json').read_text())
    )
    original = (target / 'public/models/base.glb').read_bytes()
    base_nodes = mesh_nodes_by_name(unpack(original)[0])
    replacement = original
    updated = []
    for zone in zones:
        key = zone['id']
        low, high = Mesh(), Mesh()
        for fid in zone['featureIds']:
            b = buildings[fid]
            old = objects[fid]
            z = elevation(*b['center'])
            assert abs(z - b['elevation']) < 0.0051, (fid, 'unexpected source datum')
            near = building_mesh(b, z, C, True)
            if fid in BUILDING_IDS:
                updated.append((old, near))
            # Only the selected facades may change. Check the other members
            # before writing their shared node, including any dedicated offices.
            groups = near.parts[:3] if fid in BUILDING_IDS else near.parts
            for group, start, end in groups:
                actual = component_vertices(old, old.vertex_groups[group])
                predicted = near.v[start:end]
                if not actual and not predicted:
                    continue
                assert actual and predicted, (fid, group, 'missing component')
                for left, right in ((actual, predicted), (predicted, actual)):
                    kd = KDTree(len(right))
                    for i, point in enumerate(right):
                        kd.insert(point, i)
                    kd.balance()
                    assert all(kd.find(p)[2] < 0.001 for p in left), (fid, group)
            low.extend(building_mesh(b, z, C, False))
            high.extend(near)
        props = dict(base_nodes[key]['extras'])
        far_path = target / 'work' / 'base.glb'
        near_path = target / 'public' / zone['url']
        for mesh, path in [(low, far_path), (high, near_path)]:
            obj = mesh.object(key, bpy.context.scene.collection, props)
            export_detail(obj, path, base_chunk=mesh is low)
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(data)
        optimize_export(far_path)
        replacement = splice_nodes(replacement, far_path.read_bytes(), {key})
        raw = near_path.read_bytes()
        zone.update(
            bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            geometryBytes=geometry_bytes(raw),
        )
    assert {old['featureId'] for old, near in updated} == BUILDING_IDS
    retained = validate_retained(original, replacement, {z['id'] for z in zones})
    (target / 'public/models/base.glb').write_bytes(replacement)
    for old, near in updated:
        name, collection, props = old.name, old.users_collection[0], dict(old.items())
        old_mesh = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if not old_mesh.users:
            bpy.data.meshes.remove(old_mesh)
        obj = near.object(
            name,
            collection,
            {
                **props,
                'facadeBasis': 'photo-informed-estimate',
                'facadeSourceRefs': 'newEastTour2025,newEastRoute2026'
                + (',newEastExterior2021' if props['featureId'] == WEST_SHOPS else ''),
            },
        )
        if props['featureId'] == EAST_25:
            obj['shopfrontBasis'] = 'user-located-estimate'
        compact_form_source(obj)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(target / 'blender/gxu-campus.blend'), compress=True
    )
    manifest['base'].update(
        bytes=len(replacement), sha256=hashlib.sha256(replacement).hexdigest()
    )
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
            [f'--baseline-root={ROOT}', '--update-kind=new-east-neighbours'],
        ),
        *[
            (
                'neighbour-geometry-' + z['id'],
                'validate_generic.py',
                ['--chunk=' + z['id'], '--report-prefix=neighbours-' + z['id']],
            )
            for z in zones
        ],
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
        ],
        target,
        'catalog-and-assets',
    )
    changed = [p for p, h in snapshot(target).items() if before.get(p) != h]
    assert set(changed) <= {
        'blender/gxu-campus.blend',
        'public/models/base.glb',
        *('public/' + zone['url'] for zone in zones),
        'public/data/models.json',
    }, changed
    report = {
        'passed': True,
        'changedFiles': changed,
        'retainedBaseNodes': retained,
        'updatedBuildings': sorted(BUILDING_IDS),
        'verifiedChunkBuildings': sum(len(zone['featureIds']) for zone in zones),
        **budget,
    }
    (target / 'work/neighbours-update.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    if args.publish:
        publish(ROOT, target, before)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
