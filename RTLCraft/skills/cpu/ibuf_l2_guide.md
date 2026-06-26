# IBuf — Layer 2 Design Guide

## Interface

### Inputs
| Signal | Width | Description |
|--------|-------|-------------|
| push_valid | 1 | push enable |
| push_data | 32 | instruction |
| pop_ready | 1 | pop enable |

### Outputs

| Signal | Width | Description |
|--------|-------|-------------|
| data | 32 | instruction out |
| valid | 1 | output valid |
| stall | 1 | FIFO full |

## State Variables
- **cnt**: 4bit, init=0 — entry count
- **wr**: 3bit, init=0 — write pointer
- **rd**: 3bit, init=0 — read pointer

## Timing

Pipeline timing: TBD per cycle model

## Guide to Next Layer
- Register names/widths from state variables
- FSM states from cycle model control flow
- Array sizes from FIFO/queue parameters