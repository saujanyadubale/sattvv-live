"""Observable-only test coverage safeguards for predictive-active scheduling.

A high model score cannot justify indefinitely starving physically distinct
verification procedures. These rules NEVER use scenario/fault identity and do
not override upstream safety guards or time-budget constraints.
"""
from __future__ import annotations

ADCS_ACTUATOR_PROCEDURES=('T17','T18','T20')


def adcs_observable_risk(sample):
    """Risk cues from measurable attitude response; NOT hidden wheel truth.

    This signal is necessarily weak when no wheel maneuver has excited the
    actuator. That is why diverse functional tests are still necessary.
    """
    if not sample:
        return 0.0
    if not sample.get('star_available',True):
        return 4.0
    if abs(sample.get('gyro_rads',0)-sample.get('star_rate_rads',0))>.003:
        return 4.0
    attitude_error=abs(sample.get('theta_deg',0)-sample.get('target_deg',0))
    angular_rate=abs(sample.get('omega_rads',0))
    momentum=abs(sample.get('momentum_nms',0))
    return (3.0 if attitude_error>5. and angular_rate<.001 else 0.0) + (2.0 if momentum>.10 else 0.0)


def choose_with_guard(safe, scoring, repeats, *, repeat_streak, remaining_min):
    """Return selected safe test and an auditable override reason.

    Enforce a maximum of two consecutive *repeat* selections when there are
    still safe, affordable procedures never executed. For longer campaigns,
    reserve enough budget for untried safe procedures when feasible. Neither
    rule implies all procedures can be covered under a short budget.
    """
    if not safe:
        raise ValueError('No safe affordable tests')
    untried=[t for t in safe if not repeats.get(t.id,0)]
    reason='adaptive_score'
    total_untried_cost=sum(t.cost for t in untried)
    reserve=(len(untried)>0 and remaining_min>=total_untried_cost and
             remaining_min-total_untried_cost<=2)
    if untried and (repeat_streak>=2 or reserve):
        pool=untried
        reason='repeat_streak_limit' if repeat_streak>=2 else 'coverage_budget_reserve'
    else:
        pool=safe
    selected=max(pool,key=lambda t:(scoring(t),-int(t.id[1:])))
    return selected,reason
