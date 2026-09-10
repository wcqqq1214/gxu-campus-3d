"""六教: three mapped courtyards, four entrances and an open north–south ground floor.

Portal locations follow the university's 2025 entrance diagram. Dimensions,
back/side facade details and thresholds are estimates, not a measured survey.
"""
import math
from geometry import Mesh

def teaching_six(l,b,z,C,detail=True):
    e=b['architecture'];m=Mesh();wall=C['stone'];trim=C['white'];glass=C['glass'];dark=C['dark'];h=b['height']
    for i,p in enumerate(e['parts']):
        part=Mesh();part.extrude(p['polygons'],p['triangles'],z+(5.2 if i else -.3),p['height']+(.3 if not i else 0),wall,trim)
        m.add_part(p['name'],part)
    ceiling=Mesh();cp=e['passageCeilings']
    for poly,tri in zip(cp['polygons'],cp['triangles']):
        flat=[v for ring in poly for v in ring[:-1]]
        for i in range(0,len(tri),3):ceiling.face([(flat[k][0],flat[k][1],z+5.2) for k in reversed(tri[i:i+3])],trim)
    m.add_part('南北及侧门架空通道顶板',ceiling)
    facade=Mesh()
    for ri,ring in enumerate(b['polygons'][0]):
        # Work in the same local axes as the partitioned walls.
        ca,sa=math.cos(e['angle']),math.sin(e['angle']);ox,oy=e['origin']
        ring=[((x-ox)*ca+(y-oy)*sa,-(x-ox)*sa+(y-oy)*ca) for x,y in ring]
        area=sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(ring,ring[1:]));sign=(1 if area>0 else -1)*(1 if ri==0 else -1)
        for a,c in zip(ring,ring[1:]):
            dx,dy=c[0]-a[0],c[1]-a[1];length=math.hypot(dx,dy)
            if length<1:continue
            ux,uy=dx/length,dy/length;nx,ny=uy*sign,-ux*sign;theta=math.atan2(dy,dx);count=max(1,int(length/4.5))
            for f in range(6):
                wh=2.8 if f==0 else 1.9;zz=z+(2.8 if f==0 else 5.2+(f-.5)*(h-5.2)/5)
                for i in range(count):
                    t=(i+.5)/count;x=a[0]+dx*t;y=a[1]+dy*t;ww=length/count*.70
                    # No glass, frame or sill is allowed to seal any open portal.
                    if f==0 and (abs(x)<8 or (abs(x)>29 and abs(y)<6)):continue
                    x+=nx*.14;y+=ny*.14
                    if detail:
                        facade.box(x,y,zz,ww+.18,.16,wh+.18,trim,theta)
                        facade.box(x+nx*.11,y+ny*.11,zz,ww,.09,wh,glass,theta)
                        facade.box(x+nx*.18,y+ny*.18,zz,.06,.10,wh,trim,theta)
                    else:
                        pts=[(x-ux*ww/2,y-uy*ww/2,zz-wh/2),(x+ux*ww/2,y+uy*ww/2,zz-wh/2),(x+ux*ww/2,y+uy*ww/2,zz+wh/2),(x-ux*ww/2,y-uy*ww/2,zz+wh/2)]
                        facade.face(pts if sign>0 else pts[::-1],glass)
                if detail and f>0:facade.box((a[0]+c[0])/2+nx*.18,(a[1]+c[1])/2+ny*.18,zz-wh/2-.24,length,.5,.25,trim,theta)
            facade.box((a[0]+c[0])/2,(a[1]+c[1])/2,z+h+.35,length+.35,.8,.35,trim,theta)
            if ri==0 and detail:
                for i in range(count+1):
                    t=i/count;x=a[0]+dx*t;y=a[1]+dy*t
                    # Raised stone piers stop above the open ground floor.
                    facade.box(x+nx*.35,y+ny*.35,z+(h+5.2)/2,.65,.72,h-5.2,trim,theta)
    m.add_part('窗框、层间线脚与竖向石材立柱',facade)
    roof=Mesh()
    # Thin canopy along the perimeter, lifted on posts like the official photograph.
    for y in [-29.966,29.966]:
        roof.box(0,y,z+h+1.9,115,2.4,.28,C['wood'])
        for x in range(-54,55,9):roof.box(x,y,z+h+1,.28,.3,1.8,trim)
    m.add_part('平屋顶挑檐与架空顶层框架',roof)
    floor=Mesh();floor.box(0,0,z+.68,8,60,.16,C['path'])
    for sy in [-1,1]:floor.box(0,sy*22,z+.68,14,16,.16,C['path'])
    for sx in [-1,1]:floor.box(sx*46,0,z+.68,24,7,.16,C['path'])
    m.add_part('南北贯通地面与两侧入院铺装',floor)
    for ent in e['entrances']:
        part=Mesh();w=ent['width'];major=ent['id'] in ('south','north');cw=30 if major else 10
        # Open portals: do not insert a cosmetic door slab across the through passage.
        part.box(0,-1.5,z+4.85,cw,4,.35,trim)
        part.box(0,-1.52,z+5.08,cw+.6,4.5,.18,C['wood'])
        for x in ([-14,-8,8,14] if major else [-4.1,4.1]):
            part.box(x,-1,z+2.64,.85,.85,4.0,dark)
            if detail:part.box(x,-1,z+4.62,1.08,1.08,.22,trim)
        # Northern/western DEM rises up to 0.33 m above the building anchor.
        stair_base=.34 if ent['id'] in ('north','west') else 0
        for i in range(5):
            depth=4-i*.7;top=stair_base+(.76-stair_base)*(i+1)/5
            part.box(0,-depth/2,z+(top-.3)/2,w+.4,depth,top+.3,trim)
        if detail:
            for sx in [-1,1]:
                for i in range(5):
                    yy=-3.8+i*.7;hh=z+stair_base+(.76-stair_base)*(i+1)/5+.15
                    part.line((sx*(w/2+.45),yy,hh),(sx*(w/2+.45),yy,hh+.9),.035,C['metal'],6)
                part.line((sx*(w/2+.45),-3.8,z+stair_base+(.76-stair_base)/5+1.05),(sx*(w/2+.45),-1,z+1.81),.045,C['metal'],6)
        part.rotate_z(0,0,ent['angle']);ex,ey=ent['center'];part.v=[(x+ex,y+ey,zz) for x,y,zz in part.v]
        m.add_part({'south':'南门','north':'北门','west':'西侧门','east':'东侧门'}[ent['id']]+' · 开放门厅、雨棚、台阶',part)
    m.rotate_z(0,0,e['angle']);ox,oy=e['origin'];m.v=[(x+ox,y+oy,zz) for x,y,zz in m.v]
    return m
