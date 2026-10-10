import json
from pathlib import Path
import tempfile
import unittest
from road_landing_contract import load_landings, revision


class RoadLandingContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.entry = dict(id='door', bearing=180, outerCenter=[0,0], porticoWidth=4,
                          steps=3, platformHeight=.45)
        self.surface = dict(id='road', kind='roads', tags={'highway':'service'},
                            vertices=[[-5,-5],[5,-5],[5,0],[-5,0]], triangles=[0,1,2,0,2,3])
        self.config = dict(id='landing', buildingId='building', entranceId='door',
                           surfaceId='road', surfaceRevision=revision(self.surface),
                           anchorRevision=revision([5,self.entry]), sideFeather=2,
                           depthStations=[.2,.65,1.25,4.5], meshStep=1,
                           minimumTerrainClearance=.12)
        self.write('public/data/buildings.json',[dict(id='building',elevation=5,form={'entrances':[self.entry]})])
        self.write('public/data/surfaces.json',[self.surface])
        for name in ['infrastructure','surroundings','campus-roads','sites']:
            self.write('public/data/'+name+'.json',dict(surfaceOverrides={},replaceSurfaceIds=[]))
    def write(self,name,data):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data))
    def load(self):
        self.write('data/road-landing-overrides.json',{'landings':[self.config]})
        return load_landings(self.root)
    def test_existing_stair_datum(self):
        record=self.load()[0]
        self.assertEqual(record['targetElevation'],5)
        self.assertEqual(record['halfWidth'],2)
    def test_changed_entry_rejected(self):
        self.config['anchorRevision']='stale'
        with self.assertRaisesRegex(ValueError,'anchors changed'):self.load()
    def test_changed_overlay_rejected(self):
        self.write('public/data/sites.json',{'surfaceOverrides':{'0':{'vertices':[]}}})
        with self.assertRaisesRegex(ValueError,'anchors changed'):self.load()
    def test_level_band_must_cover_toe(self):
        self.config['depthStations']=[.2,.65,.8,4.5]
        with self.assertRaisesRegex(ValueError,'toe'):self.load()
    def test_nonfinite_dimensions_rejected(self):
        self.config['meshStep']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite'):self.load()

if __name__=='__main__':unittest.main()
