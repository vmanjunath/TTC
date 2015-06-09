import unittest
import ttc


class SimpleCaseTest(unittest.TestCase):

    def setUp(self):
        self.prefs = {
            'a0': [['o1', 'o2']],
            'a1': [['o0'], ['o2'], ['o1']],
            'a2': [['o0'], ['o1'], ['o2']]
        }
        self.ends = {a: ['o{}'.format(i)] for i, a in enumerate(self.prefs.keys())}
        self.priority = {a: i for i, a in enumerate(self.prefs.keys())}

    def test_simple_case(self):
        alloc = ttc.ttc(self.prefs, self.ends, self.priority)

        self.assertEqual(alloc['a0'], ['o2'])
        self.assertEqual(alloc['a1'], ['o0'])
        self.assertEqual(alloc['a2'], ['o1'])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.prefs = {'a1': [['o1', 'o2']], 'a2': [['o1'], ['o2']]}
        self.ends = {'a1': ['o1'], 'a2': ['o2']}
        self.priority = {a: i for i, a in enumerate(self.prefs.keys())}

    def test_returns_alloc(self):
        alloc = ttc.ttc(self.prefs, self.ends, self.priority)

        # Every agent gets an endowment
        self.assertEqual(alloc.keys(), self.ends.keys())

        # Every agent gets as many allocated as he was endowed with
        for a in self.ends.keys():
            self.assertEqual(len(alloc[a]), len(self.ends[a]))

        # for each pair of agents a and b, if o is allocated to a, it's not allocated to b
        for a in self.ends.keys():
            for b in self.ends.keys():
                if b != a:
                    for o in alloc[a]:
                        self.assertNotIn(o, alloc[b])

