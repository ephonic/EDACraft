"""
PyTorch FX -> NeuralAccel NPU IR Lowering

Converts a PyTorch model (via torch.fx) into the NPU intermediate representation.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from typing import Dict, Any, Optional, Callable
import torch
import torch.nn as nn
from torch.fx import symbolic_trace, Node

from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.compiler.im2col import im2col_input, im2col_weight, conv2d_output_shape
from skills.cpu.npu.compiler.ir import (
    NPUGraph, NPUTensor, GemmOp, VecALUOp, SFUOp,
    LoadOp, StoreOp, CrossbarOp, SyncOp, Im2ColOp, PoolOp,
    VecALUFunc, SFUFunc, DataType,
)


# ---------------------------------------------------------------------------
# PyTorch -> NPU operator mapping
# ---------------------------------------------------------------------------

_VEC_ALU_MAP: Dict[str, VecALUFunc] = {
    "add": VecALUFunc.ADD,
    "sub": VecALUFunc.SUB,
    "mul": VecALUFunc.MUL,
    "relu": VecALUFunc.RELU,
}

_SFU_MAP: Dict[str, SFUFunc] = {
    "sigmoid": SFUFunc.SIGMOID,
    "tanh": SFUFunc.TANH,
}


def _get_tensor_shape(node: Node) -> tuple:
    """Extract shape from FX node metadata if available."""
    if hasattr(node, "meta") and "tensor_meta" in node.meta:
        return tuple(node.meta["tensor_meta"].shape)
    # Fallback: try to infer from example value
    if hasattr(node, "meta") and "example_value" in node.meta:
        val = node.meta["example_value"]
        if isinstance(val, torch.Tensor):
            return tuple(val.shape)
    return ()


def _make_tensor(name: str, shape: tuple, dtype: DataType = DataType.INT16) -> NPUTensor:
    return NPUTensor(name=name, shape=shape, dtype=dtype)


class NPULowering:
    """Lowers a PyTorch FX GraphModule into NPU IR."""

    def __init__(self, model: nn.Module, example_input: Optional[torch.Tensor] = None,
                 params: Optional[NeuralAccelParams] = None):
        self.model = model
        self.example_input = example_input
        self.params = params if params is not None else NeuralAccelParams()
        self.graph = NPUGraph(name=getattr(model, "_get_name", lambda: "model")())
        self._node_to_tensor: Dict[str, NPUTensor] = {}
        self._param_tensors: Dict[str, torch.Tensor] = {}

    def lower(self) -> NPUGraph:
        """Run lowering and return NPU IR graph."""
        # Symbolic trace the model
        self.gm = symbolic_trace(self.model)

        if self.example_input is not None:
            # Propagate shapes through the graph
            try:
                from torch.fx.passes.shape_prop import ShapeProp
                ShapeProp(self.gm).propagate(self.example_input)
            except Exception:
                # Fallback: just run the model
                with torch.no_grad():
                    self.gm(self.example_input)

        # Collect parameters
        for name, param in self.gm.named_parameters():
            self._param_tensors[name] = param.detach()

        # Convert FX nodes to NPU ops
        for node in self.gm.graph.nodes:
            self._lower_node(node)

        return self.graph

    def _get_or_create_tensor(self, node: Node) -> NPUTensor:
        """Get existing tensor or create new one for FX node."""
        name = node.name
        if name in self._node_to_tensor:
            return self._node_to_tensor[name]
        shape = _get_tensor_shape(node)
        tensor = _make_tensor(name, shape)
        self._node_to_tensor[name] = tensor
        return tensor

    def _lower_node(self, node: Node):
        """Lower a single FX node to NPU IR ops."""
        if node.op == "placeholder":
            # Model input
            tensor = self._get_or_create_tensor(node)
            # Insert LoadOp to bring input into SRAM
            load_op = LoadOp(name=f"load_{node.name}", src=tensor, dst=tensor)
            self.graph.add_op(load_op)

        elif node.op == "output":
            # Model output: store final tensors to DRAM
            for arg in node.args[0] if isinstance(node.args[0], (list, tuple)) else [node.args[0]]:
                if isinstance(arg, Node):
                    tensor = self._get_or_create_tensor(arg)
                    store_op = StoreOp(name=f"store_{arg.name}", src=tensor, dst=tensor)
                    self.graph.add_op(store_op)

        elif node.op == "call_module":
            self._lower_call_module(node)

        elif node.op == "call_function":
            self._lower_call_function(node)

        elif node.op == "get_attr":
            # Parameter access (weight/bias) — handled in call_module
            pass

    def _lower_call_module(self, node: Node):
        """Lower a call_module FX node."""
        target = str(node.target)
        module = self.model.get_submodule(target)

        # Input tensor
        input_node = node.args[0]
        input_tensor = self._get_or_create_tensor(input_node)

        # Output tensor
        output_tensor = self._get_or_create_tensor(node)

        if isinstance(module, nn.Linear):
            self._lower_linear(node, module, input_tensor, output_tensor)

        elif isinstance(module, nn.ReLU):
            op = VecALUOp(
                name=f"relu_{node.name}",
                func=VecALUFunc.RELU,
                inputs=[input_tensor],
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif isinstance(module, nn.Sigmoid):
            op = SFUOp(
                name=f"sigmoid_{node.name}",
                func=SFUFunc.SIGMOID,
                input_t=input_tensor,
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif isinstance(module, nn.Tanh):
            op = SFUOp(
                name=f"tanh_{node.name}",
                func=SFUFunc.TANH,
                input_t=input_tensor,
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif isinstance(module, nn.Conv2d):
            self._lower_conv2d(node, module, input_tensor, output_tensor)

        elif isinstance(module, (nn.MaxPool2d, nn.AvgPool2d, nn.AdaptiveAvgPool2d)):
            self._lower_pool(node, module, input_tensor, output_tensor)

        else:
            raise NotImplementedError(f"Module type {type(module).__name__} not supported for NPU lowering")

    def _lower_linear(self, node: Node, module: nn.Linear,
                      input_tensor: NPUTensor, output_tensor: NPUTensor):
        """Lower nn.Linear to GEMM + optional bias add."""
        in_features = module.in_features
        out_features = module.out_features

        # Weight tensor
        weight_name = f"{node.target}.weight"
        weight_tensor = _make_tensor(
            name=weight_name,
            shape=(out_features, in_features),
        )
        self.graph.tensors[weight_name] = weight_tensor

        # Load weight into SRAM (if not already resident)
        # In a real compiler, weights would be pre-loaded; here we insert a load op
        self.graph.add_op(LoadOp(name=f"load_{weight_name}", src=weight_tensor, dst=weight_tensor))

        # GEMM: output = input @ weight.T
        # For systolic array, we need to think about M, N, K dimensions
        # input shape: (..., in_features), weight shape: (out_features, in_features)
        # output shape: (..., out_features)
        # K = in_features (reduction dim)
        gemm_op = GemmOp(
            name=f"gemm_{node.name}",
            input_a=input_tensor,
            input_b=weight_tensor,
            output=output_tensor,
            k_dim=in_features,
        )
        self.graph.add_op(gemm_op)

        # Bias add (if present)
        if module.bias is not None:
            bias_name = f"{node.target}.bias"
            bias_tensor = _make_tensor(
                name=bias_name,
                shape=(out_features,),
            )
            self.graph.tensors[bias_name] = bias_tensor
            self.graph.add_op(LoadOp(name=f"load_{bias_name}", src=bias_tensor, dst=bias_tensor))

            # Bias add via VecALU ADD
            # Note: bias needs broadcasting. For simplicity, assume outer loop handles it.
            bias_op = VecALUOp(
                name=f"bias_add_{node.name}",
                func=VecALUFunc.ADD,
                inputs=[output_tensor, bias_tensor],
                output=output_tensor,
            )
            self.graph.add_op(bias_op)

    def _lower_conv2d(self, node: Node, module: nn.Conv2d,
                      input_tensor: NPUTensor, output_tensor: NPUTensor):
        """Lower nn.Conv2d to hardware im2col + GEMM + optional bias add.

        If K = in_c*kh*kw > array_size, splits along the K dimension into
        multiple tiles (each K' <= array_size) and accumulates partial sums.
        """
        kh = module.kernel_size[0] if isinstance(module.kernel_size, tuple) else module.kernel_size
        kw = module.kernel_size[1] if isinstance(module.kernel_size, tuple) else module.kernel_size
        stride_h = module.stride[0] if isinstance(module.stride, tuple) else module.stride
        stride_w = module.stride[1] if isinstance(module.stride, tuple) else module.stride
        pad_h = module.padding[0] if isinstance(module.padding, tuple) else module.padding
        pad_w = module.padding[1] if isinstance(module.padding, tuple) else module.padding
        in_c = module.in_channels
        out_c = module.out_channels
        array_size = self.params.ARRAY_SIZE

        # Determine output spatial shape from FX metadata
        input_shape = input_tensor.shape  # may be (N,C,H,W) or (C,H,W)
        conv_out_shape = conv2d_output_shape(input_shape, module.weight.shape,
                                               module.stride, module.padding)
        if len(input_shape) == 3:
            out_h, out_w = conv_out_shape[1], conv_out_shape[2]
            in_h = input_shape[1]
            in_w = input_shape[2]
        else:
            out_h, out_w = conv_out_shape[2], conv_out_shape[3]
            in_h = input_shape[2]
            in_w = input_shape[3]

        k_dim = in_c * kh * kw

        if k_dim <= array_size:
            # Single tile: original logic
            im2col_output_shape = (k_dim, out_h * out_w)
            im2col_output_name = f"{node.name}_im2col_out"
            im2col_output_tensor = _make_tensor(
                name=im2col_output_name,
                shape=im2col_output_shape,
            )
            self.graph.tensors[im2col_output_name] = im2col_output_tensor

            im2col_op = Im2ColOp(
                name=f"im2col_{node.name}",
                input_t=input_tensor,
                output=im2col_output_tensor,
                kernel_h=kh,
                kernel_w=kw,
                stride_h=stride_h,
                stride_w=stride_w,
                pad_h=pad_h,
                pad_w=pad_w,
                in_h=in_h,
                in_w=in_w,
                in_c=in_c,
                out_h=out_h,
                out_w=out_w,
            )
            self.graph.add_op(im2col_op)

            weight_name = f"{node.target}.weight"
            weight_2d_shape = (out_c, k_dim)
            weight_tensor = _make_tensor(
                name=weight_name,
                shape=weight_2d_shape,
            )
            self.graph.tensors[weight_name] = weight_tensor
            self.graph.add_op(LoadOp(name=f"load_{weight_name}", src=weight_tensor, dst=weight_tensor))

            gemm_op = GemmOp(
                name=f"gemm_{node.name}",
                input_a=weight_tensor,
                input_b=im2col_output_tensor,
                output=output_tensor,
                k_dim=k_dim,
            )
            self.graph.add_op(gemm_op)
        else:
            # K-tiling: split in_c into groups so that each group's K' <= array_size
            max_in_c_per_group = array_size // (kh * kw)
            if max_in_c_per_group == 0:
                max_in_c_per_group = 1  # Fallback for very large kernels
            num_groups = (in_c + max_in_c_per_group - 1) // max_in_c_per_group

            accum_tensor = None

            for group_idx in range(num_groups):
                in_c_start = group_idx * max_in_c_per_group
                in_c_end = min(in_c, in_c_start + max_in_c_per_group)
                group_in_c = in_c_end - in_c_start
                group_k_dim = group_in_c * kh * kw

                # Group input tensor (shares data with original input, different view)
                group_input_name = f"{node.name}_input_g{group_idx}"
                if len(input_shape) == 3:
                    group_input_shape = (group_in_c, in_h, in_w)
                else:
                    group_input_shape = (input_shape[0], group_in_c, in_h, in_w)
                group_input_tensor = _make_tensor(
                    name=group_input_name,
                    shape=group_input_shape,
                )
                self.graph.tensors[group_input_name] = group_input_tensor

                # Group im2col output
                group_im2col_shape = (group_k_dim, out_h * out_w)
                group_im2col_name = f"{node.name}_im2col_g{group_idx}"
                group_im2col_tensor = _make_tensor(
                    name=group_im2col_name,
                    shape=group_im2col_shape,
                )
                self.graph.tensors[group_im2col_name] = group_im2col_tensor

                im2col_op = Im2ColOp(
                    name=f"im2col_{node.name}_g{group_idx}",
                    input_t=group_input_tensor,
                    output=group_im2col_tensor,
                    kernel_h=kh,
                    kernel_w=kw,
                    stride_h=stride_h,
                    stride_w=stride_w,
                    pad_h=pad_h,
                    pad_w=pad_w,
                    in_h=in_h,
                    in_w=in_w,
                    in_c=group_in_c,
                    out_h=out_h,
                    out_w=out_w,
                )
                self.graph.add_op(im2col_op)

                # Group weight tensor
                group_weight_name = f"{node.target}.weight_g{group_idx}"
                group_weight_shape = (out_c, group_k_dim)
                group_weight_tensor = _make_tensor(
                    name=group_weight_name,
                    shape=group_weight_shape,
                )
                self.graph.tensors[group_weight_name] = group_weight_tensor
                self.graph.add_op(LoadOp(name=f"load_{group_weight_name}", src=group_weight_tensor, dst=group_weight_tensor))

                # Group GEMM output (accumulate into main output)
                if group_idx == 0:
                    group_gemm_output = output_tensor
                else:
                    group_gemm_output = _make_tensor(
                        name=f"{node.name}_gemm_out_g{group_idx}",
                        shape=(out_c, out_h * out_w),
                    )
                    self.graph.tensors[group_gemm_output.name] = group_gemm_output

                gemm_op = GemmOp(
                    name=f"gemm_{node.name}_g{group_idx}",
                    input_a=group_weight_tensor,
                    input_b=group_im2col_tensor,
                    output=group_gemm_output,
                    k_dim=group_k_dim,
                )
                self.graph.add_op(gemm_op)

                # Accumulate partial sums
                if group_idx > 0:
                    add_op = VecALUOp(
                        name=f"accum_{node.name}_g{group_idx}",
                        func=VecALUFunc.ADD,
                        inputs=[output_tensor, group_gemm_output],
                        output=output_tensor,
                    )
                    self.graph.add_op(add_op)

        # Bias add (if present) — applied once after all K-tiles
        if module.bias is not None:
            bias_name = f"{node.target}.bias"
            bias_tensor = _make_tensor(
                name=bias_name,
                shape=(out_c,),
            )
            self.graph.tensors[bias_name] = bias_tensor
            self.graph.add_op(LoadOp(name=f"load_{bias_name}", src=bias_tensor, dst=bias_tensor))

            bias_op = VecALUOp(
                name=f"bias_add_{node.name}",
                func=VecALUFunc.ADD,
                inputs=[output_tensor, bias_tensor],
                output=output_tensor,
            )
            self.graph.add_op(bias_op)

    def _lower_pool(self, node: Node, module: nn.Module,
                    input_tensor: NPUTensor, output_tensor: NPUTensor):
        """Lower nn.MaxPool2d / nn.AvgPool2d / nn.AdaptiveAvgPool2d to PoolOp."""
        input_shape = input_tensor.shape
        output_shape = output_tensor.shape

        if len(input_shape) == 3:
            in_c, in_h, in_w = input_shape
        else:
            in_c, in_h, in_w = input_shape[1], input_shape[2], input_shape[3]

        if len(output_shape) == 3:
            out_c, out_h, out_w = output_shape
        else:
            out_c, out_h, out_w = output_shape[1], output_shape[2], output_shape[3]

        if isinstance(module, nn.MaxPool2d):
            pool_type = "MAX"
            kh = module.kernel_size if isinstance(module.kernel_size, int) else module.kernel_size[0]
            kw = module.kernel_size if isinstance(module.kernel_size, int) else module.kernel_size[1]
            stride_h = module.stride if isinstance(module.stride, int) else module.stride[0]
            stride_w = module.stride if isinstance(module.stride, int) else module.stride[1]
            pad_h = module.padding if isinstance(module.padding, int) else module.padding[0]
            pad_w = module.padding if isinstance(module.padding, int) else module.padding[1]
            div_shift = 0
        elif isinstance(module, nn.AvgPool2d):
            pool_type = "AVG"
            kh = module.kernel_size if isinstance(module.kernel_size, int) else module.kernel_size[0]
            kw = module.kernel_size if isinstance(module.kernel_size, int) else module.kernel_size[1]
            stride_h = module.stride if isinstance(module.stride, int) else module.stride[0]
            stride_w = module.stride if isinstance(module.stride, int) else module.stride[1]
            pad_h = module.padding if isinstance(module.padding, int) else module.padding[0]
            pad_w = module.padding if isinstance(module.padding, int) else module.padding[1]
            window_size = kh * kw
            div_shift = int(window_size.bit_length()) - 1  # floor(log2(window_size))
        elif isinstance(module, nn.AdaptiveAvgPool2d):
            pool_type = "AVG"
            # AdaptiveAvgPool: output size is fixed, kernel covers entire input
            kh = in_h
            kw = in_w
            stride_h = in_h
            stride_w = in_w
            pad_h = 0
            pad_w = 0
            window_size = kh * kw
            div_shift = int(window_size.bit_length()) - 1
        else:
            return

        pool_op = PoolOp(
            name=f"pool_{node.name}",
            input_t=input_tensor,
            output=output_tensor,
            pool_type=pool_type,
            kernel_h=kh,
            kernel_w=kw,
            stride_h=stride_h,
            stride_w=stride_w,
            pad_h=pad_h,
            pad_w=pad_w,
            in_h=in_h,
            in_w=in_w,
            in_c=in_c,
            out_h=out_h,
            out_w=out_w,
            div_shift=div_shift,
        )
        self.graph.add_op(pool_op)

    def _get_attr_tensor(self, node: Node) -> torch.Tensor:
        """Get tensor value from a get_attr FX node."""
        assert node.op == "get_attr"
        target = str(node.target)
        # Navigate through nested modules/attributes
        parts = target.split(".")
        obj = self.gm
        for part in parts:
            obj = getattr(obj, part)
        return obj.detach()

    def _lower_call_function(self, node: Node):
        """Lower a call_function FX node (torch.add, torch.relu, etc.)."""
        target_name = node.target.__name__ if hasattr(node.target, "__name__") else str(node.target)

        # Gather input tensors
        input_tensors = []
        for arg in node.args:
            if isinstance(arg, Node):
                input_tensors.append(self._get_or_create_tensor(arg))

        output_tensor = self._get_or_create_tensor(node)

        if target_name == "linear":
            self._lower_fx_linear(node, input_tensors, output_tensor)

        elif target_name in ("add", "radd"):
            op = VecALUOp(
                name=f"add_{node.name}",
                func=VecALUFunc.ADD,
                inputs=input_tensors,
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif target_name in ("mul", "rmul"):
            op = VecALUOp(
                name=f"mul_{node.name}",
                func=VecALUFunc.MUL,
                inputs=input_tensors,
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif target_name == "relu":
            op = VecALUOp(
                name=f"relu_{node.name}",
                func=VecALUFunc.RELU,
                inputs=input_tensors,
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif target_name == "sigmoid":
            op = SFUOp(
                name=f"sigmoid_{node.name}",
                func=SFUFunc.SIGMOID,
                input_t=input_tensors[0],
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif target_name == "tanh":
            op = SFUOp(
                name=f"tanh_{node.name}",
                func=SFUFunc.TANH,
                input_t=input_tensors[0],
                output=output_tensor,
            )
            self.graph.add_op(op)

        elif target_name == "flatten":
            # Placeholder: reshape only, no compute needed.
            pass

        else:
            raise NotImplementedError(f"Function {target_name} not supported for NPU lowering")

    def _lower_fx_linear(self, node: Node, input_tensors: list, output_tensor: NPUTensor):
        """Lower torch.nn.functional.linear to GEMM + bias."""
        # args: (input, weight, bias)
        input_t = input_tensors[0] if input_tensors else _make_tensor("input", ())

        # Extract weight from args[1] (get_attr node)
        weight_node = node.args[1] if len(node.args) > 1 else None
        if isinstance(weight_node, Node) and weight_node.op == "get_attr":
            weight_val = self._get_attr_tensor(weight_node)
            out_features, in_features = weight_val.shape
            weight_name = weight_node.name
        else:
            weight_name = f"{node.name}_weight"
            in_features = 0
            out_features = 0

        weight_tensor = _make_tensor(name=weight_name, shape=(out_features, in_features))
        self.graph.tensors[weight_name] = weight_tensor
        self.graph.add_op(LoadOp(name=f"load_{weight_name}", src=weight_tensor, dst=weight_tensor))

        # GEMM
        gemm_op = GemmOp(
            name=f"gemm_{node.name}",
            input_a=input_t,
            input_b=weight_tensor,
            output=output_tensor,
            k_dim=in_features,
        )
        self.graph.add_op(gemm_op)

        # Bias (optional)
        if len(node.args) > 2 and node.args[2] is not None:
            bias_node = node.args[2]
            if isinstance(bias_node, Node) and bias_node.op == "get_attr":
                bias_name = bias_node.name
            else:
                bias_name = f"{node.name}_bias"
            bias_tensor = _make_tensor(name=bias_name, shape=(out_features,))
            self.graph.tensors[bias_name] = bias_tensor
            self.graph.add_op(LoadOp(name=f"load_{bias_name}", src=bias_tensor, dst=bias_tensor))

            bias_op = VecALUOp(
                name=f"bias_add_{node.name}",
                func=VecALUFunc.ADD,
                inputs=[output_tensor, bias_tensor],
                output=output_tensor,
            )
            self.graph.add_op(bias_op)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _fuse_conv_bn(model: nn.Module) -> nn.Module:
    """Fuse Conv2d + BatchNorm2d patterns in FX graph."""
    from torch.fx import symbolic_trace
    traced = symbolic_trace(model)
    graph = traced.graph
    nodes_to_remove = []
    for node in graph.nodes:
        if node.op == 'call_module' and isinstance(traced.get_submodule(node.target), nn.Conv2d):
            if len(node.users) == 1:
                bn_node = list(node.users)[0]
                if bn_node.op == 'call_module' and isinstance(traced.get_submodule(bn_node.target), nn.BatchNorm2d):
                    conv = traced.get_submodule(node.target)
                    bn = traced.get_submodule(bn_node.target)
                    with torch.no_grad():
                        mean = bn.running_mean
                        var = bn.running_var
                        eps = bn.eps
                        gamma = bn.weight
                        beta = bn.bias
                        scale = gamma / torch.sqrt(var + eps)
                        new_weight = conv.weight.clone() * scale.view(-1, 1, 1, 1)
                        old_bias = conv.bias if conv.bias is not None else torch.zeros(conv.out_channels, device=conv.weight.device, dtype=conv.weight.dtype)
                        new_bias = (old_bias - mean) * scale + beta
                        conv.weight.data = new_weight
                        if conv.bias is None:
                            conv.bias = nn.Parameter(new_bias)
                        else:
                            conv.bias.data = new_bias
                    bn_node.replace_all_uses_with(node)
                    nodes_to_remove.append(bn_node)
    for n in nodes_to_remove:
        graph.erase_node(n)
    return torch.fx.GraphModule(traced, graph)


def lower_model(model: nn.Module, example_input: Optional[torch.Tensor] = None,
                params: Optional[NeuralAccelParams] = None) -> NPUGraph:
    """Lower a PyTorch model to NPU IR.

    Args:
        model: PyTorch nn.Module to lower.
        example_input: Optional example input for tracing and shape inference.
        params: NeuralAccelParams defining hardware specs.

    Returns:
        NPUGraph representing the lowered computation.
    """
    # Fuse Conv+BN before lowering
    model = _fuse_conv_bn(model)
    lowering = NPULowering(model, example_input, params)
    return lowering.lower()
