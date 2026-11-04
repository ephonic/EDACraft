# M114 withdrawn linear-process candidate

The candidate was withdrawn after a two-round full-workload screen: it did not provide a useful improvement over M111. No warmup, shared host, GCC O2, CPU 0; this screening is not the final VCS comparison. The patch and reproduction scripts require the frozen M111 runtime/generator state.

| Full workload | Frozen M111 CPU (s) | Disabled candidate CPU (s) | Candidate CPU (s) |
| --- | ---: | ---: | ---: |
| bench_muldiv | 10.955 | 10.965 | 11.250 |
| bench_cpu | 14.990 | 14.860 | 17.525 |
| bench_crc | 4.390 | 4.375 | 4.765 |

The later NBA screen accidentally reused this generator; that mixed screen is invalid for isolated NBA attribution and is retained separately. The final NBA comparison rebuilds the compiler and verifies unchanged main bodies and exact reference machine-code identity.
