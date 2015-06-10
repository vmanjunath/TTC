import unittest
import ttc


class SimpleCaseTest(unittest.TestCase):

    def setUp(self):
        self.prefs = {
            'a0': [['o1', 'o2']],
            'a1': [['o0'], ['o2'], ['o1']],
            'a2': [['o0'], ['o1'], ['o2']]
        }
        self.ends = {a: ['o{}'.format(i)] for i, a in enumerate(sorted(self.prefs.keys()))}
        self.priority = {a: i for i, a in enumerate(sorted(self.prefs.keys()))}

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
        self.priority = {a: i for i, a in enumerate(sorted(self.prefs.keys()))}

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
        self.ctx = new_context(
            prefs={'a1': [], 'a2': [], 'a3': []},
            ends={
                'a1': list(range(4)),
                'a2': list(range(5, 6)),
                'a3': []
            },
        )

    def test_update_ends_doesnt_touch_existing_endowments(self):
        self.ctx.curr_ends['a1'] = -1  # This could be the case if we've popped -1 previously. This should remain
        ttc._update_ends(self.ctx)
        self.assertEqual(self.ctx.curr_ends['a1'], -1)

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
        self.ctx = new_context(
            prefs={'a1': [[2, 4], [1]], 'a2': [[0, 3], [5]]},
            ends={
                'a1': [0, 3, 5],
                'a2': [1, 2, 4]
            },
            curr_ends={
                'a1': [0],
                'a2': [1]
            },
        )

    def test_get_curr_prefs_omits_non_curr_ends(self):
        ttc._get_curr_prefs(self.ctx)

        self.assertNotIn(2, self.ctx.curr_prefs['a1'][0])

    def test_get_curr_prefs_includes_curr_ends(self):
        ttc._get_curr_prefs(self.ctx)

        self.assertIn(1, self.ctx.curr_prefs['a1'][0])


class BuildGraphTest(unittest.TestCase):
    def test_build_ttc_graph(self):
        prefs = {
            'a0': [['o1', 'o2']],
            'a1': [['o0'], ['o2'], ['o1']],
            'a2': [['o0'], ['o1'], ['o2']],
            'a3': [['o3']]
        }
        curr_ends = {a: 'o{}'.format(i) for i, a in enumerate(sorted(prefs.keys()))}
        ctx = new_context(curr_prefs=prefs, curr_ends=curr_ends)

        ttc._build_ttc_graph(ctx)
        self.assertEqual({'a1', 'a2'}, set(ctx.G['a0']))
        self.assertEqual({'a0'}, set(ctx.G['a1']))
        self.assertEqual({'a0'}, set(ctx.G['a2']))
        self.assertEqual({'a3'}, set(ctx.G['a3']))


class SinkAnalysisTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_finds_terminal_sink(self):
        ctx = new_context(
            prefs={
                'a': [[1]],
                'b': [[0]]
            },
            curr_ends={'a': 0, 'b': 1},
            ends={'a': [], 'b': []},
            curr_prefs={
                'a': [[1]],
                'b': [[0]]
            },
            G={'a': ['b'], 'b': ['a']}
        )

        self.assertTrue(ttc._remove_terminal_sinks(ctx))
        self.assertEqual(ctx.alloc['a'], [1])
        self.assertEqual(ctx.alloc['b'], [0])
        self.assertNotIn('a', ctx.G)
        self.assertNotIn('a', ctx.curr_prefs)
        self.assertNotIn('a', ctx.curr_ends)


class UnsatisfiedTest(unittest.TestCase):
    def test_computes_unsatisfied(self):
        ctx = new_context(
            curr_ends={'a': 0, 'b': 1},
            curr_prefs={
                'a': [[1], [0]],
                'b': [[1], [0]]
                },
            )
        ttc._unsatisfied(ctx)
        self.assertIn('a', ctx.U)
        self.assertNotIn('b', ctx.U)


def new_context(prefs=None, curr_ends=None, ends=None, curr_prefs=None, G=None,
                persistence_test=None, U=set({}), alloc=None):
    return ttc.TTCContext(
        prefs=prefs or {},
        curr_ends=curr_ends or {},
        ends=ends or {},
        curr_prefs=curr_prefs or {},
        G=G or {},
        persistence_test=persistence_test or {},
        U=U,
        alloc=alloc or {}
    )