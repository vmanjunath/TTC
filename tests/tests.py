import unittest
import ttc


def new_context(prefs=None, curr_ends=None, ends=None, curr_prefs=None, G=None,
                persistence_test=None, U=set({}), alloc=None, X=None):
    return ttc.TTCContext(
        prefs=prefs or {},
        curr_ends=curr_ends or {},
        ends=ends or {},
        curr_prefs=curr_prefs or {},
        G=G or {},
        persistence_test=persistence_test or {},
        U=U,
        alloc=alloc or {},
        X=X or {}
    )


class SimpleCaseTest(unittest.TestCase):

    def setUp(self):
        self.prefs = {
            'a0': [['o1', 'o2']],
            'a1': [['o0'], ['o2'], ['o1']],
            'a2': [['o0'], ['o1'], ['o2']]
        }
        self.ends = {a: ['o{}'.format(i)] for i, a in enumerate(sorted(self.prefs.keys()))}
        self.priority = {'o{}'.format(i): i for i in range(len(self.prefs))}

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
                'a1': 0,
                'a2': 1
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

    def test_iterative_sink_removal(self):
        prefs = {
            'a{}'.format(i): list(map(lambda x: [x], range(i+1))) for i in range(5)
        }
        ends = {'a{}'.format(i): [i] for i in range(5)}
        ctx = new_context(
            prefs=prefs,
            ends=ends
        )
        ttc._iteratively_remove_sinks(ctx)
        self.assertEqual(ctx.alloc['a0'], [0])
        self.assertEqual(ctx.alloc['a4'], [4])

        self.assertEqual(ctx.prefs, {})
        self.assertEqual(ctx.curr_prefs, {})
        self.assertEqual(ctx.ends, {})
        self.assertEqual(ctx.curr_ends, {})
        self.assertEqual(ctx.G, {})
        self.assertEqual(ctx.U, set({}))


class UnsatisfiedTest(unittest.TestCase):
    def test_computes_unsatisfied(self):
        ctx = new_context(
            curr_ends={'a': 0, 'b': 1},
            curr_prefs={
                'a': [[1], [0]],
                'b': [[1], [0]]
                },
            )
        ttc._collect_unsatisfied(ctx)
        self.assertIn('a', ctx.U)
        self.assertNotIn('b', ctx.U)


class SubgraphTest(unittest.TestCase):
    def setUp(self):
        self.ctx = new_context(
            G={
                1: [1, 3],
                2: [4, 2, 1],
                3: [5, 3],
                4: [3],
                5: [1, 6],
                6: [2]
                },
            U={4, 5, 6},
            curr_ends=dict(zip(range(1, 7), 'abcdef')),
            )
        self.priority = dict(zip('abcdef', range(1, 7)))

    def test_subgraph_picks_single_edge_for_each_node(self):
        F = ttc._subgraph(self.ctx, self.priority)
        expected_subgraph = {
            1: 3,
            2: 4,
            3: 5,
            4: 3,
            5: 1,
            6: 2
        }
        self.assertEqual(F, expected_subgraph)

    def test_reverse_graph(self):
        reverse_G = {
            1: {2, 5, 1},
            2: {2, 6},
            3: {1, 3, 4},
            4: {2},
            5: {3},
            6: {5}
        }
        self.assertEqual(reverse_G, ttc._reverse_graph(self.ctx.G))

    def test_U_select(self):
        agent_priority = lambda a: self.priority[self.ctx.curr_ends[a]]
        F = {}
        ttc._U_select(F, self.ctx.U, self.ctx.G, agent_priority)
        expected_F = {
            4: 3,
            5: 1,
            6: 2
        }
        self.assertEqual(F, expected_F)

    def test_sat_select(self):
        agent_priority = lambda a: self.priority[self.ctx.curr_ends[a]]
        F = {
            4: 3,
            5: 1,
            6: 2
        }
        ttc._sat_select(F, self.ctx.U, self.ctx.G, agent_priority)
        expected_F = {
            1: 3,
            2: 4,
            3: 5,
            4: 3,
            5: 1,
            6: 2
        }
        self.assertEqual(F, expected_F)
