"""Render and check a bounded west-wall candidate, without saving production.

The top four rows are a conservative modeling scope, not four measured rows
in the photograph. Hidden lower floors keep their existing estimated windows.
"""
import argparse
from collections import Counter
import copy
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
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
args.output.mkdir(parents=True, exist_ok=True)
source = ROOT/'public/data/buildings.json'
original = next(b for b in json.loads(source.read_text()) if b['id'] == 'way/957404988')
candidate = copy.deepcopy(original)
facade = next(f for f in candidate['form']['facades'] if f['part'] == 'north-office' and f['edge'] == 12)
assert not facade['rule'].get('skipWindowLevels'), 'Reassess candidate against changed production rules'
facade['rule']['skipWindowLevels'] = [5, 6, 7, 8]

bpy.ops.wm.read_factory_settings(use_empty=True)
colors = {'white':(.86,.85,.80), 'stone':(.64,.60,.49), 'pink':(.77,.68,.66),
          'paleRoof':(.48,.49,.46), 'dark':(.075,.09,.10), 'glass':(.12,.24,.29),
          'shadeGlass':(.085,.15,.19), 'blueRoof':(.06,.33,.56), 'red':(.48,.12,.08)}
C = {name: material(name, color) for name, color in colors.items()}
MATERIAL_NAMES = {index: name for name, index in C.items()}


def faces(mesh):
    return Counter((MATERIAL_NAMES[mesh.m[i]], tuple(tuple(mesh.v[j]) for j in face))
                   for i, face in enumerate(mesh.f))


checks = []
for detail in (False, True):
    before = ordinary_building(original, 0, C, detail)
    after = ordinary_building(candidate, 0, C, detail)
    old, new = faces(before), faces(after)
    assert not (new-old), 'Candidate must only remove existing window geometry'
    removed = old-new
    assert removed, 'Candidate must actually differ'
    for (name, vertices), count in removed.items():
        assert name in ('white', 'glass', 'shadeGlass'), name
        assert all(-735.2 < v[0] < -734.4 and -730 < v[1] < -713 and 16.5 < v[2] < 29.7 for v in vertices), vertices
    trees = [BVHTree.FromPolygons(m.v, m.f) for m in (before, after)]
    samples = []
    # Fixed prior default-window locations, separate from candidate skip rules.
    for level in range(9):
        for y in (-726.7378, -721.4538, -716.1698):
            z = (level+.56)*3.3
            # Offset from the central vertical glazing mullion in the near mesh.
            start = Vector((-736, y+.3, z))
            hits = [t.ray_cast(start, Vector((1,0,0)), 2) for t in trees]
            assert all(h[0] is not None for h in hits), (detail, level, y)
            names = [MATERIAL_NAMES[m.m[h[2]]] for m,h in zip((before,after),hits)]
            assert names[0] in ('glass', 'shadeGlass'), names
            if level >= 5:
                assert names[1] == 'white', names
                assert hits[1][1].x < -.99, hits[1][1]
            else:
                assert names[1] == names[0] and (hits[0][0]-hits[1][0]).length < 1e-6
            samples.append(dict(level=level, y=y+.3, z=z, before=names[0], after=names[1]))
    checks.append(dict(detail=detail, removedFaces=sum(removed.values()),
                       noAddedOrChangedRetainedFaces=True, samples=samples))

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.world = bpy.data.worlds.new('candidate-background')
scene.world.color = (.16,.19,.20)
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x = 1000
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
camdata = bpy.data.cameras.new('candidate-camera')
camera = bpy.data.objects.new('candidate-camera', camdata)
scene.collection.objects.link(camera)
scene.camera = camera
views = [('west', (-795,-721.45,20), (-727,-721.45,16), 40),
         ('southwest', (-790,-790,59), (-700,-751,13), 113)]
for label, b in [('original', original), ('candidate', candidate)]:
    mesh = ordinary_building(b, 0, C, True)
    obj = mesh.object(label, scene.collection)
    for name, position, target, scale in views:
        camera.location = Vector(position)
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camdata.type = 'ORTHO'
        camdata.ortho_scale = scale
        scene.render.filepath = str(args.output/f'{label}-{name}.png')
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj, do_unlink=True)

report = dict(buildingId=original['id'], buildingFileSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),
              change=dict(part='north-office', edge=12, skipWindowLevels=[5,6,7,8],
                          basis='Qualitative west upper wall in panorama 659; height cutoff conservative and estimated.'),
              geometryChecks=checks, passed=True, productionModified=False,
              candidateOnly=True, photoMetricRegistrationAccepted=False,
              unresolved=['Lower west wall and west foyer roof occluded', 'South window counts and exact dimensions not established'])
(args.output/'candidate-checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
(args.output/'proposal.json').write_text(json.dumps(dict(original=original,candidate=candidate), ensure_ascii=False)+'\n')
print('Candidate passed both detail modes; rendered four views; no production source or model saved.')
