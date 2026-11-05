"""Physics sub-package: invariants, unit checks, and guards."""
from .invariants import PhysicsInvariants, PhysicsViolation
from .reliability import CyclingDegradation, TrapKinetics
from .ferro_kinetics import (
    AvramiDomainSwitching,
    FieldHistoryCyclingState,
    KaiMultiDomain,
    simulate_kai_waveform,
)
from .electron_counting import BirthDeathChain, GillespieSampler
from .storage_readout import (
    StorageReadout, channel_metrics, decode_distributions, electron_storage_readout,
)
from .nc_verdict import (
    LKCircuitModel,
    measure_pulse_dip,
    nc_verdict,
    run_pulse_protocol,
    run_triangular_sweep,
)
from .contact import (
    SchottkyContactModel,
    WSe2CompactContactModel,
    WSe2TransportWindow,
    WSe2TwoWindowTransferModel,
)

__all__ = [
    "PhysicsInvariants", "PhysicsViolation", "TrapKinetics",
    "CyclingDegradation",
    "FieldHistoryCyclingState", "AvramiDomainSwitching",
    "KaiMultiDomain", "simulate_kai_waveform",
    "BirthDeathChain", "GillespieSampler",
    "StorageReadout", "channel_metrics", "decode_distributions", "electron_storage_readout",
    "LKCircuitModel", "measure_pulse_dip", "nc_verdict",
    "run_pulse_protocol", "run_triangular_sweep",
    "SchottkyContactModel", "WSe2CompactContactModel",
    "WSe2TransportWindow", "WSe2TwoWindowTransferModel",
]
