*  *       TSMC SPICE MODEL --- Security B --- TSMC Restricted Secret      *
*  *************************************************************************
*    PROCESS :  0.028um LOGIC (1P10M_7X2Z +UT-ALRDL) ELK-IMD (CLN28ULP)
*    MODEL   :  BSIM4 ( V4.5 )
*    VERSION :  V0.1_1p2
*    DATE    :  10:36AM, Nov. 14, 2014
*    HSPICE VERSION : E-2010.12 
****************************************************************************************************
*                   
*  1.LIB TT_res_metal                                                                              *
*        SS_res_metal                                                                              *
*        FF_res_metal                                                                              *
*    (Metal resistance)		                                                                       *                 
****************************************************************************************************     
.LIB setup_res_metal
.param scale_res_metal=0.9
.ENDL setup_res_metal

**************************************************************************
*
*   RESISTANCE MODEL
*
**************************************************************************
.LIB TT_res_metal
.lib 'res_metal.l' setup_res_metal
.param
+r_rm1l            = 0.2153            r_rm1s            = 0.45              r_rm1w            = 0.4675            
+r_rm2l            = 0.195             r_rm2s            = 0.45              r_rm2w            = 0.3967            
+r_rm3l            = 0.195             r_rm3s            = 0.45              r_rm3w            = 0.3967            
+r_rm4l            = 0.195             r_rm4s            = 0.45              r_rm4w            = 0.3967            
+r_rm5l            = 0.195             r_rm5s            = 0.45              r_rm5w            = 0.3967            
+r_rm6l            = 0.195             r_rm6s            = 0.45              r_rm6w            = 0.3967            
+r_rm7l            = 0.195             r_rm7s            = 0.45              r_rm7w            = 0.3967            
+r_rm8l            = 0.195             r_rm8s            = 0.45              r_rm8w            = 0.3967            
+r_rm9l            = 0.0221            r_rm9s            = 0.022             r_rm9w            = 0.0229            
+r_rm10l           = 0.0221            r_rm10s           = 0.022             r_rm10w           = 0.0229            
+r_rmap            = 0.011             r_rmxl            = 0.195             r_rmxs            = 0.45              
+r_rmxw            = 0.3967            r_rmzl            = 0.0221            r_rmzs            = 0.022             
+r_rmzw            = 0.0229            
.lib 'res_metal.l' res_metal
.ENDL TT_res_metal

.LIB SS_res_metal
.lib 'res_metal.l' setup_res_metal
.param
+r_rm1l            = '0.2153 * 1.26'   r_rm1s            = '0.45 * 1.29'     r_rm1w            = '0.4675 * 1.25'   
+r_rm2l            = '0.195 * 1.28'    r_rm2s            = '0.45 * 1.31'     r_rm2w            = '0.3967 * 1.26'   
+r_rm3l            = '0.195 * 1.28'    r_rm3s            = '0.45 * 1.31'     r_rm3w            = '0.3967 * 1.26'   
+r_rm4l            = '0.195 * 1.28'    r_rm4s            = '0.45 * 1.31'     r_rm4w            = '0.3967 * 1.26'   
+r_rm5l            = '0.195 * 1.28'    r_rm5s            = '0.45 * 1.31'     r_rm5w            = '0.3967 * 1.26'   
+r_rm6l            = '0.195 * 1.28'    r_rm6s            = '0.45 * 1.31'     r_rm6w            = '0.3967 * 1.26'   
+r_rm7l            = '0.195 * 1.28'    r_rm7s            = '0.45 * 1.31'     r_rm7w            = '0.3967 * 1.26'   
+r_rm8l            = '0.195 * 1.28'    r_rm8s            = '0.45 * 1.31'     r_rm8w            = '0.3967 * 1.26'   
+r_rm9l            = '0.0221 * 1.19'   r_rm9s            = '0.022 * 1.2'     r_rm9w            = '0.0229 * 1.14'   
+r_rm10l           = '0.0221 * 1.19'   r_rm10s           = '0.022 * 1.2'     r_rm10w           = '0.0229 * 1.14'   
+r_rmap            = '0.011 * 1.2'     r_rmxl            = '0.195 * 1.28'    r_rmxs            = '0.45 * 1.31'     
+r_rmxw            = '0.3967 * 1.26'   r_rmzl            = '0.0221 * 1.19'   r_rmzs            = '0.022 * 1.2'     
+r_rmzw            = '0.0229 * 1.14'   
.lib 'res_metal.l' res_metal
.ENDL SS_res_metal

.LIB FF_res_metal
.lib 'res_metal.l' setup_res_metal
.param
+r_rm1l            = '0.2153 * 0.81'   r_rm1s            = '0.45 * 0.8'      r_rm1w            = '0.4675 * 0.82'   
+r_rm2l            = '0.195 * 0.8'     r_rm2s            = '0.45 * 0.79'     r_rm2w            = '0.3967 * 0.82'   
+r_rm3l            = '0.195 * 0.8'     r_rm3s            = '0.45 * 0.79'     r_rm3w            = '0.3967 * 0.82'   
+r_rm4l            = '0.195 * 0.8'     r_rm4s            = '0.45 * 0.79'     r_rm4w            = '0.3967 * 0.82'   
+r_rm5l            = '0.195 * 0.8'     r_rm5s            = '0.45 * 0.79'     r_rm5w            = '0.3967 * 0.82'   
+r_rm6l            = '0.195 * 0.8'     r_rm6s            = '0.45 * 0.79'     r_rm6w            = '0.3967 * 0.82'   
+r_rm7l            = '0.195 * 0.8'     r_rm7s            = '0.45 * 0.79'     r_rm7w            = '0.3967 * 0.82'   
+r_rm8l            = '0.195 * 0.8'     r_rm8s            = '0.45 * 0.79'     r_rm8w            = '0.3967 * 0.82'   
+r_rm9l            = '0.0221 * 0.85'   r_rm9s            = '0.022 * 0.84'    r_rm9w            = '0.0229 * 0.89'   
+r_rm10l           = '0.0221 * 0.85'   r_rm10s           = '0.022 * 0.84'    r_rm10w           = '0.0229 * 0.89'   
+r_rmap            = '0.011 * 0.8'     r_rmxl            = '0.195 * 0.8'     r_rmxs            = '0.45 * 0.79'     
+r_rmxw            = '0.3967 * 0.82'   r_rmzl            = '0.0221 * 0.85'   r_rmzs            = '0.022 * 0.84'    
+r_rmzw            = '0.0229 * 0.89'   
.lib 'res_metal.l' res_metal
.ENDL FF_res_metal

.LIB res_metal

***********************************     Metal 1 with W/S=0.045/0.135     ***********************************
.subckt rm1l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm1l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.78e-03   ptc2 = -1.94e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm1l

***********************************     Metal 1 with W/S=0.045/0.045     ***********************************
.subckt rm1s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm1s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.75e-03   ptc2 = -3.73e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm1s

***********************************     Metal 1 with W/S=0.135/0.045     ***********************************
.subckt rm1w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm1w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.83e-03   ptc2 = -2.05e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm1w

***********************************     Metal 2 with W/S=0.045/0.135     ***********************************
.subckt rm2l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm2l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm2l

***********************************     Metal 2 with W/S=0.045/0.045     ***********************************
.subckt rm2s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm2s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm2s

***********************************     Metal 2 with W/S=0.135/0.045     ***********************************
.subckt rm2w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm2w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm2w

***********************************     Metal 3 with W/S=0.045/0.135     ***********************************
.subckt rm3l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm3l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm3l

***********************************     Metal 3 with W/S=0.045/0.045     ***********************************
.subckt rm3s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm3s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm3s

***********************************     Metal 3 with W/S=0.135/0.045     ***********************************
.subckt rm3w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm3w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm3w

***********************************     Metal 4 with W/S=0.045/0.135     ***********************************
.subckt rm4l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm4l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm4l

***********************************     Metal 4 with W/S=0.045/0.045     ***********************************
.subckt rm4s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm4s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm4s

***********************************     Metal 4 with W/S=0.135/0.045     ***********************************
.subckt rm4w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm4w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm4w

***********************************     Metal 5 with W/S=0.045/0.135     ***********************************
.subckt rm5l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm5l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm5l

***********************************     Metal 5 with W/S=0.045/0.045     ***********************************
.subckt rm5s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm5s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm5s

***********************************     Metal 5 with W/S=0.135/0.045     ***********************************
.subckt rm5w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm5w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm5w

***********************************     Metal 6 with W/S=0.045/0.135     ***********************************
.subckt rm6l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm6l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm6l

***********************************     Metal 6 with W/S=0.045/0.045     ***********************************
.subckt rm6s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm6s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm6s

***********************************     Metal 6 with W/S=0.135/0.045     ***********************************
.subckt rm6w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm6w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm6w

***********************************     Metal 7 with W/S=0.045/0.135     ***********************************
.subckt rm7l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm7l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm7l

***********************************     Metal 7 with W/S=0.045/0.045     ***********************************
.subckt rm7s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm7s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm7s

***********************************     Metal 7 with W/S=0.135/0.045     ***********************************
.subckt rm7w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm7w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm7w

***********************************     Metal 8 with W/S=0.045/0.135     ***********************************
.subckt rm8l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm8l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm8l

***********************************     Metal 8 with W/S=0.045/0.045     ***********************************
.subckt rm8s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm8s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm8s

***********************************     Metal 8 with W/S=0.135/0.045     ***********************************
.subckt rm8w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm8w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm8w

***********************************     Metal 9 with W/S=0.36/1.08     ***********************************
.subckt rm9l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm9l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.65e-03   ptc2 = -8.53e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm9l

***********************************     Metal 9 with W/S=0.36/0.36     ***********************************
.subckt rm9s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm9s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.65e-03   ptc2 = -8.53e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm9s

***********************************     Metal 9 with W/S=1.08/0.36     ***********************************
.subckt rm9w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm9w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.78e-03   ptc2 = -9.44e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm9w

***********************************     Metal 10 with W/S=0.36/1.08     ***********************************
.subckt rm10l n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm10l
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.65e-03   ptc2 = -8.53e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm10l

***********************************     Metal 10 with W/S=0.36/0.36     ***********************************
.subckt rm10s n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm10s
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.65e-03   ptc2 = -8.53e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm10s

***********************************     Metal 10 with W/S=1.08/0.36     ***********************************
.subckt rm10w n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rm10w
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.78e-03   ptc2 = -9.44e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rm10w

***********************************     AL_RDL with W/S=1.8/1.8     ***********************************
.subckt rmap n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rmap
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.89e-03   ptc2 = -1.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rmap

***********************************     Metal x with W/S=0.045/0.135     ***********************************
.subckt rmxl n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rmxl
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.02e-03   ptc2 = -2.80e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rmxl

***********************************     Metal x with W/S=0.045/0.045     ***********************************
.subckt rmxs n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rmxs
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 1.94e-03   ptc2 = -4.64e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rmxs

***********************************     Metal x with W/S=0.135/0.045     ***********************************
.subckt rmxw n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rmxw
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 2.04e-03   ptc2 = -2.50e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rmxw

***********************************     Metal z with W/S=0.36/1.08     ***********************************
.subckt rmzl n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rmzl
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.65e-03   ptc2 = -8.53e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rmzl

***********************************     Metal z with W/S=0.36/0.36     ***********************************
.subckt rmzs n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rmzs
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.65e-03   ptc2 = -8.53e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rmzs

***********************************     Metal z with W/S=1.08/0.36     ***********************************
.subckt rmzw n1 n2 l=length w=width scale='scale_res_metal' multi=1
.param rsh = r_rmzw
.param dw = 0  
.param pvc1 = 0   pvc2 = 0   ptc1 = 3.78e-03   ptc2 = -9.44e-07   
.param pt='temper'
.param tfac='1.0+ptc1*(pt-25.0)+ptc2*(pt-25.0)*(pt-25.0)'
r1 n1 n2 'rsh/multi*l*scale/(w*scale-dw)*(1+pvc1*(abs(v(n2,n1))/l/scale)+pvc2*(v(n2,n1)/l/scale)*(v(n2,n1)/l/scale))*tfac'
.ends rmzw

.ENDL res_metal