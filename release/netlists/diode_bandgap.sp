* Bandgap Reference — diode-based voltage reference
* 2 diodes with different current densities + PTAT resistor

.include diode.inc

VDD vdd 0 3.3
Iref vdd ref 100u

* Q1: 10x area diode
D1 q1a 0 simple_diode
R1 vdd q1a 5k

* Q2: 1x area diode + PTAT resistor
D2 q2 0 simple_diode
Rptat ref q2 5k

* Output buffer (simple resistor divider)
R3 vdd bg 20k
R4 bg 0 10k

.op
.print v(ref) v(q1a) v(q2) v(bg)
.end
