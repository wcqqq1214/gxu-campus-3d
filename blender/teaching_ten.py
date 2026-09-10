"""第十教学楼: height-zoned mapped envelope with photograph-informed facades.

Official gallery shows a pale curved low block and tall rear classroom wing.
Partition heights, stairs, doors and unseen elevations remain estimates.
"""
import math
from geometry import Mesh
from south_gate import inscription

def teaching_ten(l,b,z,C,detail=True):
    m=Mesh();e=b['architecture'];wall=C['tenWall'];trim=C['tenTrim'];glass=C['tenGlass']
    for p in e['parts']:
        part=Mesh();part.extrude(p['polygons'],p['triangles'],z-.3,p['height']+.3,wall,C['paleRoof'])
        # Low parapets follow each real height partition, including rounded edges.
        if detail:
            for poly in p['polygons']:
                for ring in poly:
                    for a,c in zip(ring,ring[1:]):
                        d=math.dist(a,c)
                        if d>.1:part.box((a[0]+c[0])/2,(a[1]+c[1])/2,z+p['height']+.32,d,.22,.64,trim,math.atan2(c[1]-a[1],c[0]-a[0]))
        m.add_part(p['name']+' · 原轮廓裁剪',part)
    def height(x,y):
        if y>=26:return 26.4
        if -5<x<8 and 13<y<26:return 6.6
        if -12<x<12 and -11<y<13:return 13.2
        return 9.9
    facade=Mesh();ring=e['footprint'];sign=1 if sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(ring,ring[1:]))>0 else -1
    for a,c in zip(ring,ring[1:]):
        dx,dy=c[0]-a[0],c[1]-a[1];length=math.hypot(dx,dy)
        if length<.15:continue
        ux,uy=dx/length,dy/length;nx,ny=uy*sign,-ux*sign;theta=math.atan2(dy,dx)
        x,y=(a[0]+c[0])/2,(a[1]+c[1])/2;h=height(x,y);north=y>=26
        tower=north and ((abs(x)>14 and y<36.2) or (abs(x)>24 and y>42))
        outer=not north and math.hypot(x,y)>20
        # Blank fan-shaped auditorium walls alternate with recessed glazed seams.
        if length>=2 and not outer:
            count=max(1,int(length/(4.4 if north else 4.2)))
            for i in range(count):
                t=(i+.5)/count;xx=a[0]+dx*t+nx*.035;yy=a[1]+dy*t+ny*.035
                for f in range(round(h/3.3)):
                    if not north and yy < -16 and abs(xx) < 7 and f < 2:continue
                    zz=z+f*3.3+1.05;wh=.65 if tower else 1.8;ww=min(length/count*.66,3.2 if not tower else 4)
                    def pane(w,hg,base,mat,off):
                        cx,cy=xx+nx*off,yy+ny*off
                        points=[(cx-ux*w/2,cy-uy*w/2,base),(cx+ux*w/2,cy+uy*w/2,base),(cx+ux*w/2,cy+uy*w/2,base+hg),(cx-ux*w/2,cy-uy*w/2,base+hg)]
                        facade.face(points if sign>0 else points[::-1],mat)
                    pane(ww,wh,zz,glass,.025)
                    if detail:
                        for q in [-.5,0,.5]:facade.box(xx+ux*ww*q+nx*.07,yy+uy*ww*q+ny*.07,zz+wh/2,.07,.12,wh,trim,theta)
                        facade.box(xx+nx*.08,yy+ny*.08,zz,ww+.15,.2,.1,trim,theta)
                        facade.box(xx+nx*.08,yy+ny*.08,zz+wh,ww+.15,.18,.1,trim,theta)
                if north and not tower:
                    facade.box(xx-ux*length/count*.46+nx*.19,yy-uy*length/count*.46+ny*.19,z+h/2,.25,.42,h+.3,trim,theta)
        if detail:
            for f in range(1,round(h/3.3)+1):
                facade.box(x+nx*.06,y+ny*.06,z+f*3.3,length,.12,.1,trim,theta)
            if outer and length>3:
                facade.box(x+nx*.1,y+ny*.1,z+h/2,.32,.22,h,trim,theta)
    for f in range(8):facade.box(1,25.96,z+f*3.3+1.9,5,.10,.6,glass)
    m.add_part('窗列、圆弧楼梯间窄窗与竖向框架',facade)
    roof=Mesh()
    # Glazed clerestory rises above the lower radial wings.
    for sy in [-1,1]:
        yy=-11 if sy<0 else 13
        roof.box(0,yy+sy*.045,z+11.35,22.6,.10,2.05,glass)
        if detail:
            for i in range(10):roof.box(-11.2+i*2.5,yy+sy*.12,z+11.35,.11,.18,2.1,trim)
    if detail:
        for xx in [-12,12]:roof.box(xx,1,z+13.35,.5,24,.25,trim)
        # Modest rooftop vents, wholly inside the tall mapped wing.
        for xx in [-16,0,17]:
            roof.box(xx,41,z+26.65,2.2,2.4,.5,C['slate'])
            for i in range(4):roof.box(xx,40.3+i*.4,z+26.93,2,.08,.05,trim)
    m.add_part('中央采光窗、平屋顶与设备构件',roof)
    entry=Mesh();xx,yy=e['entrance']
    # Estimated south approach stays within the mapped front recess.
    entry.box(xx,yy-.04,z+2.05,7.8,.16,3.0,glass)
    for x in [-4,0,4]:entry.box(x,yy-.14,z+2.1,.22,.28,3.4,trim)
    entry.box(0,yy-.65,z+3.95,10,1.7,.28,trim)
    for i in range(5):
        d=3.9-i*.64;entry.box(0,yy-d/2+.2,z+.07+i*.14,9.5,d,.14,trim)
    entry.box(0,yy-.10,z+4.6,9,.22,1.05,trim)
    if detail:
        name=inscription('第十教学楼',0,yy-.23,z+4.6,7,.72,C['dark'],False);entry.extend(name)
        for side in [-1,1]:
            for i in range(5):
                y=yy-3.5+i*.68;hh=z+.35+i*.12
                entry.line((side*4.65,y,hh),(side*4.65,y,hh+.9),.035,C['metal'],6)
            entry.line((side*4.65,yy-3.5,z+1.25),(side*4.65,yy-.78,z+1.73),.045,C['metal'],6)
    m.add_part('南侧入口、楼名、雨棚与台阶 · 细节估算',entry)
    m.rotate_z(0,0,e['angle']);ox,oy=e['origin'];m.v=[(x+ox,y+oy,zz) for x,y,zz in m.v]
    return m
