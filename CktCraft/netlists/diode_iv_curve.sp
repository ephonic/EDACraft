* Diode I-V Characterization — DC sweep
* Measures diode forward voltage vs current

.include diode.inc

VDD vdd 0 5
R1 vdd a 1k
D1 a 0 simple_diode

.dc VDD 0 5 0.1
.print v(a)
.end
