"""Small deterministic mesh assembler. Blender coordinates: east X, north Y, up Z."""
import bpy,math,json
from mathutils import Vector
MATERIALS=[]
def material(name,color,roughness=.8,metallic=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness;bs.inputs['Metallic'].default_value=metallic
    MATERIALS.append(m);return len(MATERIALS)-1
class Mesh:
    def __init__(self):self.v=[];self.f=[];self.m=[];self.parts=[];self.ground_uv_bounds=[];self.xy_uv_materials=set()
    def rotate_z(self,x,y,angle):
        c=math.cos(angle);s=math.sin(angle)
        self.v=[(x+(a-x)*c-(b-y)*s,y+(a-x)*s+(b-y)*c,z) for a,b,z in self.v]
    def add_part(self,name,other):
        start=len(self.v);self.extend(other);self.parts.append((name,start,len(self.v)))
    def face(self,coords,mat):
        i=len(self.v);self.v.extend(coords);self.f.append(tuple(range(i,i+len(coords))));self.m.append(mat)
    def box(self,x,y,z,w,d,h,mat,angle=0):
        c=math.cos(angle);s=math.sin(angle)
        pts=[(x+u*c-v*s,y+u*s+v*c,z+t) for u,v,t in [(-w/2,-d/2,-h/2),(w/2,-d/2,-h/2),(w/2,d/2,-h/2),(-w/2,d/2,-h/2),(-w/2,-d/2,h/2),(w/2,-d/2,h/2),(w/2,d/2,h/2),(-w/2,d/2,h/2)]]
        for face in [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:self.face([pts[i] for i in face],mat)
    def cylinder(self,x,y,z,r,h,mat,n=12,topr=None):
        r2=r if topr is None else topr
        a=[(x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z-h/2) for i in range(n)]
        b=[(x+r2*math.cos(i*math.tau/n),y+r2*math.sin(i*math.tau/n),z+h/2) for i in range(n)]
        for i in range(n):j=(i+1)%n;self.face([a[i],a[j],b[j],b[i]],mat)
        self.face(a[::-1],mat);self.face(b,mat)
    def line(self,a,b,r,mat,n=6):
        av=Vector(a);bv=Vector(b);axis=(bv-av).normalized();u=axis.cross(Vector((0,0,1)))
        if u.length<.01:u=axis.cross(Vector((0,1,0)))
        u.normalize();v=axis.cross(u);aa=[];bb=[]
        for i in range(n):q=(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n))*r;aa.append(tuple(av+q));bb.append(tuple(bv+q))
        for i in range(n):j=(i+1)%n;self.face([aa[i],aa[j],bb[j],bb[i]],mat)
    def roof(self,x,y,z,w,d,rise,mat):
        a=(x-w/2,y-d/2,z);b=(x+w/2,y-d/2,z);c=(x+w/2,y+d/2,z);d0=(x-w/2,y+d/2,z)
        p=(x-w*.26,y,z+rise);q=(x+w*.26,y,z+rise)
        for f in [[a,b,q,p],[b,c,q],[c,d0,p,q],[d0,a,p]]:self.face(f,mat)
    def ellipsoid(self,x,y,z,rx,ry,rz,mat,n=10,rings=6):
        for j in range(rings):
            t0=math.pi*j/rings;t1=math.pi*(j+1)/rings
            for i in range(n):
                a0=math.tau*i/n;a1=math.tau*(i+1)/n
                self.face([(x+rx*math.sin(t)*math.cos(a),y+ry*math.sin(t)*math.sin(a),z+rz*math.cos(t)) for t,a in [(t0,a0),(t1,a0),(t1,a1),(t0,a1)]],mat)
    def extrude(self,polys,triangles,z,h,wall,roof=None):
        for poly,tri in zip(polys,triangles):
            flat=[v for ring in poly for v in ring[:-1]]
            for i in range(0,len(tri),3):self.face([(flat[k][0],flat[k][1],z+h) for k in tri[i:i+3]],wall if roof is None else roof)
            for ring in poly:
                for a,b in zip(ring,ring[1:]):self.face([(a[0],a[1],z),(b[0],b[1],z),(b[0],b[1],z+h),(a[0],a[1],z+h)],wall)
    def extend(self,other):
        offset=len(self.v);self.v+=other.v;self.f += [tuple(i+offset for i in f) for f in other.f];self.m+=other.m
    def object(self,name,collection,props=None):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.v,[],self.f);mesh.update()
        o=bpy.data.objects.new(name,mesh);collection.objects.link(o)
        used=sorted(set(self.m));remap={v:i for i,v in enumerate(used)}
        for i in used:mesh.materials.append(MATERIALS[i])
        for p,m in zip(mesh.polygons,self.m):p.material_index=remap[m]
        for label,start,end in self.parts:
            o.vertex_groups.new(name=label).add(list(range(start,end)),1.0,'REPLACE')
        # Meter-scaled planar UVs, projected along each face's dominant normal.
        # Only textured faces need UVs; the exporter keeps the common layer for batching.
        uv=mesh.uv_layers.new(name='米制平面纹理')
        for p in mesh.polygons:
            # Fine paving-ground triangles can have an unstable float32
            # normal. Preserve other terrain/underpass UV projections.
            ground=props and props.get('layer')=='terrain' and any(x0<=p.center.x<=x1 and y0<=p.center.y<=y1 for x0,y0,x1,y1 in self.ground_uv_bounds)
            axis=2 if ground or self.m[p.index] in self.xy_uv_materials else max(range(3),key=lambda i:abs(p.normal[i]));axes=[i for i in range(3) if i!=axis]
            for loop in p.loop_indices:
                co=mesh.vertices[mesh.loops[loop].vertex_index].co
                uv.data[loop].uv=(co[axes[0]]/4,co[axes[1]]/4)
        if props:
            for k,v in props.items():o[k]=v
        return o
