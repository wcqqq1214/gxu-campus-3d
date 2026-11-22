"""Ordinary buildings: one architectural form, two levels of facade detail."""

import hashlib
import math

import college_facades as colleges
from attached_gallery import add_attached_gallery
from attached_portico import add_attached_portico
from chemical_college import BUILDING_ID as CHEMICAL_ID
from chemical_college import chemical_college
from college_annexes import (
    ELECTRIC_CENTER,
    ENERGY,
    ENVIRONMENT,
    FOOD_ANNEX,
    INORGANIC,
    LIGHTNING,
    electric_center,
    energy_center,
    environment_center,
    food_annex,
    inorganic_lab,
    lightning_lab,
)
from college_refinements import (
    CIVIL,
    MATERIALS,
    MATERIALS_REAR,
    PHYSICS,
    PHYSICS_STREET,
    civil_details,
    materials_rear,
    materials_screen,
    physics_fronts,
)
from computer_college import RESEARCH_WING, computer_west_wing
from dining_halls import (
    BEI,
    BI,
    FLAVOR_HALF_WIDTH,
    FRONTS,
    XIU,
    bihuyuan_shell,
    north_roof,
    photographed_facade,
    place,
)
from dining_interiors import beiyuan_entry
from east27_dining import EAST27_ID, east27
from electrical_college import BUILDING_ID as ELECTRICAL_ID
from electrical_college import electrical_college
from engineering_training import BUILDING_ID as TRAINING_ID
from engineering_training import add_training_front
from facade_bands import (
    add_band_ledges,
    add_band_windows,
    add_horizontal_ledges,
    band_replaces_window,
)
from facade_corridors import add_corridor, add_corridor_openings
from facade_panels import add_panels, panel_replaces_window
from facade_windows import add_grid_pilasters, add_grid_windows
from flush_entrance import add_flush_entrance, flush_entrance_blocks_window
from food_college import BUILDING_ID as FOOD_ID
from food_college import food_college
from geometry import Mesh
from humanities_facades import (
    GATE,
    HISTORIC_PAIR,
    MANAGEMENT,
    RED_HOUSE,
    SHAW,
    YULIN,
    arts_entry_sign,
    continuing_canopy,
    continuing_roof_edge,
    continuing_street_front,
    finish,
    historic_windows,
    new_east_gatehouse,
    physics_lobby,
    red_house_ends,
    rotunda,
    rotunda_faces,
    rotunda_shell,
    shaw_front,
    yulin_front,
)
from mechanical_college import BUILDING_ID as MECHANICAL_ID
from mechanical_college import mechanical_college
from nanyuan import CANTEEN_ID, nanyuan
from new_east_neighbours import BUILDING_IDS as NEW_EAST_NEIGHBOURS
from new_east_neighbours import (
    SHOP_BUILDINGS,
    facade_details,
    shopfront_details,
    wall_finish,
)
from physics_court import court_joints
from physics_pilotis import FRAME_SLOT, SOUTH_LIGHT_BAY, open_physics_portal
from physics_pilotis import PORTAL as PHYSICS_PORTAL
from recessed_stair_entry import add_recessed_stair_entry, recessed_entry_blocks_window
from roof_crown import side_wall_blocks_window
from roof_eave import add_roof_eave, replaces_parapet
from shaw_entrance import ShawEntrance
from terraced_stairs import blocks_window as stairs_block_window
from west22 import WEST22, west22
from west23 import WEST23, west23
from west_dorms import NUMBERS as WEST_DORMS
from west_dorms import west_dorm


def compact_form_source(obj):
    """Weld source vertices without dropping groups at shared wall/roof edges."""
    from huicui import compact_source

    membership = {}
    key = lambda point: tuple(round(v, 5) for v in point)
    for vertex in obj.data.vertices:
        membership.setdefault(key(vertex.co), set()).update(
            g.group for g in vertex.groups
        )
    compact_source(obj)
    grouped = {group.index: [] for group in obj.vertex_groups}
    for vertex in obj.data.vertices:
        for group in membership.get(key(vertex.co), ()):
            grouped[group].append(vertex.index)
    for group, indices in grouped.items():
        if indices:
            obj.vertex_groups[group].add(indices, 1.0, 'REPLACE')


def wall_material(b, C):
    if b['id'] in (
        colleges.MEDICINE,
        colleges.LIFE,
        colleges.SPORTS,
        colleges.SPORTS_WING,
    ):
        return C['white']
    if b['id'] == 'way/759185166':
        return C['pink']
    if b['id'] == 'relation/11564998' and 'physicsTile' in C:
        return C['physicsTile']
    if b['id'] == 'way/880089961':
        return C['white']
    if b['id'] == XIU:
        return C['xiuIvory']
    if b['id'] in FRONTS:
        return C['stone' if b['id'] == BI else 'white']
    if b['id'] in NEW_EAST_NEIGHBOURS:
        return wall_finish(b, C)
    # A shared small palette keeps the all-campus base batched. Per-building
    # warm/cool material slots added >15% draw calls in the measured pilot.
    wall = C[
        'pink'
        if b['category'] == 'living'
        else 'stone'
        if b['category'] == 'academic'
        else 'white'
    ]
    if b['tags'].get('building:colour', '').lower() == '#f0a0a0':
        wall = C['pink']
    return wall


def shared_form(b, z, C, *, entrance_mesh=None, shaw_entry=None):
    """All silhouette-defining components; never receives a detail flag."""
    if 'stairTower' in b['form']:
        from stair_tower import stair_tower_model

        return stair_tower_model(b, z, C)
    form = b['form']
    h = form['height']
    roof = form['roof']
    wall = wall_material(b, C)
    result = Mesh()
    body = Mesh()
    top = Mesh()
    entrance = Mesh() if entrance_mesh is None else entrance_mesh
    panels = Mesh()
    parts = form['parts'] or [
        {
            'polygons': b['polygons'],
            'triangles': b['roofTriangles'],
            'height': h,
            'roof': roof,
        }
    ]
    for part in parts:
        podium_entry = shaw_entry if part.get('id') == 'front-podium' else None
        if podium_entry:
            part = podium_entry.notch_part(part)
        part_body = Mesh()
        part_wall = C[part['wallFinish']] if 'wallFinish' in part else wall
        roof = part['roof']
        h = part['height']
        triangles = (
            part['triangles']
            if roof['type'] == 'flat'
            else [[] for _ in part['polygons']]
        )
        if 'openBelow' in part:
            opening = part['openBelow']
            soffit = opening['clearHeight']
            floor = opening['floorHeight']
            roof_geometry = opening.get(
                'roofGeometry', {'polygons': part['polygons'], 'triangles': triangles}
            )
            roof_wall = C['white'] if 'slattedRoof' in opening else part_wall
            edge_finish = opening.get('slattedRoof', {}).get('edgeFinish')
            part_body.extrude(
                roof_geometry['polygons'],
                roof_geometry['triangles'],
                z + soffit,
                h - soffit,
                roof_wall,
                C['white'] if 'slattedRoof' in opening else C['paleRoof'],
                exterior_wall=C[edge_finish] if edge_finish else None,
            )
            # Explicit underside and floor; the original footprint remains the canopy outline.
            for poly, indices in zip(
                roof_geometry['polygons'], roof_geometry['triangles']
            ):
                vertices = [p for ring in poly for p in ring[:-1]]
                for i in range(0, len(indices), 3):
                    part_body.face(
                        [
                            (vertices[k][0], vertices[k][1], z + soffit)
                            for k in reversed(indices[i : i + 3])
                        ],
                        roof_wall,
                    )
            entry_floor = next(
                (
                    e['recessedStairEntry']['frameFloor']
                    for e in form['entrances']
                    if e.get('recessedStairEntry', {}).get('framePart')
                    == part.get('id')
                ),
                None,
            )
            floor_geometry = entry_floor or {
                'polygons': part['polygons'],
                'triangles': triangles,
            }
            part_body.extrude(
                floor_geometry['polygons'],
                floor_geometry['triangles'],
                z - 0.15,
                floor + 0.15,
                C['stone'],
                C['stone'],
            )
            for column in opening['columns']:
                column_material = (
                    C[column['finish']] if 'finish' in column else part_wall
                )
                if column.get('shape') == 'cylinder':
                    base = column.get('base')
                    bottom = floor + (base['height'] if base else 0)
                    capital = column.get('capital')
                    shaft_top = soffit - (capital['height'] if capital else 0)
                    part_body.cylinder(
                        *column['center'],
                        z + (bottom + shaft_top) / 2,
                        column['width'] / 2,
                        shaft_top - bottom,
                        column_material,
                        n=16,
                    )
                    if capital:
                        taper = capital['taperHeight']
                        radius = column['width'] / 2 + capital['projection']
                        part_body.cylinder(
                            *column['center'],
                            z + shaft_top + taper / 2,
                            column['width'] / 2,
                            taper,
                            column_material,
                            n=16,
                            topr=radius,
                        )
                        part_body.cylinder(
                            *column['center'],
                            z + (shaft_top + taper + soffit) / 2,
                            radius,
                            capital['height'] - taper,
                            column_material,
                            n=16,
                        )
                    if base:
                        base_height = base['height']
                        cap = base['capHeight']
                        radius = column['width'] / 2 + base['projection']
                        part_body.cylinder(
                            *column['center'],
                            z + floor + (base_height - cap) / 2,
                            radius,
                            base_height - cap,
                            column_material,
                            n=16,
                        )
                        part_body.cylinder(
                            *column['center'],
                            z + floor + base_height - cap / 2,
                            radius + 0.03,
                            cap,
                            column_material,
                            n=16,
                        )
                else:
                    part_body.box(
                        *column['center'],
                        z + (floor + soffit) / 2,
                        column['width'],
                        column['depth'],
                        soffit - floor,
                        column_material,
                        column['angle'],
                    )
        else:
            roof_material = (
                C['red']
                if b['id'] == XIU
                else C['blueRoof']
                if roof.get('finish') == 'blue-metal'
                else C['paleRoof']
            )
            top_indices = (
                [[] for _ in part['polygons']] if 'inset' in roof else triangles
            )
            depth = part.get('baseDepth', 0.5)
            hall_entry = next(
                (
                    e['recessedStairEntry']
                    for e in form['entrances']
                    if 'hall' in e.get('recessedStairEntry', {})
                    and e['recessedStairEntry']['hall']['part'] == part.get('id')
                ),
                None,
            )
            if hall_entry:
                hall = hall_entry['hall']
                floor = hall_entry['doorLandingHeight']
                ceiling = floor + hall['clearHeight']
                empty = [[] for _ in part['polygons']]
                # The opening is a real omission of wall geometry. Keep the
                # mapped footprint and roof above it exactly where they were.
                part_body.extrude(
                    part['polygons'],
                    empty,
                    z - depth,
                    floor + depth,
                    part_wall,
                    part_wall,
                )
                cut = hall['wallGeometry']
                part_body.extrude(
                    cut['polygons'],
                    [[] for _ in cut['polygons']],
                    z + floor,
                    hall['clearHeight'],
                    part_wall,
                    part_wall,
                )
                part_body.extrude(
                    part['polygons'],
                    top_indices,
                    z + ceiling,
                    h - ceiling,
                    part_wall,
                    roof_material,
                )
            elif b['id'] == colleges.SPORTS_WING:
                # The east wall, including its openings, is built by sports_wing.
                colleges.sports_wing_shell(
                    part_body,
                    part['polygons'][0][0],
                    z,
                    depth,
                    h,
                    part_wall,
                    roof_material,
                )
            else:
                part_body.extrude(
                    part['polygons'],
                    top_indices,
                    z - depth,
                    h + depth,
                    part_wall,
                    roof_material,
                )
            if 'inset' in roof:
                for key, material in [
                    ('borderGeometry', C['dark']),
                    ('centerGeometry', roof_material),
                ]:
                    geometry = roof[key]
                    for poly, indices in zip(
                        geometry['polygons'], geometry['triangles']
                    ):
                        points = [p for ring in poly for p in ring[:-1]]
                        for i in range(0, len(indices), 3):
                            part_body.face(
                                [
                                    (points[k][0], points[k][1], z + h)
                                    for k in indices[i : i + 3]
                                ],
                                material,
                            )
        for facade in form.get('facades', []):
            if (
                facade['part'] == part.get('id', 'body')
                and 'wallFinish' in facade['rule']
            ):
                from facade_finish import apply_wall_finish

                apply_wall_finish(part_body, facade, z, C[facade['rule']['wallFinish']])
            if (
                facade['part'] == part.get('id', 'body')
                and 'openCorridor' in facade['rule']
                and not (b['id'] == PHYSICS and facade['edge'] == 16)
            ):
                if podium_entry and facade['edge'] == 8:
                    continue
                if podium_entry and facade['edge'] == 9:
                    facade = podium_entry.west_corridor()
                corridor = facade['rule']['openCorridor']
                finish = corridor.get('finish', {})
                front_arcade = (
                    b['id'] == SHAW
                    and corridor['firstLevel'] == 0
                    and 'shawPinkGranite' in C
                )
                wall_color = C[finish['wall']] if 'wall' in finish else wall
                if b['id'] == 'way/1501460953' and facade['edge'] in (4, 6):
                    wall_color = wall
                add_corridor(
                    part_body,
                    facade,
                    z,
                    C['shawPinkGranite'] if front_arcade else wall_color,
                    C['shawPinkGranite'] if front_arcade else C['white'],
                    C[finish.get('rail', 'white')],
                    pitched_roof=roof['type'] != 'flat',
                )
                opening_colors = {**C, 'white': C['dark']} if front_arcade else C
                add_corridor_openings(part_body, facade, z, opening_colors)
        if podium_entry:
            podium_entry.face_returns(part_body, C['shawPinkGranite'])
        custom_rotunda = (
            b['id'] == MANAGEMENT
            and part.get('id') == 'main'
            and any(f['rule'].get('panels') for f in form.get('facades', []))
        )
        if custom_rotunda:
            rotunda_shell(part_body, b, z, C)
        if b['id'] == PHYSICS and part.get('id') == 'body':
            open_physics_portal(part_body, b, z, C)
        body.extend(part_body)
        if roof['type'] != 'flat':
            geometry = roof['geometry']
            for face in geometry.get('boundaryWalls', []):
                top.face([(x, y, z + h + up) for x, y, up in face], part_wall)
            roof_material = C['paleRoof'] if roof['type'] == 'profiled' else C['red']
            for i in range(0, len(geometry['triangles']), 3):
                top.face(
                    [
                        (
                            geometry['vertices'][k][0],
                            geometry['vertices'][k][1],
                            z + h + geometry['vertices'][k][2],
                        )
                        for k in geometry['triangles'][i : i + 3]
                    ],
                    roof_material,
                )
        elif (
            b['id'] not in (colleges.MEDICINE, colleges.HALL, colleges.SPORTS_WING)
            and 'slattedRoof' not in part.get('openBelow', {})
            and 'rim' not in roof
        ):
            # Parapets follow each actual terrace elevation in both LODs.
            edges = part.get(
                'parapetEdges',
                [
                    (a, c)
                    for poly in part['polygons']
                    for ring in poly
                    for a, c in zip(ring, ring[1:])
                ],
            )
            crown = form.get('roofCrown')
            if crown and crown['part'] == part.get('id', 'body'):
                edges = crown['retainedParapetEdges']
            screen = form.get('gableScreen')
            if screen and screen['part'] == part.get('id', 'body'):
                edges = screen['retainedParapetEdges']
            # The approved 44.1 m design envelope includes an unallocated 1.8 m
            # above the 42.3 m storey stack. Represent it as an estimated upper
            # roof edge only on the tallest parts, pending the as-built section.
            rim_height = (
                44.1 - h
                if b['id'] == colleges.LAB and part['id'].endswith('-top')
                else 0.8
            )
            if custom_rotunda:
                curved = {
                    (tuple(f['start']), tuple(f['end'])) for f in rotunda_faces(b)
                }
                edges = [(a, c) for a, c in edges if (tuple(a), tuple(c)) not in curved]
            for a, c in edges:
                if replaces_parapet(form.get('roofEave'), part.get('id', 'body'), a, c):
                    continue
                length = math.dist(a, c)
                if length < 2:
                    continue
                if (
                    b['id'] == 'way/1501460953'
                    and form['levels'] == 6
                    and continuing_roof_edge(top, a, c, z + h, C)
                ):
                    continue
                parapet_height = (
                    0.26
                    if b['id'] == 'way/880089961' and 'openBelow' in part
                    else rim_height
                )
                if b['id'] == 'way/759165563':
                    parapet_height = 1.12
                top.box(
                    (a[0] + c[0]) / 2,
                    (a[1] + c[1]) / 2,
                    z + h + parapet_height / 2,
                    length,
                    0.25,
                    parapet_height,
                    C['white'],
                    math.atan2(c[1] - a[1], c[0] - a[0]),
                )
        if 'rimGeometry' in roof:
            for face in roof['rimGeometry']['tops'] + roof['rimGeometry']['walls']:
                top.face([(x, y, z + h + up) for x, y, up in face], C['white'])
    if 'roofDome' in form:
        from roof_dome import add_roof_dome

        add_roof_dome(top, form['roofDome'], z, C['white'])
    for volume in form.get('roofVolumes', []):
        top.box(
            *volume['center'],
            z + volume['baseHeight'] + volume['rise'] / 2,
            volume['width'],
            volume['depth'],
            volume['rise'],
            C['white'],
            volume['angle'],
        )
        if 'cap' in volume:
            cap = volume['cap']
            top.box(
                *volume['center'],
                z + volume['baseHeight'] + volume['rise'] + cap['height'] / 2,
                volume['width'] + 2 * cap['overhang'],
                volume['depth'] + 2 * cap['overhang'],
                cap['height'],
                C['paleRoof'],
                volume['angle'],
            )
        if 'glazing' in volume:
            from roof_volume_glazing import add_roof_volume_glazing

            add_roof_volume_glazing(top, volume, z, C)
    if 'roofEdgeFrames' in form:
        from roof_edge_frames import add_roof_edge_frames

        add_roof_edge_frames(top, form['roofEdgeFrames'], z, C['white'])
    if 'roofEave' in form:
        add_roof_eave(top, form['roofEave'], z, C['white'])
    if 'roofCrown' in form:
        from roof_crown import add_roof_crown

        add_roof_crown(top, form['roofCrown'], z, C)
    if 'gableScreen' in form:
        from gable_screen import add_gable_screen

        add_gable_screen(top, form['gableScreen'], z, C)
    for facade in form.get('facades', []):
        if 'attachedGallery' in facade:
            add_attached_gallery(body, facade, z, wall, C)
        if 'panels' in facade['rule']:
            panel_colors = C
            if b['id'] == YULIN and any(
                p['type'] == 'round-window-wall' for p in facade['rule']['panels']
            ):
                panel_colors = {**C, 'white': C['pink']}
            if (
                b['id'] == SHAW
                and facade['part'] == 'front-podium'
                and facade['edge'] in (7, 8, 9)
                and 'shawCurtainGlass' in C
            ):
                if facade['edge'] == 8:
                    continue
                panel_colors = {
                    **C,
                    'glass': C['shawCurtainGlass'],
                    'dark': C['shawGlazingFrame'],
                }
            add_panels(panels, facade, z, panel_colors)
        if 'windowGrid' in facade['rule']:
            add_grid_pilasters(body, facade, z, C)
        if 'windowBands' in facade['rule']:
            add_band_ledges(body, facade, z, C)
        if 'horizontalLedges' in facade['rule']:
            add_horizontal_ledges(body, facade, z, C)
    for door in form.get('stairAccessDoors', []):
        from stair_tower import stair_access_door

        stair_access_door(entrance, door, z, C)
    for e in form['entrances'] if entrance_mesh is None else []:
        if 'recessedStairEntry' in e:
            add_recessed_stair_entry(entrance, e, z, C)
            continue
        if 'flushEntrance' in e:
            add_flush_entrance(entrance, e, z, C)
            continue
        if 'mappedCanopy' in e:
            from mapped_canopy_entry import add_mapped_canopy_entry

            if b['id'] == 'way/759165563' and any(
                f['rule'].get('windowBands') for f in form.get('facades', [])
            ):
                shelter = e['shelter']
                e = {
                    **e,
                    'shelter': {
                        **shelter,
                        'floorHeight': shelter['floorHeight'] + 0.36,
                        'doorHeight': shelter['doorHeight'] - 0.36,
                    },
                }
            add_mapped_canopy_entry(entrance, e, z, C)
            continue
        if 'attachedPortico' in e:
            add_attached_portico(entrance, e, z, C)
            if b['id'] == 'relation/11564998' and e['id'] == 'south-glazed-entry':
                physics_lobby(entrance, e, z, C, form)
            continue
        x, y = e['center']
        bearing = math.radians(e['bearing'])
        nx, ny = math.sin(bearing), math.cos(bearing)
        theta = -bearing
        width = e['width']
        if e.get('porticoId'):
            floor = e['platformHeight']
            front = e['outerCenter']
            pw = e.get('stepWidth', e['porticoWidth'])
            if 'recessGlazing' in e:
                from recess_glazing import add_recess_glazing

                add_recess_glazing(entrance, e, z, C)
            else:
                entrance.box(
                    x + nx * 0.04,
                    y + ny * 0.04,
                    z + floor + 1.4,
                    width,
                    0.10,
                    2.8,
                    C['glass'],
                    theta,
                )
                door = e.get('recessDoor')
                if door:
                    fw = door['frameWidth']
                    tx, ty = ny, -nx
                    for i in range(door['leafCount'] + 1):
                        offset = (
                            -width / 2 + fw / 2 + (width - fw) * i / door['leafCount']
                        )
                        entrance.box(
                            x + tx * offset + nx * 0.14,
                            y + ty * offset + ny * 0.14,
                            z + floor + 1.4,
                            fw,
                            0.10,
                            2.8,
                            C['dark'],
                            theta,
                        )
                    for up in (fw / 2, 2.8 - fw / 2):
                        entrance.box(
                            x + nx * 0.14,
                            y + ny * 0.14,
                            z + floor + up,
                            width,
                            0.10,
                            fw,
                            C['dark'],
                            theta,
                        )
                    lh = door['lintelHeight']
                    entrance.box(
                        x + nx * 0.06,
                        y + ny * 0.06,
                        z + floor + 2.8 + lh / 2,
                        width + 0.2,
                        0.14,
                        lh,
                        C['stone'],
                        theta,
                    )
                else:
                    entrance.box(
                        x + nx * 0.06,
                        y + ny * 0.06,
                        z + floor + 2.83,
                        width + 0.2,
                        0.14,
                        0.12,
                        C['white'],
                        theta,
                    )
            # Counts can be sourced separately from estimated dimensions.
            steps = e.get('steps', 3)
            step_base = e.get('stepBaseHeight', 0)
            foundation = e.get('stepFoundationDepth', 0)
            for i in range(steps):
                height = (floor - step_base) * (steps - i) / steps
                entrance.box(
                    front[0] + nx * (i + 0.5) * 0.3,
                    front[1] + ny * (i + 0.5) * 0.3,
                    z + step_base + (height - foundation) / 2,
                    pw,
                    0.32,
                    height + foundation,
                    C['stone'],
                    theta,
                )
            continue
        # Reuse facade glass and stone to avoid two extra draw calls per chunk.
        landing = e.get('landingHeight', 0)
        frame = e.get('doorFrame')
        if frame:
            bay = width / frame['bays']
            pw = frame['pierWidth']
            pd = frame['pierDepth']
            tx, ty = ny, -nx
            for i in range(frame['bays']):
                offset = -width / 2 + (i + 0.5) * bay
                entrance.box(
                    x + tx * offset,
                    y + ty * offset,
                    z + landing + 1.3,
                    bay - pw,
                    0.35,
                    2.6,
                    C['glass'],
                    theta,
                )
            for i in range(frame['bays'] + 1):
                offset = -width / 2 + i * bay
                entrance.box(
                    x + tx * offset + nx * (pd / 2 - 0.2),
                    y + ty * offset + ny * (pd / 2 - 0.2),
                    z + landing + 2.775 / 2,
                    pw,
                    pd,
                    2.775,
                    C['stone'],
                    theta,
                )
            # The continuous header meets the existing canopy soffit. There
            # is no glass hidden behind the intermediate solid piers.
            entrance.box(
                x + nx * (pd / 2 - 0.2),
                y + ny * (pd / 2 - 0.2),
                z + landing + (2.6 + 2.775) / 2,
                width + pw,
                pd,
                0.175,
                C['stone'],
                theta,
            )
        else:
            entrance.box(x, y, z + landing + 1.3, width, 0.35, 2.6, C['glass'], theta)
        if (
            b['id'] == 'way/1501460953'
            and e['id'] == 'north-court'
            and 'stairFlight' in e
        ):
            continuing_canopy(entrance, e, z, C)
        else:
            entrance.box(
                x, y, z + landing + 2.9, width + 1.3, 2.5, 0.25, C['white'], theta
            )
        if 'stairFlight' in e:
            p = e['stairFlight']
            bottom = p['baseHeight'] - 0.15
            entrance.box(
                x + nx * (p['landingDepth'] - 0.15) / 2,
                y + ny * (p['landingDepth'] - 0.15) / 2,
                z + (landing + bottom) / 2,
                p['width'],
                p['landingDepth'] + 0.15,
                landing - bottom,
                C['stone'],
                theta,
            )
            for i in range(1, p['riserCount']):
                stair_top = landing - (landing - p['baseHeight']) * i / p['riserCount']
                distance = p['landingDepth'] + (i - 0.5) * p['tread']
                entrance.box(
                    x + nx * distance,
                    y + ny * distance,
                    z + (stair_top + bottom) / 2,
                    p['width'],
                    p['tread'] + 0.01,
                    stair_top - bottom,
                    C['stone'],
                    theta,
                )
        elif landing:
            # Explicitly calibrated two-level landing: both solids reach
            # below the building datum, rather than floating thin slabs.
            for distance, w, depth, landing_top in [
                (0.65, width + 1.2, 1.6, landing),
                (0.9, width + 1.6, 2, landing / 2),
            ]:
                entrance.box(
                    x + nx * distance,
                    y + ny * distance,
                    z + (landing_top - 0.15) / 2,
                    w,
                    depth,
                    landing_top + 0.15,
                    C['stone'],
                    theta,
                )
        else:
            entrance.box(
                x + nx * 0.65,
                y + ny * 0.65,
                z + 0.12,
                width + 1.2,
                1.6,
                0.20,
                C['stone'],
                theta,
            )
            entrance.box(
                x + nx * 0.9,
                y + ny * 0.9,
                z + 0.035,
                width + 1.6,
                2,
                0.08,
                C['stone'],
                theta,
            )
    if 'terracedStairs' in form:
        from terraced_stairs import add_terraced_stairs

        add_terraced_stairs(entrance, form['terracedStairs'], z, C['stone'])
    if b['id'] == BEI:
        top.extend(north_roof(b, z, C))
    if b['id'] == PHYSICS:
        from physics_east_front import east_shell

        east_shell(body, top, b, z, C)
    result.add_part('01_主体轮廓', body)
    result.add_part('02_屋顶轮廓', top)
    result.add_part('03_入口与平台', entrance)
    if panels.f:
        result.add_part('05_立面专项', panels)
    return result


def facade_segments(b):
    if 'facades' in b['form']:
        return b['form']['facades']
    result = []
    for poly in b['polygons']:
        for ri, ring in enumerate(poly):
            area = sum(a[0] * c[1] - c[0] * a[1] for a, c in zip(ring, ring[1:]))
            sign = (1 if area > 0 else -1) * (-1 if ri else 1)
            for a, c in zip(ring, ring[1:]):
                length = math.dist(a, c)
                if length < 0.01:
                    continue
                result.append(
                    {
                        'start': a,
                        'end': c,
                        'normal': [
                            (c[1] - a[1]) / length * sign,
                            -(c[0] - a[0]) / length * sign,
                        ],
                        'height': b['form']['height'],
                        'levels': b['form']['levels'],
                        'rule': {},
                    }
                )
    return result


COLLEGE_MODELS = {
    MECHANICAL_ID: mechanical_college,
    CHEMICAL_ID: chemical_college,
    ELECTRICAL_ID: electrical_college,
    FOOD_ID: food_college,
    LIGHTNING: lightning_lab,
    INORGANIC: inorganic_lab,
    ENERGY: energy_center,
    RESEARCH_WING: computer_west_wing,
    FOOD_ANNEX: food_annex,
    ENVIRONMENT: environment_center,
    ELECTRIC_CENTER: electric_center,
}

# Edge indices follow the outer footprint in buildings.json. Other edges and
# floors continue through the ordinary window generator, including trim in
# high detail. Filtering windows before emission keeps every frame complete.
COLLEGE_CUSTOM_EDGES = {
    MECHANICAL_ID: {5, 6},
    CHEMICAL_ID: {2, 3, 5, 7, 8, 9, 10, 11, 13},
    TRAINING_ID: {0, 1, 2, 3},
    FOOD_ID: {3, 4, 5, 6, 7, 8, 9, 10, 12},
    ELECTRICAL_ID: {1},
    LIGHTNING: {3},
    RESEARCH_WING: {2, 3},
    INORGANIC: {9, 11},
    FOOD_ANNEX: {3, 4, 5, 6},
    ELECTRIC_CENTER: {*range(11), 16, 17},
    ENVIRONMENT: {1, 3},
}
COLLEGE_LEVELS = {
    RESEARCH_WING: (8, 30.5),
    FOOD_ANNEX: (4, 14.8),
    ENVIRONMENT: (7, 25.1),
    ELECTRIC_CENTER: (6, 21.2),
    FOOD_ID: (6, 20.6),
    INORGANIC: (6, 23.45),
    CHEMICAL_ID: (5, 17.3),
}


def ordinary_building(b, z, C, detail):
    if b.get('form', {}).get('version') != 1:
        raise ValueError(
            f'{b["id"]}: run data:prepare before rebuilding ordinary buildings'
        )
    if b['id'] == PHYSICS:
        from physics_east_front import fit_upper_storeys, source_grid

        physics_roof = b['height']
        b = source_grid(b)
    from student_water_tower import TOWER_ID, water_tower

    if b['id'] == GATE and b['form']['levels'] == 1:
        return new_east_gatehouse(b, z, C, detail)
    if b['id'] in WEST_DORMS:
        return west_dorm(b, z, C, detail)
    if b['id'] == WEST23:
        return west23(b, z, C, detail)
    if b['id'] == WEST22:
        return west22(b, z, C, detail)
    if b['id'] == EAST27_ID:
        return east27(b, z, C, detail)
    if b['id'] == TOWER_ID:
        return water_tower(b, z, C, detail)
    if b['id'] == CANTEEN_ID:
        return nanyuan(b, z, C, detail)
    if b['id'] == 'relation/11564998' and any(
        e['id'] == 'south-glazed-entry' for e in b['form']['entrances']
    ):
        C = {
            **C,
            'glass': finish(
                C, 'physicsBlueGreenGlass', (0.15, 0.28, 0.255), 0.22, 0.32
            ),
            'physicsTile': finish(C, 'physicsWarmTile', (0.66, 0.55, 0.48), 0.78),
        }
    if b['id'] == 'way/1501460953' and any(
        e['id'] == 'north-court' for e in b['form']['entrances']
    ):
        C = {
            **C,
            'glass': finish(
                C, 'continuingDoorGlass', (0.088, 0.105, 0.093), 0.32, 0.20
            ),
        }
    if b['id'] == YULIN and b['form'].get('roofVolumes'):
        C = {
            **C,
            'glass': finish(C, 'yulinGreyGlass', (0.16, 0.175, 0.17), 0.30, 0.23),
            'pink': finish(C, 'yulinPaleRender', (0.70, 0.62, 0.58), 0.84),
        }
    if b['id'] in ('way/759165563', 'way/880089961'):
        # The independent canopy and the west courtyard share a buff stone finish.
        # The college's frontal photograph also shows smoky windows and dark doors.
        trim = finish(C, 'artsCourtyardStone', (0.49, 0.395, 0.32), 0.79)
        C = {
            **C,
            'glass': finish(C, 'artsCourtyardGlass', (0.074, 0.085, 0.089), 0.27, 0.25),
            'pink': finish(C, 'artsCourtyardPlaster', (0.63, 0.46, 0.38), 0.86),
            'white': trim,
        }
    hall_fronts = FRONTS.get(b['id'], {})
    pane_glass = C['glass']
    windows = Mesh()
    entrance = None
    if hall_fronts:
        entrance, windows = photographed_facade(b, z, C, detail)
        pane_glass = C['xiuBlueGlass' if b['id'] == XIU else 'residenceGlass']
    if b['id'] == CIVIL:
        # One complete entrance in both LODs; the generic axis-aligned
        # flush canopy would otherwise remain below the two oblique eaves.
        entrance, civil_finish = civil_details(b, z, C, detail)
    if b['id'] in (
        colleges.MEDICINE,
        colleges.SPORTS,
        colleges.SPORTS_WING,
        colleges.LIFE,
        colleges.HALL,
        colleges.EAST_GYM,
        colleges.REPRODUCTION_INSTITUTE,
    ):
        entrance = Mesh()
    if b['id'] == BI:
        b = bihuyuan_shell(b)
    shaw_entry = None
    if b['id'] == SHAW and any(p['id'] == 'stair-core' for p in b['form']['parts']):
        shaw_entry = ShawEntrance(b)
        # The primary door is an explicit opening on the recessed arcade wall.
        C = {
            **C,
            'shawPinkGranite': finish(C, 'shawPinkGranite', (0.30, 0.164, 0.132), 0.57),
            'shawDoorGlass': finish(
                C, 'shawDoorGlass', (0.023, 0.028, 0.027), 0.24, 0.32
            ),
            'shawCurtainGlass': finish(
                C, 'shawCurtainGlass', (0.24, 0.25, 0.26), 0.105, 0.74
            ),
            'shawGlazingFrame': finish(
                C, 'shawGlazingFrame', (0.039, 0.031, 0.028), 0.36, 0.55
            ),
            'glass': finish(C, 'shawSmokedGlass', (0.13, 0.14, 0.145), 0.13, 0.66),
        }
        entrance = Mesh()
    if b['id'] == YULIN and any(
        f['edge'] == 6 and 'openCorridor' in f['rule']
        for f in b['form'].get('facades', [])
    ):
        entrance = Mesh()
    glazed_rotunda = (
        b['id'] == MANAGEMENT
        and any(p['id'] == 'main' for p in b['form']['parts'])
        and any(f['rule'].get('panels') for f in b['form'].get('facades', []))
    )
    if glazed_rotunda:
        C = {
            **C,
            'glass': finish(C, 'managementGreenGlass', (0.18, 0.27, 0.25), 0.27, 0.36),
        }
        entrance = Mesh()
    builder = COLLEGE_MODELS.get(b['id'])
    college = builder is not None or b['id'] == TRAINING_ID
    if builder:
        m = builder(b, z, C, detail)
        if b['id'] == ENERGY:
            return m
    else:
        m = shared_form(b, z, C, entrance_mesh=entrance, shaw_entry=shaw_entry)
        if b['id'] == TRAINING_ID:
            add_training_front(b, m, z, C, detail)
    if (
        b['id'] == 'way/759165563'
        and any(e.get('shelter') for e in b['form']['entrances'])
        and any(f['rule'].get('windowBands') for f in b['form'].get('facades', []))
    ):
        m.add_part('西门院名与窗间壁柱', arts_entry_sign(b, z, C))
    if b['id'] == RED_HOUSE and b['form']['roof']['type'] == 'hipped':
        m.add_part('端部山花、外墙与踏步', red_house_ends(b, z, C))
    if b['id'] in HISTORIC_PAIR and any(
        f['rule'].get('panels') for f in b['form'].get('facades', [])
    ):
        m.add_part('三层窗间板与首层竖窗', historic_windows(b, z, C))
    if shaw_entry:
        m.add_part('南廊腰线与邵逸夫楼塔面', shaw_front(b, z, C, shaw_entry))
    if b['id'] == YULIN and 'roofVolumes' in b['form']:
        m.add_part('育林楼中央弧饰与重檐', yulin_front(b, z, C, detail))
    if glazed_rotunda:
        m.add_part('圆厅柱列与幕墙腰线', rotunda(b, z, C))
    if b['id'] in NEW_EAST_NEIGHBOURS:
        facades = facade_segments(b)
        if (
            b['id'] == 'way/1501460953'
            and b['form']['levels'] == 6
            and any(f['edge'] == 2 and 'windowBands' in f['rule'] for f in facades)
        ):
            m.add_part('沿街窗下板与壁柱', continuing_street_front(b, z, C))
        m.add_part('04_立面窗格', facade_details(b, z, C, detail, facades))
        if b['id'] in SHOP_BUILDINGS:
            m.add_part('05_临街店面', shopfront_details(b, z, C, detail, facades))
        return m
    if 'stairTower' in b['form']:
        return m
    form = b['form']
    h = form['height']
    wall = wall_material(b, C)
    seed = int(hashlib.sha256(b['id'].encode()).hexdigest()[:8], 16)
    levels = max(1, round(form['levels']))
    balconies = form['archetype'] in ('dormitory', 'residential-block')
    flavor_center = (
        next(
            (
                entry['center']
                for entry in form['entrances']
                if entry['id'] == 'flavor-east'
            ),
            None,
        )
        if b['id'] == BI
        else None
    )
    for edge, facade in enumerate(facade_segments(b)):
        if b['id'] in (colleges.LAB, colleges.HALL) or (
            facade.get('ring', 0) == 0
            and facade.get('edge', edge) in colleges.PHOTO_EDGES.get(b['id'], ())
        ):
            continue
        a, c = facade['start'], facade['end']
        rule = facade['rule']
        if b['id'] == XIU and edge in (3, 5):
            # These short returns have continuous glazing to the west entrance.
            continue
        if (
            b['id'] == MATERIALS
            and facade.get('part') == 'high-body'
            and facade.get('edge') in MATERIALS_REAR
        ):
            continue
        if rule.get('windows') is False:
            continue
        if 'windowGrid' in rule:
            add_grid_windows(windows, facade, z, C, detail)
            continue
        if 'windowBands' in rule:
            add_band_windows(windows, facade, z, C, detail)
        h = facade['height']
        levels = max(1, round(facade['levels']))
        dx, dy = c[0] - a[0], c[1] - a[1]
        length = math.hypot(dx, dy)
        if college:
            if edge in COLLEGE_CUSTOM_EDGES[b['id']]:
                continue
            levels, h = COLLEGE_LEVELS.get(b['id'], (levels, h))
            if b['id'] == MECHANICAL_ID:
                levels, h = 6, 22.2
            if b['id'] == CHEMICAL_ID and edge in (0, 1):
                levels, h = 6, 19.4
            if b['id'] == FOOD_ID and edge in (1, 2):
                levels, h = 6, 19.1
            if b['id'] == LIGHTNING:
                levels, h = 3, 11.6
        if length < 2:
            continue
        nx, ny = facade['normal']
        theta = math.atan2(dy, dx)
        num = max(1, int(length / rule.get('spacing', 4)))
        floor_heights = facade.get('floorHeights')
        for level in range(levels):
            if b['id'] == PHYSICS and edge == 16 and level == 4:
                continue  # The east gallery carries its own inset window wall.
            if b['id'] == PHYSICS and edge in PHYSICS_STREET and level != 4:
                if level > 0 or edge in (15, 16, 17):
                    continue
            if level in hall_fronts.get(
                facade.get('edge', edge), ()
            ) or level in rule.get('skipWindowLevels', []):
                continue
            floor_bottom = (
                math.fsum(floor_heights[:level])
                if floor_heights
                else level * h / levels
            )
            floor_height = floor_heights[level] if floor_heights else h / levels
            if (
                level == 0
                and b['id'] == 'relation/11564703'
                and facade.get('ring', 0) == 0
                and facade.get('edge') == 5
            ):
                # Forestry's photographed ground-floor grilles flank the south porch.
                continue
            gallery = facade.get('attachedGallery')
            if gallery and level > 0:
                continue
            corridor = rule.get('openCorridor')
            if corridor and any(
                level in opening['levels'] for opening in corridor.get('openings', [])
            ):
                # Explicit rear-wall openings replace this complete row only;
                # ordinary rows and bounded bands on other floors stay intact.
                continue
            recessed = corridor is not None and corridor[
                'firstLevel'
            ] <= level <= corridor.get('lastLevel', levels - 1)
            for i in range(num):
                f = (i + 0.5) / num
                x, y = a[0] + dx * f + nx * 0.07, a[1] + dy * f + ny * 0.07
                if b['id'] == PHYSICS and edge == 2 and level == levels - 1:
                    from physics_east_front import JOINT

                    if JOINT[0] < y < JOINT[1]:
                        continue  # The glazed link stops one storey below the two wings.
                if (
                    b['id'] == PHYSICS
                    and edge == 10
                    and level <= 4
                    and PHYSICS_PORTAL[0] - 1.2 < y < PHYSICS_PORTAL[1] + 1.2
                ):
                    continue
                if b['id'] == PHYSICS and (
                    (
                        edge == 10
                        and 1 <= level <= 3
                        and FRAME_SLOT[0] - 1.2 < y < FRAME_SLOT[1] + 1.2
                    )
                    or (
                        edge == 2
                        and level == 4
                        and SOUTH_LIGHT_BAY[0] - 1.2 < y < SOUTH_LIGHT_BAY[1] + 1.2
                    )
                ):
                    continue
                if b['id'] == INORGANIC and edge == 5 and -551.0 < x < -533.18:
                    continue
                if b['id'] == FOOD_ID and edge == 0 and x > -607.03 and level >= 5:
                    continue
                if b['id'] == FOOD_ANNEX and x > -598.87 and level >= 2:
                    continue
                if college and b['id'] == MECHANICAL_ID:
                    if (x >= -261.35 and level >= 5) or (edge in (3, 4) and level > 0):
                        continue
                if (
                    college
                    and b['id'] == ELECTRICAL_ID
                    and edge in (0, 2)
                    and y < -819.7
                ):
                    continue
                if (
                    flavor_center
                    and edge == 0
                    and level == 1
                    and math.dist((x, y), flavor_center) < FLAVOR_HALF_WIDTH
                ):
                    continue
                if gallery:
                    x += nx * gallery['depth']
                    y += ny * gallery['depth']
                if recessed:
                    if (
                        not corridor['endInset'] + 0.2
                        < f * length
                        < length - corridor['endInset'] - 0.2
                    ):
                        continue
                    x -= nx * corridor['depth']
                    y -= ny * corridor['depth']
                # Preserve the original arithmetic for uncalibrated facades,
                # keeping unrelated compressed assets reproducible.
                zz = (
                    z + floor_bottom + 0.56 * floor_height
                    if floor_heights
                    else z + (level + 0.56) * h / levels
                )
                ww = min(2.1, length / num * 0.60)
                wh = min(1.9, floor_height * 0.55)
                if band_replaces_window(facade, level, f, ww):
                    continue
                if panel_replaces_window(facade, f, ww, zz - z, wh):
                    continue
                if zz - wh / 2 < z + facade.get('minimumHeight', 0):
                    continue
                if 'terracedStairs' in form and stairs_block_window(
                    form['terracedStairs'],
                    x,
                    y,
                    nx,
                    ny,
                    ww + 0.3,
                    zz - z - (wh + 0.3) / 2,
                    zz - z + (wh + 0.3) / 2,
                ):
                    continue
                if 'roofCrown' in form and side_wall_blocks_window(
                    form['roofCrown'],
                    x,
                    y,
                    nx,
                    ny,
                    ww + 0.3,
                    zz - z - (wh + 0.3) / 2,
                    zz - z + (wh + 0.3) / 2,
                ):
                    continue
                blocked_by_door = False
                for entry in form['entrances']:
                    if recessed_entry_blocks_window(
                        entry, x, y, nx, ny, zz - z - wh / 2, zz - z + wh / 2, ww
                    ):
                        blocked_by_door = True
                        break
                    if flush_entrance_blocks_window(
                        entry, x, y, nx, ny, zz - z - wh / 2, zz - z + wh / 2, ww
                    ):
                        blocked_by_door = True
                        break
                    if (
                        'attachedPortico' not in entry
                        and 'doorFrame' not in entry
                        and 'shelter' not in entry
                        and not floor_heights
                    ):
                        continue
                    bearing = math.radians(entry['bearing'])
                    enx, eny = math.sin(bearing), math.cos(bearing)
                    ex, ey = entry['center']
                    floor = z + (
                        entry['shelter']['floorHeight']
                        if 'shelter' in entry
                        else entry['attachedPortico']['platformHeight']
                        if 'attachedPortico' in entry
                        else entry.get('landingHeight', 0)
                    )
                    door_top = (
                        entry['shelter']['doorHeight']
                        + entry['shelter']['transomHeight']
                        + 0.12
                        if 'shelter' in entry
                        else 2.8
                    )
                    doorway_width = entry['width'] + entry.get(
                        'shelter', entry.get('doorFrame', {})
                    ).get('pierWidth', 0)
                    if (
                        nx * enx + ny * eny > 0.999
                        and abs((x - ex) * enx + (y - ey) * eny) < 0.3
                        and abs((x - ex) * eny - (y - ey) * enx)
                        < (doorway_width + ww + 0.3) / 2
                        and zz - wh / 2 < floor + door_top
                        and zz + wh / 2 > floor
                    ):
                        blocked_by_door = True
                        break
                for door in form.get('stairAccessDoors', []):
                    door_angle = math.radians(door['bearing'])
                    dnx, dny = math.sin(door_angle), math.cos(door_angle)
                    ex, ey = door['center']
                    if (
                        nx * dnx + ny * dny > 0.999
                        and abs((x - ex) * dnx + (y - ey) * dny) < 0.3
                        and abs((x - ex) * dny - (y - ey) * dnx)
                        < (door['width'] + ww + 0.3) / 2
                        and zz - wh / 2 < z + door['floor'] + door['height']
                        and zz + wh / 2 > z + door['floor']
                    ):
                        blocked_by_door = True
                if blocked_by_door:
                    continue
                if detail:
                    windows.box(x, y, zz, ww + 0.30, 0.22, wh + 0.30, C['white'], theta)
                    windows.box(
                        x + nx * 0.13,
                        y + ny * 0.13,
                        zz,
                        ww,
                        0.10,
                        wh,
                        C['shadeGlass']
                        if b['id'] not in FRONTS and (seed + i * 7 + level * 13) % 7 < 2
                        else pane_glass,
                        theta,
                    )
                    windows.box(
                        x + nx * 0.2,
                        y + ny * 0.2,
                        zz,
                        0.055,
                        0.10,
                        wh,
                        C['white'],
                        theta,
                    )
                    if not recessed and rule.get('balconies', balconies) and i % 2 == 0:
                        windows.box(
                            x + nx * 0.65,
                            y + ny * 0.65,
                            zz - wh * 0.52,
                            ww + 0.5,
                            1.3,
                            0.14,
                            C['white'],
                            theta,
                        )
                        windows.box(
                            x + nx * 1.15,
                            y + ny * 1.15,
                            zz - wh * 0.25,
                            ww + 0.5,
                            0.1,
                            0.65,
                            wall,
                            theta,
                        )
                else:
                    ux, uy = dx / length * ww / 2, dy / length * ww / 2
                    windows.face(
                        [
                            (x - ux, y - uy, zz - wh / 2),
                            (x + ux, y + uy, zz - wh / 2),
                            (x + ux, y + uy, zz + wh / 2),
                            (x - ux, y - uy, zz + wh / 2),
                        ],
                        pane_glass,
                    )
    m.add_part('未核立面沿用原窗格' if college else '04_立面窗格', windows)
    if b['id'] == CIVIL and detail:
        m.add_part('土木东南檐面题字与分缝', civil_finish)
    if b['id'] == PHYSICS:
        m.add_part('沿街深色窗墙与东门台阶', physics_fronts(b, z, C, detail))
        if detail:
            court_joints(m, z, C)
        fit_upper_storeys(m, z, physics_roof)
        from physics_corner_access import finish_corner

        finish_corner(m, z, C, detail)
        from physics_aerial_stairs import east_stair_assembly

        m.add_part('物理东侧宽梯、折梯与院内平台', east_stair_assembly(z, C, detail))
    if b['id'] == MATERIALS:
        m.add_part('东门北塔显示屏与门额', materials_screen(b, z, C, detail))
        m.add_part('西北侧深窗墙', materials_rear(b, z, C, detail))
    if b['id'] == BEI:
        # The guide identifies the second storey. Position within the hall is approximate.
        door = beiyuan_entry(C, detail)
        interior = Mesh()
        place(
            door,
            interior,
            b['center'][0],
            b['center'][1] - 12,
            z + 3.3,
            math.radians(-7.56),
        )
        m.add_part('06_二楼餐厅内门', interior)
    if b['id'] in colleges.BUILDERS:
        m.add_part('05_学院外观', colleges.BUILDERS[b['id']](b, z, C, detail))
    return m
