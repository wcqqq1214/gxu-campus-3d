"""Check the provisional roof correspondence against a facade-only camera fit.

This diagnostic never writes building overrides or production models. Pixel
observations and model heights are assumptions, not surveyed control points.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOW = np.array([500, -400, -500, 10, -.1, -.6, -.08])
HIGH = np.array([6000, -20, -30, 200, 1.2, .1, .08])
ORIGIN = np.array([300, -326, 0])
PIXELS = np.array([[787, 519], [1305, 438], [788, 567],
                   [1302, 469], [789, 617], [1297, 503], [706, 507]])
CONTROLS = [(12, 16.5), (7, 16.5), (12, 13.2), (7, 13.2),
            (12, 9.9), (7, 9.9), (17, 16.5)]


def project(parameters, points):
    focal, x, y, z, yaw, pitch, roll = parameters
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    forward = np.array([sy * cp, cy * cp, sp])
    right = np.array([cy, -sy, 0])
    up = np.cross(right, forward)
    right, up = right * cr + up * sr, up * cr - right * sr
    delta = np.asarray(points) - [x, y, z]
    depth = delta @ forward
    if np.min(depth) < .1:
        return np.full((len(points), 2), 1e6)
    return np.column_stack((960 + focal * (delta @ right) / depth,
                            540 - focal * (delta @ up) / depth))


def fit(points, observed):
    """Bounded damped least squares with four declared initial distances."""
    attempts = []
    for distance in [80, 150, 250, 500]:
        initial = np.array([distance * 10, -distance * .7, -distance,
                            45, .4, -.12, 0])
        q = np.clip((initial - LOW) / (HIGH - LOW), 0, 1)
        damping = .001

        def residual(value):
            return (project(LOW + value * (HIGH - LOW), points) - observed).ravel()

        for _ in range(200):
            rv = residual(q)
            jacobian = np.column_stack([
                (residual(q + step) - residual(q - step)) / 2e-5
                for step in np.eye(7) * 1e-5
            ])
            hessian = jacobian.T @ jacobian
            step = np.linalg.solve(
                hessian + damping * np.diag(np.maximum(np.diag(hessian), 1)),
                -jacobian.T @ rv,
            )
            trial = np.clip(q + step, 0, 1)
            if np.linalg.norm(residual(trial)) < np.linalg.norm(rv):
                q = trial
                damping = max(damping / 3, 1e-9)
                if np.linalg.norm(step) < 1e-8:
                    break
            else:
                damping = min(damping * 5, 1e10)
        attempts.append((float(np.linalg.norm(residual(q))), LOW + q * (HIGH - LOW)))
    return min(attempts, key=lambda row: row[0])[1]


def summarize(parameters, xyz, observations, fit_count):
    predicted = project(parameters, xyz)
    errors = np.linalg.norm(predicted - observations, axis=1)
    return dict(parameters=parameters.tolist(), predicted=predicted.tolist(),
                errorsPixels=errors.tolist(), fittingPointCount=fit_count,
                fittingRmsePixels=float(np.sqrt(np.mean(errors[:fit_count] ** 2))),
                heldOutRoofErrorPixels=float(errors[6]) if fit_count == 6 else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / 'docs/model-checks/refinement/s3-agriculture-west-roof-proposal.json'
    proposal = json.loads(source.read_text())
    ring = proposal['original']['polygons'][0][0]
    xyz = np.array([[*ring[i], z] for i, z in CONTROLS]) - ORIGIN
    all_fit = summarize(fit(xyz, PIXELS), xyz, PIXELS, 7)
    facade_fit = summarize(fit(xyz[:6], PIXELS[:6]), xyz, PIXELS, 6)
    sensitivity = []
    # Coordinated endpoint offsets test sensitivity to digitization; these are
    # deterministic probes, not an uncertainty distribution or confidence band.
    for axis in [0, 1]:
        for shift in [-3, 3]:
            observations = PIXELS.copy()
            observations[[1, 3, 5], axis] += shift
            result = summarize(fit(xyz[:6], observations[:6]), xyz, observations, 6)
            sensitivity.append(dict(eastEndpointAxis=axis, shiftPixels=shift,
                                    fittingRmsePixels=result['fittingRmsePixels'],
                                    heldOutRoofErrorPixels=result['heldOutRoofErrorPixels']))
    report = dict(
        buildingId=proposal['buildingId'], productionReady=False,
        method='Seven-point fit compared with six facade points and one held-out roof corner',
        reference=dict(path='work/refinement-s3-agriculture-roof/anniversary-255s.png',
                       sha256=proposal['referenceImages']['work/refinement-s3-agriculture-roof/anniversary-255s.png'],
                       url=proposal['source']['url'], frameSeconds=255, captureDate=None),
        proposalSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        assumptions=dict(pixelPrincipalPoint=[960, 540], squarePixels=True,
                         lensDistortion='not modelled', modelOrigin=ORIGIN.tolist(),
                         parameterOrder=['focalPixels', 'cameraX', 'cameraY', 'cameraZ', 'yaw', 'pitch', 'roll'],
                         lowerBounds=LOW.tolist(), upperBounds=HIGH.tolist(),
                         maximumIterationsPerStart=200, initialDistances=[80, 150, 250, 500],
                         pointSelection='Prior manually selected wall corners and level lines; roof correspondence unverified',
                         heights='Existing estimated 3.3 m storey spacing, not surveyed heights'),
        observations=[dict(index=k, originalVertex=i, modelHeight=z, pixels=PIXELS[k].tolist(),
                           role='held-out roof corner' if k == 6 else 'facade control')
                      for k, (i, z) in enumerate(CONTROLS)],
        allPointsFit=all_fit, facadeOnlyFit=facade_fit,
        deterministicPixelSensitivity=sensitivity,
        decision='Do not infer terrace depth or roof heights from this registration. The held-out roof corner disagrees despite a better facade fit.',
        limitation='This does not identify whether the incorrect assumption is the image correspondence, roof geometry, mapped footprint, or camera model.',
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(allPointRmse=all_fit['fittingRmsePixels'],
                          facadeRmse=facade_fit['fittingRmsePixels'],
                          heldOutRoofError=facade_fit['heldOutRoofErrorPixels'],
                          sensitivity=sensitivity)))


if __name__ == '__main__':
    main()
