# pylint: disable=missing-docstring,too-many-arguments,protected-access
import unittest
import ttc


def new_context(prefs=None, curr_ends=None, ends=None, curr_prefs=None, graph=None,
                persistence_test=None, unsat=None, alloc=None, reachable_unsat=None):
    return ttc.TTCContext(
        prefs=prefs or {},
        curr_ends=curr_ends or {},
        ends=ends or {},
        curr_prefs=curr_prefs or {},
        graph=graph or {},
        persistence_test=persistence_test or {},
        unsat=unsat or set({}),
        alloc=alloc or {},
        reachable_unsat=reachable_unsat or {}
    )


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
        self.ctx.curr_ends['a1'] = -1  # This could be the case if we've popped -1 previously.
                                       # This should remain
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
        self.assertEqual({'a1', 'a2'}, set(ctx.graph['a0']))
        self.assertEqual({'a0'}, set(ctx.graph['a1']))
        self.assertEqual({'a0'}, set(ctx.graph['a2']))
        self.assertEqual({'a3'}, set(ctx.graph['a3']))


class SinkAnalysisTest(unittest.TestCase):
    def test_get_sinks(self):
        graph = {
            'a': ['a'],
            'b': ['a'],
            'c': ['c', 'b']
        }
        expected_sinks = [['a']]
        sinks = ttc._get_sinks(graph)
        self.assertEqual(sinks, expected_sinks)

    def test_doesnt_find_terminal_sink_with_everyone_in_unsat(self):
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
            graph={'a': ['b'], 'b': ['a']},
            unsat={'a', 'b'}
        )
        self.assertFalse(ttc._remove_terminal_sinks(ctx))

    def test_finds_terminal_sink(self):
        ctx = new_context(
            prefs={
                'a': [[0, 1]],
                'b': [[0, 1]]
            },
            curr_ends={'a': 0, 'b': 1},
            ends={'a': [], 'b': []},
            curr_prefs={
                'a': [[0, 1]],
                'b': [[0, 1]]
            },
            graph={'a': ['a', 'b'], 'b': ['a', 'b']},
            unsat=set({})
        )

        self.assertTrue(ttc._remove_terminal_sinks(ctx))
        self.assertEqual(ctx.alloc['a'], [0])
        self.assertEqual(ctx.alloc['b'], [1])
        self.assertNotIn('a', ctx.graph)
        self.assertNotIn('a', ctx.curr_prefs)
        self.assertNotIn('a', ctx.curr_ends)

    def test_iterative_sink_removal(self):
        prefs = {
            'a{}'.format(i): [[x] for x in range(i+1)] for i in range(5)
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
        self.assertEqual(ctx.graph, {})
        self.assertEqual(ctx.unsat, set({}))

    def test_scrub_from_curr_prefs(self):
        curr_prefs = {'a1': [['a', 'b', 'c'], ['d'], ['f']]}
        ctx = new_context(curr_prefs=curr_prefs)
        ttc._scrub_from_curr_prefs(ctx, 'd')
        expected_curr_prefs = {'a1': [['a', 'b', 'c'], ['f']]}
        self.assertEqual(expected_curr_prefs, ctx.curr_prefs)


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
        self.assertIn('a', ctx.unsat)
        self.assertNotIn('b', ctx.unsat)


class SubgraphTest(unittest.TestCase):
    def setUp(self):
        self.ctx = new_context(
            graph={
                1: [1, 3],
                2: [4, 2, 1],
                3: [5, 3],
                4: [3],
                5: [1, 6],
                6: [2]
                },
            unsat={4, 5, 6},
            curr_ends=dict(zip(range(1, 7), 'abcdef')),
            reachable_unsat={
                1: 5,
                2: 4,
                3: 5,
                4: 5,
                5: 6,
                6: 4
            }
        )
        self.priority = dict(zip('abcdef', range(1, 7)))

    def test_subgraph_picks_single_edge_for_each_node(self):
        graph_selection = ttc._subgraph(self.ctx, self.priority)
        expected_subgraph = {
            1: 3,
            2: 4,
            3: 5,
            4: 3,
            5: 1,
            6: 2
        }
        self.assertEqual(graph_selection, expected_subgraph)

    def test_reverse_graph(self):
        reverse_graph = {
            1: {2, 5, 1},
            2: {2, 6},
            3: {1, 3, 4},
            4: {2},
            5: {3},
            6: {5}
        }
        self.assertEqual(reverse_graph, ttc._reverse_graph(self.ctx.graph))

    def test_unsat_select(self):
        agent_priority = lambda a: self.priority[self.ctx.curr_ends[a]]
        graph_selection = {}
        labeled = set({})
        ttc._unsat_select(graph_selection, labeled, self.ctx.unsat, self.ctx.graph, agent_priority)
        expected_graph_selection = {
            4: 3,
            5: 1,
            6: 2
        }
        self.assertEqual(graph_selection, expected_graph_selection)
        self.assertIn(4, labeled)

    def test_sat_select(self):
        agent_priority = lambda a: self.priority[self.ctx.curr_ends[a]]
        graph_selection = {
            4: 3,
            5: 1,
            6: 2
        }
        labeled = self.ctx.unsat.copy()
        ttc._sat_select(graph_selection, labeled, self.ctx.graph, agent_priority)
        expected_graph_selection = {
            1: 3,
            2: 4,
            3: 5,
            4: 3,
            5: 1,
            6: 2
        }
        self.assertEqual(graph_selection, expected_graph_selection)
        self.assertIn(1, labeled)

    def test_first_reachable_unsat(self):
        graph_selection = {
            1: 3,
            2: 4,
            3: 5,
            4: 3,
            5: 1,
            6: 2
        }
        ttc._first_reachable_unsat(graph_selection, self.ctx)
        expected_reachable_unsat = {
            1: 5,
            2: 4,
            3: 5,
            4: 5,
            5: 5,
            6: 4
        }
        self.assertEqual(self.ctx.reachable_unsat, expected_reachable_unsat)

    def test_persistence(self):
        graph_selection = {
            1: 3,
            2: 4,
            3: 5,
            4: 3,
            5: 1,
            6: 2
        }
        ttc._record_persistences(self.ctx, graph_selection)
        # change 5's endowment and there shouldn't be persistence for 1, 3, or 4
        self.ctx.curr_ends[5] = 'a'
        self.assertIsNone(self.ctx.persistence_test[1]())
        # leave 4's endowment alone so there should be persistence for 2 and 6
        self.assertEqual(self.ctx.persistence_test[2](), 4)

    def test_persistence_select(self):
        self.ctx.persistence_test[1] = lambda: 2
        self.ctx.persistence_test[2] = lambda: None
        labeled = set({})
        graph_selection = {}
        ttc._persistence_select(graph_selection, labeled, self.ctx.persistence_test)
        self.assertEqual(graph_selection[1], 2)
        self.assertNotIn(2, graph_selection)
        self.assertIn(1, labeled)
        self.assertNotIn(2, labeled)


class TradeTest(unittest.TestCase):
    def test_trade(self):
        ctx = new_context(
            curr_ends=dict(zip(range(1, 6), 'abcde'))
        )
        graph_selection = {
            1: 2,
            2: 3,
            3: 1,
            4: 5,
            5: 4,
        }
        ttc._trade(ctx, graph_selection)
        expected_curr_ends = {
            1: 'b',
            2: 'c',
            3: 'a',
            4: 'e',
            5: 'd'
        }
        self.assertEqual(expected_curr_ends, ctx.curr_ends)


class TTCTest(unittest.TestCase):
    def test_simple_case(self):
        prefs = {
            'a0': [['o1', 'o2']],
            'a1': [['o0'], ['o2'], ['o1']],
            'a2': [['o0'], ['o1'], ['o2']]
        }
        ends = {a: ['o{}'.format(i)] for i, a in enumerate(sorted(prefs.keys()))}
        priority = {'o{}'.format(i): i for i in range(len(prefs))}

        alloc = ttc.ttc(prefs, ends, priority)

        self.assertEqual(alloc['a0'], ['o2'])
        self.assertEqual(alloc['a1'], ['o0'])
        self.assertEqual(alloc['a2'], ['o1'])

    def test_returns_alloc(self):
        prefs = {'a1': [['o1', 'o2']], 'a2': [['o1'], ['o2']]}
        ends = {'a1': ['o1'], 'a2': ['o2']}
        priority = {'o1': 1, 'o2': 2}
        agents = {'a1', 'a2'}
        num_ends = {a: len(ends[a]) for a in agents}

        ends_keys = set(ends.keys())
        alloc = ttc.ttc(prefs, ends, priority)

        # Every agent gets an endowment
        self.assertEqual(set(alloc.keys()), ends_keys)

        # Every agent gets as many allocated as he was endowed with
        for agent in agents:
            self.assertEqual(len(alloc[agent]), num_ends[agent])

        # for each pair of agents, if endowment is allocated to agent_1,
        # it's not allocated to agent_2
        for agent_1 in agents:
            for agent_2 in agents:
                if agent_2 != agent_1:
                    for endowment in alloc[agent_1]:
                        self.assertNotIn(endowment, alloc[agent_2])

    def test_example_from_sethuraman_saban(self):
        """This is the example on page 21 of SS"""
        prefs = {
            1: [['a', 'c']],
            2: [['a', 'b', 'd']],
            3: [['c', 'e']],
            4: [['c']],
            5: [['a', 'f']],
            6: [['b']]
        }
        ends = {i: [o] for i, o in zip(range(1, 7), list('abcdef'))}
        priority = dict(zip(list('abcdef'), range(1, 7)))
        alloc = ttc.ttc(prefs, ends, priority)
        expected_alloc = {
            1: ['a'],
            2: ['d'],
            3: ['e'],
            4: ['c'],
            5: ['f'],
            6: ['b']
        }
        self.assertEqual(expected_alloc, alloc)

    def test_idempotence_sethuraman_saban(self):
        prefs = {
            1: [['a', 'c']],
            2: [['a', 'b', 'd']],
            3: [['c', 'e']],
            4: [['c']],
            5: [['a', 'f']],
            6: [['b']]
        }
        ends = {
            1: ['a'],
            2: ['d'],
            3: ['e'],
            4: ['c'],
            5: ['f'],
            6: ['b']
        }
        priority = dict(zip(list('abcdef'), range(1, 7)))
        expected_alloc = {
            1: ['a'],
            2: ['d'],
            3: ['e'],
            4: ['c'],
            5: ['f'],
            6: ['b']
        }
        alloc = ttc.ttc(prefs, ends, priority)
        self.assertEqual(expected_alloc, alloc)

    def test_example_from_jaramillo_manjunath(self):
        prefs = {
            1: [['a']],
            2: [['a'], ['b']],
            3: [['f']],
            4: [['c', 'd', 'e', 'f']],
            5: [['d', 'e', 'g']],
            6: [['d', 'e']],
            7: [['d'], ['g']],
            8: [['d', 'h', 'i']],
            9: [['c', 'i']],
            10: [['a', 'b', 'j']],
            11: [['e', 'i', 'k']]
        }
        ends = {a: [e] for a, e in dict(zip(range(1, 12), list('abcdefghijk'))).items()}
        priority = dict(zip(list('abcdefghijk'), range(1, 12)))

        alloc = ttc.ttc(prefs, ends, priority)
        expected_alloc = {
            1: ['a'],
            2: ['b'],
            3: ['f'],
            4: ['c'],
            5: ['g'],
            6: ['e'],
            7: ['d'],
            8: ['h'],
            9: ['i'],
            10: ['j'],
            11: ['k']
        }
        self.assertEqual(alloc, expected_alloc)

    def test_idempotence_jaramillo_manjunath(self):
        prefs = {
            1: [['a']],
            2: [['a'], ['b']],
            3: [['f']],
            4: [['c', 'd', 'e', 'f']],
            5: [['d', 'e', 'g']],
            6: [['d', 'e']],
            7: [['d'], ['g']],
            8: [['d', 'h', 'i']],
            9: [['c', 'i']],
            10: [['a', 'b', 'j']],
            11: [['e', 'i', 'k']]
        }
        priority = dict(zip(list('abcdefghijk'), range(1, 12)))
        ends = {
            1: ['a'],
            2: ['b'],
            3: ['f'],
            4: ['c'],
            5: ['g'],
            6: ['e'],
            7: ['d'],
            8: ['h'],
            9: ['i'],
            10: ['j'],
            11: ['k']
        }
        expected_alloc = {
            1: ['a'],
            2: ['b'],
            3: ['f'],
            4: ['c'],
            5: ['g'],
            6: ['e'],
            7: ['d'],
            8: ['h'],
            9: ['i'],
            10: ['j'],
            11: ['k']
        }
        alloc = ttc.ttc(prefs, ends, priority)
        self.assertEqual(alloc, expected_alloc)

    def test_unzu_molis_1(self):
        prefs = {
            'a1': [['h2'], ['h1']],
            'a2': [['h3'], ['h2']],
            'a3': [['h4', 'h5'], ['h3']],
            'a4': [['h1'], ['h5'], ['h4']],
            'a5': [['h6'], ['h2'], ['h4'], ['h5']],
            'a6': [['h6', 'h7']],
            'a7': [['h6'], ['h7']],
            'a8': [['h9', 'h5'], ['h8']],
            'a9': [['h9', 'h10']],
            'a10': [['h9', 'h10']]
        }
        priority = {'h{}'.format(i): i for i in range(1, 11)}
        ends = {'a{}'.format(i): ['h{}'.format(i)] for i in range(1, 11)}

        alloc = ttc.ttc(prefs, ends, priority)
        expected_alloc = {'a3': ['h5'], 'a8': ['h8'], 'a2': ['h3'],
                          'a4': ['h1'], 'a5': ['h4'], 'a7': ['h6'],
                          'a6': ['h7'], 'a1': ['h2'], 'a10': ['h10'], 'a9': ['h9']}

        self.assertEqual(alloc, expected_alloc)


class MultipleEndowmentTest(unittest.TestCase):
    def test_multiple_endowments(self):
        """ The way the algorithm has been generalized to handle multiple endowments, this case
        does not end up at an efficient allocation: 1 starts with endowment a, while 2 has c and
        3 has d. After 1 and 2 trade, 2 is removed along with a. Since b is not among the current
        endowments, 3 is subsequently removed and finally 1 is. This is a downside of the fact that
        1 cannot offer b to 3 before c is assigned to him permanently.

        If this becomes an issue, we can try to be more clever in when we remove agents.
        """
        prefs = {
            1: [['c', 'd'], ['a', 'b']],
            2: [['a', 'b'], ['c']],
            3: [['a', 'b'], ['d']]
        }
        ends = {
            1: ['a', 'b'],
            2: ['c'],
            3: ['d']
        }
        priority = dict(zip(list('abcd'), range(4)))

        alloc = ttc.ttc(prefs, ends, priority)

        # expect 1 and 2 to trade 'a' and 'c'
        self.assertEqual(2, len(alloc[1]))

        self.assertTrue('a' in alloc[2])

    def test_multiple_endowments_2(self):
        """
        The algorithm should still find trades for the second edowment in cases where other
        agents who offer possible trades for a second endowment are not removed like in
        @test_multiple_endowments
        """
        prefs = {
            1: [['c'], ['d'], ['a', 'b']],
            2: [['a']],
            3: [['a', 'b'], ['e']],  # Notice that e keeps 3 from being removed with 1 and 2
            4: [['d', 'e']]
        }
        ends = {
            1: ['a', 'b'],
            2: ['c'],
            3: ['d'],
            4: ['e']
        }
        priority = dict(zip(list('abcde'), range(5)))

        alloc = ttc.ttc(prefs, ends, priority)

        # Expect 1 and 2 to trade 'a' and 'c'
        # Then, 1 and 3 trade 'b' and 'd'
        self.assertEqual(2, len(alloc[1]))
        self.assertEqual(set(alloc[1]), {'c', 'd'})
        self.assertEqual(set(alloc[2]), {'a'})
        self.assertEqual(set(alloc[3]), {'b'})
        self.assertEqual(set(alloc[4]), {'e'})
