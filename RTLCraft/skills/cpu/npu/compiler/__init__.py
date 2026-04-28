"""
NeuralAccel PyTorch Compiler

Provides end-to-end compilation from PyTorch models to NeuralAccel NPU instructions.

Example usage:
    import torch
    from skills.cpu.npu.compiler import compile_model

    model = torch.nn.Sequential(
        torch.nn.Linear(64, 32),
        torch.nn.ReLU(),
        torch.nn.Linear(32, 10),
    )

    instructions, weights = compile_model(model, example_input=torch.randn(1, 64))
    print(instructions.to_asm())
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from typing import Optional, Tuple, Dict, Any
import torch
import torch.nn as nn

from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.compiler.ir import NPUGraph
from skills.cpu.npu.compiler.lowering import lower_model
from skills.cpu.npu.compiler.codegen import NPUCodeGen, compile_graph
from skills.cpu.npu.compiler.layout import convert_weights


class CompiledModel:
    """Result of compiling a PyTorch model for NeuralAccel NPU."""

    def __init__(self, instructions: list, weight_data: dict, graph: NPUGraph,
                 params: NeuralAccelParams = None):
        self.instructions = instructions
        self.weight_data = weight_data
        self.graph = graph
        self._codegen = NPUCodeGen(params)
        self._codegen.instructions = instructions

    def to_binary(self) -> bytes:
        """Return instruction sequence as binary blob."""
        return self._codegen.to_binary()

    def to_asm(self) -> str:
        """Return instruction sequence as human-readable assembly."""
        return self._codegen.to_asm()

    def get_program_load_sequence(self):
        """Return list of (addr, instr) tuples for loading into NPU instruction memory."""
        return list(enumerate(self.instructions))

    def get_program_length(self) -> int:
        """Return number of instructions in the compiled program."""
        return len(self.instructions)


def compile_model(
    model: nn.Module,
    example_input: Optional[torch.Tensor] = None,
    params: Optional[NeuralAccelParams] = None,
) -> CompiledModel:
    """Compile a PyTorch model to NeuralAccel NPU instructions.

    Args:
        model: PyTorch nn.Module to compile.
        example_input: Optional example input for FX tracing and shape inference.
        params: NeuralAccelParams defining hardware specs. Uses enhanced defaults
                if None (array_size=32, sram_depth=8192, num_lanes=32).

    Returns:
        CompiledModel containing instructions, weights, and IR graph.
    """
    if params is None:
        params = NeuralAccelParams()

    # Step 1: Lower PyTorch model to NPU IR
    graph = lower_model(model, example_input, params)

    # Step 2: Compile NPU IR to instructions
    instructions, _ = compile_graph(graph, params)

    # Step 3: Extract and quantize weights
    param_dict = {}
    for name, param in model.named_parameters():
        param_dict[name] = param.detach()
    weight_data = convert_weights(param_dict)

    return CompiledModel(instructions, weight_data, graph, params)


__all__ = [
    "compile_model",
    "CompiledModel",
    "lower_model",
    "compile_graph",
    "convert_weights",
    "NPUGraph",
    "NPUCodeGen",
]
