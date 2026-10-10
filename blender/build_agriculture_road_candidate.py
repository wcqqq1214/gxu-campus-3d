"""Build the isolated agriculture road candidate; never update production assets.

Historical reproduction requires the pinned pre-repair production baseline.
Current production builds use data/road-landing-overrides.json instead.
"""
import argparse,bpy,json,hashlib,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
WORK=args.output.resolve()
WORK.relative_to(ROOT/'work')
config=json.loads((ROOT/'data/refinement/agriculture-road-landing-proposal.json').read_text())
for name,key in [('blender/gxu-campus.blend','sourceSHA256'),('public/models/base.glb','baseSHA256')]:
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=config[key]:
        raise ValueError('Production baseline changed; recheck the candidate before rebuilding')
for folder in ['before/blender','before/public/models','before/public/data']:(WORK/folder).mkdir(parents=True,exist_ok=True)
for name in ['blender/gxu-campus.blend','public/models/base.glb','public/data/models.json']:
    target=WORK/'before'/name
    if target.exists() and target.read_bytes()!=(ROOT/name).read_bytes():
        raise ValueError('Refusing to replace a different saved baseline')
    if not target.exists():shutil.copy2(ROOT/name,target)
sys.path[:0]=[str(ROOT/'blender'),str(ROOT/'scripts')]
from road_landing_contract import load_landings
from road_landing_geometry import build_landings
from repair_foundation_candidate import source_mesh
from export_repaired_ground import road_object
from foundation_contract import load_foundations
import terrain_export
from terrain_export import replace_precise_terrain
from preserve_glb_geometry import compact_buffer_views
bpy.ops.wm.open_mainfile(filepath=str(WORK/'before/blender/gxu-campus.blend'))
roads=bpy.data.objects['roads'];terrain=bpy.data.objects['terrain']
r,report=build_landings(load_landings(ROOT,'data/refinement/agriculture-road-landing-proposal.json'),source_mesh(roads),source_mesh(terrain),next(i for i,m in enumerate(roads.data.materials) if m.name=='road'))
from mathutils import Vector
from mathutils.bvhtree import BVHTree
def replace_road(obj, result):
    old = obj.data
    if len(old.uv_layers) != 1:
        raise ValueError('Expected exactly one road UV layer')
    old.calc_loop_triangles()
    lookup = {(tuple(tuple(old.vertices[i].co) for i in p.vertices), p.material_index):
              (p.use_smooth, [tuple(old.uv_layers.active.data[k].uv) for k in p.loop_indices])
              for p in old.polygons}
    flat = [Vector((v.co.x, v.co.y, 0)) for v in old.vertices]
    triangles = list(old.loop_triangles)
    tree = BVHTree.FromPolygons(flat, [tuple(t.vertices) for t in triangles], all_triangles=True)
    mesh = bpy.data.meshes.new(old.name + '-road-landing')
    mesh.from_pydata(result.v, [], result.f)
    new_keys = {(tuple(tuple(mesh.vertices[i].co) for i in p.vertices), material)
                for p, material in zip(mesh.polygons, result.m)}
    for face in old.polygons:
        key = (tuple(tuple(old.vertices[i].co) for i in face.vertices), face.material_index)
        if key in new_keys:
            continue
        for k in face.loop_indices:
            point = old.vertices[old.loops[k].vertex_index].co
            if tuple(old.uv_layers.active.data[k].uv) != (point.x / 4, point.y / 4):
                raise ValueError('Changed road must use the original XY/4 projection')
    for material in old.materials:
        mesh.materials.append(material)
    uv = mesh.uv_layers.new(name=old.uv_layers.active.name)
    unchanged = projected = 0
    for face, material in zip(mesh.polygons, result.m):
        face.material_index = material
        points = [mesh.vertices[i].co for i in face.vertices]
        prior = lookup.get((tuple(tuple(p) for p in points), material))
        if prior:
            face.use_smooth, values = prior
            unchanged += 1
        else:
            center = sum((Vector((p.x, p.y, 0)) for p in points), Vector()) / len(points)
            _, _, index, distance = tree.find_nearest(center)
            if index is None or distance > .002:
                raise ValueError('Retessellated road escaped its original XY surface')
            tri = triangles[index]
            if tri.material_index != material:
                raise ValueError('Repair crossed an original road material boundary')
            values = [(p.x / 4, p.y / 4) for p in points]
            face.use_smooth = old.polygons[tri.polygon_index].use_smooth
            projected += 1
        for k, value in zip(face.loop_indices, values):
            uv.data[k].uv = value
    obj.data = mesh
    return {'unchangedFacesWithExactUVs': unchanged, 'projectedFaces': projected}


uv=replace_road(roads,r)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'candidate.blend'),compress=True,relative_remap=False)
(WORK/'build.json').write_text(json.dumps({'roadLandings':report,'uvPreservation':uv},indent=2)+'\n')
target=WORK/'base.glb';shutil.copy2(WORK/'before/public/models/base.glb',target)
export=road_object(roads,load_foundations(ROOT)['foundations'],json.loads((ROOT/'public/data/pavings.json').read_text())['pavings'])
# Pin historical candidate precision independently of future exporter changes.
original_bits=terrain_export.ROAD_UV_BITS
try:
    terrain_export.ROAD_UV_BITS=12
    replace_precise_terrain(target,[terrain,export])
finally:
    terrain_export.ROAD_UV_BITS=original_bits
compact_buffer_views(target)
# Keep the candidate node metadata consistent with its actual encoding.
from preserve_glb_geometry import unpack,mesh_nodes_by_name
import struct
doc,binary=unpack(target.read_bytes())
mesh_nodes_by_name(doc)['roads']['extras']['roadMaterialTexcoordQuantizationBits']=12
header=json.dumps(doc,separators=(',',':')).encode();header+=b' '*(-len(header)%4)
target.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
manifest=json.loads((WORK/'before/public/data/models.json').read_text())
manifest['base'].update(bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(WORK/'models.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(report,uv,'Initial bytes',manifest['base']['bytes']+manifest['trees']['bytes'],flush=True)

# Make standard validators usable against the isolated candidate.
for folder in ['blender','public/models','public/data']:(WORK/'check-root'/folder).mkdir(parents=True,exist_ok=True)
for folder in ['public/models','public/data']:
    for path in (ROOT/folder).iterdir():
        if not path.is_file():continue
        target=WORK/'check-root'/folder/path.name
        actual=WORK/path.name if path.name in ('base.glb','models.json') else path
        if not target.exists():target.symlink_to(actual)
source=WORK/'check-root/blender/gxu-campus.blend'
if not source.exists():source.symlink_to(WORK/'candidate.blend')
