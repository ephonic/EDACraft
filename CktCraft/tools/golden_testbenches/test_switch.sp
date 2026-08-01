* Test S voltage-controlled switch
VDD vdd 0 5.0
R1 vdd a 1k
R2 a 0 1k
VIN ctrl 0 DC 0.0

* S: switch between node a and gnd, controlled by ctrl
* When V(ctrl) > vt=0.5, switch closes (Ron=1), else open (Roff=1e6)
S1 a 0 ctrl 0 sw_model

.model sw_model vswitch ron=1 roff=1e6 vt=0.5 vh=0.1

.dc VIN 0 1 0.1
.print v(ctrl) v(a)
.end
