"""
This module extends the Highest Priority Object TTC algorithm as defined in Saban and
Sethuraman (http://bit.ly/1B9Hmvi) to allow multiple endowments.

TTC takes, as arguments, preferences, endowments, and priority.

Preferences are provided as a dict with agent as keys and list of lists of endowments as
values. Each element of the preference list is an indifference class. So [['a'], ['b','c'],['d']]
represents a preference where 'a' is best, 'b' and 'c' are next best (and indifferent), and 'd' is
worst.

Endowments are provided as a dict with agents as keys and lists of endowments as values.

Priority is a dict with endowments as keys numeric values.

TODO: provide a conflict checker to avoid clashing endowments being assigned to agent
"""
from collections import namedtuple
from functools import reduce
from tarjan import tarjan
from heap_set import HeapSet


__all__ = ['ttc']


""" Context passed to subroutines of TTC """
TTCContext = namedtuple(
    'TTCContext',
    [
        'prefs',  # Starts as input prefs, but elements popped as agents trades
        'ends',  # Starts as input ends, but elements popped as agents trade
        'curr_ends',  # Single endowment for current round
        'curr_prefs',  # Preferences over endowments for current round
        'graph',  # TTC graph for current round
        'persistence_test',  # A function that returns a boolean for each agent to determine
                             # persistence.
        'unsat',  # Set of unsatisfied agents in current round
        'alloc',  # The final allocation
        'reachable_unsat'  # First reachable unsatisfied agent
    ]
    )


def ttc(prefs, ends, priority):
    """
    :param prefs: dict with agents as keys and lists of lists of endowments as values
    Example:
    {
    'agent 1': [['endowment 1'], ['endowment 2', 'endowment 3'], ['endowment 4']],
    'agent 2': [['endowment 3'], ['endowment 1']],
    'agent 3': [['endowment 3', 'endowment 1', 'endowment 2']]
    }

    :param ends: dict with agents as keys and lists of endowments as values
    Example:
    {
    'agent 1': ['endowment 1', 'endowment 2'],
    'agent 2': ['endowment 3', 'endowment 4', 'endowment 15'],
    'agent 3': ['endowment 8']
    }
    NB. No endowment should appear in the list of more than one agent.
    :param priority: dict with endowments as keys and numerical values
     {'endowment 1': 3, 'endowment 3': 5, 'endowment 2': 3.4, ... }
     NB. Each value in ends has to be a key in priority
    :return: a dict with agents as keys and lists of endowments as values
    Example:
    {
    'agent 1': ['endowment 8', 'endowment 4'],
    'agent 2': ['endowment 1', 'endowment 3', 'endowment 2'],
    'agent 3': ['endowment 15']
    }
    This will be computed according to an adaptation of the HPO TTC algorithm. The change
    from Saban and Sethuraman is an adaptation to allow multiple endowments.

    Each agent is allocated exactly as many items as he is endowed with. We modify the
    HPO TTC algorithm by having agents trade their endowments one at a time. So in the
    above listed example for ends, we would start with a single endowment input where
    agent 1 starts with endowment 1, agent 2 starts with endowment 3, and agent 3 starts
    with endowment 8.

    TO DO: add a fourth parameter conflict which is a boolean valued function that takes
    two endowments as input and returns True only when the two endowments are incompatible
    (i.e. no agent can be assigned both of endowments). We could easily make this function
    take a third argument to make it agent specific.
    """
    ctx = TTCContext(
        prefs=prefs,
        ends=ends,
        curr_ends={},
        curr_prefs={},
        graph={},
        persistence_test={},
        unsat=set({}),
        alloc={},
        reachable_unsat={}
    )
    while ctx.prefs:
        _update_ends(ctx)
        _get_curr_prefs(ctx)

        _build_ttc_graph(ctx)

        _iteratively_remove_sinks(ctx)

        graph_selection = _subgraph(ctx, priority)

        _first_reachable_unsat(graph_selection, ctx)

        _record_persistences(ctx, graph_selection)

        _trade(ctx, graph_selection)

    return ctx.alloc


def _update_ends(ctx):
    """
    For each agent with an endowment in ctx.ends but not in ctx.curr_ends, pop the first element of
    his ctx.ends. If there isn't anything there, you need to do some housekeeping: delete him from
    ctx.prefs, ctx.ends, and ctx.persistence_test
    """
    to_delete = []
    for agent in ctx.ends:
        if agent not in ctx.curr_ends:
            try:
                endowment = ctx.ends[agent].pop(0)
                ctx.curr_ends[agent] = endowment
            except IndexError:
                to_delete.append(agent)

    for agent in to_delete:
        del ctx.ends[agent]
        del ctx.prefs[agent]
        if ctx.persistence_test:
            del ctx.persistence_test[agent]


def _get_curr_agent_prefs(pref, end_set):
    """
    Takes a single agents preferences and the set of available endowments and returns a
    'cleaned up' version of the input preference by filtering out any endowment that isn't
    in end_set
    TODO: filter out objects that conflict with other endowments or allocs from preferences
    """
    clean_pref = []
    for indifference_class in pref:
        clean_indifference_class = [endowment for endowment in indifference_class
                                    if endowment in end_set]
        if clean_indifference_class:
            clean_pref.append(clean_indifference_class)

    return clean_pref


def _get_curr_prefs(ctx):
    """
    Return the restriction of each agent's preference to curr_ends.
    """
    # all possible endowments
    end_set = reduce(lambda x, y: x.union({y}), ctx.curr_ends.values(), set({}))
    for agent, pref in ctx.prefs.items():
        ctx.curr_prefs[agent] = _get_curr_agent_prefs(pref, end_set)


def _build_ttc_graph(ctx):
    """
    Given a context that specifies current endowments and preferences, clears the current graph
    and replaces it with a graph with an edge from every agent to every agent who owns one of his
    most preferred objects.
    """
    # need reverse relationship between endowments and agents
    reverse_ends = {end: a for a, end in ctx.curr_ends.items()}

    ctx.graph.clear()

    for agent, pref in ctx.curr_prefs.items():
        ctx.graph[agent] = [reverse_ends[endowment] for endowment in pref[0]]


def _add_to_unsat(agent, ctx):
    """ Add agent to unsatisfied set if he's not satisfied """
    if ctx.curr_ends[agent] not in ctx.curr_prefs[agent][0]:
        ctx.unsat.add(agent)


def _collect_unsatisfied(ctx):
    """ Clear and repopulate the current unsatisfied set """
    ctx.unsat.clear()
    for agent in ctx.curr_ends:
        _add_to_unsat(agent, ctx)


def _is_sink(scc, graph):
    """ Given a subset of vertices in graph returns True if there are no edges out of scc"""
    for vertex in scc:
        for neighbor in graph[vertex]:
            if neighbor not in scc:
                return False
    return True

def _get_sinks(graph):
    """ Run Tarjan's algorithm to find all strongly connected components of graph """
    sccs = tarjan(graph)
    sinks = [scc for scc in sccs if _is_sink(scc, graph)]
    # TODO: figure out if it's ever reasonable for sinks to be empty.

    return sinks


def _is_terminal(sink, ctx):
    """ A sink is terminal if no vertex in it is an unsatisfied agent """
    return reduce(lambda x, a: x and a not in ctx.unsat, sink, True)


def _scrub_from_curr_prefs(ctx, endowment):
    """ remove all occurrences of endowment from the current preferences """
    for pref in ctx.curr_prefs.values():
        blank_indifference_class = False
        for indifference_class in pref:
            if endowment in indifference_class:
                indifference_class.remove(endowment)
                if not indifference_class:
                    blank_indifference_class = True
                break
        if blank_indifference_class:
            pref.remove([])


def _remove_terminal_sinks(ctx):
    """
    Use Tarjan's strongly connected component algorithm to find all sinks.
    If a sink is terminal remove it.
    Continue until there are no more terminal sinks
    :returns True if a terminal sink was removed
    """
    found_terminal_sink = False

    sinks = _get_sinks(ctx.graph)

    for sink in sinks:
        if _is_terminal(sink, ctx):
            found_terminal_sink = True
            for agent in sink:
                #  make assignment:
                #  remove curr_pref[agent], G[agent], curr_end[agent]
                #  add alloc[agent]
                #  NB. _update_ends() takes care of ends[agent] and prefs[agent] so
                #  don't worry about it here
                alloc = ctx.curr_ends[agent]
                if agent in ctx.alloc:
                    ctx.alloc[agent].append(alloc)
                else:
                    ctx.alloc[agent] = [alloc]
                del ctx.curr_ends[agent]  # remove it from the problem
                del ctx.graph[agent]
                del ctx.curr_prefs[agent]
                # Now you have to remove alloc from everyone else's curre_prefs
                _scrub_from_curr_prefs(ctx, alloc)

    return found_terminal_sink


def _update_ctx_and_build_graph(ctx):
    """Clean up endowments (pop them) and preferences, build TTC graph, and update
    the unsatisfied set"""
    _update_ends(ctx)
    _get_curr_prefs(ctx)
    _build_ttc_graph(ctx)
    _collect_unsatisfied(ctx)


def _iteratively_remove_sinks(ctx):
    """Remove terminal sinks and update the context until there are none left"""
    _update_ctx_and_build_graph(ctx)
    while _remove_terminal_sinks(ctx):
        _update_ctx_and_build_graph(ctx)


def _subgraph(ctx, priority):
    """ Selects a subgraph of ctx.graph so that every vertex has exactly one out edge.
     This subgraph is calculated according to the HPO TTC described by Saban and Sethuraman"""
    agent_priority = _agent_priority(ctx, priority)
    graph_selection = {}
    labeled = set({})
    if ctx.persistence_test:
        _persistence_select(graph_selection, labeled, ctx.persistence_test)
    _unsat_select(graph_selection, labeled, ctx.unsat, ctx.graph, agent_priority)
    _sat_select(graph_selection, labeled, ctx.graph, agent_priority)
    return graph_selection


def _agent_priority(ctx, priority):
    """Given a priority over endowments, returns a function that takes an agent and returns
    the priority of his current endowment."""
    return lambda a: priority[ctx.curr_ends[a]]


def _reverse_graph(graph):
    """ Given a directed graph, returns a new graph with the edges reversed """
    reverse_graph = {v: set({}) for v in graph}
    for vertex, neighbors in graph.items():
        for neighbor in neighbors:
            reverse_graph[neighbor].add(vertex)
    return reverse_graph


def _unsat_select(graph_selection, labeled, unsat_set, graph, agent_priority):
    """
    updates graph_selection for members of unsat so that there's an edge to each member's
    highest priority neighbor in graph.
    agent_priority is a function mapping agents to their endowment's priority
    """
    for unsat in unsat_set:
        graph_selection[unsat] = min(graph[unsat], key=agent_priority)
        labeled.add(unsat)


def _persistence_select(graph_selection, labeled, persistence_test):
    """
    For each vertex where persistence_test returns a vertex (not None), set the edge
    in graph_selection from that vertex to this return value. Also mark that vertex as
    labeled.
    """
    for vertex in persistence_test:
        persist = persistence_test[vertex]()
        if persist:
            graph_selection[vertex] = persist
            labeled.add(vertex)


def _sat_select(graph_selection, labeled, graph, agent_priority):
    """
    Keep sets of labeled (who have an out edge in F) and unlabeled vertices of F. Label each
    vertex by labeling unlabeled vertices that are adjacent to labeled vertices.
    """
    unlabeled = set(graph.keys()).difference(labeled)
    adjacent_to_labeled = HeapSet(agent_priority)  # Adjacent to labeled
    reverse_graph = _reverse_graph(graph)
    while unlabeled:
        _collect_adjacent_to_labeled(adjacent_to_labeled, reverse_graph, labeled)
        vertex = adjacent_to_labeled.pop()
        labeled_adjacent_to_a = [neighbor for neighbor in graph[vertex] if neighbor in labeled]
        graph_selection[vertex] = min(labeled_adjacent_to_a, key=agent_priority)
        labeled.add(vertex)
        unlabeled.remove(vertex)


def _collect_adjacent_to_labeled(adjacent_to_labeled, reverse_graph, labeled):
    """ Given a HeapSet of vertices that are adjacent to vetices in labeled,
    and reverse_graph (a mapping from each vertex to the vertices that have edges to it)
    update adjacent_to_labeled by adding all vertices that have a neighbor in labeled
    """
    for vertex in labeled:
        for reverse_neighbor in reverse_graph[vertex]:
            if reverse_neighbor not in labeled:
                adjacent_to_labeled.add(reverse_neighbor)


def _first_reachable_unsat(graph_selection, ctx):
    """ Given a context and a graph selection, update the context's reachable_unsat to map each
    agent to his first reachable unsatisfied agent."""
    ctx.reachable_unsat.clear()
    verts = set(graph_selection.keys())
    while verts:
        curr_vert = verts.pop()
        path = [curr_vert]
        curr_vert = graph_selection[curr_vert]
        while curr_vert not in ctx.unsat and curr_vert not in ctx.reachable_unsat:
            path.append(curr_vert)
            curr_vert = graph_selection[curr_vert]
        for vert in path:
            if curr_vert in ctx.unsat:
                ctx.reachable_unsat[vert] = curr_vert
            else:
                ctx.reachable_unsat[vert] = ctx.reachable_unsat[curr_vert]
            if vert in verts:
                verts.remove(vert)
    return ctx.reachable_unsat


def _record_persistences(ctx, graph_selection):
    """Given a context and a graph selection, for each vertex, set ctx.persistence_test to a
    function that either returns the first unsatisfied agent reachable from that vertex _if_ that
    agent is still unsatisfied and None otherwise.
    """
    ctx.persistence_test.clear()
    for vertex in ctx.reachable_unsat.keys():
        ctx.persistence_test[vertex] = _persistence(ctx, graph_selection, vertex,
                                                    ctx.curr_ends[ctx.reachable_unsat[vertex]])


def _persistence(ctx, graph_selection, vertex, end):
    """
    returns a function that returns graph_selection[vertex] _if_ the first  unsatisfied agent
    reachable from vertex holds the same endowment as he currently does. The function returns
    None otherwise.
    """
    return lambda: graph_selection[vertex] if ctx.reachable_unsat[vertex]in ctx.curr_ends\
        and ctx.curr_ends[ctx.reachable_unsat[vertex]] == end else None


def _trade(ctx, graph_selection):
    """
    Find cycles in F efficiently using Tarjan's algorithm.
    """
    # tarjan takes a dict with list values
    tarjan_graph = {vert: [neighbor] for vert, neighbor in graph_selection.items()}
    cycles = tarjan(tarjan_graph)

    for cycle in cycles:
        last_end = ctx.curr_ends[cycle[-1]]
        if len(cycle) > 1:
            # Tarjan finds SCCs. With out degree of 1 for every vertex, if len(cycle) == 1,
            # it's not a cycle
            for vert, pred in reversed(list(zip(cycle[1:], cycle[:-1]))):
                ctx.curr_ends[vert] = ctx.curr_ends[pred]
            ctx.curr_ends[cycle[0]] = last_end
