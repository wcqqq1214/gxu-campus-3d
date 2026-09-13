"""Unequal window groups and projecting ledges; backing walls stay solid."""
import math


def frame(facade):
    a, b = facade['start'], facade['end']
    length = math.dist(a, b)
    u = [(b[k]-a[k])/length for k in (0, 1)]
    n = facade['normal']
    def point(t, depth):
        return [a[k]+u[k]*t*length+n[k]*depth for k in (0, 1)]
    return length, u, n, math.atan2(u[1], u[0]), point


def add_band_ledges(mesh, facade, z, C):
    band = facade['rule']['windowBands']
    length, _, _, theta, point = frame(facade)
    fh = facade['height']/facade['levels']
    x, y = point((band['from']+band['to'])/2, band['depth']/2)
    for level in range(band['firstLevel'], int(facade['levels'])):
        top = z+(level+.56+band['heightRatio']/2)*fh+.12
        mesh.box(x, y, top+band['thickness']/2,
                 (band['to']-band['from'])*length, band['depth'],
                 band['thickness'], C['white'], theta)


def add_band_windows(mesh, facade, z, C, detail):
    band = facade['rule']['windowBands']
    length, u, n, theta, point = frame(facade)
    fh = facade['height']/facade['levels']; wh = fh*band['heightRatio']
    for level in range(band['firstLevel'], int(facade['levels'])):
        zz = z+(level+.56)*fh
        for window in band['windows']:
            ww = (window['to']-window['from'])*length
            x, y = point((window['from']+window['to'])/2, .07)
            if detail:
                mesh.box(x, y, zz, ww+.12, .22, wh+.12, C['white'], theta)
                mesh.box(x+n[0]*.13, y+n[1]*.13, zz, ww, .10, wh, C['glass'], theta)
                for pane in range(1, window['panes']):
                    offset = -ww/2+ww*pane/window['panes']
                    mesh.box(x+u[0]*offset+n[0]*.20, y+u[1]*offset+n[1]*.20,
                             zz, .045, .04, wh, C['white'], theta)
            else:
                ux, uy = u[0]*ww/2, u[1]*ww/2
                mesh.face([(x-ux,y-uy,zz-wh/2),(x+ux,y+uy,zz-wh/2),
                           (x+ux,y+uy,zz+wh/2),(x-ux,y-uy,zz+wh/2)],C['glass'])


def band_replaces_window(facade, level, fraction, width):
    band = facade['rule'].get('windowBands')
    if band is None or level < band['firstLevel']:
        return False
    half = (width+.30)/2/math.dist(facade['start'], facade['end'])
    return fraction+half > band['from'] and fraction-half < band['to']
