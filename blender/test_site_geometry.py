"""Road clipping must preserve both planar elevation and partitioned area."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from site_geometry import split_convex

def area(p):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1])))/2 if p else 0

outline=[(1,1),(4,1),(4,4),(1,4)]
for xy in [[(0,0),(8,0),(0,8)],[(2,2),(3,2),(2,3)],[(-5,0),(-2,0),(-2,3)],[(1,1),(4,1),(1,4)]]:
    triangle=[(x,y,5+2*x+.3*y) for x,y in xy]
    kept,removed=split_convex(triangle,outline)
    assert abs(area(triangle)-area(kept)-sum(area(r) for r in removed))<1e-8
    for ring in [kept]+removed:
        for x,y,z in ring:assert abs(z-(5+2*x+.3*y))<1e-8
    assert all(1-1e-8<=x<=4+1e-8 and 1-1e-8<=y<=4+1e-8 for x,y,_ in kept)
print('Four road clipping cases preserve area and original inclined plane',flush=True)
