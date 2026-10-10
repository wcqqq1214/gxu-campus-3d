"""Compare nearest visible depth using snapshots from check-convex-culling.mjs.

Usage: blender --background --python-exit-code 1 --python blender/check_convex_culling_rays.py -- OUTPUT_DIR
"""
import json,array,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(sys.argv[sys.argv.index('--')+1]).resolve()

def read(name,kind):
 a=array.array(kind);a.frombytes((W/name).read_bytes());return a
xyz=read('ray-positions.bin','f');points=[tuple(xyz[i:i+3]) for i in range(0,len(xyz),3)]
ids=read('ray-before.bin','I');source=BVHTree.FromPolygons(points,[tuple(ids[i:i+3]) for i in range(0,len(ids),3)],all_triangles=True)
reports=[];failures=[]
for frame in json.loads((W/'ray-frames.json').read_text()):
 i=frame['order'];ids=read(f'ray-after-{i}.bin','I');retained=set(read(f'ray-faces-{i}.bin','I'))
 candidate=BVHTree.FromPolygons(points,[tuple(ids[k:k+3]) for k in range(0,len(ids),3)],all_triangles=True)
 hits=0;maximum=0;removed_first=[]
 for k,ray in enumerate(frame['rays']):
  origin=Vector(ray[:3]);direction=Vector(ray[3:]);origin+=direction*frame['near']
  a=source.ray_cast(origin,direction,30000);b=candidate.ray_cast(origin,direction,30000)
  if (a[0] is None)!=(b[0] is None):failures.append([i,k,'hit mismatch']);continue
  if a[0] is None:continue
  hits+=1;err=abs(a[3]-b[3]);maximum=max(maximum,err)
  if a[2] not in retained:removed_first.append(k)
  if err>.001:failures.append([i,k,err])
 reports.append(dict(frame=i,rays=len(frame['rays']),hits=hits,maximumDepthDifference=maximum,removedFirstHitTriangles=removed_first))
result=dict(passed=not failures and all(not r['removedFirstHitTriangles'] for r in reports),totalRays=sum(r['rays'] for r in reports),frames=reports,failures=failures)
(W/'ray-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);assert result['passed']
