* Full-Wave Rectifier — 4 diode bridge + RC filter
* 60Hz AC input, DC output after rectification

.include diode.inc

VAC in1 0 0 SIN(0 5 60)
VAC2 in2 0 0 SIN(0 5 60)
Rload out 0 1k
Cload out 0 100u

D1 in1 out simple_diode
D2 in2 out simple_diode
D3 0 in1 simple_diode
D4 0 in2 simple_diode

.op
.print v(out)
.end
