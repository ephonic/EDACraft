# M222 — heap array reference arguments

Implement real aliases for one-dimensional class dynamic-array/queue fields.
The unchanged full UVM library supplies the actual `rhs.get_value_array(value)`
reproducer; `methods.sv` retains that shape with 65-bit elements. A per-object,
per-field signal routes existing automatic reference frames to indexed heap
storage. Multiple aliases see allocation/replacement immediately. Captured
receivers survive handle reassignment and delayed calls; field writes notify
reference waiters. No vector pointers or copy-in/copy-out emulation are used.

VCS W-2024.09 accepts bounded actual queues for unbounded ref formals, retaining
actual capacity. Both heap and ordinary queue references implement this rule,
including nested forwarding. A bounded formal still requires the same bound.
The initial overstrict bound-negative was accepted by VCS; the rule was fixed,
positive bounded tests added, and the final negative uses unequal bounded types.
All initial results remain external, including an oracle runner failure caused
by AppleDouble metadata files; the final runner excludes hidden fixture files.

Ten same-byte VCS sources verify trace and source hashes; one receiver-evaluation
probe is kept explicitly native-only. VCS evaluates `choose().data` twice in
that probe while dsim evaluates the receiver once. The portable comparison uses
a saved handle and does not claim this difference is fixed. Seven final invalid
bindings are rejected by both compilers. A null receiver is rejected at runtime.
A class-array ref NBA is explicitly unsupported; VCS rejects this particular
ref-port NBA with NYI as well (not a claim that the language forbids it).

The support boundary is whole, one-dimensional class dynamic arrays/queues and
existing element types. Associative-array references, ref slices, multidimensional
heap arrays and class-array ref NBAs remain outside this implementation.

Persistent raw evidence: `dsim-test/evidence/m222-object-array-refs`. Generated
programs, ordered waves, initial failures and proprietary oracle logs stay there
or under isolated `/tmp/dsim-m222-*` directories on 103. No VCS-generated code is
copied into the repository. This batch adds no performance ratio or C910 claim.

Development normal execution passes 33 model/mode combinations, seven protected
compile rejections and two runtime rejections. The earlier ref group rebuilt 77
captures and the class dynamic-array group rebuilt 110 captures. Four forced
failed predictions restore aliases, delayed receivers, queue bounds and waiters
with complete ordered waveform identity. The unchanged full UVM source hash is
checked; default/shared/sanitized frontends all advance to `uvm_event.svh:268`
event-handle assignment. No complete UVM model or `run_test` success is claimed.

All eleven sanitized frontend/native builds and runs completed without ASan/UBSan
errors. The initial final C++ identity check caught an incidental header comment
edit during six normal compilations. Those six inputs are refreshed with the
frozen bytes, their native traces/waves are rechecked, and `code-identity.py`
confirms exact C++ plus all 33 captures against the existing sanitized runs.
Initial wrapper failures and programs remain in the external evidence directory;
this does not count as eleven additional sanitizer executions.

Production `4d3c25b0` is pushed. Mac stable
`20261102T145849674617Z-e740775849da` passes the clean frozen 33-capture group,
seven compile/two runtime rejections, mandatory parser/format/native DB checks
and eleven actual-entry C++/native reruns with complete waveform identity.
103 Intel stable `20261102T145852266781Z-e740775849da` is active after the same
frozen release checks; both root/bin aliases and all eleven actual entries pass. Source SHA, eleven
complete generated C++ files and TRACE outputs match Mac; full ordered captures
are checked against each platform's validated native inputs. See release receipts
and `cross-platform.json`.
