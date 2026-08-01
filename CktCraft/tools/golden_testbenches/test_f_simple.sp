* Simple F (CCCS) test
V1 in 0 DC 1.0
R1 in vsense 1k
VSENSE vsense 0 DC 0.0
F1 out 0 VSENSE 2.0
R2 out 0 1k
.op
.print v(in) v(vsense) i(VSENSE) v(out)
.end
