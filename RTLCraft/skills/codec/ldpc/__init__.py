"""
skills.codec.ldpc — LDPC Decoder Skill

WiMax 802.16e LDPC decoder (Min-Sum algorithm) with Spec2RTL flow.
One Min-Sum iteration per clock cycle, with parity-check termination.

Architecture:
  LDPC_Decoder (top wrapper: llr in → decoded bits out)
    ├── VarNode[N]   — variable nodes (P_v = llr + ΣR, Q_i = P_v - R_i)
    ├── CheckNode[M] — check nodes (min/second-min tree + sign XOR)
    ├── QuantizedAdder  — saturating signed adder (combinational)
    ├── QuantizedSubber — saturating signed subtractor (combinational)
    └── Comparator      — min/second-min tree node (combinational)

Modules:
  - behaviors.py: 6 behavior templates (quantized_adder, quantized_subber,
    comparator, check_node, var_node, ldpc_decoder)
  - models.py: CheckNode_Model, VarNode_Model, LDPCDecoder_Model, minsum_decode
  - arch_templates.py: build_ldpc_arch(), build_ldpc_params()
  - skeleton_templates.py: PE type → implementation steps (6 PE types)
"""

# Register behaviors and skeleton steps at import time
import skills.codec.ldpc.behaviors  # noqa: F401
import skills.codec.ldpc.skeleton_templates  # noqa: F401

from skills.codec.ldpc.models import (
    minsum_decode,
    CheckNode_Model,
    VarNode_Model,
    LDPCDecoder_Model,
)
from skills.codec.ldpc.arch_templates import (
    build_ldpc_arch,
    build_ldpc_params,
)
from skills.codec.ldpc.skeleton_templates import (
    QUANTIZED_ADDER_STEPS,
    QUANTIZED_SUBBER_STEPS,
    COMPARATOR_STEPS,
    CHECK_NODE_STEPS,
    VAR_NODE_STEPS,
    LDPC_DECODER_STEPS,
    register_ldpc_skeleton_steps,
)

from skills.codec.ldpc.dsl_modules import (
    QuantizedAdder,
    QuantizedSubber,
    Comparator,
    CheckNode,
    VarNode,
    LDPC_Decoder,
)

__all__ = [
    "QuantizedAdder", "QuantizedSubber", "Comparator", "CheckNode", "VarNode", "LDPC_Decoder",
    "minsum_decode",
    "CheckNode_Model",
    "VarNode_Model",
    "LDPCDecoder_Model",
    "build_ldpc_arch",
    "build_ldpc_params",
    "QUANTIZED_ADDER_STEPS",
    "QUANTIZED_SUBBER_STEPS",
    "COMPARATOR_STEPS",
    "CHECK_NODE_STEPS",
    "VAR_NODE_STEPS",
    "LDPC_DECODER_STEPS",
    "register_ldpc_skeleton_steps",
]
