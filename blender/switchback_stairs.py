"""Exterior stair study: real stepped waist slabs, landings and solid parapets."""
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


def add_switchback_stairs(mesh, stairs, z, material):
    s=stairs;u=Vector((*s['tangent'],0));n=Vector((*s['normal'],0))
    origin=Vector((*s['center'],z))
    def point(along,out,height):
        return origin+u*along+n*out+Vector((0,0,height))
    def face(points,normal):
        points=[Vector(p) for p in points]
        if (points[1]-points[0]).cross(points[2]-points[0]).dot(normal)<0:points.reverse()
        mesh.face([tuple(p) for p in points],material)
    def prism(profile,left,right):
        # Profile is a clockwise outline in the outward-distance / height plane.
        low=[point(left,d,h) for d,h in profile]; high=[point(right,d,h) for d,h in profile]
        for ring,normal in ((low,-u),(high,u)):
            for tri in tessellate_polygon([ring]):
                face([ring[i] for i in tri] if isinstance(tri[0],int) else tri,normal)
        for i,(d,h) in enumerate(profile):
            j=(i+1)%len(profile);dd,hh=profile[j]
            normal=n*(-(hh-h))+Vector((0,0,dd-d))
            face([low[i],low[j],high[j],high[i]],normal)
    def slab(left,right,near,far,top):
        prism([(near,top),(far,top),(far,top-s['slabThickness']),(near,top-s['slabThickness'])],left,right)
    def rail(left,right,near,far,bottom_near,bottom_far,embed=0):
        prism([(near,bottom_near+s['railHeight']),(far,bottom_far+s['railHeight']),
               (far,bottom_far-embed),(near,bottom_near-embed)],left,right)
    half=s['width']/2; ld=s['landingDepth']; run=s['run']; fw=s['flightWidth']; rt=s['railThickness']
    # Building-side landings remain open toward the wall. Doors are unknown.
    for level in s['levels']:
        slab(-half,half,0,ld,level)
        for side in (-1,1):
            left=-half if side<0 else half-rt
            rail(left,left+rt,0,ld,level,level)
    for bottom,top in zip(s['levels'],s['levels'][1:]):
        middle=(bottom+top)/2; rise=(top-bottom)/(2*s['risers'])
        slab(-half,half,ld+run,s['depth'],middle)
        # Outer landing guard: three sides, passage toward both flights stays open.
        for side in (-1,1):
            left=-half if side<0 else half-rt
            rail(left,left+rt,ld+run,s['depth'],middle,middle)
        rail(-half+rt,half-rt,s['depth']-rt,s['depth'],middle,middle)
        for lane,direction,base in ((s['firstLane'],1,bottom),(-s['firstLane'],-1,middle)):
            left=(s['gap']/2 if lane>0 else -half); right=left+fw
            start=ld if direction>0 else ld+run
            profile=[]
            for i in range(1,s['risers']):
                profile.extend([(start+direction*(i-1)*s['tread'],base+i*rise),
                                (start+direction*i*s['tread'],base+i*rise)])
            profile.extend([(start+direction*run,base+(top-bottom)/2-s['slabThickness']),
                            (start,base-s['slabThickness'])])
            if direction<0:profile.reverse()
            prism(profile,left,right)
            for side in (left,right-rt):
                if direction>0:low,high=base,base+(top-bottom)/2
                else:low,high=base+(top-bottom)/2,base
                rail(side,side+rt,ld,ld+run,low,high,s['slabThickness'])
