"""Build a bounded west-gate candidate; --publish installs it after validation."""

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
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
from preserve_glb_geometry import mesh_nodes_by_name, unpack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument(
        '--base-root',
        type=Path,
        help='accepted candidate retaining other unpublished landmarks; candidate-only',
    )
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(
        sys.argv[sys.argv.index('--') + 1 :] if '--' in sys.argv else []
    )
    target = args.output_root.resolve()
    base = args.base_root.resolve() if args.base_root else ROOT
    if args.publish and base != ROOT:
        parser.error('--base-root is candidate-only; publish from a staged formal root')
    with publication_lock(base):
        require_recovered(base)
        before = snapshot(base)
        copy_inputs(base, target, source_root=ROOT)
        for folder in ['app', 'components', 'hooks']:
            shutil.copytree(ROOT / folder, target / folder, dirs_exist_ok=True)
        for name in ['index.html', 'vite.config.ts', 'tsconfig.json']:
            shutil.copy2(ROOT / name, target / name)
        if snapshot(base) != before:
            raise RuntimeError('Inputs changed during candidate copy')
    (target / 'work/baseline.json').write_text(json.dumps(before))
    catalog = json.loads((target / 'public/data/landmarks.json').read_text())
    record = next(item for item in catalog if item['id'] == 'west-gate')
    source = next(
        item
        for item in json.loads((target / 'data/landmarks.json').read_text())
        if item['id'] == record['id']
    )
    record.update(source)
    record['sourceRefs'] = ['osm', record['reference'], *record['additionalReferences']]
    (target / 'public/data/landmarks.json').write_text(
        json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))
    )
    references = json.loads((target / 'public/data/sources.json').read_text())
    fresh = {
        item['id']: item
        for item in json.loads((target / 'data/sources.json').read_text())
        if item['id'] in record['sourceRefs']
    }
    references['sources'] = [
        fresh.pop(item['id'], item) for item in references['sources']
    ] + list(fresh.values())
    (target / 'public/data/sources.json').write_text(
        json.dumps(references, ensure_ascii=False, indent=2) + '\n'
    )

    bpy.ops.wm.open_mainfile(filepath=str(target / 'blender/gxu-campus.blend'))
    (old,) = [
        obj for obj in bpy.context.scene.objects if obj.get('landmark') == record['id']
    ]
    MATERIALS[:] = list(bpy.data.materials)
    colors = {material.name: i for i, material in enumerate(MATERIALS)}
    collection = old.users_collection[0]
    properties = dict(old.items())
    name = old.name
    unchanged = {
        obj.name: (obj.as_pointer(), obj.data.as_pointer() if obj.data else None)
        for obj in bpy.context.scene.objects
        if obj != old
    }
    high = campus_gate(record, record['elevation'], colors, True)
    low = campus_gate(record, record['elevation'], colors, False)
    key = 'landmark-west-gate'
    original = (target / 'public/models/base.glb').read_bytes()
    export_properties = dict(
        mesh_nodes_by_name(unpack(original)[0])[key].get('extras', {})
    )
    for mesh, path in [
        (high, target / 'public/models/west-gate.glb'),
        (low, target / 'work/west-base.glb'),
    ]:
        obj = mesh.object(key, collection, export_properties)
        export_detail(obj, path)
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(data)
    updated = splice_nodes(
        original, (target / 'work/west-base.glb').read_bytes(), {key}
    )
    validate_retained(original, updated, {key})
    (target / 'public/models/base.glb').write_bytes(updated)
    old_mesh = old.data
    bpy.data.objects.remove(old, do_unlink=True)
    if not old_mesh.users:
        bpy.data.meshes.remove(old_mesh)
    high.object(
        name,
        collection,
        {**properties, 'modelingBasis': 'photo', 'reference': record['reference']},
    )
    assert all(
        (
            bpy.data.objects[key].as_pointer(),
            bpy.data.objects[key].data.as_pointer()
            if bpy.data.objects[key].data
            else None,
        )
        == value
        for key, value in unchanged.items()
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(target / 'blender/gxu-campus.blend'), compress=True
    )
    manifest = json.loads((target / 'public/data/models.json').read_text())
    for asset in [
        manifest['base'],
        next(item for item in manifest['landmarks'] if item['id'] == record['id']),
    ]:
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
            [f'--baseline-root={base}', '--update-kind=west-gate'],
        ),
        ('west-geometry', 'validate_west_gate.py', []),
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
    changed = [
        path for path, digest in snapshot(target).items() if before.get(path) != digest
    ]
    allowed = {
        'blender/gxu-campus.blend',
        'public/models/base.glb',
        'public/models/west-gate.glb',
        'public/data/models.json',
        'public/data/landmarks.json',
        'public/data/sources.json',
    }
    assert set(changed) <= allowed, changed
    report = {
        'passed': True,
        'changedFiles': changed,
        'retainedSourceObjects': len(unchanged),
        **budget,
    }
    (target / 'work/west-gate-update.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    if args.publish:
        publish(ROOT, target, before)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
