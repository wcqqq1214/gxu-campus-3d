"""Public road, grade-separated crossings and mapped lake bridges.

Positional geometry is OSM-derived. Section sizes and unsighted components are
explicit estimates in infrastructure.json, not a claim of engineering accuracy.
"""
import math
from geometry import Mesh
from south_gate import inscription

def frames(path):
    result=[]
    for i,p in enumerate(path):
        a=path[max(0,i-1)];b=path[min(len(path)-1,i+1)];dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
        result.append((dx/length,dy/length))
    return result

def ribbon(m,path,left,right,mat,raise_z=0,axes=None):
    left,right=sorted([left,right])
    axes=axes or frames(path)
    for i,(a,b) in enumerate(zip(path,path[1:])):
        ux,uy=axes[i];vx,vy=axes[i+1]
        m.face([(a[0]-uy*left,a[1]+ux*left,a[2]+raise_z),
                (b[0]-vy*left,b[1]+vx*left,b[2]+raise_z),
                (b[0]-vy*right,b[1]+vx*right,b[2]+raise_z),
                (a[0]-uy*right,a[1]+ux*right,a[2]+raise_z)],mat)

def edge_box(m,a,b,offset,width,height,mat,zoffset=0,axes=None):
    if axes is None:axes=frames([a,b])
    (ux,uy),(vx,vy)=axes;nx=-uy;ny=ux;mx=-vy;my=vx
    # Sloping box faces rather than horizontal blocks keep ramp curbs continuous.
    for side in [-1,1]:
        off=offset+side*width/2
        face=[(a[0]+nx*off,a[1]+ny*off,a[2]+zoffset),
                (b[0]+mx*off,b[1]+my*off,b[2]+zoffset),
                (b[0]+mx*off,b[1]+my*off,b[2]+zoffset+height),
                (a[0]+nx*off,a[1]+ny*off,a[2]+zoffset+height)]
        m.face(face if side<0 else face[::-1],mat)
    m.face([(a[0]+nx*(offset-width/2),a[1]+ny*(offset-width/2),a[2]+zoffset+height),
            (b[0]+mx*(offset-width/2),b[1]+my*(offset-width/2),b[2]+zoffset+height),
            (b[0]+mx*(offset+width/2),b[1]+my*(offset+width/2),b[2]+zoffset+height),
            (a[0]+nx*(offset+width/2),a[1]+ny*(offset+width/2),a[2]+zoffset+height)],mat)

def fence_panel(m,a,b,side,C,detail,axes):
    dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);nx=-dy/length;ny=dx/length;angle=math.atan2(dy,dx)
    edge_box(m,a,b,side*7.7,.35,.52,C['wallStone'],.14,axes)
    if not detail:return
    def point(t,h):
        ux=axes[0][0]*(1-t)+axes[1][0]*t;uy=axes[0][1]*(1-t)+axes[1][1]*t
        return (a[0]+dx*t-uy*side*7.7,a[1]+dy*t+ux*side*7.7,a[2]*(1-t)+b[2]*t+h)
    x,y,z=point(0,.14)
    for h,w,d,hh in [(.95,.48,.48,1.9),(1.96,.61,.61,.14),(2.07,.51,.51,.1)]:
        m.box(x,y,z+h,w,d,hh,C['wallStone'],angle)
    for h in [.7,1.78]:m.line(point(0,h),point(1,h),.038,C['fenceIron'],4)
    # The 2023 photograph shows inward-leaning pickets between square uprights.
    count=max(6,round(length/.23))
    for j in range(1,count):
        t=j/count;pinch=.5+(t-.5)*.67
        m.line(point(t,.64),point(pinch,1.24),.023,C['fenceIron'],4)
        m.line(point(pinch,1.24),point(t,1.9),.023,C['fenceIron'],4)
    for t in [.05,.5,.95]:m.line(point(t,.64),point(t,1.92),.032,C['fenceIron'],4)
    # Schematic planting: photo-supported species / colour, not surveyed flower positions.
    if int(abs(a[0])+abs(a[1]))%4==0:
        for t in [.28,.62,.85]:
            px,py,pz=point(t,1.65)
            m.ellipsoid(px,py,pz,.65,.56,.5,C['leaf2'],6,3)
            m.ellipsoid(px+nx*.2,py+ny*.2,pz+.18,.58,.48,.36,C['gateFlower'],6,3)

def road_chunk(chunk,C,detail):
    m=Mesh();p=chunk['path'];axes=chunk['frames'];ribbon(m,p,-5,5,C['asphalt'],axes=axes)
    for side in [-1,1]:
        ribbon(m,p,side*5,side*7,C['pavingRed'],.17,axes)
        ribbon(m,p,side*5.7,side*6.05,C['tactile'],.185,axes)
        for i,(a,b) in enumerate(zip(p,p[1:])):
            edge_box(m,a,b,side*5,.25,.18,C['curb'],axes=axes[i:i+2])
            if chunk['fence'][i][0 if side==-1 else 1] and chunk['fence'][i+1][0 if side==-1 else 1]:
                fence_panel(m,a,b,side,C,detail,axes[i:i+2])
    # Dashed centre line is visible even in the inexpensive overview mesh.
    for i in range(0,len(p)-1,3):ribbon(m,p[i:i+2],-.07,.07,C['roadYellow'],.035,axes[i:i+2])
    if detail:
        for offset in [-4.65,4.65]:ribbon(m,p,offset-.055,offset+.055,C['roadWhite'],.035,axes)
        for i in range(5,len(p)-1,10):
            x,y,z=p[i];ux,uy=axes[i];nx=-uy;ny=ux;x+=nx*6.7;y+=ny*6.7
            m.cylinder(x,y,z+3.8,.105,7.2,C['lampMetal'],8)
            m.line((x,y,z+7.3),(x-nx*1.4,y-ny*1.4,z+7.6),.065,C['lampMetal'],6)
            m.box(x-nx*1.5,y-ny*1.5,z+7.58,.8,.34,.16,C['lampMetal'],math.atan2(ny,nx))
            m.box(x-nx*1.5,y-ny*1.5,z+7.48,.62,.24,.025,C['lampGlass'],math.atan2(ny,nx))
        for i in range(12,len(p)-1,22):
            x,y,z=p[i];ux,uy=axes[i];nx=-uy;ny=ux
            for side in [-1,1]:
                # Direction arrows, drawn as flat original geometry.
                cx=x+nx*side*2.4;cy=y+ny*side*2.4;tx=-ux*side;ty=-uy*side
                arrow=[(cx+tx*2,cy+ty*2,z+.04),(cx-tx*.1+nx*.7,cy-ty*.1+ny*.7,z+.04),
                        (cx+tx*.3+nx*.18,cy+ty*.3+ny*.18,z+.04),(cx-tx*1.5+nx*.18,cy-ty*1.5+ny*.18,z+.04),
                        (cx-tx*1.5-nx*.18,cy-ty*1.5-ny*.18,z+.04),(cx+tx*.3-nx*.18,cy+ty*.3-ny*.18,z+.04),
                        (cx-tx*.1-nx*.7,cy-ty*.1-ny*.7,z+.04)]
                # Drape paint onto the same local slope as the asphalt ribbon.
                def paint_height(q):
                    along=(q[0]-x)*ux+(q[1]-y)*uy
                    neighbor=p[i+1] if along>=0 else p[i-1]
                    run=(neighbor[0]-x)*ux+(neighbor[1]-y)*uy
                    return (q[0],q[1],z+(neighbor[2]-z)*along/run+.045)
                arrow=[paint_height(q) for q in arrow]
                m.face(arrow if side<0 else arrow[::-1],C['roadWhite'])
    return m

def approaches(b,C):
    m=Mesh();road=Mesh();walks=Mesh();walls=Mesh()
    path=b['underpass'];axes=frames(path);walk=b['pedestrian'];walkpath=walk['path']
    inner=walk['innerOffset'];outer=inner+walk['width']
    ba,bc=b['upper'];dx=bc[0]-ba[0];dy=bc[1]-ba[1];length=math.hypot(dx,dy)
    def covered_segment(a,c,side,local_axes):
        points=[]
        for p,(ux,uy) in zip([a,c],local_axes):
            x=p[0]-uy*side*walk['cutHalfWidth']-ba[0]
            y=p[1]+ux*side*walk['cutHalfWidth']-ba[1]
            points.append(((x*dx+y*dy)/length,(-x*dy+y*dx)/length))
        return min(q[0] for q in points)<length+.5 and max(q[0] for q in points)>-.5 and min(q[1] for q in points)<b['deckWidth']/2+.5 and max(q[1] for q in points)>-b['deckWidth']/2-.5
    ribbon(road,path,-5,5,C['asphalt'],axes=axes)
    for side in [-1,1]:
        ribbon(road,path,side*5,side*inner,C['curb'],.15,axes)
        ribbon(walks,walkpath,side*inner,side*outer,C['path'],axes=axes)
        for i,(a,c) in enumerate(zip(path,path[1:])):
            ux,uy=axes[i];vx,vy=axes[i+1]
            wa,wc=walkpath[i:i+2]
            covered=covered_segment(a,c,side,axes[i:i+2])
            # Terminate the outer wall inside the edge beam so their junction
            # closes, while staying below the public-road wearing surface.
            ceiling=b['deckElevation']-.2
            wall_top=tuple(min(p[3]+.25,ceiling) if covered else p[3]+.25 for p in [a,c])
            # Inner wall supports the raised walk; outer wall meets the terrain.
            # Neither the walk nor its railing inherits the uncut DEM elevation.
            for offset,lower,upper in [(inner,(a[2]-.1,c[2]-.1),(wa[2],wc[2])),
                                       (outer,(wa[2]-.15,wc[2]-.15),wall_top)]:
                off=side*offset
                wall=[(a[0]-uy*off,a[1]+ux*off,lower[0]),(c[0]-vy*off,c[1]+vx*off,lower[1]),
                      (c[0]-vy*off,c[1]+vx*off,upper[1]),(a[0]-uy*off,a[1]+ux*off,upper[0])]
                walls.face(wall if side>0 else wall[::-1],C['bridgeConcrete'])
            edge_box(walls,wa,wc,side*inner,.24,.10,C['curb'],axes=axes[i:i+2])
            # The outer cap also covers the small construction joint to the cut.
            top=[a[0],a[1],a[3]];top2=[c[0],c[1],c[3]]
            # An untrimmed terrain-height cap would cut across the public road.
            if not covered:edge_box(walls,top,top2,side*walk['cutHalfWidth'],.3,.25,C['curb'],axes=axes[i:i+2])
            edge_box(road,a,c,side*5,.22,.18,C['curb'],axes=axes[i:i+2])
    for i in range(0,len(path)-1,4):ribbon(road,path[i:i+2],-.07,.07,C['roadYellow'],.035,axes[i:i+2])
    m.add_part('下穿车行道与排水边带',road)
    m.add_part('两侧抬高人行步道',walks)
    m.add_part('步道支挡与外侧挡墙',walls)
    return m

def bridge(b,C,detail):
    m=Mesh();a,c=b['upper'];dx=c[0]-a[0];dy=c[1]-a[1];length=math.hypot(dx,dy);angle=math.atan2(dy,dx)
    cx=(a[0]+c[0])/2;cy=(a[1]+c[1])/2;z=b['deckElevation'];width=b['deckWidth'];floor=b['floorElevation'];slab=b['slabThickness']
    deck=Mesh();deck.box(0,0,z-(slab+.04)/2,length,width,slab-.04,C['bridgeConcrete'])
    for abutment in b['abutments']:
        deck.extrude([abutment['rings']],[abutment['triangles']],floor,z-floor,C['bridgeConcrete'])
    for side in [-1,1]:
        deck.box(0,side*(width/2-.2),z-.35,length+.3,.55,.6,C['bridgeEdge'])
        # Vehicle parapets / railings above the public road.
        deck.box(0,side*(width/2-.16),z+.28,length,.3,.5,C['curb'])
        if detail:
            for xx in range(math.ceil(-length/2),math.floor(length/2),2):
                deck.box(xx,side*(width/2-.16),z+.85,.09,.09,1.1,C['lampMetal'])
            for h in [.62,1.3]:deck.box(0,side*(width/2-.16),z+h,length,.065,.065,C['lampMetal'])
            for xx in range(math.ceil(-length/2),math.floor(length/2)-2,2):
                for sign in [-1,1]:deck.line((xx,side*(width/2-.16),z+.64 if sign==1 else z+1.23),(xx+2,side*(width/2-.16),z+1.23 if sign==1 else z+.64),.027,C['lampMetal'],4)
        else:deck.box(0,side*(width/2-.16),z+.9,length,.08,.08,C['lampMetal'])
    if detail:
        # Exposed beam ends and joints; exact reinforcement is not asserted.
        for yy in [-4,-2,0,2,4]:deck.box(0,yy,z-slab-b['beamDepth']+.125,length-1,.24,.25,C['bridgeEdge'])
        for xx in [-length/2+.2,length/2-.2]:deck.box(xx,0,z+.015,.08,width,.025,C['bridgeJoint'])
    deck.rotate_z(0,0,angle);deck.v=[(x+cx,y+cy,h) for x,y,h in deck.v]
    m.add_part('桥面梁板与桥台',deck)
    path=b['underpass'];axes=frames(path)
    if b['id']=='chongzuo-bridge':
        # Historical photo shows a median pier. Align it with the campus road.
        bearing=math.radians(b['frontBearing']);ux=math.sin(bearing);uy=math.cos(bearing)
        m.box(*b['center'],(z-slab+floor)/2,16,.65,z-slab-floor,C['bridgeConcrete'],math.atan2(uy,ux))
        if detail:
            # The historical name panel sits beside the campus-road opening,
            # not at the far end of the much longer public-road bridge span.
            reach=math.dist(b['portalCenter'],b['center'])
            for sign in [-1,1]:
                fx,fy=ux*sign,uy*sign
                px=b['center'][0]+fx*(reach+.18)-fy*5.65
                py=b['center'][1]+fy*(reach+.18)+fx*5.65
                panel=Mesh();panel.box(0,0,floor+2.3,1.12,.22,3.8,C['bridgePlaque'])
                for i,char in enumerate('崇左桥'):
                    panel.extend(inscription(char,0,-.13,floor+3.45-i*1.05,.85,.9,C['white'],True))
                panel.rotate_z(0,0,math.atan2(fy,fx)+math.pi/2)
                panel.v=[(x+px,y+py,h) for x,y,h in panel.v]
                m.add_part('崇左桥入口题名（历史照片辅助；双面位置估算）',panel)
    if detail:
        rails=Mesh();drains=Mesh();walk=b['pedestrian'];walkpath=walk['path']
        for i,(a,c) in enumerate(zip(path,path[1:])):
            ux,uy=axes[i];theta=math.atan2(uy,ux)
            for side in [-1,1]:
                off=side*walk['innerOffset'];vx,vy=axes[i+1]
                start=(a[0]-uy*off,a[1]+ux*off,walkpath[i][2]+.1)
                end=(c[0]-vy*off,c[1]+vx*off,walkpath[i+1][2]+.1)
                def rail_point(t,h):
                    return tuple(start[k]*(1-t)+end[k]*t+(h if k==2 else 0) for k in range(3))
                rails.cylinder(*rail_point(0,.58),.045,1.16,C['lampMetal'],6)
                if i==len(path)-2:rails.cylinder(*rail_point(1,.58),.045,1.16,C['lampMetal'],6)
                for h in [.12,1.12]:rails.line(rail_point(0,h),rail_point(1,h),.04,C['lampMetal'],5)
                # Chongzuo's photographed rail has alternating solid round panels
                # and upright bars. Other unsighted bridge rails stay generic.
                segment=math.dist(start[:2],end[:2])
                for t in [.16,.32,.68,.84]:
                    rails.line(rail_point(t,.12),rail_point(t,1.08),.019,C['lampMetal'],4)
                if b['id']=='chongzuo-bridge':
                    radius=.39 if i%2==0 else .19
                    circle=[rail_point(.5+radius*math.cos(j*math.tau/16)/segment,.6+radius*math.sin(j*math.tau/16)) for j in range(16)]
                    rails.face(circle,C['curb']);rails.face(circle[::-1],C['curb'])
                    for u,v in zip(circle,circle[1:]+circle[:1]):rails.line(u,v,.022,C['lampMetal'],4)
                # Covered drainage channel and paired drain slots beside the retaining wall.
                qx=a[0]-uy*side*5.7;qy=a[1]+ux*side*5.7
                drains.box(qx,qy,a[2]+.2,1.6,.68,.12,C['drainStone'],theta)
                for t in [-.42,0,.42]:
                    drains.box(qx+ux*t,qy+uy*t,a[2]+.267,.3,.10,.014,C['bridgeJoint'],theta)
        m.add_part('坡道圆纹金属护栏（照片参照）' if b['id']=='chongzuo-bridge' else '坡道金属护栏（估算）',rails);m.add_part('下穿排水沟与盖板',drains)
        for side in [-1,1]:
            ux=dx/length;uy=dy/length
            for j in [-.28,.28]:
                x=cx+ux*length*j-uy*side*4;y=cy+uy*length*j+ux*side*4
                m.box(x,y,z-slab-.16,.65,.26,.08,C['lampGlass'],angle)
    return m

def lake_bridge(b,C,detail):
    m=Mesh();path=b['path'];half=b['width']/2
    ribbon(m,path,-half,half,C['bridgeConcrete'])
    for side in [-1,1]:
        for a,c in zip(path,path[1:]):
            edge_box(m,a,c,side*half,.2,.16,C['curb'],-.16)
            edge_box(m,a,c,side*half,.1,.1,C['lampMetal'],1.03)
        if detail:
            for p,(ux,uy) in zip(path,frames(path)):
                x=p[0]-uy*side*half;y=p[1]+ux*side*half
                m.cylinder(x,y,p[2]+.52,.05,1.04,C['lampMetal'],6)
            ribbon(m,path,side*(half-.45),side*(half-.2),C['pavingRed'],.025)
    for i in range(1,len(path)-1,max(2,len(path)//3)):
        x,y,z=path[i];bottom=b['waterLevel']-1
        m.box(x,y,(z+bottom)/2,.65,b['width']*.75,z-bottom,C['bridgeConcrete'],math.atan2(path[-1][1]-path[0][1],path[-1][0]-path[0][0]))
    return m
