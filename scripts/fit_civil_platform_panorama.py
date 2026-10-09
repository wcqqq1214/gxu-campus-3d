"""Read-only panorama correspondence hypothesis; never alters model parameters.

Fit the physics building first, then predict the separate civil platform.
The cube-face camera and existing roof heights are assumptions, not a survey.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PHYSICS = 'way/957404989'
PLATFORM = 'way/957404988'
# Manually picked outer parapet corners, original 4096 x 4096 f cube face.
# These are deliberately not points on the target platform.
CORNER_IDS = [0, 1, 6, 7, 14, 15, 17, 16]
PIXELS = np.array([[3132, 3333], [3018, 3221], [2934, 3155], [2843, 3080],
                   [2781, 3021], [2708, 2975], [3590, 3259], [3047, 2939]], float)
# Three visible corners of the target roof, held out of camera fitting.
# The southeast corner is obscured by the raised rooftop volume.
TARGET_PIXELS = np.array([[2330, 2850], [2348, 2891], [2525, 2838]], float)
LOW = np.array([-1400, -1800, 20, -.5, -.3, -.1])
HIGH = np.array([-700, -950, 250, .5, .3, .1])


def project(parameters, world):
    x, y, z, yaw, pitch, roll = parameters
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    forward = np.array([sy * cp, cy * cp, sp])
    right = np.array([cy, -sy, 0])
    up = np.cross(right, forward)
    right, up = right * cr + up * sr, up * cr - right * sr
    delta = np.asarray(world) - [x, y, z]
    depth = delta @ forward
    if np.any(depth <= .1):
        raise ValueError('Control point behind trial camera')
    return np.column_stack([2048 + 2048 * (delta @ right) / depth,
                            2048 - 2048 * (delta @ up) / depth])


def solve(world, observed):
    span = HIGH - LOW

    def residual(q):
        try:
            return (project(LOW + q * span, world) - observed).ravel()
        except ValueError:
            return np.full(observed.size, 1e6)

    results = []
    for height in (50, 100, 150):
        q = (np.array([-820, -1200, height, 0, 0, 0]) - LOW) / span
        damping = .001
        for iteration in range(250):
            r = residual(q)
            eye = np.eye(6) * 1e-5
            jac = np.column_stack([(residual(q + s) - residual(q - s)) / 2e-5 for s in eye])
            hessian = jac.T @ jac
            step = np.linalg.solve(hessian + damping * np.diag(np.maximum(hessian.diagonal(), 1)), -jac.T @ r)
            trial = np.clip(q + step, 0, 1)
            if np.linalg.norm(residual(trial)) < np.linalg.norm(r):
                q = trial
                damping = max(damping / 3, 1e-9)
                if np.linalg.norm(step) < 1e-9:
                    break
            else:
                damping = min(damping * 5, 1e12)
        results.append(dict(startHeight=height, iterations=iteration + 1,
                            parameters=(LOW + q * span).tolist(),
                            rmsPixels=float(np.linalg.norm(residual(q)) / len(observed) ** .5),
                            activeBounds=np.flatnonzero((q < 1e-5) | (q > 1 - 1e-5)).tolist()))
    return min(results, key=lambda r: r['rmsPixels']), results


def report(buildings_path):
    buildings = {b['id']: b for b in json.loads(buildings_path.read_text())}
    physics, platform = buildings[PHYSICS], buildings[PLATFORM]
    ring = physics['polygons'][0][0]
    world = np.array([[*ring[i], physics['elevation'] + physics['height']] for i in CORNER_IDS])
    fit, starts = solve(world, PIXELS)
    parameters = fit['parameters']
    office = next(p for p in platform['form']['parts'] if p['id'] == 'north-office')
    target = np.array([[*office['polygons'][0][0][i], platform['elevation'] + office['height']]
                       for i in (3, 4, 2)])  # northwest, southwest, northeast
    prediction = project(parameters, target)
    sensitivity = []
    for omit in range(len(world)):
        mask = np.arange(len(world)) != omit
        trial, _ = solve(world[mask], PIXELS[mask])
        sensitivity.append(dict(kind='leave-one-control-out', omittedCorner=CORNER_IDS[omit],
                                rmsPixels=trial['rmsPixels'], activeBounds=trial['activeBounds'],
                                targetPixels=project(trial['parameters'], target).tolist()))
    for dz in (-3, 3):
        trial, _ = solve(world + [0, 0, dz], PIXELS)
        sensitivity.append(dict(kind='physics-roof-height-assumption', deltaMeters=dz,
                                rmsPixels=trial['rmsPixels'], activeBounds=trial['activeBounds'],
                                targetPixels=project(trial['parameters'], target).tolist()))
    projections = []
    for part in platform['form']['parts']:
        points = [[x, y, platform['elevation'] + part['height']] for x, y in part['polygons'][0][0]]
        projections.append(dict(part=part['id'], roofPixels=project(parameters, points).tolist()))
    projections.append(dict(part='physics-dome-apex', roofPixels=project(parameters, [[
        *physics['form']['roofDome']['center'], physics['elevation'] + physics['height'] +
        physics['form']['roofDome']['drumHeight'] + physics['form']['roofDome']['rise']]]).tolist()))
    extent = np.array([s['targetPixels'] for s in sensitivity])
    return dict(
        purpose='Qualitative object/face correspondence only; no automatic model approval or dimension recovery.',
        sourceUrl='https://www.gx720.net/pano/viewer/?slug=pano-659',
        sourceFace='4/f, 512px tiles assembled at their original row/column offsets into 4096px square',
        assumptions=['90-degree rectilinear cube face, focal length 2048px and centered principal point',
                     'Existing physics footprint and one estimated roof elevation for all eight parapet corners',
                     'Parapet picks, panorama stitching, roof offsets and model heights are uncertain',
                     'No source capture date established; directory 2021/8 is not a capture date'],
        buildingFile=str(buildings_path.relative_to(ROOT)) if buildings_path.is_relative_to(ROOT) else str(buildings_path),
        buildingFileSHA256=hashlib.sha256(buildings_path.read_bytes()).hexdigest(),
        physicsId=PHYSICS, targetId=PLATFORM,
        controls=[dict(corner=i, world=w.tolist(), observed=o.tolist(), predicted=p.tolist(), errorPixels=float(np.linalg.norm(p-o)))
                  for i, w, o, p in zip(CORNER_IDS, world, PIXELS, project(parameters, world))],
        camera=fit, starts=starts, cameraParameterOrder=['east', 'north', 'up', 'yaw', 'pitch', 'roll'],
        targetHoldout=[dict(corner=n, world=w.tolist(), observed=o.tolist(), predicted=p.tolist(), errorPixels=float(np.linalg.norm(p-o)))
                       for n, w, o, p in zip(['northwest', 'southwest', 'northeast'], target, TARGET_PIXELS, prediction)],
        targetRmsPixels=float(np.sqrt(np.mean(np.sum((prediction-TARGET_PIXELS)**2, axis=1)))),
        domeHoldout=dict(observed=[3001, 3038], predicted=projections[-1]['roofPixels'][0],
                         errorPixels=float(np.linalg.norm(np.array(projections[-1]['roofPixels'][0])-[3001, 3038])),
                         caveat='Existing dome center/rise are estimates; this discrepancy prevents metric registration acceptance.'),
        sensitivity=sensitivity,
        sensitivityTargetPixelRanges=[dict(corner=n, minimum=lo.tolist(), maximum=hi.tolist())
                                      for n, lo, hi in zip(['northwest', 'southwest', 'northeast'], extent.min(axis=0), extent.max(axis=0))],
        projections=projections, photoMetricRegistrationAccepted=False,
        productionModified=False, wholeBuildingAccepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--buildings', type=Path, default=ROOT/'public/data/buildings.json')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = report(args.buildings.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['targetRmsPixels', 'photoMetricRegistrationAccepted', 'productionModified']}))
