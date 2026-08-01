* VCCS test: G device as voltage-controlled current source
* G1 converts V(in) to current at output
VDD vdd 0 5.0
VIN in 0 1.0
R1 vdd out 1k
G1 out 0 in 0 0.001
.op
.print v(in) v(out) i(VDD)
.end
