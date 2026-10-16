"""v0.8 illustrative single-axis attitude control, coupled to EPS power and thermal.

Not flight-control software. The controller is a toy PD reaction-wheel plant;
attitude units are radians, angular rates rad/s, torque N m, momentum N m s.
"""
from __future__ import annotations
from math import radians,degrees,isfinite
from dataclasses import dataclass
from .core import TestCase, Mode
from .coupled import CoupledSpacecraft, make_episodes, SCENARIOS
from .dynamic_campaign import _navigate

ADCS_FAULTS=('adcs_wheel_weak','adcs_gyro_bias','adcs_star_dropout')
ALL_SCENARIOS=SCENARIOS+ADCS_FAULTS
ADCS_TESTS=(
    TestCase('T17','ADCS attitude hold','ADCS',Mode.NOMINAL,4,('REQ-ADCS-HOLD',),criticality=1.9),
    TestCase('T18','ADCS commanded slew','ADCS',Mode.PAYLOAD,5,('REQ-ADCS-SLEW',),criticality=2.),
    TestCase('T19','ADCS sensor cross-check','ADCS',Mode.NOMINAL,3,('REQ-ADCS-SENS',),criticality=1.8),
    TestCase('T20','ADCS momentum and safe recovery','ADCS',Mode.NOMINAL,6,('REQ-ADCS-MOM',),criticality=2.1),
)
ADCS_REQUIREMENTS={
 'REQ-ADCS-HOLD':'Hold commanded attitude within 3 degrees in a standardized 4-min scenario',
 'REQ-ADCS-SLEW':'Complete 15-degree attitude slew within 5 degrees after 5 minutes',
 'REQ-ADCS-SENS':'Star tracker available and gyro-rate residual < 0.003 rad/s',
 'REQ-ADCS-MOM':'Healthy wheel momentum stays within 0.12 N m s and SAFE return command succeeds',
}

@dataclass
class ADCSState:
    theta_rad:float=0.
    omega_rads:float=0.
    momentum_nms:float=0.
    target_rad:float=0.
    last_torque_nm:float=0.
    star_available:bool=True

class SpacecraftWithADCS(CoupledSpacecraft):
    def __init__(self,scenario='healthy',severity=1.,onset_s=600,seed=0,initial_soc=.8,eclipse=False):
        if scenario not in ALL_SCENARIOS:raise ValueError('Unknown coupled/ADCS scenario')
        episodes=make_episodes(scenario,severity,onset_s) if scenario in SCENARIOS else ()
        super().__init__(episodes,seed=seed,initial_soc=initial_soc,eclipse=eclipse)
        self.adcs=ADCSState()
        self.adcs_scenario=scenario
        self.adcs_severity=severity
        self.adcs_onset_s=onset_s
        self.adcs_extra_power_w=0.0

    def _electrical(self):
        # Include ADCS electricity in both telemetry and thermal/SOC integration,
        # without overwriting the load commanded by the current test procedure.
        commanded=self.extra_load_w
        self.extra_load_w=commanded+self.adcs_extra_power_w
        try:return super()._electrical()
        finally:self.extra_load_w=commanded

    def _adcs_fault_active(self):
        return self.state.time_s>=self.adcs_onset_s and self.adcs_scenario in ADCS_FAULTS

    def step(self,dt_s,*,sunlit=True):
        if not isfinite(dt_s) or dt_s<=0 or dt_s>30:raise ValueError('Invalid dynamics step')
        # Subsecond-scale attitude integration, once-per-step power/thermal integration.
        # All campaign steps are integral seconds.
        self.adcs_extra_power_w=0.
        for _ in range(int(round(dt_s))):
            fault=self._adcs_fault_active()
            enabled=self.state.mode in (Mode.NOMINAL,Mode.PAYLOAD,Mode.DOWNLINK)
            torque=0.
            if enabled:
                error=self.adcs.target_rad-self.adcs.theta_rad
                desired=.012*error-.028*self.adcs.omega_rads
                max_torque=.007
                if fault and self.adcs_scenario=='adcs_wheel_weak':max_torque*=max(0.,1.-self.adcs_severity)
                torque=max(-max_torque,min(max_torque,desired))
                if abs(self.adcs.momentum_nms)>0.12 and self.adcs.momentum_nms*torque<0:torque=0.
            # Simple angular plant with weak damping, friction, and reaction-wheel momentum.
            self.adcs.omega_rads+=(torque-.002*self.adcs.omega_rads)/.08
            self.adcs.theta_rad+=self.adcs.omega_rads
            self.adcs.momentum_nms-=torque
            self.adcs.last_torque_nm=torque
            self.adcs.star_available=not (fault and self.adcs_scenario=='adcs_star_dropout')
            self.adcs_extra_power_w+=(.8+abs(torque)*120 if enabled else .12)
        self.adcs_extra_power_w/=int(round(dt_s))
        super().step(dt_s,sunlit=sunlit)

    def adcs_telemetry(self):
        active=self._adcs_fault_active()
        bias=.013*self.adcs_severity if active and self.adcs_scenario=='adcs_gyro_bias' else 0.
        return {'theta_deg':round(degrees(self.adcs.theta_rad),5),
                'omega_rads':round(self.adcs.omega_rads,6),
                'gyro_rads':round(self.adcs.omega_rads+bias+self._rng.gauss(0,.00015),6),
                'star_rate_rads':round(self.adcs.omega_rads+self._rng.gauss(0,.00015),6),
                'momentum_nms':round(self.adcs.momentum_nms,6),
                'star_available':self.adcs.star_available,
                'target_deg':round(degrees(self.adcs.target_rad),5),
                'bus_voltage_v':self._electrical()[1],
                'time_s':self.state.time_s}

def execute_adcs_test(sim:SpacecraftWithADCS,test:TestCase):
    if test.id not in {t.id for t in ADCS_TESTS}:raise ValueError('Not an ADCS procedure')
    start=sim.state.time_s
    reached,actions=_navigate(sim,test.target)
    # All ADCS procedures have standardized starting conditions; no hidden truth used.
    if test.id=='T17':sim.adcs.theta_rad=radians(9.);sim.adcs.omega_rads=0;sim.adcs.target_rad=0.
    elif test.id=='T18':sim.adcs.theta_rad=0.;sim.adcs.omega_rads=0.;sim.adcs.target_rad=radians(15.)
    elif test.id=='T19':sim.adcs.target_rad=sim.adcs.theta_rad
    else:sim.adcs.theta_rad=radians(8);sim.adcs.target_rad=0.;sim.adcs.momentum_nms=.06
    samples=[]
    for i in range(test.cost*6):
        samples.append(sim.adcs_telemetry())
        sim.step(10)
    samples.append(sim.adcs_telemetry())
    final=samples[-1]
    if not reached:check=None
    elif test.id=='T17':check=abs(final['theta_deg']-final['target_deg'])<=3.
    elif test.id=='T18':check=abs(final['theta_deg']-15.)<=5.
    elif test.id=='T19':check=all(x['star_available'] and abs(x['gyro_rads']-x['star_rate_rads'])<.003 for x in samples)
    else:check=all(abs(x['momentum_nms'])<=.12 for x in samples)
    # T20 also verifies legal command to SAFE, but doesn't mutate test time.
    if test.id=='T20' and reached:
        ack=sim.command(Mode.SAFE)
        check=bool(check and ack['accepted'])
    if int(sim.state.time_s-start)!=test.cost*60:raise AssertionError('ADCS clock discrepancy')
    req=test.checks[0]
    return {'kind':'test','test_id':test.id,'test_name':test.name,'subsystem':'ADCS',
            'start_s':start,'end_s':sim.state.time_s,'status':('INCONCLUSIVE' if check is None else 'PASS' if check else 'FAIL'),
            'detected':check is False,'checks':{req:check},'actions':actions,
            'transitions':[f"{a['from']}->{a['to']}" for a in actions if a['accepted']],
            'telemetry_end':sim.telemetry(),'adcs_end':final,
            'adcs_samples':samples,'cost_min':test.cost}

def run_adcs_suite(scenario='adcs_wheel_weak',seed=10,onset_s=0,severity=1.):
    result={}
    for t in ADCS_TESTS:
        sim=SpacecraftWithADCS(scenario,seed=seed,onset_s=onset_s,severity=severity)
        rec=execute_adcs_test(sim,t)
        result[t.id]={'status':rec['status'],'adcs_end':rec['adcs_end'],'min_bus_voltage_v':min(x['bus_voltage_v'] for x in rec['adcs_samples'])}
    return {'scenario':scenario,'procedures':result}
