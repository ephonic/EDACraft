* Large RC Ladder — 500 sections (1001 nodes)
* Tests sparse AC solver scalability
* Uses subcircuit for compactness

.subckt rc10 in out
+ params: r=1k c=1p
R1 in n1 r
C1 n1 0 c
R2 n1 n2 r
C2 n2 0 c
R3 n2 n3 r
C3 n3 0 c
R4 n3 n4 r
C4 n4 0 c
R5 n4 n5 r
C5 n5 0 c
R6 n5 n6 r
C6 n6 0 c
R7 n6 n7 r
C7 n7 0 c
R8 n7 n8 r
C8 n8 0 c
R9 n8 n9 r
C9 n9 0 c
R10 n9 out r
C10 out 0 c
.ends

VDD in 0 1 AC 1

X1 in n10 rc10
X2 n10 n20 rc10
X3 n20 n30 rc10
X4 n30 n40 rc10
X5 n40 n50 rc10
X6 n50 n60 rc10
X7 n60 n70 rc10
X8 n70 n80 rc10
X9 n80 n90 rc10
X10 n90 n100 rc10
X11 n100 n110 rc10
X12 n110 n120 rc10
X13 n120 n130 rc10
X14 n130 n140 rc10
X15 n140 n150 rc10
X16 n150 n160 rc10
X17 n160 n170 rc10
X18 n170 n180 rc10
X19 n180 n190 rc10
X20 n190 n200 rc10
X21 n200 n210 rc10
X22 n210 n220 rc10
X23 n220 n230 rc10
X24 n230 n240 rc10
X25 n240 n250 rc10
X26 n250 n260 rc10
X27 n260 n270 rc10
X28 n270 n280 rc10
X29 n280 n290 rc10
X30 n290 n300 rc10
X31 n300 n310 rc10
X32 n310 n320 rc10
X33 n320 n330 rc10
X34 n330 n340 rc10
X35 n340 n350 rc10
X36 n350 n360 rc10
X37 n360 n370 rc10
X38 n370 n380 rc10
X39 n380 n390 rc10
X40 n390 n400 rc10
X41 n400 n410 rc10
X42 n410 n420 rc10
X43 n420 n430 rc10
X44 n430 n440 rc10
X45 n440 n450 rc10
X46 n450 n460 rc10
X47 n460 n470 rc10
X48 n470 n480 rc10
X49 n480 n490 rc10
X50 n490 out rc10

.ac dec 20 1k 1g
.print v(out)
.end
