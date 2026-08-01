$****************************************************
$*                CZ6  SPICE MODEL                  *
$*                   MOD001  1/4                    *
$*                   2000/03/27                     *
$*                                                  *
$*             Shanghai Huahong-NEC                 *
$****************************************************
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
$ Model Name: MOD078 1/4                 $
$ Date: 1996/ 4/15                       $
$ (C) NEC Corporation                    $
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
$                                                          $
$         HPSICE inc  file  for CZ6  process               $
$                                                          $
$       Rev. 1.3   Apr.  15, 1996                          $
$                                                          $
$     NOTE : USE THIS MODEL WITH HSPICE VERSION H93A.02    $
$                                                 95.2     $
$            DO NOT USE WITH THE OTHER VERSIONS            $
$                                                          $
$       << NEC CONFIDENTIAL and PROPRIETARY >>             $
$                                                          $
$   Rev. 1.0(MOD054)  First edition. Only Typ model        $
$   Rev. 1.1(MOD055)  Slow model, Fast model added.        $
$                     Temp coefficient added.              $
$   Rev. 1.2(MOD057)  N-Slow,P-Fast model added.           $
$                     N-Fast,P-Slow model added.           $
$   Rev. 1.3(MOD078)  Parameter "wmin" changed from 1.2um  $
$                     to 0.8um.                            $
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
$
$
$
.model n.1 nmos
+ level = 28      
$   Common Model parameters
$+ lmlt  = multl    wmlt  = multl   
+ lref  = 0.49e-6  wref  = 10e-6 
+ xlref = 0        xwref = 0       
+ lmin  = 0.47e-6  lmax  = 0.99e-6 
+ wmin  = 0.8u     wmax  = 1       
+ ld    = 0.00e-6  xl    = xln     
+ wd    = 0.11e-6  xw    = xwn     
+ tox   = toxn     delvto= delvton 
$   Drain-Source Resistors and Capacitance
+ acm   = 3       
+ rsh   = rshn     
+ ldif  = 0.2e-6   hdif  = hdifn   
+ rs    = 1.9943e+3 rd    = 1.9943e+3
+ js    = 4.30e-7  $jsw   = jswn    
+ cj    = cjn      cjsw  = cjswn   
+ mj    = mjn      mjsw  = mjswn   
+ pb    = pbn      $php   = pbn     
+ cjgate= 0       
$   MOS Gate Capacitance
+ capop = 4       
$+ meto  = meton   
+  xqc  = 4.00e-1 
+ cgbo  = 0
+ cgdo  = cgdon    cgso  = cgdon   
$   Temperature Parameters
+ tlev  = 1        
+ tcv   = 471.4650u
+ bex   = -1.6012  
+ fex   = -1.9636  
$   Transistor Process Parameters
+ x2e   = -7.1341m 
+ x3e   = 1.1029m  
+ k1    = 683.3637m
+ k2    = 46.4882m 
+ vfb0  = -371.9567m
+ muz   = muzn
+ u00   = 135.6674m
+ x2m   = -4.9553  
+ x2u0  = -11.4981m
+ wfac  = 15.7054  
+ wfacu = 29.6356m 
+ n0    = 1.4840   
+ nb0   = 3.3733m  
+ u1    = 583.1208m
+ x3u1  = 35.2762m 
+ x3ms  = 1.0000k  
+ x33m  = 6.4475k  
+ b1    = 191.1860m
+ b2    = 436.0067m
+ eta0  = 4.0704m  
+ nd0   = 22.5222m 
+ x2u1  = -1.0207m 
+ lx2e   = -6.921504e-03
+ lx3e   = 1.070034e-03
+ lk1    = -2.192541e-01
+ lk2    = 4.257626e-02
+ lvfb   = 1.488989e-01
+ lmuz   = lmuzn
+ lu0    = 2.404544e-02
+ lx2m   = -1.200865e+01
+ lx2u0  = -9.229125e-03
+ lwfac  = 2.108633e+00
+ lwfacu = -9.147996e-02
+ ln0    = -5.811498e-02
+ lnb    = -7.801747e-02
+ lu1    = 4.641269e-01
+ lx3u1  = -2.295445e-02
+ lx3ms  = 8.274592e+02
+ lx33m  = 4.708381e+03
+ lb1    = -5.344581e-01
+ lb2    = 3.162590e-01
+ leta   = 3.949102e-03
+ lnd    = 1.616974e-02
+ lx2u1  = -1.293092e-02
+ ltcv   = -3.846496e-04
+ lbex   = 1.559111e-01
+ lfex   = 1.351004e+00
$
$
$
.model n.2 nmos
+ level = 28      
$   Common Model parameters
$+ lmlt  = multl    wmlt  = multl   
+ lref  = 0.99e-6  wref  = 10e-6 
+ xlref = 0        xwref = 0       
+ lmin  = 0.99e-6  lmax  = 9.99e-6 
+ wmin  = 0.8u     wmax  = 1       
+ ld    = 0.00e-6  xl    = xln     
+ wd    = 0.11e-6  xw    = xwn     
+ tox   = toxn     delvto= delvton 
$   Drain-Source Resistors and Capacitance
+ acm   = 3       
+ rsh   = rshn     
+ ldif  = 0.2e-6   hdif  = hdifn   
+ rs    = 1.9943e+3 rd    = 1.9943e+3
+ js    = 4.30e-7  $jsw   = jswn    
+ cj    = cjn      cjsw  = cjswn   
+ mj    = mjn      mjsw  = mjswn   
+ pb    = pbn      $php   = pbn     
+ cjgate= 0       
$   MOS Gate Capacitance
+ capop = 4       
$+ meto  = meton   
+  xqc  = 4.00e-1 
+ cgbo  = 0
+ cgdo  = cgdon    cgso  = cgdon   
$   Temperature Parameters
+ tlev  = 1        
+ tcv   = 867.9292u
+ bex   = -1.7619  
+ fex   = -3.3561  
$   Transistor Process Parameters
+ x2e   = 0
+ x3e   = 0
+ k1    = 909.3523m
+ k2    = 2.6042m  
+ vfb0  = -525.4291m
+ muz   = muz2n
+ u00   = 110.8834m
+ x2m   = 7.4222   
+ x2u0  = -1.9855m 
+ wfac  = 13.5320  
+ wfacu = 123.9254m
+ n0    = 1.5439   
+ nb0   = 83.7871m 
+ u1    = 104.7381m
+ x3u1  = 58.9357m 
+ x3ms  = 147.1251 
+ x33m  = 1.5945k  
+ b1    = 742.0602m
+ b2    = 110.0337m
+ eta0  = 0
+ nd0   = 5.8558m  
+ x2u1  = 12.3074m 
+ lx2e   = 0
+ lx3e   = 0
+ lk1    = -2.542118e-02
+ lk2    = 2.849349e-03
+ lvfb   = 8.714310e-02
+ lmuz   = lmuz2n
+ lu0    = 1.195977e-02
+ lx2m   = -1.692702e+01
+ lx2u0  = -1.141779e-02
+ lwfac  = -3.606919e+00
+ lwfacu = -1.124346e-01
+ ln0    = -2.923074e-02
+ lnb    = 2.926393e-02
+ lu1    = 1.200593e-01
+ lx3u1  = 6.476444e-02
+ lx3ms  = 1.603080e+02
+ lx33m  = 1.752116e+03
+ lb1    = -1.375387e-01
+ lb2    = 6.591609e-02
+ leta   = 0
+ lnd    = -2.601536e-03
+ lx2u1  = 1.091988e-02
+ ltcv   = -1.182931e-04
+ lbex   = -1.915383e-01
+ lfex   = -3.298324e+00
$
$
$
.model n.3 nmos
+ level = 28      
$   Common Model parameters
$+ lmlt  = multl    wmlt  = multl   
+ lref  = 9.99e-6  wref  = 10e-6 
+ xlref = 0        xwref = 0       
+ lmin  = 9.99e-6  lmax  = 25e-6   
+ wmin  = 0.8u     wmax  = 1       
+ ld    = 0.00e-6  xl    = xln     
+ wd    = 0.11e-6  xw    = xwn     
+ tox   = toxn     delvto= delvton 
$   Drain-Source Resistors and Capacitance
+ acm   = 3       
+ rsh   = rshn     
+ ldif  = 0.2e-6   hdif  = hdifn   
+ rs    = 1.9943e+3 rd    = 1.9943e+3
+ js    = 4.30e-7  $jsw   = jswn    
+ cj    = cjn      cjsw  = cjswn   
+ mj    = mjn      mjsw  = mjswn   
+ pb    = pbn      $php   = pbn     
+ cjgate= 0       
$   MOS Gate Capacitance
+ capop = 4       
$+ meto  = meton   
+  xqc  = 4.00e-1 
+ cgbo  = 0
+ cgdo  = cgdon    cgso  = cgdon   
$   Temperature Parameters
+ tlev  = 1        
+ tcv   = 975.5760u
+ bex   = -1.5876  
+ fex   = -354.6220m
$   Transistor Process Parameters
+ x2e   = 0
+ x3e   = 0
+ k1    = 932.4856m
+ k2    = 11.2900u 
+ vfb0  = -604.7294m
+ muz   = muz3n
+ u00   = 100.0000m
+ x2m   = 22.8258  
+ x2u0  = 8.4047m  
+ wfac  = 16.8143  
+ wfacu = 226.2410m
+ n0    = 1.5705   
+ nb0   = 57.1569m 
+ u1    = -4.5160m 
+ x3u1  = 0.       
+ x3ms  = 1.2447   
+ x33m  = 72.7590m 
+ b1    = 867.2205m
+ b2    = 50.0500m 
+ eta0  = 0
+ nd0   = 0
+ x2u1  = 2.3703m  
$
$
$
.model p.1 pmos
+ level = 28      
$   Common Model parameters
$+ lmlt  = multl    wmlt  = multl   
+ lref  = 0.47e-6  wref  = 10e-6 
+ xlref = 0        xwref = 0       
+ lmin  = 0.47e-6  lmax  = 0.99e-6 
+ wmin  = 0.8u     wmax  = 1       
+ ld    = 0.04e-6  xl    = xlp     
+ wd    = 0.11e-6  xw    = xwp     
+ tox   = toxp     delvto= delvtop 
$   Drain-Source Resistors and Capacitance
+ acm   = 3       
+ rsh   = rshp     
+ ldif  = 0.2e-6   hdif  = hdifp   
+ rs    = 4.6246e+3 rd    = 4.6246e+3
+ js    = 1.30e-7  $jsw   = jswp    
+ cj    = cjp      cjsw  = cjswp   
+ mj    = mjp      mjsw  = mjswp   
+ pb    = pbp      $php   = pbp     
+ cjgate= 0       
$   MOS Gate Capacitance
+ capop = 4       
$+ meto  = metop   
+ xqc   = 4.00e-1 
+ cgbo  = 0
+ cgdo  = cgdop    cgso  = cgdop   
$   Temperature Parameters
+ tlev  = 1        
+ tcv   = 1.2338m  
+ bex   = -765.9786m
+ fex   = -1.4036  
$   Transistor Process Parameters
+ x2e   = 1.2842m  
+ x3e   = -6.9157m 
+ k1    = 620.4721m
+ k2    = 35.9952m 
+ vfb0  = -360.1143m
+ muz   = muzp
+ u00   = 100.0000m
+ x2m   = 1.5767   
+ x2u0  = -15.1873m
+ wfac  = 13.9691  
+ wfacu = 71.7417m 
+ n0    = 1.6400   
+ nb0   = 20.3711m 
+ u1    = 148.9269m
+ x3u1  = 0.       
+ x3ms  = 46.5298  
+ x33m  = 181.9334 
+ b1    = 766.2217m
+ b2    = 462.8782m
+ eta0  = 80.4356m 
+ nd0   = 45.5799m 
+ x2u1  = 17.0000m 
+ lx2e   = 8.764665e-04
+ lx3e   = -4.719965e-03
+ lk1    = -1.291153e-03
+ lk2    = 2.456672e-02
+ lvfb   = -9.523776e-02
+ lmuz   = lmuzp
+ lu0    = -8.929966e-03
+ lx2m   = -4.659700e+00
+ lx2u0  = -1.842852e-02
+ lwfac  = -1.669941e+00
+ lwfacu = 4.896371e-02
+ ln0    = 1.984710e-01
+ lnb    = -2.353724e-02
+ lu1    = 6.641592e-02
+ lx3u1  = -2.084901e-03
+ lx3ms  = 2.182792e+01
+ lx33m  = 9.717428e+01
+ lb1    = 4.601592e-02
+ lb2    = 3.808370e-02
+ leta   = 5.489730e-02
+ lnd    = 2.722998e-02
+ lx2u1  = 6.281457e-03
+ ltcv   = -2.988667e-04
+ lbex   = 1.149046e-01
+ lfex   = -1.055145e-01
$
$
$
.model p.2 pmos
+ level = 28      
$   Common Model parameters
$+ lmlt  = multl    wmlt  = multl   
+ lref  = 0.99e-6  wref  = 10e-6 
+ xlref = 0        xwref = 0       
+ lmin  = 0.99e-6  lmax  = 9.99e-6 
+ wmin  = 0.8u     wmax  = 1       
+ ld    = 0.04e-6  xl    = xlp     
+ wd    = 0.11e-6  xw    = xwp     
+ tox   = toxp     delvto= delvtop 
$   Drain-Source Resistors and Capacitance
+ acm   = 3       
+ rsh   = rshp     
+ ldif  = 0.2e-6   hdif  = hdifp   
+ rs    = 4.6246e+3 rd    = 4.6246e+3
+ js    = 1.30e-7  $jsw   = jswp    
+ cj    = cjp      cjsw  = cjswp   
+ mj    = mjp      mjsw  = mjswp   
+ pb    = pbp      $php   = pbp     
+ cjgate= 0       
$   MOS Gate Capacitance
+ capop = 4       
$+ meto  = metop   
+ xqc   = 4.00e-1 
+ cgbo  = 0
+ cgdo  = cgdop    cgso  = cgdop   
$   Temperature Parameters
+ tlev  = 1        
+ tcv   = 1.6717m  
+ bex   = -934.3370m
+ fex   = -1.2490  
$   Transistor Process Parameters
+ x2e   = 0        
+ x3e   = 0        
+ k1    = 622.3639m
+ k2    = 0.       
+ vfb0  = -220.5718m
+ muz   = muz2p
+ u00   = 113.0842m
+ x2m   = 8.4041   
+ x2u0  = 11.8142m 
+ wfac  = 16.4159  
+ wfacu = 0.       
+ n0    = 1.3492   
+ nb0   = 54.8579m 
+ u1    = 51.6142m 
+ x3u1  = 3.0548m  
+ x3ms  = 14.5475  
+ x33m  = 39.5535  
+ b1    = 698.7991m
+ b2    = 407.0779m
+ eta0  = 0        
+ nd0   = 5.6825m  
+ x2u1  = 7.7964m  
+ lx2e   = -0.000000e+00
+ lx3e   = -0.000000e+00
+ lk1    = -5.414367e-03
+ lk2    = -0.000000e+00
+ lvfb   = 4.424981e-03
+ lmuz   = lmuz2p
+ lu0    = -1.459439e-02
+ lx2m   = -2.896714e+00
+ lx2u0  = -5.720782e-03
+ lwfac  = 2.099013e+00
+ lwfacu = -1.877963e-01
+ ln0    = -1.042092e-01
+ lnb    = 2.009132e-03
+ lu1    = 5.171479e-02
+ lx3u1  = 3.060944e-03
+ lx3ms  = 1.242804e+01
+ lx33m  = 3.101806e+01
+ lb1    = -2.016055e-01
+ lb2    = 3.125397e-01
+ leta   = -0.000000e+00
+ lnd    = 5.693928e-03
+ lx2u1  = 7.885674e-03
+ ltcv   = 3.381787e-04
+ lbex   = 1.744131e-01
+ lfex   = 5.110257e-02
$
$
$
.model p.3 pmos
+ level = 28      
$   Common Model parameters
$+ lmlt  = multl    wmlt  = multl   
+ lref  = 9.99e-6  wref  = 10e-6 
+ xlref = 0        xwref = 0       
+ lmin  = 9.99e-6  lmax  = 25e-6   
+ wmin  = 0.8u     wmax  = 1       
+ ld    = 0.04e-6  xl    = xlp     
+ wd    = 0.11e-6  xw    = xwp     
+ tox   = toxp     delvto= delvtop 
$   Drain-Source Resistors and Capacitance
+ acm   = 3       
+ rsh   = rshp     
+ ldif  = 0.2e-6   hdif  = hdifp   
+ rs    = 4.6246e+3 rd    = 4.6246e+3
+ js    = 1.30e-7  $jsw   = jswp    
+ cj    = cjp      cjsw  = cjswp   
+ mj    = mjp      mjsw  = mjswp   
+ pb    = pbp      $php   = pbp     
+ cjgate= 0       
$   MOS Gate Capacitance
+ capop = 4       
$+ meto  = metop   
+ xqc   = 4.00e-1 
+ cgbo  = 0
+ cgdo  = cgdop    cgso  = cgdop   
$   Temperature Parameters
+ tlev  = 1        
+ tcv   = 1.3342m
+ bex   = -1.1084
+ fex   = -1.3
$   Transistor Process Parameters
+ x2e   = 0        
+ x3e   = 0        
+ k1    = 627.7674m
+ k2    = 0.
+ vfb0  = -224.9879m
+ muz   = muz3p
+ u00   = 127.6493m
+ x2m   = 11.2950
+ x2u0  = 17.5235m
+ wfac  = 14.3211
+ wfacu = 187.4194m
+ n0    = 1.4532
+ nb0   = 52.8528m
+ u1    = 3.2040u
+ x3u1  = 0.
+ x3ms  = 2.1444
+ x33m  = 8.5977
+ b1    = 900.0000m
+ b2    = 95.1655m
+ eta0  = 0
+ nd0   = 0
+ x2u1  = -73.4470u

