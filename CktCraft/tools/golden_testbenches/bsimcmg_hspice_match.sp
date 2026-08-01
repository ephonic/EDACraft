* BSIMCMG HSPICE test with EXACT same params as rfsim test
* Direct drive: Vds=1.0 Vgs=1.0 Vbs=0.2
VDS d 0 1.0
VGS g 0 1.0
VBS b 0 0.2

M1 d g 0 b nmos TFIN=15n L=40n NFIN=10 NRS=1 NRD=1

.model nmos bsimcmg
+ type=1
+ toxe=1e-9 toxp=1.2e-9 hfin=30e-9
+ phig=4.61 nbody=1e24 nsd=2e26
+ u0=0.04 vsat=1.5e5 rdsw=100
+ eta0=0.07 dsub=0.53 drout=0.53
+ bg0sub=1.12 bulkmod=1
+ eot=1.0e-9 epsrox=3.9 epsrsub=11.9
+ fech=2.0 geomod=1
+ cdsc=5e-3 cdscd=5e-3
+ dvt0=0 dvt1=0.3
+ pdibl1=0.3 pdibl2=0.0086
+ pclm=0
+ ua=0.1 ua1=1.032e-3
+ ud=1.0 eu=0.9 etamob=2.5
+ nfactor=1.5
+ k1=0.001 k11=0 k2=0 k21=0
+ phibe=0.7
+ deltavsat=1.0 mexp=3
+ ptwg=0 at=0.007
+ rdswmin=0 rdw=50 rdwmin=0
+ rsw=50 rswmin=0
+ igcmod=0 igbmod=0
+ gidlmod=0 iimod=0
+ rgatemod=0 nqsmod=0 rdsmod=0 shmod=0
+ cgso=0 cgdo=0
+ cjs=5e-4 cjd=5e-4
+ cjsws=5e-10 cjswd=5e-10
+ pbs=1.0 pbd=1.0
+ mjs=0.5 mjd=0.5
+ mjsws=0.33 mjswd=0.33

.op
.print dc v(d) i(VDS)
.temp 27
.end
