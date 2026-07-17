* RC Ladder Lowpass — 100 sections, 201 nodes
* AC sweep to see -3dB frequency

VDD in 0 1 AC 1

* 100 RC sections
R1 in n1 1k
C1 n1 0 1p
R2 n1 n2 1k
C2 n2 0 1p
R3 n2 n3 1k
C3 n3 0 1p
R4 n3 n4 1k
C4 n4 0 1p
R5 n4 n5 1k
C5 n5 0 1p
R6 n5 n6 1k
C6 n6 0 1p
R7 n6 n7 1k
C7 n7 0 1p
R8 n7 n8 1k
C8 n8 0 1p
R9 n8 n9 1k
C9 n9 0 1p
R10 n9 n10 1k
C10 n10 0 1p

* Repeat pattern for sections 11-100 using subcircuit
.subckt rc5 in out
R1 in n1 1k
C1 n1 0 1p
R2 n1 n2 1k
C2 n2 0 1p
R3 n2 n3 1k
C3 n3 0 1p
R4 n3 n4 1k
C4 n4 0 1p
R5 n4 out 1k
C5 out 0 1p
.ends

X1 n10 n15 rc5
X2 n15 n20 rc5
X3 n20 n25 rc5
X4 n25 n30 rc5
X5 n30 n35 rc5
X6 n35 n40 rc5
X7 n40 n45 rc5
X8 n45 n50 rc5
X9 n50 n55 rc5
X10 n55 n60 rc5
X11 n60 n65 rc5
X12 n65 n70 rc5
X13 n70 n75 rc5
X14 n75 n80 rc5
X15 n80 n85 rc5
X16 n85 n90 rc5
X17 n90 n95 rc5
X18 n95 out rc5

.ac dec 20 1k 1g
.print v(out)
.end
