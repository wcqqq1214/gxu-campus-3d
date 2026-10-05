"""Northern campus architecture from traced plans and dated photographs.

Visible features are reconstructed; all dimensions remain documented estimates.
Local U runs left-to-right on the principal facade; positive V points inward.
"""
import math
from geometry import Mesh


class Frame:
    def __init__(self,b):
        self.b=b;self.form=b['northForm'];f=self.form['frame']
        self.cx,self.cy=f['center'];self.ux,self.uy=f['u']
        self.u0,self.v0,self.u1,self.v1=f['bounds']
        self.w=self.u1-self.u0;self.d=self.v1-self.v0;self.z=b['elevation']
        self.angle=math.atan2(self.uy,self.ux)
        self.quad=None
        if self.form['kind']=='gym':
            points=list(b['polygons'][0][0][:-1])
            points.sort(key=lambda p:-(p[0]-self.cx)*self.uy+(p[1]-self.cy)*self.ux)
            along=lambda p:(p[0]-self.cx)*self.ux+(p[1]-self.cy)*self.uy
            self.quad=sorted(points[:2],key=along)+sorted(points[2:],key=along)
    def point(self,u,v,z):
        if self.quad:
            # Fit gables, windows and roof to the traced skew quadrilateral.
            # A rectangular envelope leaves floating windows at its corners.
            a=(u-self.u0)/self.w;b=(v-self.v0)/self.d
            weights=((1-a)*(1-b),a*(1-b),(1-a)*b,a*b)
            return (*[sum(p[i]*t for p,t in zip(self.quad,weights)) for i in (0,1)],self.z+z)
        return (self.cx+u*self.ux-v*self.uy,self.cy+u*self.uy+v*self.ux,self.z+z)
    def box(self,m,u,v,z,w,d,h,mat):
        if self.quad:
            pts=[self.point(u+du,v+dv,z+dz) for du,dv,dz in [(-w/2,-d/2,-h/2),(w/2,-d/2,-h/2),(w/2,d/2,-h/2),(-w/2,d/2,-h/2),(-w/2,-d/2,h/2),(w/2,-d/2,h/2),(w/2,d/2,h/2),(-w/2,d/2,h/2)]]
            for face in ((3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)):m.face([pts[i] for i in face],mat)
            return
        x,y,zz=self.point(u,v,z);m.box(x,y,zz,w,d,h,mat,self.angle)
    def face(self,m,pts,mat):m.face([self.point(*p) for p in pts],mat)
    def window(self,m,u,v,z,w,h,mat,back=False):
        pts=[(u-w/2,v,z),(u+w/2,v,z),(u+w/2,v,z+h),(u-w/2,v,z+h)]
        self.face(m,pts[::-1] if back else pts,mat)
    def letters(self,m,text,u,v,z,w,h,mat):
        from south_gate import inscription
        glyphs=inscription(text,u,v,z,w,h,mat,True)
        glyphs.v=[self.point(*p) for p in glyphs.v];m.extend(glyphs)


def building_model(b,c,detail=False):
    f=Frame(b);p=f.form;kind=p['kind'];result=Mesh()
    body,windows,trim,roof,entry=Mesh(),Mesh(),Mesh(),Mesh(),Mesh()
    h=p['bodyHeight'];white,gray,glass,dark=(c[k] for k in ('white','paleRoof','glass','dark'))
    for solid in p['solids']:
        body.extrude(solid['polygons'],solid['triangles'],f.z+solid['bottom'],
                     solid['top']-solid['bottom'],gray if kind=='teaching' and solid['top']<=3.8 else white,c['paleRoof'])
    if kind=='gym':
        count=40 if detail else 16
        rise=b['height']-h;um=(f.u0+f.u1)/2
        def crown(u):return h+rise*max(0,1-((u-um)/(f.w/2))**2)
        # Barrel vault with its long axis running east-west. The front is the
        # east gable facing the track, not the much larger blue-roof warehouse.
        for i in range(count):
            a=f.u0+f.w*i/count;bb=f.u0+f.w*(i+1)/count
            f.face(roof,[(a,f.v0,crown(a)),(a,f.v1,crown(a)),(bb,f.v1,crown(bb)),(bb,f.v0,crown(bb))][::-1],c['red'])
            for v,back in [(f.v0-.03,False),(f.v1+.03,True)]:
                pts=[(a,v,h),(bb,v,h),(bb,v,crown(bb)),(a,v,crown(a))]
                f.face(body,pts[::-1] if back else pts,white)
            if detail and i%2==0:
                a0=f.point(a,f.v0,crown(a)+.055);a1=f.point(a,f.v1,crown(a)+.055)
                roof.line(a0,a1,.035,c['metal'],4)
        # High paired window bands are visible in the 2024 official interior.
        for v,back in [(f.v0-.055,False),(f.v1+.055,True)]:
            for j in range(5):
                u=f.u0+f.w*(j+.5)/5
                for z in (1.2,5.4):
                    f.window(windows,u,v,z,f.w*.12,2.3,glass,back)
                    if detail:
                        for k in range(1,5):f.box(trim,u-f.w*.06+f.w*.12*k/5,v,z+1.15,.065,.12,2.3,white)
                        f.box(trim,u,v,z+1.15,f.w*.12,.12,.09,white)
        for side in (-1,1):
            u=f.u0-.045 if side<0 else f.u1+.045
            for i in range(14):
                v=f.v0+f.d*(i+.5)/14;span=f.d/14*.73
                f.face(windows,[(u,v-span/2,2.1),(u,v+span/2,2.1),(u,v+span/2,5.3),(u,v-span/2,5.3)][::side],glass)
                if detail:
                    for offset in (-span/4,0,span/4):f.box(trim,u,v+offset,3.7,.1,.08,3.2,white)
        # Ground plinth and eave fascia do not add an invented second storey.
        f.box(trim,0,f.v0-.07,.8,f.w,.14,1.6,gray)
        f.box(trim,0,f.v0-.09,3.95,f.w,.18,.3,white)
        if detail:f.letters(entry,'体育馆',0,f.v0-.13,11.9,f.w*.36,2.2,c['stone'])
    elif kind=='gallery':
        # Open galleries: daylight underneath and between the rails.
        floors=int(b['levels'])
        for level in range(1,floors+1):
            z=level*h/floors
            f.box(body,0,(f.v0+f.v1)/2,z,f.w,f.d,.28,white)
            for v in (f.v0+.2,f.v1-.2):
                f.box(trim,0,v,z+.63,f.w,.16,1.0,gray)
                f.box(trim,0,v,z+1.18,f.w,.12,.1,white)
        for u in (f.u0+.3,0,f.u1-.3):
            for v in (f.v0+.35,f.v1-.35):f.box(body,u,v,h/2,.48,.48,h,white)
    elif kind=='library':
        # The raised ends frame a recessed central portico, with four columns.
        middle=f.w*.54;v=f.v0-.055
        for level in range(3):
            z=12.1+level*2.85
            for j in range(6):
                u=(j-2.5)*middle/6
                f.window(windows,u,v,z,middle/6-.65,2.35,glass)
                if detail:
                    for dx in (-middle/24,0,middle/24):f.box(trim,u+dx,v-.035,z+1.175,.06,.08,2.35,c['metal'])
                    f.box(trim,u,v-.045,z+.8,middle/6-.65,.1,.12,white)
        for side in (-1,1):
            u=(f.u0+f.w*.115) if side<0 else (f.u1-f.w*.115)
            f.box(trim,u,v-.06,8.8,f.w*.23,.2,17.6,gray)
            f.window(windows,u,v-.18,19.7,f.w*.16,3.5,glass)
            f.box(roof,u,(f.v0+f.v1)/2,b['height']-.2,f.w*.25,f.d+1.6,.4,dark)
        f.box(roof,0,(f.v0+f.v1)/2,h+.12,f.w*.55,f.d+.9,.24,dark)
        f.window(windows,0,f.v0+4.95,4,middle,6.15,glass)
        # Raised landing joins the final tread to the recessed entrance.
        f.box(entry,0,f.v0+2.5,2,middle,5,4,c['stone'])
        for u in (-middle*.46,-middle*.16,middle*.16,middle*.46):
            f.box(entry,u,f.v0+.7,7.1,.75,.8,6.2,dark)
        f.box(entry,0,f.v0+2.5,10.1,middle+1,5,.42,white)
        # 32 treads preserve the same silhouette in both LODs.
        rise=p['entry']['rise'];depth=p['entry']['depth'];steps=32
        profile=[(f.v0-depth,0)]
        def stair_width(v):return middle+(f.w*.90-middle)*(f.v0-v)/depth
        for i in range(steps):
            hh=rise*(i+1)/steps;start=f.v0-depth+i*depth/steps
            end=start+depth/steps;prev=rise*i/steps
            wa,wb=stair_width(start)/2,stair_width(end)/2
            f.face(entry,[(-wa,start,hh),(wa,start,hh),(wb,end,hh),(-wb,end,hh)],c['stone'])
            f.face(entry,[(-wa,start,prev),(wa,start,prev),(wa,start,hh),(-wa,start,hh)],c['stone'])
            profile.extend([(start,hh),(end,hh)])
        profile.append((f.v0,0))
        # Only the exposed stepped envelope, without 32 nested hidden boxes.
        for side,reverse in [(-1,False),(1,True)]:
            pts=[(side*stair_width(v)/2,v,z) for v,z in profile]
            f.face(entry,pts[::-1] if reverse else pts,c['stone'])
        for side in (-1,1):
            for i in range(8):
                hh=rise*(i+1)/8;v0=f.v0-depth+i*depth/8
                f.box(entry,side*(stair_width(v0+depth/16)/2+.55),v0+depth/16,hh/2+.35,1.1,depth/8,hh+.7,white)
        if detail:f.letters(entry,'图书馆',0,f.v0-.1,11,middle*.6,1.45,c['stone'])
        # Rear and side elevations lack confirmed photographs; retain simple
        # window grids rather than copying the ceremonial front onto all faces.
        for level in range(5):
            z=1.2+level*3.7
            columns=10 if detail else 5
            for j in range(columns):
                f.window(windows,f.u0+f.w*(j+.5)/columns,f.v1+.04,z,f.w/columns*.72,2.1,glass,True)
        for u,reverse in [(f.u0-.04,True),(f.u1+.04,False)]:
            for level in range(5):
                for j in range(5):
                    v=f.v0+f.d*(j+.5)/5;z=1.2+level*3.7
                    pts=[(u,v-2,z),(u,v+2,z),(u,v+2,z+2.1),(u,v-2,z+2.1)]
                    f.face(windows,pts[::-1] if reverse else pts,glass)
    else:
        levels=int(b['levels']);floor=h/levels;count=max(4,round(f.w/(5.4 if detail else 21.6)))
        gap=p.get('portalWidth',0);stair=p.get('openStair');stair_u=stair['centerFraction']*f.w if stair else None
        for v,back in [(f.v0-.04,False),(f.v1+.04,True)]:
            for level in range(levels):
                z=level*floor+1.0
                for j in range(count):
                    u=f.u0+f.w*(j+.5)/count;ww=f.w/count*.76
                    if (level==0 and abs(u)<gap/2+ww/2) or (stair and not back and abs(u-stair_u)<stair['width']/2+ww/2):continue
                    f.window(windows,u,v,z,ww,floor*.62,glass,back)
                    if detail:
                        f.box(trim,u,v,z+floor*.27,ww,.1,.11,white)
                        for dx in (-ww*.25,0,ww*.25):f.box(trim,u+dx,v,z+floor*.31,.065,.1,floor*.62,c['metal'])
                # White floor rails repeat the photo's structural grid; the
                # ground-level opening stays open, including its soffit.
                if detail and level>0 and not (stair and not back):f.box(trim,0,v,level*floor+.15,f.w-3,.22,.3,white)
            if gap:
                for side in (-1,1):f.box(entry,side*(gap/2+.4),v-.2,1.9,.6,.6,3.8,white)
                f.box(entry,0,v-.35,3.9,gap+1.4,.8,.3,gray)
        if p.get('portalCeiling'):
            # It is a convex rectangular slice of this wing's footprint.
            body.face([(x,y,f.z+3.8) for x,y in p['portalCeiling'][:-1]][::-1],white)
        for solid in p['solids']:
            if solid['name'].startswith('屋面高起'):
                for poly in solid['polygons']:
                    ring=poly[0]
                    roof.face([(x,y,f.z+b['height']) for x,y in ring[:-1]],dark)
                    for a,bb in zip(ring,ring[1:]):
                        roof.face([(a[0],a[1],f.z+b['height']-.45),(bb[0],bb[1],f.z+b['height']-.45),(bb[0],bb[1],f.z+b['height']),(a[0],a[1],f.z+b['height'])],dark)
        if stair:
            # Alternating two-flight stair, visible in the historical second
            # teaching building photograph; position and step sizes estimated.
            sw=stair['width'];run=sw-.4;depth=3.5
            for level in range(levels-1):
                z0=level*floor
                for flight in range(2):
                    for i in range(12 if detail else 0):
                        t=(i+.5)/12;u=stair_u+(-run/2+run*t)*(1 if flight==0 else -1)
                        z=z0+(flight+i/12)*floor/2
                        f.box(entry,u,f.v0+.9+flight*1.7,z,run/12+.03,1.55,.16,white)
                    if not detail:
                        # A continuous flight preserves the stair envelope at
                        # distance; individual tread nosings load in near LOD.
                        ua,ub=stair_u-run/2,stair_u+run/2
                        za,zb=z0+flight*floor/2,z0+(flight+1)*floor/2
                        if flight:za,zb=zb,za
                        va=f.v0+.13+flight*1.7;vb=va+1.55
                        f.face(entry,[(ua,va,za),(ub,va,zb),(ub,vb,zb),(ua,vb,za)],white)
                    a=f.point(stair_u-run/2,f.v0+.16+flight*1.7,z0+flight*floor/2+1)
                    bb=f.point(stair_u+run/2,f.v0+.16+flight*1.7,z0+(flight+1)*floor/2+1)
                    if flight==1:a,bb=f.point(stair_u+run/2,f.v0+1.86,z0+floor/2+1),f.point(stair_u-run/2,f.v0+1.86,z0+floor+1)
                    if detail:entry.line(a,bb,.065,c['metal'],4)
            f.box(entry,stair_u,f.v0+depth,h+.12,sw,.4,.25,white)
    for label,mesh in [('主体与真实门洞',body),('门窗分格（照片约束及估算）',windows),('立面框格与灰色基座',trim),('分段檐顶与曲面屋顶',roof),('入口台阶与开放连廊',entry)]:
        result.add_part(label,mesh)
    return result
