* Diode DC Sweep - HSPICE Golden Reference
* Simple diode circuit: V -> R -> Diode -> GND
V1 in 0 DC 0.0 AC 0
R1 in out 1k
D1 out 0 diode_model

.model diode_model D (IS=1e-14 N=1.0 RS=10 CJ0=1p VJ=0.7 M=0.5 TT=1n)

.dc V1 0 2 0.1
.print dc v(out) i(V1)
.end
