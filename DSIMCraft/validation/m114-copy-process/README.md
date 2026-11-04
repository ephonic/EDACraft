# M114 withdrawn copy-process candidate

The candidate was withdrawn after a two-round full-workload screen: it did not provide a useful improvement over M111. No warmup, shared host, GCC O2, CPU 0; this screening is not the final VCS comparison. The patch and reproduction scripts require the frozen M111 runtime/generator state.

| Full workload | Frozen M111 CPU (s) | Disabled candidate CPU (s) | Candidate CPU (s) |
| --- | ---: | ---: | ---: |
| bench_muldiv | 11.135 | 10.910 | 11.315 |
| bench_cpu | 14.840 | 14.810 | 15.145 |
| bench_crc | 4.440 | 4.420 | 4.850 |
