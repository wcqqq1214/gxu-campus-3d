import copy,json,math,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from mathutils.geometry import intersect_ray_tri
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from generic_buildings import ordinary_building
from gallery_checks import check_galleries
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129515')
C={name:i for i,name in enumerate(['stone','pink','white','glass','dark','shadeGlass','paleRoof','red'])}
for angle in (0,math.pi/2,math.pi*.173):
    current=copy.deepcopy(b);c=math.cos(angle);s=math.sin(angle)
    def rotate(p):return [p[0]*c-p[1]*s,p[0]*s+p[1]*c]+list(p[2:])
    current['polygons']=[[[rotate(p) for p in ring] for ring in poly] for poly in current['polygons']]
    for part in current['form']['parts']:
        part['polygons']=[[[rotate(p) for p in ring] for ring in poly] for poly in part['polygons']]
        if 'parapetEdges' in part:part['parapetEdges']=[[rotate(p) for p in edge] for edge in part['parapetEdges']]
        if 'geometry' in part['roof']:part['roof']['geometry']['vertices']=[rotate(p) for p in part['roof']['geometry']['vertices']]
    current['form']['entrances']=[]
    for f in current['form']['facades']:
        for key in ('start','end','normal'):f[key]=rotate(f[key])
    meshes=[]
    for detail in (False,True):
        mesh=ordinary_building(current,0,C,detail);meshes.append(mesh)
        check_galleries(current,[BVHTree.FromPolygons(mesh.v,mesh.f)],1e-4)
        # The slab's white front face must not overlap the lower stone wall.
        for f in current['form']['facades']:
            if 'attachedGallery' not in f:continue
            p=f['attachedGallery'];a=Vector((*f['start'],0));edge=Vector((*f['end'],0))-a;n=Vector((*f['normal'],0))
            origin=a+edge*.37+n*(p['depth']+.3)+Vector((0,0,p['floorHeight']-p['slabThickness']/2))
            hits=0
            for face in mesh.f:
                vertices=[Vector(mesh.v[k]) for k in face]
                for i in range(1,len(vertices)-1):
                    h=intersect_ray_tri(vertices[0],vertices[i],vertices[i+1],-n,origin,True)
                    if h is not None and abs((h-origin).length-.3)<1e-4:
                        hits+=1;break
            assert hits==1,('coplanar wall/slab front',angle,f['edge'],hits)
    def body(mesh):
        _,start,end=next(p for p in mesh.parts if p[0]=='01_主体轮廓');return mesh.v[start:end]
    assert body(meshes[0])==body(meshes[1]),'attached gallery changes with LOD'
print('Passed two attached galleries: voids, floor, sloping soffit, lower wall, balusters and openings at 0/90/31.14 degrees in both LODs')
