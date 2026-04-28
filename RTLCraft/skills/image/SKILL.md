# image — Image Signal Processing (ISP) & Computer Vision

## Overview

Image processing accelerators including ISP pipelines, filtering kernels, geometric transforms, and DCT/IDCT engines.

## Status

🚧 **Reserved directory** — Designs will be added in future releases.

## Planned Modules

| Module | Description |
|--------|-------------|
| `BayerDemosaic` | Bayer CFA demosaicing (bilinear / edge-aware) |
| `GaussianBlur` | 2D Gaussian filter with line buffers |
| `ImageResize` | Bilinear / bicubic image scaling |
| `2D-DCT` | 8×8 DCT for JPEG compression |
| `HistogramEqualizer` | Contrast enhancement pipeline |

## Design Guidelines

- Use **line buffers** (ShiftReg-based) to provide sliding-window access
- **Fixed-point arithmetic** is usually sufficient for image processing
- Consider **pixel-rate = 1 pixel/cycle** throughput for real-time HD/4K

## See Also

- `../video/SKILL.md` — Video codec integration
