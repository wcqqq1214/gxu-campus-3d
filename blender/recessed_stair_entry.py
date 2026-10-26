"""Inset entry stairs, graded approach and an open lattice canopy in both LODs."""
import math


def recessed_entry_blocks_window(entry,x,y,nx,ny,bottom,top,width):
    if 'recessedStairEntry' not in entry:return False
    p=entry['recessedStairEntry'];angle=math.radians(entry['bearing']);en=(math.sin(angle),math.cos(angle))
    dx,dy=x-p['rearCenter'][0],y-p['rearCenter'][1]
    hall=p.get('hall');span=hall['width'] if hall else entry['width']
    height=hall['clearHeight'] if hall else p['doorHeight']
    return (nx*en[0]+ny*en[1]>.999 and abs(dx*en[0]+dy*en[1])<.3
            and abs(dx*en[1]-dy*en[0])<(span+width+.3)/2
            and bottom<p['doorLandingHeight']+height+.15 and top>p['doorLandingHeight']-.15)


def add_recessed_stair_entry(mesh,entry,z,C):
    p=entry['recessedStairEntry'];a=math.radians(entry['bearing']);nx,ny=math.sin(a),math.cos(a)
    x,y=entry['center'];floor=p['platformHeight'];upper=p['doorLandingHeight'];bottom=-.2
    def point(w,d,h):return (x+ny*w-nx*d,y-nx*w-ny*d,z+h)
    def box(w,d,h,width,depth,height,material):
        mesh.box(*point(w,d,h),width,depth,height,C[material],-a)
    def slab(d0,d1,top,width):
        box(0,(d0+d1)/2,(top+bottom)/2,width,d1-d0,top-bottom,'stone')
    # Front paving follows the existing terrain profile; it meets the first
    # tread without keeping the old flat frame floor underneath it.
    pw=p['platformWidth'];heights=p['apronFrontHeights'];toe=p['toe'];base=p['baseHeight']
    start=p.get('apronStart',0);fw=p.get('apronFrontWidth',pw)
    if 'landscape' in p:
        from entry_forecourt_geometry import landscape_mesh
        visible,_,_=landscape_mesh(entry,z,C);mesh.extend(visible)
    else:
        for i in range(len(heights)-1):
            ta=i/(len(heights)-1);tb=(i+1)/(len(heights)-1)
            wa=fw*(ta-.5);wb=fw*(tb-.5);ia=pw*(ta-.5);ib=pw*(tb-.5)
            # Two triangles also define the exact grading plane when the front
            # terrain profile varies across the width.
            pts=[point(wa,start,heights[i]),point(wb,start,heights[i+1]),point(ib,toe,base),point(ia,toe,base)]
            mesh.face([pts[2],pts[1],pts[0]],C['stone']);mesh.face([pts[3],pts[2],pts[0]],C['stone'])
            mesh.face([point(wb,start,heights[i+1]),point(wa,start,heights[i]),point(wa,start,bottom),point(wb,start,bottom)][::-1],C['stone'])
        for side,h in [(-1,heights[0]),(1,heights[-1])]:
            w=side*fw/2;inner=side*pw/2
            face=[point(w,start,bottom),point(w,start,h),point(inner,toe,base),point(inner,toe,bottom)]
            mesh.face(face if side>0 else face[::-1],C['stone'])
    slab(p['outerEnd'],p['innerStart'],floor,pw)
    for i in range(p['outerRisers']-1):
        top=base+(floor-base)*(i+1)/p['outerRisers']
        d0=toe+i*p['tread'];slab(d0,d0+p['tread'],top,pw)
    for i in range(p['innerRisers']-1):
        top=floor+(upper-floor)*(i+1)/p['innerRisers']
        d0=p['innerStart']+i*p['tread'];slab(d0,d0+p['tread'],top,p['stairWidth'])
    hall=p.get('hall')
    slab(p['innerEnd'],p['recess']+.04,upper,hall['width'] if hall else p['stairWidth'])
    # Framed glass panels follow the photographed stair / landing edges.
    from entry_guardrails import guard as add_guard
    def guard(width,start,end,h0,h1):
        for side in (-1,1):
            w=side*(width/2-.12)
            add_guard(mesh,point,box,C,w,start,w,end,h0,h1)
    rise=(floor-base)/p['outerRisers']
    guard(pw,toe,p['outerEnd'],base+rise,floor)
    guard(pw,p['outerEnd'],p['innerStart'],floor,floor)
    guard(p['stairWidth'],p['innerStart'],p['innerEnd'],floor+(upper-floor)/p['innerRisers'],upper)
    if hall:
        # A thin elevated floor keeps the side aisles visibly open below;
        # the stair top opens laterally into both aisles without cross rails.
        gw=hall['galleryWidth'];hw=hall['width'];gs=hall['galleryStart'];end=p['recess']
        for side in (-1,1):
            w=side*(hw/2-gw/2)
            box(w,(gs+end)/2,upper-.15,gw,end-gs,.3,'white')
            for d in (gs+.25,(gs+end)/2):box(side*(hw/2-.2),d,upper/2,.3,.3,upper,'stone')
            for edge in (side*hw/2,side*(hw/2-gw)):
                rail_end=end if abs(edge)==hw/2 else p['innerEnd']
                add_guard(mesh,point,box,C,edge,gs,edge,rail_end,upper,upper)
            add_guard(mesh,point,box,C,side*(hw/2-gw),gs,side*hw/2,gs,upper,upper)
        depth=hall['depth'];ceiling=upper+hall['clearHeight']
        box(0,end+depth/2,upper-.12,hw,depth,.24,'stone')
        box(0,end+depth/2,ceiling+.10,hw,depth,.20,'stone')
    else:
        guard(p['stairWidth'],p['innerEnd'],p['recess']-.15,upper,upper)
    # The low canopy is visibly open between its ribs, as in the photographs.
    c=p['canopy'];d0=-c['frontOffset'];d1=d0+c['depth'];top=c['topHeight'];th=c['thickness'];soffit=top-th
    for d in (d0,d1):box(0,d,top-th/2,c['width']+.5,.30,th,'dark')
    for i in range(8):
        w=-c['width']/2+c['width']*i/7
        box(w,(d0+d1)/2,top-th/2,.24,c['depth'],th,'dark')
    for frac in (.33,.66):box(0,d0+c['depth']*frac,top-th/2,c['width'],.20,th,'dark')
    beam=c.get('portalBeam')
    if beam:
        box(0,d0+c['columnInset'],beam['topHeight']-beam['thickness']/2,beam['width'],beam['depth'],beam['thickness'],'stone')
    for i,(cx,cy) in enumerate(p['columns']):
        # Full shafts are embedded in the stair/plinth, never suspended at
        # the intermediate landing when their plan position is on a tread.
        shaft_top=beam['topHeight']-beam['thickness'] if beam and i%2==0 else soffit
        mesh.cylinder(cx,cy,z+(bottom+shaft_top)/2,c['columnDiameter']/2,shaft_top-bottom,C['white'],n=16)
        # Dark protective sleeves are visible where the round shafts meet
        # the intermediate platform in the front photograph.
        mesh.cylinder(cx,cy,z+floor+.25,c['columnDiameter']/2+.018,.5,C['dark'],n=16)
        mesh.cylinder(cx,cy,z+shaft_top-.12,c['columnDiameter']/2+.035,.14,C['dark'],n=16)
    # Glazing belongs at the back of the covered hall, not on the stair head.
    dh=p['doorHeight'];dw=entry['width'];d=p['recess']+(hall['depth'] if hall else 0)-.08
    if hall:
        for side in (-1,1):
            width=(hall['width']-dw)/2-.25;w=side*(dw/2+.125+width/2)
            box(w,d,upper+dh/2,width,.08,dh,'glass')
            for edge in (-width/2,0,width/2):box(w+edge,d-.07,upper+dh/2,.065,.09,dh+.08,'dark')
            for h in (upper+.035,upper+dh):box(w,d-.07,h,width,.09,.07,'dark')
    box(0,d,upper+dh/2,dw,.08,dh,'glass')
    for w in (-dw/2,-dw/4,0,dw/4,dw/2):box(w,d-.07,upper+dh/2,.065,.09,dh+.08,'dark')
    for h in (upper+.035,upper+2.15,upper+dh):box(0,d-.07,h,dw+.08,.09,.07,'dark')
    for w in (-.18,.18):box(w,d-.13,upper+1.05,.035,.06,.38,'white')
