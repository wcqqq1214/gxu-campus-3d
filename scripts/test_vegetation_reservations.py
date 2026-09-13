import copy,json,math,shutil,tempfile,unittest
from pathlib import Path
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
from architecture_data import entrance_tree_masks,clear_entrance_trees
from infrastructure_footprints import strip_shape
from vegetation_data import prepare_vegetation
from vegetation_reservations import CrownReservation,filter_reservations,crown_reservations,INPUT_NAMES


class CrownReservationTests(unittest.TestCase):
    def test_exact_sculpture_radius_boundary_and_stable_survivors(self):
        mask=CrownReservation('sculpture','sculpture',Point(100,-100),13.5)
        rows=[[118.5,-100,9,0,3],[118.500001,-100,9,0,3],[100,-100,12,1,-1],[150,-100,12,2,5]]
        original=copy.deepcopy(rows)
        kept,removed=filter_reservations(rows,[mask])
        self.assertEqual(kept,[rows[1],rows[3]])
        self.assertEqual([r['treeIndex'] for r in removed],[0,2])
        self.assertEqual(rows,original)
        self.assertEqual(filter_reservations(kept,[mask]),(kept,[]))
        self.assertEqual(filter_reservations(rows,[]),(rows,[]))

    def test_courtyard_and_no_unrelated_ordinary_road_buffer(self):
        ring=Polygon(box(0,0,100,100).exterior.coords,[box(10,10,90,90).exterior.coords])
        mask=CrownReservation('entrance','explicit-only',ring)
        rows=[[50,50,9,0],[-4,50,9,0],[-6,50,9,0],[94,50,9,0]]
        kept,_=filter_reservations(rows,[mask])
        self.assertEqual(kept,[rows[0],rows[2]])
        # No generic street layer is accepted by this reservation collector.
        self.assertNotIn('surfaces',INPUT_NAMES)

    def test_rotated_entrance_is_identical_in_early_and_final_filter(self):
        building={'id':'example','landmark':'teaching-ten','architecture':{'origin':[100,200],'angle':math.pi/2}}
        masks=entrance_tree_masks([building])
        self.assertEqual(len(masks),1)
        self.assertTrue(masks[0][1].covers(Point(120,200)))
        rows=[[120,200,9,0],[128,200,9,0],[130,200,9,0],[80,200,9,0]]
        new,_=filter_reservations(rows,[CrownReservation('entrance',i,g) for i,g in masks])
        self.assertEqual(new,[rows[2],rows[3]])
        self.assertEqual(new,clear_entrance_trees(rows,[building]))

    def test_tapered_strip_retains_asymmetric_width_and_rejects_truncation(self):
        path=[[0,0,2],[10,0,3]];axes=[[1,0],[1,0]];sections=[[-3,3,-5,5],[-3,3,-4,6]]
        shape=strip_shape(path,axes,sections,extra=1)
        expected=Polygon([(0,-6),(10,-5),(10,7),(0,6)])
        self.assertLess(shape.symmetric_difference(expected).area,1e-12)
        with self.assertRaisesRegex(ValueError,'matching'):
            strip_shape(path,axes[:1],sections)

    def test_all_current_reservation_witnesses_survive_old_ground_but_fail_final_preparation(self):
        root=Path(__file__).resolve().parents[1]
        witnesses=json.loads((root/'scripts/fixtures/vegetation-reservation-witnesses.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            isolated=Path(directory)
            shutil.copytree(root/'data',isolated/'data')
            shutil.copytree(root/'public/data',isolated/'public/data')
            out=isolated/'public/data';read=lambda n:json.loads((out/f'{n}.json').read_text())
            original=read('vegetation')
            data={n:read(n) for n in INPUT_NAMES}
            masks=crown_reservations(data)
            injected=[w['tree'] for w in witnesses]
            self.assertEqual({m.kind for m in masks},{w['kind'] for w in witnesses})
            for witness in witnesses:
                mask=next(m for m in masks if (m.kind,m.id)==(witness['kind'],witness['id']))
                self.assertEqual(filter_reservations([witness['tree']],[mask])[0],[])
            # Assert the failure mechanism explicitly: centre-only ground masks
            # and the two existing open zones do not reject these crown witnesses.
            from vegetation_exclusions import INPUT_NAMES as GROUND,final_ground_exclusions
            from vegetation_data import filter_zones,load_zones
            self.assertEqual(final_ground_exclusions(injected,{n:read(n) for n in GROUND})[0],injected)
            resolved={('campus-roads',read('campus-roads')['lawn']['osmId']):Polygon(read('campus-roads')['lawn']['polygon'])}
            resolved.update({('sites',s['id']):Polygon(s['pavingPolygon']) for s in read('sites')['sites']})
            self.assertEqual(filter_zones(injected,load_zones(isolated),resolved),injected)
            (out/'vegetation.json').write_text(json.dumps(original+injected))
            prepare_vegetation(isolated)
            result=read('vegetation')
            self.assertEqual(len(result),len(original),'Late crown reservations were bypassed')
            self.assertEqual(result,original)
            report=read('vegetation-zones')['finalCrownReservations']
            self.assertEqual([r['tree'] for r in report['removed']],injected)
            self.assertEqual(report['inputTrees'],len(original)+len(injected))
            self.assertEqual(read('overview')['trees'],len(original))
            prepare_vegetation(isolated)
            self.assertEqual(read('vegetation'),original)
            self.assertEqual(read('vegetation-zones')['finalCrownReservations']['removed'],[])


if __name__=='__main__':unittest.main()
