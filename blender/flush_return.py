"""Shared side glazing, stone piers and connected canopy; no inferred side door."""
import math


def add_flush_return(mesh,entry,z,C):
    p=entry['flushEntrance'];r=p['returnGlazing'];a=r['corner'];u=r['tangent'];n=r['normal']
    angle=math.atan2(u[1],u[0]);width=r['depth']-.2;bay=width/r['bays']
    floor,top=p['floorHeight'],p['glazingHeight'];pw,pd,fw=r['pierWidth'],r['pierDepth'],p['frameWidth']
    def box(distance,depth,bottom,w,d,h,material):
        mesh.box(a[0]+u[0]*distance+n[0]*depth,a[1]+u[1]*distance+n[1]*depth,
                 z+bottom+h/2,w,d,h,C[material],angle)
    for i in range(r['bays']):
        distance=.1+(i+.5)*bay
        box(distance,.055,floor,bay-pw,.05,top-floor,'glass')
        box(distance,.095,floor,fw,.09,top-floor,'white')
    for i in range(r['bays']+1):
        distance=.1+pw/2 if i==0 else r['depth']-.1-pw/2 if i==r['bays'] else .1+i*bay
        box(distance,pd/2-.03,floor,pw,pd,top-floor,'stone')
    box(r['depth']/2,pd/2-.03,p['splitHeight']-r['beamHeight']/2,width,pd,r['beamHeight'],'stone')
    box(r['depth']/2,.095,top-fw,width,.09,fw,'white')
    geometry=r['canopyGeometry'];thickness=p['canopy']['thickness']
    mesh.extrude(geometry['polygons'],geometry['triangles'],z+top,thickness,C['stone'],C['stone'])
    for poly,indices in zip(geometry['polygons'],geometry['triangles']):
        vertices=[p for ring in poly for p in ring[:-1]]
        for i in range(0,len(indices),3):
            mesh.face([(vertices[k][0],vertices[k][1],z+top) for k in reversed(indices[i:i+3])],C['stone'])


def return_blocks_window(entry,x,y,nx,ny,bottom,top,width):
    p=entry['flushEntrance'];r=p.get('returnGlazing')
    if not r:return False
    a=r['corner'];n=r['normal'];u=r['tangent'];dx,dy=x-a[0],y-a[1]
    distance=dx*u[0]+dy*u[1]
    return (nx*n[0]+ny*n[1]>.999 and abs(dx*n[0]+dy*n[1])<.3
            and distance+(width+.3)/2>.1 and distance-(width+.3)/2<r['depth']-.1
            and bottom<p['glazingHeight'] and top>p['floorHeight'])
