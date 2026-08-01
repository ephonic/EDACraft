# ADC with ideal reference voltage, and with bonding wire model,and coherent sampling 1024 points  
* NETLIST/ADC025S40M.C.RAW
* NETLIST OUTPUT FOR HSPICES.
* GENERATED ON MAY 8 11:23:28 2004
   
* FILE NAME: ADC025S40MSCH_ADC025S40M_SCHEMATIC.S.
* SUBCIRCUIT FOR CELL: ADC025S40M.
* GENERATED FOR: HSPICES.
* GENERATED ON MAY  8 11:23:39 2004.   
   
   
* INCLUDE FILES
.include './ADC018S40MHJV1.net'   
   
   
Iref vdda iref 25uA      
   

.options device temp=27.0000
*.TEMP    25.0000    
.OP
.save
.OPTION  INGOLD=2 post=1
+        PROBE=1 

.option accurate=1 
.option ITL4=100 
.option acct
.option gmindc=1e-6
*.option method=gear
.option nomod
.options timeint delmax=0.1ns
.options NONLIN-TRAN DELTAXTOL=1 RELTOL=1e-3


.param supply=1.8
VDDD VDDD 0 pwl 0 0 10n supply
*VDDD VDDD 0 supply
VSSD VSSD 0 0
VDDA VDDA 0 pwl 0 0 10n supply
*VDDA VDDA 0 supply
VSSA VSSA 0 0
VDDC VDDC 0 pwl 0 0 10n supply
*VDDC VDDC 0 supply
VSSC VSSC 0 0
VSS VSS 0 0


vcminput cminput vss 0.9		$ seperate the input DC bias from CMO
EIP inp cminput VCVS nc vss 0.5		$ to avoid the charge injection of 
EIN inm cminput VCVS nc vss -0.5	$ the bootstrapped switch.

Vi nc vss sin 0V 595mV 7.96875MEG
vpd pd vss 0
vpdb pdb vss 0
vtwos twos vss supply   $ output complementary code by set twos high


.tran 1ns 600ns
.param comvoltage=0.91V


*.print v(inp,inm) v(refp,refn) 
*.print v(inp) v(inm) v(cmo) v(refp) v(refn) 
*.print v(clk) v(pd) 
*.print v(b10) v(b11) v(b20) v(b21) v(b30) v(b31) v(b40) v(b41) 
*.print v(b50) v(b51) v(b60) v(b61) v(b70) v(b71) v(b80) v(b81)
*.print v(b90) v(b91) 


*.print  v(vsp,vsn)     
*.print  v(op12,on12) 
*.print  v(op34,on34) 
*.print  v(op56,on56) 
*.print  v(op78,on78)   



*.print v(XISTG12.QN1B) v(XISTG12.QP1B) v(XISTG12.QN1B) v(XISTG12.QN1) v(XISTG12.QP1) v(XISTG12.QC1) 
*.print v(XISTG12.QC1B) v(XISTG12.CIMB1) v(XISTG12.CIPB1) v(XISTG12.P11) v(XISTG12.P11D) v(XISTG12.P21D) 
*.print v(XISTG12.P12D) v(XISTG12.P22D)  v(XISTG12.P22)
*.print v(XISTG12.INM) v(XISTG12.INP)  v(XISTG12.INP,XISTG12.INM)
*.print v(XISTG12.L1OOO) v(XISTG12.L1OO)  v(XISTG12.P11DB) v(XISTG12.INMP,XISTG12.INPM)



*.print v(b9) v(b8) v(b7) v(b6) v(b5) v(b4) v(b3) v(b2) v(b1) v(b0)
.print v(b9) v(b8) v(b7) v(b6) v(b5) v(b4) v(b3) v(b2) v(b1) v(b0)


*.print v(xistg12.l1o) v(xistg12.l2o)
*.print v(latch9) 
*.print lx1(crefp) lx1(ccm) lx1(crefn)

*.print v(LATCH9)

*.print v(XI16.NET059) v(XI16.NET24)




.prot
*.lib 'MM180_REG18_V123.LIB' tt
.inc 'model_b.inc'
.unprot

vrefp refp 0 1.24
vrefn refn 0 0.62
vcmo  cmo  0 0.96

 
VCLK CLK 0 PULSE 0 supply 2.0ns 1ns 1ns 11.5ns 25ns

.END
   
  
