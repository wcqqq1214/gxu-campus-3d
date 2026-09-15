"""Door bays beneath an existing separate canopy; no duplicate roof/platform."""
import math


def add_mapped_canopy_entry(mesh,entry,z,C):
    p=entry['shelter'];bearing=math.radians(entry['bearing']);n=(math.sin(bearing),math.cos(bearing));t=(n[1],-n[0]);angle=-bearing
    x,y=entry['center'];floor=z+p['floorHeight'];bay=entry['width']/p['bays'];pier=p['pierWidth'];height=p['doorHeight'];transom=p['transomHeight']
    for i in range(p['bays']):
        offset=-entry['width']/2+(i+.5)*bay;cx,cy=x+t[0]*offset,y+t[1]*offset;w=bay-pier
        mesh.box(cx+n[0]*.08,cy+n[1]*.08,floor+height/2,w,.12,height,C['glass'],angle)
        mesh.box(cx+n[0]*.08,cy+n[1]*.08,floor+height+transom/2,w,.12,transom,C['glass'],angle)
        # The photograph shows paired glazed leaves and a continuous transom.
        for dx in [-w/2,0,w/2]:
            mesh.box(cx+t[0]*dx+n[0]*.16,cy+t[1]*dx+n[1]*.16,floor+(height+transom)/2,.055,.08,height+transom,C['dark'],angle)
        for dz in [0,height,height+transom]:
            mesh.box(cx+n[0]*.16,cy+n[1]*.16,floor+dz,w,.08,.055,C['dark'],angle)
    for i in range(p['bays']+1):
        offset=-entry['width']/2+i*bay
        mesh.box(x+t[0]*offset+n[0]*.10,y+t[1]*offset+n[1]*.10,floor+(height+transom)/2,pier,.25,height+transom,C['stone'],angle)
    mesh.box(x+n[0]*.10,y+n[1]*.10,floor+height+transom+.06,entry['width']+pier,.25,.12,C['stone'],angle)
