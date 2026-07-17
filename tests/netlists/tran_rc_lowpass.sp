* Transient analysis test: RC low-pass step response
* Vin steps from 0 to 1V at t=0; RC time constant = R*C = 1k*1u = 1ms
* Expected: V(out) charges toward 1V with tau=1ms
Vin in 0 PULSE(0 1 0 1n 1n 10m 20m)
R1  in out 1k
C1  out 0   1u
.tran 0.1m 5m
.print v(in) v(out)
.end
