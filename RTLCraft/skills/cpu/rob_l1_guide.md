# ROB — Layer 1 Design Guide

## Interface

### Inputs
| Signal | Width | Description |
|--------|-------|-------------|
| alloc | 1 | allocate entry |
| complete | 1 | mark complete |
| retire_ready | 1 | retire handshake |

### Outputs

| Signal | Width | Description |
|--------|-------|-------------|
| retire_en | 1 | retire valid |
| full | 1 | ROB full |
| empty | 1 | ROB empty |

## State Variables
- **head**: 5bit, init=0 — retire pointer
- **tail**: 5bit, init=0 — allocate pointer
- **cnt**: 5bit, init=0 — entry count

## Behavioral Description
- 32-entry reorder buffer

## Guide to Next Layer
- Pipeline stages: determine from L1 sequential dependencies
- State variables: derived from L1 internal state requirements