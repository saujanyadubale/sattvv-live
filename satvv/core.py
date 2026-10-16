"""Transparent, intentionally simplified spacecraft emulator and test catalog.

Not flight software; sensor values and unit costs are illustrative assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random


class Mode(str, Enum):
    BOOT = 'BOOT'
    SAFE = 'SAFE'
    NOMINAL = 'NOMINAL'
    PAYLOAD = 'PAYLOAD'
    DOWNLINK = 'DOWNLINK'


class Fault(str, Enum):
    NONE = 'none'
    UNDERVOLTAGE = 'undervoltage'
    OVERCURRENT = 'overcurrent'
    THERMAL_RUNAWAY = 'thermal_runaway'
    SENSOR_STUCK = 'sensor_stuck'
    PAYLOAD_BOOT_FAIL = 'payload_boot_fail'
    PACKET_LOSS = 'packet_loss'
    LATE_TELEMETRY = 'late_telemetry'
    WATCHDOG_FAILURE = 'watchdog_failure'
    ILLEGAL_TRANSITION = 'illegal_transition'
    CORRUPT_PACKET = 'corrupt_packet'


# Requirement IDs are local, project-defined; they are not ECSS identifiers.
REQUIREMENTS = {
    'REQ-MODE': 'Commanded legal mode must be reached',
    'REQ-EPS-V': 'Loaded EPS bus >= 6.70 V',
    'REQ-EPS-I': 'Loaded EPS current <= 2.60 A',
    'REQ-THM-T': 'Thermal sensor temperature <= 70 C',
    'REQ-THM-D': 'Redundant thermal sensors differ by <= 3 C',
    'REQ-PAY': 'Payload successfully enables',
    'REQ-COM-L': 'Downlink packet loss fraction <= 0.10',
    'REQ-COM-T': 'Telemetry latency <= 250 ms',
    'REQ-COM-C': 'Downlink checksum valid',
    'REQ-OBC-W': 'Watchdog recovers from injected hang',
    'REQ-OBC-G': 'Illegal SAFE to DOWNLINK transition rejected',
}


@dataclass(frozen=True)
class TestCase:
    id: str
    name: str
    subsystem: str
    target: Mode
    cost: int  # synthetic execution-time units; NOT measured seconds
    checks: tuple[str, ...]
    load: float = 1.0
    thermal_soak: bool = False
    exercise_link: bool = False
    exercise_watchdog: bool = False
    exercise_guard: bool = False
    criticality: float = 1.0


TESTS = (
    TestCase('T01', 'Boot to safe health', 'OBC', Mode.SAFE, 1, ('REQ-MODE', 'REQ-EPS-V')),
    TestCase('T02', 'Safe to nominal', 'OBC', Mode.NOMINAL, 1, ('REQ-MODE',)),
    TestCase('T03', 'Nominal EPS load', 'EPS', Mode.NOMINAL, 3, ('REQ-EPS-V', 'REQ-EPS-I'), load=3.0, criticality=1.5),
    TestCase('T04', 'Payload power-up', 'PAYLOAD', Mode.PAYLOAD, 2, ('REQ-MODE', 'REQ-PAY'), load=2.0, criticality=1.6),
    TestCase('T05', 'Downlink packet test', 'COMMS', Mode.DOWNLINK, 3, ('REQ-COM-L', 'REQ-COM-T', 'REQ-COM-C'), load=2.0, exercise_link=True, criticality=1.8),
    TestCase('T06', 'Payload thermal soak', 'THERMAL', Mode.PAYLOAD, 4, ('REQ-THM-T',), load=2.0, thermal_soak=True, criticality=1.3),
    TestCase('T07', 'Peak-load EPS check', 'EPS', Mode.PAYLOAD, 4, ('REQ-EPS-V', 'REQ-EPS-I'), load=4.0, criticality=1.5),
    TestCase('T08', 'Link retry and checksum', 'COMMS', Mode.DOWNLINK, 4, ('REQ-COM-L', 'REQ-COM-T', 'REQ-COM-C'), exercise_link=True, criticality=1.4),
    TestCase('T09', 'Payload cycle', 'PAYLOAD', Mode.PAYLOAD, 3, ('REQ-MODE', 'REQ-PAY'), criticality=1.1),
    TestCase('T10', 'Watchdog recovery', 'OBC', Mode.NOMINAL, 3, ('REQ-OBC-W',), exercise_watchdog=True, criticality=1.7),
    TestCase('T11', 'Sensor cross-check', 'THERMAL', Mode.NOMINAL, 3, ('REQ-THM-D',), criticality=1.3),
    TestCase('T12', 'Illegal transition guard', 'OBC', Mode.SAFE, 2, ('REQ-OBC-G',), exercise_guard=True, criticality=1.8),
)


@dataclass
class Observation:
    test_id: str
    mode: str
    transitions: tuple[str, ...]
    telemetry: dict[str, float | bool]
    results: dict[str, bool]

    @property
    def detected(self) -> bool:
        return not all(self.results.values())


class SpacecraftEmulator:
    """Independent cold-start per test. The strategy never accesses self.fault."""

    _PATHS = {
        Mode.BOOT: (Mode.BOOT,),
        Mode.SAFE: (Mode.BOOT, Mode.SAFE),
        Mode.NOMINAL: (Mode.BOOT, Mode.SAFE, Mode.NOMINAL),
        Mode.PAYLOAD: (Mode.BOOT, Mode.SAFE, Mode.NOMINAL, Mode.PAYLOAD),
        Mode.DOWNLINK: (Mode.BOOT, Mode.SAFE, Mode.NOMINAL, Mode.PAYLOAD, Mode.DOWNLINK),
    }

    def __init__(self, fault: Fault, seed: int = 0):
        self.fault = fault
        self.rng = random.Random(seed)

    def execute(self, test: TestCase) -> Observation:
        path = self._PATHS[test.target]
        transitions = tuple(f'{a.value}->{b.value}' for a, b in zip(path, path[1:]))
        reached = test.target
        payload_on = test.target in (Mode.PAYLOAD, Mode.DOWNLINK)
        if self.fault == Fault.PAYLOAD_BOOT_FAIL and payload_on:
            reached = Mode.NOMINAL
            payload_on = False
            transitions = tuple(x for x in transitions if not x.endswith('->PAYLOAD') and not x.endswith('->DOWNLINK'))

        loaded = test.load >= 2.0
        voltage = 7.55 - 0.08 * test.load + self.rng.uniform(-0.035, 0.035)
        if self.fault == Fault.UNDERVOLTAGE:
            # A weak *observable* precursor appears at low load; under load it
            # crosses the failure limit. Tests do not see the hidden fault label.
            voltage -= (0.95 if loaded else 0.55)
        current = 0.4 + 0.4 * test.load + self.rng.uniform(-0.025, 0.025)
        if self.fault == Fault.OVERCURRENT and loaded:
            current += 1.7
        temp = 28 + (37 if test.thermal_soak else 0) + self.rng.uniform(-0.5, 0.5)
        if self.fault == Fault.THERMAL_RUNAWAY and test.thermal_soak:
            temp += 28
        temp_secondary = temp + self.rng.uniform(-0.35, 0.35)
        if self.fault == Fault.SENSOR_STUCK and test.id == 'T11':
            temp_secondary = 20.0
        loss = (0.38 if self.fault == Fault.PACKET_LOSS and test.exercise_link else 0.01)
        latency = (670 if self.fault == Fault.LATE_TELEMETRY and test.exercise_link else 80)
        checksum = not (self.fault == Fault.CORRUPT_PACKET and test.exercise_link)
        watchdog_ok = self.fault != Fault.WATCHDOG_FAILURE
        guard_ok = self.fault != Fault.ILLEGAL_TRANSITION

        telemetry: dict[str, float | bool] = {
            'bus_voltage_v': round(voltage, 3),
            'current_a': round(current, 3),
            'temperature_c': round(temp, 3),
            'redundant_temperature_c': round(temp_secondary, 3),
            'packet_loss_fraction': loss,
            'latency_ms': latency,
            'checksum_ok': checksum,
            'payload_on': payload_on,
            'watchdog_recovered': watchdog_ok,
            'guard_rejected_illegal_transition': guard_ok,
        }
        # Only test-specified requirements are assessed. A telemetry reading cannot
        # count as detecting a fault unless its corresponding check was executed.
        assert all(req in REQUIREMENTS for req in test.checks)
        predicates = {
            'REQ-MODE': reached == test.target,
            'REQ-EPS-V': voltage >= 6.70,
            'REQ-EPS-I': current <= 2.60,
            'REQ-THM-T': temp <= 70,
            'REQ-THM-D': abs(temp - temp_secondary) <= 3,
            'REQ-PAY': payload_on,
            'REQ-COM-L': loss <= 0.10,
            'REQ-COM-T': latency <= 250,
            'REQ-COM-C': checksum,
            'REQ-OBC-W': watchdog_ok,
            'REQ-OBC-G': guard_ok,
        }
        results = {req: predicates[req] for req in test.checks}
        return Observation(test.id, reached.value, transitions, telemetry, results)
