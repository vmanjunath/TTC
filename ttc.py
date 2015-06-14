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
        'G',  # TTC graph for current round
        'persistence_test',  # A function that returns a boolean for each agent to determine
                             # persistence.
        'U',  # Set of unsatisfied agents in current round
        'alloc',  # The final allocation
        'X'  # First reachable unsatisfied agent
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
        G={},
        persistence_test={},
        U=set({}),
        alloc={},
        X={}
    )
    while ctx.prefs:
        _update_ends(ctx)
        _get_curr_prefs(ctx)

        _build_ttc_graph(ctx)

        _iteratively_remove_sinks(ctx)

        F = _subgraph(ctx, priority)

        _record_persistences(ctx, F)

        _trade(ctx, F)

    return ctx.alloc



def _update_ends(ctx):
    """
    For each agent with an endowment in ctx.ends but not in ctx.curr_ends, pop the first element of
    his ctx.ends. If there isn't anything there, you need to do some housekeeping: delete him from
    ctx.prefs, delete him from ctx.ends
    """
    to_delete = []
    for a in ctx.ends:
        if a not in ctx.curr_ends:
            try:
                endowment = ctx.ends[a].pop(0)
                ctx.curr_ends[a] = endowment
            except IndexError:
                to_delete.append(a)

    for a in to_delete:
        del ctx.ends[a]
        del ctx.prefs[a]


def _get_curr_agent_prefs(pref, end_set):
    # TODO: filter out objects that conflict with other endowments or allocs from preferences
    clean_pref = []
    for ic in pref:
        clean_ic = list(filter(lambda x: x in end_set, ic))
        if clean_ic:
            clean_pref.append(ic)

    return clean_pref


def _get_curr_prefs(ctx):
    """
    Return the restriction of each agent's preference to curr_ends.
    """
    # all possible endowments
    end_set = reduce(lambda x, y: x.union({y}), ctx.curr_ends.values(), set({}))
    for a, p in ctx.prefs.items():
        ctx.curr_prefs[a] = _get_curr_agent_prefs(p, end_set)


def _build_ttc_graph(ctx):
    # need reverse relationship between endowments and agents
    reverse_ends = {end: a for a, end in ctx.curr_ends.items()}

    ctx.G.clear()

    for a, p in ctx.curr_prefs.items():
        ctx.G[a] = list(map(lambda e: reverse_ends[e], p[0]))


def _add_to_U(a, ctx):
    # Add a to unsatisfied set if he's not satisfied
    if ctx.curr_ends[a] not in ctx.curr_prefs[a][0]:
        ctx.U.add(a)


def _collect_unsatisfied(ctx):
    ctx.U.clear()
    for a in ctx.curr_ends:
        _add_to_U(a, ctx)


def _is_sink(scc, G):
    for v in scc:
        for w in G[v]:
            if w not in scc:
                return False
    return True


def _get_sinks(G):
    sccs = tarjan(G)
    return list(filter(lambda scc: _is_sink(scc, G), sccs))


def _is_terminal(sink, ctx):
    return reduce(lambda x, a: x and a not in ctx.U, sink, True)


def _scrub_from_curr_prefs(ctx, alloc):
    for a, p in ctx.curr_prefs.items():
        blank_ic = False
        for ic in p:
            if alloc in ic:
                ic.remove(alloc)
                if not ic:
                    blank_ic = True
                break
        if blank_ic:
            p.remove([])



def _remove_terminal_sinks(ctx):
    """
    Use Tarjan's strongly connected component algorithm to find all sinks.
    If a sink is terminal remove it.
    Continue until there are no more terminal sinks
    :returns True if a terminal sink was removed
    """
    found_terminal_sink = False

    sinks = _get_sinks(ctx.G)

    for sink in sinks:
        if _is_terminal(sink, ctx):
            found_terminal_sink = True
            for a in sink:
                #  make assignment:
                #  remove curr_pref[a], G[a], curr_end[a]
                #  add alloc[a]
                #  NB. _update_ends() takes care of ends[a] and prefs[a] so don't worry about
                #  it here
                alloc = ctx.curr_ends[a]
                if a in ctx.alloc:
                    ctx.alloc[a].append(alloc)
                else:
                    ctx.alloc[a] = [alloc]
                del ctx.curr_ends[a]  # remove it from the problem
                del ctx.G[a]
                del ctx.curr_prefs[a]
                # Now you have to remove alloc from everyone else's curre_prefs
                _scrub_from_curr_prefs(ctx, alloc)

    return found_terminal_sink


def _update_context_and_clear_cycles(ctx):  # rename this to _update_context_and_build_graph
    _update_ends(ctx)
    _get_curr_prefs(ctx)
    _build_ttc_graph(ctx)
    _collect_unsatisfied(ctx)


def _iteratively_remove_sinks(ctx):
    _update_context_and_clear_cycles(ctx)
    while _remove_terminal_sinks(ctx):
        _update_context_and_clear_cycles(ctx)


def _subgraph(ctx, priority):
    agent_priority = _agent_priority(ctx, priority)
    F = {}
    L = set({})
    if ctx.persistence_test:
        _persistence_select(F, L, ctx.persistence_test)
    _U_select(F, L, ctx.U, ctx.G, agent_priority)
    _sat_select(F, L, ctx.G, agent_priority)
    return F


def _agent_priority(ctx, priority):
    return lambda a: priority[ctx.curr_ends[a]]


def _reverse_graph(G):
    reverse_G = {v: set({}) for v in G}
    for v, ws in G.items():
        for w in ws:
            reverse_G[w].add(v)
    return reverse_G


def _U_select(F, L, U, G, agent_priority):
    """
    updates F for members of U so that there's an edge to each member's highest priority neighbor
    in G agent_priority is a function mapping agents to their endowment's priority
    """
    for u in U:
        F[u] = min(G[u], key=agent_priority)
        L.add(u)


def _persistence_select(F, L, persistence_test):
    for a in persistence_test:
        persist = persistence_test[a]()
        if persist:
            F[a] = persist
            L.add(a)


def _sat_select(F, L, G, agent_priority):
    """
    Keep sets of labeled (who have an out edge in F) and unlabeled vertices of F. Label each
    vertex by labeling unlabeled vertices that are adjacent to labeled vertices.
    """
    UL = set(G.keys()).difference(L)
    AL = HeapSet(agent_priority)  # Adjacent to labeled
    reverse_G = _reverse_graph(G)
    while UL:
        _collect_adjacent_to_labeled(AL, reverse_G, L)
        a = AL.pop()
        labeled_adjacent_to_a = filter(lambda adj_to_a: adj_to_a in L, G[a])
        F[a] = min(labeled_adjacent_to_a, key=agent_priority)
        L.add(a)
        UL.remove(a)


def _collect_adjacent_to_labeled(AL, reverse_G, L):
    for labeled in L:
        for a in reverse_G[labeled]:
            if a not in L:
                AL.add(a)


def _first_reachable_U(F, ctx):
    ctx.X.clear()
    verts = set(F.keys())
    while verts:
        curr_vert = verts.pop()
        path = [curr_vert]
        curr_vert = F[curr_vert]
        while curr_vert not in ctx.U and curr_vert not in ctx.X:
            path.append(curr_vert)
            curr_vert = F[curr_vert]
            assert curr_vert not in path  # If this fails, we're going in circles and shouldn't be.
        for vert in path:
            if curr_vert in ctx.U:
                ctx.X[vert] = curr_vert
            else:
                ctx.X[vert] = ctx.X[curr_vert]
            if vert in verts:
                verts.remove(vert)
    return ctx.X


def _record_persistences(ctx, F):
    for a in ctx.X.keys():
        ctx.persistence_test[a] = _persistence(ctx, F, a, ctx.curr_ends[ctx.X[a]])


def _persistence(ctx, F, a, end):
    """
    Returns a function that returns F[a] if the first reachable unsatisfied agent in F still
    holds end
    """
    return lambda: F[a] if ctx.curr_ends[ctx.X[a]] == end else None


def _trade(ctx, F):
    """
    Find cycles in F efficiently using Tarjan's algorithm.
    """
    # tarjan takes a dict with list values
    tarjan_F = {a: [e] for a, e in F.items()}
    cycles = tarjan(tarjan_F)

    for cycle in cycles:
        last_end = ctx.curr_ends[cycle[-1]]
        if len(cycle) > 1:
            # Tarjan finds SCCs. With out degree of 1 for every vertex, if len(cycle) == 1,
            # it's not a cycle
            for a, b in reversed(list(zip(cycle[1:], cycle[:-1]))):
                ctx.curr_ends[a] = ctx.curr_ends[b]
            ctx.curr_ends[cycle[0]] = last_end
