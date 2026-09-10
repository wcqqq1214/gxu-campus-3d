"""Deterministic near and far tree templates, shared by full and vegetation-only builds."""
import math, random, bmesh
from geometry import Mesh

def tree_templates(C, collection, detail):
    if detail:
        templates=[]
        for typ in range(3):
            m=Mesh();m.cylinder(0,0,2.5,.24,5,C['bark'],8,topr=.12)
            if typ<2:
                rng=random.Random(200+typ)
                for i in range(8 if typ==0 else 5):
                    angle=i*math.tau/8;r=1.7 if i else 0
                    m.ellipsoid(math.cos(angle)*r,math.sin(angle)*r,5+rng.uniform(-.8,1.6),2.0,1.8,2.0 if typ==0 else 3.2,C[['leaf','leaf2','leaf3'][i%3]],12,8)
            else:
                # Continuous arching rachis and paired leaflets replace disconnected triangles.
                for i in range(10):
                    a=i*math.tau/10;ux,uy=math.cos(a),math.sin(a);vx,vy=-uy,ux
                    def stem(t):return (ux*t*4.1,uy*t*4.1,6.2+math.sin(t*math.pi)*1.0-t*1.6)
                    for j in range(9):
                        t=j/9;t1=(j+1)/9;p0=stem(t);p1=stem(t1)
                        m.line(p0,p1,.028,C['leaf'],4)
                        for side in [-1,1]:
                            spread=.63*math.sin((t+.10)*math.pi)*side
                            tip=(p0[0]+ux*.36+vx*spread,p0[1]+uy*.36+vy*spread,p0[2]-.18-abs(spread)*.15)
                            m.face([p0,tip,p1],C['leaf2'] if j%3 else C['leaf3'])
            template=m.object(f'Tree-template-{typ}',collection,{'template':typ})
            if typ<2:
                bm=bmesh.new();bm.from_mesh(template.data)
                bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
                bm.to_mesh(template.data);bm.free()
                for poly in template.data.polygons:poly.use_smooth=True
                template.data.update()
            templates.append(template)
    else:
        templates=[]
        for typ in range(3):
            m=Mesh();m.cylinder(0,0,2.5,.24,5,C['bark'],8,topr=.12)
            if typ<2:
                rng=random.Random(200+typ)
                for i in range(8 if typ==0 else 5):
                    angle=i*math.tau/8;r=1.7 if i else 0
                    m.ellipsoid(math.cos(angle)*r,math.sin(angle)*r,5+rng.uniform(-.8,1.6),2.0,1.8,2.0 if typ==0 else 3.2,C[['leaf','leaf2','leaf3'][i%3]],8,5)
            else:
                for i in range(10):
                    a=i*math.tau/10
                    for j in range(5):
                        r=j*.8;r1=(j+1)*.8;z0=6+math.sin(j/5*math.pi)*1.3-j*.26;z1=6+math.sin((j+1)/5*math.pi)*1.3-(j+1)*.26
                        m.face([(math.cos(a)*r-math.sin(a)*.5,math.sin(a)*r+math.cos(a)*.5,z0),(math.cos(a)*r1,math.sin(a)*r1,z1),(math.cos(a)*r+math.sin(a)*.5,math.sin(a)*r-math.cos(a)*.5,z0)],C['leaf2'])
            templates.append(m.object(f'Tree-far-template-{typ}',collection,{'template':typ}))
    return templates
