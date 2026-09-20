"""Shared closed roof-eave profile for the base and near representations."""


def replaces_parapet(config, part_id, a, b):
    return (config and config['part'] == part_id
            and ((list(a) == config['start'] and list(b) == config['end'])
                 or (list(b) == config['start'] and list(a) == config['end'])))


def add_roof_eave(mesh, config, elevation, material):
    a, b = config['start'], config['end']
    length = config['length']
    tx, ty = (b[0]-a[0])/length, (b[1]-a[1])/length
    nx, ny = config['normal']
    base = elevation + config['baseHeight']

    def ring(side, projection, height):
        coordinates = [(-side, -config['backDepth']), (length+side, -config['backDepth']),
                       (length+side, projection), (-side, projection)]
        if tx*ny-ty*nx < 0:
            coordinates.reverse()
        return [(a[0]+tx*u+nx*v, a[1]+ty*u+ny*v, base+height) for u, v in coordinates]

    lower = ring(0, 0, 0)
    shoulder = ring(config['sideOverhang'], config['projection'], config['rise'])
    upper = ring(config['sideOverhang'], config['projection'], config['rise']+config['capThickness'])
    mesh.face(lower[::-1], material)
    for bottom, top in ((lower, shoulder), (shoulder, upper)):
        for i in range(4):
            j = (i+1) % 4
            mesh.face([bottom[i], bottom[j], top[j], top[i]], material)
    mesh.face(upper, material)
