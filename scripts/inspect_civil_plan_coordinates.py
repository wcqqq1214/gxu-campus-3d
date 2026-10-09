"""Check DL-37's internal metric coordinates; never georeference or edit models.

Requires numpy and PyMuPDF. The PDF is a local, separately obtained research
input. Its locked hash and manually read leader endpoints make point selection
reviewable; unused survey labels test the fitted transform independently.
"""
import argparse
import hashlib
import json
from pathlib import Path

import fitz
import numpy as np

PDF_SHA256 = '5df1451daa47fd16d01cac778e39375256f5f054525c530ac9ee72786df10213'
# name, CAD X (north), CAD Y (east), PDF vector drawing seqno, endpoint (pt).
# These are coordinate leader endpoints, NOT text positions or building corners.
POINTS = [
    ('C1', 2526925.050, 529019.383, 36956, [675.56, 361.90]),
    ('C2', 2526925.050, 529072.273, 36770, [872.12, 361.90]),
    ('C3', 2526946.589, 528910.852, 36708, [272.24, 281.86]),
    ('C4', 2526941.100, 528969.723, 38011, [491.00, 302.26]),
    ('C5', 2526937.100, 528973.723, 38042, [505.88, 317.08]),
    ('H1', 2526937.300, 529011.654, 36739, [646.88, 316.36]),
    ('H2', 2526903.050, 528932.737, 36925, [353.60, 443.62]),
    ('H3', 2526900.223, 528935.732, 38269, [364.70, 454.18]),
    ('H4', 2526887.500, 528936.468, 38207, [367.46, 501.46]),
    ('H5', 2526887.500, 528949.273, 38238, [415.04, 501.46]),
    ('H6', 2526884.500, 528952.273, 36894, [426.20, 512.56]),
    ('H7', 2526868.050, 528952.273, 36863, [426.20, 573.70]),
    ('H8', 2526869.106, 529072.273, 36801, [872.12, 569.80]),
]


def fit_similarity(world, observed):
    """Uniform scale + rotation + translation; no affine shear or stretching."""
    origin = world.mean(axis=0)
    q = world - origin
    design = np.zeros((len(q) * 2, 4))
    design[::2] = np.column_stack([q[:, 0], -q[:, 1], np.ones(len(q)), np.zeros(len(q))])
    design[1::2] = np.column_stack([q[:, 1], q[:, 0], np.zeros(len(q)), np.ones(len(q))])
    coefficients, _, rank, _ = np.linalg.lstsq(design, observed.ravel(), rcond=None)
    if rank != 4:
        raise ValueError('Degenerate coordinate controls')
    a, b, tx, ty = coefficients
    matrix = np.array([[a, -b], [b, a]])
    return origin, matrix, np.array([tx, ty])


def inspect(pdf):
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != PDF_SHA256:
        raise ValueError('PDF differs from the reviewed source; re-identify leaders before use')
    with fitz.open(pdf) as document:
        page = document[38]
        paths = {d['seqno']: d for d in page.get_drawings()}
        rows = []
        for name, north, east, seqno, picked in POINTS:
            items = paths[seqno]['items']
            if len(items) != 1 or items[0][0] != 'l':
                raise ValueError(f'{name}: expected one reviewed leader line')
            endpoint = np.array(items[0][1], dtype=float)
            if np.linalg.norm(endpoint - picked) > .001:
                raise ValueError(f'{name}: selected leader endpoint changed')
            rows.append(dict(id=name,role='control' if name.startswith('C') else 'holdout',
                             cadNorth=north,cadEast=east,pdfPoint=endpoint.tolist(),
                             drawingSeqno=seqno,leaderOtherEnd=list(items[0][2])))
        page_size = list(page.rect)
        # This reviewed outline is visible in the southwest of DL-37. It is
        # not identified as an as-built wall, apron, or roof projection.
        outline_items = paths[146]['items']
        if not outline_items or any(item[0] != 'l' for item in outline_items):
            raise ValueError('Candidate outline is no longer the reviewed polyline')
        for previous, following in zip(outline_items, outline_items[1:]):
            if not np.allclose(previous[2], following[1], atol=.001, rtol=0):
                raise ValueError('Candidate outline contains disconnected segments')
        outline_pdf = np.array([list(outline_items[0][1])] + [list(item[2]) for item in outline_items])
        if not np.allclose(outline_pdf[0], outline_pdf[-1], atol=.001, rtol=0):
            raise ValueError('Candidate outline is not closed')
    # Paper coordinates have y down; north must have the opposite sign.
    world = np.array([[r['cadEast'], -r['cadNorth']] for r in rows])
    observed = np.array([r['pdfPoint'] for r in rows])
    origin, matrix, offset = fit_similarity(world[:5], observed[:5])
    predicted = (world - origin) @ matrix.T + offset
    scale = float(np.linalg.norm(matrix[0]))
    for r, q, point in zip(rows, predicted, observed):
        r.update(predictedPDF=q.tolist(),residualPoints=float(np.linalg.norm(q-point)),
                 residualDrawingMeters=float(np.linalg.norm(q-point)/scale))
    tolerance = .05
    accepted = all(r['residualDrawingMeters'] <= tolerance for r in rows[5:])
    # Refit swapped axes too: this tests reflection, not merely a wrong origin.
    swapped = np.array([[-r['cadNorth'], r['cadEast']] for r in rows])
    wrong_origin, wrong_matrix, wrong_offset = fit_similarity(swapped[:5], observed[:5])
    wrong = (swapped - wrong_origin) @ wrong_matrix.T + wrong_offset
    negative = float(np.linalg.norm(wrong[5:] - observed[5:],axis=1).min()/scale)
    if negative <= tolerance:
        raise AssertionError('Axis-swap negative check unexpectedly passed')
    outline_world = (outline_pdf - offset) @ np.linalg.inv(matrix).T + origin
    outline_cad = [[float(-north), float(east)] for east, north in outline_world]
    return dict(candidateOutline=dict(drawingSeqno=146, pdfPoints=outline_pdf.tolist(),
                                      cadNorthEast=outline_cad,
                                      axisExtentMeters=np.ptp(outline_world,axis=0).tolist(),
                                      extentAxisOrder=['east', 'north'],
                                      classification='Unresolved southwest rectangular outline with southern offsets',
                                      buildingId=None, productionReady=False),
                sourceURL='https://www.gxu.edu.cn/info/1364/36271.htm',
                attachmentURL='https://www.gxu.edu.cn/system/_content/download.jsp?owner=1556120285&urltype=news.DownloadAttachUrl&wbfileid=14901393',
                pdfSHA256=digest,pageOneBased=39,sheet='DL-37',pageRectPoints=page_size,
                pymupdfVersion=fitz.VersionBind,controlCount=5,holdoutCount=8,
                inputAxes=['CAD Y east','negative CAD X north'],
                worldOrigin=origin.tolist(),matrix=matrix.tolist(),offsetPDF=offset.tolist(),
                pointsPerDrawingMeter=scale,rotationDegrees=float(np.degrees(np.arctan2(matrix[1,0],matrix[0,0]))),
                holdoutToleranceDrawingMeters=tolerance,internalDrawingMappingAccepted=accepted,
                maximumHoldoutDrawingMeters=max(r['residualDrawingMeters'] for r in rows[5:]),
                axisSwapRefitMinimumHoldoutDrawingMeters=negative,points=rows,
                sourceCRSIdentified=False,campusRegistrationAccepted=False,
                excavationBoundaryIsBuildingFootprint=False,productionModified=False,
                limitations=['Residuals check internal PDF coordinate consistency, not ground survey accuracy.',
                             'Coordinate datum, projection and survey date not established from the reviewed sheet.',
                             'Leader anchors describe excavation geometry; do not extrude them as building footprints.',
                             'Existing building outlines, roof projections, level labels and construction lines must be distinguished.'])


def diagram(report):
    rows = report['points']
    outline = report['candidateOutline']['cadNorthEast']
    east0 = min([r['cadEast'] for r in rows] + [p[1] for p in outline])
    north0 = min([r['cadNorth'] for r in rows] + [p[0] for p in outline])

    def xy(east, north):
        return 65 + (east - east0) * 3.5, 460 - (north - north0) * 3.5

    out=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="560" viewBox="0 0 900 560">',
         '<rect width="900" height="560" fill="#f8fafc"/>',
         '<g font-family="system-ui, sans-serif" fill="#172033">',
         '<text x="32" y="38" font-size="22">DL-37: internal drawing coordinate check</text>',
         '<text x="32" y="66" font-size="14">5 controls + 8 held-out coordinate leaders; no campus georeferencing</text>',
         '<path d="M 45 450 V 120 l -5 12 m 5 -12 l 5 12" stroke="#60758a" fill="none"/>',
         '<text x="32" y="109" font-size="12">N</text>']
    outline_points = ' '.join(f'{x:.2f},{y:.2f}' for x, y in (xy(e, n) for n, e in outline))
    out += [f'<polyline points="{outline_points}" stroke="#64748b" stroke-dasharray="5 4" fill="none"/>',
            '<text x="330" y="439" font-size="13">Dashed: unassigned outline; outside control coverage</text>']
    for r in rows:
        x,y=xy(r['cadEast'], r['cadNorth']);color='#176b9b' if r['role']=='control' else '#c46520'
        out += [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}"/>',
                f'<text x="{x+8:.2f}" y="{y-5:.2f}" font-size="12">{r["id"]}</text>']
    out += ['<text x="32" y="505" font-size="14">Blue: fitted controls    Orange: independent holdouts</text>',
            f'<text x="32" y="532" font-size="14">Max held-out residual: {report["maximumHoldoutDrawingMeters"]:.4f} drawing m; not site accuracy.</text>',
            '</g></svg>']
    return '\n'.join(out)+'\n'


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--diagram',type=Path)
    args=p.parse_args();result=inspect(args.pdf)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    if args.diagram:
        args.diagram.parent.mkdir(parents=True,exist_ok=True);args.diagram.write_text(diagram(result))
    print(json.dumps({k:result[k] for k in ['internalDrawingMappingAccepted','maximumHoldoutDrawingMeters','pointsPerDrawingMeter','campusRegistrationAccepted']}))
    if not result['internalDrawingMappingAccepted']:raise SystemExit(1)
