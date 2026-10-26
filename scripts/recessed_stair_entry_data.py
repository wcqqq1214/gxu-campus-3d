"""Two rising flights through a mapped open frame to a courtyard rear wall."""
import math
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union


def resolve_recessed_stair_entry(b, entry, config, parts):
    fields={'framePart','rearRing','rearEdge','platformHeight','doorLandingHeight','platformWidth','stairWidth','outerRisers','innerRisers','tread','rearLandingDepth','toeInset','baseHeight','doorHeight','canopy','apronFrontHeights'}
    if not isinstance(config,dict) or set(config)-{'hall','forecourt','landscape'}!=fields:
        raise ValueError('Recessed stair entry requires explicit frame, rear anchor, flights and canopy')
    for key in fields-{'framePart','rearRing','rearEdge','outerRisers','innerRisers','canopy','apronFrontHeights','toeInset'}:
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]) or config[key]<=0:
            raise ValueError('Recessed stair entry dimensions must be positive finite numbers')
    for key in ('outerRisers','innerRisers'):
        if type(config[key]) is not int or not 2<=config[key]<=32:
            raise ValueError('Recessed stair flights need 2–32 risers')
    polygon=b['polygons'][entry['polygon']]
    ri,ei=config['rearRing'],config['rearEdge']
    if type(ri) is not int or not 1<=ri<len(polygon) or type(ei) is not int or not 0<=ei<len(polygon[ri])-1:
        raise ValueError('Rear doorway must name a mapped courtyard wall')
    frame=next((p for p in parts if p['id']==config['framePart']),None)
    if not frame or 'slattedRoof' not in frame.get('openBelow',{}):
        raise ValueError('Recessed stair entry requires an existing open lattice frame')
    n=[math.sin(math.radians(entry['bearing'])),math.cos(math.radians(entry['bearing']))];u=[n[1],-n[0]]
    front=entry['center']
    def point(w,d):return [front[i]+u[i]*w-n[i]*d for i in (0,1)]
    rear_line=LineString(polygon[ri][ei:ei+2])
    hit=rear_line.intersection(LineString([point(0,0),point(0,50)]))
    if hit.geom_type!='Point':raise ValueError('Entry axis must reach its rear wall')
    recess=hit.distance(Point(front));rear=list(hit.coords)[0]
    door=LineString([point(-entry['width']/2,recess),point(entry['width']/2,recess)])
    if not rear_line.buffer(.01).covers(door):raise ValueError('Doorway must fit its mapped rear wall')
    base,floor,upper=(config[k] for k in ('baseHeight','platformHeight','doorLandingHeight'))
    if not 0<base<floor<upper<frame['openBelow']['clearHeight']-3 or not 2<=config['doorHeight']<=3.5:
        raise ValueError('Entry landings and door conflict with the overhead frame')
    toe=config['toeInset'];court=config.get('forecourt')
    if type(toe) not in (int,float) or not math.isfinite(toe) or not (-8<=toe<=-2 if court else .5<=toe<=3):
        raise ValueError('Unsupported stair toe position')
    if not .25<=config['tread']<=.4 or not 1<=config['rearLandingDepth']<=4:
        raise ValueError('Unsupported stair tread or landing depth')
    for rise,count in [(floor-base,config['outerRisers']),(upper-floor,config['innerRisers'])]:
        if not .1<=rise/count<=.2:raise ValueError('Stair risers must lie between 0.1 and 0.2 metres')
    w,pw=config['stairWidth'],config['platformWidth']
    if not entry['width']+.4<=w<=pw:raise ValueError('Stair and platform must contain the doorway')
    inner_end=recess-config['rearLandingDepth']
    inner_start=inner_end-(config['innerRisers']-1)*config['tread']
    toe=config['toeInset']
    outer_end=toe+(config['outerRisers']-1)*config['tread']
    if inner_start-outer_end<1.2:raise ValueError('Flights leave no intermediate landing')
    def rect(width,d0,d1):return Polygon([point(-width/2,d0),point(width/2,d0),point(width/2,d1),point(-width/2,d1)])
    apron_start=0;front_width=pw
    if court:
        if not isinstance(court,dict) or set(court)!={'frontDistance','frontWidth'} or any(type(v) not in (int,float) or not math.isfinite(v) for v in court.values()):
            raise ValueError('Forecourt needs an explicit finite frontage and projection')
        if not -toe+2<=court['frontDistance']<=20 or not pw<=court['frontWidth']<=24:
            raise ValueError('Unsupported forecourt extent')
        apron_start=-court['frontDistance'];front_width=court['frontWidth']
    apron=Polygon([point(-front_width/2,apron_start),point(front_width/2,apron_start),point(pw/2,toe),point(-pw/2,toe)])
    footprint=rect(pw,min(0,toe),recess).union(apron)
    body=unary_union([Polygon(p[0],p[1:]) for part in parts if 'openBelow' not in part for p in part['polygons']])
    if footprint.intersection(body.buffer(-.01)).area>1e-5:raise ValueError('Entry platforms or flights intersect solid building parts')
    frame_shape=unary_union([Polygon(p[0],p[1:]) for p in frame['polygons']])
    if not frame_shape.buffer(.01).covers(LineString([point(-pw/2,0),point(pw/2,0)])):
        raise ValueError('Entry platform does not fit its frame frontage')
    route=rect(w,0,recess)
    for col in frame['openBelow']['columns']:
        if Point(col['center']).buffer(max(col['width'],col['depth'])/2).intersects(route):
            raise ValueError('Existing frame column obstructs the stair route')
    c=config['canopy'];keys={'width','depth','frontOffset','topHeight','thickness','columnDiameter','columnInset'}
    if not isinstance(c,dict) or set(c)-{'portalBeam'}!=keys or any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) for k in keys):
        raise ValueError('Canopy requires finite explicit dimensions')
    if not w+.6<=c['width']<=pw or not 2<=c['depth']<=10 or not -2<=c['frontOffset']<=0 or not .15<=c['thickness']<=.6 or not .4<=c['columnDiameter']<=1:
        raise ValueError('Unsupported low canopy size')
    if not upper+config['doorHeight']+.3<c['topHeight']-c['thickness']<c['topHeight']<frame['openBelow']['clearHeight']-.5:
        raise ValueError('Low canopy conflicts with the entry headroom or upper lattice')
    inset=c['columnInset'];radius=c['columnDiameter']/2
    if not radius<=inset<min(c['width'],c['depth'])/2-radius or c['width']-2*inset-2*radius<w:
        raise ValueError('Low canopy columns obstruct the stair width')
    d0=-c['frontOffset'];d1=d0+c['depth']
    if d0+inset<0 or d1-inset>inner_start:
        raise ValueError('Canopy columns must remain within the entrance approach')
    if rect(c['width'],d0,d1).intersection(body).area>1e-5:
        raise ValueError('Low canopy intersects the solid building')
    columns=[point(x,d) for x in (-c['width']/2+inset,c['width']/2-inset) for d in (d0+inset,d1-inset)]
    if 'portalBeam' in c:
        beam=c['portalBeam'];keys={'width','depth','topHeight','thickness'}
        if not isinstance(beam,dict) or set(beam)!=keys or any(type(v) not in (int,float) or not math.isfinite(v) for v in beam.values()):
            raise ValueError('Portal beam needs explicit finite dimensions')
        if not c['width']<=beam['width']<=16 or not .8<=beam['depth']<=2.5 or not .5<=beam['thickness']<=1.5:
            raise ValueError('Unsupported portal beam dimensions')
        if not c['topHeight']+1<beam['topHeight']-beam['thickness']<beam['topHeight']<frame['openBelow']['clearHeight']-1:
            raise ValueError('Portal beam conflicts with the canopies')
        shape=rect(beam['width'],d0+inset-beam['depth']/2,d0+inset+beam['depth']/2)
        if not frame_shape.buffer(.01).covers(shape):raise ValueError('Portal beam must stay inside the open frame')
    heights=config['apronFrontHeights']
    if (not isinstance(heights,list) or len(heights)!=13 or
            any(type(h) not in (int,float) or not math.isfinite(h) or not 0<=h<=(base+1.5 if court else base) for h in heights)):
        raise ValueError('Approach needs 13 ground-relative edge heights at equal width intervals')
    from architecture_data import pack
    floor_geometry=pack(frame_shape.difference(footprint),'retained-frame-floor',frame['openBelow']['floorHeight'])
    floor_geometry['polygons']=[[[list(v) for v in ring] for ring in rings] for rings in floor_geometry['polygons']]
    result={**config,'apronStart':apron_start,'apronFrontWidth':front_width,'frameFloor':{k:floor_geometry[k] for k in ('polygons','triangles')},'rearCenter':list(rear),'recess':recess,'innerStart':inner_start,'innerEnd':inner_end,'outerEnd':outer_end,'toe':toe,'columns':columns,'footprint':[list(p) for p in footprint.exterior.coords]}
    if 'hall' in config:
        hall=config['hall'];keys={'part','width','depth','clearHeight','galleryWidth','galleryStart'}
        if not isinstance(hall,dict) or set(hall)!=keys or any(type(hall[k]) not in (int,float) or not math.isfinite(hall[k]) for k in keys-{'part'}):
            raise ValueError('Hall requires explicit finite dimensions and a solid part')
        part=next((v for v in parts if v.get('id')==hall['part'] and 'openBelow' not in v),None)
        if not part or not w<=hall['width']<=pw or not 2<=hall['depth']<=6 or not 3<=hall['clearHeight']<=6:
            raise ValueError('Unsupported recessed hall dimensions')
        if not 1<=hall['galleryWidth']<=2 or not 0<=hall['galleryStart']<inner_start:
            raise ValueError('Unsupported side gallery')
        solid=unary_union([Polygon(poly[0],poly[1:]) for poly in part['polygons']])
        cavity=rect(hall['width'],recess-.05,recess+hall['depth'])
        if not solid.buffer(.06).covers(rect(hall['width'],recess+.06,recess+hall['depth'])):
            raise ValueError('Hall must stay inside its mapped crossbar')
        if upper+hall['clearHeight']>=part['height']:
            raise ValueError('Hall cuts through the roof')
        geometry=pack(solid.difference(cavity),'hall-wall-section',1)
        geometry['polygons']=[[[list(v) for v in ring] for ring in rings] for rings in geometry['polygons']]
        result['hall']={**hall,'wallGeometry':{k:geometry[k] for k in ('polygons','triangles')}}
    if 'landscape' in config:
        from entry_forecourt_data import resolve_landscape
        result['landscape'],extra=resolve_landscape(config['landscape'],result)
        expanded=footprint.union(Polygon([point(w,d) for w,d in extra.exterior.coords]))
        if expanded.geom_type!='Polygon' or not expanded.is_valid:raise ValueError('Invalid landscape footprint')
        result['footprint']=[list(v) for v in expanded.exterior.coords]
    return result
