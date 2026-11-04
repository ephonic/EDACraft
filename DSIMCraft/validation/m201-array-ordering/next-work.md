# Next: mixed container dimensions

The unchanged public UVM first stops at `uvm_resource_pool.svh:659`: `rsrc_sv_q_t all[int]`, where the typedef is a queue of resource handles. The independent next-blocker.sv also exercises push_front, leaf size/indexing and two-axis foreach; VCS W-2024.09 passes, dsim rejects with its source location. This is not counted as a supported test.

Retain per-axis type/container metadata through typedefs and specializations. Current bind_container_dimensions/append_type_ranges explicitly reject mixed runtime dimensions; simply deleting that guard would send queue axes through associative-only lowering and silently miscompile valid syntax.

Extend the owned nested container representation and a typed path reference, sharing existing logical signal, automatic-frame and snapshot ownership. Dispatch each path axis by kind, expose a queue leaf through common queue operations/order/copies, and notify the root dependency on mutations. Do not store host vector/map element addresses across growth or checkpoint restore. Reading a missing key and mutating a leaf need distinct behavior.

Follow the storage change through indexed reads/writes, methods, assignment, matching formal types and per-axis foreach. Validate missing keys, signed/string/class keys, bounded queues, copies/deletion, automatic activations, ref behavior and rollback against same-source VCS models, then re-run unchanged public UVM to identify its next actual blocker. Keep unsupported combinations diagnosed until all corresponding execution paths are implemented.
