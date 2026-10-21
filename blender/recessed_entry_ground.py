"""Clip the old road from the entrance and clear ground below its paving."""
import math
from geometry import Mesh
from site_geometry import mesh_triangles, contact_road
from paving_geometry import clear_paving_ground


def build_recessed_entry_ground(site,C,elevation,terrain,roads):
    e=site['entry'];p=e['recessedStairEntry'];a=math.radians(e['bearing'])
    nx,ny=math.sin(a),math.cos(a);x,y=e['center'];z=elevation(*site['buildingCenter'])
    def point(w,d,h):return (x+ny*w-nx*d,y-nx*w-ny*d,z+h)
    fw=p['apronFrontWidth'];pw=p['platformWidth'];start=p['apronStart'];toe=p['toe']
    hs=p['apronFrontHeights'];base=p['baseHeight'];grading=Mesh()
    for i in range(len(hs)-1):
        a=i/(len(hs)-1)-.5;b=(i+1)/(len(hs)-1)-.5
        pts=[point(a*fw,start,hs[i]),point(b*fw,start,hs[i+1]),point(b*pw,toe,base),point(a*pw,toe,base)]
        grading.face([pts[2],pts[1],pts[0]],C['grass']);grading.face([pts[3],pts[2],pts[0]],C['grass'])
    grading.face([point(-pw/2,toe,base),point(-pw/2,0,base),point(pw/2,0,base),point(pw/2,toe,base)],C['grass'])
    extra_masks=[]
    if 'landscape' in p:
        from entry_forecourt_geometry import landscape_mesh
        _,grading,extra_masks=landscape_mesh(e,z,C)
        grading.face([point(-pw/2,toe,base),point(-pw/2,0,base),point(pw/2,0,base),point(pw/2,toe,base)],C['grass'])
    terrain,report=clear_paving_ground(terrain,grading,{'bounds':site['gradingBounds'],'groundClearance':site['groundClearance'],'roundoffTolerance':.002})
    if 'landscape' in p:
        from entry_ground_bedding import bed_forecourt
        terrain,bedding=bed_forecourt(terrain,e,z,C['grass'])
        report['bedding']=bedding
    # Isolate nearby original faces once. Re-clipping the entire campus for
    # every small paving triangle is unnecessary and changes vertex order.
    outside=Mesh();local_roads=Mesh();x0,y0,x1,y1=site['gradingBounds']
    for f,m in zip(roads.f,roads.m):
        points=[roads.v[i] for i in f]
        separate=(max(v[0] for v in points)<x0 or min(v[0] for v in points)>x1 or
                  max(v[1] for v in points)<y0 or min(v[1] for v in points)>y1)
        (outside if separate else local_roads).face(points,m)
    # Clip the trapezoid and rectangle separately: their union has two
    # concave shoulders. Keep original road planes outside both pieces.
    for local in [[(-fw/2,start),(fw/2,start),(pw/2,toe),(-pw/2,toe)],
                  [(-pw/2,toe),(pw/2,toe),(pw/2,0),(-pw/2,0)]]+extra_masks:
        ring=[point(w,d,0)[:2] for w,d in local]
        if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))<0:ring.reverse()
        local_roads,_=contact_road(local_roads,mesh_triangles(local_roads),ring,ring,.1,0)
    outside.extend(local_roads);roads=outside
    if 'landscape' in p:
        from entry_ground_bedding import grade_rear_road_contact
        roads,rear_contact=grade_rear_road_contact(roads,e,z)
        report['rearRoadContact']=rear_contact
    return terrain,roads,{},[{'id':site['id'],'groundRepair':report,'pavingInBuildingMesh':True,'perimeterRoadFootprintsPreserved':True}]
