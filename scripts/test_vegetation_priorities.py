import unittest
from vegetation_priorities import priority_positions


class PriorityTests(unittest.TestCase):
    def test_only_surviving_sourced_trees_are_prioritized(self):
        layout={'avenues':[{'retainedCandidates':[[2,3,9,0],[8,9,9,0]]}],
                'courtyards':[{'retainedCandidates':[[2,3,9,0],[4,5,9,0]]}]}
        trees=[[0,0,9,0,2],[2,3,9,0,3],[4,5,9,0,4]]
        self.assertEqual(priority_positions(layout,trees),[[2,3],[4,5]])
        self.assertEqual(priority_positions({},trees),[])


if __name__=='__main__': unittest.main()
