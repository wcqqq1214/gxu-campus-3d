"""Photo-calibrated window bays with shared continuous vertical piers."""
import math


def layout(facade):
    a,c=facade['start'],facade['end'];n=facade['normal'];g=facade['rule']['windowGrid']
    length=math.dist(a,c);u=[(c[k]-a[k])/length for k in (0,1)]
    bay=(length-2*g['edgeInset'])/g['columns']
    def point(t,d):return [a[k]+u[k]*t+n[k]*d for k in (0,1)]
    return g,bay,facade['height']/facade['levels'],math.atan2(u[1],u[0]),point,u,n


def add_grid_pilasters(mesh, facade, z, C):
    g,bay,fh,theta,point,_,_=layout(facade)
    bottom=max(g['firstLevel']*fh,facade.get('minimumHeight',0))
    top=facade['height']
    for column in range(g['columns']+1):
        x,y=point(g['edgeInset']+column*bay,g['pilasterDepth']/2)
        mesh.box(x,y,z+(bottom+top)/2,g['pilasterWidth'],g['pilasterDepth'],
                 top-bottom,C['white'],theta)


def add_grid_windows(mesh, facade, z, C, detail):
    g,bay,fh,theta,point,u,n=layout(facade)
    ww=bay*g['widthRatio'];wh=fh*g['heightRatio']
    for level in range(g['firstLevel'],int(facade['levels'])):
        zz=z+(level+.56)*fh
        for column in range(g['columns']):
            x,y=point(g['edgeInset']+(column+.5)*bay,.07)
            if detail:
                mesh.box(x,y,zz,ww+.12,.22,wh+.12,C['white'],theta)
                mesh.box(x+n[0]*.13,y+n[1]*.13,zz,ww,.10,wh,C['glass'],theta)
                mesh.box(x+n[0]*.20,y+n[1]*.20,zz,.045,.04,wh,C['white'],theta)
                for row in range(1,g['paneRows']):
                    mesh.box(x+n[0]*.20,y+n[1]*.20,zz-wh/2+wh*row/g['paneRows'],
                             ww,.04,.045,C['white'],theta)
            else:
                ux,uy=u[0]*ww/2,u[1]*ww/2
                mesh.face([(x-ux,y-uy,zz-wh/2),(x+ux,y+uy,zz-wh/2),
                           (x+ux,y+uy,zz+wh/2),(x-ux,y-uy,zz+wh/2)],C['glass'])
