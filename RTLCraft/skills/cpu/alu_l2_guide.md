# ALU — Layer 2 Design Guide

## Interface

### Inputs
| Signal | Width | Description |
|--------|-------|-------------|
| op | 4 | operation code |
| a | 64 | operand A |
| b | 64 | operand B |

### Outputs

| Signal | Width | Description |
|--------|-------|-------------|
| result | 64 | computation result |
| zero | 1 | result is zero |

## State Variables
- **shamt**: 7bit, init=0 — shift amount from b[6:0]

## Timing

Pipeline timing: TBD per cycle model

## Guide to Next Layer
- Register names/widths from state variables
- FSM states from cycle model control flow
- Array sizes from FIFO/queue parameters