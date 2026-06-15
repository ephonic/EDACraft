# Earphone SoC - Top-Level Design Specification

| Field | Value |
|-------|-------|
| Document ID | EARPHONE-TOP-001 |
| Version | 0.2 |
| Status | Contract draft |
| Owner | RTLCraft Agent |

## Purpose

Define the top-level SoC integration contract that drives module integration,
system verification, and top-level sign-off. This document is the L0 source for
the `earphone/top` layered contracts.

## Integrated Blocks

| Instance | Module | Role |
|----------|--------|------|
| cpu | EarphoneRV32 | RV32IM control processor |
| simd16 | EarphoneSIMD16 | 16-lane audio/vector accelerator |
| fft256 | EarphoneFFT256 | Streaming 256-point FFT accelerator |
| qspi | EarphoneQSPI | External XIP flash interface |
| apb_bridge | EarphoneAPBBridge | APB4 decode and response mux |
| sram | EarphoneSRAM256K | 256 KB on-chip SRAM |
| i2c | EarphoneI2C | APB I2C master |

## External Interfaces

| Interface | Protocol | Width / Signals | Direction |
|-----------|----------|-----------------|-----------|
| clk/rst_n | Clock/reset | 1-bit each | Input |
| imem | Simple request/grant memory bus | 32-bit address/data | CPU master exposed |
| dmem | Simple request/grant memory bus | 32-bit address/data, 4-bit write enable | CPU master exposed |
| apb_debug | APB4-lite | 32-bit address/data, 4-bit strobe | External master to SoC |
| qspi_pads | Quad SPI | sck, cs_n, io[3:0], oe[3:0] | External flash |
| i2c_pads | Open-drain style I2C pins | scl/sda input/output/oe | External bus |

## APB Memory Map

APB slots are decoded by `m_paddr[29:22]`, with 4 MB per slot.

| Slot | Base Offset | Region | Integrated In Top |
|------|-------------|--------|-------------------|
| 0 | 0x00000000 | QSPI | Reserved for XIP path |
| 1 | 0x00400000 | SRAM | Yes |
| 2 | 0x00800000 | SPI | No |
| 3 | 0x00C00000 | UART | No |
| 4 | 0x01000000 | I2C | Yes |
| 5 | 0x01400000 | I2S | No |
| 6 | 0x01800000 | BTLE | No |
| 7 | 0x01C00000 | SIMD16 | Reserved for accelerator control |

## Required Invariants

- The top-level contract must include every module discovered by the SoC closure plan.
- APB slot ownership must match the APB bridge L1/L3 contracts.
- `EarphoneTop` must emit synthesizable Verilog into `earphone_top.v`.
- Top-level closure must not run before all module approvals and SoC approval are current.
