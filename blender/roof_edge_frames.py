"""Open post-and-beam roof frames, identical in both detail modes."""


def add_roof_edge_frames(mesh, frames, z, material):
    for frame in frames:
        post_height = frame['rise']-frame['beamHeight']
        for center in frame['posts']:
            mesh.box(*center, z+frame['baseHeight']+post_height/2,
                     frame['postWidth'], frame['postDepth'], post_height, material, frame['angle'])
        mesh.box(*frame['center'], z+frame['baseHeight']+frame['rise']-frame['beamHeight']/2,
                 frame['width'], frame['beamDepth'], frame['beamHeight'], material, frame['angle'])
