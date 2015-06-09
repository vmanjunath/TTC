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

    @unittest.skip
    def test_simple_case(self):
        alloc = ttc.ttc(self.prefs, self.ends, self.priority)

        self.assertEqual(alloc['a0'], ['o2'])
        self.assertEqual(alloc['a1'], ['o0'])
        self.assertEqual(alloc['a2'], ['o1'])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.prefs = {'a1': [['o1', 'o2']], 'a2': [['o1'], ['o2']]}
        self.ends = {'a1': ['o1'], 'a2': ['o2']}
        self.priority = {a: i for i, a in enumerate(self.prefs.keys())}

    def test_returns_alloc(self):
        alloc = ttc.ttc(self.prefs, self.ends, self.priority)

        # Every agent gets an endowment
        self.assertEqual(alloc.keys(), self.ends.keys())

        # Every agent gets as many allocated as he was endowed with
        for a in self.ends:
            self.assertEqual(len(alloc[a]), len(self.ends[a]))

        # for each pair of agents a and b, if o is allocated to a, it's not allocated to b
        for a in self.ends:
            for b in self.ends:
                if b != a:
                    for o in alloc[a]:
                        self.assertNotIn(o, alloc[b])


class UpdateEndsTest(unittest.TestCase):
    def setUp(self):
        self.ctx = ttc.TTCContext(
            prefs={'a1': [], 'a2': [], 'a3': []},
            ends={
                'a1': list(range(4)),
                'a2': list(range(5, 6)),
                'a3': []
            },
            curr_ends={},
            curr_prefs={},
            G={},
            persistence_test={},
            U=set({})
        )

    def test_update_ends_picks_one_endowment_per_agent(self):
        ttc._update_ends(self.ctx)
        self.assertEqual(self.ctx.curr_ends['a1'], 0)
        self.assertEqual(self.ctx.curr_ends['a2'], 5)
        self.assertNotIn('a3', self.ctx.curr_ends)

    def test_update_ends_deletes_empties(self):
        ttc._update_ends(self.ctx)
        self.assertNotIn('a3', self.ctx.prefs)
        self.assertNotIn('a3', self.ctx.ends)


class GetCurrPrefsTest(unittest.TestCase):
    def setUp(self):
        self.ctx = ttc.TTCContext(
            prefs={'a1': [[2, 4], [1]], 'a2': [[0, 3], [5]]},
            ends={
                'a1': [0, 3, 5],
                'a2': [1, 2, 4]
            },
            curr_ends={
                'a1': [0],
                'a2': [1]
            },
            curr_prefs={},
            G={},
            persistence_test={},
            U=set({})
        )

    def test_get_curr_prefs_omits_non_curr_ends(self):
        ttc._get_curr_prefs(self.ctx)

        self.assertNotIn(2, self.ctx.curr_prefs['a1'][0])

    def test_get_curr_prefs_includes_curr_ends(self):
        ttc._get_curr_prefs(self.ctx)

        self.assertIn(1, self.ctx.curr_prefs['a1'][0])


class BuildGraphTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_build_ttc_graph(self):
        pass





