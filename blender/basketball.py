"""Mapped outdoor courts with proportioned markings and modeled basket units."""
import math
from geometry import Mesh
from sports import strip

def court_model(court,C):
    m=Mesh();z=court['elevation']+.025
    floor=Mesh()
    # Disjoint color regions avoid coplanar overlapping paint under Draco.
    for x0,x1,y0,y1,key in [(-7.5,-2.45,-14,14,False),(2.45,7.5,-14,14,False),(-2.45,2.45,-8.2,8.2,False),(-2.45,2.45,-14,-8.2,True),(-2.45,2.45,8.2,14,True)]:
        floor.face([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)],C['courtKey' if key else 'courtGreen'])
    m.add_part('比赛区与两端禁区配色',floor)
    paint=Mesh();pz=z+.04;white=C['sportWhite']
    def draw(points,closed=False):strip(paint,points,pz,.05,white,closed)
    def arc(x,y,r,start=0,end=math.tau,segments=64):
        draw([(x+r*math.cos(a),y+r*math.sin(a)) for a in [start+(end-start)*i/segments for i in range(segments+1)]])
    draw([(-7.525,-14.025),(7.525,-14.025),(7.525,14.025),(-7.525,14.025)],True)
    draw([(-7.65,0),(7.65,0)]);arc(0,0,1.775)
    for sign in [-1,1]:
        end=sign*14;free=sign*(14-5.775);rim=sign*(14-1.575)
        draw([(-2.425,end),(-2.425,free),(2.425,free),(2.425,end)])
        # Solid free-throw semicircle faces midcourt; the inner half is dashed.
        start=0 if sign<0 else math.pi
        arc(0,free,1.775,start,start+math.pi,32)
        for k in range(6):arc(0,free,1.775,start+math.pi+k*math.pi/6,start+math.pi+(k+.55)*math.pi/6,4)
        radius=6.725;side=6.575;dy=math.sqrt(radius*radius-side*side)
        draw([(-side,end),(-side,rim-sign*dy)])
        draw([(side,end),(side,rim-sign*dy)])
        if sign<0:arc(0,rim,radius,math.atan2(dy,side),math.pi-math.atan2(dy,side),64)
        else:arc(0,rim,radius,math.pi+math.atan2(dy,side),math.tau-math.atan2(dy,side),64)
        arc(0,rim,1.275,start,start+math.pi,24)
        for side_sign in [-1,1]:
            draw([(side_sign*1.275,rim),(side_sign*1.275,rim+sign*.375)])
            for d in [1.75,2.60,3.45,4.30]:draw([(side_sign*2.45,end-sign*d),(side_sign*2.62,end-sign*d)])
    m.add_part('边线中圈罚球线三分线与合理冲撞区',paint)
    for sign,label in [(-1,'南端'),(1,'北端')]:
        hoop=Mesh();rim=sign*12.425;board=sign*12.815;post=sign*14.55
        hoop.box(0,post,z+.06,.74,.52,.12,C['courtMetal'])
        hoop.cylinder(0,post,z+1.38,.11,2.7,C['courtFrame'],8)
        hoop.box(0,post-sign*.04,z+.94,.34,.34,1.72,C['courtFrame'])
        hoop.line((0,post,z+2.65),(0,sign*13.35,z+3.5),.10,C['courtFrame'],8)
        hoop.line((0,sign*13.35,z+3.5),(0,board,z+3.5),.10,C['courtFrame'],8)
        for side in [-1,1]:
            hoop.line((0,sign*13.4,z+3.46),(side*.65,board,z+3.60),.035,C['courtMetal'],6)
        hoop.box(0,board,z+3.425,1.8,.03,1.05,C['courtGlass'])
        for x in [-.875,.875]:hoop.box(x,board-sign*.025,z+3.425,.05,.03,1.05,white)
        for h in [2.925,3.925]:hoop.box(0,board-sign*.025,z+h,1.8,.03,.05,white)
        for x in [-.275,.275]:hoop.box(x,board-sign*.038,z+3.25,.05,.025,.45,white)
        for h in [3.05,3.475]:hoop.box(0,board-sign*.038,z+h,.60,.025,.05,white)
        hoop.box(0,board-sign*.035,z+2.89,1.86,.13,.10,C['courtFrame'])
        hoop.line((0,board-sign*.03,z+3.041),(0,rim+sign*.22,z+3.041),.025,C['courtOrange'],6)
        # 450 mm clear opening and 18 mm rim tube; top is 3.05 m above floor.
        rr=.234;rz=z+3.041
        for i in range(40):
            for j in range(8):
                coords=[]
                for u,v in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
                    a=u*math.tau/40;b=v*math.tau/8
                    coords.append(((rr+.009*math.cos(b))*math.cos(a),rim+(rr+.009*math.cos(b))*math.sin(a),rz+.009*math.sin(b)))
                hoop.face(coords,C['courtOrange'])
        m.add_part(label+'篮架篮板与篮圈',hoop)
        net=Mesh()
        # Open tapered net, real diamond links rather than a solid white cone.
        for level in range(2):
            h0,h1=rz-.20*level,rz-.20*(level+1);r0,r1=.225-.045*level,.225-.045*(level+1)
            for i in range(12):
                a=(i+(level%2)*.5)*math.tau/12
                for direction in [-1,1]:
                    b=a+direction*math.pi/12
                    net.line((r0*math.cos(a),rim+r0*math.sin(a),h0),(r1*math.cos(b),rim+r1*math.sin(b),h1),.008,C['goalNet'],3)
        m.add_part(label+'镂空篮网',net)
    c,s=math.cos(court['rotation']),math.sin(court['rotation']);cx,cy=court['center']
    m.v=[(cx+x*c-y*s,cy+x*s+y*c,h) for x,y,h in m.v]
    return m

def bank_paving(bank,C):
    mesh=Mesh();p=bank['paving'];z=bank['elevation']
    for i in range(0,len(p['triangles']),3):mesh.face([(*p['vertices'][k],z) for k in p['triangles'][i:i+3]],C['courtApron'])
    for a,b in zip(bank['ground'],bank['ground'][1:]):mesh.face([(*a,bank['terrainLevel']),(*b,bank['terrainLevel']),(*b,z),(*a,z)],C['courtApron'])
    return mesh

def bank_model(bank,courts,C):
    mesh=bank_paving(bank,C)
    for court in courts:
        if court['bank']==bank['id']:mesh.extend(court_model(court,C))
    return mesh
