* rfsim generated-model: diode forward-bias DC operating point
* Same circuit as diode_dc.sp, but routed to the rfsim_codegen C++ model
* via .model generated=1 (no openvaf/OSDI dll involved).
* V1=5V, R1=1k, D1(anode,cathode) forward biased
* Expect: V_anode ~ 0.7V, current ~ 4.3mA (same as diode_dc.sp)

V1 vec 0 5
R1 vec anode 1k
D1 anode 0 simple_diode

* generated=1 -> use built-in generated model (src/model/generated/)
.model simple_diode simple_diode generated=1

.op
.print v(anode) i(v1)

.end
