* rfsim OSDI: diode driven by current source (easier convergence than voltage)
* I1=1mA drives diode; expect V_anode ~ 0.6V (Shockley: V = nVt*ln(I/Is+1))

I1 0 anode 1m
D1 anode 0 simple_diode

.model simple_diode simple_diode file="models\simple_diode.dll"

.op
.print v(anode)

.end
