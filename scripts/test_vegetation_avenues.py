import copy,json,shutil,tempfile,unittest
from pathlib import Path
from shapely.geometry import box,Point
from vegetation_avenues import derive_avenues,apply_avenues,revision


class AvenueTests(unittest.TestCase):
    def test_local_replacement_preserves_other_rows_and_grounded_candidates(self):
        config={'id':'test'}
        avenue={'config':config,'replacement':box(0,0,20,20),
                'candidates':[{'tree':[5,5,10,0]},{'tree':[15,5,10,0]}],'junctionRejected':[]}
        old=[[5,5,10,0,3.25],[10,10,15,1,4],[-5,5,9,2,-2],[100,100,17,0,1]]
        original=copy.deepcopy(old)
        rows,report=apply_avenues(old,[avenue])
        self.assertEqual(rows,[*old[2:],old[0],[15,5,10,0]])
        self.assertEqual(old,original)
        self.assertEqual(report[0]['replacedPriorRows'],2)
        self.assertEqual(apply_avenues(rows,[avenue])[0],rows)
        self.assertEqual(apply_avenues(old,[])[0],old)

    def isolated(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(__file__).resolve().parents[1];target=Path(self.temp.name)
        shutil.copytree(root/'data',target/'data');shutil.copytree(root/'public/data',target/'public/data')
        return target

    def test_junction_opening_uses_station_even_when_rows_are_outside_radius(self):
        from prepare_geodata import inverse
        root=self.isolated();path=root/'data/vegetation-avenues.json'
        config=json.loads(path.read_text());a=config['avenues'][0]
        coords=[list(inverse(0,0)),list(inverse(100,0))]
        a.update(startMeters=1,endMeters=97,junctionClearanceMeters=3,roadRevision=revision(coords))
        geo={'type':'FeatureCollection','features':[
            {'id':'campus','properties':{},'geometry':{'type':'Polygon','coordinates':[[list(inverse(x,y)) for x,y in [(-20,-20),(120,-20),(120,20),(-20,20),(-20,-20)]]]}},
            {'id':a['roadId'],'properties':{'kind':'roads','tags':{}},'geometry':{'type':'LineString','coordinates':coords}},
            {'id':'branch','properties':{'kind':'roads','tags':{}},'geometry':{'type':'LineString','coordinates':[list(inverse(48,0)),list(inverse(48,15))]}}]}
        (root/'public/data/geography.geojson').write_text(json.dumps(geo));path.write_text(json.dumps(config))
        result=derive_avenues(root)[0]
        self.assertEqual(len(result['candidates']),14)
        self.assertEqual({r['stationIndex'] for r in result['junctionRejected']},{4})
        self.assertTrue(all(abs(r['tree'][0]-48)>3 for r in result['candidates']))

    def test_stale_axes_missing_sources_and_invalid_parameters_fail(self):
        root=self.isolated();path=root/'data/vegetation-avenues.json';original=json.loads(path.read_text())
        for field,value in [('roadRevision','bad'),('sourceRefs',['missing']),('spacingMeters',0),
                            ('startMeters',-1),('heightMeters',float('nan')),('template',True),
                            ('replacementHalfWidthMeters',3),('junctionClearanceMeters',0)]:
            data=copy.deepcopy(original);data['avenues'][0][field]=value;path.write_text(json.dumps(data))
            with self.assertRaises(ValueError,msg=field):derive_avenues(root)
        data=copy.deepcopy(original);data['schemaVersion']=True;path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):derive_avenues(root)

    def test_current_pilot_is_bounded_and_deterministic(self):
        root=Path(__file__).resolve().parents[1]
        first=derive_avenues(root);second=derive_avenues(root)
        self.assertEqual(first[0]['candidates'],second[0]['candidates'])
        self.assertTrue(first[0]['candidates'])
        self.assertTrue(all(first[0]['replacement'].covers(Point(r['tree'][:2])) for r in first[0]['candidates']))


if __name__=='__main__':unittest.main()
