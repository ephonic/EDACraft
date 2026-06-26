# ALU — Layer 1 Design Guide

## Interface

### Inputs
| Signal | Width | Description |
|--------|-------|-------------|
| op | 4 | op |
| a | 64 | a |
| b | 64 | b |

### Outputs

| Signal | Width | Description |
|--------|-------|-------------|
| result | 64 | r |
| zero | 1 | z |

## Behavioral Description
- Arithmetic Logic Unit with cross-layer verification

## Guide to Next Layer
- Pipeline stages: determine from L1 sequential dependencies
- State variables: derived from L1 internal state requirements