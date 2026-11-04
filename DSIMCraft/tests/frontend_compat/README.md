# Reported frontend compatibility cases

The twelve shared models exercise packed module ports, parameterized generate
clones, non-ANSI ports, 2D/3D packed storage, typedef shape, automatic task/function
value parameters, ascending/descending and negative bounds, wide data/indices,
invalid accesses, single-evaluation updates, delayed NBA address sampling,
genvar prefix/postfix updates, unnamed-root inference, escaped identifiers and
Verilog keyword compatibility. `expected.json` contains independent TRACE values;
the parallel case also checks both final outputs and two executed partitions.

`regression.py` executes serial, time-wheel and two-thread compilations, compares
complete ordered/settled streams for VCD and DWF, and checks three failed
predictions against uninterrupted runs. Eight rejection cases and two root
selection cases check diagnostics and selection behavior. Test-owned wave files
are removed before rerunning, preserving the simulator's no-overwrite policy.

Actual VCS compilation/simulation and boundary probes are retained in
[M72](../../validation/m72-frontend-compat/README.md). The keyword models explicitly
select Verilog mode; their filename extension does not change dsim's default.
