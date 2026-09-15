"""Evidence-attributed open return stair in an existing mapped round footprint."""
import copy,hashlib,json,math


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_stair_tower(c):
    keys={'host','baseHeight','landingCut','flightWidth','wellWidth','risersPerFlight','slabThickness','parapetHeight','parapetThickness','roofThickness','bridgeWidth','doorWidth','doorHeight','columns'}
    if not isinstance(c,dict) or set(c)!=keys:raise ValueError('Invalid stair tower fields')
    host=c['host']
    if not isinstance(host,dict) or set(host)!={'buildingId','footprintRevision','polygon','ring','edge','t'}:raise ValueError('Stair tower needs a complete host facade anchor')
    if type(c['risersPerFlight']) is not int or not 6<=c['risersPerFlight']<=16:raise ValueError('Invalid stair riser count')
    limits={'baseHeight':(.1,.3),'landingCut':(1.5,3),'flightWidth':(1.5,2.5),'wellWidth':(.6,1.5),'slabThickness':(.15,.3),'parapetHeight':(.8,1.2),'parapetThickness':(.12,.25),'roofThickness':(.15,.4),'bridgeWidth':(2,3),'doorWidth':(1.2,2),'doorHeight':(2,2.5)}
    for k,(lo,hi) in limits.items():
        v=c[k]
        if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid stair '+k)
    if c['doorWidth']>c['bridgeWidth']-.4:raise ValueError('Stair doorway does not fit the bridge')
    if not isinstance(c['columns'],list) or not 4<=len(c['columns'])<=8:raise ValueError('Stair tower needs explicit supports')
    for p in c['columns']:
        if set(p)!={'center','width','top'} or p['top'] not in ['roof','landing']:raise ValueError('Invalid stair support')
        if not isinstance(p['center'],list) or len(p['center'])!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p['center']):raise ValueError('Invalid stair support centre')
        if type(p['width']) not in (int,float) or not .25<=p['width']<=.7:raise ValueError('Invalid stair support width')


def context(b,host,c):
    return digest([c,b['polygons'],b['height'],b['levels'],host['polygons'],host['center'],host['height'],host['levels']])


def resolve_stair_tower_context(buildings):
    from shapely.geometry import Polygon,box,LineString
    from shapely.geometry.polygon import orient
    from shapely.affinity import rotate,translate
    from shapely.ops import unary_union
    from building_overrides import anchor,footprint_revision,pack_geometry
    by_id={b['id']:b for b in buildings}
    for b in buildings:b.get('form',{}).pop('stairAccessDoors',None)
    for b in buildings:
        form=b.get('form',{})
        if 'stairTower' not in form:continue
        c=form['stairTower']['config'];validate_stair_tower(c);h=c['host'];host=by_id.get(h['buildingId'])
        if not host or host['id']==b['id'] or 'stairTower' in host.get('form',{}) or footprint_revision(host)!=h['footprintRevision']:
            raise ValueError('Missing or stale stair host')
        if host['levels']!=b['levels'] or b['levels'] not in [2,3,4,5,6] or len(b['polygons'])!=1 or len(b['polygons'][0])!=1:
            raise ValueError('Stair needs a simple footprint and matching host levels')
        a,d,n,length=anchor(host,h,exterior=True);t=h['t']
        if type(t) not in (int,float) or not 0<t<1 or min(t,1-t)*length<c['bridgeWidth']/2:raise ValueError('Stair bridge exceeds its host facade')
        target=[a[i]+(d[i]-a[i])*t for i in (0,1)];angle=math.atan2(-n[0],-n[1])*-1
        # Local +Y points toward the host; +X is along its facade.
        cs,sn=math.cos(angle),math.sin(angle);origin=b['center']
        def local(p):
            x,y=p[0]-origin[0],p[1]-origin[1];return [x*cs+y*sn,-x*sn+y*cs]
        def world(p):return [origin[0]+p[0]*cs-p[1]*sn,origin[1]+p[0]*sn+p[1]*cs]
        ring=[local(p) for p in b['polygons'][0][0]];foot=Polygon(ring);end=local(target)
        if abs(end[0])>.02 or not 1<end[1]-foot.bounds[3]<8:raise ValueError('Stair bridge must face the nearest host wall')
        cut=c['landingCut'];flight=c['flightWidth'];well=c['wellWidth'];width=c['bridgeWidth']
        positive=foot.intersection(box(-100,cut,100,100));negative=foot.intersection(box(-100,-100,100,-cut))
        bridge=box(-width/2,cut,width/2,end[1]);upper=unary_union([positive,bridge]);extra=bridge.difference(foot)
        lanes=[box(well/2,-cut,well/2+flight,cut),box(-well/2-flight,-cut,-well/2,cut)]
        if not all(foot.covers(lane) for lane in lanes) or min(positive.area,negative.area)<5:raise ValueError('Flights and landings do not fit the mapped tower')
        gap=host['height']/host['levels'];top=c['baseHeight']+(b['levels']-1)*gap
        if not 2<=b['height']-c['roofThickness']-top<=3:raise ValueError('Stair canopy has insufficient headroom')
        if gap/2-c['slabThickness']<1:raise ValueError('Invalid stair storey clearance')
        occupied=translate(rotate(extra,angle,use_radians=True,origin=(0,0)),*origin)
        for other in buildings:
            if other['id']==b['id']:continue
            shape=unary_union([Polygon(p[0],p[1:]) for p in other['polygons']])
            if occupied.intersection(shape).area>1e-5:raise ValueError('Stair bridge crosses a mapped building')
        supports=[]
        for p in c['columns']:
            x,y=p['center'];w=p['width'];shape=box(x-w/2,y-w/2,x+w/2,y+w/2)
            support_area=foot if p['top']=='roof' else upper
            if not support_area.covers(shape) or any(shape.intersection(lane).area>1e-5 for lane in lanes) or any(shape.intersection(q).area>1e-5 for q in supports):raise ValueError('Stair support obstructs a flight or leaves its platform')
            if p['top']=='landing' and abs(x)-w/2<c['doorWidth']/2:raise ValueError('Bridge support obstructs its doorway axis')
            supports.append(shape)
        def packed(shape):
            polys,triangles=pack_geometry([orient(shape,sign=1)]);return dict(polygons=polys,triangles=triangles)
        doors=[]
        for level in range(1,int(b['levels'])):
            doors.append(dict(ownerId=b['id'],center=target,bearing=math.degrees(math.atan2(n[0],n[1]))%360,width=c['doorWidth'],height=c['doorHeight'],floor=c['baseHeight']+level*gap))
        resolved=dict(config=copy.deepcopy(c),origin=origin,angle=angle,hostCenter=host['center'],floorHeight=gap,hostDistance=end[1],ground=packed(foot),north=packed(upper),south=packed(negative),roof=packed(foot),bridgeFootprint=[world(p) for p in extra.exterior.coords],doors=doors,contextRevision=context(b,host,c))
        resolved['geometryRevision']=digest(resolved);form['stairTower']=resolved
        host['form'].setdefault('stairAccessDoors',[]).extend(copy.deepcopy(doors))


def check_prepared_stair_towers(buildings):
    by_id={b['id']:b for b in buildings};expected={}
    for b in buildings:
        s=b.get('form',{}).get('stairTower')
        if not s:continue
        c=s['config'];host=by_id.get(c['host']['buildingId'])
        if not host or s.get('contextRevision')!=context(b,host,c) or s.get('geometryRevision')!=digest({k:v for k,v in s.items() if k!='geometryRevision'}):raise ValueError('Stair tower context is stale; prepare data')
        expected.setdefault(host['id'],[]).extend(s['doors'])
    for b in buildings:
        if b.get('form',{}).get('stairAccessDoors',[])!=expected.get(b['id'],[]):raise ValueError('Stair access doors are stale; prepare data')
