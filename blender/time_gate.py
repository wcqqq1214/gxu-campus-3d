"""Photograph-informed study of 时光之门; proportions and folds are estimated.

2025 official close-up: crumpled polished metal, three feet, low plaque.
2023 overall photograph: joined arch-like shoulders and small top projection.
No external photographs or scan geometry are embedded in these meshes.
"""
import bpy,math
from functools import lru_cache
from mathutils import Vector,noise
from geometry import Mesh
from south_gate import inscription

@lru_cache(maxsize=2)
def body(detail,metal):
    m=Mesh()
    # Three asymmetric upright feet, spaced around an open centre.
    for k,(x,y) in enumerate([(-4.65,-2.3),(4.65,-2.3),(.25,3.5)]):
        n=28;rings=[]
        for j in range(27):
            t=j/26;z=.08+15.4*t
            cx=x*(1-.08*t)+.32*math.sin(t*math.pi*3+k)
            cy=y*(1-.1*t)+.22*math.sin(t*math.pi*2+k)
            radius=1.9+.22*math.cos(t*math.pi*4+k)+.45*t*t
            rings.append([(cx+radius*math.cos(i*math.tau/n),cy+radius*(.87 if k<2 else 1)*math.sin(i*math.tau/n),z) for i in range(n)])
        m.face(rings[0][::-1],metal);m.face(rings[-1],metal)
        for a,b in zip(rings,rings[1:]):
            for i in range(n):q=(i+1)%n;m.face([a[i],a[q],b[q],b[i]],metal)
    m.ellipsoid(0,.15,15.3,6.85,5.5,2.8,metal,48,26)
    m.ellipsoid(.25,.7,18.9,1.37,1.35,1.6,metal,28,20)
    mesh=bpy.data.meshes.new('时光之门融合临时网格');mesh.from_pydata(m.v,[],m.f);mesh.update()
    obj=bpy.data.objects.new('时光之门融合临时对象',mesh);bpy.context.scene.collection.objects.link(obj)
    old=bpy.context.view_layer.objects.active;bpy.context.view_layer.objects.active=obj
    remesh=obj.modifiers.new('三足与顶部连续融合','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.22 if detail else .8;remesh.use_smooth_shade=False
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=obj.modifiers.new('消除体量接头','SMOOTH');smooth.factor=1;smooth.iterations=3
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    # Continuous spatial noise produces folded reflections; the seed is fixed
    # through deterministic coordinates, with finer relief only in the near LOD.
    normals=[v.normal.copy() for v in obj.data.vertices]
    for v,normal in zip(obj.data.vertices,normals):
        p=v.co.copy();floor_weight=min(1,max(0,p.z/.6))
        broad=noise.noise_vector(p*.92+Vector((9,17,3))).x
        fine=noise.noise_vector(p*3.6+Vector((4,2,8))).y
        fold=(broad*.36+fine*(.12 if detail else .035))*floor_weight
        v.co+=normal*fold
        v.co.z=max(.03,v.co.z)
    dec=obj.modifiers.new('分级简化','DECIMATE');dec.ratio=.6 if detail else .55
    bpy.ops.object.modifier_apply(modifier=dec.name)
    result=Mesh();result.v=[tuple(v.co) for v in obj.data.vertices]
    result.f=[tuple(p.vertices) for p in obj.data.polygons];result.m=[metal]*len(result.f)
    used=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(used)
    bpy.context.view_layer.objects.active=old
    return result

def time_gate(l,z,C,detail=True):
    m=Mesh();x,y=l['center'];floor=l['islandElevation'];angle=math.radians(180-l['frontBearing'])
    sculpture=Mesh();sculpture.extend(body(detail,C['timeSilver']));sculpture.rotate_z(0,0,angle)
    sculpture.v=[(a+x,b+y,c+floor) for a,b,c in sculpture.v]
    m.add_part('三足、相连拱顶与顶部突起 · 银色褶皱（比例估算）',sculpture)
    island=Mesh();n=64;r=l['radius']
    island.cylinder(x,y,floor-.08,r-.9,.12,C['grass'],n)
    # Narrow ring on the existing mapped plaza; the outside drapes to coarse DEM.
    for i in range(n):
        j=(i+1)%n;a=i*math.tau/n;b=j*math.tau/n
        inner=[(x+(r-.9)*math.cos(t),y+(r-.9)*math.sin(t),floor-.015) for t in [a,b]]
        outer=[(x+r*math.cos(t),y+r*math.sin(t),floor-.025) for t in [a,b]]
        island.face([inner[0],outer[0],outer[1],inner[1]],C['path'])
        island.face([outer[0],l['groundRing'][i],l['groundRing'][j],outer[1]],C['path'])
    m.add_part('中央草地岛与环形铺装 · 范围估算',island)
    plaque=Mesh();plaque.box(0,-10.2,floor+.16,1.8,1.45,.32,C['dark'])
    # A readable model label, not a fabricated transcription of the real plaque.
    if detail:
        label=inscription('时光之门',0,-.02,0,1.4,.32,C['timeLetter'],True)
        label.v=[(a,-10.2+c,floor+.33-b) for a,b,c in label.v];plaque.extend(label)
    plaque.rotate_z(0,0,angle);plaque.v=[(a+x,b+y,c) for a,b,c in plaque.v]
    m.add_part('低矮铭牌 · 文字与尺寸示意',plaque)
    lamps=Mesh()
    for k in range(3):
        a=angle+math.radians(30+120*k);px=x+8.3*math.cos(a);py=y+8.3*math.sin(a)
        lamps.box(px,py,floor+.06,.4,.4,.12,C['dark'])
        lamps.box(px,py,floor+.13,.3,.3,.025,C['timeLight'])
    m.add_part('地面投光灯 · 位置示意',lamps)
    return m
