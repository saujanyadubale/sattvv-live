"""SAT-V&V v0.2: deterministic, dimensioned, time-evolving spacecraft mock-up.

Engineering teaching/research model only. Parameters are illustrative rather than
calibrated against any actual spacecraft. The policy-facing telemetry omits fault truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite
import random
from typing import Any

from .core import Fault, Mode


@dataclass(frozen=True)
class DynamicsConfig:
    battery_capacity_wh: float = 24.0
    initial_soc: float = 0.80
    solar_array_w: float = 8.0
    charge_efficiency: float = 0.90
    ambient_temperature_c: float = 18.0
    initial_temperature_c: float = 23.0
    thermal_capacity_j_per_k: float = 260.0
    thermal_conductance_w_per_k: float = 0.075
    heat_fraction: float = 0.72
    minimum_bus_voltage_v: float = 6.70
    max_temperature_c: float = 70.0
    max_bus_current_a: float = 1.30
    watchdog_timeout_s: float = 120.0

    def __post_init__(self):
        positive = ('battery_capacity_wh', 'thermal_capacity_j_per_k',
                    'thermal_conductance_w_per_k', 'watchdog_timeout_s')
        if any(not isfinite(getattr(self, k)) or getattr(self, k) <= 0 for k in positive):
            raise ValueError('capacity, thermal constants, and watchdog timeout must be positive')
        if not 0 <= self.initial_soc <= 1 or not 0 <= self.charge_efficiency <= 1:
            raise ValueError('state of charge / efficiency must be in [0, 1]')
        if self.solar_array_w < 0 or not isfinite(self.solar_array_w):
            raise ValueError('solar generation must be a finite non-negative number')


@dataclass(frozen=True)
class FaultInjection:
    kind: Fault = Fault.NONE
    start_s: float = 600.0
    severity: float = 1.0

    def __post_init__(self):
        if not isfinite(self.start_s) or self.start_s < 0:
            raise ValueError('fault start must be non-negative and finite')
        if not isfinite(self.severity) or not 0 <= self.severity <= 3:
            raise ValueError('severity must be within [0, 3]')


# Simplified steady-state subsystem power. The model intentionally prioritizes
# coupling/traceability over engineering fidelity.
MODE_LOAD_W: dict[Mode, float] = {
    Mode.BOOT: 2.3, Mode.SAFE: 1.8, Mode.NOMINAL: 3.8,
    Mode.PAYLOAD: 6.4, Mode.DOWNLINK: 5.6,
}
LEGAL_TRANSITIONS = {
    Mode.BOOT: {Mode.SAFE},
    Mode.SAFE: {Mode.NOMINAL},
    Mode.NOMINAL: {Mode.SAFE, Mode.PAYLOAD},
    Mode.PAYLOAD: {Mode.NOMINAL, Mode.SAFE, Mode.DOWNLINK},
    Mode.DOWNLINK: {Mode.PAYLOAD, Mode.SAFE},
}


@dataclass
class SpacecraftState:
    time_s: float
    mode: Mode
    soc: float
    temperature_c: float
    cpu_hung: bool = False
    hung_since_s: float | None = None


class DynamicSpacecraft:
    """Emulated spacecraft with sequential commands and persistent physical state.

    All dynamics advance in *simulation seconds*. Commands are instantaneous at
    sampling boundaries. Fault truth remains private to the harness; published
    telemetry and command acknowledgments do not contain Fault or severity.
    """

    def __init__(self, config: DynamicsConfig | None = None,
                 injection: FaultInjection | None = None, seed: int = 0):
        self.config = config or DynamicsConfig()
        self._fault = injection or FaultInjection()
        self._rng = random.Random(seed)
        self.state = SpacecraftState(0.0, Mode.BOOT, self.config.initial_soc,
                                     self.config.initial_temperature_c)
        self.events: list[dict[str, Any]] = []
        self._stuck_temperature_c: float | None = None
        self._last_alarm_codes: list[str] = []

    def _active(self, at_s: float | None = None) -> bool:
        t = self.state.time_s if at_s is None else at_s
        return (self._fault.kind is not Fault.NONE and
                self._fault.severity > 0 and t >= self._fault.start_s)

    def _fault_is(self, fault: Fault) -> bool:
        return self._active() and self._fault.kind is fault

    def _event(self, type_: str, **properties: Any) -> None:
        self.events.append({'time_s': round(self.state.time_s, 5),
                            'type': type_, **properties})

    def command(self, target: Mode | str) -> dict[str, Any]:
        target = Mode(target)
        previous = self.state.mode
        if self.state.cpu_hung:
            response = {'accepted': False, 'reason': 'CPU_UNRESPONSIVE'}
        elif target not in LEGAL_TRANSITIONS[previous]:
            # A fault in the command guard erroneously permits SAFE->DOWNLINK.
            if self._fault_is(Fault.ILLEGAL_TRANSITION) and previous is Mode.SAFE and target is Mode.DOWNLINK:
                self.state.mode = target
                self._event('guard_violation', from_mode=previous.value, to_mode=target.value)
                response = {'accepted': True, 'reason': 'ACCEPTED_BY_FAULTY_GUARD'}
            else:
                response = {'accepted': False, 'reason': 'ILLEGAL_TRANSITION'}
        elif target is Mode.PAYLOAD and self._fault_is(Fault.PAYLOAD_BOOT_FAIL):
            self._event('payload_enable_failure')
            response = {'accepted': False, 'reason': 'PAYLOAD_ENABLE_FAILED'}
        else:
            self.state.mode = target
            response = {'accepted': True, 'reason': 'ACK'}
        self._event('command', from_mode=previous.value, to_mode=target.value, **response)
        return response

    def trigger_cpu_hang(self):
        if not self.state.cpu_hung:
            self.state.cpu_hung = True
            self.state.hung_since_s = self.state.time_s
            self._event('cpu_hang')

    def _electrical(self) -> tuple[float, float, float]:
        base_load = MODE_LOAD_W[self.state.mode]
        load = base_load + (5.2 * self._fault.severity if self._fault_is(Fault.OVERCURRENT) else 0)
        # Open-circuit proxy falls with SOC; load and fault add ohmic sag.
        voltage = (6.55 + 1.60 * self.state.soc) - 0.045 * load
        if self._fault_is(Fault.UNDERVOLTAGE):
            voltage -= self._fault.severity * (0.25 + 0.11 * load)
        current = load / max(voltage, 0.5)
        return load, voltage, current

    def step(self, dt_s: float, *, sunlit: bool = True) -> None:
        if not isfinite(dt_s) or dt_s <= 0:
            raise ValueError('step size must be positive and finite')
        t0 = self.state.time_s
        load, voltage, _ = self._electrical()
        solar = self.config.solar_array_w * self.config.charge_efficiency if sunlit else 0.0
        net_energy_wh = (solar - load) * dt_s / 3600.0
        self.state.soc = min(1.0, max(0.0, self.state.soc + net_energy_wh / self.config.battery_capacity_wh))
        q_in = self.config.heat_fraction * load
        if self._fault_is(Fault.THERMAL_RUNAWAY):
            q_in += 13.0 * self._fault.severity
        k = self.config.thermal_conductance_w_per_k
        decay = exp(-k * dt_s / self.config.thermal_capacity_j_per_k)
        amb = self.config.ambient_temperature_c
        self.state.temperature_c = (amb + (self.state.temperature_c - amb) * decay +
                                     (q_in / k) * (1.0 - decay))
        self.state.time_s = round(t0 + dt_s, 9)
        if self.state.cpu_hung and self.state.hung_since_s is not None:
            if (self.state.time_s - self.state.hung_since_s >= self.config.watchdog_timeout_s and
                    not self._fault_is(Fault.WATCHDOG_FAILURE)):
                self.state.cpu_hung = False
                self.state.hung_since_s = None
                self.state.mode = Mode.SAFE
                self._event('watchdog_recovered', mode=Mode.SAFE.value)
        _, voltage, _ = self._electrical()
        if (self.state.mode not in (Mode.BOOT, Mode.SAFE) and
                (voltage < self.config.minimum_bus_voltage_v or
                 self.state.temperature_c > self.config.max_temperature_c)):
            cause = 'LOW_VOLTAGE' if voltage < self.config.minimum_bus_voltage_v else 'OVERHEAT'
            self.state.mode = Mode.SAFE
            self._event('autonomous_safe_mode', cause=cause)

    def telemetry(self, *, sunlit: bool = True) -> dict[str, Any]:
        """Only externally visible signals, with no latent fault labels."""
        load, voltage, current = self._electrical()
        t1 = self.state.temperature_c + self._rng.gauss(0, 0.10)
        t2 = self.state.temperature_c + self._rng.gauss(0, 0.10)
        if self._fault_is(Fault.SENSOR_STUCK):
            if self._stuck_temperature_c is None:
                self._stuck_temperature_c = t2
            t2 = self._stuck_temperature_c
        else:
            self._stuck_temperature_c = None
        link_up = self.state.mode is Mode.DOWNLINK
        loss = 0.012 if link_up else 0.0
        latency = 80.0 if link_up else 0.0
        checksum = True
        if link_up:
            if self._fault_is(Fault.PACKET_LOSS):
                loss += min(0.95 - loss, 0.40 * self._fault.severity)
            if self._fault_is(Fault.LATE_TELEMETRY):
                latency += 560.0 * self._fault.severity
            if self._fault_is(Fault.CORRUPT_PACKET):
                checksum = False
        # Demonstration alarms are separately defined from the test policy.
        alarms = []
        if voltage < self.config.minimum_bus_voltage_v:
            alarms.append('EPS_UNDERVOLTAGE')
        if current > self.config.max_bus_current_a:
            alarms.append('EPS_OVERCURRENT')
        if t1 > self.config.max_temperature_c:
            alarms.append('THERMAL_OVERLIMIT')
        if abs(t1 - t2) > 3.0:
            alarms.append('SENSOR_DISAGREEMENT')
        if link_up and (loss > 0.10 or latency > 250 or not checksum):
            alarms.append('COMMS_DEGRADED')
        if self.state.cpu_hung and self.state.hung_since_s is not None:
            if self.state.time_s - self.state.hung_since_s >= self.config.watchdog_timeout_s:
                alarms.append('WATCHDOG_TIMEOUT')
        obs = {
            'time_s': round(self.state.time_s, 5),
            'mode': self.state.mode.value,
            'battery_soc_pct': round(100 * self.state.soc, 3),
            'bus_voltage_v': round(voltage, 3),
            'bus_current_a': round(current, 3),
            'load_w': round(load, 3),
            'solar_w': round(self.config.solar_array_w * self.config.charge_efficiency if sunlit else 0, 3),
            'temperature_c': round(t1, 3),
            'redundant_temperature_c': round(t2, 3),
            'packet_loss_fraction': round(loss, 3),
            'latency_ms': round(latency, 1),
            'checksum_ok': checksum,
            'cpu_responsive': not self.state.cpu_hung,
            'alarms': alarms,
        }
        self._last_alarm_codes = alarms
        return obs


def _default_commands() -> list[tuple[int, Mode]]:
    return [(0, Mode.SAFE), (60, Mode.NOMINAL), (180, Mode.PAYLOAD),
            (360, Mode.DOWNLINK), (900, Mode.SAFE), (960, Mode.DOWNLINK),
            (1020, Mode.NOMINAL), (1140, Mode.PAYLOAD), (1260, Mode.DOWNLINK),
            (1800, Mode.SAFE), (1860, Mode.NOMINAL), (1980, Mode.PAYLOAD)]


def run_scenario(*, fault: Fault | str = Fault.NONE, severity: float = 1.0,
                 fault_start_s: float = 600.0, duration_s: int = 3000,
                 step_s: int = 30, sunlit: bool = True, seed: int = 7,
                 initial_soc: float = 0.8,
                 commands: list[tuple[int, Mode]] | None = None,
                 probe_watchdog: bool = True) -> dict[str, Any]:
    """Execute a reproducible experiment. JSON-ready result for CLI and web API.

    Events run at sample boundaries: duration, fault onset, and commands should
    be multiples of step_s; this is checked to avoid hidden event-time drift.
    """
    fault = Fault(fault)
    if not (isinstance(duration_s, int) and isinstance(step_s, int)):
        raise ValueError('duration and step must be integers in seconds')
    if duration_s < 1 or step_s < 1 or duration_s % step_s or duration_s > 86400:
        raise ValueError('duration must be a positive step multiple and <= 86400 s')
    if fault_start_s % step_s:
        raise ValueError('fault_start_s must lie on a simulation step boundary')
    if not 0 <= initial_soc <= 1:
        raise ValueError('initial SOC must lie in [0, 1]')
    schedule = _default_commands() if commands is None else commands
    grouped: dict[int, list[Mode]] = {}
    for t, mode in schedule:
        if int(t) != t or t < 0 or t % step_s:
            raise ValueError('command times must be nonnegative step-aligned integers')
        grouped.setdefault(int(t), []).append(Mode(mode))
    sim = DynamicSpacecraft(
        DynamicsConfig(initial_soc=initial_soc),
        FaultInjection(fault, fault_start_s, severity), seed=seed)
    timeline: list[dict[str, Any]] = []
    for t in range(0, duration_s + 1, step_s):
        if probe_watchdog and t == 1500:
            sim.trigger_cpu_hang()
        for mode in grouped.get(t, []):
            sim.command(mode)
        timeline.append(sim.telemetry(sunlit=sunlit))
        if t < duration_s:
            sim.step(step_s, sunlit=sunlit)
    alerts = [(p['time_s'], alarm) for p in timeline for alarm in p['alarms']]
    faults = [e for e in sim.events if e['type'] in (
        'guard_violation', 'payload_enable_failure', 'autonomous_safe_mode')]
    first_alarm = alerts[0][0] if alerts else None
    evidence_times = [t for t, _ in alerts] + [e['time_s'] for e in sim.events
                    if e['type'] in ('guard_violation', 'payload_enable_failure')]
    first_evidence = min(evidence_times) if evidence_times else None
    return {
        'meta': {'version': '0.2', 'fault': fault.value, 'fault_start_s': fault_start_s,
                 'severity': severity, 'duration_s': duration_s, 'step_s': step_s,
                 'sunlit': sunlit, 'seed': seed, 'initial_soc': initial_soc,
                 'limitations': 'Synthetic physics and faults; not flight-validated.'},
        'telemetry': timeline, 'events': sim.events,
        'summary': {
            'samples': len(timeline), 'first_alarm_s': first_alarm,
            'first_evidence_s': first_evidence,
            'distinct_alarms': sorted(set(x[1] for x in alerts)),
            'autonomous_safe_entries': sum(e['type'] == 'autonomous_safe_mode' for e in sim.events),
            'command_rejections': sum(e['type'] == 'command' and not e['accepted'] for e in sim.events),
            'guard_violations': sum(e['type'] == 'guard_violation' for e in sim.events),
            'watchdog_recoveries': sum(e['type'] == 'watchdog_recovered' for e in sim.events),
            'minimum_soc_pct': round(min(p['battery_soc_pct'] for p in timeline), 3),
            'maximum_temp_c': round(max(p['temperature_c'] for p in timeline), 3),
            'incident_count': len(faults),
        },
    }
