"""Shared visible surfaces and grading planes for the lower entrance landscape."""
import math
from geometry import Mesh, MATERIALS


def _split_finish(polygon, boundary):
    """Partition a sloping polygon into a convex inlay and disjoint remainder."""
    if any(max(p[i] for p in polygon)<=min(p[i] for p in boundary)+1e-9 or
           min(p[i] for p in polygon)>=max(p[i] for p in boundary)-1e-9 for i in (0,1)):
        return [],[polygon]
    result=polygon;outside=[]
    def valid(poly):
        return len(poly)>=3 and abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(poly,poly[1:]+poly[:1])))>1e-10
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):
        output=[];remainder=[]
        def distance(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        for p,q in zip(result,result[1:]+result[:1]):
            dp,dq=distance(p),distance(q)
            if dp>=-1e-9:output.append(p)
            if dp<=1e-9:remainder.append(p)
            if (dp>1e-9 and dq<-1e-9) or (dp<-1e-9 and dq>1e-9):
                t=dp/(dp-dq);crossing=[p[i]+t*(q[i]-p[i]) for i in range(3)]
                output.append(crossing);remainder.append(crossing)
        if valid(remainder):outside.append(remainder)
        result=output
        if not valid(result):return [],outside
    return result,outside


def _conform_finishes(finishes):
    """Close T junctions left by patch grading and stone-inlay partitions."""
    vertices={tuple(round(v,9) for v in p):p for poly,_,_ in finishes for p in poly}
    for polygon,material,course in finishes:
        ring=[]
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            delta=[b[i]-a[i] for i in range(3)];length2=sum(v*v for v in delta)
            if length2<1e-16:continue
            stations=[(0,a)]
            for p in vertices.values():
                t=sum((p[i]-a[i])*delta[i] for i in range(3))/length2
                if 1e-7<t<1-1e-7 and sum((a[i]+t*delta[i]-p[i])**2 for i in range(3))<1e-14:
                    stations.append((t,p))
            ring.extend(p for _,p in sorted(stations,key=lambda v:v[0]))
        if len(ring)==len(polygon):
            yield polygon,material,course
        else:
            # A centre fan retains inserted collinear boundary vertices when
            # Blender tessellates the face; an ngon may discard those points.
            centre=[sum(p[i] for p in polygon)/len(polygon) for i in range(3)]
            for a,b in zip(ring,ring[1:]+ring[:1]):
                yield [centre,a,b],material,course


def _parking_margins(patch):
    if not patch['id'].endswith('parking'):return []
    side=-1 if patch['id'].startswith('north') else 1
    rear=max(abs(w) for w,d,_ in patch['vertices'] if abs(d+.3)<1e-6)
    # The rear joint narrows to a finite mouth at the north lane. South meets
    # the existing stone access paving, which needs no second finish layer.
    end=rear-.7 if side<0 else rear
    # A short 6 cm nose avoids a needle-like zero-width end. The flush
    # margin begins along the shoulder wall, before its terrace return,
    # and widens over 80 cm. It stays flush across that wall transition.
    rear_strip=([(16,-.46),(end,-.46),(rear,-.36),(rear,-.3),(16,-.3)]
                if side<0 else [(16,-.46),(rear,-.46),(rear,-.3),(16,-.3)])
    strips=[[(16,-8.8),(16.06,-8.8),(16.18,-8.4),(16.24,-8.0),(16.24,-.46),(16,-.46)],
            rear_strip,
            [(16.24,-.81),(16.59,-.46),(16.24,-.46)]]
    result=[]
    for strip in strips:
        boundary=[(side*w,d) for w,d in strip]
        if side<0:boundary.reverse()
        result.append(boundary)
    return result


def _parking_grass(patch):
    """Conform rear approach cells to paving triangles across grade breaks."""
    vs=patch['vertices'];ts=patch['triangles']
    w0=-20.7 if patch['id'].startswith('north') else 16.5
    for i in range(7):
        # Only the last 10 m have the rear grading transitions being refined.
        for j in range(14,28):
            w=w0+i*.6;d=-19+j*.65
            cell=[(w,d),(w+.28,d),(w+.28,d+.28),(w,d+.28)]
            # A minimal lift prevents coplanar flicker. Ease from the front
            # cells' 8 mm to 4 mm so rear cells read as part of the paving.
            lift=.008-.004*min(1,max(0,(d+9.9)/1.3))
            for k in range(0,len(ts),3):
                triangle=[vs[index] for index in ts[k:k+3]]
                inside,_=_split_finish(triangle,cell)
                if inside:yield [(ww,dd,h+lift) for ww,dd,h in inside]


def _parking_paving_uv(patch,points):
    # The existing texture has two columns and four rows per repeat.
    # Centre those joints in the solid webs between the 0.28 m grass cells,
    # rather than running the campus-wide 2 x 1 m slab grid through them.
    w0=-20.7 if patch['id'].startswith('north') else 16.5
    return [((w-w0+.16)/1.2,(d+19.185)/2.6) for w,d,_ in points]


def _parking_margin_uv(patch,points,course):
    # One stone across each narrow margin, with transverse joints matching
    # the adjacent grass-paver rhythm. The bevel is a single cut stone.
    w0=-20.7 if patch['id'].startswith('north') else 16.5
    if course==0:
        # The regular grid starts a joint 15 mm after the tapered nose.
        # Absorb that sliver into the first cut stone; the following rows
        # retain the grass-paver rhythm. Shared corners receive identical UVs.
        return [((abs(w)-16)/.48,max(4.,(d+19.185)/2.6)) for w,d,_ in points]
    if course==1:
        return [((w-w0+.16)/1.2,(d+.46)/.64) for w,d,_ in points]
    return [(.05+(abs(w)-16.24),.03+(d+.81)*.16/.35) for w,d,_ in points]


def landscape_mesh(entry,z,C):
    p=entry['recessedStairEntry'];c=p['landscape'];a=math.radians(entry['bearing']);nx,ny=math.sin(a),math.cos(a);x,y=entry['center']
    mesh=Mesh();grading=Mesh();masks=[]
    # Keep this small UV domain in its own primitive: campus-wide stone UVs
    # quantize too coarsely for narrow courses. Reuse the same stone finish.
    if "entryBorderStone" not in C:
        material=MATERIALS[C["stone"]].copy();material.name="entryBorderStone"
        C["entryBorderStone"]=len(MATERIALS);MATERIALS.append(material)
    def point(w,d,h):return (x+ny*w-nx*d,y-nx*w-ny*d,z+h)
    def box(w,d,h,width,depth,height,mat='stone'):
        mesh.box(*point(w,d,h),width,depth,height,C[mat],-a)
    def face(points,mat='stone',grade=True,uvs=None):
        coords=[point(*v) for v in points]
        # W,D has the opposite handedness to world X,Y.
        if sum(v[0]*q[1]-q[0]*v[1] for v,q in zip(coords,coords[1:]+coords[:1]))<0:
            coords.reverse()
            if uvs is not None:uvs=list(reversed(uvs))
        mesh.face(coords,C[mat],uvs)
        if grade:grading.face(coords,C['grass'])
    def plane(w0,w1,d0,d1,h):
        face([(w0,d0,h),(w1,d0,h),(w1,d1,h),(w0,d1,h)])
        masks.append([(w0,d0),(w1,d0),(w1,d1),(w0,d1)])
    def wall(w0,d0,w1,d1,top,bottom):
        if w0==w1:box(w0,(d0+d1)/2,(top+bottom)/2,.22,abs(d1-d0),top-bottom)
        else:box((w0+w1)/2,d0,(top+bottom)/2,abs(w1-w0),.22,top-bottom)
    def rail(w0,d0,w1,d1,h0,h1,glazed=True):
        from entry_guardrails import guard
        guard(mesh,point,box,C,w0,d0,w1,d1,h0,h1,glazed=glazed)
    def tread(w0,w1,d0,d1,top,bottom):
        box((w0+w1)/2,(d0+d1)/2,(top+bottom)/2,w1-w0,d1-d0,top-bottom)
        # The identical top surface drives terrain contact, but is not duplicated visually.
        coords=[point(w0,d1,top),point(w1,d1,top),point(w1,d0,top),point(w0,d0,top)]
        grading.face(coords,C['grass']);masks.append([(w0,d0),(w1,d0),(w1,d1),(w0,d1)])
    lower=c['lowerFlight'];start=p['apronStart'];toe=lower['toe'];base=lower['baseHeight'];tw=c['terraceWidth'];pw=p['platformWidth'];top=p['baseHeight'];heights=p['apronFrontHeights'];fw=p['apronFrontWidth']
    # Low approach, an additional broad flight, then the raised transverse landing.
    for i in range(len(heights)-1):
        wa=fw*(i/(len(heights)-1)-.5);wb=fw*((i+1)/(len(heights)-1)-.5)
        ia=lower['width']*(i/(len(heights)-1)-.5);ib=lower['width']*((i+1)/(len(heights)-1)-.5)
        face([(wa,start,heights[i]),(wb,start,heights[i+1]),(ib,toe,base)])
        face([(wa,start,heights[i]),(ib,toe,base),(ia,toe,base)])
    masks.append([(-fw/2,start),(fw/2,start),(lower['width']/2,toe),(-lower['width']/2,toe)])
    for i in range(lower['risers']-1):
        d=toe+i*lower['tread'];h=base+(top-base)*(i+1)/lower['risers']
        tread(-lower['width']/2,lower['width']/2,d,d+lower['tread'],h,base-.2)
    end=c['lowerEnd'];court=c['court'];back=court['back'];outer=court['outerWidth']/2;floor=court['floorHeight'];front=p['toe'];sw=court['stairWidth']
    tread(-tw/2,tw/2,end,front,top,-.2)
    for side in (-1,1):
        # Raised outer walk; the middle remains an actual excavated lightwell.
        lo,hi=sorted((side*outer,side*tw/2));tread(lo,hi,front,back,top,-.2)
        lo,hi=sorted((side*pw/2,side*outer));plane(lo,hi,front,back,floor)
        # Stairs descend along the outside edge, leaving a full lower landing.
        stair_w=side*(outer-sw/2-.25);rise=(top-floor)/court['risers']
        for i in range(court['risers']-1):
            d=front+i*court['tread'];h=top-rise*(i+1)
            tread(stair_w-sw/2,stair_w+sw/2,d,d+court['tread'],h,floor-.15)
        wall(side*outer,front,side*outer,back,top,floor-.2)
        wall(side*pw/2,back,side*outer,back,top,floor-.2)
        rail(side*outer,front,side*outer,back,top,top)
        rail(side*tw/2,end,side*tw/2,back,top,top)
        rail(side*pw/2,back,side*outer,back,top,top)
        # The transverse guard stops at the descending stair opening.
        rail(side*pw/2,front,stair_w-side*sw/2,front,top,top)
        # Both handrails follow the descending flight; the level court
        # guard on the retaining wall is not a stair handrail.
        stair_end=front+(court['risers']-1)*court['tread']
        for edge in (stair_w-side*sw/2,stair_w+side*sw/2):
            rail(edge,front,edge,stair_end,top-rise,floor+rise,False)
        # Light stone coping separates the raised pedestrian walk from
        # the parking surface outside, without adding a vehicle crossing.
        box(side*tw/2,(end+back)/2,top,.30,back-end,.12,'stone')
        # Stone face of the broad terrace and guard beside the lower flight.
        wall(side*lower['width']/2,end,side*tw/2,end,top,base-.2)
        rail(side*lower['width']/2,end,side*tw/2,end,top,top)
        rail(side*(lower['width']/2-.12),toe,side*(lower['width']/2-.12),end,base+rise,top)
    for patch in c['groundPatches']:
        vs=patch['vertices'];ts=patch['triangles']
        margins=_parking_margins(patch);finishes=[]
        for k in range(0,len(ts),3):
            pts=[vs[i] for i in ts[k:k+3]]
            # Split the visible finish itself: inlay and paving share exact
            # edge coordinates and heights, with no stacked coplanar faces.
            remaining=[pts]
            for course,boundary in enumerate(margins):
                rest=[]
                for polygon in remaining:
                    inside,outside=_split_finish(polygon,boundary)
                    if inside:finishes.append((inside,'entryBorderStone',course))
                    rest.extend(outside)
                remaining=rest
            finishes.extend((polygon,patch['material'],None) for polygon in remaining)
            coords=[point(*v) for v in pts]
            if sum(v[0]*q[1]-q[0]*v[1] for v,q in zip(coords,coords[1:]+coords[:1]))<0:coords.reverse()
            grading.face(coords,C['grass']);masks.append([v[:2] for v in pts])
        for polygon,material,course in (_conform_finishes(finishes) if margins else finishes):
            uvs=(_parking_margin_uv(patch,polygon,course) if course is not None else
                 _parking_paving_uv(patch,polygon) if margins else None)
            face(polygon,material,grade=False,uvs=uvs)
        def height(w,d):
            for k in range(0,len(ts),3):
                a,b,c=[vs[i] for i in ts[k:k+3]]
                den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                if abs(den)<1e-12:continue
                u=((b[1]-c[1])*(w-c[0])+(c[0]-b[0])*(d-c[1]))/den
                v=((c[1]-a[1])*(w-c[0])+(a[0]-c[0])*(d-c[1]))/den
                if min(u,v,1-u-v)>=-1e-6:return u*a[2]+v*b[2]+(1-u-v)*c[2]
            raise ValueError('Paver detail outside its sampled parking patch')
        # A shallow paving edge meets the graded soil bedding. Only the
        # raised terrace/courtyard uses retaining walls; the outer plaza does
        # not sit on a deep stone plinth. Shared patch joins stay open.
        ring=patch['boundary']
        for a,b in zip(ring,ring[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
            stations={0.,1.}
            for w,d,_ in vs:
                t=((w-a[0])*dx+(d-a[1])*dy)/length2
                if 0<t<1 and abs((w-a[0])*dy-(d-a[1])*dx)<1e-6:stations.add(t)
            if abs(dx)<1e-7 and min(a[1],b[1])<-20<max(a[1],b[1]):stations.add((-20-a[1])/dy)
            values=sorted(stations)
            for ta,tb in zip(values,values[1:]):
                w=a[0]+dx*(ta+tb)/2;d=a[1]+dy*(ta+tb)/2
                exposed=(patch['id']=='outer-plaza' and (abs(d+24)<1e-6 or abs(abs(w)-16)<1e-6 and d<-20))
                exposed|=('parking' in patch['id'] or patch['id']=='south-access') and (abs(d+20)<1e-6 or abs(d+.3)<1e-6)
                if not exposed:continue
                wa,da=a[0]+dx*ta,a[1]+dy*ta;wb,db=a[0]+dx*tb,a[1]+dy*tb
                ha,hb=height(wa,da),height(wb,db)
                edge_uvs=None;edge_material=patch['material']
                if patch['id'].endswith('parking'):
                    # Carry the same joints down the shallow road-facing edge.
                    # Keeping this local also avoids a huge UV range that
                    # wastes the exported texture-coordinate precision.
                    if abs(d+.3)<1e-6:
                        edge_material='entryBorderStone'
                        ua,ub=_parking_margin_uv(patch,[(wa,da,ha),(wb,db,hb)],1)
                        # Unfold the stone course over its shallow outer edge.
                        edge_uvs=[(ua[0],ua[1]+.08/.64),(ub[0],ub[1]+.08/.64),ub,ua]
                    else:
                        ua,ub=_parking_paving_uv(patch,[(wa,da,ha),(wb,db,hb)])
                        edge_uvs=[(ua[0],ua[1]-.08/2.6),(ub[0],ub[1]-.08/2.6),ub,ua]
                mesh.face([point(wa,da,ha-.08),point(wb,db,hb-.08),point(wb,db,hb),point(wa,da,ha)],C[edge_material],edge_uvs)
        if 'shoulder' in patch['id']:
            # The sloping shoulder needs a real stone retaining face.
            ring=patch['boundary']
            for a,b in zip(ring,ring[1:]):
                if abs(a[0]-b[0])<1e-7:
                    mesh.face([point(*a,-.2),point(*b,-.2),point(*b,height(*b)),point(*a,height(*a))],C['stone'])
        if patch['id'].endswith('parking'):
            # Repeated grass cells identify permeable parking paving. These
            # are a material pattern, not surveyed stalls or parked vehicles.
            w0=-20.7 if patch['id'].startswith('north') else 16.5
            for i in range(7):
                for j in range(14):
                    w=w0+i*.6;d=-19+j*.65
                    face([(ww,dd,height(ww,dd)+.008) for ww,dd in
                          [(w,d),(w+.28,d),(w+.28,d+.28),(w,d+.28)]],'green',grade=False)
            for polygon in _parking_grass(patch):face(polygon,'green',grade=False)
    return mesh,grading,masks
