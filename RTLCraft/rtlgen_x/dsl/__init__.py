"""DSL capability surface for rtlgen_x."""

from rtlgen_x.dsl.adapter import (
    LegacyLoweringError,
    LegacyLoweringReport,
    LoweredLegacyModule,
    build_compiled_simulator_from_legacy,
    lower_legacy_module_to_sim,
)
from rtlgen_x.dsl.native import NativeMemory, NativeModuleBuilder, NativeSignal, NativeValue, const, mux
from rtlgen_x.dsl.legacy import *  # noqa: F401,F403
