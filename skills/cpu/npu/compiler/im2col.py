"""
Im2Col utility for CNN convolution.

Converts convolution into matrix multiplication via im2col.
"""

import torch
import torch.nn.functional as F


def im2col_input(x: torch.Tensor, kernel_h: int, kernel_w: int,
                 stride_h: int = 1, stride_w: int = 1,
                 pad_h: int = 0, pad_w: int = 0) -> torch.Tensor:
    """
    Apply im2col to input tensor.

    Args:
        x: Input tensor of shape (N, C, H, W)
        kernel_h, kernel_w: Kernel size
        stride_h, stride_w: Stride
        pad_h, pad_w: Padding

    Returns:
        Column matrix of shape (N, C*kh*kw, out_h*out_w)
    """
    if x.dim() == 3:
        # (C, H, W) -> (1, C, H, W)
        x = x.unsqueeze(0)
        squeeze = True
    else:
        squeeze = False

    n, c, h, w = x.shape
    # Use torch.nn.functional.unfold (im2col)
    x_padded = F.pad(x, (pad_w, pad_w, pad_h, pad_h))
    cols = F.unfold(x_padded, (kernel_h, kernel_w), stride=(stride_h, stride_w))
    # cols shape: (N, C*kh*kw, out_h*out_w)

    if squeeze:
        cols = cols.squeeze(0)
    return cols


def im2col_weight(weight: torch.Tensor) -> torch.Tensor:
    """
    Reshape conv weight to 2D matrix for GEMM.

    Args:
        weight: Conv weight of shape (C_out, C_in, KH, KW)

    Returns:
        Reshaped weight of shape (C_out, C_in*KH*KW)
    """
    cout, cin, kh, kw = weight.shape
    return weight.view(cout, cin * kh * kw)


def conv2d_output_shape(input_shape, weight_shape, stride, padding):
    """
    Calculate Conv2d output shape.

    Args:
        input_shape: (N, C, H, W) or (C, H, W)
        weight_shape: (C_out, C_in, KH, KW)
        stride: (stride_h, stride_w) or int
        padding: (pad_h, pad_w) or int

    Returns:
        Output shape tuple
    """
    if len(input_shape) == 3:
        c, h, w = input_shape
        n = 1
    else:
        n, c, h, w = input_shape

    cout, cin, kh, kw = weight_shape

    if isinstance(stride, int):
        stride_h = stride_w = stride
    else:
        stride_h, stride_w = stride

    if isinstance(padding, int):
        pad_h = pad_w = padding
    else:
        pad_h, pad_w = padding

    out_h = (h + 2 * pad_h - kh) // stride_h + 1
    out_w = (w + 2 * pad_w - kw) // stride_w + 1

    if len(input_shape) == 3:
        return (cout, out_h, out_w)
    return (n, cout, out_h, out_w)
