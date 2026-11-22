"""Audit independently loaded source and GLB meshes for tree crossings/containment.

Read-only: imports into a disposable Blender process; never saves source/models.
Use --scope=buildings, --scope=site, or --scope=all (default).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'blender'))
from tree_mesh_audit import check_meshes, snapshot

SCOPES = {
    'buildings': {'buildings', 'context'},
    'site': {'roads', 'water', 'sports'},
    'all': {'buildings', 'context', 'roads', 'water', 'sports'},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(asset, layers, *, require_feature_id=False):
    meshes = []
    for obj in bpy.context.scene.objects:
        if (
            obj.type != 'MESH'
            or obj.get('layer') not in layers
            or not obj.data.polygons
        ):
            continue
        if require_feature_id and not obj.get('featureId'):
            continue
        key = (
            f'{obj.get("featureId")}/{obj.name}'
            if require_feature_id
            else f'{asset}/{obj.name}'
        )
        meshes.append((key, snapshot(obj)))
    return meshes


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1 :] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=tuple(SCOPES), default='all')
    parser.add_argument('--report-prefix', default='tree-clearance')
    args = parser.parse_args(argv)
    if not args.report_prefix or any(
        c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.report_prefix
    ):
        raise ValueError('Invalid clearance report prefix')
    return args


def main():
    args = parse_args()
    layers = SCOPES[args.scope]
    rows = json.loads((ROOT / 'public/data/vegetation.json').read_text())
    manifest = json.loads((ROOT / 'public/data/models.json').read_text())
    fingerprints = {
        'source': sha(ROOT / 'blender/gxu-campus.blend'),
        'trees': sha(ROOT / 'public/data/vegetation.json'),
        'manifest': sha(ROOT / 'public/data/models.json'),
    }

    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
    source_meshes = collect(
        'source', layers, require_feature_id=args.scope == 'buildings'
    )
    source_templates = {
        o['template']: snapshot(o)
        for o in bpy.context.scene.objects
        if o.type == 'MESH' and o.get('template') is not None
    }
    assert set(source_templates) == {0, 1, 2, 3}
    source = check_meshes(rows, source_meshes, {'near': source_templates})
    print(
        'Saved source',
        {k: v for k, v in source.items() if k != 'collisions'},
        flush=True,
    )
    del source_meshes
    bpy.ops.wm.read_factory_settings(use_empty=True)

    templates = {}
    for key, lod in [('trees', 'base'), ('treesNear', 'near')]:
        path = ROOT / 'public' / manifest[key]['url']
        assert sha(path) == manifest[key]['sha256']
        bpy.ops.import_scene.gltf(filepath=str(path))
        templates[lod] = {
            o['template']: snapshot(o)
            for o in bpy.context.scene.objects
            if o.type == 'MESH' and o.get('template') is not None
        }
        assert set(templates[lod]) == {0, 1, 2, 3}
        bpy.ops.wm.read_factory_settings(use_empty=True)

    assets = [manifest['base']] + manifest['zones'] + manifest['landmarks']
    if args.scope != 'buildings':
        assets += manifest['infrastructure'] + manifest['sports']
    shipping_meshes = []
    for asset in assets:
        path = ROOT / 'public' / asset['url']
        assert sha(path) == asset['sha256']
        bpy.ops.import_scene.gltf(filepath=str(path))
        shipping_meshes.extend(collect(asset['url'], layers))
        bpy.ops.wm.read_factory_settings(use_empty=True)
    shipping = check_meshes(rows, shipping_meshes, templates)
    print(
        'Decoded GLBs',
        {k: v for k, v in shipping.items() if k != 'collisions'},
        flush=True,
    )

    report = {
        'scope': args.scope,
        'layers': sorted(layers),
        'fingerprints': fingerprints,
        'source': source,
        'shipping': shipping,
        'passed': source['passed'] and shipping['passed'],
    }
    target = ROOT / 'work/model-checks' / f'{args.report_prefix}-geometry.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    assert report['passed'], (source['collisions'], shipping['collisions'])


if __name__ == '__main__':
    main()
