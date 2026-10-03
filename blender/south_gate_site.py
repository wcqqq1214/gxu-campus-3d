"""South-gate forecourt: dated 2024 satellite trace and recent ground photographs.

All dimensions below are estimates in world metres, independent of gate scaling.
The outer ends meet the existing mapped carriageways. Seasonal pots are not beds.
"""
import json, math, random
from functools import lru_cache
from pathlib import Path
from geometry import Mesh, material

# Ground traces from dated satellite imagery; vectors are kept separate from images.
SITE=json.loads((Path(__file__).resolve().parents[1]/'data/south-gate-site.json').read_text())
REPAIR_BOUNDS=tuple(SITE['repairBounds'])
CROSSING_CENTRES=tuple(tuple(p) for p in SITE['crossingStripeCenters'])

SITE_COLORS={'gatePaving':'#b8b7aa','gatePavingAlt':'#aaa99e','gatePot':'#aa6347',
             'gateLime':'#9aab4f','gateBurgundy':'#663b43','gateBloom':'#c82e77'}


def ensure_materials(C):
    for name,hexcolor in SITE_COLORS.items():
        if name in C:continue
        rgb=[int(hexcolor[i:i+2],16)/255 for i in (1,3,5)]
        C[name]=material(name,[((c+.055)/1.055)**2.4 if c>.04045 else c/12.92 for c in rgb],.96,0)


@lru_cache(maxsize=1)
def terrain():
    return json.loads((Path(__file__).resolve().parents[1]/'public/data/terrain.json').read_text())


def ground(x,y):
    t=terrain();x0,y0,x1,y1=t['bounds'];cols,rows=t['cols'],t['rows']
    u=max(0,min(cols-1.001,(x-x0)/(x1-x0)*(cols-1)));v=max(0,min(rows-1.001,(y-y0)/(y1-y0)*(rows-1)))
    i,j=int(u),int(v);a,b=u-i,v-j;h=t['heights']
    return (h[j*cols+i]*(1-a)+h[j*cols+i+1]*a)*(1-b)+(h[(j+1)*cols+i]*(1-a)+h[(j+1)*cols+i+1]*a)*b+.4


def surface(m,x,y,points,C,offset=0):
    p=[(x+a,y+b,ground(x+a,y+b)+offset) for a,b in points]
    for i in range(1,len(p)-1):m.face([p[0],p[i],p[i+1]],C)


def paving_row(m,x,y,ya,yb,left_a,right_a,left_b,right_b,mat,offset):
    # A narrow grid follows terrain without the heavy uniform subdivision of
    # long, thin triangles. It also keeps slab tops above the joint backing.
    count=math.ceil(max(right_a-left_a,right_b-left_b)/.8)
    for k in range(count):
        la=left_a+(right_a-left_a)*k/count;ra=left_a+(right_a-left_a)*(k+1)/count
        lb=left_b+(right_b-left_b)*k/count;rb=left_b+(right_b-left_b)*(k+1)/count
        surface(m,x,y,[(la,ya),(lb,yb),(rb,yb),(ra,ya)],mat,offset)


def strip(m,x,y,a,b,width,mat,offset=.012):
    dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
    nx,ny=-dy/length*width/2,dx/length*width/2
    surface(m,x,y,[(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)],mat,offset)


def road_patch(x,y,C):
    m=Mesh()
    for tri in SITE['roadTriangles']:surface(m,x,y,tri,C['asphalt'])
    # Only mark actual approach boundaries. The road patch's other edges are
    # overlap seams with Daxue East Road, not curbs across the intersection.
    outline=SITE['features']['road']['localMeters']
    for indices in [range(1,10),range(len(outline)-6,len(outline)-1)]:
        for i in indices:
            a,b=outline[i],outline[i+1]
            n=math.ceil(math.dist(a,b))
            for j in range(n):
                aa=tuple(a[k]+(b[k]-a[k])*j/n for k in range(2))
                bb=tuple(a[k]+(b[k]-a[k])*(j+1)/n for k in range(2))
                strip(m,x,y,aa,bb,.10,C['roadWhite'],.018)
    # The wide 2025 reference shows yellow cross-hatching around the round nose.
    # Clip both diagonal families to a half-annulus, keeping all paint off paving.
    inner,outer=4.9,5.6
    for slope in [-1,1]:
        for k in range(-12,13):
            intercept=k*.90;cuts=[-intercept/slope]
            for r in [inner,outer]:
                disc=8*r*r-4*intercept*intercept
                if disc>=0:
                    cuts.extend([(-2*slope*intercept+sign*math.sqrt(disc))/4 for sign in [-1,1]])
            cuts.sort()
            for a,b in zip(cuts,cuts[1:]):
                t=(a+b)/2;v=slope*t+intercept
                if b-a>1e-5 and v<=0 and inner**2<t*t+v*v<outer**2:
                    strip(m,x,y,(a-1.5,-40.97+slope*a+intercept),(b-1.5,-40.97+slope*b+intercept),.12,C['roadYellow'],.022)
    for i in range(48):
        a=math.pi+i*math.pi/48;b=math.pi+(i+1)*math.pi/48
        strip(m,x,y,(outer*math.cos(a)-1.5,-40.97+outer*math.sin(a)),
              (outer*math.cos(b)-1.5,-40.97+outer*math.sin(b)),.12,C['roadYellow'],.022)
    # White bars follow the oblique envelope traced from the 2024 image.
    for stripe in SITE['crossingStripeTriangles']:
        for tri in stripe:surface(m,x,y,tri,C['roadWhite'],.022)
    return m


def clip_edge(poly,a,b,inside):
    """Clip XYZ/UV vertices against a CCW mask edge, interpolating all fields."""
    out=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        dp=((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))*(1 if inside else -1)
        dq=((b[0]-a[0])*(q[1]-a[1])-(b[1]-a[1])*(q[0]-a[0]))*(1 if inside else -1)
        if dp>=-1e-8:out.append(p)
        if (dp>0 and dq<0) or (dp<0 and dq>0):
            t=dp/(dp-dq);out.append(tuple(u+(v-u)*t for u,v in zip(p,q)))
    return out


def repair_roads(mesh,x,y,C):
    """Replace the traced junction plus the superseded patch, preserving outside UVs."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    masks=[]
    for points in SITE['maskConvexPolygons']:
        p=[(x+a,y+b) for a,b in points]
        if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1]))<0:p.reverse()
        masks.append((p,(min(a for a,b in p),min(b for a,b in p),max(a for a,b in p),max(b for a,b in p))))
    out=Mesh();out.v=list(mesh.v);uvs=[];source_uvs=getattr(mesh,'source_uvs',None)
    out.changed_materials=set()
    x0,y0,x1,y1=REPAIR_BOUNDS;x0+=x;x1+=x;y0+=y;y1+=y
    def overlaps(p,b):return max(v[0] for v in p)>b[0] and min(v[0] for v in p)<b[2] and max(v[1] for v in p)>b[1] and min(v[1] for v in p)<b[3]
    for index,(face,mat) in enumerate(zip(mesh.f,mesh.m)):
        points=[mesh.v[i] for i in face]
        if not overlaps(points,(x0,y0,x1,y1)):
            out.f.append(face);out.m.append(mat)
            if source_uvs is not None:uvs.append(source_uvs[index])
            continue
        original=[tuple(v)+tuple(uv) for v,uv in zip(points,source_uvs[index])] if source_uvs is not None else points
        fragments=[original];changed=False
        for mask,bounds in masks:
            remaining=[]
            for poly in fragments:
                if not overlaps(poly,bounds):remaining.append(poly);continue
                # Test intersection first, preserving wholly unrelated faces exactly.
                intersection=poly
                for a,b in zip(mask,mask[1:]+mask[:1]):
                    intersection=clip_edge(intersection,a,b,True)
                    if len(intersection)<3:break
                if len(intersection)<3:remaining.append(poly);continue
                changed=True;inside=poly
                for a,b in zip(mask,mask[1:]+mask[:1]):
                    outside=clip_edge(inside,a,b,False)
                    if len(outside)>=3:remaining.append(outside)
                    inside=clip_edge(inside,a,b,True)
                    if len(inside)<3:break
            fragments=remaining
        if not changed:
            out.f.append(face);out.m.append(mat)
            if source_uvs is not None:uvs.append(source_uvs[index])
        else:
            out.changed_materials.add(mat)
            for poly in fragments:
                out.face([v[:3] for v in poly],mat)
                if source_uvs is not None:uvs.append([v[3:] for v in poly])
    patch=road_patch(x,y,C)
    # Blend to the original road plane where this patch overlaps existing asphalt.
    # Coarse old DEM triangles can otherwise leave centimetre-high seam steps.
    old_surface=BVHTree.FromPolygons(mesh.v,[f for f,mat in zip(mesh.f,mesh.m) if mat==C['asphalt']])
    boundary=SITE['features']['road']['localMeters'];stitched=[]
    def edge_distance(px,py,a,b):
        dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((px-a[0])*dx+(py-a[1])*dy)/(dx*dx+dy*dy)))
        return math.hypot(px-a[0]-t*dx,py-a[1]-t*dy)
    for px,py,pz in patch.v:
        distance=min(edge_distance(px-x,py-y,a,b) for a,b in zip(boundary,boundary[1:]+boundary[:1]))
        if distance<1.5:
            hit=old_surface.ray_cast(Vector((px,py,ground(px,py)+10)),Vector((0,0,-1)),20)[0]
            if hit is not None:pz+=(1-distance/1.5)*(hit.z-ground(px,py))
        stitched.append((px,py,pz))
    patch.v=stitched;out.add_part('南门路口 · 2024-11-30 卫星影像描图',patch)
    if source_uvs is not None:
        uvs.extend([[(patch.v[i][0]/4,patch.v[i][1]/4) for i in face] for face in patch.f]);out.source_uvs=uvs
    return out


def forecourt(x,y,C,detail):
    m=Mesh();island=Mesh()
    # Traced island and side aprons. The gate's architecture stays in place.
    for name,triangles in SITE['pavingTriangles'].items():
        offset=.14 if name=='island' else .10
        for i,tri in enumerate(triangles):
            surface(island,x,y,tri,C['gatePaving'],offset)
        outline=SITE['features'][name]['localMeters']
        for a,b in zip(outline,outline[1:]+outline[:1]):
            n=math.ceil(math.dist(a,b)/.6)
            for i in range(n):
                aa=tuple(a[k]+(b[k]-a[k])*i/n for k in range(2));bb=tuple(a[k]+(b[k]-a[k])*(i+1)/n for k in range(2))
                strip(island,x,y,aa,bb,.16,C['curb'],offset+.01)
                island.face([(x+p[0],y+p[1],ground(x+p[0],y+p[1])+h) for p,h in [(aa,-.42),(bb,-.42),(bb,offset),(aa,offset)]],C['curb'])
    m.add_part('门前铺装分流岛 · 低路缘与留白拍照区',island)
    pots=Mesh();rng=random.Random(20241010);segments,rings=(7,4) if detail else (4,2)
    def pot(px,py,r,h):
        zz=ground(px,py)+.15
        pots.cylinder(px,py,zz+h/2,r*.7,h,C['gatePot'],8 if detail else 4,topr=r)
        pots.cylinder(px,py,zz+h-.018,r*1.07,.055,C['gatePot'],8 if detail else 4)
        return zz+h
    # Hundreds of individual small pots, low yellow-green front, burgundy middle.
    for row in range(12):
        for col in range(20):
            px=x-4.05+col*.27+(row%2)*.04;py=y-38.7+row*.46
            zz=pot(px,py,.145,.17)
            height=rng.uniform(.22,.31) if row<4 else rng.uniform(.32,.43)
            mat=C['gateLime'] if row<4 or row>8 else C['gateBurgundy']
            pots.ellipsoid(px+rng.uniform(-.045,.045),py+rng.uniform(-.04,.04),zz+height*.65,.23,.24,height,mat,segments,rings)
    # Broad, branching bougainvillea masses across the rear and down both flanks.
    anchors=[(u,-31.7) for u in [-3,-1.55,0]]
    anchors += [(u,v) for u in [-4.5,1.35] for v in [-33.5,-35.5,-37.5]]
    for index,(dx,dy) in enumerate(anchors):
        px,py=x+dx,y+dy;rng=random.Random(300+index);zz=pot(px,py,.28,.43)
        crown=zz+rng.uniform(.85,1.2);top=(px+.06,py+.03,crown)
        pots.line((px,py,zz),top,.032,C['bark'],6)
        for branch in range(8):
            angle=branch*math.tau/8+rng.uniform(-.25,.25);reach=rng.uniform(.35,.68)
            bx,by=px+math.cos(angle)*reach,py+math.sin(angle)*reach;bz=crown+rng.uniform(-.3,.45)
            pots.line((px+.03,py,zz+.28),(bx,by,bz),.016,C['bark'],5)
            if detail:
                for spray in range(3):
                    a=angle+spray*math.tau/3
                    pots.ellipsoid(bx+math.cos(a)*.20,by+math.sin(a)*.18,bz+(spray-1)*.045,.30,.27,.26,C['leaf'],6,4)
            else:pots.ellipsoid(bx,by,bz,.48,.43,.34,C['leaf'],segments,rings)
            for j in range(5):
                angle2=rng.uniform(0,math.tau);d=rng.uniform(.14,.46)
                fz=bz+rng.uniform(.05,.32)
                fx,fy=bx+math.cos(angle2)*d,by+math.sin(angle2)*d
                if detail:
                    for petal in range(4):
                        a=angle2+petal*math.tau/4
                        pots.ellipsoid(fx+math.cos(a)*.09,fy+math.sin(a)*.08,fz+(petal%2)*.045,.078,.068,.06,C['gateBloom'],5,3)
                elif j%2==0:pots.ellipsoid(fx,fy,fz,.16,.14,.12,C['gateBloom'],segments,2)
    m.add_part('门前盆栽花境 · 黄绿前缘暗红色带与三角梅',pots)
    rails=Mesh()
    # Short white edging only at the flower front; no cage around the display.
    for i in range(59):
        px=x-4.55+i*.10;py=y-39.2;zz=ground(px,py)+.15
        rails.box(px,py,zz+.13,.052,.035,.26,C['roadWhite'])
    for z in [.06,.19]:
        for i in range(10):
            px=x-4.3+i*.56;py=y-39.2
            rails.box(px,py,ground(px,py)+.15+z,.56,.03,.028,C['roadWhite'])
    # Side-gate approaches remain open, per user direction. Only flower edging stays.
    m.add_part('盆栽前沿白色矮栅',rails)
    return m
