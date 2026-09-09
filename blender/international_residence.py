"""24-storey international residence and academic podium, independently editable.
Official exterior photo: gjxy.gxu.edu.cn current gallery, capture date unknown.
Footprint and floors are mapped; tower setbacks / unseen elevations are estimates.
"""
import math
from geometry import Mesh
from library import outline_edges
from south_gate import inscription


def international_residence(l,b,z,C,detail):
    m=Mesh();e=b['architecture'];body=Mesh();balconies=Mesh();rails=Mesh();glazing=Mesh();fins=Mesh();roof=Mesh();entrance=Mesh()
    stone=C['residenceStone'];trim=C['white'];glass=C['residenceGlass'];dark=C['libraryMullion']
    for part in e['parts']:
        h=part['height'];podium=h<20
        body.extrude(part['polygons'],part['triangles'],z if podium else z+13.2,h if podium else h-13.2,stone if not podium else C['residencePodium'],C['paleRoof'])
        for a,bb,ln,angle,nx,ny in outline_edges(part):
            if ln<1:continue
            dx=(bb[0]-a[0])/ln;dy=(bb[1]-a[1])/ln
            def box_at(t,out,zz,w,d,hh,mat,target):target.box(a[0]+dx*t+nx*out,a[1]+dy*t+ny*out,z+zz,w,d,hh,mat,angle)
            if podium:
                # Vertical brise-soleil stands off the glazing by 0.85 m.
                for f in range(4):box_at(ln/2,.10,1.65+f*3.3,ln-.4,.12,2.6,glass,glazing)
                for j in range(max(1,int(ln/2.8))):
                    t=(j+.5)*ln/max(1,int(ln/2.8))
                    box_at(t,.65,8.1,.28,1.2,9.2,C['residencePodium'],fins)
                    if detail:box_at(t+.20,.9,8.1,.10,.75,8.8,trim,fins)
                for hh in [3.3,13.2]:box_at(ln/2,.16,hh,ln+.6,.8,.4,trim,fins)
                continue
            count=max(1,int(ln/3.6));bay=ln/count
            # Balcony treatment is concentrated on the inward-facing facades.
            balcony_side=ln>22
            for f in range(4,24):
                base=f*3.3
                if balcony_side:
                    box_at(ln/2,.8,base,ln,1.8,.18,trim,balconies)
                    box_at(ln/2,1.60,base+.55,ln,.16,.92,stone,rails)
                    if detail:
                        box_at(ln/2,1.62,base+1.07,ln,.10,.055,dark,rails)
                    for j in range(count):
                        t=(j+.5)*bay
                        box_at(t,.10,base+1.85,bay*.78,.14,2.6,glass,glazing)
                        box_at(t-bay/2,.82,base+1.65,.22,1.8,3.12,stone,balconies)
                        if detail:
                            box_at(t,.21,base+1.85,.065,.12,2.6,dark,glazing)
                            for k in range(1,5):box_at(t-bay*.5+k*bay/5,1.62,base+.99,.035,.06,.2,dark,rails)
                else:
                    # Official facilities gallery shows nearly blind end walls, with
                    # a narrow glazed corner strip; do not fill them with a window grid.
                    t=ln*.13
                    box_at(t,.10,base+1.65,min(3.1,ln*.22),.14,2.86,glass,glazing)
                    if detail:box_at(t,.20,base+1.65,.08,.12,2.86,trim,glazing)
                box_at(ln/2,.07,base+3.17,ln,.20,.16,trim,fins)
            box_at(ln/2,.08,h+.52,ln,.35,1.04,stone,roof)
            box_at(ln/2,.10,h+1.1,ln+.6,.8,.22,trim,roof)
    # Open white crowns on both wings, visible in the official facilities photos.
    for cx,cy,w,d in [(-22.9,-.05,17.8,49.3),(.85,15.7,29.7,17.8)]:
        for sx in [-1,1]:
            for sy in [-1,1]:roof.box(cx+sx*(w/2-.45),cy+sy*(d/2-.45),z+80.8,.75,.75,3.2,trim)
        for sy in [-1,1]:roof.box(cx,cy+sy*(d/2-.45),z+82.65,w,.85,.65,trim)
        for sx in [-1,1]:roof.box(cx+sx*(w/2-.45),cy,z+82.65,.85,d,.65,trim)
    # Tall glazed corner bay, broken by each floor slab as in the official photograph.
    for f in range(4,24):
        glazing.box(-13.85,-22.7,z+f*3.3+1.65,.22,3.6,2.85,glass)
        glazing.box(-15.5,-24.76,z+f*3.3+1.65,3.4,.22,2.85,glass)
        fins.box(-13.72,-22.7,z+(f+1)*3.3,.35,3.9,.22,trim)
    for xx,yy in [(-23,11),(4,16)]:
        roof.box(xx,yy,z+80.2,8,8,2,stone)
        if detail:
            for j in range(4):roof.box(xx-2+j*1.3,yy,z+81.35,.7,3,.35,C['metal'])
    entrance.box(7,-24.8,z+2.4,15,.18,4.1,glass)
    entrance.box(7,-27,z+4.8,19,5,.45,C['residencePodium'])
    for xx in [-1,15]:entrance.box(xx,-27,z+2.4,.38,.38,4.8,trim)
    for j in range(6):entrance.box(7,-28.8+j*.3,z+(j+1)*.10,19,4-j*.6,(j+1)*.20,C['stone'])
    for name,part in [('01_地图裙楼与双翼',body),('02_逐层凹阳台',balconies),('03_阳台栏板与扶手',rails),('04_玻璃与转角窗带',glazing),('05_裙楼竖向遮阳板',fins),('06_屋顶女儿墙与设备',roof),('07_入口雨棚与台阶',entrance)]:m.add_part(name,part)
    m.add_part('08_入口标识',inscription('留学生公寓',7,-29.58,z+4.8,11,.52,trim,False))
    m.rotate_z(0,0,e['angle']);ox,oy=e['origin'];m.v=[(x+ox,y+oy,zz) for x,y,zz in m.v]
    return m
