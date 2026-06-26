# 01 Spec Review — Smart Earphone SoC

## Modules
| Module | Type | Key Ports | PPA Goals |
|--------|------|-----------|-----------|
| EarphoneRV32 | RV32IM core | imem/dmem buses | <30k NAND2, <0.5mW/MHz |
| EarphoneSIMD16 | Vector ALU | vsrc0/1/2[255:0], vdst | 16 ops/cycle |
| EarphoneFFT256 | FFT accelerator | di_re/im, do_re/im | 256-pt streaming |
| EarphoneQSPI | QSPI XIP | qspi_io[3:0] | memory-mapped flash |
| EarphoneI2C | I2C master | scl, sda | codec/PMIC config |
| EarphoneSRAM256K | SRAM | APB | 256KB single-cycle |
| EarphoneAPBBridge | APB decoder | 8 slave slots | low area |
| EarphoneTop | Top-level | SoC ports | integration |
