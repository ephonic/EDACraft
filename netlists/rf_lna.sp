* RF Single-Ended LNA — common source + inductive degeneration
* 2.4GHz, input match via Ls, load via Ld

.include bsim4_nmos.inc

VDD vdd 0 1.2
VG  g  0 0.6 SIN(0.6 0.01 2.4g)
Ls  vss 0 2n
Ld  vdd out 8n
Cd  out 0 100f
Rd  out 0 1k
M1  out g vss 0 nmos w=10u l=130n

.ac dec 50 100meg 10g
.print v(out)
.end
