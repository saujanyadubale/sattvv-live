"""v0.5 coupled EPS/thermal simulator with finite, recurring, and ramping episodes.

Toy engineering model for research; all parameters illustrative. Truth labels stay
in the experiment harness and are never included in telemetry or policy evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt, exp, isfinite
from typing import Any
from .core import Mode
from .dynamics import DynamicSpacecraft, DynamicsConfig, LEGAL_TRANSITIONS, MODE_LOAD_W

SCENARIOS = ('healthy', 'resistance_ramp', 'intermittent_resistance',
             'sensor_drift', 'heater_fault', 'radio_burst', 'normal_load_cycle')

@dataclass(frozen=True)
class Episode:
    mechanism: str
    start_s: float
    end_s: float
    severity: float = 1.0
    ramp_s: float = 0.0

    def __post_init__(self):
        if self.mechanism not in ('battery_resistance', 'sensor_drift', 'heater_fault',
                                  'radio_burst', 'extra_load'):
            raise ValueError('Unknown episode mechanism')
        if not (0 <= self.start_s < self.end_s and self.ramp_s >= 0 and
                0 <= self.severity <= 3 and all(isfinite(x) for x in
                (self.start_s, self.end_s, self.severity, self.ramp_s))):
            raise ValueError('Invalid episode interval/severity')

    def weight(self, time_s: float) -> float:
        if not self.start_s <= time_s < self.end_s:
            return 0.0
        if self.ramp_s:
            return self.severity * min(1.0, (time_s-self.start_s)/self.ramp_s)
        return self.severity


def make_episodes(scenario: str, severity: float = 1.0,
                  onset_s: int = 480) -> tuple[Episode, ...]:
    if scenario not in SCENARIOS:
        raise ValueError('Unknown scenario')
    if type(onset_s) is not int or onset_s < 0 or onset_s % 10:
        raise ValueError('onset_s must be a nonnegative multiple of 10')
    if not isfinite(severity) or not 0 <= severity <= 3:
        raise ValueError('severity must be [0, 3]')
    if scenario == 'resistance_ramp':
        return (Episode('battery_resistance', onset_s, onset_s+1500, severity, 700),)
    if scenario == 'intermittent_resistance':
        return (Episode('battery_resistance', onset_s, onset_s+180, severity),
                Episode('battery_resistance', onset_s+360, onset_s+660, severity*min(1.35, 3/max(severity, .001))),)
    if scenario == 'sensor_drift':
        return (Episode('sensor_drift', onset_s, onset_s+1500, severity, 900),)
    if scenario == 'heater_fault':
        return (Episode('heater_fault', onset_s, onset_s+1500, severity),)
    if scenario == 'radio_burst':
        return (Episode('radio_burst', onset_s, onset_s+150, severity),
                Episode('radio_burst', onset_s+350, onset_s+510, severity))
    if scenario == 'normal_load_cycle':
        # healthy operational change / hard negative (NOT a fault label)
        return (Episode('extra_load', onset_s, onset_s+180, severity),)
    return ()


def predict_nominal_voltage(soc: float, power_w: float, resistance_ohm: float = .12) -> float:
    """Positive root of V*(Voc-V)/R=P for constant-power load, stable branch."""
    voc = 7.25 + .6 * min(1., max(0., soc))
    disc = voc*voc - 4*resistance_ohm*max(0., power_w)
    return (voc + sqrt(max(0., disc))) / 2 if disc >= 0 else .5*voc


class CoupledSpacecraft(DynamicSpacecraft):
    """Compatible with v0.4 command/test executor; independent v0.5 dynamics."""
    def __init__(self, episodes: tuple[Episode,...] = (), seed: int = 0,
                 initial_soc: float = .80, eclipse: bool = False):
        super().__init__(DynamicsConfig(initial_soc=initial_soc), seed=seed)
        self._episodes = tuple(episodes)
        self.eclipse = eclipse
        self.extra_load_w = 0.0
        self.sunlit_override: bool | None = None
        self.true_temperature_c = self.state.temperature_c
        self.true_resistance_ohm = .12
        self._temperature_bias_c = 0.0

    def _weights(self, t: float | None = None) -> dict[str, float]:
        when = self.state.time_s if t is None else t
        out: dict[str, float] = {}
        for ep in self._episodes:
            out[ep.mechanism] = out.get(ep.mechanism, 0.0) + ep.weight(when)
        return out

    def _sun(self, external_sunlit: bool) -> bool:
        if self.sunlit_override is not None:
            return self.sunlit_override
        # An independently specified orbit eclipse window, not a fault.
        return external_sunlit and not (self.eclipse and 600 <= self.state.time_s < 1200)

    def _electrical(self):
        weights = self._weights()
        load = (MODE_LOAD_W[self.state.mode] + self.extra_load_w +
                3.0 * weights.get('extra_load', 0.0))
        resistance = .12 + .60 * weights.get('battery_resistance', 0.0)
        voltage = predict_nominal_voltage(self.state.soc, load, resistance)
        current = load / max(.5, voltage)
        self.true_resistance_ohm = resistance
        return load, voltage, current

    def step(self, dt_s: float, *, sunlit: bool = True) -> None:
        if not isfinite(dt_s) or dt_s <= 0 or dt_s > 30:
            raise ValueError('Step must be finite and in (0,30] seconds')
        # Explicit Euler for SOC, exact update for one-node thermal model.
        load, voltage, current = self._electrical()
        solar = self.config.solar_array_w*self.config.charge_efficiency if self._sun(sunlit) else 0.
        self.state.soc = max(0., min(1., self.state.soc +
                              (solar-load)*dt_s/(3600*self.config.battery_capacity_wh)))
        weights = self._weights()
        dissipation = current*current*self.true_resistance_ohm
        heat = .58*load + dissipation + 8.*weights.get('heater_fault', 0.)
        k = self.config.thermal_conductance_w_per_k
        decay = exp(-k*dt_s/self.config.thermal_capacity_j_per_k)
        amb = self.config.ambient_temperature_c
        self.state.temperature_c = (amb+(self.state.temperature_c-amb)*decay+
                                     heat/k*(1.-decay))
        self.true_temperature_c = self.state.temperature_c
        self.state.time_s = round(self.state.time_s + dt_s, 9)
        if self.state.cpu_hung and self.state.hung_since_s is not None:
            if self.state.time_s-self.state.hung_since_s >= self.config.watchdog_timeout_s:
                self.state.cpu_hung = False
                self.state.hung_since_s = None
                self.state.mode = Mode.SAFE
                self._event('watchdog_recovered', mode=Mode.SAFE.value)
        _, new_voltage, _ = self._electrical()
        if self.state.mode not in (Mode.BOOT, Mode.SAFE) and (new_voltage < 6.70 or self.state.temperature_c > 70.):
            cause = 'LOW_VOLTAGE' if new_voltage < 6.70 else 'OVERHEAT'
            self.state.mode = Mode.SAFE
            self._event('autonomous_safe_mode', cause=cause)

    def telemetry(self, *, sunlit: bool = True) -> dict[str, Any]:
        load, voltage, current = self._electrical()
        weights = self._weights()
        t1 = self.state.temperature_c + self._rng.gauss(0, .12)
        t2 = (self.state.temperature_c + 5.*weights.get('sensor_drift', 0.) +
              self._rng.gauss(0, .12))
        observed_voltage = voltage + self._rng.gauss(0, .012)
        link = self.state.mode is Mode.DOWNLINK
        loss = (.012 + .32*weights.get('radio_burst', 0.)) if link else 0.
        loss = min(.99, loss)
        solar = self.config.solar_array_w*self.config.charge_efficiency if self._sun(sunlit) else 0.
        alarms: list[str] = []
        if observed_voltage < 6.70: alarms.append('EPS_UNDERVOLTAGE')
        if current > self.config.max_bus_current_a: alarms.append('EPS_OVERCURRENT')
        if t1 > 70.: alarms.append('THERMAL_OVERLIMIT')
        if abs(t1-t2) > 3.: alarms.append('SENSOR_DISAGREEMENT')
        if link and loss > .1: alarms.append('COMMS_DEGRADED')
        if self.state.cpu_hung and self.state.hung_since_s is not None:
            if self.state.time_s-self.state.hung_since_s >= self.config.watchdog_timeout_s:
                alarms.append('WATCHDOG_TIMEOUT')
        return {'time_s':round(self.state.time_s,5), 'mode':self.state.mode.value,
                'battery_soc_pct':round(100*self.state.soc,3),
                'bus_voltage_v':round(observed_voltage,4),
                'bus_current_a':round(current,4), 'load_w':round(load,4),
                'solar_w':round(solar,3), 'temperature_c':round(t1,3),
                'redundant_temperature_c':round(t2,3),
                'packet_loss_fraction':round(loss,4),
                'latency_ms':80. if link else 0., 'checksum_ok':True,
                'cpu_responsive':not self.state.cpu_hung, 'alarms':alarms}


def simulate_health(scenario: str = 'resistance_ramp', *, severity: float = 1.,
                    onset_s: int = 480, duration_s: int = 2400, step_s: int = 10,
                    seed: int = 7, eclipse: bool = False,
                    initial_soc: float = .8, mode: str = 'NOMINAL') -> dict[str, Any]:
    if scenario not in SCENARIOS: raise ValueError('Invalid scenario')
    if not type(duration_s) is int or not type(step_s) is int or not 1 <= step_s <= 30 or not 300 <= duration_s <= 5400 or duration_s % step_s:
        raise ValueError('duration_s must be 300-5400 and divisible by step_s (<=30)')
    if not type(seed) is int or not 0 <= seed <= 1000000:
        raise ValueError('seed must be [0,1000000] integer')
    if type(eclipse) is not bool or not 0 <= initial_soc <= 1: raise ValueError('Invalid environment')
    episodes = make_episodes(scenario, severity, onset_s)
    sim = CoupledSpacecraft(episodes, seed, initial_soc, eclipse)
    if mode not in ('SAFE','NOMINAL','PAYLOAD','DOWNLINK'):
        raise ValueError('Invalid operating mode')
    for m in (Mode.SAFE, Mode.NOMINAL, Mode.PAYLOAD, Mode.DOWNLINK):
        if mode == 'SAFE' and m != Mode.SAFE: break
        if mode == 'NOMINAL' and m == Mode.PAYLOAD: break
        sim.command(m)
        if m.value == mode: break
    timeline=[]
    for i in range(duration_s // step_s + 1):
        timeline.append(sim.telemetry())
        if i < duration_s//step_s: sim.step(step_s)
    return {'meta': {'version':'0.5', 'scenario':scenario,'severity':severity,
                     'onset_s':onset_s,'duration_s':duration_s,'step_s':step_s,
                     'seed':seed,'eclipse':eclipse,'initial_soc':initial_soc,
                     'model':'Uncalibrated synthetic coupled EPS/thermal system'},
            'telemetry':timeline,'events':sim.events,
            # Ground-truth intervals are only in evaluation metadata, never in observations.
            'truth':{'is_fault':scenario not in ('healthy','normal_load_cycle') and severity>0,
                     'episodes':[{'start_s':e.start_s,'end_s':e.end_s,'mechanism':e.mechanism}
                                 for e in episodes if e.mechanism != 'extra_load' and e.severity>0]}}
