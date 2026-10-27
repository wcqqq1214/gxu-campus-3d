"""Compare refined landmarks with saved source and decoded near/base assets.

Requires the local source blend. Tolerances cover mesh welding and Draco
quantization, not real-world accuracy. Run separately from factory-only CI tests.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from geometry import MATERIALS
from landmarks import landmark

TARGETS = ('huixue', 'laboratory', 'student-center', 'west-gate')


def distance(points, reference):
    assert points and reference, 'Missing landmark geometry'
    tree = KDTree(len(reference))
    for index, point in enumerate(reference):
        tree.insert(point, index)
    tree.balance()
    return max(tree.find(point)[2] for point in points)


def compare(actual, expected, tolerance):
    error = max(distance(actual, expected), distance(expected, actual))
    assert error < tolerance, ('Landmark mesh mismatch', error, tolerance)
    return error


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return obj.name


def main():
    records = {r['id']: r for r in json.loads((ROOT / 'public/data/landmarks.json').read_text())}
    buildings = {r['id']: r for r in json.loads((ROOT / 'public/data/buildings.json').read_text())}
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
    MATERIALS[:] = list(bpy.data.materials)
    colors = {material.name: i for i, material in enumerate(MATERIALS)}
    expected = {}
    for key in TARGETS:
        record = records[key]
        for detail in (True, False):
            expected[key, detail] = landmark(
                record, buildings.get(record.get('osmId')),
                record['elevation'], colors, detail).v
    report = {'source': {}, 'base': {}, 'near': {}}
    for key in TARGETS:
        obj, = [o for o in bpy.context.scene.objects if o.get('landmark') == key]
        points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        report['source'][key] = compare(points, expected[key, True], .001)
    assets = [('base.glb', False, 'base')]
    assets.extend((key + '.glb', True, 'near') for key in TARGETS)
    for filename, detail, level in assets:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT / 'public/models' / filename))
        bpy.context.view_layer.update()
        for key in TARGETS if level == 'base' else (filename[:-4],):
            points = [obj.matrix_world @ vertex.co
                      for obj in bpy.context.scene.objects
                      if obj.type == 'MESH' and root_name(obj) == 'landmark-' + key
                      for vertex in obj.data.vertices]
            report[level][key] = compare(points, expected[key, detail], .02 if detail else .05)
    output = ROOT / 'work/landmark-refinements.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
