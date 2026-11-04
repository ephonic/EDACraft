# M224 — UVM event identity transfer and automatic local events

The unchanged complete UVM library previously stopped on the event member copy
in `uvm_event.svh:268`. Typed event transfers now preserve the full event identity
in class fields and automatic local storage. Reset's automatic local event gets
a fresh identity on activation. Captured waits and delayed NBA triggers retain
the issue-time object even after the variable is rebound. Static module events
can be sources; alias dependency notifications keep level waits responsive.

Ten same-byte VCS W-2024.09 sources cover class/local copies, reset, saved old
waits, concurrent automatic/explicit block locals, static sources, receiver
side effects, delayed triggers and null formatting. Initial null experiments
mixed triggering and querying; separate probes establish that null triggers are
no-ops, waiting blocks, and querying errors. Initial unsuccessful oracle wrappers
and all raw sources/logs are retained externally. Six completed non-null runs
were recovered from their successful raw outputs after the first wrapper stopped
on null; their exact source bytes and finish markers were checked.

Seven dsim compile boundaries are checked: VCS rejects five of those sources,
but accepts module destinations and delayed handle assignments. Those two remain
explicit dsim gaps. Null query and null receiver runtime failures match VCS.
This is not complete event typing: arrays, declaration aliases/initializers,
ordinary module destinations, timed transfers, event formals/returns remain out
of scope. No integer coercion or event NBA assignment is enabled.

The unchanged public library advances to `uvm_printer.svh:1501`, runtime string
replication. No complete UVM native model or successful `run_test` is claimed.
`process::await` is still a later gap, requiring process lifetime state and wake
notifications, not just a parser method name. No new C910 or speed ratio is added.

Persistent raw evidence: `dsim-test/evidence/m224-event-aliases`; VCS raw logs are
also under isolated `/tmp/dsim-m224-*` directories on 103. No proprietary generated
code is copied into this repository.

The final matrix passes 40 native captures across default/shared/wheel and thread
requests, seven compile diagnostics and two runtime rejections. Ten frontend and
ten generated native ASan/UBSan programs pass with shared C++/full ordered-wave
identity. Six forced failed predictions restore copied/reset/local event
identities, pending subscribers and module-source notifications. The final
one-line local ownership metadata correction was rechecked with the normal and
sanitized frontends: all 40 normal and ten sanitizer C++ inputs remain identical;
the corresponding native results are reused, not counted as new executions.

Old class events rebuilt 146 captures (rollback/commit), named events 62 captures
(two rollbacks and real two partitions), and explicit automatic 76 captures
(three rollback models plus restore-before-allocation). The explicit automatic
wrapper stopped after all positives on a stale rejection of module-level static,
already accepted by the M223 stable entry. That negative is replaced by duplicate
static; current negatives rerun with output protection and prior complete semantic
wave streams are checked by `explicit-negatives.py`. Legal automatic-event
negatives in two old suites are replaced by unsupported arrays/initializers,
with new automatic/explicit positives in this group. Initial failures remain
external and are not presented as successful wrapper exits.

Production `78c8698a` is pushed. Mac stable
`20261102T163817898267Z-999d1fdd881e` and 103 Intel stable
`20261102T163810225295Z-999d1fdd881e` are active from clean frozen sources.
Each endpoint passes the new and legacy class-event groups: 186 captures,
19 compile diagnostics, two runtime rejections, plus mandatory parser, format
and native DB checks. The new 40 full C++ inputs match development; ten actual
entry emissions match each release's verified native inputs. Those programs
are reused and rerun with complete ordered-wave identity. Both 103 root/bin
aliases pass. Source SHA, ten full entry C++ files and TRACE outputs match
across platforms; receipts are included. Full UVM remains incomplete at runtime
string replication, with `process::await` and other later gaps outstanding.
