from collections import namedtuple
from functools import reduce


TTCContext = namedtuple('TTCContext', ['prefs',  # Starts as input prefs, but elements popped as agents trades
                                       'ends',  # Starts as input ends, but elements popped as agents trade
                                       'curr_ends',  # Single endowment for current round
                                       'curr_prefs',  # Preferences over endowments for current round
                                       'G',  # TTC graph for current round
                                       'persistence_test',  # a function that returns a boolean for each agent to
                                                            # determine persistence.
                                       'U'  # Set of unsatisfied agents in current round
                                       ])


def ttc(prefs, ends, priority):
    ctx = TTCContext(
        prefs=prefs,
        ends=ends,
        curr_ends={},
        curr_prefs={},
        G={},
        persistence_test={},
        U=set({})
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
    end_set = reduce(lambda x, y: x.union(set(y)), ctx.curr_ends.values(), set({}))  # all possible endowments
    for a, p in ctx.prefs.items():
        ctx.curr_prefs[a] = _get_curr_agent_prefs(p, end_set)


def _build_ttc_graph(ctx):
    # need reverse relationship between endowments and agents
    reverse_ends = {end: a for a, end in ctx.curr_ends.items()}

    ctx.G.clear()

    for a, p in ctx.curr_prefs.items():
        ctx.G[a] = map(lambda e: reverse_ends[e], ctx.curr_prefs[a][0])


