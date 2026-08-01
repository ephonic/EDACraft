* Test E/G behavioral sources: voltage amplifier + transconductance
VDD vdd 0 5.0
VIN in 0 DC 1.0

* E: VCVS - gain=2 voltage amplifier
E1 out1 0 in 0 2.0

* G: VCCS - transconductance 1mS into 1k load = gain=1
G1 out2 0 in 0 1m
R1 out2 0 1k

.op
.print v(in) v(out1) v(out2)
.end
