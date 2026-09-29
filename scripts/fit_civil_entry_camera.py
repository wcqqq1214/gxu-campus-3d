"""Bounded single-image hypothesis fitting; not a survey or production approval."""
import argparse
import json
import math
from pathlib import Path
import numpy as np

# TL, TR, BR, BL glazing corners; front L/R and rear L/R column/soffit contacts.
NAMES=['glass-tl','glass-tr','glass-br','glass-bl','front-left','front-right','rear-left','rear-right']
OBS=np.array([[284,239],[459,240],[461,357],[280,357],[150,96],[580,97],[269,166],[473,166]],float)
ROOF_X=np.array([80,427,760],float)
ROOF_Y=np.array([47,64,44],float)
# f(px), outward distance, camera x, height, yaw/pitch/roll(rad), front/rear
# half-spans, rear setback, front clearance, principal y. Principal x is fixed.
LOW=np.array([250,3,-5,1.3,-.4,-.1,-.1,3,2.2,2,.4,100],float)
HIGH=np.array([1800,50,5,2.5,.4,.55,.1,6,3.5,5.3,1.5,700],float)
BASE=np.array([534,8.7,1.5,1.65,0,.05,0,5.2,2.8,4.7,.6,451],float)
ROUNDED=[4.0,2.35,3.8,1.0]
ROOF=np.array([[x,.8*max(0,1-(x/9)**2),8.25] for x in np.linspace(-18,13,250)])


def basis(p):
    yaw,pitch,roll=p[4:7]
    cy,sy,cp,sp,cr,sr=math.cos(yaw),math.sin(yaw),math.cos(pitch),math.sin(pitch),math.cos(roll),math.sin(roll)
    forward=np.array([sy*cp,cy*cp,sp]);right=np.array([cy,-sy,0]);up=np.cross(right,forward)
    return right*cr+up*sr,up*cr-right*sr,forward


def project(p,points):
    right,up,forward=basis(p)
    delta=np.asarray(points)-np.array([p[2],-p[1],p[3]])
    depth=delta@forward
    if np.any(depth<=.1):raise ValueError('Fitted feature lies behind the camera')
    return np.column_stack([427.5+p[0]*(delta@right)/depth,p[11]-p[0]*(delta@up)/depth])


def landmarks(p):
    front_half,rear_half,rear,clearance=p[7:11]
    front=clearance+.8*max(0,1-(front_half/9)**2)
    return np.array([[-2.425,5.85,7.45],[2.425,5.85,7.45],[2.425,5.85,4.25],[-2.425,5.85,4.25],
                     [-front_half,front,8.25],[front_half,front,8.25],[-rear_half,rear,8.25],[rear_half,rear,8.25]])


def roof_prediction(p):
    # Ignore parts of the long canopy behind a trial camera; only the visible
    # monotonic front-edge segment can provide the three image intersections.
    depth=(ROOF-np.array([p[2],-p[1],p[3]]))@basis(p)[2]
    visible=project(p,ROOF[depth>.1]);order=np.argsort(visible[:,0]);visible=visible[order]
    if visible[0,0]>ROOF_X[0] or visible[-1,0]<ROOF_X[-1]:
        raise ValueError('Roof edge does not span the observed image samples')
    return np.interp(ROOF_X,visible[:,0],visible[:,1])


def solve(*,joint=False,geometry=None,height=1.65,observed=OBS,roof_observed=ROOF_Y):
    initial=BASE.copy();initial[3]=height
    if geometry is not None:initial[7:11]=geometry
    ids=np.array([0,1,2,4,5,6]+(list(range(7,12)) if joint else [11]));span=HIGH-LOW
    def decode(q):
        p=initial.copy();p[ids]=LOW[ids]+q*span[ids];return p
    def residual(q):
        p=decode(q)
        try:return np.r_[(project(p,landmarks(p))-observed).ravel(),roof_prediction(p)-roof_observed]
        except ValueError:return np.full(19,1e6)
    best=None;starts=[]
    for distance in (5,9,16,30):
        start=initial.copy();start[1]=distance;start[0]=36*(distance+6)
        q=np.clip((start[ids]-LOW[ids])/span[ids],0,1);damping=.001
        for iteration in range(180):
            r=residual(q);eye=np.eye(len(q))*1e-5
            jac=np.column_stack([(residual(q+step)-residual(q-step))/2e-5 for step in eye])
            hessian=np.einsum('ij,ik->jk',jac,jac);gradient=np.einsum('ij,i->j',jac,r)
            step=np.linalg.solve(hessian+damping*np.diag(np.maximum(np.diag(hessian),1)), -gradient)
            trial=np.clip(q+step,0,1)
            if np.linalg.norm(residual(trial))<np.linalg.norm(r):
                q=trial;damping=max(damping/3,1e-9)
                if np.linalg.norm(step)<1e-8:break
            else:damping=min(damping*5,1e10)
        error=float(np.linalg.norm(residual(q)));starts.append(dict(distance=distance,residualNorm=error,iterations=iteration+1))
        if best is None or error<best[0]:best=(error,decode(q),q.copy())
    _,p,q=best
    prediction=project(p,landmarks(p));roof_y=roof_prediction(p)
    return dict(parameters=p.tolist(),geometry=dict(zip(['frontHalfSpan','rearHalfSpan','rearSetback','frontClearance'],p[7:11].tolist())),
        camera=dict(focalPixels=p[0],outwardDistance=p[1],rightOffset=p[2],height=p[3],yaw=p[4],pitch=p[5],roll=p[6],
                    principalPoint=[427.5,p[11]],imageSize=[855,570]),
        landmarkRmsPixels=float(np.sqrt(np.mean(np.sum((prediction-observed)**2,axis=1)))),
        roofRmsPixels=float(np.sqrt(np.mean((roof_y-roof_observed)**2))),
        predictions=prediction.tolist(),roofPredictions=roof_y.tolist(),
        activeBounds=[int(ids[i]) for i,v in enumerate(q) if v<1e-5 or v>1-1e-5],starts=starts)


def report():
    fixed=solve();joint=solve(joint=True);rounded=solve(geometry=ROUNDED)
    sensitivity=[]
    for height in (1.4,1.9):
        r=solve(joint=True,height=height);sensitivity.append(dict(kind='assumed-height',height=height,geometry=r['geometry'],landmarkRmsPixels=r['landmarkRmsPixels']))
    rng=np.random.default_rng(20260930)
    for i in range(3):
        r=solve(joint=True,observed=OBS+rng.uniform(-2,2,OBS.shape),roof_observed=ROOF_Y+rng.uniform(-2,2,3))
        sensitivity.append(dict(kind='two-pixel-perturbation',sample=i,geometry=r['geometry'],landmarkRmsPixels=r['landmarkRmsPixels']))
    earlier=OBS.copy();earlier[:4]=[[284,241],[460,241],[460,357],[284,357]]
    pick_sensitivity=solve(joint=True,observed=earlier)
    # Independent of the pose fit: mullion intersections in the source image.
    # Six columns and nonuniform rows are a separate facade interpretation.
    xs=np.array([313,342,371,400,429]);ys=np.array([284,313])
    heldout_observed=np.array([[x,y] for y in ys for x in xs])
    points=np.array([[-2.425+.07+i*(4.85-.14)/6,5.85,4.25+.07+fraction*(3.2-.14)]
                     for fraction in (.625,.375) for i in range(1,6)])
    predicted=project(np.array(rounded['parameters']),points)
    return dict(status='bounded-single-image-hypothesis',sourceURL='https://tmjz.gxu.edu.cn/info/1452/6575.htm',
        imageURL='https://tmjz.gxu.edu.cn/__local/B/11/E5/A12DDA85D1E7598DA582B485BE1_12A98A97_61751.png',
        imageSize=[855,570],landmarks=[dict(name=name,pixel=p.tolist()) for name,p in zip(NAMES,OBS)],
        roofSamples=[dict(x=x,y=y) for x,y in zip(ROOF_X.tolist(),ROOF_Y.tolist())],
        cameraHeightAssumedM=1.65,principalXFixed=427.5,parameterBounds=dict(lower=LOW.tolist(),upper=HIGH.tolist()),
        fixedGeometry=fixed,jointFit=joint,roundedCandidate=rounded,sensitivity=sensitivity,
        earlierRectangularCornerPicks=dict(observed=earlier.tolist(),geometry=pick_sensitivity['geometry'],camera=pick_sensitivity['camera'],landmarkRmsPixels=pick_sensitivity['landmarkRmsPixels']),
        mullionsNotUsedInPoseFit=dict(observed=heldout_observed.tolist(),predicted=predicted.tolist(),
            rmsPixels=float(np.sqrt(np.mean(np.sum((predicted-heldout_observed)**2,axis=1))))),
        limitations=['Manual correspondences and an uncalibrated pinhole model; principal y absorbs unknown cropping.',
                     'Fixed camera height and assumed metre dimensions prevent treating this as a metric survey.',
                     'Sensitivity trials are bounded alternatives, not statistical confidence intervals.',
                     'No independent aerial registration, lens correction, complete column count or production acceptance.'],
        photoRegistrationAccepted=False,productionReady=False,wholeBuildingAccepted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();r=report();args.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:{j:r[k][j] for j in ('geometry','landmarkRmsPixels','roofRmsPixels','activeBounds')} for k in ('fixedGeometry','jointFit','roundedCandidate')},indent=2))
