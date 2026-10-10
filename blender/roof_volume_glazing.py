"""Explicit window bands on a rooftop envelope; shared by both detail modes."""
import math


def add_roof_volume_glazing(mesh, volume, z, C):
    g = volume['glazing']
    u = (math.cos(volume['angle']), math.sin(volume['angle']))
    n = volume['outwardNormal']
    faces = {'outer': (n, volume['depth']/2, volume['width']),
             'inner': ([-v for v in n], volume['depth']/2, volume['width']),
             'start': ([-v for v in u], volume['width']/2, volume['depth']),
             'end': (u, volume['width']/2, volume['depth'])}
    for name, count in g['faces'].items():
        normal, offset, wall_span = faces[name]
        tangent = (-normal[1], normal[0])
        angle = math.atan2(tangent[1], tangent[0])
        span = wall_span-2*g['margin']
        bottom = z+volume['baseHeight']+g['sill']
        def point(along, depth, height):
            return (*[volume['center'][k]+normal[k]*(offset+depth)+tangent[k]*along
                      for k in (0, 1)], height)
        # Surface glazing, not an opening or an assertion about the interior.
        mesh.face([point(-span/2, .015, bottom), point(span/2, .015, bottom),
                   point(span/2, .015, bottom+g['height']),
                   point(-span/2, .015, bottom+g['height'])], C['glass'])
        fw = g['frameWidth']
        for height in (bottom+fw/2, bottom+g['height']-fw/2):
            mesh.box(*point(0, g['projection']/2, height), span, g['projection'], fw, C['white'], angle)
        for i in range(count+1):
            along = -(span-fw)/2+i*(span-fw)/count
            mesh.box(*point(along, g['projection']/2, bottom+g['height']/2),
                     fw, g['projection'], g['height']-2*fw, C['white'], angle)
