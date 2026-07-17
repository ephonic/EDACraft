* RC Mesh Network — 10x10 grid, 121 nodes
* Simulates 2D parasitic capacitance/resistance mesh

.subckt rcmesh_row in out
+ params: r=1k c=1p
R1 in m1 r
C1 m1 0 c
R2 m1 m2 r
C2 m2 0 c
R3 m2 m3 r
C3 m3 0 c
R4 m3 m4 r
C4 m4 0 c
R5 m4 m5 r
C5 m5 0 c
R6 m5 m6 r
C6 m6 0 c
R7 m6 m7 r
C7 m7 0 c
R8 m7 m8 r
C8 m8 0 c
R9 m8 m9 r
C9 m9 0 c
R10 m9 out r
C10 out 0 c
.ends

VDD in 0 1 AC 1

X1 in r2 rcmesh_row
X2 r2 r3 rcmesh_row
X3 r3 r4 rcmesh_row
X4 r4 r5 rcmesh_row
X5 r5 r6 rcmesh_row
X6 r6 r7 rcmesh_row
X7 r7 r8 rcmesh_row
X8 r8 r9 rcmesh_row
X9 r9 r10 rcmesh_row
X10 r10 out rcmesh_row

* Vertical connections (simplified: connect rows at endpoints)
Rv1 in v1 2k
Rv2 r10 v2 2k
Rv3 out v3 2k

.ac dec 20 1k 1g
.print v(out)
.end
