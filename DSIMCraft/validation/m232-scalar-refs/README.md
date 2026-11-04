# M232 — scalar class references and real UVM execution

Scalar field references use stable object/field identities and cached physical
signals. Ordinary class stores update those signals; ref stores normalize their
value and route through the real object setter before publishing. Direct-field
and alias waiters both wake. The cache, signals, heap and activation aliases are
owned by the simulation state and restored together by checkpoints. No raw
pointer into a growable heap or return-time value copy implements the alias.

Ten fixtures pass serial/shared/shared-wheel modes (30 complete ordered captures),
four protected compile boundaries and one real null-object runtime rejection.
They cover live delayed writes, two aliases, receiver rebinding, direct/ref
waiters, wide X/Z values, two-state normalization, text, real, enum/class handles,
inheritance/shadowing, recursion, cancellation and aggregate string fields.
Nine same-byte VCS outputs match. The receiver-effect probe calls its function
once in dsim and twice in VCS, consistent with the earlier array-ref difference.
This probe remains a visible difference rather than an alignment success.
VCS rejects three compile boundaries but accepts nonconst ref to a const field;
dsim currently rejects that case. Both reject the null object at runtime.

Six frontend/native ASan/UBSan models pass with complete C++/wave identity.
Five forced failed predictions pass equal-horizon full-wave comparisons before
allocation and after alias binding. The first checkpoint harness started before
the final aggregate artifact existed; that incomplete attempt is retained, and
the complete five-case suite passes after enforcing the prerequisite.
Older ordinary refs pass 77 captures, five failed predictions, bounded storage
and two actual partitions. Class-array refs pass 33 captures and their boundaries.

The unchanged complete Accellera UVM 2020.3.1 source (181 files, tree SHA
65296510b8010f96fccb3cd294936a68ec1fc7f71c9fe540af181bfddf45fe6f)
now compiles natively and passes run_test with zero UVM_ERROR/UVM_FATAL:

- Original hello test: `TRACE REAL_UVM_SMOKE`.
- Sequence integration: factory override creates tagged_packet values 100/101/102;
  config_db provides the count; sequencer/driver get_next_item/item_done and
  analysis port/imp deliver three transactions to the scoreboard, sum 303;
  phase objections finish normally. All TRACE lines match the same-source VCS run.

These use UVM_NO_DPI and native -O0 verification. The complete integration
frontend and actual native program also pass ASan/UBSan, with generated C++
identical to the normal frontend. Initial native testing caught a missing fast
set_planes entry after a new reference overload; corrected before final tests.
A hand-written expected hex string was one digit short; the actual final output
matches VCS. All early failed attempts remain in the raw evidence directory.

This is measured UVM workflow coverage, not full UVM or DPI/VPI support.
The next real utilities fixture (field automation, clone/copy/compare, constraints
and uvm_event) passes VCS but dsim still rejects its field macro's dynamic-array
stream assignment target. The fixture is retained unchanged; no library source
is replaced. General dead-branch pruning is deferred because it must preserve
static declaration initialization, so it is not part of this release.

Production 3417c960 is pushed. Mac 20261103T235703527576Z-ddbe7dcd6145 and
103 Intel 20261103T235737266273Z-ddbe7dcd6145 are active. Each immutable
release passes three groups (140 captures, 22 compile boundaries, five runtime
rejections) and mandatory parser/format/native DB checks. All 30 new C++ files
match development inputs. Ten actual-entry C++/traces match across hosts and
complete per-platform wave reruns pass; both 103 aliases pass.

Both actual stable entries also reproduce each complete UVM hello/integration
model byte-for-byte before reusing their validated -O0 native program, then pass
run_test again with zero errors/fatals. Source tree and test fingerprints and
all TRACE lines match across hosts. The final sanitized frontend is rebuilt
from production source and reproduces all six sanitized native inputs plus
the complete sanitized UVM integration input exactly.

The next stream-target probe is retained separately: VCS allocates eight bits
and prints 01101001 for 8'h96; dsim rejects compilation without overwriting the
protected C++ output. This remains a known gap, not an alignment success.
Raw evidence: `dsim-test/evidence/m232-scalar-refs/`. No performance comparison.
