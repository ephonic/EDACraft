* Clock Tree — H-tree distributed RC, 16 endpoints
* Simulates clock distribution parasitic delay

.subckt htree2 in mid out
+ params: r=100 c=1p
R1 in mid r
C1 mid 0 c
R2 mid out r
C2 out 0 c
.ends

VDD clk 0 1 AC 1

* Level 1: 2 branches
R1 clk a1 200
R2 clk a2 200
Ca1 a1 0 2p
Ca2 a2 0 2p

* Level 2: 4 branches
R3 a1 b1 100
R4 a1 b2 100
R5 a2 b3 100
R6 a2 b4 100
Cb1 b1 0 1p
Cb2 b2 0 1p
Cb3 b3 0 1p
Cb4 b4 0 1p

* Level 3: 8 leaf endpoints
R7 b1 c1 50
R8 b1 c2 50
R9 b2 c3 50
R10 b2 c4 50
R11 b3 c5 50
R12 b3 c6 50
R13 b4 c7 50
R14 b4 c8 50
Cc1 c1 0 0.5p
Cc2 c2 0 0.5p
Cc3 c3 0 0.5p
Cc4 c4 0 0.5p
Cc5 c5 0 0.5p
Cc6 c6 0 0.5p
Cc7 c7 0 0.5p
Cc8 c8 0 0.5p

.ac dec 20 1k 1g
.print v(c1) v(c8)
.end
