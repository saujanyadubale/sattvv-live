"""Causal weak-signal observer for synthetic SAT-V&V verification.

No fault label or injected scenario is available here. Signals are residuals
relative to *nominal project equations*, not hardware-calibrated probabilities.
Only PASS/FAIL from an executed requirement is a verified failure.
Thresholds are fixed before evaluation; monitor low-impact recall and healthy
false-alert rate on held-out seeds before attributing research merit.
"""
from __future__ import annotations
from collections import deque
from math import exp, isfinite
from statistics import mean
from .coupled import predict_nominal_voltage

# Conservative persistence thresholds in simulated units. Not flight limits.
THRESHOLDS = {'sensor_drift':0.43, 'battery_residual':0.050,
              'thermal_innovation':0.62, 'comms_loss':0.045}
SUBSYSTEM = {'sensor_drift':'THERMAL', 'battery_residual':'EPS',
             'thermal_innovation':'THERMAL','comms_loss':'COMMS'}
NAMES = {'sensor_drift':'Persistent signed sensor-pair bias',
         'battery_residual':'Load-conditioned voltage deficit',
         'thermal_innovation':'Excess thermal rise versus nominal heat balance',
         'comms_loss':'Persistent packet-loss excess during downlink'}


def _number(row,key):
    x=row.get(key)
    return float(x) if type(x) in (float,int) and isfinite(x) else None


class WeakSignalMonitor:
    """Bounded-memory, online observer updated only as samples arrive.

    Alerts are advisory and never directly modify a formal requirement result.
    Uses a signed difference between redundant thermometers to avoid triggering
    on normal common-mode heating; short spikes are suppressed by persistence.
    """
    def __init__(self):
        self.rows=deque(maxlen=20)
        self.events=[]
        self._consecutive={k:0 for k in THRESHOLDS}
        self._latched=set()
        self._active={}
        self.last_time=-1.
        self.last_features={}

    def _features(self):
        rows=list(self.rows)
        window=[x for x in rows if x['time_s']>=rows[-1]['time_s']-60]
        metrics={}
        if len(window)>=5:
            try:
                metrics['sensor_drift']=abs(mean(x['temperature_c']-x['redundant_temperature_c'] for x in window))
                metrics['battery_residual']=mean(predict_nominal_voltage(x['battery_soc_pct']/100,x['load_w'])-x['bus_voltage_v'] for x in window)
                comm=[x['packet_loss_fraction'] for x in window if x.get('mode')=='DOWNLINK']
                if len(comm)>=4:metrics['comms_loss']=mean(comm)-0.012
            except (KeyError,TypeError,ValueError):
                pass
        # Compare common-mode thermal rise to a nominal 100-second integrated
        # heat balance. This is a *synthetic model residual*, not a temperature
        # limit; abrupt test-mode load changes are included in the heat model.
        long=[x for x in rows if x['time_s']>=rows[-1]['time_s']-100]
        if len(long)>=7 and all('load_w' in x and 'bus_current_a' in x and 'temperature_c' in x and 'redundant_temperature_c' in x for x in long):
            if long[-1]['time_s']-long[0]['time_s']>=60:
                temp=.5*(long[0]['temperature_c']+long[0]['redundant_temperature_c'])
                for prior,next_row in zip(long,long[1:]):
                    dt=next_row['time_s']-prior['time_s']
                    if not 0<dt<=30:break
                    decay=exp(-.075*dt/260)
                    power=.58*prior['load_w']+.12*prior['bus_current_a']**2
                    temp=18+(temp-18)*decay+(power/.075)*(1-decay)
                else:
                    actual=.5*(long[-1]['temperature_c']+long[-1]['redundant_temperature_c'])
                    # A drifting *one* temperature sensor is not evidence of
                    # an actual common-mode thermal-heating abnormality.
                    if abs(long[-1]['temperature_c']-long[-1]['redundant_temperature_c'])<.55:
                        metrics['thermal_innovation']=actual-temp
        return metrics

    def update(self, row):
        if not isinstance(row,dict):return []
        t=_number(row,'time_s')
        if t is None or t<=self.last_time:return []
        self.last_time=t
        # Copy only publicly observable fields; no oracle/episode metadata.
        observable={k:row[k] for k in ('time_s','mode','temperature_c','redundant_temperature_c',
             'battery_soc_pct','load_w','bus_voltage_v','bus_current_a','packet_loss_fraction') if k in row}
        self.rows.append(observable)
        metrics=self._features();self.last_features=metrics
        fresh=[]
        for kind,limit in THRESHOLDS.items():
            value=metrics.get(kind)
            on=value is not None and value>limit
            self._consecutive[kind]=self._consecutive[kind]+1 if on else 0
            if not on:self._latched.discard(kind)
            if self._consecutive[kind]>=3:
                self._active[kind]=t
                if kind not in self._latched:
                    self._latched.add(kind)
                    event={'time_s':int(t),'kind':kind,'subsystem':SUBSYSTEM[kind],
                           'metric':NAMES[kind],'measured':round(value,5),
                           'threshold':limit,'source':'online_weak_signal_monitor',
                           'meaning':'Observable sustained deviation; advisory only, not a requirement FAIL.'}
                    self.events.append(event);fresh.append(event)
        return fresh

    def risks(self,now_s):
        """Soft relevance cue, decayed and never a bypass of safety gates."""
        risks={}
        for kind,last in self._active.items():
            age=now_s-last
            if 0<=age<=180:
                subsys=SUBSYSTEM[kind]
                risks[subsys]=max(risks.get(subsys,0.),3.0*(1-age/240))
        return risks

    def summary(self):
        return {'warning_events':self.events,'warning_count':len(self.events),
                'method':'causal 60–100 second rolling residuals with three-sample persistence',
                'thresholds':dict(THRESHOLDS),'features_last':dict(self.last_features),
                'status':'early_warning' if self.events else 'no_warning',
                'formal_verification_unchanged':True,
                'limitations':'Model-dependent thresholds; no calibrated flight false-alarm guarantees or verified multi-fault isolation.'}
