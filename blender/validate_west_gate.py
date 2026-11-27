"""Compare the editable west gate with the saved campus and both published LODs."""

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from campus_gates import campus_gate
from validate_landmark_refinements import compare


def gate_object():
    (gate,) = [o for o in bpy.context.scene.objects if o.get('landmark') == 'west-gate']
    return gate


def measure(obj, expected):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    obj.data.calc_loop_triangles()
    count = len(obj.data.loop_triangles)
    return {
        'triangles': count,
        'maxVertexErrorMeters': compare(points, expected.v, 0.006),
    }


def main():
    record = next(
        item
        for item in json.loads((ROOT / 'public/data/landmarks.json').read_text())
        if item['id'] == 'west-gate'
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    levels = {
        detail: campus_gate(record, record['elevation'], {}, detail)
        for detail in (True, False)
    }
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
    source = gate_object()
    assert {g.name for g in source.vertex_groups} == {g[0] for g in levels[True].parts}
    report = {'source': measure(source, levels[True])}
    for filename, detail in [('base', False), ('west-gate', True)]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(
            filepath=str(ROOT / 'public/models' / (filename + '.glb'))
        )
        report[filename] = measure(gate_object(), levels[detail])
    (ROOT / 'work/west-gate-geometry.json').write_text(
        json.dumps(report, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
