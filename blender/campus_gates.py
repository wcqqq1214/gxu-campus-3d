"""Three independent gate studies. All dimensions are estimates, not surveys.

East: 2018 inauguration photo, later undated street view. West: undated low-res
street view. New east: verified location/guardroom, provisional exterior study.
Local facade faces -Y; rotation is derived from the catalogue compass bearing.
"""
import math
from geometry import Mesh
from south_gate import inscription


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


def new_east_gate(C,detail):
    """Provisional guardroom and walk-in gate study: exterior photo still missing."""
    m=Mesh();p=Mesh();booth(p,-5.9,1.4,2.7,3.2,C,detail);m.add_part('01_门卫室_外观推定',p)
    p=Mesh()
    # Low walls stop short of the mapped central access road.
    for x in [-7.2,6.6]:
        p.box(x,0,1.05,1.4,.60,2.1,C['stone']);p.box(x,0,2.18,1.6,.8,.18,C['white'])
    m.add_part('02_入口边墙_尺寸推定',p)
    p=Mesh()
    for x in [4.0,6.0]:p.box(x,0,1.75,.10,.12,3.5,C['metal'])
    p.box(5,0,3.55,2.4,2.5,.16,C['metal'])
    if detail:
        for yy in [-.8,0,.8]:p.box(5,yy,3.44,2.25,.055,.12,C['metal'])
    for x in [4.1,5.1,6.1]:
        p.box(x,0,.62,.20,1.05,1.24,C['metal'])
        if detail:p.box(x,-.22,1.30,.12,.14,.12,C['dark'])
    m.add_part('03_步行通道_设施推定',p)
    p=Mesh();barrier(p,-3.6,0,C,detail,-1);railing(p,5.1,2.6,3.5,C,detail)
    m.add_part('04_车行道闸与护栏_推定',p)
    return m


def west_gate(C,detail):
    m=Mesh();p=Mesh();booth(p,-5.1,2.8,2.1,2.7,C,detail);m.add_part('01_林荫入口值守岗亭',p)
    p=Mesh()
    for x in [-7.8,-6.5]:
        p.box(x,-.2,2.08,.18,.24,4.16,C['white'])
        if detail:p.box(x,-.35,3.1,.09,.03,1.4,C['gateRed'])
    m.add_part('02_入口标杆',p)
    p=Mesh();barrier(p,-3.5,1,C,detail,-1);barrier(p,3.5,1,C,detail)
    m.add_part('03_车行道闸',p)
    p=Mesh()
    for x in [6.8,8.2,9.6]:
        # Three rails separate pedestrian lanes without a fictitious triumphal arch.
        q=Mesh();railing(q,0,0,4.6,C,detail);q.rotate_z(0,0,math.pi/2)
        q.v=[(a+x,b+.5,c) for a,b,c in q.v];p.extend(q)
    m.add_part('04_步行通道不锈钢护栏',p)
    p=Mesh()
    for x in [-10.2,10.5]:
        p.box(x,2, .35,1,5,.7,C['stone']);p.box(x,2,.76,1.12,5.1,.12,C['gateTrim'])
    m.add_part('05_入口低矮围挡',p)
    return m


def campus_gate(l,z,C,detail=True):
    m={'east-gate':east_gate,'new-east-gate':new_east_gate,'west-gate':west_gate}[l['id']](C,detail)
    p=Mesh()
    pads={'east-gate':[(-12,0,5.5,6),(12,0,5.5,6)],
          'new-east-gate':[(-5.9,.8,3.5,5.8),(5,0,4,6)],
          'west-gate':[(-5.1,1,4.5,6.4),(8.1,1,4.9,6.4)]}
    for x,y,w,d in pads[l['id']]:p.box(x,y,.20,w,d,.20,C['path'])
    m.add_part('07_人行铺装_范围估算',p)
    if l['id']=='east-gate':
        # Width is constrained by the actual corridor between neighbouring OSM
        # footprints. Keep the mapped gate node rather than moving neighbours.
        m.v=[(a*l['gateWidth']/35,b,c*l['height']/11) for a,b,c in m.v]
    m.rotate_z(0,0,math.radians(180-l['frontBearing']))
    x,y=l['center'];m.v=[(a+x,b+y,c+z+.24) for a,b,c in m.v]
    return m
