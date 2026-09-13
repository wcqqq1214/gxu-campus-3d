import copy
import unittest
from shapely.geometry import Polygon
from attached_gallery_data import resolve_attached_gallery, validate_gallery_context
from test_vegetation_exclusions import context
from vegetation_exclusions import final_ground_exclusions


class AttachedGalleryTests(unittest.TestCase):
    def test_parser_rejects_conflicting_rules_and_preserves_derived_identity(self):
        from building_overrides import resolve_building, footprint_revision
        b,f,p=self.fixture();b.update(name='Teaching block',category='academic',tags={},height=6.6,levels=2,center=[4,5])
        rule=dict(polygon=0,ring=0,edge=0,balconies=False,attachedGallery=p)
        record=dict(footprintRevision=footprint_revision(b),levels=2,roof={'type':'hipped','rise':1.4},facadeRules=[rule],evidence={})
        for key in ('levels','roof.type','roof.rise','facadeRules'):
            record['evidence'][key]=dict(status='estimated',sourceRefs=['osm'],note='test fixture')
        result=resolve_building(b,record,{'osm'})
        self.assertEqual(result['polygons'],b['polygons'])
        self.assertIn('attachedGallery',result['form']['facades'][0])
        for extra in [{'windows':False},{'balconies':True},{'spacing':3},
                      {'panels':[]},{'windowGrid':{}},{'openCorridor':{}}]:
            bad=copy.deepcopy(record);bad['facadeRules'][0].update(extra)
            with self.subTest(extra=extra),self.assertRaises(ValueError):resolve_building(b,bad,{'osm'})

    def fixture(self):
        b={'id':'test','polygons':[[[[0,0],[8,0],[8,10],[0,10],[0,0]]]]}
        f=dict(polygon=0,ring=0,edge=0,part='body',start=[0,0],end=[8,0],normal=[0,-1],height=6.6,levels=2)
        p=dict(depth=2.8,endInset=.15,railHeight=.9,balusterWidth=.11,balusterSpacing=.32,
               roofDrop=.25,slabThickness=.18,upperOpenings=[dict(t=.5,width=1,bottom=3.3,top=6.05,kind='door')])
        return b,f,p

    def test_gallery_preserves_outline_and_rotates_outward(self):
        b,f,p=self.fixture();original=copy.deepcopy(b['polygons'])
        g=resolve_attached_gallery(b,f,{'roof':{'type':'hipped'}},p)
        self.assertEqual(b['polygons'],original)
        self.assertAlmostEqual(Polygon(g['footprint']).area,7.7*2.8)
        for point in g['footprint']:self.assertLessEqual(point[1],0)
        b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]]
        for key in ('start','end','normal'):x,y=f[key];f[key]=[-y,x]
        turned=resolve_attached_gallery(b,f,{'roof':{'type':'hipped'}},p)
        self.assertAlmostEqual(Polygon(turned['footprint']).area,Polygon(g['footprint']).area)
        self.assertGreaterEqual(min(v[0] for v in turned['footprint']),0)

    def test_invalid_dimensions_openings_and_context(self):
        b,f,p=self.fixture();part={'roof':{'type':'hipped'}}
        for key,value in [('depth',float('nan')),('depth',True),('depth',5),('endInset',-.1),('balusterSpacing',.22),('roofDrop',0)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):resolve_attached_gallery(b,f,part,{**p,key:value})
        for patch in [{'bottom':3.4},{'t':0},{'top':7},{'width':True},{'kind':'unknown'}]:
            bad=copy.deepcopy(p);bad['upperOpenings'][0].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):resolve_attached_gallery(b,f,part,bad)
        bad=copy.deepcopy(p);bad['upperOpenings']*=2
        with self.assertRaisesRegex(ValueError,'overlap'):resolve_attached_gallery(b,f,part,bad)
        for part_change in [{'roof':{'type':'flat'}},{**part,'openBelow':{}}]:
            with self.assertRaises(ValueError):resolve_attached_gallery(b,f,part_change,p)
        f['attachedGallery']=resolve_attached_gallery(b,f,part,p);b['form']={'facades':[f]}
        validate_gallery_context([b])
        other={'id':'neighbor','polygons':[[[[1,-2],[2,-2],[2,-1],[1,-1],[1,-2]]]]}
        with self.assertRaisesRegex(ValueError,'another building'):validate_gallery_context([b,other])
        b['form']['entrances']=[{'stairFlight':{'footprint':other['polygons'][0][0]}}]
        with self.assertRaisesRegex(ValueError,'entrance'):validate_gallery_context([b])

    def test_zero_inset_follows_oblique_wings_without_gaps(self):
        b,f,p=self.fixture()
        with self.assertRaisesRegex(ValueError,'enclosing'):resolve_attached_gallery(b,f,{'roof':{'type':'hipped'}},{**p,'endInset':0})
        b['polygons']=[[[[0,-4],[.01,0],[8,0],[8.02,-4],[12,-4],[12,10],[-4,10],[-4,-4],[0,-4]]]]
        f.update(edge=1,start=[.01,0],end=[8,0])
        g=resolve_attached_gallery(b,f,{'roof':{'type':'hipped'}},{**p,'endInset':0})
        self.assertTrue(g['boundedEnds'])
        from shapely.geometry import LineString
        shape=Polygon(g['footprint']);ring=b['polygons'][0][0]
        for side in [LineString(ring[:2]),LineString(ring[2:4])]:
            self.assertGreater(shape.boundary.intersection(side.buffer(1e-7)).length,2.79)
        self.assertLess(shape.intersection(Polygon(ring)).area,1e-6)

    def test_gallery_excludes_planting_on_new_occupied_ground(self):
        b,f,p=self.fixture();f['attachedGallery']=resolve_attached_gallery(b,f,{'roof':{'type':'hipped'}},p)
        b['form']={'facades':[f]};data=context();data['buildings']=[b]
        rows=[[4,-1,9,0],[4,-2.8,9,0],[4,-4,9,0]]
        kept,report=final_ground_exclusions(rows,data)
        self.assertEqual(kept,[rows[-1]])
        self.assertEqual(report['maskCounts']['attached-gallery'],1)
