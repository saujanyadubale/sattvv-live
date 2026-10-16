"""v0.9.6 requirement-level Bayesian *illustrative* diagnostic signatures.

Likelihoods are explicitly declared expert priors for this synthetic model, NOT
learned/calibrated probabilities. No fault oracle is consulted at inference.
For combined faults, categorical hypotheses identify the best individual mechanism,
not a complete multi-label or causal diagnosis.
"""
from __future__ import annotations
from math import log2

# Each requirement has a physically motivated fault signature. These are
# toy likelihoods, independent of injected hidden labels at decision time.
SIGNATURES={
 'REQ-COM-L':{'radio_burst':.92},
 'REQ-COM-T':{'radio_burst':.30},
 'REQ-COM-C':{'radio_burst':.16},
 'REQ-EPS-R':{'resistance_ramp':.86,'intermittent_resistance':.82},
 'REQ-EPS-REC':{'resistance_ramp':.67,'intermittent_resistance':.77},
 'REQ-EPS-V':{'resistance_ramp':.58,'intermittent_resistance':.72},
 'REQ-EPS-I':{'resistance_ramp':.25,'intermittent_resistance':.30},
 'REQ-ECL-V':{'resistance_ramp':.75,'intermittent_resistance':.71},
 'REQ-ECL-S':{'resistance_ramp':.16,'intermittent_resistance':.15},
 'REQ-THM-T':{'heater_fault':.81,'resistance_ramp':.20},
 'REQ-THM-R':{'heater_fault':.77},
 'REQ-THM-D':{'sensor_drift':.78},
 'REQ-THM-DR':{'sensor_drift':.90},
 'REQ-ADCS-HOLD':{'adcs_wheel_weak':.73,'adcs_gyro_bias':.25},
 'REQ-ADCS-SLEW':{'adcs_wheel_weak':.87},
 'REQ-ADCS-SENS':{'adcs_gyro_bias':.91,'adcs_star_dropout':.91},
 'REQ-ADCS-MOM':{'adcs_wheel_weak':.83},
}

def fail_probability(hypothesis,requirement):
    # Nonzero background failure chance is essential for a probabilistic update.
    if hypothesis=='healthy':return .018
    if requirement in SIGNATURES and hypothesis in SIGNATURES[requirement]:
        return SIGNATURES[requirement][hypothesis]
    return .038

def update_requirements(prior, checks):
    """Update using PASS/FAIL/INCONCLUSIVE outcomes separately.

    This is a *naive* conditional independence approximation; repeated correlated
    observations can cause overconfidence. Report weights as uncalibrated.
    """
    unnorm={h:max(1e-40,float(p)) for h,p in prior.items()}
    for req,outcome in checks.items():
        if outcome is None:continue
        for hypothesis in unnorm:
            pf=fail_probability(hypothesis,req)
            unnorm[hypothesis]*=(1.-pf)**.12 if outcome is True else pf
    total=sum(unnorm.values())
    if total<1e-100:return dict(prior)
    return {h:v/total for h,v in unnorm.items()}

def entropy(p):return -sum(v*log2(v) for v in p.values() if v>0)

def expected_information(prior,requirements):
    # Aggregate independent test checks into a Bernoulli ANY-FAIL event.
    if not requirements:return 0.
    likelihood={h:1. for h in prior}
    for req in requirements:
        for h in likelihood:likelihood[h]*=(1-fail_probability(h,req))
    likelihood={h:1-v for h,v in likelihood.items()}
    pf=sum(prior[h]*likelihood[h] for h in prior)
    if pf<=1e-10 or pf>=1-1e-10:return 0.
    after_fail={h:prior[h]*likelihood[h]/pf for h in prior}
    after_pass={h:prior[h]*(1-likelihood[h])/(1-pf) for h in prior}
    return max(0.,entropy(prior)-pf*entropy(after_fail)-(1-pf)*entropy(after_pass))
