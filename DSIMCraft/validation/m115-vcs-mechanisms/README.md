# M115: evidence from VCS itself

The previous dsim hotspot work did not establish what gives VCS its main speed
advantage. This investigation finds two concrete structural differences to test:
fixed grouped NBA commits and direct calls between generated propagation functions.
Their individual runtime contribution has **not** been established.

## Original executable diagnostics

`collect.py` runs the unchanged, complete original CPU/CRC/muldiv fixtures with
the frozen VCS executables. Each has a control run, an NBA request-count run and
one PC-sampled run, pinned to CPU 0. All complete PERF results agree with their
frozen oracle. `collection.json` retains executable/input identities and commands;
`audit.json` checks ten outputs including the separate generated-C run.

| Full workload | dsim M111 NBA records, prior diagnostic | VCS NBA_Semiler requests | VCS objects receiving requests |
| --- | ---: | ---: | ---: |
| CPU | 118,500,239 | 34,500,055 | 19 |
| CRC | 24,641,619 | 23,321,342 | 6 |
| muldiv | 163,197,031 | 93,598,039 | 15 |

The dsim column comes from [the earlier complete diagnostic](../m112-hotspots/counts.json).
These are different units: per-assignment records versus scheduling API requests.
Requests need not be distinct enqueues or executed callbacks. This table neither
implies a speed ratio nor explains CRC's remaining overhead. The counting shim
uses the two-argument ABI confirmed in generated headers, forwards every request,
and records overflow checks and counts by object. It is for these single-thread
simulation runs; no FGP measurement is claimed. CPU startup/runtime strace has no
`CLONE_THREAD` creation.

PC sampling uses ITIMER_PROF and unique PID-qualified files. VCS starts helper
processes; the first shared-prefix trial could overwrite capture files and is
excluded. The accepted collector selects exactly one substantial capture with
the VCS runtime mapped. The sampler checks its handler is still installed on
exit. Accepted CPU/CRC/muldiv captures have 5,679/3,920/6,810 samples. `samples.json`
retains module/symbol attribution. Some native local functions share a symbol
range, so a symbol percentage is not the cost of one RTL process. Sampling is
diagnostic, not PMU data or a subtraction from dsim runtime. Instrumented times
are retained privately and are excluded from speed claims.

## Same-source generated C

The installed VCS help documents `-gen_c`. Rebuilding the original CPU fixture
with that option exposes readable design routines. Its full result matches the
original executable, but this is a separate backend and is not assumed to have
identical machine code or speed. Exact command, run logs and vendor-generated
code remain privately on 103 at `/tmp/dsim-m115-vcs/`.

`analyze.py` exports only hashes and structural facts into `structure.json`:

- The CPU model initializes 23 fixed NBA objects, with 64-byte stride. Pending
  values are stored at fixed offsets. Multiple destination values share a commit
  callback, instead of creating one generic runtime record per assignment.
- One callback, for the object at offset 1192, writes two scalar-byte values and
  five pairs of 32-bit four-state planes, then directly calls seven generated
  successor functions. The original default executable's counter independently
  reports 7,500,010 requests to that object. It is a request count, not a callback
  execution count.
- The original native design library contains NBA scheduling call sites as well;
  the statement about fewer requests comes from that original executable, rather
  than extrapolating the generated-C result.

This substantiates specialization of storage, commit groups and propagation.
It does not show that VCS eliminates all port adapters, all delta cycles or all
watcher work. Runtime notification and scheduling functions remain prominent in
the accepted samples. The report `/home/yangfan/vcs/vcs1017.md` was also reread;
its older design/timings are not mixed into this measurement.

## Next controlled implementation experiment

Generate static NBA jobs and fixed successor connections for a conservative
subset, then measure grouping and propagation separately on unchanged full
fixtures. Dynamic/selected targets, suspending or reentrant execution, repeated
writes, overlapping writers and observable intermediate states require fallback
or an explicit proof. Exact budget/resumption, X/Z, repeated same-time triggers,
NBA cascades, force/release, ordered waves and checkpoint rollback remain required
validation. The current [M114 release](../m114-nba-storage/README.md) only shrinks
records; it does not implement these structural changes.

`count_nba.c`, `cpu_sample.c`, collection/symbolization/analysis/audit scripts and
derived JSON facts are public. Proprietary generated C and vendor binaries are
not added to dsim's repository or its distributable evidence archives.
