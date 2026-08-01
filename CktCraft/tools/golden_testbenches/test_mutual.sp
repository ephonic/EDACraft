* Test K mutual inductance: transformer
* L1=1mH, L2=1mH, k=0.9
* V1 drives L1, measure induced voltage on L2
V1 in 0 PULSE(0 1 0 1u 1u 1m 2m)
L1 in 0 1m
L2 out 0 1m
K1 L1 L2 0.9
RL out 0 1k

.tran 10u 5m
.print v(in) v(out)
.end
