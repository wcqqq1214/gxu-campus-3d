"""Ray stations for attached galleries, applicable to decoded and source meshes."""
import math
from mathutils import Vector


def check_galleries(b, trees, tolerance, z=0):
    samples=[]
    def hit(point,direction,limit=10):
        hits=[h[3] for tree in trees if (h:=tree.ray_cast(point,direction,limit))[0] is not None]
        return min(hits) if hits else None
    def require(kind,point,direction,expected,limit=10):
        actual=hit(point,direction,limit)
        assert actual is not None and abs(actual-expected)<=tolerance,(kind,actual,expected,list(point))
        samples.append(dict(kind=kind,errorMeters=abs(actual-expected)))
    facades=[f for f in b['form']['facades'] if 'attachedGallery' in f]
    assert len(facades)==2,'expected two east-wing gallery bays'
    for f in facades:
        a=Vector((*f['start'],z));edge=Vector((*f['end'],z))-a;length=edge.length
        u=edge.normalized();n=Vector((*f['normal'],0));p=f['attachedGallery']
        lo=p['endInset'];hi=length-lo;d=p['depth'];floor=p['floorHeight']
        def point(t,depth,h):return a+u*t+n*depth+Vector((0,0,h))
        for fraction in (.17,.39,.61,.83):
            t=lo+(hi-lo)*fraction
            distance=hit(point(t,d+.3,floor+1.5),-n)
            assert distance is not None and d+.05-tolerance<=distance<=d+.35+tolerance,('closed upper gallery',f['edge'],distance)
            samples.append(dict(kind='upper-gallery-void',edge=f['edge'],rearDistanceMeters=distance))
            require('gallery-deck',point(t,d*.5,floor+1),Vector((0,0,-1)),1)
            ceiling=f['height']-p['roofDrop']*.5-p['slabThickness']
            require('sloping-gallery-soffit',point(t,d*.5,floor+1),Vector((0,0,1)),ceiling-floor-1)
            require('lower-gallery-solid',point(t,d+.3,.3),-n,.3)
        if p.get('boundedEnds'):
            for side,offset in zip((lo,hi),(.04,-.04)):
                outer=p['outerOffsets'][0 if side==lo else 1]
                t=(side+outer)/2+offset
                require('gallery-roof-wing-join',point(t,d*.5,9),Vector((0,0,-1)),9-f['height']+p['roofDrop']*.5)
        count=math.ceil((hi-lo)/p['balusterSpacing'])
        for i in (2,4,6):
            t=lo+(hi-lo)*(i+.5)/count
            require('front-baluster',point(t,d+.3,floor+.5),-n,.3+.08-p['balusterWidth']/2)
            t=lo+(hi-lo)*(i+1)/count
            assert hit(point(t,d+.3,floor+.5),-n,.8) is None,'filled front baluster gap'
        for opening in p['upperOpenings']:
            require('upper-'+opening['kind'],point(opening['t']*length,.8,(opening['bottom']+opening['top'])/2),-n,.62)
        # No old lower-storey window remains in the now-internal rear plane.
        require('rear-lower-wall',point(length*.5,.8,1.848),-n,.8)
    return dict(passed=True,samples=samples)
