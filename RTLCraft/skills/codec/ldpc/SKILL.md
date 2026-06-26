# ldpc — LDPC Decoder Design Skill

## Overview

WiMax 802.16e LDPC decoder using the Min-Sum algorithm.
One decoding iteration per clock cycle, with parity-check termination.

Reference RTL: `ref_rtl/LDPC_Decoder` (Fudan University VIPcore).

## Modules

| File | Description |
|------|-------------|
| `behaviors.py` | Cycle-accurate templates for 6 PE types (quantized_adder, quantized_subber, comparator, check_node, var_node, ldpc_decoder) |
| `models.py` | CheckNode_Model, VarNode_Model, LDPCDecoder_Model, minsum_decode golden reference |
| `arch_templates.py` | build_ldpc_arch(), build_ldpc_params() — parameterizable architecture builder |
| `skeleton_templates.py` | PE type → implementation steps (6 PE types) |

## Quick Start

### Low-level Flow

```python
from skills.codec.ldpc.arch_templates import build_ldpc_arch, build_ldpc_params
from skills.codec.ldpc.models import minsum_decode

# Build parameters from WiMax base matrix
params = build_ldpc_params(Hbm, z=1)  # z=1 → n=24, m=12
arch = build_ldpc_arch(n=params["n"], m=params["m"], prec=4, iter_max=25,
                       vn_degrees=params["vn_degrees"], cn_degrees=params["cn_degrees"])
```

### Golden Reference Verification

```python
from skills.codec.ldpc.models import minsum_decode, LDPCDecoder_Model

# Pure Python Min-Sum decoder
P_v, x, num_iter, converged = minsum_decode(llr_list, H, max_iter=25, prec=4)

# Cycle-accurate model
model = LDPCDecoder_Model(H=H, prec=4, max_iter=25)
model.load_llrs(llr_list)
for _ in range(30):
    if model.cycle():
        break
```

## LDPC Pipeline Stages

| Stage | pe_type | Description |
|-------|---------|-------------|
| QuantizedAdder | quantized_adder | Saturating signed adder (combinational, prec+1 bit internal) |
| QuantizedSubber | quantized_subber | Saturating signed subtractor (combinational) |
| Comparator | comparator | Min/second-min tree node (combinational) |
| CheckNode | check_node | Min-Sum check node: sign XOR tree + comparator tree + registered R |
| VarNode | var_node | Variable node: adder tree for sum_R, P_v=llr+sum_R, Q_i=P_v-R_i |
| LDPC_Decoder | ldpc_decoder | Top-level: VN/CN instantiation, interconnect, iteration counter, parity check |

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| N | 24 | Number of variable nodes (code length = n_b * z) |
| M | 12 | Number of check nodes (parity constraints = m_b * z) |
| z | 1 | Expansion factor (24 → full WiMax n=576) |
| prec | 4 | Message bit precision (signed) |
| ITER_MAX | 25 | Maximum decoding iterations |

## Algorithm

One Min-Sum iteration per clock cycle:

1. **CheckNode**: For each check node c:
   - Extract |Q| and sign from each connected variable node
   - Find min and second-min of |Q| via comparator tree
   - Compute sign_product = XOR of all Q signs
   - R_i = (sign_product ⊕ Q_sign_i) ? -min : min (use second_min if |Q_i| == min)

2. **VarNode**: For each variable node v:
   - sum_R = saturating_add_tree(R_0, R_1, ..., R_{d_v-1})
   - P_v = saturate(sum_R + llr)
   - Q_i = saturate(P_v - R_i) for each connected check node
   - x = P_v[prec-1] (hard decision bit)

3. **Control**: 
   - Count iterations
   - Parity check: for each CN, XOR of connected x bits should be 0
   - Done when ITER_MAX or all parity checks pass

## Saturation Arithmetic

All arithmetic uses (prec)-bit signed saturation:
- pmax = (1 << (prec-1)) - 1  (e.g., 7 for prec=4)
- pmin = -(1 << (prec-1))     (e.g., -8 for prec=4)
- Overflow clips to pmax/pmin

**Note**: The reference RTL uses saturating add after each pairwise addition (tree-style),
which differs slightly from summing all values then saturating once. This is intentional
and matches the hardware implementation.
