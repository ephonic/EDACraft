* S-parameter device DC test
* 2-port S-parameter element in DC circuit

VDD vdd 0 1.2
VIN in 0 0.6

* 2-port S-parameter device (DC analysis uses Y(ω→0))
K1 in out file="netlists/test.s2p" z0=50

* Load resistor
Rload out 0 50

.op
.print v(in) v(out)
.end
