import copy
import unittest
from corridor_detail_data import validate_corridor_details


class CorridorDetailTests(unittest.TestCase):
    def rule(self):
        return {'windows': False, 'openCorridor': {'endInset': .35,
            'finish': {'wall': 'white', 'rail': 'pink'},
            'openings': [{'kind': 'door', 't': .2, 'width': 1., 'height': 2.15,
                          'sill': 0., 'levels': [0, 1, 2, 3]}]}}

    def check(self, rule):
        validate_corridor_details(rule, 15, 13.2, 4)

    def test_openings_accept_four_floors_and_do_not_mutate_input(self):
        rule = self.rule(); before = copy.deepcopy(rule)
        self.check(rule)
        self.assertEqual(rule, before)

    def test_rejects_window_duplicates_and_unsupported_material(self):
        for patch in ('windows', 'finish', 'overlap'):
            rule = self.rule()
            if patch == 'windows': rule['windows'] = True
            if patch == 'finish': rule['openCorridor']['finish']['wall'] = 'custom'
            if patch == 'overlap': rule['openCorridor']['openings'] *= 2
            with self.subTest(patch=patch), self.assertRaises(ValueError): self.check(rule)

    def test_rejects_crossing_slab_returns_and_invalid_levels(self):
        for key, value in [('height', 3.0), ('t', .99), ('width', True),
                           ('sill', .1), ('levels', [4]), ('levels', [True]),
                           ('levels', [1, 1]), ('t', float('nan'))]:
            rule = self.rule(); rule['openCorridor']['openings'][0][key] = value
            if key == 'height':
                rule['openCorridor']['openings'][0].update(kind='window', sill=.2)
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): self.check(rule)

    def test_separate_floor_openings_can_share_a_position(self):
        rule = self.rule(); first = rule['openCorridor']['openings'][0]
        first['levels'] = [0]; second = copy.deepcopy(first); second['levels'] = [1, 2, 3]
        rule['openCorridor']['openings'].append(second)
        self.check(rule)
