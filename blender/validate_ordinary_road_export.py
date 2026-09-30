"""Audit ordinary-road export fidelity, with explicit step-edge witnesses."""
import bpy,sys,json,math,hashlib,argparse
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import re
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'blender'))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
from site_geometry import ring_distance
paths=[args.baseline.resolve()/'blender/gxu-campus.blend',args.baseline.resolve()/'public/models/base.glb',R/'public/models/base.glb']
repairs=[r for r in json.loads((R/'public/data/foundations.json').read_text())['foundations'] if r.get('roadExportConformMargin')]
areas=[(r['bounds'][0]-r['roadExportConformMargin'],r['bounds'][1]-r['roadExportConformMargin'],r['bounds'][2]+r['roadExportConformMargin'],r['bounds'][3]+r['roadExportConformMargin']) for r in repairs]
def read(path):
 if path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(path))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path))
 bpy.context.view_layer.update();vs=[];ts=[];polys=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or re.sub(r'\.\d{3,}$','',o.name) not in ('roads','paving-civil-platform-service-export'):continue
  offset=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);o.data.calc_loop_triangles()
  for tri in o.data.loop_triangles:
   ids=[offset+i for i in tri.vertices];a,b,c=[vs[i] for i in ids]
   if (b-a).cross(c-a).z>1e-9:ts.append(ids);polys.append([vs[i].copy() for i in ids])
 return BVHTree.FromPolygons(vs,ts,all_triangles=True),polys
def hit(tree,p):
 q=tree.ray_cast(Vector((*p,150)),Vector((0,0,-1)),300)[0];return None if q is None else q.z
source,source_polys=read(paths[0]);road=bpy.data.objects['roads'];road.data.calc_loop_triangles();points={};counts={};excluded=0
for t in road.data.loop_triangles:
 vs=[road.matrix_world@road.data.vertices[k].co for k in t.vertices];n=(vs[1]-vs[0]).cross(vs[2]-vs[0]);c=sum(vs,Vector())/3
 if n.z<=1e-9:continue
 p=(c.x,c.y)
 # The local repair is covered separately by its dense boundary/grid test.
 if any(x0<p[0]<x1 and y0<p[1]<y1 for x0,y0,x1,y1 in areas):continue
 ring=[v[:2] for v in vs];ring.append(ring[0])
 if ring_distance(p,ring)<.05:excluded+=1;continue
 mat=road.data.materials[t.material_index].name;counts[mat]=counts.get(mat,0)+1;points[p]=mat
rows={p:[hit(source,p)] for p in points}
for path in paths[1:]:
 tree,_=read(path)
 for p in points:rows[p].append(hit(tree,p))
errors=[];new_misses=[];old_misses=[];old_large=[];current_large=[];deltas=[];boundary_witnesses=[]
for p,(s,b,a) in rows.items():
 if s is None:continue
 if b is None:old_misses.append(p)
 if a is None:
  new_misses.append(p)
  if b is not None:errors.append(['new miss',p,points[p]])
  continue
 ae=abs(a-s);be=abs(b-s) if b is not None else None
 deltas.append((ae,p,points[p],s,b,a))
 if be is not None and be>.025:old_large.append(p)
 if ae>.025:
  current_large.append((p,ae,be))
  hit_source,_,idx,_=source.ray_cast(Vector((*p,150)),Vector((0,0,-1)),300)
  ring=[v[:2] for v in source_polys[idx]];ring.append(ring[0]);distance=ring_distance(p,ring)
  nearest,_,_,surface_distance=tree.find_nearest(hit_source)
  if distance<=.01 and surface_distance<=.01:
   boundary_witnesses.append({'xy':p,'sourceTopTriangleEdgeDistance':distance,'candidate3DSurfaceDistance':surface_distance,'pointwiseHeightDifference':ae})
  elif be is None or ae>be+.002:errors.append(['increased source error',p,ae,be])
r={'passed':not errors,'scope':'All upward ordinary-road triangle centroids with at least 5cm to their own triangle XY boundary, outside the separately checked third-teaching repair collar. Ordinary roads plus the separate civil service node compared with the saved ordinary source mesh; decorative geometry from infrastructure nodes is not road pavement. Source top-triangle edges within 1cm are separately checked by candidate 3D nearest-surface distance <=1cm because a lateral quantization shift at a real step changes ray height; these are explicitly reported. New misses fail; errors above 2.5cm fail if worsened by more than 2mm. Existing errors and excluded small/edge faces are reported, not certified.','materialCandidateSamples':counts,'samples':len(points),'excludedSmallOrEdgeTriangles':excluded,'oldMisses':old_misses,'candidateMisses':new_misses,'oldErrorsOver25mm':len(old_large),'candidateErrorsOver25mm':current_large,'discontinuityBoundaryWitnesses':boundary_witnesses,'worstSourceErrors':sorted(deltas,reverse=True)[:10],'errors':errors,'files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(r,indent=2)+'\n');print('GLOBAL_ROAD_REGRESSION',r['passed'],len(points),len(errors),flush=True);assert r['passed'],errors[:10]
