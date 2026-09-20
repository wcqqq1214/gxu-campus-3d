import copy
import unittest
from building_overrides import resolve_facades


class FacadeFinishTests(unittest.TestCase):
    def fixture(self):
        b={'id':'fixture','polygons':[[[[0,0],[10,0],[10,10],[0,10],[0,0]]]]}
        form={'parts':[],'height':10.8,'levels':3,'roof':{'type':'flat','rise':0}}
        rule=dict(polygon=0,ring=0,edge=0,wallFinish='white',balconies=False,
                  windowGrid=dict(columns=3,firstLevel=0,edgeInset=.55,widthRatio=.5,heightRatio=.4,pilasterWidth=0,pilasterDepth=0,paneRows=1))
        return b,form,rule

    def test_complete_white_wall_and_unpilastered_windows_preserve_input(self):
        b,form,rule=self.fixture();before=copy.deepcopy((b,form,rule));fs=resolve_facades(b,form,[rule])
        self.assertEqual(next(f for f in fs if f['rule'])['rule'],rule)
        self.assertEqual((b,form,rule),before)

    def test_rejects_unknown_finish_and_conflicting_recess(self):
        for patch in [dict(wallFinish='blue'),dict(wallFinish=True),dict(balconies=True),dict(openCorridor={})]:
            b,form,r=self.fixture();r.update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):resolve_facades(b,form,[r])

    def test_rejects_half_disabled_or_nonfinite_pilasters(self):
        for w,d in [(0,.2),(.2,0),(-.1,.2),(True,.2),(.2,float('nan'))]:
            b,form,r=self.fixture();r['windowGrid'].update(pilasterWidth=w,pilasterDepth=d)
            with self.subTest(w=w,d=d),self.assertRaises(ValueError):resolve_facades(b,form,[r])

    def test_rejects_painting_only_part_of_a_wall(self):
        b,form,r=self.fixture();b['polygons'][0][0]=[[0,0],[5,0],[10,0],[10,10],[0,10],[0,0]]
        form['parts']=[dict(id='body',polygons=[[[[0,0],[10,0],[10,10],[0,10],[0,0]]]],height=10.8,levels=3,roof={'type':'flat','rise':0})]
        with self.assertRaises(ValueError):resolve_facades(b,form,[r])
