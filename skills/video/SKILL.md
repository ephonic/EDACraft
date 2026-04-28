# video — Video Codecs & Display Pipelines

## Overview

Video processing hardware including codec accelerators (H.264/HEVC/AV1), display controllers, and high-speed interface IPs (HDMI, DisplayPort, MIPI DSI).

## Status

🚧 **Reserved directory** — Designs will be added in future releases.

## Planned Modules

| Module | Description |
|--------|-------------|
| `H264EntropyDecoder` | CAVLC / CABAC entropy decoding pipeline |
| `MotionCompensation` | Inter-prediction motion compensation engine |
| `HDMIController` | HDMI 2.0 transmitter with TMDS encoding |
| `DisplayPipeline` | Color space conversion, gamma correction, dithering |

## Design Guidelines

- Video pipelines are typically **line-buffer based** rather than frame-buffer based for area efficiency
- Use **async FIFOs** for clock-domain crossing between pixel clock and system clock
- Consider **burst DMA** for frame buffer memory access

## See Also

- `../image/SKILL.md` — Image processing primitives (resize, filter)
