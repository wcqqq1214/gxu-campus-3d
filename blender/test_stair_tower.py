"""Actual generated treads, headroom and shared LOD at three world rotations."""
import bpy,sys,json,math,copy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from stair_tower import stair_tower_model
from geometry import MATERIALS
colors=['white','pink','stone','glass','dark'];C={n:i for i,n in enumerate(colors)};MATERIALS[:]=[bpy.data.materials.new(n) for n in colors]
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/880089960')
for rotation in [0,.63,math.pi/2]:
    sample=copy.deepcopy(b);s=sample['form']['stairTower'];s['origin']=[0,0];s['angle']=rotation;c=s['config'];m=stair_tower_model(sample,0,C);obj=m.object('stair-test',bpy.context.scene.collection);obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
    tree=BVHTree.FromPolygons([v.co for v in obj.data.vertices],[t.vertices for t in tris],all_triangles=True)
    def world(x,y,z):return Vector((x*math.cos(rotation)-y*math.sin(rotation),x*math.sin(rotation)+y*math.cos(rotation),z))
    for level in range(3):
        for lane in range(2):
            for i in range(10):
                x=(1 if lane==0 else -1)*(c['wellWidth']/2+c['flightWidth']/2);y=(1 if lane==0 else -1)*(c['landingCut']-2*c['landingCut']*(i+.5)/10);expected=c['baseHeight']+(level+lane*.5)*s['floorHeight']+(i+1)*s['floorHeight']/20
                hit,normal,_,_=tree.ray_cast(world(x,y,expected+.1),Vector((0,0,-1)),.2)
                assert hit is not None and abs(hit.z-expected)<1e-5 and normal.z>.99,('tread',rotation,level,lane,i,hit,normal)
                assert tree.ray_cast(world(x,y,expected+.02),Vector((0,0,1)),1.78)[0] is None,('headroom',level,lane,i)
    assert tree.ray_cast(world(0,0,1),Vector((0,0,1)),10)[0] is None,'central well filled'
    for start,direction,expected in [(13,-1,12.65),(11,1,12.4)]:
        hit=tree.ray_cast(world(0,0,start),Vector((0,0,direction)),3)[0]
        assert hit is not None and abs(hit.z-expected)<1e-5
    print('Passed rotation',rotation,'60 tread surfaces, headroom, open well and thin canopy',flush=True)
