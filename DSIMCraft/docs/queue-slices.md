# Queue slices and function output

The RTL frontend accepts right-side slices of one-dimensional queues,
including class properties and subroutine values. Bounds are evaluated once;
`$` uses the captured queue's last index. Negative lower bounds and excessive
upper bounds are clipped, reversed ranges produce empty queues, and assignment
copies queue values without changing the source queue.

Slices work in queue assignment, input arguments, returned queue values,
array comparison and size queries. Existing pure array operations can consume
materialized results. Left-side slice assignment and nested selections remain
outside this implementation. VCS W-2024.09 rejects the direct slice event probe
saved under `validation/m217-queue-slices`; it is not counted as alignment.

Functions may execute existing zero-time `$display`, `$write`, `$fdisplay`
and `$fwrite` operations, in addition to `$sformat`/`$swrite`. User task calls
and timing controls remain rejected in functions.

Five same-source VCS fixtures cover bounds, class fields, parameters/returns,
comparisons, queries and file content. The unchanged complete UVM library now
passes the previous slice/function-output blockers but still encounters a
later elaboration binding error (`map::at`). No full UVM model or successful
`run_test` is claimed.
