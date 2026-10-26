"""Photo-based Xindongyuan gate, reviewed 2026-10-26.

2025-11-08 Douyin photo: silver fins, tall west guardroom, horizontal lintel,
ringed east pier, gold bilingual name. September 2026 route footage: blue arched
canopy beside East 25, card readers and brick paving. Dimensions and unseen rear
faces are estimates, not a survey. Sources are recorded in data/sources.json.
"""
import math
import random
from pathlib import Path
import bpy
import geometry
from geometry import Mesh
from south_gate import gate_wordmark

DECK = .16  # campus_gate adds catalogue elevation + .24; matches the nearby road.


def ensure_materials(C):
    for name, rgb, rough, metal in [
        ('newEastSilver',(.62,.66,.67),.48,.35),
        ('newEastAgedSilver',(.32,.31,.27),.72,.20),
        ('newEastBaseSilver',(.45,.47,.44),.76,.25),
        ('newEastRecess',(.15,.18,.19),.72,.18),
        ('newEastGold',(.68,.45,.13),.30,.52),
        ('newEastStone',(.63,.64,.61),.85,0),
        ('newEastGlass',(.055,.10,.105),.26,.22),
        ('newEastFrame',(.065,.075,.075),.42,.3),
        ('newEastWindowFrame',(.12,.135,.13),.38,.35),
        ('newEastBlue',(.035,.18,.34),.6,.2),
        ('newEastCanopyBlue',(.025,.11,.22),.65,.12),
        ('newEastBrick',(.34,.30,.28),.95,0),
        ('newEastBrickLight',(.38,.34,.32),.95,0),
        ('newEastBrickDark',(.30,.27,.25),.95,0),
        ('newEastMortar',(.20,.21,.20),1,0),
        ('newEastYellow',(.78,.46,.055),.65,.12),
        ('newEastBarrierWhite',(.76,.77,.73),.65,0),
        ('newEastBarrierRed',(.48,.055,.035),.64,0),
        ('newEastRubber',(.035,.04,.04),.94,0),
        ('newEastWall',(.49,.49,.44),.94,0),
        ('newEastWallCap',(.53,.54,.50),.88,0),
        ('newEastSoil',(.075,.06,.04),1,0),
        ('newEastLeaf',(.035,.09,.028),.98,0),
        ('newEastLeafLight',(.065,.145,.045),.98,0),
        ('newEastLeafTips',(.10,.20,.055),.96,0),
    ]:
        if name not in C:
            existing=bpy.data.materials.get(name)
            if existing:
                C[name]=len(geometry.MATERIALS);geometry.MATERIALS.append(existing)
            else:C[name]=geometry.material(name,rgb,rough,metal)
        # Refresh this gate's dedicated finishes on incremental rebuilds too.
        mat=geometry.MATERIALS[C[name]]
        mat.diffuse_color=(*rgb,1)
        bs=mat.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value=(*rgb,1)
        bs.inputs['Roughness'].default_value=rough
        bs.inputs['Metallic'].default_value=metal
    # Original, deterministic grain: no reference photograph is redistributed.
    # Embed it in the editable source and both GLBs; no runtime image request.
    mat=geometry.MATERIALS[C['newEastStone']]
    name='新东园门_自制细砂纹理_128'
    grain=bpy.data.images.get(name)
    if grain is None:
        grain=bpy.data.images.new(name,width=128,height=128)
        base=[1.055*v**(1/2.4)-.055 for v in (.63,.64,.61)]
        rng=random.Random('new-east-fine-grain-v1');pixels=[]
        for _ in range(128*128):
            shade=rng.uniform(.93,1.045)
            if rng.random()<.065:shade*=.82
            pixels.extend([min(1,v*shade) for v in base]+[1])
        grain.pixels.foreach_set(pixels);grain.file_format='PNG';grain.pack()
    node=mat.node_tree.nodes.get('new-east-stone-grain')
    if node is None:
        node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.name='new-east-stone-grain'
    node.image=grain;node.extension='REPEAT'
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])


def solid(m, ring, bottom, top, mat):
    """Extrude a convex XY footprint."""
    m.face([(x,y,bottom) for x,y in reversed(ring)],mat)
    m.face([(x,y,top) for x,y in ring],mat)
    for (x,y),(a,b) in zip(ring,ring[1:]+ring[:1]):
        m.face([(x,y,bottom),(a,b,bottom),(a,b,top),(x,y,top)],mat)


def rounded_ring(x,y,w,d,r,n=8):
    ring=[]
    for cx,cy,start in [(x+w/2-r,y+d/2-r,0),(x-w/2+r,y+d/2-r,90),
                        (x-w/2+r,y-d/2+r,180),(x+w/2-r,y-d/2+r,270)]:
        for j in range(n+1):
            a=math.radians(start+j*90/n);ring.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return ring


def metal_fin(m,x,y,bottom,top,width,depth,angle,mat):
    """Small folded edges catch light on the narrow metal blades."""
    w,d=width/2,depth/2;e=.007
    ring=[(-w+e,-d),(w-e,-d),(w,-d+e),(w,d-e),
          (w-e,d),(-w+e,d),(-w,d-e),(-w,-d+e)]
    c,s=math.cos(angle),math.sin(angle)
    solid(m,[(x+a*c-b*s,y+a*s+b*c) for a,b in ring],bottom,top,mat)


def beveled_sill(m,bottom,top,C):
    lower=rounded_ring(-6.05,.4,3.52,2.92,.71)
    upper=rounded_ring(-6.05,.4,3.46,2.86,.68)
    solid(m,lower,bottom,top-.025,C['newEastSilver'])
    for i in range(len(lower)):
        j=(i+1)%len(lower)
        m.face([(*lower[i],top-.025),(*lower[j],top-.025),
                (*upper[j],top),(*upper[i],top)],C['newEastSilver'])
    m.face([(*p,top) for p in upper],C['newEastSilver'])


def vertical_fins(m,ring,bottom,top,C,base_band=False):
    # Sample by distance so curved returns have the same rhythm as the frontage.
    segments=[(a,b,math.dist(a,b)) for a,b in zip(ring,ring[1:]+ring[:1])]
    perimeter=sum(length for _,_,length in segments)
    count=round(perimeter/.17);step=perimeter/count
    index=0;offset=0
    for j in range(count):
        distance=(j+.5)*step
        while distance>offset+segments[index][2]:
            offset+=segments[index][2];index+=1
        (x,y),(a,b),length=segments[index];t=(distance-offset)/length
        finish='newEastSilver'
        if base_band:
            # The booth's low cladding is darker and uneven in the front photo.
            # Keep this subtle variation below the sill, without random rebuilds.
            finish='newEastAgedSilver' if j%13 in (2,8,11) else 'newEastBaseSilver'
        metal_fin(m,x+(a-x)*t,y+(b-y)*t,bottom,top,.075,.14,
                  math.atan2(b-y,a-x),C[finish])


def paving(m,C,detail):
    p=Mesh()
    finish=C['newEastMortar'] if detail else C['newEastBrick']
    for x,y,w,d in [(-4.9,.65,3.7,5.7),(6.55,0,2.8,4.6)]:
        p.box(x,y,(DECK-.52)/2,w,d,DECK+.52,finish if x>0 else C['newEastBrick'])
    # Solid, gentle end transitions rather than thin pads hovering over terrain.
    for y0,y1,z0,z1 in [(-4,-2.3,-.36,DECK),(2.3,4,DECK,-.36)]:
        a,b=5.15,7.95
        p.face([(a,y0,z0),(b,y0,z0),(b,y1,z1),(a,y1,z1)],finish)
        for x in (a,b):p.face([(x,y0,-.52),(x,y1,-.52),(x,y1,z1),(x,y0,z0)],C['stone'])
        for y,z in [(y0,z0),(y1,z1)]:p.face([(a,y,-.52),(b,y,-.52),(b,y,z),(a,y,z)],C['stone'])
    if detail:
        # Long, staggered pavers run along the pedestrian route in the video.
        # Clip rows at the ramp breaks so the finish follows the grounded slab.
        def level(y):
            return DECK if abs(y)<=2.3 else DECK-(abs(y)-2.3)*.52/1.7
        tones=['newEastBrick','newEastBrick','newEastBrick','newEastBrickLight','newEastBrickDark']
        for i in range(14):
            x0=5.15+i*.20+.005;x1=x0+.19
            for j in range(-1,21):
                y0=max(-4,-4+j*.40+(i%2)*.20+.005)
                y1=min(4,-4+(j+1)*.40+(i%2)*.20-.005)
                if y1<=y0:continue
                cuts=[y0]+[y for y in [-2.3,2.3] if y0<y<y1]+[y1]
                mat=C[tones[(i*17+j*7)%len(tones)]]
                for a,b in zip(cuts,cuts[1:]):
                    p.face([(x0,a,level(a)+.004),(x1,a,level(a)+.004),
                            (x1,b,level(b)+.004),(x0,b,level(b)+.004)],mat)
    m.add_part('01_砖铺地与接地基础_高程估算',p)


def guardroom(m,C,detail):
    p=Mesh();ring=rounded_ring(-6.05,.4,3.4,2.8,.65)
    # The booth is integrated into the west tower, not a separate portable shed.
    solid(p,ring,DECK,DECK+.75,C['newEastRecess'])
    solid(p,ring,DECK+2.35,DECK+6.9,C['newEastRecess'])
    solid(p,ring,DECK+8.05,DECK+9.4,C['newEastRecess'])
    solid(p,ring,DECK+9.4,DECK+9.44,C['newEastSilver'])
    for x in [-7.5,-4.6]:
        post=rounded_ring(x,.4,.4,2.8,.06,3)
        solid(p,post,DECK+6.9,DECK+8.05,C['newEastRecess'])
        vertical_fins(p,post,DECK+6.9,DECK+8.05,C)
    for lo,hi in [(DECK,DECK+.75),(DECK+2.35,DECK+6.9),(DECK+8.05,DECK+9.4)]:
        vertical_fins(p,ring,lo,hi,C,base_band=lo==DECK)
    # A continuous inset band closes the corner gaps between the flat panes.
    # Opaque dark glazing suggests reflections without inventing an interior.
    solid(p,rounded_ring(-6.05,.4,3.24,2.68,.60),DECK+.79,DECK+2.35,C['newEastGlass'])
    for x in [-7.35,-6.5,-5.65,-4.75]:p.box(x,-.99,DECK+1.55,.045,.07,1.65,C['newEastFrame'])
    for z in [.80,2.31]:p.box(-6.05,-.99,DECK+z,2.7,.08,.045,C['newEastFrame'])
    for y in [-.3,.5,1.3]:p.box(-4.34,y,DECK+1.55,.09,.045,1.65,C['newEastFrame'])
    # Horizontal meeting rails and the lane-facing return are visible in the
    # frontal reference. Their exact section and joint heights are estimates.
    p.box(-6.05,-1.01,DECK+1.32,2.70,.07,.045,C['newEastWindowFrame'])
    p.box(-4.355,.4,DECK+1.32,.07,1.55,.045,C['newEastWindowFrame'])
    p.box(-6.05,1.76,DECK+1.55,2.6,.10,1.6,C['newEastRecess'])
    # The 2025 inside view shows a narrow dark doorway on the lane side of
    # the booth's rear. Show a closed glazed leaf; dimensions and hardware are
    # estimates, and no unseen room interior is invented.
    door=-5.4
    p.box(door,1.875,DECK+1.12,.80,.025,2.10,C['newEastGlass'])
    for x in [door-.425,door+.425]:
        p.box(x,1.90,DECK+1.135,.05,.08,2.17,C['newEastFrame'])
    for z in [.075,2.195]:
        p.box(door,1.90,DECK+z,.80,.08,.05,C['newEastFrame'])
    p.box(door,1.88,DECK+.025,.96,.25,.05,C['newEastBaseSilver'])
    if detail:
        p.cylinder(door+.28,1.965,DECK+1.15,.012,.22,C['newEastSilver'],10)
        for z in [1.04,1.26]:
            p.box(door+.28,1.925,DECK+z,.025,.08,.025,C['newEastSilver'])
    # Return closures keep the window band enclosed without blocking its glass.
    p.box(-7.69,.4,DECK+1.55,.12,2.6,1.6,C['newEastSilver'])
    # The photo shows a continuous curved sill and two low plinth bands.
    for lo,hi,w,d,r in [(.04,.12,3.52,2.92,.71),(.22,.27,3.46,2.86,.68),
                         (2.35,2.41,3.48,2.88,.69)]:
        solid(p,rounded_ring(-6.05,.4,w,d,r),DECK+lo,DECK+hi,C['newEastSilver'])
    beveled_sill(p,DECK+.72,DECK+.79,C)
    for z in [6.91,8.04]:
        p.box(-6.05,.4,DECK+z,2.65,2.25,.06,C['newEastSilver'])
    for i in range(15):
        p.box(-7.24+i*.17,.4,DECK+8.01,.075,2.60,.07,C['newEastSilver'])
    if detail:
        # Sliding-window tracks and small pulls sit proud of the glazing.
        for z in [.83,2.30]:p.box(-6.05,-.98,DECK+z,2.5,.05,.026,C['newEastRecess'])
        for x in [-6.44,-5.71]:
            p.box(x,-1.01,DECK+1.48,.025,.06,.23,C['newEastSilver'])
            for z in [1.37,1.59]:p.box(x,-.975,DECK+z,.045,.08,.025,C['newEastSilver'])
    # Fit the tower beside mapped way/1501460937 without moving that building.
    p.v=[(x+1.15,y,z) for x,y,z in p.v]
    m.add_part('02_西侧高塔与门卫窗_照片建模',p)


def english_wordmark(C):
    """Photo-like serif capitals from a bundled, renamed Noto-derived subset.

    This approximates the photographed lettering, not an identified sign font.
    """
    curve=bpy.data.curves.new('new-east-latin','FONT')
    curve.font=bpy.data.fonts.load(str(Path(__file__).parent/'fonts/GXUGateSerif.otf'),check_existing=True)
    curve.font.pack()
    curve.body='GUANGXI UNIVERSITY';curve.space_character=1.15
    curve.extrude=.03;curve.resolution_u=3
    obj=bpy.data.objects.new('new-east-latin',curve);bpy.context.scene.collection.objects.link(obj)
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    x0=min(v.co.x for v in mesh.vertices);x1=max(v.co.x for v in mesh.vertices)
    y0=min(v.co.y for v in mesh.vertices);y1=max(v.co.y for v in mesh.vertices)
    p=Mesh()
    for face in mesh.polygons:
        p.face([(-.6+(mesh.vertices[i].co.x-(x0+x1)/2)*5.8/(x1-x0),
                 -1.44-mesh.vertices[i].co.z,
                 DECK+5.62+(mesh.vertices[i].co.y-(y0+y1)/2)*.32/(y1-y0)) for i in face.vertices],C['newEastGold'])
    evaluated.to_mesh_clear();bpy.data.objects.remove(obj,do_unlink=True);bpy.data.curves.remove(curve)
    return p


def circular_rib(m,x,y,z,r,h,mat,n):
    """Closed folded rim; its inner edge seats into the existing pier core."""
    bevel=.007
    profile=[(r-.085,-h/2),(r-bevel,-h/2),(r,-h/2+bevel),
             (r,h/2-bevel),(r-bevel,h/2),(r-.085,h/2)]
    rings=[[(x+radius*math.cos(i*math.tau/n),y+radius*math.sin(i*math.tau/n),z+height)
            for i in range(n)] for radius,height in profile]
    for a,b in zip(rings,rings[1:]+rings[:1]):
        for i in range(n):
            j=(i+1)%n;m.face([a[i],a[j],b[j],b[i]],mat)


def lintel(m,C,detail):
    p=Mesh();silver=C['newEastSilver'];dark=C['newEastRecess']
    # Curved plan return towards the east end cap, visible in the frontal photo.
    samples=[(-6.1,-1.12)]
    samples += [(-6.1+i*.17,-1.12) for i in range(1,63)]
    samples += [(4.44+1.36*i/9,-1.12+.72*(i/9)**2) for i in range(1,10)]
    bottom,top=DECK+5.15,DECK+7.02
    for (x,y),(a,b) in zip(samples,samples[1:]):
        solid(p,[(x,y+.05),(a,b+.05),(a,1.12),(x,1.12)],bottom,top,dark)
        angle=math.atan2(b-y,a-x)
        # Butt vertical blades to the soffit ribs: overlapping front faces
        # at the fold otherwise render as a row of black rectangles.
        metal_fin(p,(x+a)/2,(y+b)/2,bottom,top+.05,.08,.30,angle,silver)
        metal_fin(p,(x+a)/2,1.16,bottom,top+.05,.08,.22,0,silver)
        # Wrap the front blades underneath the beam, a strong cue in the photo.
        # Keep these ribs in both LODs for views looking through the gate.
        # Follow the facade normal through the curved return, instead of
        # keeping every soffit blade parallel to the straight part of the beam.
        midx,midy=(x+a)/2,(y+b)/2
        tx,ty=math.cos(angle),math.sin(angle);nx,ny=-ty,tx
        reach=(1.27-midy)/ny
        front=(midx-.15*nx,midy-.15*ny)
        rear=(midx+reach*nx,midy+reach*ny)
        solid(p,[(front[0]-.04*tx,front[1]-.04*ty),
                 (front[0]+.04*tx,front[1]+.04*ty),
                 (rear[0]+.04*tx,rear[1]+.04*ty),
                 (rear[0]-.04*tx,rear[1]-.04*ty)],bottom-.14,bottom,silver)
        p.face([(x,y,top+.01),(a,b,top+.01),(a,1.12,top+.01),(x,1.12,top+.01)],silver)
    # The right-hand termination is a broad front-facing stone panel, not just
    # a thin side cap. Its recessed face and edge frame remain visible in both LODs.
    # One central horizontal joint is visible in the frontal photograph.
    # Recess the backing and seat two face panels above it, without overlay lines.
    middle=(bottom+top)/2
    p.box(6.725,.40,middle,1.85,1.56,top-bottom+.12,C['newEastStone'])
    for lo,hi in [(bottom-.06,middle-.006),(middle+.006,top+.06)]:
        p.box(6.725,-.39,(lo+hi)/2,1.85,.02,hi-lo,C['newEastStone'])
    p.box(6.725,-.383,middle,1.85,.012,.012,dark)
    # The frontal photograph shows the ribbed underside continuing below the
    # broad end panel. Keep its shallow dark joints in both LODs.
    p.box(6.725,.39,bottom-.065,1.85,1.58,.01,dark)
    for i in range(11):
        p.box(5.875+i*.17,.39,bottom-.105,.075,1.58,.07,silver)
    # Mitred frame strips meet edge-to-edge at all four corners.
    outer=[(5.7825,bottom-.0725),(7.6675,bottom-.0725),
           (7.6675,top+.0725),(5.7825,top+.0725)]
    inner=[(5.8375,bottom-.0175),(7.6125,bottom-.0175),
           (7.6125,top+.0175),(5.8375,top+.0175)]
    for i in range(4):
        j=(i+1)%4;outline=[outer[i],outer[j],inner[j],inner[i]]
        front=[(x,-.485,z) for x,z in outline]
        back=[(x,-.385,z) for x,z in outline]
        p.face(front,silver);p.face(back[::-1],silver)
        for k in range(4):
            nxt=(k+1)%4;p.face([front[k],back[k],back[nxt],front[nxt]],silver)
    m.add_part('03_银灰格栅横梁与弧形收头_照片建模',p)
    p=Mesh()
    p.cylinder(4.5,.25,(DECK-.52)/2,.65,DECK+.52,C['gateTrim'],32)
    p.cylinder(4.5,.25,(DECK+bottom)/2,.56,bottom-DECK,dark,32)
    for i in range(36):
        # Darker, warmer lower rings are visible in the 2025 frontal photo;
        # colour and weathering extent remain estimates, not material analysis.
        finish=C['newEastAgedSilver'] if i in (1,2,4) else silver
        circular_rib(p,4.5,.25,DECK+.07+i*.142,.63,.045,finish,40 if detail else 24)
    for z,r,h in [(DECK+.04,.68,.08),(DECK+.18,.65,.06),(bottom-.08,.68,.10)]:
        p.cylinder(4.5,.25,z,r,h,silver,40 if detail else 24)
    m.add_part('04_东侧横肋圆柱_照片建模',p)
    p=gate_wordmark(-.6,-1.43,DECK+6.35,5.8,1.0,C['newEastGold'])
    # Both LODs retain lettering, so the name does not appear only at close range.
    p.extend(english_wordmark(C))
    m.add_part('05_金色中英文校名_照片建模',p)


def pedestrian_entry(m,C,detail):
    p=Mesh();cx=6.55;half=1.35;sheet=C['newEastCanopyBlue']
    for x in [cx-half,cx+half]:
        for y in [-1.45,1.45]:p.cylinder(x,y,DECK+1.35,.045,2.7,C['newEastSilver'],10)
    n=20 if detail else 12
    def roof(x):return DECK+2.75+.36*(1-((x-cx)/half)**2)
    def arch(y,offset,width,height):
        # Continuous rectangular framing follows the filmed canopy silhouette.
        # Shared cross sections and closed ends avoid holes between short tubes.
        rings=[]
        for i in range(n+1):
            x=cx-half+2*half*i/n;z=roof(x)+offset
            rings.append([(x,y-width/2,z-height/2),(x,y+width/2,z-height/2),
                          (x,y+width/2,z+height/2),(x,y-width/2,z+height/2)])
        for a,b in zip(rings,rings[1:]):
            for j in range(4):
                k=(j+1)%4;p.face([a[j],a[k],b[k],b[j]],C['newEastSilver'])
        p.face(rings[0][::-1],C['newEastSilver']);p.face(rings[-1],C['newEastSilver'])
    for i in range(n):
        a=cx-half+2*half*i/n;b=cx-half+2*half*(i+1)/n
        p.face([(a,-1.85,roof(a)),(b,-1.85,roof(b)),(b,1.85,roof(b)),(a,1.85,roof(a))],sheet)
        p.face([(a,1.85,roof(a)-.045),(b,1.85,roof(b)-.045),(b,-1.85,roof(b)-.045),(a,-1.85,roof(a)-.045)],sheet)
        # Close the curved front/rear sheet edges; no open, paper-thin silhouette.
        for y in [-1.85,1.85]:
            p.face([(a,y,roof(a)-.045),(b,y,roof(b)-.045),
                    (b,y,roof(b)),(a,y,roof(a))],sheet)
    for y in [-1.45,-.5,.5,1.45]:arch(y,-.065,.045,.06)
    for y in [-1.85,0,1.85]:arch(y,.01,.07,.07)
    for x in [cx-half,cx,cx+half]:
        # Let the closed ends project 10 mm past the arch face. Coincident
        # end caps at their junction produce dark z-fighting in decoded GLBs.
        p.box(x,0,roof(x),.07,3.79,.07,C['newEastSilver'])
    for x in [cx-half,cx+half]:
        p.face([(x,-1.85,roof(x)-.045),(x,1.85,roof(x)-.045),
                (x,1.85,roof(x)),(x,-1.85,roof(x))],sheet)
        for y in [-1.45,1.45]:
            p.box(x,y,DECK+.025,.18,.18,.05,C['newEastSilver'])
            p.line((x,y,DECK+2.38),(x,y+(-.3 if y<0 else .3),roof(x)-.04),.025,C['newEastSilver'],6)
    # The 00:12 view shows a framed notice panel on the planted side. Retain
    # its opaque backing and frame; the unreadable artwork is not recreated.
    p.box(7.925,0,DECK+1.68,.045,2.35,1.55,C['newEastBlue'])
    # Four mitred strips share edges instead of overlapping front faces at
    # the corners, which otherwise turn black after export/rendering.
    outer=[(-1.225,.855),(1.225,.855),(1.225,2.505),(-1.225,2.505)]
    inner=[(-1.175,.905),(1.175,.905),(1.175,2.455),(-1.175,2.455)]
    for i in range(4):
        j=(i+1)%4;outline=[outer[i],outer[j],inner[j],inner[i]]
        a=[(7.885,y,DECK+z) for y,z in outline]
        b=[(7.965,y,DECK+z) for y,z in outline]
        p.face(a[::-1],C['newEastSilver']);p.face(b,C['newEastSilver'])
        for k in range(4):
            nxt=(k+1)%4;p.face([a[k],a[nxt],b[nxt],b[k]],C['newEastSilver'])
    for y in [-1.2,1.2]:
        for z in [.88,2.48]:
            p.line((7.925,y,DECK+z),(7.9,math.copysign(1.45,y),DECK+z),.018,C['newEastSilver'],6)
    m.add_part('06_东25栋旁蓝色弧形雨棚_视频建模',p)
    p=Mesh()
    for x in [5.65,6.55,7.45]:
        # Rounded stainless housings with a recessed base and separate top seam.
        solid(p,rounded_ring(x,0,.23,1.26,.065,4),DECK+.08,DECK+1.02,C['newEastSilver'])
        solid(p,rounded_ring(x,0,.20,1.19,.05,4),DECK,DECK+.10,C['newEastRecess'])
        solid(p,rounded_ring(x,0,.24,1.28,.07,4),DECK+1.02,DECK+1.045,C['newEastRecess'])
        solid(p,rounded_ring(x,0,.25,1.30,.075,4),DECK+1.045,DECK+1.10,C['newEastSilver'])
        for y in [-.43,.43]:
            facing=-1 if y<0 else 1
            p.box(x,y,DECK+1.20,.045,.055,.20,C['newEastSilver'])
            p.box(x,y,DECK+1.48,.18,.085,.42,C['newEastRecess'])
            p.box(x,y+facing*.047,DECK+1.46,.13,.014,.26,C['newEastGlass'])
            # A separate lens above the portrait screen, on both approaches.
            p.line((x,y+facing*.043,DECK+1.65),
                   (x,y+facing*.059,DECK+1.65),.021,C['newEastGlass'],12)
            p.face([(x+.021*math.cos(i*math.tau/12),y+facing*.059,
                     DECK+1.65-facing*.021*math.sin(i*math.tau/12)) for i in range(12)],C['newEastGlass'])
            if detail:
                p.box(x,y+facing*.047,DECK+1.30,.055,.014,.015,C['newEastSilver'])
                # Access panels lie on the housing, not across the clear lane.
                for side in [-1,1]:
                    p.box(x+side*.117,y,DECK+.55,.008,.20,.72,C['newEastRecess'])
                    p.box(x+side*.123,y,DECK+.55,.008,.18,.70,C['newEastSilver'])
        # Blue end covers are visible from inside and outside the entrance.
        for y in [-.637,.637]:p.box(x,y,DECK+.53,.12,.025,.78,C['newEastBlue'])
    # The video shows blue swing leaves. Display an estimated open position,
    # folded along the housings, rather than placing a solid panel in the lane.
    for x,direction in [(5.80,1),(6.40,-1),(6.70,1),(7.30,-1)]:
        y=direction*.23
        p.box(x,y,DECK+.73,.018,.46,.32,C['newEastBlue'])
        for z in [.56,.90]:p.box(x,y,DECK+z,.025,.48,.02,C['newEastSilver'])
        p.cylinder(x,0,DECK+.73,.022,.37,C['newEastSilver'],10)
        for z in [.64,.82]:
            p.line((x-direction*.06,0,DECK+z),(x,0,DECK+z),.012,C['newEastSilver'],8)
    for x in [5.2,7.9]:
        for y in [-2.5,0,2.5]:
            foot=DECK-max(0,abs(y)-2.3)*.52/1.7
            p.cylinder(x,y,(foot+DECK+1.1)/2,.035,DECK+1.1-foot,C['newEastSilver'],8)
        for z in [.25,1.05]:p.line((x,-2.5,DECK+z),(x,2.5,DECK+z),.026,C['newEastSilver'],6)
        for i in range(27):
            y=-2.4+i*4.8/26
            p.line((x,y,DECK+.25),(x,y,DECK+1.05),.014,C['newEastSilver'],6)
    m.add_part('07_门禁与纵向护栏_视频建模',p)


def garden_enclosure(m,C):
    """East 25's planted edge, seen from inside the gate at 00:12.

    The low masonry edge and metal bars are visible; the short return lengths,
    planting layout and grade are estimates constrained by the mapped building.
    Do not extrude the illustrative campus boundary into a physical wall.
    """
    def grade(y):
        return DECK-min(1,max(0,(y-2.3)/1.7))*.52

    def wall_segment(p,a,b,width,lo,hi,mat):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        nx,ny=-dy/length*width/2,dx/length*width/2
        ring=[(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),
              (b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)]
        # Footings remain below the local ground without enlarging the camera
        # box with invisible deep foundations.
        bottom=[(x,y,max(-.52,grade(y)+lo)) for x,y in ring]
        top=[(x,y,grade(y)+hi) for x,y in ring]
        p.face(bottom[::-1],mat);p.face(top,mat)
        for i in range(4):
            j=(i+1)%4;p.face([bottom[i],bottom[j],top[j],top[i]],mat)

    p=Mesh()
    # A narrow planted strip leaves the canopy and both accessible lanes clear.
    stations=[-2.1,1.45,2.3,4,6.1,8.2]
    for x in [8.15,10.8]:
        for a,b in zip(stations,stations[1:]):
            wall_segment(p,(x,max(a,-2)),(x,min(b,8.1)),.20,-1,.15,C['newEastWall'])
            # Butt the long coping into the end caps, avoiding doubled top faces.
            wall_segment(p,(x,max(a,-1.97)),(x,min(b,8.07)),.26,.15,.19,C['newEastWallCap'])
    for y in [-2.1,8.2]:
        wall_segment(p,(8.05,y),(10.9,y),.20,-1,.15,C['newEastWall'])
        wall_segment(p,(8.02,y),(10.93,y),.26,.15,.19,C['newEastWallCap'])
    for a,b in zip(stations,stations[1:]):
        wall_segment(p,(9.475,max(a,-2)),(9.475,min(b,8.1)),2.43,-1,.06,C['newEastSoil'])
    m.add_part('09_东25栋侧矮墙与压顶_视频形制范围估算',p)

    p=Mesh();metal=C['newEastSilver']
    # The transverse panel meets the canopy; its return encloses the planted
    # edge without putting bars across the public pedestrian passage.
    panels=[((7.9,1.45),(10.8,1.45))]
    panels += [((8.15,a),(8.15,b)) for a,b in zip(stations[1:],stations[2:])]
    panels += [((8.15,8.2),(10.8,8.2))]
    posts=set()
    for a,b in panels:
        posts.update([a,b])
        for h in [.43,1.86]:
            p.line((*a,grade(a[1])+h),(*b,grade(b[1])+h),.023,metal,6)
        n=math.ceil(math.dist(a,b)/.16)
        for i in range(1,n):
            x=a[0]+(b[0]-a[0])*i/n;y=a[1]+(b[1]-a[1])*i/n
            p.box(x,y,grade(y)+1.135,.024,.024,1.43,metal)
    for x,y in sorted(posts):
        if x==7.9:continue  # Existing canopy column carries this junction.
        p.box(x,y,grade(y)+1.05,.065,.065,1.72,metal)
        p.box(x,y,grade(y)+.215,.14,.14,.05,metal)
        p.box(x,y,grade(y)+1.925,.082,.082,.035,metal)
    m.add_part('10_东侧金属围栏与雨棚衔接_视频形制范围估算',p)

    p=Mesh()
    # Continuous, uneven shrub masses rather than repeated clipped topiary.
    # Shared silhouettes in both LODs avoid foliage popping at distance changes.
    profile=[(-.5,0),(-.5,.45),(-.34,.85),(-.04,1),(.32,.85),(.5,.45),(.5,0)]
    rng=random.Random('new-east-leaf-sprays-v1')
    ys=sorted(set([-1.85+i*9.85/26 for i in range(27)]+[2.3,4]))
    for row,(cx,width) in enumerate([(8.94,1.08),(9.96,1.18)]):
        rings=[]
        for i,y in enumerate(ys):
            taper=.58 if i in (0,len(ys)-1) else 1
            x=cx+.055*math.sin(i*1.7+row)
            w=width*taper*(.92+.08*math.sin(i*1.3+row)**2)
            height=.55+.20*math.sin(i*.71+row)**2+.09*math.cos(i*1.9)**2
            rings.append([(x+side*w,y,grade(y)+.055+rise*height*taper) for side,rise in profile])
        mat=C['newEastLeaf' if row else 'newEastLeafLight']
        for a,b in zip(rings,rings[1:]):
            for j in range(len(profile)):
                k=(j+1)%len(profile);p.face([a[j],a[k],b[k],b[j]],mat)
        p.face(rings[0][::-1],mat);p.face(rings[-1],mat)
        # The route video shows leafy, irregular crowns. Small attached sprays
        # soften the coarse masses without claiming a plant species or survey.
        # Both LODs retain these silhouettes; all dimensions remain estimates.
        for ring in rings[1:-1:2]:
            for point in ring[2:5]:
                x,y,z=point;z-=.008;phase=rng.uniform(0,math.tau)
                sx,sy=.14*math.cos(phase),.14*math.sin(phase)
                p.line((x,y,z),(x+sx*.82,y+sy*.82,z+.09*.82),.003,C['newEastLeaf'],5)
                # Offset pairs along a short stem, avoiding repeated radial stars.
                for node in [.22,.52,.82]:
                    for side in [-1,1]:
                        t=node-(.045 if side<0 else 0)
                        root=(x+sx*t,y+sy*t,z+.09*t)
                        angle=phase+side*rng.uniform(.65,1.0)
                        length=rng.uniform(.075,.10);width=rng.uniform(.014,.024)
                        dx,dy=math.cos(angle),math.sin(angle);rise=rng.uniform(.025,.045)
                        tip=(root[0]+dx*length,root[1]+dy*length,root[2]+rise)
                        mid=(root[0]+dx*length*.55,root[1]+dy*length*.55,root[2]+rise*.55)
                        outline=[root,(mid[0]+dy*width,mid[1]-dx*width,mid[2]),
                                 tip,(mid[0]-dy*width,mid[1]+dx*width,mid[2])]
                        ridge=(mid[0],mid[1],mid[2]+.008)
                        finish=C['newEastLeafTips' if rng.random()<.65 else 'newEastLeafLight']
                        for a,b in zip(outline,outline[1:]+outline[:1]):p.face([a,b,ridge],finish)
                        p.face(outline[::-1],C['newEastLeaf'])
    m.add_part('11_东侧低矮绿篱_视频依据布置估算',p)


def new_east_gate(C,detail):
    ensure_materials(C)
    m=Mesh();paving(m,C,detail);guardroom(m,C,detail);lintel(m,C,detail);pedestrian_entry(m,C,detail)
    # The frontal photo shows a tall blue notice board, a grey upper sign and
    # yellow equipment on either side. Unreadable poster text is not invented.
    p=Mesh()
    p.box(0,1.4,DECK+.04,.82,.65,.08,C['newEastRecess'])
    p.box(0,1.4,DECK+1.05,.72,.50,2.02,C['newEastSilver'])
    p.box(0,1.139,DECK+1.16,.58,.025,1.56,C['newEastFrame'])
    p.box(0,1.121,DECK+1.16,.51,.018,1.47,C['newEastBlue'])
    p.box(0,1.4,DECK+2.13,.10,.10,.28,C['newEastSilver'])
    p.box(0,1.4,DECK+2.55,.92,.15,.60,C['newEastSilver'])
    p.box(0,1.318,DECK+2.55,.84,.018,.52,C['newEastRecess'])
    for x in [-.49,.49]:
        p.box(x,1.4,DECK+.05,.22,.42,.10,C['newEastRecess'])
        p.box(x,1.4,DECK+.60,.18,.35,1.10,C['newEastYellow'])
        # The frontal photograph shows the two vehicle arms lowered. Their
        # lengths/sections are estimated; the separate pedestrian lanes stay open.
        p.box(x,1.20,DECK+1.08,.17,.10,.17,C['newEastRecess'])
        p.box(x,1.135,DECK+1.08,.12,.05,.12,C['newEastSilver'])
        direction=-1 if x<0 else 1
        reach=2.56 if x<0 else 3.23
        for i in range(math.ceil(reach/.32)):
            a=i*.32;b=min(reach,(i+1)*.32)
            finish='newEastBarrierWhite' if i%2==0 else 'newEastBarrierRed'
            p.box(x+direction*(a+b)/2,1.085,DECK+1.08,b-a,.07,.09,C[finish])
        p.box(x+direction*(reach+.015),1.085,DECK+1.08,.03,.075,.095,C['newEastRubber'])
    m.add_part('08_中央核验设施_照片建模',p)
    garden_enclosure(m,C)
    west_connector(m,C)
    speed_cushions(m,C)
    # Half-metre repeat keeps the grain fine at this small end panel. Explicit
    # local UVs survive the later world-space translation and Draco export.
    for i,material in enumerate(m.m):
        if material!=C['newEastStone']:continue
        points=[m.v[j] for j in m.f[i]]
        a=[points[1][k]-points[0][k] for k in range(3)]
        b=[points[2][k]-points[0][k] for k in range(3)]
        normal=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        drop=max(range(3),key=lambda k:abs(normal[k]));u,v=[k for k in range(3) if k!=drop]
        m.face_uvs[i]=[(p[u]*2,p[v]*2) for p in points]
    return m


def speed_cushions(m,C):
    """Black/yellow road strips in the frontal photo; dimensions are estimated.

    The local plane is fitted to the existing road, not the lower terrain.
    Independent ray probes against the saved road guard this calibration.
    """
    p=Mesh()
    def road(x,y):return .1949-.02308*x+.0128*(y-2.8)
    profile=[(-.18,-.012),(-.18,0),(-.13,.024),(-.07,.048),
             (.07,.048),(.13,.024),(.18,0),(.18,-.012)]
    for left,right in [(-3.05,-.70),(.70,3.55)]:
        for i in range(math.ceil((right-left)/.45)):
            a=left+i*.45+.008;b=min(right,left+(i+1)*.45)-.008
            ends=[[(x,.35+y,road(x,.35+y)+h) for y,h in profile] for x in (a,b)]
            mat=C['newEastYellow' if i%2 else 'newEastRubber']
            for j in range(len(profile)):
                k=(j+1)%len(profile)
                p.face([ends[0][j],ends[1][j],ends[1][k],ends[0][k]],mat)
            p.face(ends[0],mat);p.face(ends[1][::-1],mat)
    m.add_part('13_车道黑黄减速带_照片形制尺寸估算',p)


def west_connector(m,C):
    """Short clad wall beside the tower; no inferred long campus perimeter.

    The 2021 exterior clip shows a low silver ribbed wall on the tower's west;
    the 2025 reverse view provides context for that connection. Its dimensions
    and hidden rear are estimates. The neighbouring OSM polygon has a recess:
    keep this wall inside that gap without changing the mapped building.
    """
    p=Mesh();left,right=-9.80,-6.50;front,back=.03,.37
    solid(p,[(left,front),(right,front),(right,back),(left,back)],
          -.52,DECK+.20,C['newEastWall'])
    solid(p,[(left,front),(right,front),(right,back),(left,back)],
          DECK+.20,DECK+3.02,C['newEastRecess'])
    # The visible face repeats the tower's narrow silver cladding rhythm.
    for i in range(19):
        x=left+.08+i*.17
        for y in [front,back]:
            metal_fin(p,x,y,DECK+.20,DECK+3.02,.075,.14,0,C['newEastSilver'])
    # Folded end closure and a shallow weather cap finish the short segment.
    p.box(left+.015,.20,DECK+1.61,.03,.36,2.82,C['newEastSilver'])
    p.box((left+right)/2,.20,DECK+3.05,right-left+.04,.52,.06,C['newEastSilver'])
    m.add_part('12_西侧银灰围墙_实景依据尺寸估算',p)
