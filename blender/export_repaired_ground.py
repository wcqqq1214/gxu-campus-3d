"""Re-export repaired ground from an editable source into a copied base GLB.

Keeps other published nodes and material/texture payloads. Does not save the
source or update the manifest; callers validate the candidate before promotion.
"""
import argparse,json,sys,struct
from pathlib import Path
import bpy
from mathutils import Vector,Matrix,geometry as math_geometry
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'));sys.path.insert(0,str(ROOT/'scripts'))
from geometry import Mesh
import geometry
from foundation_contract import load_foundations
from road_export import conform_foundation_road_exports
from paving_geometry import split_grounded_road_exports
from terrain_export import replace_precise_terrain
from preserve_glb_geometry import unpack,mesh_nodes_by_name


def road_object(source,records,pavings):
    if source.matrix_world!=Matrix.Identity(4) or source.modifiers:
        raise ValueError('Expected untransformed ordinary source roads without modifiers')
    old=source.data
    mesh=Mesh();mesh.v=[tuple(v.co) for v in old.vertices]
    mesh.f=[tuple(p.vertices) for p in old.polygons];mesh.m=[p.material_index for p in old.polygons]
    groups=conform_foundation_road_exports({'roads':mesh},records)
    groups=split_grounded_road_exports(groups,pavings,
        [r['groundedServiceRoad'] for r in records if r.get('groundedServiceRoad')])
    geometry.MATERIALS=list(old.materials)
    source.name='editable-source-roads'
    obj=groups['roads'].object('roads',bpy.context.scene.collection,{'layer':'roads'})
    # Reassembling a mesh must not replace published UVs with a new projection.
    lookup={(old.materials[p.material_index].name,tuple(tuple(old.vertices[i].co) for i in p.vertices)):
            (p.use_smooth,[tuple(old.uv_layers.active.data[k].uv) for k in p.loop_indices]) for p in old.polygons}
    old.calc_loop_triangles();trees={};triangles={};changed=0;maximum=0
    for p in obj.data.polygons:
        name=obj.data.materials[p.material_index].name
        key=(name,tuple(tuple(obj.data.vertices[i].co) for i in p.vertices))
        original=lookup.get(key)
        if original:p.use_smooth,uvs=original
        else:
            changed+=1
            if name not in trees:
                ts=[t for t in old.loop_triangles if old.materials[t.material_index].name==name]
                triangles[name]=ts
                trees[name]=BVHTree.FromPolygons([v.co for v in old.vertices],[tuple(t.vertices) for t in ts],all_triangles=True)
            center=sum((obj.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
            _,_,index,distance=trees[name].find_nearest(center)
            if index is None or distance>.002:raise ValueError(('Road export changed source plane',name,distance))
            maximum=max(maximum,distance);tri=triangles[name][index]
            xyz=[old.vertices[i].co for i in tri.vertices]
            uv=[Vector((*old.uv_layers.active.data[k].uv,0)) for k in tri.loops]
            uvs=[math_geometry.barycentric_transform(obj.data.vertices[i].co,*xyz,*uv)[:2] for i in p.vertices]
            p.use_smooth=old.polygons[tri.polygon_index].use_smooth
        for k,uv in zip(p.loop_indices,uvs):obj.data.uv_layers.active.data[k].uv=uv
    print('Road export UV interpolation',changed,'faces; max source-plane distance',maximum,flush=True)
    return obj


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--target',type=Path,required=True,help='Existing candidate copy of the published base GLB')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    records=load_foundations(ROOT)['foundations']
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    terrain=bpy.data.objects['terrain']
    roads=road_object(bpy.data.objects['roads'],records,json.loads((ROOT/'public/data/pavings.json').read_text())['pavings'])
    replace_precise_terrain(args.target,[terrain,roads])
    document,binary=unpack(args.target.read_bytes())
    mesh_nodes_by_name(document)['roads'].setdefault('extras',{}).update(
        positionQuantizationBits=18,sharedPositionQuantizationBounds=True,
        roadMaterialPositionQuantizationBits=18,roadMaterialTexcoordQuantizationBits=12,
        otherMaterialTexcoordQuantizationBits=12)
    header=json.dumps(document,separators=(',',':')).encode();header+=b' '*(-len(header)%4)
    args.target.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+
        struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)

if __name__=='__main__':main()
