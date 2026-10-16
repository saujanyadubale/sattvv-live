"""v1.0.2 bounded, observable-only, risk-aware verification sequence planning.

Searches short lists of scheduled tests under the remaining budget. Expected failure
likelihoods are *heuristic expert signatures*, not calibrated probabilities. A plan
is reconsidered after every observed test; future physics is not rolled out.
Safety filtering must be done by the caller at each actual decision.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from .diagnosis_v096 import fail_probability, expected_information

@dataclass(frozen=True)
class PlanDecision:
    test: object
    sequence: tuple[str,...]
    objective: float
    reason: str
    candidate_count: int
    search_depth: int


def ranked_plan(safe, belief, coverage, ages, repeats, *, time_s, remaining_min,
                warning_weights, risk, adcs_risk=0., beam_width=12, depth=3):
    """Bounded beam search with observable state and frozen heuristic beliefs.

    Rewards an early expected FAIL, new requirements, subsystem diversity,
    stale-check renewal, and diagnostic information; penalizes repeats and cost.
    Sequence outcomes are approximated as independent and do not leak simulated faults.
    """
    if not safe:raise ValueError('No safe affordable procedures')
    if not isinstance(remaining_min,(int,float)) or not isfinite(remaining_min) or remaining_min<=0:
        raise ValueError('Invalid remaining budget')
    if not isinstance(depth,int) or not 1<=depth<=5 or not 1<=beam_width<=64:
        raise ValueError('Invalid search limits')
    # Restrict the expensive search to candidates that can actually run now.
    safe=tuple(t for t in safe if t.cost<=remaining_min)
    if not safe:raise ValueError('No affordable procedures')
    subsystems={t.subsystem for t in safe}
    by_subsystem={s:sum(repeats.get(t.id,0) for t in safe if t.subsystem==s) for s in subsystems}
    def hazard(t):
        chance_pass=0.
        for h,p in belief.items():
            local=1.
            for req in t.checks:local*=1.-fail_probability(h,req)
            chance_pass+=float(p)*(1.-local)
        # Outcome model is only qualitative under compound faults / changing time.
        return min(.70,max(.02,chance_pass))
    def age_metric(t):
        return sum(max(0.,min(2.5,(time_s-ages[r])/1200.)) for r in t.checks if r in ages)
    first_features={}
    for t in safe:
        h=hazard(t)
        ig=expected_information(belief,t.checks)
        subrisk=max(0.,float(warning_weights.get(t.subsystem,0.)))+max(0.,float(risk.get(t.subsystem,0.)))
        if t.subsystem=='ADCS':subrisk+=max(0.,float(adcs_risk))
        first_features[t.id]=(h,ig,subrisk,age_metric(t))
    # (value, selected objects, accumulated duration, plan coverage, plan subsystems, survival)
    beam=[(0.,(),0.,frozenset(coverage),frozenset(),1.)]
    evaluated=0
    best=None
    # Candidate sequences are deliberately short and replanned after observation.
    for level in range(1,depth+1):
        next_beam=[]
        for score,seq,cost,seen,subseen,survival in beam:
            chosen_ids={x.id for x in seq}
            for t in safe:
                if t.id in chosen_ids or cost+t.cost>remaining_min:continue
                evaluated+=1
                prob,ig,subrisk,age=first_features[t.id]
                novel=len(set(t.checks)-seen)
                novel_sub=int(t.subsystem not in subseen)
                # Avoid allowing repeatedly executed quick tests to dominate the search.
                repeats_before=repeats.get(t.id,0)
                subrepeats=by_subsystem[t.subsystem]
                # Recency encourages return patrols when faults may start late.
                expired=age / max(1,len(t.checks))
                # A previously passing check becomes less reassuring with time.
                # Avoid a completely one-pass schedule in evolving fault conditions.
                stale_minutes=min((max(0,time_s-ages[r])/60 for r in t.checks if r in ages),default=0.)
                renewal=2.6*min(2.5,max(0.,(stale_minutes-15.)/12.)) if repeats_before else 0.
                effective_prob=min(.8,prob*(1.+.12*subrisk))
                detection_value=survival*effective_prob*8.0/(1.+.025*(cost+t.cost))
                immediate=(detection_value + 1.55*novel + 1.3*novel_sub +
                           .36*ig + .35*subrisk + .75*expired + renewal + .23*t.criticality -
                           1.9*repeats_before - .20*subrepeats)
                # Avoid unrealistic pressure to fill every minute with short tests.
                immediate-=.32*t.cost
                value=score+immediate*(.88**cost)
                seq2=seq+(t,)
                candidate=(value,seq2,cost+t.cost,seen.union(t.checks),
                           subseen.union((t.subsystem,)),survival*(1-effective_prob))
                next_beam.append(candidate)
                # A prefix is a valid plan when the remaining budget is short.
                if best is None or (value,-cost,tuple(-int(x.id[1:]) for x in seq2)) > (best[0],-best[2],tuple(-int(x.id[1:]) for x in best[1])):
                    best=candidate
        if not next_beam:break
        next_beam.sort(key=lambda x:(-x[0],x[2],tuple(int(t.id[1:]) for t in x[1])))
        beam=next_beam[:beam_width]
    assert best is not None
    # Future utility can bias toward short tests; select first action of best plan.
    return PlanDecision(best[1][0],tuple(t.id for t in best[1]),round(best[0],5),
                        'bounded_sequence_lookahead',evaluated,len(best[1]))
