"""
NeuralAccel Data Layout and Quantization

Converts PyTorch floating-point tensors to NPU-compatible fixed-point formats.
Supports INT16 quantization with configurable scale factors.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from typing import Dict, Any, Optional
import torch
import numpy as np

from skills.cpu.npu.compiler.ir import NPUTensor, DataType


def quantize_tensor(
    tensor: torch.Tensor,
    dtype: DataType = DataType.INT16,
    scale: Optional[float] = None,
    zero_point: Optional[float] = None,
) -> tuple:
    """Quantize a float tensor to fixed-point.

    Args:
        tensor: PyTorch float tensor.
        dtype: Target data type.
        scale: Optional manual scale factor. If None, computed from tensor range.
        zero_point: Optional zero point. If None, computed from tensor range.

    Returns:
        (quantized_array, scale, zero_point) where quantized_array is a
        numpy array of the quantized values.
    """
    arr = tensor.detach().cpu().numpy()
    min_val = arr.min()
    max_val = arr.max()

    if dtype == DataType.INT16:
        qmin, qmax = -32768, 32767
    elif dtype == DataType.INT32:
        qmin, qmax = -2147483648, 2147483647
    else:
        qmin, qmax = -32768, 32767

    if scale is None:
        # Symmetric quantization around zero
        abs_max = max(abs(min_val), abs(max_val))
        if abs_max < 1e-8:
            scale = 1.0
        else:
            scale = abs_max / qmax

    if zero_point is None:
        zero_point = 0.0

    quantized = np.round((arr - zero_point) / scale).astype(np.int32)
    quantized = np.clip(quantized, qmin, qmax)

    if dtype == DataType.INT16:
        quantized = quantized.astype(np.int16)
    elif dtype == DataType.INT32:
        quantized = quantized.astype(np.int32)

    return quantized, scale, zero_point


def dequantize_tensor(
    quantized: np.ndarray,
    scale: float,
    zero_point: float = 0.0,
) -> np.ndarray:
    """Dequantize fixed-point array back to float."""
    return quantized.astype(np.float32) * scale + zero_point


def convert_weights(
    param_dict: Dict[str, torch.Tensor],
    dtype: DataType = DataType.INT16,
) -> Dict[str, np.ndarray]:
    """Convert a dictionary of PyTorch parameters to quantized NPU weights.

    Args:
        param_dict: Mapping from parameter name to PyTorch tensor.
        dtype: Target quantization data type.

    Returns:
        Dictionary mapping parameter names to quantized numpy arrays.
    """
    result = {}
    for name, tensor in param_dict.items():
        qarr, _, _ = quantize_tensor(tensor, dtype)
        result[name] = qarr
    return result


def pack_weights_for_dram(
    weight_dict: Dict[str, np.ndarray],
    alignment: int = 8,
) -> bytes:
    """Pack quantized weights into a contiguous DRAM blob.

    Args:
        weight_dict: Dictionary of quantized weight arrays.
        alignment: Byte alignment for each tensor.

    Returns:
        Packed binary data.
    """
    blobs = []
    for name in sorted(weight_dict.keys()):
        arr = weight_dict[name]
        data = arr.tobytes()
        # Pad to alignment
        pad = (alignment - len(data) % alignment) % alignment
        data += b"\x00" * pad
        blobs.append(data)
    return b"".join(blobs)
