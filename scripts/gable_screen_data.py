"""An evidenced gable-shaped screen on a flat roof, not a pitched roof claim."""
import copy
import math
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def arch_outline(center, width, height, bottom):
    radius=width/2;spring=bottom+height-radius
    return [[center-radius,bottom],[center+radius,bottom]]+[
        [center+radius*math.cos(i*math.pi/16),spring+radius*math.sin(i*math.pi/16)]
        for i in range(17)]+[[center-radius,bottom]]


def resolve_gable_screen(building, form, config):
    from building_overrides import anchor,pack_geometry
    fields={'part','polygon','edge','thickness','shoulderRise','peakRise','peakT','window'}
    if not isinstance(config,dict) or set(config)!=fields:
        raise ValueError('Gable screen requires one complete roof-edge anchor and window')
    for key in ('polygon','edge'):
        if type(config[key]) is not int or config[key]<0:raise ValueError('Invalid gable screen index')
    for key in ('thickness','shoulderRise','peakRise','peakT'):
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]):raise ValueError('Gable screen dimensions must be finite')
    if not .15<=config['thickness']<=.6 or not .5<=config['shoulderRise']<=1.5 or not config['shoulderRise']+1<=config['peakRise']<=5 or not .25<=config['peakT']<=.75:
        raise ValueError('Gable screen profile outside supported bounds')
    parts=form['parts'] or [dict(id='body',polygons=building['polygons'],height=form['height'],roof=form['roof'])]
    matches=[p for p in parts if p['id']==config['part']]
    if len(matches)!=1 or matches[0]['roof']['type']!='flat' or 'openBelow' in matches[0]:
        raise ValueError('Gable screen needs one solid flat support part')
    if any(form.get(k,{}).get('part')==config['part'] for k in ('roofCrown','roofEave','roofDome')) or 'stairTower' in form:
        raise ValueError('Gable screen conflicts with another feature on its support')
    part=matches[0]
    a,b,n,length=anchor({**building,'polygons':part['polygons']},{'polygon':config['polygon'],'ring':0,'edge':config['edge']})
    if not 4<=length<=30:raise ValueError('Gable screen edge length outside supported bounds')
    u=[(b[i]-a[i])/length for i in (0,1)]
    at=lambda s,d:[a[i]+u[i]*s-n[i]*d for i in (0,1)]
    footprint=Polygon([at(0,0),at(length,0),at(length,config['thickness']),at(0,config['thickness'])])
    support=unary_union([Polygon(p[0],p[1:]) for p in part['polygons']])
    # Mapped adjoining edges are only approximately perpendicular. Bound their
    # micrometre corner mismatch below the source mesh's float32 precision.
    if not support.buffer(1e-5).covers(footprint):raise ValueError('Gable screen leaves its support or enters a courtyard')
    w=config['window'];wf={'centerT','width','height','bottom','frameWidth'}
    if not isinstance(w,dict) or set(w)!=wf or any(type(v) not in (int,float) or not math.isfinite(v) for v in w.values()):
        raise ValueError('Gable window needs finite complete dimensions')
    if not .2<=w['centerT']<=.8 or not .6<=w['width']<=3 or not w['width']/2+.25<=w['height']<=3 or not .2<=w['bottom']<=2 or not .04<=w['frameWidth']<=min(.15,w['width']/6):
        raise ValueError('Gable window dimensions outside supported bounds')
    outline=[[0,0],[length,0],[length,config['shoulderRise']],[length*config['peakT'],config['peakRise']],[0,config['shoulderRise']],[0,0]]
    opening=arch_outline(length*w['centerT'],w['width'],w['height'],w['bottom'])
    glass=arch_outline(length*w['centerT'],w['width']-2*w['frameWidth'],w['height']-2*w['frameWidth'],w['bottom']+w['frameWidth'])
    outer,hole=Polygon(outline),Polygon(opening)
    if not outer.buffer(-.15).covers(hole):raise ValueError('Arched opening must clear the gable profile')
    packed=lambda shape:dict(zip(('polygons','triangles'),pack_geometry([shape])))
    edges=part.get('parapetEdges',[(p,q) for poly in part['polygons'] for ring in poly for p,q in zip(ring,ring[1:])])
    retained=[]
    for p,q in edges:
        line=LineString([p,q]).difference(footprint.buffer(1e-7))
        pieces=[line] if line.geom_type=='LineString' else list(getattr(line,'geoms',[]))
        retained.extend([list(s.coords[0]),list(s.coords[-1])] for s in pieces if s.geom_type=='LineString' and s.length>.01)
    return {**copy.deepcopy(config),'start':list(a),'end':list(b),'normal':list(n),'tangent':u,'length':length,
            'baseHeight':part['height'],'outline':outline,'opening':opening,'glass':glass,
            'wallGeometry':packed(outer.difference(hole)),'frameGeometry':packed(hole.difference(Polygon(glass))),
            'glassGeometry':packed(Polygon(glass)),'footprint':[list(p) for p in footprint.exterior.coords],
            'retainedParapetEdges':retained}
