"""v0.9 experimental offline-learned test ranking.

Classifier is trained on independent synthetic test executions, without fault
identity or future telemetry as predictors. It ranks test failure likelihoods,
not root causes, and probabilities are not asserted to be calibrated.
"""
from __future__ import annotations
from functools import lru_cache
from .adcs_v08 import SpacecraftWithADCS
from .verification_v05 import ALL_TESTS
from .adcs_v08 import ADCS_TESTS
from .coupled import predict_nominal_voltage
from .integrated_v08 import execute

ALL=ALL_TESTS+ADCS_TESTS
MODES=('BOOT','SAFE','NOMINAL','PAYLOAD','DOWNLINK')

def feature_row(obs,test,age=0.,repeats=0):
    return [int(test.id[1:]),test.cost,test.criticality,obs['time_s']/60,
            obs['bus_voltage_v'],obs['bus_current_a'],obs['temperature_c'],
            obs['redundant_temperature_c']-obs['temperature_c'],
            obs['packet_loss_fraction'],obs['battery_soc_pct'],
            MODES.index(obs['mode']),min(3.,age),min(5,repeats),
            obs['bus_voltage_v']-predict_nominal_voltage(obs['battery_soc_pct']/100,obs['load_w'])]

@lru_cache(maxsize=1)
def fit_failure_ranker():
    from sklearn.ensemble import RandomForestClassifier
    from .integrated_v08 import CAUSES
    X=[];y=[]
    for idx,cause in enumerate(CAUSES):
        for seed in (171,172,173):
            for onset,elapsed in ((0,300),(300,600)):
                for test in ALL:
                    sim=SpacecraftWithADCS(cause,onset_s=onset,seed=seed,severity=.85+idx*.05)
                    for _ in range(elapsed//10):sim.step(10)
                    obs=sim.telemetry()
                    rec=execute(sim,test)
                    if rec['status']=='INCONCLUSIVE':continue
                    X.append(feature_row(obs,test))
                    y.append(int(rec['detected']))
    if len(set(y))<2:raise AssertionError('Need both PASS and FAIL training examples')
    model=RandomForestClassifier(n_estimators=80,max_depth=8,min_samples_leaf=3,random_state=2026,n_jobs=1)
    model.fit(X,y)
    model.training_summary={'samples':len(X),'positive_rate':sum(y)/len(y),
        'mechanisms':len(CAUSES),'seeds':(171,172,173),'no_oracle_features':True}
    return model
