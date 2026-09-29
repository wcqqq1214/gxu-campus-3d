import unittest
import numpy as np
from fit_civil_entry_camera import BASE,landmarks,project,roof_prediction,solve


class CameraFitTests(unittest.TestCase):
    def test_level_pinhole_axes_and_depth(self):
        p=BASE.copy();p[:7]=[500,10,0,1.65,0,0,0];p[11]=285
        actual=project(p,[[0,0,1.65],[1,0,1.65],[0,0,2.65],[1,10,1.65]])
        np.testing.assert_allclose(actual,[[427.5,285],[477.5,285],[427.5,235],[452.5,285]])
        with self.assertRaises(ValueError):project(p,[[0,-11,1.65]])

    def test_bounded_solver_recovers_synthetic_pixels(self):
        p=BASE.copy();p[:7]=[550,9,.4,1.65,.04,.07,-.01];p[11]=390
        observed=project(p,landmarks(p));roof=roof_prediction(p)
        fitted=solve(observed=observed,roof_observed=roof)
        self.assertLess(fitted['landmarkRmsPixels'],.001)
        self.assertLess(fitted['roofRmsPixels'],.001)
        self.assertEqual(fitted['activeBounds'],[])


if __name__=='__main__':unittest.main()
