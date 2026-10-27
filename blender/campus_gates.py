"""Three independent gate studies. All dimensions are estimates, not surveys.

East: 2018 inauguration photo, later undated street view. West: 2021 outside /
inside gate video and 2025 entrance footage; the undated thumbnail is secondary.
New east: November 2025 photo and September 2026 route footage.
Local facade faces -Y; rotation is derived from the catalogue compass bearing.
"""
import math
from geometry import Mesh
from south_gate import inscription
from new_east_gate import new_east_gate


def arch(m, x, half, spring, rise, depth, top, C, detail):
    """Segmented solid spandrel with a genuinely empty elliptical opening."""
    n=40 if detail else 12
    points=[(x-half*math.cos(i*math.pi/n),spring+rise*math.sin(i*math.pi/n)) for i in range(n+1)]
    for (a,za),(b,zb) in zip(points,points[1:]):
        for sy in [-1,1]:
            yy=sy*depth/2
            m.face([(a,yy,za),(b,yy,zb),(b,yy,top),(a,yy,top)],C['gateStone'])
        m.face([(a,-depth/2,za),(a,depth/2,za),(b,depth/2,zb),(b,-depth/2,zb)],C['gateTrim'])
    m.box(x,0,top+.05,half*2,depth,.1,C['gateStone'])
    for sy in [-1,1]:
        for band,thick in [(0,.13),(.24,.11),(.42,.09)] if detail else [(0,.15)]:
            for i in range(n):
                a=i*math.pi/n;b=(i+1)*math.pi/n
                def p(t,r,h):return (x-r*math.cos(t),sy*(depth/2+.06+band*.08),spring+h*math.sin(t))
                m.face([p(a,half+band,rise+band),p(b,half+band,rise+band),
                        p(b,half+band+thick,rise+band+thick),p(a,half+band+thick,rise+band+thick)],C['gateTrim'])


def east_gate(C,detail):
    m=Mesh();stone=C['gateStone'];trim=C['gateTrim']
    for i,x in enumerate([-16,-8,8,16]):
        p=Mesh();p.box(x,0,.25,2.8,3.6,.5,trim);p.box(x,0,.7,2.5,3.3,.4,stone)
        p.box(x,0,4.9,2.2,3.0,8.0,stone)
        for z,w,d,h in [(1.2,2.5,3.3,.25),(7.6,2.45,3.3,.28),(8.7,2.9,3.7,.35)]:p.box(x,0,z,w,d,h,trim)
        if detail:
            for sy in [-1,1]:
                for j in range(8):
                    p.box(x+(j-3.5)*.245,sy*1.515,4.4,.08,.05,5.85,C['gateJoint'])
                # Three rows of leaf-like stone capitals; a relief interpretation.
                for row in range(3):
                    for j in range(5):
                        xx=x+(j-2)*.47+(row%2)*.10;zz=7.93+row*.22
                        p.ellipsoid(xx,sy*1.67,zz,.24,.19,.16,trim,8,4)
            for sy in [-1,1]:
                for j in range(12):p.box(x,sy*1.508,1.6+j*.52,2.14,.017,.013,C['gateJoint'])
        m.add_part(f'01_石柱_{i+1}',p)
    for i,(x,r,s,h) in enumerate([(0,6.9,6.15,2.05),(-12,2.9,4.55,2.65),(12,2.9,4.55,2.65)]):
        p=Mesh();arch(p,x,r,s,h,3,8.9,C,detail);m.add_part(f'02_贯通拱洞_{i+1}',p)
    p=Mesh()
    for z,w,d,h in [(9.0,34.8,3.75,.35),(9.85,34.4,3.4,1.5),(10.66,35,3.8,.18),(10.85,35,3.9,.20)]:p.box(0,0,z,w,d,h,stone if h>1 else trim)
    p.box(0,-1.72,9.88,10,.10,1.38,trim)
    m.add_part('03_通长檐口与校名嵌板',p)
    p=Mesh()
    for sy in [-1,1]:
        for x in [-15,-12,-9,-6,6,9,12,15]:
            yy=sy*1.73
            for a in range(4):
                t=a*math.pi/2;p.line((x+.17*math.cos(t),yy,9.92+.17*math.sin(t)),(x+.17*math.cos(t+math.pi/2),yy,9.92+.17*math.sin(t+math.pi/2)),.045,trim,4)
            if detail:
                for t in [0,math.pi/2,math.pi,math.pi*1.5]:p.ellipsoid(x+.19*math.cos(t),yy,9.92+.19*math.sin(t),.11,.045,.11,trim,8,4)
        if detail:
            for i in range(112):p.box((i-55.5)*.30,sy*1.83,9.22,.14,.12,.16,trim)
    m.add_part('04_檐下齿饰与菱花浮雕',p)
    if detail:m.add_part('05_红色立体校名',inscription('广西大学',0,-1.79,9.9,8.5,1.1,C['gateRed'],True))
    p=Mesh();booth(p,-7,3.1,1.45,2.0,C,detail);m.add_part('06_内侧值守岗亭',p)
    return m


def booth(m,x,y,w,d,C,detail):
    """Recessed glazing, individual frames, door and overhanging metal roof."""
    m.box(x,y,.15,w+.22,d+.22,.30,C['gateTrim'])
    m.box(x,y,1.8,w,d,3.3,C['white'])
    for sy in [-1,1]:
        m.box(x,y+sy*(d/2+.025),2.05,w-.3,.07,1.55,C['glass'])
        for zz in [1.25,2.85]:m.box(x,y+sy*(d/2+.08),zz,w-.18,.10,.08,C['metal'])
        for xx in [-w/2+.10,0,w/2-.10]:m.box(x+xx,y+sy*(d/2+.08),2.05,.06,.10,1.68,C['metal'])
    for sx in [-1,1]:
        m.box(x+sx*(w/2+.025),y,2.05,.07,d-.3,1.55,C['glass'])
        for yy in [-d/2+.10,0,d/2-.10]:m.box(x+sx*(w/2+.08),y+yy,2.05,.10,.06,1.68,C['metal'])
    m.box(x,y,3.50,w+.65,d+.65,.18,C['metal'])
    m.box(x,y,3.64,w+.50,d+.50,.10,C['white'])
    if detail:
        m.box(x+w/2+.085,y-.48,1.52,.08,.86,2.65,C['dark'])
        m.box(x+w/2+.13,y-.48,1.70,.035,.70,1.92,C['glass'])
        m.line((x+w/2+.17,y-.72,1.2),(x+w/2+.17,y-.72,1.65),.025,C['metal'])
        for j in range(5):m.box(x,y-d/2-.045,.43+j*.12,w-.2,.045,.035,C['gateJoint'])
        for sy in [-1,1]:m.box(x,y+sy*(d/2+.2),3.39,w*.65,.10,.05,C['white'])


def railing(m,x,y,length,C,detail):
    for xx in [-length/2,length/2]:m.cylinder(x+xx,y,.65,.055,1.3,C['metal'],8)
    for z in [.35,1.18]:m.line((x-length/2,y,z),(x+length/2,y,z),.04,C['metal'],6)
    if detail:
        for j in range(int(length/.28)):
            xx=x-length/2+(j+.5)*.28;m.line((xx,y,.35),(xx,y,1.18),.022,C['metal'],6)


def barrier(m,x,y,C,detail,sign=1):
    m.box(x,y,.55,.35,.45,1.1,C['white']);m.box(x,y,1.16,.39,.48,.12,C['dark'])
    # Raised arm keeps the vehicle entrance open in the display model.
    a=(x,y,1.15);b=(x+sign*.7,y,4.0);m.line(a,b,.045,C['white'],6)
    if detail:
        for j in range(5):
            t=j/5;m.line((x+sign*.7*t,y,1.15+2.85*t),(x+sign*.7*(t+.09),y,1.15+2.85*(t+.09)),.047,C['gateRed'],6)


def west_gate(C,detail):
    # 2021 video 7047681296730082572, 26-31s: outside and inside views.
    # The undated thumbnail is not enough to locate its red poles on the gate.
    # Preserve an open lane between the north guardhouse and south name wall.
    from south_gate import prism
    m=Mesh();p=Mesh()
    # Recessed, full-height glazed guardhouse, with a broad concrete canopy.
    p.box(-7.15,1.15,.14,5.6,3.7,.28,C['gateTrim'])
    p.box(-7.15,1.15,1.85,5.25,3.35,3.42,C['glass'])
    for sy in (-1,1):
        yy=1.15+sy*1.70
        for xx in [-9.7,-8.85,-8.0,-7.15,-6.30,-5.45,-4.60]:
            p.box(xx,yy,1.85,.065,.08,3.42,C['white'])
        for zz in (.22,2.65,3.52):
            p.box(-7.15,yy,zz,5.25,.08,.065,C['white'])
    for sx in (-1,1):
        xx=-7.15+sx*2.66
        for yy in (-.50,.60,1.70,2.80):p.box(xx,yy,1.85,.08,.065,3.42,C['white'])
    p.box(-7.15,1.15,3.65,5.65,3.75,.25,C['paleRoof'])
    # Flared edge pier and two shallow staggered slabs; sizes are estimates.
    prism(p,[(-10.55,.10),(-9.55,.10),(-9.30,3.75),(-8.65,4.60),(-10.55,4.60)],.30,3.90,C['paleRoof'])
    prism(p,[(-10.60,4.55),(-4.05,4.72),(-4.05,5.05),(-10.60,5.18)],.20,4.40,C['paleRoof'])
    prism(p,[(-9.95,5.15),(-5.10,5.15),(-5.10,5.48),(-9.95,5.48)],.45,3.80,C['paleRoof'])
    m.add_part('01_玻璃门卫室与错层厚檐_视频比例估算',p)
    p=Mesh()
    # Slanted pale name wall is visible at 26-27s; no invented rear text.
    prism(p,[(7.65,.10),(10.65,.10),(10.65,6.40),(8.85,6.05)],-1.55,.70,C['white'])
    prism(p,[(7.65,.10),(9.35,.10),(9.35,4.78),(8.58,4.93)],-1.94,.08,C['paleRoof'])
    for char,z in zip('广西大学',(4.50,3.55,2.60,1.65)):
        p.extend(inscription(char,8.65,-2.01,z,.70,.72,C['wood'],detail))
    m.add_part('02_斜边竖向校名墙_背面未证实',p)
    p=Mesh();barrier(p,-3.50,.80,C,detail,-1);barrier(p,3.50,.80,C,detail)
    m.add_part('03_开放车行道闸',p)
    p=Mesh()
    # Photo shows long lane dividers; keep vehicle and pedestrian corridors open.
    for x in (4.70,6.10,7.45):
        q=Mesh();railing(q,0,0,4.6,C,detail);q.rotate_z(0,0,math.pi/2)
        q.v=[(a+x,b+2.0,c) for a,b,c in q.v];p.extend(q)
    for x in (-3.95,3.95):
        q=Mesh();railing(q,0,0,5.8,C,detail);q.rotate_z(0,0,math.pi/2)
        q.v=[(a+x,b+2.0,c) for a,b,c in q.v];p.extend(q)
    m.add_part('04_入口分流护栏_间距估算',p)
    return m


def campus_gate(l,z,C,detail=True):
    m={'east-gate':east_gate,'new-east-gate':new_east_gate,'west-gate':west_gate}[l['id']](C,detail)
    p=Mesh()
    pads={'east-gate':[(-12,0,5.5,6),(12,0,5.5,6)],
          'new-east-gate':[],  # Its grounded paving and ramps are part of the gate.
          'west-gate':[(-7.15,.6,6.8,6.0),(7.65,.6,5.9,6.0)]}
    for x,y,w,d in pads[l['id']]:
        p.box(x,y,-.06 if l['id']=='west-gate' else .20,w,d,
              .10 if l['id']=='west-gate' else .20,C['path'])
    if p.v:m.add_part('07_人行铺装_范围估算',p)
    if l['id']=='east-gate':
        # Width is constrained by the actual corridor between neighbouring OSM
        # footprints. Keep the mapped gate node rather than moving neighbours.
        m.v=[(a*l['gateWidth']/35,b,c*l['height']/11) for a,b,c in m.v]
    m.rotate_z(0,0,math.radians(180-l['frontBearing']))
    x,y=l['center'];m.v=[(a+x,b+y,c+z+.24) for a,b,c in m.v]
    return m
