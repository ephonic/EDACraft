* Test F (CCCS) and H (CCVS) behavioral sources
* Circuit: V1 -> R1 -> sense VS -> F copies current to output
VDD vdd 0 5.0
VIN in 0 DC 1.0
R1 in vsense 1k
* VS with 0V acts as current sensor
VSENSE vsense 0 DC 0.0

* F: CCCS - copies VSENSE current (1mA) with gain=2 -> 2mA into out
F1 vdd out VSENSE 2.0
R2 out 0 1k

* H: CCVS - converts VSENSE current (1mA) to voltage with gain=1k -> 1V
H1 vdd hout VSENSE 1000.0
R3 hout 0 1k

.op
.print v(in) v(vsense) i(VSENSE) v(out) v(hout)
.end
