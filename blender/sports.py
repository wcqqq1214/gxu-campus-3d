"""Editable, meter-scale athletics models. Dimensions are visual estimates.

The mapped red apron is retained, including east-field straight extensions.
All paint is actual flat geometry, so it remains visible without remote textures.
"""
import math
from geometry import Mesh


def oval(radius, half, segments=96):
    return [(radius * math.cos(a), y + radius * math.sin(a))
            for y, start in [(half, 0), (-half, math.pi)]
            for a in [start + math.pi * i / segments for i in range(segments + 1)]]


def strip(mesh, points, z, width, material, closed=False):
    pairs = zip(points, points[1:] + (points[:1] if closed else []))
    for a, b in pairs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-8:
            continue
        nx, ny = dy / length * width / 2, -dx / length * width / 2
        mesh.face([(a[0]+nx,a[1]+ny,z),(b[0]+nx,b[1]+ny,z),
                   (b[0]-nx,b[1]-ny,z),(a[0]-nx,a[1]-ny,z)], material)


def band(mesh, inner, outer, z, material):
    for i in range(len(inner)):
        j = (i + 1) % len(inner)
        mesh.face([(*inner[i], z), (*outer[i], z), (*outer[j], z), (*inner[j], z)], material)


def athletics(field, C):
    model = Mesh()
    z = field['elevation'] + .46
    cx, cy = field['center']
    angle = field['rotation']
    c, s = math.cos(angle), math.sin(angle)
    local = lambda x,y: ((x-cx)*c+(y-cy)*s, -(x-cx)*s+(y-cy)*c)
    half = field['straightHalfLength']
    outer = field['outerRadius']
    inner = outer-field['laneCount']*field['laneWidth']
    # Use Earcut for the concave source apron rather than filling its track hole.
    apron = Mesh()
    for i in range(0,len(field['groundTriangles']),3):
        apron.face([(*local(*field['ground'][k]),z-.025)
                    for k in field['groundTriangles'][i:i+3]],C['trackApron'])
    model.add_part('外侧原始轮廓与直道延伸',apron)
    track = Mesh()
    for lane in range(field['laneCount']):
        r = inner + lane*field['laneWidth']
        band(track,oval(r,half),oval(r+field['laneWidth'],half),z,
             C['track'] if lane%2==0 else C['trackAlt'])
    model.add_part('连续圆弧与八条跑道',track)
    turf = Mesh();edge=oval(inner,half)
    for i,a in enumerate(edge):
        turf.face([(0,0,z),(*a,z),(*edge[(i+1)%len(edge)],z)],C['fieldGreen'])
    width,length=field['pitchWidth'],field['pitchLength']
    for i in range(20):
        y=-length/2+i*length/20
        turf.face([(-width/2,y,z+.008),(width/2,y,z+.008),
                   (width/2,y+length/20,z+.008),(-width/2,y+length/20,z+.008)],
                  C['fieldGreen'] if i%2 else C['fieldStripe'])
    model.add_part('内场草坪与足球场条纹',turf)
    paint=Mesh();white=C['sportWhite']
    for lane in range(field['laneCount']+1):
        strip(paint,oval(inner+lane*field['laneWidth'],half),z+.035,.07,white,True)
    # Finish line on the eastern straight; the exact official line is unverified.
    finish=-half+9
    strip(paint,[(inner,finish),(outer,finish)],z+.037,.14,white)
    strip(paint,[(inner,half-9),(outer,half-9)],z+.037,.07,white)
    # Small lane numerals as planar seven-segment stencils, no font dependency.
    segments=[((-.26,.5),(.26,.5)),((.26,.5),(.26,0)),((.26,0),(.26,-.5)),
              ((-.26,-.5),(.26,-.5)),((-.26,0),(-.26,-.5)),
              ((-.26,.5),(-.26,0)),((-.26,0),(.26,0))]
    digits=['12','01643','01236','5612','05623','056432','012','0123456']
    for lane, glyph in enumerate(digits[:field['laneCount']]):
        x=inner+(lane+.5)*field['laneWidth']
        for index in map(int,glyph):
            strip(paint,[(x+a,finish-2+b*1.5) for a,b in segments[index]],z+.04,.09,white)
    model.add_part('分道线与起终点示意标记',paint)
    lines=Mesh();pz=z+.055
    def draw(points,closed=False):strip(lines,points,pz,.10,white,closed)
    def circle(x,y,r,start=0,end=math.tau):
        draw([(x+r*math.cos(a),y+r*math.sin(a)) for a in
              [start+(end-start)*i/96 for i in range(97)]])
    draw([(-width/2,-length/2),(width/2,-length/2),(width/2,length/2),(-width/2,length/2)],True)
    draw([(-width/2,0),(width/2,0)]);circle(0,0,9.15)
    circle(0,0,.16)
    for sign in [-1,1]:
        y=sign*length/2
        for w,d in [(40.32,16.5),(18.32,5.5)]:
            draw([(-w/2,y),(-w/2,y-sign*d),(w/2,y-sign*d),(w/2,y)])
        circle(0,y-sign*11,.16)
        # Only the section outside the penalty area, not an overlapping full ring.
        a=math.asin(5.5/9.15)
        if sign<0:circle(0,y+11,9.15,a,math.pi-a)
        else:circle(0,y-11,9.15,math.pi+a,math.tau-a)
        for side in [-1,1]:
            start={(1,1):math.pi,(-1,1):1.5*math.pi,(1,-1):math.pi/2,(-1,-1):0}[(side,sign)]
            circle(side*width/2,y,1,start,start+math.pi/2)
    model.add_part('足球场完整白色标线',lines)
    goals=Mesh()
    for sign in [-1,1]:
        y=sign*length/2;back=y+sign*2
        for x in [-3.66,3.66]:
            goals.line((x,y,z),(x,y,z+2.44),.065,white,8)
            goals.line((x,y,z+2.44),(x,back,z+1.8),.045,white,6)
            goals.line((x,back,z+1.8),(x,back,z+.05),.045,white,6)
            for k in range(1,6):
                h=k*.30
                goals.line((x,y,z+h),(x,back,z+h),.012,C['goalNet'],4)
        goals.line((-3.66,y,z+2.44),(3.66,y,z+2.44),.065,white,8)
        goals.line((-3.66,back,z+1.8),(3.66,back,z+1.8),.035,white,6)
        for k in range(20):
            x=-3.66+k*7.32/19
            goals.line((x,y,z+2.44),(x,back,z+1.8),.012,C['goalNet'],4)
            goals.line((x,back,z+1.8),(x,back,z+.05),.012,C['goalNet'],4)
        for k in range(1,6):goals.line((-3.66,back,z+k*.3),(3.66,back,z+k*.3),.012,C['goalNet'],4)
        for side in [-1,1]:
            x=side*width/2
            goals.cylinder(x,y,z+.7,.025,1.4,white,6)
            goals.face([(x,y,z+1.4),(x+.4,y,z+1.3),(x,y,z+1.05)],C['seatYellow'])
    model.add_part('两端球门网架与角旗',goals)
    for i,(x,y,h) in enumerate(model.v):model.v[i]=(cx+x*c-y*s,cy+x*s+y*c,h)
    return model


def west_stand(building,z,C,detail):
    """2025 photo-based west-facing stage on the mapped roof footprint."""
    model=Mesh();x0,y0,x1,y1=building['bounds'];cx,cy=building['center']
    width=y1-y0;depth=x1-x0
    stage=Mesh();stage.box(cx,cy,z+.4,depth,width,.8,C['white'])
    stage.box(x1-.4,cy,z+4,.8,width-2,7.2,C['stone'])
    for y in [cy-width/2+1.8,cy+width/2-1.8]:
        stage.box(cx+3,y,z+4.2,depth-6,1.3,7.6,C['white'])
        stage.cylinder(x0+3,y,z+4.5,.40,8.2,C['white'],16)
    for i in range(4):stage.box(x0+.3+i*.35,cy,z+(i+.5)*.2,.35,width-4,.2,C['white'])
    model.add_part('开放主席台与两根前柱',stage)
    roof=Mesh();roof.box(cx,cy,z+8.9,depth,width,.40,C['white'])
    roof.box(x0+.22,cy,z+8.6,.44,width,.9,C['white'])
    if detail:
        for i in range(9):
            y=y0+.8+i*(width-1.6)/8
            roof.line((x0+1,y,z+8.45),(x1-.5,y,z+8.45),.075,C['dark'])
            for j in range(6):
                x=x0+1+j*(depth-1.5)/6;xx=x+(depth-1.5)/6
                roof.line((x,y,z+8.45),(xx,y,z+8),.045,C['dark'],4)
                roof.line((x,y,z+8),(xx,y,z+8.45),.045,C['dark'],4)
        for i in range(6):
            x=x0+1+i*(depth-1.5)/5
            roof.line((x,y0+.8,z+8.1),(x,y1-.8,z+8.1),.065,C['dark'],4)
    model.add_part('白色悬挑屋盖与檐下桁架',roof)
    seating=Mesh()
    for side in [-1,1]:
        wingcy=cy+side*(width/2+10)
        for row in range(6):
            x=x0+1+row*.8;h=.25+row*.36
            seating.box(x,wingcy,z+h/2,.8,18,h,C['white'])
            for seat in range(25):
                y=wingcy-8.4+seat*.7
                if 11<=seat<=13:continue
                mat=C['seatYellow'] if side<0 and seat<12 else C['seatBlue'] if side>0 and seat<12 else C['seatGreen']
                seating.box(x-.03,y,z+h+.075,.46,.56,.15,mat)
                if detail:seating.box(x+.20,y,z+h+.27,.085,.56,.40,mat)
        for end in [-1,1]:
            y=wingcy+end*9.2
            seating.line((x0+.5,y,z+.65),(x0+5.7,y,z+2.9),.04,C['metal'],6)
    model.add_part('黄绿青蓝阶梯座席与侧扶手',seating)
    return model
