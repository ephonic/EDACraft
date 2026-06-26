# 05 Structure Review

```
EarphoneTop
├── EarphoneRV32
│   ├── 3-stage pipeline regs (clock-gated)
│   ├── M-extension unit (operand-isolated multiplier, iterative divider)
│   └── register file
├── EarphoneSIMD16
│   ├── INT16 ALU array (int_ce gated)
│   └── FP16 MAC pipeline (fp_ce gated)
├── EarphoneFFT256 (wraps FFTController)
├── EarphoneQSPI (idle-gated FSM)
├── EarphoneI2C (idle-gated FSM)
├── EarphoneSRAM256K (transfer-gated memory)
└── EarphoneAPBBridge
```
