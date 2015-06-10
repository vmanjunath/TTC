from collections import namedtuple
from functools import reduce
from tarjan import tarjan

TTCContext = namedtuple('TTCContext', ['prefs',  # Starts as input prefs, but elements popped as agents trades
                                       'ends',  # Starts as input ends, but elements popped as agents trade
                                       'curr_ends',  # Single endowment for current round
                                       'curr_prefs',  # Preferences over endowments for current round
                                       'G',  # TTC graph for current round
                                       'persistence_test',  # A function that returns a boolean for each agent to
                                                            # determine persistence.
                                       'U',  # Set of unsatisfied agents in current round
                                       'alloc'  # The final allocation
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
        alloc={}
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
            alloc_next = ctx.curr_ends[sink[-1]]  # this is what you give the first guy
            for a in sink:
                #  make assignment:
                #  remove curr_pref[a], G[a], curr_end[a]
                #  add alloc[a]
                #  NB. _update_ends() takes care of ends[a] and prefs[a] so don't worry about it here
                if a in ctx.alloc:
                    ctx.alloc[a].append(alloc_next)
                else:
                    ctx.alloc[a] = [alloc_next]
                alloc_next = ctx.curr_ends[a]  # for the next guy
                del ctx.curr_ends[a]  # remove it from the problem
                del ctx.G[a]
                del ctx.curr_prefs[a]

    return found_terminal_sink


def _update_context(ctx):
    _update_ends(ctx)
    _get_curr_prefs(ctx)
    _build_ttc_graph(ctx)
    _collect_unsatisfied(ctx)


def _iteratively_remove_sinks(ctx):
    _update_context(ctx)
    while _remove_terminal_sinks(ctx):
        _update_context(ctx)

