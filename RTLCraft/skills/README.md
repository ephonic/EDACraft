# skills — Domain-specific Spec2RTL Extensions

Each sub-package provides behavioral models, architecture templates, DSL module
implementations, and skeleton steps for a particular design domain.

> **⚠️ License Notice**
>
> The Python DSL modules in `skills/` are inspired by or derived from third-party
> open-source Verilog reference designs located under `ref_rtl/`. **The copyright of
> these reference RTL designs belongs to their respective original authors.**
>
> When using any skill, you must comply with the license terms of the original
> reference project. If a project does not specify a license, you should contact
> the original author for permission before use.
>
> See the "Project Source" section in each sub-directory's README.md for the
> original author, source link, and license information.

## Skills Index

| Domain | Path | Source | GitHub | License |
|--------|------|--------|--------|---------|
| Codec/LDPC | `codec/ldpc/` | WiMax 802.16e LDPC decoder | [crboth/LDPC_Decoder](https://github.com/crboth/LDPC_Decoder) | — |
| Codec/Video | `codec/video/` | xk265 — Fudan University VIPcore | [openasic-org/xk265](https://github.com/openasic-org/xk265) | Open source |
| CPU | `cpu/` | T-Head C910 (Xuantie) | [T-head-Semi/openc910](https://github.com/T-head-Semi/openc910) | Apache-2.0 |
| DSP | `dsp/` | Alex Forencich DSP library | [alexforencich/verilog-dsp](https://github.com/alexforencich/verilog-dsp) | MIT |
| FFT | `fft/` | R2^2SDF FFT | [nanamake/r22sdf](https://github.com/nanamake/r22sdf) | MIT |
| GPGPU | `gpgpu/` | Ventus GPGPU (乘影) | [THU-DSP-LAB/ventus-gpgpu-verilog](https://github.com/THU-DSP-LAB/ventus-gpgpu-verilog) | Mulan PSL v2 |
| Image/ISP | `image/isp/` | Infinite-ISP v1.1 | [10x-Engineers/Infinite-ISP](https://github.com/10x-Engineers/Infinite-ISP) | Apache-2.0 |
| I/F AXI | `interfaces/axi/` | AXI bus | [alexforencich/verilog-axi](https://github.com/alexforencich/verilog-axi) | MIT |
| I/F AXI-Lite | `interfaces/axi_lite/` | AXI-Lite slave RAM (verilog-axi) | [alexforencich/verilog-axi](https://github.com/alexforencich/verilog-axi) | MIT |
| I/F AXI-S | `interfaces/axis/` | AXI-Stream | [alexforencich/verilog-axis](https://github.com/alexforencich/verilog-axis) | MIT |
| I/F BTLE | `interfaces/btle/` | Xianjun Jiao BTLE | [JiaoXianjun/BTLE](https://github.com/JiaoXianjun/BTLE) | Apache-2.0 |
| I/F Ethernet | `interfaces/ethernet/` | Alex Forencich verilog-ethernet | [alexforencich/verilog-ethernet](https://github.com/alexforencich/verilog-ethernet) | MIT |
| I/F I2C | `interfaces/i2c/` | I2C slave | [alexforencich/verilog-i2c](https://github.com/alexforencich/verilog-i2c) | MIT |
| I/F PCIe | `interfaces/pcie/` | Alex Forencich verilog-pcie | [alexforencich/verilog-pcie](https://github.com/alexforencich/verilog-pcie) | MIT |
| I/F SPI | `interfaces/spi/` | Dr. med. Jan Schiefer verilog_spi | [janschiefer/verilog_spi](https://github.com/janschiefer/verilog_spi) | LGPL-2.1 |
| I/F UART | `interfaces/uart/` | AXI-Stream UART | [alexforencich/verilog-uart](https://github.com/alexforencich/verilog-uart) | MIT |
| I/F Wishbone | `interfaces/wishbone/` | Wishbone bus | [alexforencich/verilog-wishbone](https://github.com/alexforencich/verilog-wishbone) | MIT |
| Mem/CAM | `mem/cam/` | Alex Forencich verilog-cam | [alexforencich/verilog-cam](https://github.com/alexforencich/verilog-cam) | MIT |
| Mem/DDR3 | `mem/ddr3/` | ultraembedded DDR3 controller | [ultraembedded/core_ddr3_controller](https://github.com/ultraembedded/core_ddr3_controller) | Apache-2.0 |
| NoC | `noc/` | 2D mesh NoC | [bakhshalipour/NoC-Verilog](https://github.com/bakhshalipour/NoC-Verilog) | — |
| NPU | `npu/` | Intel FPGA-NPU | [intel/fpga-npu](https://github.com/intel/fpga-npu) | BSD-3-Clause |

See each sub-directory's README.md for detailed project attribution and licensing.
