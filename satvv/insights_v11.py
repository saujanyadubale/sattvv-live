"""Explainable monitoring and review-only advisory layer for synthetic SAT-V&V.

Causality boundary: this module only reads recorded telemetry and executed
verification evidence. No hidden injected-fault metadata is accepted. Neither
an early warning nor a recommendation may alter a formal PASS/FAIL verdict.
The heuristic thresholds are prototype choices, NOT flight-qualified limits.
"""
from __future__ import annotations
from math import isfinite
from .coupled import predict_nominal_voltage

SIGNALS = {
    'bus_voltage_v':('Bus voltage','V','EPS'),
    'bus_current_a':('Bus current','A','EPS'),
    'battery_soc_pct':('Battery charge','%','EPS'),
    'temperature_c':('Primary temperature','°C','THERMAL'),
    'redundant_temperature_c':('Redundant temperature','°C','THERMAL'),
    'packet_loss_fraction':('Packet loss','fraction','COMMS'),
    'load_w':('Power load','W','EPS'),
    'solar_w':('Solar input','W','EPS'),
    'latency_ms':('Link latency','ms','COMMS'),
}

PLAYBOOKS={
    'THERMAL':{
        'check':'T11 / T16 — compare redundant temperature sensors and measure drift during a stable operating mode.',
        'mitigation':'Review sensor calibration and redundancy handling; consider restricting decisions that rely on a suspect sensor, subject to approved operations procedures.'},
    'EPS':{
        'check':'T03 / T14 — review load-step response and compare measured voltage against charge- and load-conditioned expectations.',
        'mitigation':'Review allowable payload power and battery margins; consider approved load shedding only after confirming spacecraft mode and constraints.'},
    'COMMS':{
        'check':'T05 / T08 — repeat packet-loss, latency and checksum checks, and inspect attitude and downlink mode.',
        'mitigation':'Review link margin, data rate, coding and retry settings using mission-approved ground procedures.'},
    'ADCS':{
        'check':'T17–T20 — check attitude hold, slew response, sensor agreement and wheel momentum.',
        'mitigation':'Review approved attitude-control safe modes and reaction-wheel constraints; do not issue unvalidated autonomous commands.'},
    'OBC':{
        'check':'T01 / T10 / T12 — review reboot history, watchdog recovery and command guards.',
        'mitigation':'Review watchdog logs and the recovery plan before an authorized reset or mode transition.'},
    'PAYLOAD':{
        'check':'T04 / T09 / T15 — inspect payload power cycling and thermal recovery.',
        'mitigation':'Review duty cycle and power budget; protect instruments under approved operating limits.'},
}

def _numeric(row,key):
    v=row.get(key)
    return float(v) if type(v) in (int,float) and isfinite(float(v)) else None

def analyse(observations:list[dict], evidence:list[dict], weak_events=None) -> dict:
    """Produce post-run observable-only hints and a review action, not diagnosis truth."""
    rows=sorted((r for r in observations if isinstance(r,dict) and _numeric(r,'time_s') is not None),key=lambda x:x['time_s'])
    alerts=[];live=[]
    # Debounced low-level monitoring; not the formal verification oracle.
    consecutive={'thermal':0,'power':0,'comms':0};latched=set()
    for r in rows:
        t=int(r['time_s']);a=_numeric(r,'temperature_c');b=_numeric(r,'redundant_temperature_c')
        voltage=_numeric(r,'bus_voltage_v');soc=_numeric(r,'battery_soc_pct');load=_numeric(r,'load_w')
        packet=_numeric(r,'packet_loss_fraction')
        drift=abs(a-b) if a is not None and b is not None else None
        nominal=predict_nominal_voltage(soc/100.,load) if soc is not None and load is not None else None
        residual=(nominal-voltage) if nominal is not None and voltage is not None else None
        tests={
          'thermal':drift is not None and drift>=1.20,
          'power':residual is not None and residual>.16,
          'comms':packet is not None and packet>.08 and r.get('mode')=='DOWNLINK'
        }
        for kind,on in tests.items():
            consecutive[kind]=consecutive[kind]+1 if on else 0
            if not on:latched.discard(kind)
            if consecutive[kind]>=3 and kind not in latched:
                latched.add(kind)
                metric={'thermal':'Redundant sensor disagreement','power':'Physics-based voltage residual','comms':'Packet loss in downlink'}[kind]
                value={'thermal':drift,'power':residual,'comms':packet}[kind]
                alerts.append({'time_s':t,'kind':kind,'subsystem':{'thermal':'THERMAL','power':'EPS','comms':'COMMS'}[kind],
                  'metric':metric,'measured':round(value,5),
                  'meaning':'Persistent model-conditioned deviation; a review warning, not a verified fault.'})
        live.append({'time_s':t,'sensor_delta_c':round(drift,5) if drift is not None else None,
                     'voltage_residual_v':round(residual,5) if residual is not None else None})
    # Window-specific evidence may expose faults too brief for sampled replay telemetry.
    for r in evidence:
        if r.get('test_window_monitor',{}).get('comms_warning'):
            alerts.append({'time_s':int(r['end_s']),'kind':'comms','subsystem':'COMMS',
                           'metric':'Packet loss measured during verification procedure',
                           'measured':None,'meaning':'Test-window warning; not itself a PASS/FAIL outcome.'})
    # Merge causal high-resolution monitor alerts, preserving event timestamps.
    # Existing three-sample monitor remains for backward compatibility.
    for event in (weak_events or []):
        if not any(x['subsystem']==event['subsystem'] and abs(x['time_s']-event['time_s'])<=60 for x in alerts):
            alerts.append(dict(event))
    alerts.sort(key=lambda e:e['time_s'])
    failed=[{'test_id':r.get('test_id'),'requirements':[k for k,v in r.get('checks',{}).items() if v is False],
             'subsystem':r.get('subsystem'),'time_s':r.get('end_s')} for r in evidence if r.get('status')=='FAIL']
    if failed:
        focus=failed[0]['subsystem'];level='verified_failure'
        basis='The executed verification procedure failed a project-defined requirement.'
    elif alerts:
        focus=alerts[-1]['subsystem'];level='early_warning'
        basis='A persistent deviation or test-window warning was observed, but no executed requirement check failed.'
    else:
        focus=None;level='no_evidence'
        basis='No warning or failed requirement was found in the available recorded evidence; this does not establish the absence of faults.'
    book=PLAYBOOKS.get(focus,{ 'check':'Review the available measurements and select a safe, relevant verification procedure.',
                              'mitigation':'No corrective action is justified from the current evidence.'})
    return {'status':level,'explanation':basis,'warning_events':alerts,'warning_count':len(alerts),
            'derived_telemetry':live,'failed_checks':failed,'focus_subsystem':focus,
            'recommended_next_check':book['check'],'possible_mitigation_for_review':book['mitigation'],
            'limitations':'Prototype heuristic thresholds, model-dependent synthetic telemetry; neither an early warning nor the suggested mitigation changes requirement outcomes or triggers a spacecraft command.',
            'evidence_scope':'computed only from recorded measurements and executed checks; hidden fault oracle excluded'}
