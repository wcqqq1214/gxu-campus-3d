"""Shared low-poly roof silhouette; dimensions remain explicit estimates."""
import math


def add_roof_dome(mesh, config, elevation, material):
    x, y = config['center']
    radius, rise = config['radius'], config['rise']
    floor = elevation + config['baseHeight']
    spring = floor + config['drumHeight']
    segments, bands = 32, 8

    def ring(r, z):
        return [(x+r*math.cos(i*math.tau/segments),
                 y+r*math.sin(i*math.tau/segments), z) for i in range(segments)]

    previous = ring(radius, floor)
    mesh.face(previous[::-1], material)
    rings = [ring(radius, spring)] + [
        ring(radius*math.cos(j*math.pi/(2*bands)),
             spring+rise*math.sin(j*math.pi/(2*bands))) for j in range(1, bands)]
    for current in rings:
        for i in range(segments):
            k = (i+1) % segments
            mesh.face([previous[i], previous[k], current[k], current[i]], material)
        previous = current
    apex = (x, y, spring+rise)
    for i in range(segments):
        mesh.face([previous[i], previous[(i+1) % segments], apex], material)
