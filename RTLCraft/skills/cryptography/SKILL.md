# cryptography — Encryption, Decryption & Security Primitives

## Overview

Cryptographic hardware accelerators for symmetric encryption, hashing, and post-quantum primitives. Designs in this directory are fully pipelined to achieve high throughput (1 result / cycle) for streaming data.

## Sub-directories

### `chacha20/` — ChaCha20 Stream Cipher

| File | Description |
|------|-------------|
| `chacha20_pipe.py` | Fully pipelined ChaCha20 quarter-round engine |

**Key Features:**
- Column-round and diagonal-round pipeline stages
- 16-word state register with ARX (Add-Rotate-XOR) operations
- 20 rounds of quarter-round iterations

## Related Designs

SHA3-256 / Keccak implementations are located in `../arithmetic/sha3/` because they are primarily hash/datapath engines, but they are also widely used in cryptographic protocols.

## Design Patterns

### ARX Pipeline Stage

```python
a = b + c
d = d ^ a
d = rotl(d, n)
```

Each ARX operation is typically one pipeline stage in rtlgen to meet timing.

## See Also

- `../arithmetic/SKILL.md` — SHA3-256 hash engine
- `../fundamentals/SKILL.md` — Standard library (LFSR for PRNG, CRC for integrity)
