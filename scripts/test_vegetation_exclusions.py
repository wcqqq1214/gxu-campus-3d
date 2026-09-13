import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import Point, Polygon, box
from vegetation_data import prepare_vegetation
from vegetation_exclusions import GroundMask, ground_masks, filter_ground, final_ground_exclusions, INPUT_NAMES


def surface(ident, x=0, kind='roads', **extra):
    return dict(id=ident, kind=kind, vertices=[[x,0],[x+10,0],[x+10,10],[x,10]],
                triangles=[0,1,2,0,2,3], **extra)


def context():
    return {'surfaces': [], 'infrastructure': {'surfaceOverrides': {}, 'replaceSurfaceIds': []},
            'surroundings': {'surfaceOverrides': {}, 'layers': []},
            'campus-roads': {'surfaceOverrides': {}, 'layers': []},
            'sites': {'surfaceOverrides': {}, 'sites': []},
            'pavings': {'pavings': []}, 'shores': {'shores': []}, 'sports': [], 'buildings': []}


class FinalVegetationTests(unittest.TestCase):
    def test_external_portico_platform_excludes_centres_but_preserves_nearby_shade(self):
        data=context()
        data['buildings']=[{'id':'college','polygons':[[list(box(0,0,20,20).exterior.coords)]],
            'form':{'entrances':[{'id':'south','attachedPortico':{
                'footprint':list(box(5,-4,15,0).exterior.coords)}}]}}]
        rows=[[10,-2,9,0],[10,-4,9,0],[10,-5,9,0]]
        kept,report=final_ground_exclusions(rows,data)
        self.assertEqual(kept,[rows[2]])
        self.assertEqual(report['maskCounts'],{'buildings':1,'entrance-platform':1})
        self.assertTrue(all(r['masks']==[{'kind':'entrance-platform','id':'college:south'}]
                            for r in report['removed']))

    def test_boundary_holes_disconnected_masks_and_stable_survivors(self):
        courtyard = Polygon(box(0,0,20,20).exterior.coords, [box(5,5,15,15).exterior.coords])
        masks = [GroundMask('buildings','court',courtyard), GroundMask('roads','path',box(25,0,30,20))]
        rows = [[1,1,9,0,5], [0,10,11,2,-1], [10,10,17,1,3], [26,10,12,0,7], [40,10,15,1,1]]
        original = copy.deepcopy(rows)
        kept, removed = filter_ground(rows, masks)
        self.assertEqual(kept, [rows[2], rows[4]])
        self.assertEqual([r['treeIndex'] for r in removed], [0,1,3])
        self.assertEqual(filter_ground(kept, masks), (kept, []))
        self.assertEqual(filter_ground(rows, list(reversed(masks)))[0], kept)
        self.assertEqual(rows, original)
        self.assertEqual(filter_ground(rows, [])[0], rows)

    def test_final_overlay_order_and_replaced_surfaces(self):
        data = context(); data['surfaces'] = [surface('road'), surface('replaced',100), surface('hidden',200,suppressed=True)]
        data['infrastructure']['replaceSurfaceIds'] = ['replaced']
        for name, x in [('infrastructure',10), ('surroundings',20), ('campus-roads',30), ('sites',40)]:
            data[name]['surfaceOverrides']['0'] = {'vertices': surface('new',x)['vertices']}
        rows = [[5,5,9,0], [45,5,9,0], [105,5,9,0], [205,5,9,0]]
        original = copy.deepcopy(data)
        kept, report = final_ground_exclusions(rows,data)
        self.assertEqual(kept, [rows[0],rows[2],rows[3]])
        self.assertEqual(report['maskCounts'], {'roads':1})
        self.assertEqual(data,original)

    def test_ordinary_shade_retained_and_layered_roads_deferred(self):
        data = context()
        data['surfaces'] = [surface('plain',tags={'bridge':'no'}), surface('bridge',20,tags={'bridge':'yes'}),
                            surface('tunnel',40,tags={'tunnel':'yes'}), surface('layer',60,tags={'layer':'1'})]
        # The first crown extends above the ordinary road but its tree centre is outside.
        rows = [[-1,5,17,0], [5,5,9,0], [25,5,9,0], [45,5,9,0], [65,5,9,0]]
        kept, report = final_ground_exclusions(rows,data)
        self.assertEqual(kept, [rows[0],*rows[2:]])
        self.assertEqual(report['deferredLayeredSurfaceIds'], ['bridge','tunnel','layer'])

    def test_each_final_ground_source_and_invalid_polygons(self):
        data = context()
        data['surfaces'] = [surface('water',0,'water'),surface('sport',20,'sports')]
        data['campus-roads']['layers'] = [surface('road',40)]
        data['surroundings']['layers'] = [surface('walk',60)]
        ring = lambda x: list(box(x,0,x+10,10).exterior.coords)
        data['buildings'] = [{'id':'b','polygons':[[ring(80)]]}]
        data['sports'] = [{'id':'ground','ground':ring(100)}]
        data['sites']['sites'] = [{'id':'entry','pavingPolygon':ring(120)}]
        data['pavings']['pavings'] = [surface('plaza',140)]
        data['shores']['shores'] = [{'id':'shore','capPolygons':[[ring(160)]]}]
        rows = [[x+5,5,9,0] for x in range(0,180,20)]
        kept,report = final_ground_exclusions(rows,data)
        self.assertEqual(kept,[])
        self.assertEqual(sum(report['maskCounts'].values()),9)
        data['buildings'][0]['polygons'] = [[[[0,0],[10,10],[10,0],[0,10],[0,0]]]]
        with self.assertRaisesRegex(ValueError,'Invalid final vegetation mask'):
            ground_masks(data)

    def test_final_preparation_rejects_late_injected_occupied_ground_trees(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            shutil.copytree(root/'data', isolated/'data')
            shutil.copytree(root/'public/data', isolated/'public/data')
            out = isolated/'public/data'
            read = lambda name: json.loads((out/f'{name}.json').read_text())
            original = read('vegetation')
            data = {name:read(name) for name in INPUT_NAMES}
            masks,_ = ground_masks(data)
            zones = [Polygon(z['polygon']) for z in read('vegetation-zones')['zones']]
            injected = []
            for kind in ('buildings','roads','water','sports'):
                mask = next(m for m in masks if m.kind == kind and
                            all(z.distance(m.geometry.representative_point()) > 8 for z in zones))
                p = mask.geometry.representative_point()
                injected.append([p.x,p.y,9,0,0])
            (out/'vegetation.json').write_text(json.dumps(original+injected))
            prepare_vegetation(isolated)
            result = read('vegetation')
            self.assertEqual(result,original, 'Late injected ground conflicts survived the final preparation step')
            report = read('vegetation-zones')['finalGroundExclusion']
            self.assertEqual(report['inputTrees'],len(original)+4)
            self.assertEqual(len(report['removed']),4)
            self.assertEqual(read('overview')['trees'],len(original))
            self.assertEqual([r['tree'] for r in report['removed']],injected)
            prepare_vegetation(isolated)
            self.assertEqual(read('vegetation'),original)
            self.assertEqual(read('vegetation-zones')['finalGroundExclusion']['removed'],[])


if __name__ == '__main__':
    unittest.main()
