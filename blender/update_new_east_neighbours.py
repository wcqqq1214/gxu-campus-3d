"""Rebuild the gate's neighbours and their shared chunk, then validate/publish."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'blender'))
from geometry import Mesh, MATERIALS
from generic_buildings import ordinary_building, compact_form_source
from new_east_neighbours import BUILDING_IDS, WEST_SHOPS, EAST_25, ensure_materials
from incremental_glb import splice_nodes, validate_retained
from incremental_update import copy_inputs, snapshot, publication_lock, publish, require_recovered, run_checked
from initial_model_budget import check_initial_model_budget
from preserve_glb_geometry import unpack, mesh_nodes_by_name
from detail_export import export_detail
from validate_generic import component_vertices
from mathutils.kdtree import KDTree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    target = args.output_root.resolve()
    with publication_lock(ROOT):
        require_recovered(ROOT)
        before = snapshot(ROOT)
        copy_inputs(ROOT, target)
        if snapshot(ROOT) != before:
            raise RuntimeError('Inputs changed during candidate copy')
    (target/'work/baseline.json').write_text(json.dumps(before))
    buildings = json.loads((target/'public/data/buildings.json').read_text())
    selected = [b for b in buildings if b['id'] in BUILDING_IDS]
    assert len(selected) == len(BUILDING_IDS)
    key, = {b['chunk'] for b in selected}
    chunk = [b for b in buildings if b.get('chunk') == key]
    bpy.ops.wm.open_mainfile(filepath=str(target/'blender/gxu-campus.blend'))
    MATERIALS[:] = list(bpy.data.materials)
    C = {m.name: i for i, m in enumerate(MATERIALS)}
    ensure_materials(C, refresh=True)
    objects = {o.get('featureId'): o for o in bpy.context.scene.objects if o.get('featureId')}
    low, high = Mesh(), Mesh()
    updated = []
    for b in chunk:
        # This updater intentionally handles only the chunk's simple forms.
        # Refuse a future specialised building rather than silently flattening it.
        assert not b.get('customModel') and not b.get('landmark')
        assert not b['form']['parts'] and set(b['form']) <= {
            'version', 'archetype', 'levels', 'height', 'parts', 'roof', 'entrances'}
        old = objects[b['id']]
        body = component_vertices(old, old.vertex_groups['01_主体轮廓'])
        z = min(p.z for p in body)+.5
        assert abs(z-b['elevation']) < .0051, (b['id'], 'unexpected source datum')
        near = ordinary_building(b, z, C, True)
        # Keep the selected buildings' structural forms too; refuse stale data.
        groups = near.parts[:3] if b['id'] in BUILDING_IDS else near.parts
        for group, start, end in groups:
            actual = component_vertices(old, old.vertex_groups[group])
            predicted = near.v[start:end]
            if not actual and not predicted:
                continue
            assert actual and predicted, (b['id'], group, 'missing component')
            for left, right in ((actual, predicted), (predicted, actual)):
                kd = KDTree(len(right))
                for i, p in enumerate(right):
                    kd.insert(p, i)
                kd.balance()
                assert all(kd.find(p)[2] < .001 for p in left), (b['id'], group)
        if b['id'] in BUILDING_IDS:
            updated.append((old, near))
        low.extend(ordinary_building(b, z, C, False))
        high.extend(near)
    original = (target/'public/models/base.glb').read_bytes()
    props = dict(mesh_nodes_by_name(unpack(original)[0])[key].get('extras', {}))
    for mesh, path in [(low, target/'work/neighbours-base.glb'), (high, target/'public/models'/f'{key}.glb')]:
        obj = mesh.object(key, bpy.context.scene.collection, props)
        export_detail(obj, path)
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(data)
    replacement = splice_nodes(original, (target/'work/neighbours-base.glb').read_bytes(), {key})
    retained = validate_retained(original, replacement, {key})
    (target/'public/models/base.glb').write_bytes(replacement)
    for old, near in updated:
        name, collection, props = old.name, old.users_collection[0], dict(old.items())
        old_mesh = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if not old_mesh.users:
            bpy.data.meshes.remove(old_mesh)
        obj = near.object(name, collection, {**props, 'facadeBasis': 'photo-informed-estimate',
                          'facadeSourceRefs': 'newEastTour2025,newEastRoute2026'
                          + (',newEastExterior2021' if props['featureId'] == WEST_SHOPS else '')})
        if props['featureId'] == EAST_25:
            obj['shopfrontBasis'] = 'user-located-estimate'
        compact_form_source(obj)
    bpy.ops.wm.save_as_mainfile(filepath=str(target/'blender/gxu-campus.blend'), compress=True)
    manifest = json.loads((target/'public/data/models.json').read_text())
    for asset in [manifest['base'], next(x for x in manifest['zones'] if x['id'] == key)]:
        raw = (target/'public'/asset['url']).read_bytes()
        asset.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    budget = check_initial_model_budget(manifest['base']['bytes']+manifest['trees']['bytes'])
    (target/'public/data/models.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    for label, script, extra in [
        ('source-retention', 'validate_incremental_source.py', [f'--baseline-root={ROOT}', '--update-kind=new-east-neighbours']),
        ('neighbour-geometry', 'validate_generic.py', [f'--chunk={key}', '--report-prefix=new-east-neighbours']),
    ]:
        run_checked([bpy.app.binary_path, '-b', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                     '--python', str(target/'blender'/script), '--', *extra], target, label)
    run_checked([os.environ.get('NODE_BIN', 'node'), '--experimental-strip-types', '--test',
                 'scripts/test-campus.mjs', 'scripts/test-sources.mjs'], target, 'catalog-and-assets')
    changed = [p for p, h in snapshot(target).items() if before.get(p) != h]
    assert set(changed) <= {'blender/gxu-campus.blend', 'public/models/base.glb',
                            f'public/models/{key}.glb', 'public/data/models.json'}, changed
    report = {'passed': True, 'changedFiles': changed, 'retainedBaseNodes': retained,
              'updatedBuildings': sorted(BUILDING_IDS), 'verifiedChunkBuildings': len(chunk), **budget}
    (target/'work/neighbours-update.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    if args.publish:
        publish(ROOT, target, before)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
