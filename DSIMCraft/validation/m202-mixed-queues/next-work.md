# Next: class fields and containers of unpacked structs containing strings

The unchanged public UVM first rejects `uvm_default_factory::m_inst_aliases` at `uvm_factory.svh:622`. Its element has a nested factory type pair plus two strings. `next-blocker.sv` isolates the same class queue storage issue and VCS prints `TRACE struct_string_queue 7 packet`.

Use the existing V::StructStrings copy-on-write representation, not packed text handles or string truncation. Preserve aggregate type identity, defaults, nested offsets and object/class fields. Review all gates together: class field registration/object_part; queue/vector element compatibility; dynamic function signatures; aggregate default initialization; struct member reads and writes through selected queue elements. Existing struct strings support has guards in each of these paths, so removing one guard alone is insufficient.

Cover scalar class struct fields, bounded/unbounded object queues, input/output/return and automatic activation, nested structs and class handles, queue sort/locator with fields, deep copies, equality and invalid/default reads. Validate width and type identity before native code generation; rejected programs must not leave partial CPP. Confirm rollback restores the owned immutable string maps together with integral bits. Use VCS same-source checks, parser and generated runtime sanitizers, then repeat the pinned unmodified public UVM and record its next actual error.

Do not count this plan or an isolated positive probe as complete UVM support.
