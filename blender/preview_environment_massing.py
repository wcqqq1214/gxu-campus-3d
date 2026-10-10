"""Render actual shared-generator hypotheses and check their two detail modes.

Never opens/saves the campus blend or writes a shipping GLB. A coarse roof
envelope is intentionally insufficient for production appearance acceptance.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'blender'))
from geometry import material
from generic_buildings import ordinary_building

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--proposal', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
proposal = json.loads(args.proposal.read_text())
if hashlib.sha256((ROOT/'public/data/buildings.json').read_bytes()).hexdigest() != proposal['sourceSha256']:
    raise ValueError('Proposal is stale: resolve it against current production')
args.output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
colors = {'white': (.86,.85,.80), 'stone': (.64,.60,.49), 'pink': (.77,.68,.66),
          'paleRoof': (.48,.49,.46), 'dark': (.075,.09,.10), 'glass': (.12,.24,.29),
          'shadeGlass': (.085,.15,.19), 'blueRoof': (.06,.33,.56), 'red': (.48,.12,.08)}
C = {name: material(name, color) for name, color in colors.items()}


def lower_faces(mesh):
    # Exclude the large spanning body walls in both versions. This checks that
    # all pre-existing entrance/window details below the revised roof remain.
    return Counter((mesh.m[i], tuple(tuple(round(v, 8) for v in mesh.v[j]) for j in face))
                   for i, face in enumerate(mesh.f)
                   if max(mesh.v[j][2] for j in face) < 23.09)


checks = []
original = proposal['original']
for detail in (False, True):
    before = ordinary_building(original, 0, C, detail)
    old_tree = BVHTree.FromPolygons(before.v, before.f)
    for name, building in proposal['variants'].items():
        mesh = ordinary_building(building, 0, C, detail)
        assert lower_faces(mesh) == lower_faces(before), (name, detail, 'lower details changed')
        tree = BVHTree.FromPolygons(mesh.v, mesh.f)
        volume = building['form']['roofVolumes'][0]
        # Independent numerical expectations, not heights copied from the mesh.
        # A point near the opposite longitudinal end, away from roof features.
        ring = building['polygons'][0][0]
        roof_xy = [sum(p[k] for p in ring[:-1])/4 for k in (0, 1)]
        roof_xy[0] -= 30
        points = [('body-roof', roof_xy, 23.1), ('pavilion-cap', volume['center'], 26.5)]
        samples = []
        for kind, xy, expected in points:
            hit = tree.ray_cast(Vector((*xy, 40)), Vector((0,0,-1)), 50)
            old = old_tree.ray_cast(Vector((*xy, 40)), Vector((0,0,-1)), 50)
            assert hit[0] is not None and hit[1].z > .99, (kind, hit)
            assert abs(hit[0].z-expected) < 1e-4, (kind, hit[0].z, expected)
            assert old[0] is not None and abs(old[0].z-expected) > .05, 'Old model must fail proposed height'
            samples.append(dict(kind=kind, xy=xy, expected=expected,
                                actual=hit[0].z, original=old[0].z))
        checks.append(dict(variant=name, detail=detail, samples=samples,
                           preservedLowerFaces=sum(lower_faces(mesh).values()),
                           trianglesBefore=sum(len(f)-2 for f in before.f),
                           trianglesAfter=sum(len(f)-2 for f in mesh.f)))

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.world = bpy.data.worlds.new('hypothesis-background')
scene.world.color = (.16,.19,.20)
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x, scene.render.resolution_y = 1100, 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
camdata = bpy.data.cameras.new('hypothesis-camera')
camera = bpy.data.objects.new('hypothesis-camera', camdata)
scene.collection.objects.link(camera)
scene.camera = camera
exports = []
views = [('northwest', (230,-310,48), (322,-407,12), 125),
         ('southwest', (250,-500,55), (322,-407,12), 125)]
for label, building in {'original': original, **proposal['variants']}.items():
    obj = ordinary_building(building, 0, C, True).object(label, scene.collection)
    for name, position, target, scale in views:
        camera.location = Vector(position)
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camdata.type, camdata.ortho_scale = 'ORTHO', scale
        scene.render.filepath = str(args.output/f'{label}-{name}.png')
        bpy.ops.render.render(write_still=True)
    # Review artifact only: selection prevents the preview camera entering it.
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    obj['candidateOnly'] = True
    obj['productionReady'] = False
    output = args.output/f'{label}.glb'
    bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB',
                             use_selection=True, export_extras=True,
                             export_cameras=False, export_lights=False)
    exports.append(dict(file=output.name, bytes=output.stat().st_size,
                        sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
    bpy.data.objects.remove(obj, do_unlink=True)

report = dict(buildingId=original['id'], proposalSha256=hashlib.sha256(args.proposal.read_bytes()).hexdigest(),
              sourceSha256=proposal['sourceSha256'], checks=checks, passed=True,
              lowerGeometryComparisonDecimals=8,
              cameraViews=views, productionReady=False, productionModified=False,
              reviewGlbs=exports,
              validationScope='Generated mesh height, upward cap/roof normals and lower detail preservation; not real dimensions, facade registration, shipping assets or runtime performance.')
(args.output/'geometry.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print('Both LODs checked; six hypothesis views rendered; no production files changed')
