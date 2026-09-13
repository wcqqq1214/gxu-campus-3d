"""Source/decoded mesh audit; shares the closed-shell primitive with generation.

Callers select and label scene assets explicitly. This module does not import
models, mutate assets, choose scene layers, or write acceptance reports.
"""
import bpy, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from vegetation_layout import tree_rotation
from mesh_volumes import MeshVolumes

def snapshot(obj):
    obj.data.calc_loop_triangles()
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    faces=[tuple(t.vertices) for t in obj.data.loop_triangles]
    box=tuple(tuple(fn(v[i] for v in vertices) for i in range(3)) for fn in (min,max))
    return vertices,faces,box


def check_meshes(rows, buildings, templates):
    obstacles=[dict(name=name,box=box,bvh=BVHTree.FromPolygons(vs,ts,all_triangles=True),
                    vertices=vs,triangles=ts,volumes=None) for name,(vs,ts,box) in buildings]
    tree_volumes={(lod,typ):MeshVolumes(vs,ts) for lod,variants in templates.items() for typ,(vs,ts,_) in variants.items()}
    hits=[];tested=0
    for i,row in enumerate(rows):
        x,y,h,typ,z=row;scale=h/9;angle=tree_rotation(x,y);c,s=math.cos(angle),math.sin(angle)
        for lod,variants in templates.items():
            vs,ts,_=variants[typ]
            world=[Vector((x+scale*(c*v.x-s*v.y),y+scale*(s*v.x+c*v.y),z+scale*v.z)) for v in vs]
            lo=[min(v[k] for v in world) for k in range(3)];hi=[max(v[k] for v in world) for k in range(3)]
            nearby=[o for o in obstacles if all(lo[k]<=o['box'][1][k] and hi[k]>=o['box'][0][k] for k in range(3))]
            if not nearby:continue
            bvh=BVHTree.FromPolygons(world,ts,all_triangles=True)
            volumes=tree_volumes[lod,typ]
            points=[(x+scale*(c*v[0]-s*v[1]),y+scale*(s*v[0]+c*v[1]),z+scale*v[2]) for v in volumes.representatives]
            for other in nearby:
                tested+=1;pairs=bvh.overlap(other['bvh']);witness=None;kind='surface-intersection'
                if not pairs:
                    if other['volumes'] is None:other['volumes']=MeshVolumes(other['vertices'],other['triangles'])
                    witness=other['volumes'].witness_inside(points);kind='tree-component-inside-building'
                    if witness is None and volumes.shells:
                        local=(((c*(v[0]-x)+s*(v[1]-y))/scale,(-s*(v[0]-x)+c*(v[1]-y))/scale,(v[2]-z)/scale) for v in other['volumes'].representatives_in_bounds((lo,hi)))
                        witness=volumes.witness_inside(local);kind='building-component-inside-tree'
                        if witness is not None:
                            a,b,h=witness;witness=(x+scale*(c*a-s*b),y+scale*(s*a+c*b),z+scale*h)
                if pairs or witness is not None:
                    hits.append(dict(treeIndex=i,tree=row,treeLOD=lod,buildingMesh=other['name'],trianglePairs=len(pairs),collisionKind=kind,containmentWitness=witness))
    return dict(trees=len(rows),buildingMeshes=len(buildings),treeLODs=list(templates),testedPairs=tested,
                testedClosedBuildingComponents=sum(len(o['volumes'].shells) for o in obstacles if o['volumes']),
                testedOpenBuildingComponents=sum(o['volumes'].open_components for o in obstacles if o['volumes']),
                templateClosedComponents={lod:{str(typ):len(tree_volumes[lod,typ].shells) for typ in variants} for lod,variants in templates.items()},
                collisions=hits,passed=not hits)


