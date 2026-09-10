"""Rebuild the web base and replace editable road surfaces, preserving near assets.

Run after scripts/surroundings_data.py when only perimeter road styling changes.
The regular build_campus.py also incorporates the same derived data.
"""
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS
script=ROOT/'blender/build_campus.py';namespace={'__file__':str(script),'__name__':'__main__'}
sys.argv.append('--base-only')
try:exec(compile(script.read_text(),str(script),'exec'),namespace)
except SystemExit as result:
    if result.code not in (None,0):raise
roads=namespace['base']['roads'];names=[m.name for m in MATERIALS]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
MATERIALS[:]=[bpy.data.materials[name] for name in names]
old=bpy.data.objects['roads'];collection=old.users_collection[0];data=old.data
bpy.data.objects.remove(old,do_unlink=True);bpy.data.meshes.remove(data)
roads.object('roads',collection,{'layer':'roads','basis':'OSM 道路位置；校外同层路面合并，路幅和路缘按类型估算'})
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
print('Updated editable road surfaces and base GLB',flush=True)
