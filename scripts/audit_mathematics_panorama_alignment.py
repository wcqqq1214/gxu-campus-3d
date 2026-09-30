"""Audit manual roof correspondences; never change production building data.

Run with the repository refinement Python environment (NumPy required).
The source images remain local research references; numeric observations below
allow the diagnostic to run without downloading or redistributing photographs.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = np.array([-240.0, -870.0, 0.0])
FOCAL = 800 / math.tan(math.radians(17))
OBSERVED = np.array([
    [920, 356], [942, 333], [754, 320], [780, 300], [754, 349],
    [504, 299], [530, 275], [440, 253], [499, 269], [469, 236], [530, 254],
], dtype=float)
NAMES = [
    'west-NW', 'west-SW', 'split-high-N', 'split-high-S', 'split-low-N',
    'middle-NE', 'middle-SE', 'east-NE', 'east-NW', 'east-SE', 'east-SW',
]
# Camera relative to ORIGIN, yaw/pitch/roll, split relative X, east roof datum.
LOW = np.array([-400, 60, 40, 2.1, -1.1, -.2, -30, 10.0])
HIGH = np.array([400, 800, 400, 4.3, -.05, .2, 10, 22.0])
CENTER_POINTS = np.array([
    [-284.841, -837.171, 9.92], [-197.12, -837.271, 6.62],
]) - ORIGIN
CENTER_OBSERVED = np.array([[845, 491], [328, 399]], dtype=float)
BASELINE = 'd53cc0b913dee1c6e94c4a3b1290e92d431e1115'


def roof_points(parameters):
    split = parameters[6] - 240
    north = -868.05 - (split + 272.93) * .00118
    south = -877.79 - (split + 196.86) * .00122
    east = parameters[7]
    return np.array([
        [-283.107, -867.405, 18.88], [-283.128, -878.103, 18.88],
        [split, north, 18.88], [split, south, 18.88], [split, north, 15.58],
        [-206.886, -868.129, 15.58], [-206.895, -877.779, 15.58],
        [-196.853, -870.411, east], [-206.886, -870.4, east],
        [-196.863, -877.792, east], [-206.895, -877.779, east],
    ]) - ORIGIN


def project(parameters, xyz):
    yaw, pitch, roll = parameters[3:6]
    forward = np.array([math.sin(yaw) * math.cos(pitch),
                        math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
    right = np.array([math.cos(yaw), -math.sin(yaw), 0])
    up = np.cross(right, forward)
    r = right * math.cos(roll) + up * math.sin(roll)
    u = up * math.cos(roll) - right * math.sin(roll)
    delta = xyz - parameters[:3]
    depth = delta @ forward
    if np.any(depth <= 0):
        return np.full((len(xyz), 2), 1e6)
    return np.column_stack([800 + FOCAL * (delta @ r) / depth,
                            400 - FOCAL * (delta @ u) / depth])


def fit(observed=OBSERVED, *, fixed_split=None, fixed_east=None):
    indices = list(range(8))
    if fixed_split is not None:
        indices.remove(6)
    if fixed_east is not None:
        indices.remove(7)
    attempts = []
    for distance in [250, 450, 650]:
        initial = np.array([distance * .5, distance, distance * .55,
                            3.6, -.44, 0, -10, 18.88])
        if fixed_split is not None:
            initial[6] = fixed_split
        if fixed_east is not None:
            initial[7] = fixed_east

        def decode(value):
            parameters = initial.copy()
            parameters[indices] = LOW[indices] + value * (HIGH - LOW)[indices]
            return parameters

        def residual(value):
            parameters = decode(value)
            return (project(parameters, roof_points(parameters)) - observed).ravel()

        q = np.clip((initial[indices] - LOW[indices]) / (HIGH - LOW)[indices], 0, 1)
        damping = .001
        for iteration in range(250):
            rv = residual(q)
            jacobian = np.column_stack([
                (residual(q + step) - residual(q - step)) / 2e-5
                for step in np.eye(len(indices)) * 1e-5
            ])
            hessian = np.einsum('ij,ik->jk', jacobian, jacobian)
            gradient = np.einsum('ij,i->j', jacobian, rv)
            step = np.linalg.solve(
                hessian + damping * np.diag(np.maximum(np.diag(hessian), 1)),
                -gradient,
            )
            trial = np.clip(q + step, 0, 1)
            if np.linalg.norm(residual(trial)) < np.linalg.norm(rv):
                q = trial
                damping = max(damping / 3, 1e-9)
                if np.linalg.norm(step) < 1e-9:
                    break
            else:
                damping = min(damping * 5, 1e10)
        parameters = decode(q)
        predicted = project(parameters, roof_points(parameters))
        errors = np.linalg.norm(predicted - observed, axis=1)
        assert np.isfinite(parameters).all() and np.isfinite(errors).all()
        attempts.append(dict(
            parameters=parameters.tolist(), splitX=float(parameters[6] - 240),
            eastRelativeHeight=float(parameters[7] - 2.38),
            rmsePixels=float(np.sqrt(np.mean(errors ** 2))),
            errorsPixels=errors.tolist(), predicted=predicted.tolist(),
            activeBounds=[indices[i] for i, v in enumerate(q) if v < 1e-5 or v > 1-1e-5],
            startDistance=distance, iterations=iteration + 1,
        ))
    best = min(attempts, key=lambda result: result['rmsePixels']).copy()
    best['starts'] = [{k: a[k] for k in ['startDistance', 'rmsePixels', 'iterations']}
                      for a in attempts]
    predicted = project(np.array(best['parameters']), CENTER_POINTS)
    errors = np.linalg.norm(predicted - CENTER_OBSERVED, axis=1)
    best['independentCenter'] = dict(predicted=predicted.tolist(),
                                    errorsPixels=errors.tolist(),
                                    rmsePixels=float(np.sqrt(np.mean(errors ** 2))))
    return best


def report():
    cases = dict(current=fit(fixed_split=-25, fixed_east=15.58),
                 free=fit(), equalEndHeights=fit(fixed_east=18.88))
    sensitivity = []
    for axis in [0, 1]:
        for shift in [-3, 3]:
            observations = OBSERVED.copy()
            observations[7:, axis] += shift
            result = fit(observations)
            sensitivity.append(dict(axis=axis, eastCornerShiftPixels=shift,
                                    splitX=result['splitX'],
                                    eastRelativeHeight=result['eastRelativeHeight'],
                                    fitRmsePixels=result['rmsePixels'],
                                    independentCenter=result['independentCenter']))
    # A numerical check with generated observations is not real-world validation.
    truth = np.array([-180, 340, 185, 2.7, -.46, -.04, -10, 18.88])
    synthetic = fit(project(truth, roof_points(truth)))
    assert synthetic['rmsePixels'] < 1e-5, 'Solver failed synthetic recovery'
    independent_height_sensitivity = []
    for dz in [-3.3, 0, 3.3]:
        points = CENTER_POINTS.copy()
        points[:, 2] += dz
        predicted = project(np.array(cases['equalEndHeights']['parameters']), points)
        error = predicted - CENTER_OBSERVED
        independent_height_sensitivity.append(dict(
            centerEaveHeightShiftM=dz, predicted=predicted.tolist(),
            errorsPixels=np.linalg.norm(error, axis=1).tolist(),
            horizontalErrorsPixels=np.abs(error[:, 0]).tolist(),
        ))
    evidence = ROOT / 'docs/model-checks/refinement/s2-mathematics-panorama-evidence.json'
    source = json.loads(evidence.read_text())
    image = next(item for item in source['derivedViews']
                 if item['path'].endswith('math-common-perspective.png'))
    groups = {}
    inventory = []
    entries = subprocess.check_output(['git', 'ls-tree', '-rz', BASELINE], cwd=ROOT)
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        info, path_bytes = entry.split(b'\t', 1)
        path = path_bytes.decode()
        if not path.startswith(('app/', 'components/', 'lib/', 'scripts/',
                                'blender/', 'data/', 'public/')):
            continue
        contents = (ROOT / path).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(contents)).encode() + b'\0' + contents).hexdigest()
        assert blob == info.decode().split()[2], f'Baseline file changed: {path}'
        group = path.split('/')[0]
        groups[group] = groups.get(group, 0) + 1
        inventory.append([path, blob])
    return dict(
        status='candidate-rejected-for-production', buildingId='way/759129516',
        productionReady=False, wholeBuildingAccepted=False,
        source=dict(url=source['source']['viewer'], image=image,
                    evidenceSHA256=hashlib.sha256(evidence.read_bytes()).hexdigest()),
        baselineCommit=BASELINE,
        productionPreservation=dict(countsByRoot=groups,
                                    allExistingBaselineFilesMatchGitBlob=True,
                                    inventorySHA256=hashlib.sha256(json.dumps(inventory, separators=(',', ':')).encode()).hexdigest(),
                                    newAuditScriptExcludedFromBaseline=True),
        auditScriptSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        assumptions=dict(imageSize=[1600, 800], principalPoint=[800, 400],
                         focalPixels=FOCAL, horizontalFovDegrees=34,
                         origin=ORIGIN.tolist(), lowerBounds=LOW.tolist(), upperBounds=HIGH.tolist(),
                         parameterOrder=['cameraX', 'cameraY', 'cameraZ', 'yaw', 'pitch', 'roll',
                                         'splitRelativeX', 'eastAbsoluteRoofDatum'],
                         heights='Current assumed west/central 16.5/13.2 m above 2.38 m model datum; not surveyed.',
                         map='Current OSM outer vertices rounded to millimetres; eaves identified manually.',
                         lens='Common cube reprojection assumed pinhole; stitch/lens errors not calibrated.'),
        fittingObservations=[dict(name=n, pixel=p.tolist()) for n, p in zip(NAMES, OBSERVED)],
        independentObservations=dict(buildingId='way/759129515',
                                     names=['north-west-eave', 'north-east-eave'],
                                     xyz=(CENTER_POINTS + ORIGIN).tolist(),
                                     pixels=CENTER_OBSERVED.tolist(),
                                     note='Not fitted; mapped corners and existing 9.9/6.6 m eaves plus 0.02 m datum are assumptions.'),
        observationRevision=dict(
            discardedSplitPixels=[[720, 321], [757, 295], [720, 342]],
            correctedSplitPixels=OBSERVED[2:5].tolist(),
            discardedCenterPixels=[[870, 479], [318, 402]],
            correctedCenterPixels=CENTER_OBSERVED.tolist(),
            reason='Image overlay exposed a split selected on the low roof and an eave selected on the wall. Re-picked actual visible corners with enlarged pixel grids; first fits are superseded, not retained as accepted evidence.',
        ),
        cases=cases, eastCornerSensitivity=sensitivity,
        independentEaveHeightSensitivity=independent_height_sensitivity,
        syntheticRecovery=dict(rmsePixels=synthetic['rmsePixels'],
                               maxParameterError=float(np.max(np.abs(np.array(synthetic['parameters']) - truth))),
                               realImageValidation=False),
        decision='Do not adopt the fitted numeric split or height. A better target fit still leaves independent neighbouring eaves inconsistent under the declared assumptions; this does not isolate whether map geometry, heights, correspondence or camera/stitch assumptions are wrong. Keep the raised east end as a qualitative candidate; close this correspondence set and move to another building until stronger control points arrive.',
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = report()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({name: {key: case[key] for key in
                            ['splitX', 'eastRelativeHeight', 'rmsePixels', 'independentCenter']}
                      for name, case in result['cases'].items()}, indent=2))
