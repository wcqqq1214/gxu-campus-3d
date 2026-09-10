"""Distinct architectural studies, using the reference catalogue and OSM footprints."""
import math
from geometry import Mesh
from south_gate import south_gate
from library import library
from international_residence import international_residence
from campus_gates import campus_gate
from time_gate import time_gate
from teaching_ten import teaching_ten

def facade(m,x,y,z,w,d,h,wall,glass,trim,floors=6,spacing=4,band=False):
    m.box(x,y,z+h/2,w,d,h,wall)
    for sy in [-1,1]:
        for f in range(floors):
            zz=z+(f+.55)*h/floors
            if band:m.box(x,y+sy*(d/2+.08),zz,w-2,.12,h/floors*.61,glass)
            else:
                count=max(1,int(w/spacing))
                for i in range(count):m.box(x-w/2+(i+.5)*w/count,y+sy*(d/2+.08),zz,w/count*.56,.14,h/floors*.55,glass)
            m.box(x,y+sy*(d/2+.20),z+(f+1)*h/floors,w+.5,.38,.2,trim)
    for sx in [-1,1]:
        for f in range(floors):
            count=max(1,int(d/spacing))
            for i in range(count):m.box(x+sx*(w/2+.08),y-d/2+(i+.5)*d/count,z+(f+.55)*h/floors,.14,d/count*.52,h/floors*.55,glass)
    m.box(x,y,z+h+.3,w+1.5,d+1.5,.6,trim)
def steps(m,x,y,z,width,depth,height,mat,n=12):
    for i in range(n):m.box(x,y+depth*i/n/2,z+height*(i+.5)/n,width,depth*(1-i/n),height/n,mat)
def landmark(l,b,z,C,detail=True):
    m=Mesh();x,y=l['center'];xmin,ymin,xmax,ymax=l['bounds'];w=xmax-xmin;d=ymax-ymin;x=(xmin+xmax)/2;y=(ymin+ymax)/2;h=l['height']
    stone,white,glass,dark,roof,wood=C['stone'],C['white'],C['glass'],C['dark'],C['slate'],C['wood']
    k=l['id']
    if k=='teaching-ten':return teaching_ten(l,b,z,C,detail)
    if l.get('placeKind')=='sculpture':return time_gate(l,z,C,detail)
    if l.get('placeKind')=='gate':return campus_gate(l,z,C,detail)
    if k=='south-gate':
        return south_gate(x,y,z,C,detail,footprint_width=w,footprint_depth=d)
    elif k=='huixue':
        # Keep the mapped E/W and N/S extents after rotating the south-facing study east.
        w,d=d,w
        m.box(x,y,z+10,w*.94,d*.88,20,stone)
        m.box(x,y+d*.2,z+22,w*.9,d*.44,6,dark)
        m.roof(x,y+d*.08,z+23,w*.88,d*.82,3.5,roof)
        front=y-d*.45
        m.box(x,front-.25,z+10,w*.36,.6,16,dark)
        m.box(x,front-.7,z+7,w*.3,.4,10,wood)
        m.roof(x,front+7,z+21,w*.47,23,4,roof)
        m.box(x,front-4.6,z+21,w*.47,1.5,.65,C['red'])
        for i in [-1,1]:
            m.box(x+i*w*.245,front-.2,z+11,5,3,22,stone)
            for j in range(5):m.box(x+i*(w*.30+j*w*.033),front-.6,z+11,1.35,1.2,19,white)
        for sx in [-1,1]:
            for j in range(13):
                m.box(x+sx*w*.476,y-d*.4+j*d*.065,z+10,.8,1.0,19,white)
                m.box(x+sx*w*.477,y-d*.37+j*d*.065,z+10,.15,1.1,14,glass)
        steps(m,x,front-8,z,w*.4,12,2.1,stone)
        m.rotate_z(x,y,math.pi/2)
    elif k=='auditorium':
        m.box(x,y,z+5.4,w*.9,d*.93,10.8,white)
        m.roof(x,y,z+10.8,w*.98,d,3,C['paleRoof'])
        front=y-d*.49
        m.box(x,front,z+11.3,w,6,.8,stone)
        m.face([(x-w*.38,front-3,z+11.7),(x+w*.38,front-3,z+11.7),(x,front-3,z+15)],white)
        m.line((x-w*.41,front-3,z+11.7),(x,front-3,z+15.3),.20,stone)
        m.line((x,front-3,z+15.3),(x+w*.41,front-3,z+11.7),.20,stone)
        for i in range(6):
            xx=x+(i-2.5)*w*.13;m.cylinder(xx,front-2,z+6,.56,10,white,20);m.cylinder(xx,front-2,z+10.8,.82,.5,stone,20);m.cylinder(xx,front-2,z+1,.8,.4,stone,20)
            m.box(xx,front+.08,z+2,2,.15,2.5,wood)
            for f in [1,2]:m.box(xx,front+.08,z+2+f*3,1.8,.15,2.2,glass)
        for sx in [-1,1]:
            for j in range(8):
                for f in range(3):m.box(x+sx*w*.455,y-d*.39+j*d*.106,z+1.8+3*f,.15,1.7,2,glass)
                m.box(x+sx*w*.465,y-d*.43+j*d*.12,z+5.5,.4,.5,10,stone)
        steps(m,x,front-6,z,w*.94,9,1.2,stone)
    elif k=='library':
        return library(l,b,z,C,detail)
    elif k=='international-residence':
        return international_residence(l,b,z,C,detail)
    elif k=='student-center':
        # Use the mapped curved exterior and courtyard instead of a substitute rectangle.
        for f in range(5):
            m.extrude(b['polygons'],b['roofTriangles'],z+f*h/5,h/5,glass,white)
            for poly in b['polygons']:
                for ring in poly:
                    for a,bb in zip(ring,ring[1:]):
                        dx=bb[0]-a[0];dy=bb[1]-a[1];ln=math.hypot(dx,dy)
                        m.box((a[0]+bb[0])/2,(a[1]+bb[1])/2,z+(f+1)*h/5,ln+.2,.75,.8,white,math.atan2(dy,dx))
                        if detail:
                            for i in range(max(1,int(ln/2))):
                                t=(i+.5)/max(1,int(ln/2));m.box(a[0]+dx*t,a[1]+dy*t,z+(f+.5)*h/5,.12,.12,h/5-.5,dark)
        m.box(x,ymin-2,z+2.5,12,5,5,glass);m.box(x,ymin-3,z+5.2,16,8,.4,white)
    elif k=='stadium':
        # Official 2021 video, 00:07 and 00:12: broad shallow roof, vertical piers, horizontal louvers.
        # The mapped footprint has a narrow north wing. Using the full bounding
        # rectangle filled that concavity and pushed the east annex into Nongyuan Road.
        ring=b['polygons'][0][0][:-1]
        winding=sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(ring,ring[1:]+ring[:1]))
        reflex=[]
        for i,p in enumerate(ring):
            a=ring[i-1];c=ring[(i+1)%len(ring)]
            cross=(p[0]-a[0])*(c[1]-p[1])-(p[1]-a[1])*(c[0]-p[0])
            if cross*winding<0:reflex.append(p)
        notch=max(reflex,key=lambda p:p[0]);split=notch[1]
        north=[p for p in ring if p[1]>split+1]
        wing_left=min(p[0] for p in north);wing_right=max(p[0] for p in north)
        mainw=w*.9;maind=(split-ymin)*.93;hh=h*.83;xx=x;y=(ymin+split)/2
        facade(m,xx,y,z,mainw,maind,hh,stone,glass,white,2,5,True)
        m.roof(xx,y,z+hh+1.4,mainw+8,maind+8,1.9,C['paleRoof'])
        for sy in [-1,1]:
            front=y+sy*(maind/2+.3)
            for i in range(9):m.box(xx+(i-4)*mainw*.108,front,z+hh*.47,1.8,2.0,hh*.94,stone)
            for j in range(5):m.box(xx,front+sy*.8,z+hh*.66+j*.85,mainw-5,.35,.22,C['metal'])
            m.box(xx,front,z+hh+1.1,mainw+8,4,1.1,dark)
        facade(m,(wing_left+wing_right)/2,(split+ymax)/2,z,(wing_right-wing_left)*.93,(ymax-split)*.96,h*.48,stone,glass,white,2,4,True)
        for row in range(5):
            for col in range(6):
                sx=xx+(col-2.5)*mainw*.115;sy=y+(row-2)*maind*.14
                m.box(sx,sy,z+hh+3.1,2.3,2.3,.7,white)
        steps(m,xx,ymin-3,z,mainw*.65,8,1.2,stone)
    elif k=='laboratory':
        # The central through-opening on the campus axis is left genuinely open.
        ww=w*.35;gap=w*.22
        for sx in [-1,1]:facade(m,x+sx*(gap/2+ww/2),y,z,ww,d*.8,h*.76,stone,glass,white,7,4)
        facade(m,x,y,z+h*.48,w*.94,d*.70,h*.45,stone,glass,white,4,4)
        m.box(x,y,z+h,w*.76,d*.84,1.1,white)
        for i in [-3,-2,2,3]:m.box(x+i*w*.08,y-d*.45,z+h*.26,1.3,1.8,h*.52,stone)
        m.box(x,y-d*.45,z+h*.52,w*.85,3,.8,white)
    elif k=='teaching-six':
        m.extrude(b['polygons'],b['roofTriangles'],z,h,stone,white)
        for poly in b['polygons']:
            for ring in poly:
                for a,bb in zip(ring,ring[1:]):
                    dx=bb[0]-a[0];dy=bb[1]-a[1];ln=math.hypot(dx,dy);angle=math.atan2(dy,dx)
                    if ln<2:continue
                    count=max(1,int(ln/3.8))
                    for floor in range(6):
                        for i in range(count):
                            t=(i+.5)/count;xx=a[0]+dx*t;yy=a[1]+dy*t
                            m.box(xx,yy,z+(floor+.54)*h/6,ln/count*.68,.32,h/6*.68,glass,angle)
                            if detail:m.box(xx,yy,z+(floor+.54)*h/6,.07,.38,h/6*.7,white,angle)
                    m.box((a[0]+bb[0])/2,(a[1]+bb[1])/2,z+h+.6,ln+2,2,.5,white,angle)
        edges=[(a,bb) for poly in b['polygons'] for a,bb in zip(poly[0],poly[0][1:]) if math.dist(a,bb)>w*.4]
        a,bb=min(edges,key=lambda pair:(pair[0][1]+pair[1][1])/2)
        dx=bb[0]-a[0];dy=bb[1]-a[1];ln=math.hypot(dx,dy);theta=math.atan2(dy,dx)
        frontx=(a[0]+bb[0])/2;fronty=(a[1]+bb[1])/2
        for i in range(max(2,int(ln/7))):
            t=(i+.5)/max(2,int(ln/7));m.box(a[0]+dx*t,a[1]+dy*t-.35,z+h*.5,1.1,1.4,h,white,theta)
        m.box(frontx,fronty-3,z+5,ln*.42,8,.65,C['wood'],theta)
        steps(m,frontx,fronty-6,z,ln*.40,10,1.5,stone)
    elif k=='teaching-two':
        facade(m,x,y,z,w,d,h,C['pink'],glass,white,7,3.8)
        m.box(x,ymin-1.6,z+h*.50,9,3,h,stone)
        m.box(x,ymin-3,z+4.5,15,7,.5,white)
        for sx in [-1,1]:m.box(x+sx*(w*.4),y,z+h+1,6,d*.8,2.2,stone)
        steps(m,x,ymin-4,z,14,6,.8,stone)
    elif k=='computer':
        facade(m,x,y,z,w,d,h,white,glass,stone,10,3.6)
        m.box(x+w*.44,y,z+h/2,w*.18,d+1,h,C['pink'])
        m.box(x-w*.05,ymin-.8,z+h*.52,w*.14,.35,h*.91,glass)
        for i in range(8):m.box(x-w*.4+i*w*.05,ymin-.8,z+h*.48,.9,1.0,h*.79,stone)
        m.box(x,y,z+h+1.8,w+5,d+3,.55,white)
        m.box(x+w*.18,ymin-.6,z+h/2,w*.15,1.4,h+2,stone)
        m.box(x-w*.35,ymax-d*.2,z+h+1,w*.26,d*.28,3,stone)
        m.box(x,ymin-2,z+4.6,12,7,.55,white)
        for sx in [-1,1]:m.cylinder(x+sx*4.5,ymin-4,z+2.2,.4,4.4,stone)
        steps(m,x,ymin-4,z,12,6,.7,stone)
    return m
