* S-parameter device AC test
* 2-port S-parameter element connected between nodes 1 and 2

VDD vdd 0 1.2
VIN in 0 0.6 AC 1

* 2-port S-parameter device
K1 in out file="netlists/test.s2p" z0=50

* Load resistor
Rload out 0 50

.ac dec 10 1meg 100meg
.print v(out)
.end
