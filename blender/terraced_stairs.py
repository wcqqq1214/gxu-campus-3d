"""Two flights and their grounded terrace, shared by base and near models."""
import math


def blocks_window(stairs, x, y, nx, ny, width, bottom, top):
    """Do not leave fragments of default windows cut by the solid terrace."""
    a,u,n=stairs['center'],stairs['tangent'],stairs['normal']
    if nx*n[0]+ny*n[1]<.999 or abs((x-a[0])*n[0]+(y-a[1])*n[1])>.3:
        return False
    center=(x-a[0])*u[0]+(y-a[1])*u[1]
    for offset,w,height in [(0,stairs['width'],stairs['intermediateHeight']),
                            (stairs['upperOffset'],stairs['upperWidth'],stairs['landingHeight'])]:
        if (center-width/2<offset+w/2 and center+width/2>offset-w/2
                and bottom<height and top>stairs['baseHeight']-.25):
            return True
    return False


def add_terraced_stairs(mesh, stairs, z, material):
    s=stairs;u=s['tangent'];n=s['normal'];a=s['center'];theta=math.atan2(u[1],u[0])
    def solid(offset,near,far,bottom,top,width):
        distance=(near+far)/2
        x,y=[a[k]+u[k]*offset+n[k]*distance for k in (0,1)]
        mesh.box(x,y,z+(bottom+top)/2,width,far-near,top-bottom,material,theta)
    foundation=s['baseHeight']-.25
    solid(0,0,s['terraceFront'],foundation,s['intermediateHeight'],s['width'])
    rise=(s['intermediateHeight']-s['baseHeight'])/s['lowerRisers']
    for i in range(1,s['lowerRisers']):
        near=s['terraceFront']+(i-1)*s['tread']
        solid(0,near,near+s['tread'],foundation,s['intermediateHeight']-i*rise,s['width'])
    solid(s['upperOffset'],0,s['landingDepth'],s['intermediateHeight'],s['landingHeight'],s['upperWidth'])
    rise=(s['landingHeight']-s['intermediateHeight'])/s['upperRisers']
    for i in range(1,s['upperRisers']):
        near=s['landingDepth']+(i-1)*s['tread']
        solid(s['upperOffset'],near,near+s['tread'],s['intermediateHeight'],s['landingHeight']-i*rise,s['upperWidth'])
