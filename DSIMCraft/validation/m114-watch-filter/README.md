# M114 withdrawn watch-filter candidate

The candidate was withdrawn after a two-round full-workload screen: it did not provide a useful improvement over M111. No warmup, shared host, GCC O2, CPU 0; this screening is not the final VCS comparison. The patch and reproduction scripts require the frozen M111 runtime/generator state.

| Full workload | Frozen M111 CPU (s) | Disabled candidate CPU (s) | Candidate CPU (s) |
| --- | ---: | ---: | ---: |
| bench_muldiv | 11.315 | 11.060 | 11.625 |
| bench_cpu | 14.930 | 15.045 | 16.535 |
| bench_crc | 4.465 | 4.505 | 4.645 |
