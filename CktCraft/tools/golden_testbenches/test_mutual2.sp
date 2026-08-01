* Test K mutual inductance (node-based form)
V1 in 0 PULSE(0 1 0 1u 1u 1m 2m)
L1 in 0 1m
L2 out 0 1m
K1 in 0 out 0 L1=1m L2=1m k=0.9
RL out 0 1k
.tran 10u 5m
.print v(in) v(out)
.end
