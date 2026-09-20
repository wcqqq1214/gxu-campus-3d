"""A thin gable profile with a real arched cutout and inset pane in both LODs."""
import math


def add_gable_screen(mesh,c,z,C):
    a,u,n=c['start'],c['tangent'],c['normal'];base=z+c['baseHeight']
    def at(s,d,h):return (a[0]+u[0]*s+n[0]*d,a[1]+u[1]*s+n[1]*d,base+h)
    def prism(geometry,front,back,material):
        # Local face axes (along edge, up) have outward normal n on either winding.
        positive=u[1]*n[0]-u[0]*n[1]>0
        for rings,indices in zip(geometry['polygons'],geometry['triangles']):
            flat=[p for ring in rings for p in ring[:-1]]
            for i in range(0,len(indices),3):
                tri=[flat[k] for k in indices[i:i+3]]
                area=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(tri,tri[1:]+tri[:1]))
                if (area>0)!=positive:tri.reverse()
                mesh.face([at(s,front,h) for s,h in tri],material)
                mesh.face([at(s,back,h) for s,h in reversed(tri)],material)
            for index,ring in enumerate(rings):
                points=ring[:-1];area=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(points,points[1:]+points[:1]))
                if (area>0)!=(positive if index==0 else not positive):points.reverse()
                for p,q in zip(points,points[1:]+points[:1]):
                    mesh.face([at(p[0],front,p[1]),at(p[0],back,p[1]),at(q[0],back,q[1]),at(q[0],front,q[1])],material)
    prism(c['wallGeometry'],0,-c['thickness'],C['white'])
    prism(c['frameGeometry'],.015,-.05,C['dark'])
    prism(c['glassGeometry'],-.08,-.10,C['glass'])
    w=c['window'];center=c['length']*w['centerT'];radius=w['width']/2-w['frameWidth']
    bottom=w['bottom']+w['frameWidth'];spring=w['bottom']+w['height']-w['width']/2
    angle=math.atan2(u[1],u[0])
    for offset in (-radius/2,0,radius/2):
        top=spring+math.sqrt(radius*radius-offset*offset)
        x,y,_=at(center+offset,-.055,0)
        mesh.box(x,y,base+(bottom+top)/2,.035,.035,top-bottom,C['dark'],angle)
    x,y,_=at(center,-.055,0)
    mesh.box(x,y,base+spring,radius*2,.035,.035,C['dark'],angle)
