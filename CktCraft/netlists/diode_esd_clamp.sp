* ESD Clamp — diode-based protection circuit
* AC analysis for clamping behavior

.include diode.inc

VDD vdd 0 1.5
Vin pad 0 0 AC 1

* Top clamp: pad → VDD
D1 pad vdd simple_diode

* Bottom clamp: GND → pad
D2 0 pad simple_diode

* Series protection resistor
Rser pad internal 100

* Internal load
Rload internal 0 1k
Cload internal 0 1p

.ac dec 50 1 1g
.print v(pad) v(internal)
.end
