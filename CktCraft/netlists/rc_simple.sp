* Simple RC lowpass for AC test
VDD in 0 1 AC 1
R1 in out 1k
C1 out 0 1p
.ac dec 10 1k 1g
.print v(out)
.end
