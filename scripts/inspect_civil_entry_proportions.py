"""Compare central glazing proportions, without claiming calibrated photogrammetry."""
import argparse
import json
import math
from pathlib import Path
from preview_civil_platform_entry import proposal


def inspect():
    # Manual outer-window picks in the 855 x 570 original, clockwise from TL.
    # No image rectification, camera fit, lens calibration or metric scale.
    points = [(284,241), (460,241), (460,357), (284,357)]
    width = (math.dist(points[0],points[1])+math.dist(points[3],points[2]))/2
    height = (math.dist(points[0],points[3])+math.dist(points[1],points[2]))/2
    ratio = width/height
    # +/-3 pixels per endpoint: a sensitivity range, not a confidence interval.
    interval = [(width-6)/(height+6), (width+6)/(height-6)]
    variants = {}
    for name,tall in [('preceding',False),('proportional',True)]:
        b = proposal(tall_surround=tall,curved_roof=False)['candidate']
        facade = next(f for f in b['form']['facades'] if f.get('region')=='under-portico')
        panel = next(p for p in facade['rule']['panels'] if p['id']=='central-upper-glass')
        w = (panel['to']-panel['from'])*math.dist(facade['start'],facade['end'])
        h = panel['top']-panel['bottom']
        variants[name] = dict(widthM=w,heightM=h,ratio=w/h,
            relativeDifferenceFromImage=(w/h)/ratio-1,
            insidePixelSensitivityRange=interval[0] <= w/h <= interval[1])
    return dict(status='uncalibrated-proportion-screen',
        sourceURL='https://tmjz.gxu.edu.cn/info/1452/6575.htm',
        imageURL='https://tmjz.gxu.edu.cn/__local/B/11/E5/A12DDA85D1E7598DA582B485BE1_12A98A97_61751.png',
        imageSize=[855,570],manualWindowCorners=points,
        imageWidthPixels=width,imageHeightPixels=height,imageRatio=ratio,
        endpointSensitivityPixels=3,ratioSensitivityRange=interval,variants=variants,
        assumptions=['Compare apparent image ratio with model ratio under an approximate frontal-wall assumption.',
                     'Pixel sensitivity excludes unknown camera pose, lens distortion and hidden boundaries.',
                     'Keeping estimated width and increasing height is one alternative; the photo does not uniquely determine metre dimensions.'],
        photoRegistrationAccepted=False,productionReady=False,wholeBuildingAccepted=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=inspect()
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['variants'],indent=2))
