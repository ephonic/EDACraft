# Direct stream RHS with an intra-assignment event control

The retained source was compiled on `10.131.254.103` after
`source /apps/EDAs/syn.bash`, using
`vcs -full64 -sverilog ../dsim-m75-event.sv -o simv`, and executed with
`./simv -no_save`. `compile.log` and `run.log` are the actual VCS output.

The plain packed NBA continues at time 0 and updates `a` on the event at 2 ns.
The direct streaming RHS continues its process at 2 ns and leaves `b` unknown
through the final observation at 3 ns. This is retained as a compatibility gap,
not as a test expectation for the new native feature. The compiler rejects a
direct streaming RHS with an event control until its behavior is resolved.
The shared timing fixture instead captures the stream in a packed temporary,
then uses an ordinary event NBA; all its public bits are compared with VCS.
