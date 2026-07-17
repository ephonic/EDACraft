* rfsim OSDI: diode forward-bias DC operating point
* D1 uses simple_diode.dll compiled by OpenVAF (Shockley equation)
* V1=5V, R1=1k, D1(anode,cathode) forward biased
* Expect: V_anode ~ 0.7V, current ~ 4.3mA

V1 vec 0 5
R1 vec anode 1k
D1 anode 0 simple_diode

* OSDI library for the diode model
.model simple_diode simple_diode file="models\simple_diode.dll"

.op
.print v(anode) i(v1)

.end
