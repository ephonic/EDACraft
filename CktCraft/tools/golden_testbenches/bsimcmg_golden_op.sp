* BSIMCMG Golden DC OP — matches test_generated_models.cpp BsimcmgDcOpMatchesGolden
* Direct I-V: VDS/VGS/VBS drive BSIMCMG FinFET, measure I(VDS)
* Model card: simplified BSIMCMG v110, L=40n TFIN=15n NFIN=10
*
* Run: finesim -spice bsimcmg_golden_op.sp

.option post=2 nomod

.param vg_val=1.0
.param vd_val=1.0
.param vb_val=0.2

VDS d 0 'vd_val'
VGS g 0 'vg_val'
VBS b 0 'vb_val'

M1 d g 0 b nmos1 TFIN=15n L=40n NFIN=10 NRS=1 NRD=1

.model nmos1 bsimcmg
+ TYPE = 1.0
+ TOXE = 1.0n
+ TOXP = 1.2n
+ HFIN = 30n
+ PHIG = 4.61
+ NBODY = 1e24
+ NSD = 2e26
+ U0 = 0.04
+ VSAT = 1.5e5
+ RDSW = 100
+ ETA0 = 0.07
+ DSUB = 0.53
+ DROUT = 0.53
+ BG0SUB = 1.12
+ BULKMOD = 1
+ AGIDL = 50.00f
+ AGISL = 50.00f
+ AIGBINV = 11.10m
+ AIGC = 13.60m
+ AT = 0.007
+ BGIDL = 400.0E6
+ BGISL = 400.0E6
+ BIGBINV = -1.000m
+ BIGC = 1.710m
+ CDSC = 5.000m
+ CDSCD = 5.000m
+ CFS = 1.0e-10
+ CFD = 1.0e-10
+ CGEOMOD = 0
+ CGSL = 1.0e-10
+ CGDL = 1.0e-10
+ CIGBINV = 6.000m
+ CIGC = 75.00m
+ CIT = 0.000
+ CTH0 = 2.0e-5
+ D = 40n
+ DELTAW = 0.000
+ DELTAWCV = 0.000
+ DLC = 0.000
+ DVT0 = 0.000
+ DVT1 = 300.0m
+ EASUB = 4.050
+ EGIDL = 0.000
+ EGISL = 0.000
+ EIGBINV = 1.100
+ EOT = 1.0n
+ EPSROX = 3.900
+ EPSRSUB = 11.90
+ ETAMOB = 2.500
+ EU = 0.9
+ FECH = 2.000
+ FECHCV = 1.000
+ GEOMOD = 1.000
+ GIDLMOD = 1.000
+ IGCMOD = 1.000
+ IGBMOD = 1.000
+ K1RSCE = 0.000
+ KSATIV = 1.000
+ KT1 = 0.0
+ LINT = 0.000
+ LL = 0.000
+ LLC = 0.000
+ LLN = 1.000
+ LPA = 0.000
+ LPE0 = 5.000n
+ MEXP = 3
+ NC0SUB = 2.86000E+25
+ NGATE = 0.0
+ NI0SUB = 1.10000E+16
+ NIGBINV = 3.000
+ PCLM = 0.000
+ PDIBL1 = 0.300
+ PDIBL2 = 0.000
+ PHIN = 50.00m
+ PRWGS = 0.000
+ PVAG = 0.000
+ QMFACTOR = 0.000
+ RDSWMIN = 0.000
+ RSHS = 2.0
+ RTH0 = 0.05
+ UA = 0.100
+ UA1 = 1.032m
+ UCS = 1.0
+ UD = 1.0
+ UP = 0.000
+ UTE = 0.000
+ UTL = -1.497m
+ WR = 1.000
+ XL = -5.00n
+ IIMOD = 0.0
+ BETAII0 = 0
+ BETAII1 = .028
+ BETAII2 = .067
+ TII = -0.7
+ SII0 = 3.4
+ SII1 = .8
+ SII2 = .08
+ SIID = 0.08
+ ESATII = 1.7e6
+ LII = 3e-9
+ RGATEMOD = 0
+ RGFIN = 100
+ NQSMOD = 0
+ RDSMOD = 0
+ SHMOD = 0

.op
.print dc i(VDS) v(d) v(g) v(b)
.probe dc ids=M1.ids

.temp 27

.end
