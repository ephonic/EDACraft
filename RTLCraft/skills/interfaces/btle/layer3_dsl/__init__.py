"""skills.interfaces.btle.layer3_dsl — DSL Module Implementations"""
from __future__ import annotations
import os, sys, math
from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
    Protocol_Model, datapath_template,
)
from rtlgen.core import (
    Module, Input, Output, Wire, Reg, Array, Const,
    Memory, Parameter, LocalParam,
)
from rtlgen import Cat, Rep, Mux
from rtlgen.logic import If, Else, Switch, ForGen, GenIf, GenElse
from rtlgen.codegen import VerilogEmitter, EmitProfile, ModuleDocTemplate, fill_doc_template
from rtlgen.ppa_optimizer import PPAOptimizer, SpecIR
from .crc24_core import CRC24_CORE
from .scramble_core import SCRAMBLE_CORE
from .search_unique_bit_seq import SEARCH_UNIQUE_BIT_SEQ
from .gfsk_demodulation import GFSK_DEMODULATION
from .gauss_filter import GAUSS_FILTER
from .bit_repeat_upsample import BIT_REPEAT_UPSAMPLE
from .sdpram_one_clk import SDPRAM_ONE_CLK
from .sdpram_two_clk import SDPRAM_TWO_CLK
from .crc24 import CRC24
from .scramble import SCRAMBLE
from .vco import VCO
from .gfsk_modulation import GFSK_MODULATION
from .btle_rx_core import BTLE_RX_CORE
from .btle_tx import BTLE_TX
from .btle_phy import BTLE_PHY

__all__ = [
    "CRC24_CORE",
    "SCRAMBLE_CORE",
    "SEARCH_UNIQUE_BIT_SEQ",
    "GFSK_DEMODULATION",
    "GAUSS_FILTER",
    "BIT_REPEAT_UPSAMPLE",
    "SDPRAM_ONE_CLK",
    "SDPRAM_TWO_CLK",
    "CRC24",
    "SCRAMBLE",
    "VCO",
    "GFSK_MODULATION",
    "BTLE_RX_CORE",
    "BTLE_TX",
    "BTLE_PHY",
]

