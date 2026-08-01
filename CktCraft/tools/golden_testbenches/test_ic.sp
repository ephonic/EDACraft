* Test .ic initial conditions for transient
* RC circuit with .ic override
V1 in 0 PULSE(0 1 0 1n 1n 5n 10n)
R1 in out 1k
C1 out 0 1n
.ic v(out)=0.5
.tran 100p 5n
.print v(in) v(out)
.end
