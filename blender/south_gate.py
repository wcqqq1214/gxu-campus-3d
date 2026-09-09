"""Current three-bay south gate: 2022 official, 2024 dated and 2026 reference photos.

Dimensions and unseen rear ornament are estimates. No geometry from the obsolete
freestanding-column gate is reused. Blender axes: east X, north Y, up Z.
"""
import math,random
from pathlib import Path
import bpy
from geometry import Mesh


def prism(m, outline, y, depth, mat):
    """Extrude an X/Z silhouette, preserving the open space below the arch."""
    front=[(x,y-depth/2,z) for x,z in outline]
    back=[(x,y+depth/2,z) for x,z in outline]
    m.face(front,mat);m.face(back[::-1],mat)
    for i in range(len(outline)):
        j=(i+1)%len(outline);m.face([front[i],back[i],back[j],front[j]],mat)


def inscription(text, x, y, z, width, height, mat, detail):
    """Self-contained raised glyph meshes; bundled OFL font, no runtime font fetch."""
    path=str(Path(__file__).parent/'fonts/MaShanZheng-Regular.ttf')
    font=bpy.data.fonts.get('MaShanZheng-Regular') or bpy.data.fonts.load(path)
    font.name='MaShanZheng-Regular'
    curve=bpy.data.curves.new('校名字形临时','FONT');curve.body=text;curve.font=font
    curve.size=1;curve.extrude=.012;curve.resolution_u=8 if detail else 3
    curve.bevel_depth=.002 if detail else 0;curve.bevel_resolution=1
    obj=bpy.data.objects.new('校名字形临时',curve);bpy.context.scene.collection.objects.link(obj)
    deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
    a=min(v.co.x for v in mesh.vertices);b=max(v.co.x for v in mesh.vertices)
    c=min(v.co.y for v in mesh.vertices);d=max(v.co.y for v in mesh.vertices)
    scale=min(width/(b-a),height/(d-c));m=Mesh()
    for face in mesh.polygons:
        # Text XY becomes the south-facing XZ plane, with extrusion toward south.
        m.face([(x+(mesh.vertices[i].co.x-(a+b)/2)*scale,
                 y-mesh.vertices[i].co.z*scale,
                 z+(mesh.vertices[i].co.y-(c+d)/2)*scale) for i in face.vertices],mat)
    evaluated.to_mesh_clear();bpy.data.objects.remove(obj,do_unlink=True);bpy.data.curves.remove(curve)
    return m


def pavilion(m,x,y,z,scale,C,detail):
    stone=C['gateStone'];trim=C['gateTrim'];s=scale
    for h,w,d in [(.10,1.55,1.55),(.27,1.32,1.32),(.43,1.08,1.08)]:
        m.box(x,y,z+h*s,w*s,d*s,.18*s,stone)
    for dx in [-.40,.40]:
        for dy in [-.40,.40]:m.box(x+dx*s,y+dy*s,z+1.0*s,.19*s,.19*s,1.0*s,stone)
    for sy in [-1,1]:
        m.box(x,y+sy*.40*s,z+1.47*s,1.0*s,.20*s,.22*s,trim)
        if detail:
            for side in [-1,1]:
                pts=[(x+side*(.27-.12*math.sin(t*math.pi/2))*s,z+(1.15+.23*t)*s) for t in [i/8 for i in range(9)]]
                for a,b in zip(pts,pts[1:]):m.line((a[0],y+sy*.41*s,a[1]),(b[0],y+sy*.41*s,b[1]),.035*s,trim,6)
    for sx in [-1,1]:m.box(x+sx*.40*s,y,z+1.47*s,.20*s,1.0*s,.22*s,trim)
    m.box(x,y,z+1.62*s,1.32*s,1.32*s,.17*s,trim)
    # Four slopes and a small ridge: roof silhouette visible in all recent photos.
    m.roof(x,y,z+1.71*s,1.38*s,1.38*s,.48*s,stone)


def panel(m,x,y,z,width,height,C,detail):
    stone=C['gateStone'];trim=C['gateTrim']
    m.box(x,y,z,width+.25,.10,height+.25,trim)
    m.box(x,y-.07,z,width,.06,height,C['gateRecess'])
    if not detail:return
    # Geometric relief study of the interlaced stone panel, not an exact carving scan.
    for row in range(int(height/.40)):
        zz=z-height/2+.24+row*.40
        for col in [-1,0,1]:
            xx=x+col*width*.28;rx=width*.135;rz=.20
            p=[(xx-rx,y-.13,zz),(xx,y-.13,zz+rz),(xx+rx,y-.13,zz),(xx,y-.13,zz-rz)]
            for a,b in zip(p,p[1:]+p[:1]):m.line(a,b,.035,stone,5)
    for dx in [-1,1]:m.box(x+dx*(width/2+.09),y-.1,z,.09,.12,height+.24,stone)


def south_gate(x,y,z,C,detail=True,footprint_width=66.65,footprint_depth=5.3):
    m=Mesh();stone=C['gateStone'];trim=C['gateTrim'];joint=C['gateJoint']
    # Four rectangular piers; centre opening is wider and higher than the side bays.
    for i,px in enumerate([-31,-16,16,31]):
        high=abs(px)==16;pw=4.2 if high else 3.4;ph=16.0 if high else 11.4
        part=Mesh();xx=x+px
        part.box(xx,y,z+.23,pw+1.2,5.3,.46,trim)
        part.box(xx,y,z+.58,pw+.7,4.7,.26,stone)
        part.box(xx,y,z+1.15,pw+.35,4.4,.88,stone)
        # Narrow recessed joints between actual stone courses.
        n=12 if high else 9;hh=(ph-1.6)/n
        for row in range(n):part.box(xx,y,z+1.6+(row+.5)*hh,pw,4.0,hh-.025,stone if row%3 else trim)
        for zz,ww,dd,hh in [(ph-3.0,pw+.5,4.5,.30),(ph-.30,pw+1.0,4.9,.40),(ph+.03,pw+1.25,5.1,.24)]:
            part.box(xx,y,z+zz,ww,dd,hh,trim)
        if high:
            # Rear repeats the structural panel; its exact ornament is inferred.
            front=Mesh();panel(front,xx,y-2.03,z+6.4,1.15,7.3,C,detail);part.extend(front)
            rear=Mesh();panel(rear,xx,y-2.03,z+6.4,1.15,7.3,C,detail);rear.rotate_z(xx,y,math.pi);part.extend(rear)
        elif detail:
            for sy in [-1,1]:
                for dx in [-.65,.65]:part.box(xx+dx,y+sy*2.03,z+4.9,.08,.08,5.9,joint)
                part.box(xx,y+sy*2.03,z+7.85,1.35,.08,.08,joint)
        for sy in [-1,1]:pavilion(part,xx,y+sy*1.20,z+ph+.20,1.05 if high else .83,C,detail)
        m.add_part(f'门柱-{i+1:02} · 石材分缝与顶部小亭',part)

    # Three genuinely open portals, with quadrant corner brackets and layered cornices.
    for name,cx,span,underside,top in [('中央门跨',0,27.8,11.3,15.85),('西侧门跨',-23.7,11.24,7.7,11.23),('东侧门跨',23.7,11.24,7.7,11.23)]:
        part=Mesh();xx=x+cx;radius=2.25 if cx==0 else 1.45
        part.box(xx,y,z+(underside+top)/2,span,3.35,top-underside,stone)
        for height,width,depth in [(underside+.10,.15,3.65),(underside+1.55,.32,3.85),(top,.36,3.95)]:
            part.box(xx,y,z+height,span+.18,depth,width,trim)
        for side in [-1,1]:
            edge=xx+side*span/2;center=edge-side*radius;spring=z+underside-radius
            arc=[(center+side*radius*math.cos(t*math.pi/2),spring+radius*math.sin(t*math.pi/2)) for t in [j/(28 if detail else 10) for j in range((28 if detail else 10)+1)]]
            prism(part,[(edge,z+underside)]+arc,y,3.35,stone)
            for sy in [-1,1]:
                for a,b in zip(arc,arc[1:]):part.line((a[0],y+sy*1.76,a[1]),(b[0],y+sy*1.76,b[1]),.075,trim,6)
        if detail:
            for sy in [-1,1]:
                # Repeating diagonal dentils below the cornice, visible on recent close views.
                for j in range(int(span/.22)):
                    xx0=xx-span/2+j*.22
                    part.line((xx0,y+sy*1.72,z+underside+1.76),(xx0+.16,y+sy*1.72,z+underside+2.01),.033,trim,5)
                for j in range(1,int(span/1.8)):
                    part.box(xx-span/2+j*1.8,y+sy*1.68,z+(underside+top)/2,.018,.022,top-underside-.4,joint)
        m.add_part(name+' · 弧形承托与叠檐',part)

    plaque=Mesh();plaque.box(x,y,z+14.64,14.6,3.9,3.20,trim)
    for sy in [-1,1]:
        plaque.box(x,y+sy*2.00,z+14.66,13.80,.12,2.72,C['gateRecess'])
        plaque.box(x,y+sy*2.08,z+14.66,13.53,.12,2.47,stone)
    plaque.box(x,y,z+16.33,15.3,4.50,.34,trim)
    prism(plaque,[(x-3.5,z+16.50),(x+3.5,z+16.50),(x,z+17.02)],y,3.6,stone)
    m.add_part('中央校名匾额 · 山花与嵌框',plaque)
    # Font is explicitly a substitute for the historical handwritten inscription.
    letters=inscription('广西大学',x,y-2.18,z+14.65,10.4,2.05,C['gateRed'],detail)
    m.add_part('南向红色立体校名 · 开源书法字体替代',letters)
    # Four-lobed rosettes either side of the plaque, kept as raised stone geometry.
    ornaments=Mesh()
    for sy in [-1,1]:
        for side in [-1,1]:
            for i in range(4):
                xx=x+side*(8.5+i*1.45);zz=z+14.50
                for a in range(4):
                    angle=a*math.pi/2;px=xx+math.cos(angle)*.15;pz=zz+math.sin(angle)*.15
                    points=[(px+.14*math.cos(t*math.tau/16),y+sy*1.75,pz+.14*math.sin(t*math.tau/16)) for t in range(17)]
                    for p,q in zip(points,points[1:]):ornaments.line(p,q,.035,trim,5)
    m.add_part('梁面四瓣石雕纹样',ornaments)
    # Low entrance islands, flower display and portable railings seen in 2024 / 2026.
    landscape=Mesh();landscape.box(x,y-13,z+.18,17.5,8.5,.30,C['path'])
    rng=random.Random(20261010)
    for row in range(3):
        for col in range(19 if detail else 10):
            count=19 if detail else 10;xx=x-7.9+col*15.8/(count-1);yy=y-15.5+row*2.1
            landscape.ellipsoid(xx,yy,z+.48,.54,.55,.38,C['leaf2'],8,4)
            if row==2:
                landscape.cylinder(xx,yy,z+.9,.065,1.2,C['bark'],6)
                for j in range(9 if detail else 3):
                    dx=rng.uniform(-.45,.45);dy=rng.uniform(-.4,.4);zz=z+rng.uniform(.85,1.55)
                    landscape.ellipsoid(xx+dx,yy+dy,zz,.27,.24,.25,C['gateFlower'] if j%3 else C['leaf'],7,4)
    if detail:
        for xx in [-8.8,8.8]:
            for j in range(22):
                landscape.box(x+xx,y-17+j*.38,z+.58,.10,.08,.85,trim)
            for zz in [.28,.68]:landscape.box(x+xx,y-13,z+zz,.08,8.5,.07,trim)
        for sy in [-1,1]:
            for j in range(46):landscape.box(x-8.7+j*.38,y-13+sy*4.2,z+.48,.10,.08,.65,trim)
    m.add_part('门前花坛与白色矮栏 · 近期照片示意配置',landscape)
    # Fit the actual mapped gate footprint. Vertical scale follows width (no exaggeration).
    sx=footprint_width/66.65;sy=footprint_depth/5.3
    # Mapped road surface is draped 0.40 m above the DEM; retain visible plinths.
    m.v=[(x+(a-x)*sx,y+(b-y)*sy,z+.45+(c-z)*sx) for a,b,c in m.v]
    return m
