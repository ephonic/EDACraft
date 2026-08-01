* BSIM4 HSPICE golden with COMPLETE PTM 130nm NMOS model card
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0 0.7

M1 d g 0 0 nmos w=1u l=130n

.model nmos nmos level=54
+ type=1 version=4.8 binunit=1 paramchk=1
+ mobmod=0 capmod=2 rdsmod=0 rgatemod=0 rgeomod=0
+ rbodymod=0 diomod=0 tnoimod=1 fnoimod=0 igcmod=1 igbmod=1
+ toxe=3.0e-9 toxp=3.0e-9 toxm=3.0e-9 toxref=3.0e-9
+ dtox=0.0 eot=3.0e-9
+ nsub=1.7e17 ndep=1.7e17 nsd=2.0e20
+ phin=0.0 ngate=0 xt=1.55e-7
+ vth0=0.4271 k1=0.3031 k2=-0.0191 k3=80 k3b=0
+ vbm=-4.0 vbx=0.6391
+ gamma1=0.3875 gamma2=0.0
+ dvt0=2.2 dvt1=0.53 dvt2=-0.032
+ dvt0w=0 dvt1w=0 dvt2w=0
+ drout=0.56 dsub=0.56
+ eta0=0.08 etab=-0.07 pclm=1.3
+ pdiblc1=0.39 pdiblc2=0.0086 pdiblcb=0
+ fprout=0.2 pdits=0.2 pditsl=0.2 pditsd=0.2
+ u0=0.0421 ua=-1.41e-9 ub=2.08e-18 uc=-4.65e-11
+ eu=1.67 ud=0.0 ucs=1.67
+ rdsw=165 rdswmin=0 rsw=0 rdw=0
+ rdwmin=0 rswmin=0 prwg=0 prwb=0 prt=0
+ vsat=8.24e4 at=3.3e4 a0=1.0
+ ags=0.2 a1=0.0 a2=1.0
+ keta=-0.047 nfactor=1.5
+ voff=-0.128 minv=0.0 voffl=0.0
+ pscbe1=4.25e6 pscbe2=1.0e-5 pvag=0.0
+ aigc=0.0136 bigc=1.71e-3 cigc=0.075
+ aigs=0.0136 bigs=1.71e-3 cigs=0.075
+ aigd=0.0136 bigd=1.71e-3 cigd=0.075
+ agidl=5.0e-5 bgidl=5.0e5 egidl=0.2
+ agisl=5.0e-5 bgisl=5.0e5 egisl=0.2
+ cjs=1.0e-3 cjd=1.0e-3
+ cjsws=5.0e-10 cjswd=5.0e-10
+ cjswgs=0.0 cjswgd=0.0
+ pbs=0.88 pbd=0.88
+ mjs=0.5 mjd=0.5
+ mjsws=0.33 mjswd=0.33
+ mjswgs=0.33 mjswgd=0.33
+ pbsws=0.88 pbswd=0.88
+ pbswgs=0.88 pbswgd=0.88
+ jss=0.0 jsd=0.0
+ cgso=2.0e-10 cgdo=2.0e-10 cgbo=0.0
+ xpart=0.0
+ noff=1.0 voffcv=0.0 acde=1.0 moin=15.0
+ rsh=0
+ tnom=27.0 ute=-1.48
+ kt1=-0.35 kt1l=0.0 kt2=-0.042
+ ua1=3.31e-9 uc1=-0.015
+ noia=1.0e20 noib=5.0e18 noic=-1.0e-12
+ delta=0.01 xj=0.15e-6
+ cdsc=2.4e-4 cdscb=0.0 cdscd=0.0
+ cit=0.0 vfbcv=-0.025
+ w0=0.0 dvtp0=0.0 dvtp1=0.0
+ lpe0=5.728e-8 lpeb=0.0
+ xrcrg1=12.0 xrcrg2=1.0
+ dmcg=0.0 dmci=0.0 dmdg=0.0 dmcgt=0.0
+ xgw=0.0 xgl=0.0 rshg=0.0 ngcon=1.0

.op
.print dc v(d) v(g) i(VDD)
.temp 27
.end
