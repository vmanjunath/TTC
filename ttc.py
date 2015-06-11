from collections import namedtuple
from functools import reduce
from tarjan import tarjan
from fibonacci_heap_mod import Fibonacci_heap

TTCContext = namedtuple('TTCContext', ['prefs',  # Starts as input prefs, but elements popped as agents trades
                                       'ends',  # Starts as input ends, but elements popped as agents trade
                                       'curr_ends',  # Single endowment for current round
                                       'curr_prefs',  # Preferences over endowments for current round
                                       'G',  # TTC graph for current round
                                       'persistence_test',  # A function that returns a boolean for each agent to
                                                            # determine persistence.
                                       'U',  # Set of unsatisfied agents in current round
                                       'alloc',  # The final allocation
                                       'X'  # First reachable unsatisfied agent
                                       ])


def ttc(prefs, ends, priority):
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
    return ends


def _update_ends(ctx):
    """
    For each agent with an endowment in ctx.ends but not in ctx.curr_ends, pop the first element of his ctx.ends.
    If there isn't anything there, you need to do some housekeeping: delete him from ctx.prefs, delete him from ctx.ends
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
    end_set = reduce(lambda x, y: x.union({y}), ctx.curr_ends.values(), set({}))  # all possible endowments
    for a, p in ctx.prefs.items():
        ctx.curr_prefs[a] = _get_curr_agent_prefs(p, end_set)


def _build_ttc_graph(ctx):
    # need reverse relationship between endowments and agents
    reverse_ends = {end: a for a, end in ctx.curr_ends.items()}

    ctx.G.clear()

    for a, p in ctx.curr_prefs.items():
        ctx.G[a] = map(lambda e: reverse_ends[e], ctx.curr_prefs[a][0])


def _add_to_U(a, ctx):
    # Add a to unsatisfied set if he's not satisfied
    if ctx.curr_ends[a] not in ctx.curr_prefs[a][0]:
        ctx.U.add(a)


def _collect_unsatisfied(ctx):
    ctx.U.clear()
    for a in ctx.curr_ends:
        _add_to_U(a, ctx)


def _is_terminal(sink, ctx):
    return reduce(lambda x, a: x and a not in ctx.U, sink, True)


def _remove_terminal_sinks(ctx):
    """
    Use Tarjan's strongly connected component algorithm to find all sinks.
    If a sink is terminal remove it.
    Continue until there are no more terminal sinks
    :returns True if a terminal sink was removed
    """
    found_terminal_sink = False

    sinks = tarjan(ctx.G)

    for sink in sinks:
        if _is_terminal(sink, ctx):
            found_terminal_sink = True
            for a in sink:
                #  make assignment:
                #  remove curr_pref[a], G[a], curr_end[a]
                #  add alloc[a]
                #  NB. _update_ends() takes care of ends[a] and prefs[a] so don't worry about it here
                if a in ctx.alloc:
                    ctx.alloc[a].append(ctx.curr_ends[a])
                else:
                    ctx.alloc[a] = [ctx.curr_ends[a]]
                del ctx.curr_ends[a]  # remove it from the problem
                del ctx.G[a]
                del ctx.curr_prefs[a]

    return found_terminal_sink


def _update_context_and_clear_cycles(ctx):
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


def _U_select(F, L, U, G,  agent_priority):
    """
    updates F for members of U so that there's an edge to each member's highest priority neighbor in G
    agent_priority is a function mapping agents to their endowment's priority
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
    Keep sets of labeled (who have an out edge in F) and unlabeled vertices of F. Label each vertex by labeling
    unlabeled vertices that are adjacent to labeled vertices.
    """
    UL = set(G.keys()).difference(L)
    AL = Fibonacci_heap()  # Adjacent to labeled
    reverse_G = _reverse_graph(G)
    while UL:
        _collect_adjacent_to_labeled(AL, reverse_G, L, agent_priority)
        a = AL.dequeue_min().get_value()
        labeled_adjacent_to_a = filter(lambda adj_to_a: adj_to_a in L, G[a])
        F[a] = min(labeled_adjacent_to_a, key=agent_priority)
        L.add(a)
        UL.remove(a)


def _collect_adjacent_to_labeled(AL, reverse_G, L, priority):
    for labeled in L:
        for a in reverse_G[labeled]:
            if a not in L:
                AL.enqueue(a, priority=priority(a))


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
    Returns a function that returns F[a] if the first reachable unsatisfied agent in F still holds end
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
        assert len(cycle) > 1
        for a, b in reversed(list(zip(cycle[1:], cycle[:-1]))):
            ctx.curr_ends[a] = ctx.curr_ends[b]
        ctx.curr_ends[cycle[0]] = last_end