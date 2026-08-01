* Diode DC Sweep - rfsim Test
* Simple diode circuit: V -> R -> Diode -> GND
V1 in 0 DC 0.0
R1 in out 1k
D1 out 0 diode

.model diode diode_va generated=1 is=1e-14 n=1.0 rs=10 cj0=1p vj=0.7 m=0.5

.dc V1 0 2 0.1
.print v(out) i(V1)
.end
