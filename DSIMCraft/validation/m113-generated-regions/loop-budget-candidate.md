# Withdrawn native-loop budget candidate

This candidate is not enabled in the current product. Its full-workload measurement showed no useful gain; the source patch and tests are retained here for review and reproduction.

The generator can evaluate a non-suspending, known-bit scalar loop using unsigned host arithmetic. This path already requires scalar variables with no watches, aliases, observers or forces, and rejects operations that can call runtime services or throw. Waveform, timing-check and other observation builds retain the ordinary path.

The budget candidate calculates `(limit - executed_steps) / iteration_stride` once. A local iteration counter bounds the host loop; the exact completed instruction count is committed before publishing the loop's values or returning to the instruction dispatcher. An exhausted budget resumes the same original PC as the per-iteration reservation path. Zero iterations, a limit below the current count, and uint64 limits are handled without subtraction or multiplication overflow.

`DSIM_RTL_REFERENCE_LOOP_BUDGET` selects the existing per-iteration reservation from the same generated source. `tests/loop_budget` compares full signal snapshots, instruction counts, exception text and subsequent execution over 454 budget limits; it also exercises X/Z inputs, two-state variables, timed execution and prediction acceptance/rejection. `tests/integral_loops` supplies infinite-loop and real two-partition coverage. These tests establish semantics; the full original perf-kit measurements determine adoption.

This is not general RTL process fusion: signal notifications, process order, suspension points and observable writes are unchanged. Basic-block aggregation outside this restricted loop requires separate handling of callbacks, exceptions, nested calls and budget boundaries.
