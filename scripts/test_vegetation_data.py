import copy
import ast
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from shapely.geometry import box, Polygon, Point
from vegetation_data import load_zones, filter_zones, apply_stage, load_background, generate_background
from vegetation_layout import tree_rotation


class VegetationDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        for name in ['sources', 'huicui-sources', 'basketball-sources', 'building-sources']:
            (self.root / f'data/{name}.json').write_text(json.dumps([{'id': 'osm'}] if name == 'sources' else []))
        self.zone = dict(id='lawn', type='no-tree', stage='campus-roads', maskRef='mapped-lawn', sourceRefs=['osm'], evidence='Mapped boundary and user correction.')
        self.save([self.zone])

    def save(self, zones):
        (self.root / 'data/vegetation-zones.json').write_text(json.dumps(dict(schemaVersion=1, zones=zones)))

    def test_stage_uses_crowns_and_preserves_survivors(self):
        trees = [[-9,5,9,0], [-4,5,9,1], [5,5,9,0], [17,5,9,2], [25,5,12,0]]
        original = copy.deepcopy(trees)
        masks = {'mapped-lawn': box(0,0,10,10)}
        kept = apply_stage(trees, 'campus-roads', masks, self.root)
        self.assertEqual(kept, [trees[0], trees[3], trees[4]])
        self.assertEqual(trees, original)
        self.assertEqual(apply_stage(kept, 'campus-roads', masks, self.root), kept)
        # A local enlargement removes one additional tree, without modifying any survivor.
        wider = apply_stage(trees, 'campus-roads', {'mapped-lawn': box(0,0,15,10)}, self.root)
        self.assertEqual(wider, [trees[0], trees[4]])
        self.assertEqual([tree_rotation(*t[:2]) for t in wider], [tree_rotation(*trees[i][:2]) for i in [0,4]])

    def test_invalid_sources_rules_ids_and_unresolved_masks_fail(self):
        for field, value in [('sourceRefs', ['missing']), ('type', 'avenue'), ('evidence', ''), ('stage', 'missing'), ('maskRef', '')]:
            z = {**self.zone, field: value}; self.save([z])
            with self.assertRaises(ValueError): load_zones(self.root)
        self.save([self.zone, self.zone])
        with self.assertRaisesRegex(ValueError, 'duplicate'): load_zones(self.root)
        self.save([self.zone])
        with self.assertRaisesRegex(ValueError, 'Unresolved'): apply_stage([], 'campus-roads', {}, self.root)
        with self.assertRaisesRegex(ValueError, 'Invalid'): apply_stage([], 'campus-roads', {'mapped-lawn': Polygon()}, self.root)

    def test_multiple_masks_are_unioned_without_duplicate_rows(self):
        zones = [self.zone, {**self.zone, 'id': 'second', 'maskRef': 'other'}]
        trees = [[5,5,9,0], [12,5,9,1], [30,5,9,0]]
        masks = {('campus-roads', 'mapped-lawn'): box(0,0,10,10), ('campus-roads', 'other'): box(8,0,18,10)}
        self.assertEqual(filter_zones(trees, zones, masks), [trees[2]])
        self.assertEqual(filter_zones(trees, list(reversed(zones)), masks), [trees[2]])

    def test_rotation_is_position_based_not_list_or_sector_order(self):
        rows = [[-450.1,-0.1,9,0], [0,0,12,2], [450.1,900.2,10,1]]
        original = {tuple(t[:2]): tree_rotation(*t[:2]) for t in rows}
        for survivors in [rows[1:], list(reversed(rows)), rows + [[901,901,9,0]]]:
            for t in survivors:
                angle = tree_rotation(*t[:2]); self.assertTrue(0 <= angle < math.tau)
                if tuple(t[:2]) in original: self.assertEqual(angle, original[tuple(t[:2])])

    def test_incremental_blender_updates_use_position_after_reindexing(self):
        root = Path(__file__).resolve().parents[1]
        trees = [[-450.1,-0.1,9,0,1.2], [450.1,900.2,10,1,3.4]]
        for filename in ['update_roads.py', 'update_basketball.py']:
            # Execute the actual survivor-update branch without rebuilding unrelated roads.
            syntax = ast.parse((root / 'blender' / filename).read_text())
            branch = next(n for n in syntax.body if isinstance(n, ast.For) and isinstance(n.iter, ast.Name) and n.iter.id == 'survivors')
            objects = [SimpleNamespace(name='', rotation_euler=SimpleNamespace(z=None), location=SimpleNamespace(z=None)) for _ in trees]
            namespace = {'tree_rotation': tree_rotation, 'trees': trees}
            scope = {'survivors': list(zip(objects, range(len(trees)))), 'trees': trees, 'namespace': namespace, 'ns': namespace}
            exec(compile(ast.Module(body=[branch], type_ignores=[]), filename, 'exec'), scope)
            self.assertEqual([o.rotation_euler.z for o in objects], [tree_rotation(*t[:2]) for t in trees])
            self.assertEqual([o.location.z for o in objects], [t[4] for t in trees])


class BackgroundVegetationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_background(Path(__file__).resolve().parents[1])
        self.area = box(-130,-130,130,130)
        self.green = box(-100,-100,100,100)

    def generate(self, valid=None, green=None, bounds=None):
        return generate_background(bounds or self.area.bounds, self.area if valid is None else valid,
                                   self.green if green is None else green, self.config)

    def test_early_local_obstacle_cannot_reseed_distant_cells(self):
        patch = box(-120,-120,-65,-65)
        before = self.generate()
        after = self.generate(valid=self.area.difference(patch))
        self.assertEqual(after, [t for t in before if not patch.covers(Point(t[:2]))])
        self.assertLess(len(after), len(before))

    def test_local_green_density_change_keeps_other_cells_identical(self):
        patch = box(-100,-100,-35,-35)
        before = self.generate(green=Polygon())
        after = self.generate(green=patch)
        outside = lambda rows: [t for t in rows if not patch.covers(Point(t[:2]))]
        self.assertEqual(outside(before), outside(after))
        self.assertGreater(len(after), len(before))

    def test_crop_and_expand_bounds_preserve_negative_and_positive_cells(self):
        original = self.generate()
        larger = self.generate(bounds=(-200,-200,200,200))
        self.assertEqual(larger, original)
        bounds = (-70,-40,80,90)
        cropped = self.generate(bounds=bounds)
        self.assertEqual(cropped, [t for t in original if box(*bounds).covers(Point(t[:2]))])
        self.assertEqual(len({tuple(t[:2]) for t in original}), len(original))

    def test_repeated_and_tiled_generation_are_identical(self):
        rows = self.generate()
        self.assertEqual(rows, self.generate())
        left = self.generate(bounds=(-130,-130,0,130))
        right = self.generate(bounds=(0,-130,130,130))
        self.assertEqual(sorted(rows), sorted(left+right))
        for x,y,h,typ in rows:
            self.assertTrue(9 <= h <= 17 and typ in (0,1,2))

    def test_invalid_background_parameters_are_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); (target/'data').mkdir()
            for name in ['sources','huicui-sources','basketball-sources','building-sources']:
                (target/f'data/{name}.json').write_text((root/f'data/{name}.json').read_text())
            for field,value in [('seed',True),('jitterMeters',7),('spacingMeters',0),('otherDensity',float('nan')),
                                ('heightRangeMeters',[17,9]),('typeWeights',[0,0,0]),('sourceRefs',['missing'])]:
                cfg={**self.config,field:value}
                (target/'data/vegetation-zones.json').write_text(json.dumps(dict(schemaVersion=1,zones=[],background=cfg)))
                with self.assertRaises(ValueError): load_background(target)


if __name__ == '__main__': unittest.main()
