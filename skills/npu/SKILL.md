# npu — Neural Processing Units

## Overview

AI/ML inference accelerators: systolic arrays, tensor cores, activation engines, and quantization units.

## Status

🚧 **Reserved directory** — Designs will be added in future releases.

## Planned Modules

| Module | Description |
|--------|-------------|
| `SystolicArray` | N×N MAC array with weight-stationary dataflow |
| `TensorCore` | 4×4 or 8×8 matrix multiply accumulate unit |
| `ReLUUnit` | Activation function pipeline (ReLU, LeakyReLU, SiLU) |
| `Quantizer` | INT8 / INT4 post-training quantization engine |
| `SoftmaxEngine` | Numerically stable softmax (max subtract + exp LUT + sum recip) |

## Design Guidelines

- **Systolic arrays** minimize memory bandwidth by keeping weights stationary
- **Bit-width reduction** (FP16 → INT8 → INT4) is the primary area/energy optimization
- **Sparsity** (zero skipping) can provide 2-4× speedup with minimal hardware overhead

## See Also

- `../arithmetic/SKILL.md` — Fixed-point and floating-point ALUs
- `../accelerators/SKILL.md` — Broader accelerator taxonomy
