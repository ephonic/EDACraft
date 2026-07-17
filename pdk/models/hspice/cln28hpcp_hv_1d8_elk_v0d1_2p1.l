*  **************************************************************   
*  *  TSMC SPICE MODEL --- Security B - TSMC Restricted Secret  *   
*  **************************************************************   
*   
*    PROCESS :  0.028um LOGIC HIGH PERFORMANCE COMPACT MOBILE COMPUTING PLUS High Voltage 1.8V SPICE MODEL 28HPC+ (5V HVMOS)   
*    MODEL   :  BSIM4 ( V4.5 )   
*    DOC. NO.:  T-N28-CL-SP-083  
*    VERSION :  v0.1_2p1   
*    DATE    :  06:15PM, Aug. 15, 2015   
*    HSPICE VERSION : I-2013.12-SP2-2   
*   
****************************************************************************************************  
* Release Note:							                       					                                       *  
*									                         					                       					               *  
*    Date         Version	  Description	  				 					                                       *  
* 1. 2015/08/15   v0.1_2p1    1. Copy from T-N28-CL-SP-043 for 1.8V/5V HVMOS.                        *  
****************************************************************************************************   
****************************************************************************************************   
* THIS MODEL LIB CONTAINS :                                                                        *   
*                                                                                                  *   
*  1.LIB stat_hv                                                                                   *   
*    (MOSFET Common used statistical library)                                                      *   
*                                                                                                  *   
*  2.LIB global_hv18                                                                               *   
*    (1.8V I/O HV devices with different geometric and global monte carlo models)                  *   
*                                                                                                  *   
*  3.LIB Total_hv18                                                                                *   
*    (1.8V I/O HV devices with different geometric and total monte carlo models)                   *   
*                                                                                                  *   
*  4.LIB ttg_hv18                                                                                  *   
*        ssg_hv18                                                                                  *   
*        ffg_hv18                                                                                  *   
*        sfg_hv18                                                                                  *   
*        fsg_hv18                                                                                  *   
*    (1.8V I/O HV devices with different geometric and global corner models)                       *   
*                                                                                                  *   
*  5.LIB TT_hv18                                                                                   *   
*        SS_hv18                                                                                   *   
*        FF_hv18                                                                                   *   
*        SF_hv18                                                                                   *   
*        FS_hv18                                                                                   *   
*    (1.8V I/O HV devices with different geometric and corner models)                              *   
*                                                                                                  *   
****************************************************************************************************   
   
  
.LIB setup_hv18    
.param ccoflag_hv18=0    
.param rgflag_hv18=0    
.param sigma_factor_hv18=1    
.param rcoflag_hv18=0    
.param scale_mos_hv18=0.9    
.param totalflag_mos_hv18=1    
.param globalflag_mos_hv18=1    
.param mismatchflag_mos_hv18=1    
.param global_factor_hv18=1    
.param local_factor_hv18=1    
.ENDL setup_hv18    
    
.LIB stat_hv  
.param   
   
+r1_hv=agauss(0,1,1) r2_hv=agauss(0,1,1) r3_hv=agauss(0,1,1) r4_hv=agauss(0,1,1) r5_hv=agauss(0,1,1)    
+par1_hv=r1_hv par2_hv=r2_hv par3_hv=r3_hv par4_hv=r4_hv par5_hv=r5_hv    
+r6_hv=agauss(0,1,1) r7_hv=0             r8_hv=0             r9_hv=0             r10_hv=0    
+par6_hv=r6_hv par7_hv=r7_hv par8_hv=r8_hv par9_hv=r9_hv par10_hv=r10_hv    
+r11_hv=agauss(0,1,1) r12_hv=agauss(0,1,1) r13_hv=agauss(0,1,1) r14_hv=agauss(0,1,1) r15_hv=agauss(0,1,1)    
+par11_hv=r11_hv par12_hv=r12_hv par13_hv=r13_hv par14_hv=r14_hv par15_hv=r15_hv    
+r16_hv=agauss(0,1,1) r17_hv=0             r18_hv=0             r19_hv=0             r20_hv=0    
+par16_hv=r16_hv par17_hv=r17_hv par18_hv=r18_hv par19_hv=r19_hv par20_hv=r20_hv    
+r21_hv=agauss(0,1,1) r22_hv=agauss(0,1,1) r23_hv=agauss(0,1,1) r24_hv=agauss(0,1,1) r25_hv=agauss(0,1,1)    
+par21_hv=r21_hv par22_hv=r22_hv par23_hv=r23_hv par24_hv=r24_hv par25_hv=r25_hv    
+r26_hv=agauss(0,1,1) r27_hv=0             r28_hv=0             r29_hv=0             r30_hv=0    
+par26_hv=r26_hv par27_hv=r27_hv par28_hv=r28_hv par29_hv=r29_hv par30_hv=r30_hv    
+r31_hv=agauss(0,1,1) r32_hv=agauss(0,1,1)    
+par31_hv=r31_hv par32_hv=r32_hv    
   
+r1_io_hv=agauss(0,1,1) r2_io_hv=agauss(0,1,1) r3_io_hv=agauss(0,1,1) r4_io_hv=agauss(0,1,1) r5_io_hv=agauss(0,1,1)    
+par1_io_hv=r1_io_hv par2_io_hv=r2_io_hv par3_io_hv=r3_io_hv par4_io_hv=r4_io_hv par5_io_hv=r5_io_hv    
+r6_io_hv=agauss(0,1,1) r7_io_hv=agauss(0,1,1) r8_io_hv=agauss(0,1,1) r9_io_hv=agauss(0,1,1) r10_io_hv=agauss(0,1,1)    
+par6_io_hv=r6_io_hv par7_io_hv=r7_io_hv par8_io_hv=r8_io_hv par9_io_hv=r9_io_hv par10_io_hv=r10_io_hv    
+r11_io_hv=agauss(0,1,1) r12_io_hv=agauss(0,1,1) r13_io_hv=agauss(0,1,1) r14_io_hv=agauss(0,1,1) r15_io_hv=agauss(0,1,1)    
+par11_io_hv=r11_io_hv par12_io_hv=r12_io_hv par13_io_hv=r13_io_hv par14_io_hv=r14_io_hv par15_io_hv=r15_io_hv    
+r16_io_hv=agauss(0,1,1) r17_io_hv=agauss(0,1,1) r18_io_hv=agauss(0,1,1) r19_io_hv=agauss(0,1,1) r20_io_hv=agauss(0,1,1)    
+par16_io_hv=r16_io_hv par17_io_hv=r17_io_hv par18_io_hv=r18_io_hv par19_io_hv=r19_io_hv par20_io_hv=r20_io_hv    
   
+plo_tox_hv=agauss(0,1,1) plo_dxl_hv=agauss(0,1,1) plo_dxw_hv=agauss(0,1,1)   
+parl1_hv =agauss(0,1,1) parl2_hv =agauss(0,1,1)   
   
+r1_cap_hv=agauss(0,1,1) r2_cap_hv=agauss(0,1,1)   
+par1_cap_hv=r1_cap_hv par2_cap_hv=r2_cap_hv   
   
+w1_c_hv='2.0125*0.40825' w2_c_hv='0.86603*-0.40825' w3_c_hv='0.54772*0.22744' w4_c_hv='0.54772*-0.40547' w5_c_hv='0.54772*-0.12313' w6_c_hv='0.54772*0.65982' w7_c_hv=0 w8_c_hv=0 w9_c_hv=0 w10_c_hv=0    
+w11_c_hv='2.0125*0.40825' w12_c_hv='0.86603*0.40825' w13_c_hv='0.54772*-0.32234' w14_c_hv='0.54772*-0.3726' w15_c_hv='0.54772*-0.60858' w16_c_hv='0.54772*-0.23143' w17_c_hv=0 w18_c_hv=0 w19_c_hv=0 w20_c_hv=0    
+w21_c_hv='2.0125*0.40825' w22_c_hv='0.86603*-0.40825' w23_c_hv='0.54772*0.41074' w24_c_hv='0.54772*0.45095' w25_c_hv='0.54772*-0.32968' w26_c_hv='0.54772*-0.43118' w27_c_hv=0 w28_c_hv=0 w29_c_hv=0 w30_c_hv=0    
+w31_c_hv='2.0125*0.40825' w32_c_hv='0.86603*0.40825' w33_c_hv='0.54772*-0.16779' w34_c_hv='0.54772*0.6456' w35_c_hv='0.54772*0.063924' w36_c_hv='0.54772*0.4665' w37_c_hv=0 w38_c_hv=0 w39_c_hv=0 w40_c_hv=0    
+w41_c_hv='2.0125*0.40825' w42_c_hv='0.86603*-0.40825' w43_c_hv='0.54772*-0.63819' w44_c_hv='0.54772*-0.045477' w45_c_hv='0.54772*0.45281' w46_c_hv='0.54772*-0.22865' w47_c_hv=0 w48_c_hv=0 w49_c_hv=0 w50_c_hv=0    
+w51_c_hv='2.0125*0.40825' w52_c_hv='0.86603*0.40825' w53_c_hv='0.54772*0.49013' w54_c_hv='0.54772*-0.273' w55_c_hv='0.54772*0.54466' w56_c_hv='0.54772*-0.23507' w57_c_hv=0 w58_c_hv=0 w59_c_hv=0 w60_c_hv=0    
+w61_c_hv=0 w62_c_hv=0 w63_c_hv=0 w64_c_hv=0 w65_c_hv=0 w66_c_hv=0 w67_c_hv=0 w68_c_hv=0 w69_c_hv=0 w70_c_hv=0    
+w71_c_hv=0 w72_c_hv=0 w73_c_hv=0 w74_c_hv=0 w75_c_hv=0 w76_c_hv=0 w77_c_hv=0 w78_c_hv=0 w79_c_hv=0 w80_c_hv=0    
+w81_c_hv=0 w82_c_hv=0 w83_c_hv=0 w84_c_hv=0 w85_c_hv=0 w86_c_hv=0 w87_c_hv=0 w88_c_hv=0 w89_c_hv=0 w90_c_hv=0    
+w91_c_hv=0 w92_c_hv=0 w93_c_hv=0 w94_c_hv=0 w95_c_hv=0 w96_c_hv=0 w97_c_hv=0 w98_c_hv=0 w99_c_hv=0 w100_c_hv=0    
   
+w1_io_hv='2.0125*0.40825' w2_io_hv='0.86603*-0.40825' w3_io_hv='0.54772*0.22744' w4_io_hv='0.54772*-0.40547' w5_io_hv='0.54772*-0.12313' w6_io_hv='0.54772*0.65982'    
+w7_io_hv='2.0125*0.40825' w8_io_hv='0.86603*0.40825' w9_io_hv='0.54772*-0.32234' w10_io_hv='0.54772*-0.3726' w11_io_hv='0.54772*-0.60858' w12_io_hv='0.54772*-0.23143'    
+w13_io_hv='2.0125*0.40825' w14_io_hv='0.86603*-0.40825' w15_io_hv='0.54772*0.41074' w16_io_hv='0.54772*0.45095' w17_io_hv='0.54772*-0.32968' w18_io_hv='0.54772*-0.43118'    
+w19_io_hv='2.0125*0.40825' w20_io_hv='0.86603*0.40825' w21_io_hv='0.54772*-0.16779' w22_io_hv='0.54772*0.6456' w23_io_hv='0.54772*0.063924' w24_io_hv='0.54772*0.4665'    
+w25_io_hv='2.0125*0.40825' w26_io_hv='0.86603*-0.40825' w27_io_hv='0.54772*-0.63819' w28_io_hv='0.54772*-0.045477' w29_io_hv='0.54772*0.45281' w30_io_hv='0.54772*-0.22865'    
+w31_io_hv='2.0125*0.40825' w32_io_hv='0.86603*0.40825' w33_io_hv='0.54772*0.49013' w34_io_hv='0.54772*-0.273' w35_io_hv='0.54772*0.54466' w36_io_hv='0.54772*-0.23507'    
   
+p1_c1n_hv='w1_c_hv*par1_hv+w2_c_hv*par2_hv+w3_c_hv*par3_hv+w4_c_hv*par4_hv+w5_c_hv*par5_hv+w6_c_hv*par6_hv+w7_c_hv*par7_hv+w8_c_hv*par8_hv+w9_c_hv*par9_hv+w10_c_hv*par10_hv'   
+p1_c1p_hv='w11_c_hv*par1_hv+w12_c_hv*par2_hv+w13_c_hv*par3_hv+w14_c_hv*par4_hv+w15_c_hv*par5_hv+w16_c_hv*par6_hv+w17_c_hv*par7_hv+w18_c_hv*par8_hv+w19_c_hv*par9_hv+w20_c_hv*par10_hv'   
+p1_c2n_hv='w21_c_hv*par1_hv+w22_c_hv*par2_hv+w23_c_hv*par3_hv+w24_c_hv*par4_hv+w25_c_hv*par5_hv+w26_c_hv*par6_hv+w27_c_hv*par7_hv+w28_c_hv*par8_hv+w29_c_hv*par9_hv+w30_c_hv*par10_hv'   
+p1_c2p_hv='w31_c_hv*par1_hv+w32_c_hv*par2_hv+w33_c_hv*par3_hv+w34_c_hv*par4_hv+w35_c_hv*par5_hv+w36_c_hv*par6_hv+w37_c_hv*par7_hv+w38_c_hv*par8_hv+w39_c_hv*par9_hv+w40_c_hv*par10_hv'   
+p1_c3n_hv='w41_c_hv*par1_hv+w42_c_hv*par2_hv+w43_c_hv*par3_hv+w44_c_hv*par4_hv+w45_c_hv*par5_hv+w46_c_hv*par6_hv+w47_c_hv*par7_hv+w48_c_hv*par8_hv+w49_c_hv*par9_hv+w50_c_hv*par10_hv'   
+p1_c3p_hv='w51_c_hv*par1_hv+w52_c_hv*par2_hv+w53_c_hv*par3_hv+w54_c_hv*par4_hv+w55_c_hv*par5_hv+w56_c_hv*par6_hv+w57_c_hv*par7_hv+w58_c_hv*par8_hv+w59_c_hv*par9_hv+w60_c_hv*par10_hv'   
+p1_c4n_hv='w61_c_hv*par1_hv+w62_c_hv*par2_hv+w63_c_hv*par3_hv+w64_c_hv*par4_hv+w65_c_hv*par5_hv+w66_c_hv*par6_hv+w67_c_hv*par7_hv+w68_c_hv*par8_hv+w69_c_hv*par9_hv+w70_c_hv*par10_hv'   
+p1_c4p_hv='w71_c_hv*par1_hv+w72_c_hv*par2_hv+w73_c_hv*par3_hv+w74_c_hv*par4_hv+w75_c_hv*par5_hv+w76_c_hv*par6_hv+w77_c_hv*par7_hv+w78_c_hv*par8_hv+w79_c_hv*par9_hv+w80_c_hv*par10_hv'   
+p1_c5n_hv='w81_c_hv*par1_hv+w82_c_hv*par2_hv+w83_c_hv*par3_hv+w84_c_hv*par4_hv+w85_c_hv*par5_hv+w86_c_hv*par6_hv+w87_c_hv*par7_hv+w88_c_hv*par8_hv+w89_c_hv*par9_hv+w90_c_hv*par10_hv'   
+p1_c5p_hv='w91_c_hv*par1_hv+w92_c_hv*par2_hv+w93_c_hv*par3_hv+w94_c_hv*par4_hv+w95_c_hv*par5_hv+w96_c_hv*par6_hv+w97_c_hv*par7_hv+w98_c_hv*par8_hv+w99_c_hv*par9_hv+w100_c_hv*par10_hv'   
   
+p2_c1n_hv='w1_c_hv*par11_hv+w2_c_hv*par12_hv+w3_c_hv*par13_hv+w4_c_hv*par14_hv+w5_c_hv*par15_hv+w6_c_hv*par16_hv+w7_c_hv*par17_hv+w8_c_hv*par18_hv+w9_c_hv*par19_hv+w10_c_hv*par20_hv'   
+p2_c1p_hv='w11_c_hv*par11_hv+w12_c_hv*par12_hv+w13_c_hv*par13_hv+w14_c_hv*par14_hv+w15_c_hv*par15_hv+w16_c_hv*par16_hv+w17_c_hv*par17_hv+w18_c_hv*par18_hv+w19_c_hv*par19_hv+w20_c_hv*par20_hv'   
+p2_c2n_hv='w21_c_hv*par11_hv+w22_c_hv*par12_hv+w23_c_hv*par13_hv+w24_c_hv*par14_hv+w25_c_hv*par15_hv+w26_c_hv*par16_hv+w27_c_hv*par17_hv+w28_c_hv*par18_hv+w29_c_hv*par19_hv+w30_c_hv*par20_hv'   
+p2_c2p_hv='w31_c_hv*par11_hv+w32_c_hv*par12_hv+w33_c_hv*par13_hv+w34_c_hv*par14_hv+w35_c_hv*par15_hv+w36_c_hv*par16_hv+w37_c_hv*par17_hv+w38_c_hv*par18_hv+w39_c_hv*par19_hv+w40_c_hv*par20_hv'   
+p2_c3n_hv='w41_c_hv*par11_hv+w42_c_hv*par12_hv+w43_c_hv*par13_hv+w44_c_hv*par14_hv+w45_c_hv*par15_hv+w46_c_hv*par16_hv+w47_c_hv*par17_hv+w48_c_hv*par18_hv+w49_c_hv*par19_hv+w50_c_hv*par20_hv'   
+p2_c3p_hv='w51_c_hv*par11_hv+w52_c_hv*par12_hv+w53_c_hv*par13_hv+w54_c_hv*par14_hv+w55_c_hv*par15_hv+w56_c_hv*par16_hv+w57_c_hv*par17_hv+w58_c_hv*par18_hv+w59_c_hv*par19_hv+w60_c_hv*par20_hv'   
+p2_c4n_hv='w61_c_hv*par11_hv+w62_c_hv*par12_hv+w63_c_hv*par13_hv+w64_c_hv*par14_hv+w65_c_hv*par15_hv+w66_c_hv*par16_hv+w67_c_hv*par17_hv+w68_c_hv*par18_hv+w69_c_hv*par19_hv+w70_c_hv*par20_hv'   
+p2_c4p_hv='w71_c_hv*par11_hv+w72_c_hv*par12_hv+w73_c_hv*par13_hv+w74_c_hv*par14_hv+w75_c_hv*par15_hv+w76_c_hv*par16_hv+w77_c_hv*par17_hv+w78_c_hv*par18_hv+w79_c_hv*par19_hv+w80_c_hv*par20_hv'   
+p2_c5n_hv='w81_c_hv*par11_hv+w82_c_hv*par12_hv+w83_c_hv*par13_hv+w84_c_hv*par14_hv+w85_c_hv*par15_hv+w86_c_hv*par16_hv+w87_c_hv*par17_hv+w88_c_hv*par18_hv+w89_c_hv*par19_hv+w90_c_hv*par20_hv'   
+p2_c5p_hv='w91_c_hv*par11_hv+w92_c_hv*par12_hv+w93_c_hv*par13_hv+w94_c_hv*par14_hv+w95_c_hv*par15_hv+w96_c_hv*par16_hv+w97_c_hv*par17_hv+w98_c_hv*par18_hv+w99_c_hv*par19_hv+w100_c_hv*par20_hv'   
   
+p3_c1n_hv='w1_c_hv*par21_hv+w2_c_hv*par22_hv+w3_c_hv*par23_hv+w4_c_hv*par24_hv+w5_c_hv*par25_hv+w6_c_hv*par26_hv+w7_c_hv*par27_hv+w8_c_hv*par28_hv+w9_c_hv*par29_hv+w10_c_hv*par30_hv'   
+p3_c1p_hv='w11_c_hv*par21_hv+w12_c_hv*par22_hv+w13_c_hv*par23_hv+w14_c_hv*par24_hv+w15_c_hv*par25_hv+w16_c_hv*par26_hv+w17_c_hv*par27_hv+w18_c_hv*par28_hv+w19_c_hv*par29_hv+w20_c_hv*par30_hv'   
+p3_c2n_hv='w21_c_hv*par21_hv+w22_c_hv*par22_hv+w23_c_hv*par23_hv+w24_c_hv*par24_hv+w25_c_hv*par25_hv+w26_c_hv*par26_hv+w27_c_hv*par27_hv+w28_c_hv*par28_hv+w29_c_hv*par29_hv+w30_c_hv*par30_hv'   
+p3_c2p_hv='w31_c_hv*par21_hv+w32_c_hv*par22_hv+w33_c_hv*par23_hv+w34_c_hv*par24_hv+w35_c_hv*par25_hv+w36_c_hv*par26_hv+w37_c_hv*par27_hv+w38_c_hv*par28_hv+w39_c_hv*par29_hv+w40_c_hv*par30_hv'   
+p3_c3n_hv='w41_c_hv*par21_hv+w42_c_hv*par22_hv+w43_c_hv*par23_hv+w44_c_hv*par24_hv+w45_c_hv*par25_hv+w46_c_hv*par26_hv+w47_c_hv*par27_hv+w48_c_hv*par28_hv+w49_c_hv*par29_hv+w50_c_hv*par30_hv'   
+p3_c3p_hv='w51_c_hv*par21_hv+w52_c_hv*par22_hv+w53_c_hv*par23_hv+w54_c_hv*par24_hv+w55_c_hv*par25_hv+w56_c_hv*par26_hv+w57_c_hv*par27_hv+w58_c_hv*par28_hv+w59_c_hv*par29_hv+w60_c_hv*par30_hv'   
+p3_c4n_hv='w61_c_hv*par21_hv+w62_c_hv*par22_hv+w63_c_hv*par23_hv+w64_c_hv*par24_hv+w65_c_hv*par25_hv+w66_c_hv*par26_hv+w67_c_hv*par27_hv+w68_c_hv*par28_hv+w69_c_hv*par29_hv+w70_c_hv*par30_hv'   
+p3_c4p_hv='w71_c_hv*par21_hv+w72_c_hv*par22_hv+w73_c_hv*par23_hv+w74_c_hv*par24_hv+w75_c_hv*par25_hv+w76_c_hv*par26_hv+w77_c_hv*par27_hv+w78_c_hv*par28_hv+w79_c_hv*par29_hv+w80_c_hv*par30_hv'   
+p3_c5n_hv='w81_c_hv*par21_hv+w82_c_hv*par22_hv+w83_c_hv*par23_hv+w84_c_hv*par24_hv+w85_c_hv*par25_hv+w86_c_hv*par26_hv+w87_c_hv*par27_hv+w88_c_hv*par28_hv+w89_c_hv*par29_hv+w90_c_hv*par30_hv'   
+p3_c5p_hv='w91_c_hv*par21_hv+w92_c_hv*par22_hv+w93_c_hv*par23_hv+w94_c_hv*par24_hv+w95_c_hv*par25_hv+w96_c_hv*par26_hv+w97_c_hv*par27_hv+w98_c_hv*par28_hv+w99_c_hv*par29_hv+w100_c_hv*par30_hv'   
   
+p4_c1n_hv='par31_hv'   
+p4_c1p_hv='par31_hv'   
+p4_c2n_hv='par31_hv'   
+p4_c2p_hv='par31_hv'   
+p4_c3n_hv='par31_hv'   
+p4_c3p_hv='par31_hv'   
+p4_c4n_hv='par31_hv'   
+p4_c4p_hv='par31_hv'   
+p4_c5n_hv='par31_hv'   
+p4_c5p_hv='par31_hv'   
   
+p5_c1n_hv='par32_hv'   
+p5_c1p_hv='par32_hv'   
+p5_c2n_hv='par32_hv'   
+p5_c2p_hv='par32_hv'   
+p5_c3n_hv='par32_hv'   
+p5_c3p_hv='par32_hv'   
+p5_c4n_hv='par32_hv'   
+p5_c4p_hv='par32_hv'   
+p5_c5n_hv='par32_hv'   
+p5_c5p_hv='par32_hv'   
   
+p1_io1n_hv='w1_io_hv*par1_io_hv+w2_io_hv*par2_io_hv+w3_io_hv*par3_io_hv+w4_io_hv*par4_io_hv+w5_io_hv*par5_io_hv+w6_io_hv*par6_io_hv'   
+p1_io1p_hv='w7_io_hv*par1_io_hv+w8_io_hv*par2_io_hv+w9_io_hv*par3_io_hv+w10_io_hv*par4_io_hv+w11_io_hv*par5_io_hv+w12_io_hv*par6_io_hv'   
+p1_io2n_hv='w13_io_hv*par1_io_hv+w14_io_hv*par2_io_hv+w15_io_hv*par3_io_hv+w16_io_hv*par4_io_hv+w17_io_hv*par5_io_hv+w18_io_hv*par6_io_hv'   
+p1_io2p_hv='w19_io_hv*par1_io_hv+w20_io_hv*par2_io_hv+w21_io_hv*par3_io_hv+w22_io_hv*par4_io_hv+w23_io_hv*par5_io_hv+w24_io_hv*par6_io_hv'   
+p1_io3n_hv='w25_io_hv*par1_io_hv+w26_io_hv*par2_io_hv+w27_io_hv*par3_io_hv+w28_io_hv*par4_io_hv+w29_io_hv*par5_io_hv+w30_io_hv*par6_io_hv'   
+p1_io3p_hv='w31_io_hv*par1_io_hv+w32_io_hv*par2_io_hv+w33_io_hv*par3_io_hv+w34_io_hv*par4_io_hv+w35_io_hv*par5_io_hv+w36_io_hv*par6_io_hv'   
   
+p2_io1n_hv='w1_io_hv*par7_io_hv+w2_io_hv*par8_io_hv+w3_io_hv*par9_io_hv+w4_io_hv*par10_io_hv+w5_io_hv*par11_io_hv+w6_io_hv*par12_io_hv'   
+p2_io1p_hv='w7_io_hv*par7_io_hv+w8_io_hv*par8_io_hv+w9_io_hv*par9_io_hv+w10_io_hv*par10_io_hv+w11_io_hv*par11_io_hv+w12_io_hv*par12_io_hv'   
+p2_io2n_hv='w13_io_hv*par7_io_hv+w14_io_hv*par8_io_hv+w15_io_hv*par9_io_hv+w16_io_hv*par10_io_hv+w17_io_hv*par11_io_hv+w18_io_hv*par12_io_hv'   
+p2_io2p_hv='w19_io_hv*par7_io_hv+w20_io_hv*par8_io_hv+w21_io_hv*par9_io_hv+w22_io_hv*par10_io_hv+w23_io_hv*par11_io_hv+w24_io_hv*par12_io_hv'   
+p2_io3n_hv='w25_io_hv*par7_io_hv+w26_io_hv*par8_io_hv+w27_io_hv*par9_io_hv+w28_io_hv*par10_io_hv+w29_io_hv*par11_io_hv+w30_io_hv*par12_io_hv'   
+p2_io3p_hv='w31_io_hv*par7_io_hv+w32_io_hv*par8_io_hv+w33_io_hv*par9_io_hv+w34_io_hv*par10_io_hv+w35_io_hv*par11_io_hv+w36_io_hv*par12_io_hv'   
   
+p3_io1n_hv='w1_io_hv*par13_io_hv+w2_io_hv*par14_io_hv+w3_io_hv*par15_io_hv+w4_io_hv*par16_io_hv+w5_io_hv*par17_io_hv+w6_io_hv*par18_io_hv'   
+p3_io1p_hv='w7_io_hv*par13_io_hv+w8_io_hv*par14_io_hv+w9_io_hv*par15_io_hv+w10_io_hv*par16_io_hv+w11_io_hv*par17_io_hv+w12_io_hv*par18_io_hv'   
+p3_io2n_hv='w13_io_hv*par13_io_hv+w14_io_hv*par14_io_hv+w15_io_hv*par15_io_hv+w16_io_hv*par16_io_hv+w17_io_hv*par17_io_hv+w18_io_hv*par18_io_hv'   
+p3_io2p_hv='w19_io_hv*par13_io_hv+w20_io_hv*par14_io_hv+w21_io_hv*par15_io_hv+w22_io_hv*par16_io_hv+w23_io_hv*par17_io_hv+w24_io_hv*par18_io_hv'   
+p3_io3n_hv='w25_io_hv*par13_io_hv+w26_io_hv*par14_io_hv+w27_io_hv*par15_io_hv+w28_io_hv*par16_io_hv+w29_io_hv*par17_io_hv+w30_io_hv*par18_io_hv'   
+p3_io3p_hv='w31_io_hv*par13_io_hv+w32_io_hv*par14_io_hv+w33_io_hv*par15_io_hv+w34_io_hv*par16_io_hv+w35_io_hv*par17_io_hv+w36_io_hv*par18_io_hv'   
   
+p4_io1n_hv='par19_io_hv'   
+p4_io1p_hv='par19_io_hv'   
+p4_io2n_hv='par19_io_hv'   
+p4_io2p_hv='par19_io_hv'   
+p4_io3n_hv='par19_io_hv'   
+p4_io3p_hv='par19_io_hv'   
   
+p5_io1n_hv='par20_io_hv'   
+p5_io1p_hv='par20_io_hv'   
+p5_io2n_hv='par20_io_hv'   
+p5_io2p_hv='par20_io_hv'   
+p5_io3n_hv='par20_io_hv'   
+p5_io3p_hv='par20_io_hv'   
   
.ENDL stat_hv   
    
.LIB ttg_hv18    
.param    
+toxp_hv18_ms_global        = 0    
+dxlp_hv18_ms_global        = 0    
+dxwp_hv18_ms_global        = 0    
+cjsp_hv18_ms_global        = 0    
+cjswsp_hv18_ms_global      = 0    
+cjswgsp_hv18_ms_global     = 0    
+cjdp_hv18_ms_global        = 0    
+cjswdp_hv18_ms_global      = 0    
+cjswgdp_hv18_ms_global     = 0    
+cgdop_hv18_ms_global       = 0    
+cgsop_hv18_ms_global       = 0    
+cgdlp_hv18_ms_global       = 0    
+cgslp_hv18_ms_global       = 0    
+cfsp_hv18_ms_global        = 0    
+cfdsp_hv18_ms_global       = 0    
+dvthp_hv18_ms_global       = 0    
+dlvthp_hv18_ms_global      = 0    
+dwvthp_hv18_ms_global      = 0    
+dpvthp_hv18_ms_global      = 0    
+du0p_hv18_ms_global        = 0    
+dlu0p_hv18_ms_global       = 0    
+dwu0p_hv18_ms_global       = 0    
+dpu0p_hv18_ms_global       = 0    
+dvsatp_hv18_ms_global      = 0    
+dcitp_hv18_ms_global       = 0    
+da0p_hv18_ms_global        = 0    
+dla0p_hv18_ms_global       = 0    
+dwa0p_hv18_ms_global       = 0    
+dpa0p_hv18_ms_global       = 0    
+ss_flagp_hv18_ms_global    = 0    
+ff_flagp_hv18_ms_global    = 0    
+monte_flagp_hv18_ms_global = 0    
+sf_flagp_hv18_ms_global    = 0    
+fs_flagp_hv18_ms_global    = 0    
.param    
+toxn_hv18_ms_global        = 0    
+dxln_hv18_ms_global        = 0    
+dxwn_hv18_ms_global        = 0    
+cjsn_hv18_ms_global        = 0    
+cjswsn_hv18_ms_global      = 0    
+cjswgsn_hv18_ms_global     = 0    
+cjdn_hv18_ms_global        = 0    
+cjswdn_hv18_ms_global      = 0    
+cjswgdn_hv18_ms_global     = 0    
+cfsn_hv18_ms_global        = 0    
+cfdsn_hv18_ms_global       = 0    
+cgdln_hv18_ms_global       = 0    
+cgsln_hv18_ms_global       = 0    
+cgdon_hv18_ms_global       = 0    
+cgson_hv18_ms_global       = 0    
+dvthn_hv18_ms_global       = 0    
+dlvthn_hv18_ms_global      = 0    
+dwvthn_hv18_ms_global      = 0    
+dpvthn_hv18_ms_global      = 0    
+dcitn_hv18_ms_global       = 0    
+du0n_hv18_ms_global        = 0    
+dlu0n_hv18_ms_global       = 0    
+dwu0n_hv18_ms_global       = 0    
+dpu0n_hv18_ms_global       = 0    
+dvsatn_hv18_ms_global      = 0    
+dwvsatn_hv18_ms_global     = 0    
+dagsn_hv18_ms_global       = 0    
+dlagsn_hv18_ms_global      = 0    
+dwagsn_hv18_ms_global      = 0    
+ss_flagn_hv18_ms_global    = 0    
+ff_flagn_hv18_ms_global    = 0    
+monte_flagn_hv18_ms_global = 0    
+sf_flagn_hv18_ms_global    = 0    
+fs_flagn_hv18_ms_global    = 0    
.ENDL ttg_hv18    
    
.LIB ssg_hv18    
.param    
+toxp_hv18_ms_global        = 2e-010    
+dxlp_hv18_ms_global        = 6.67e-009    
+dxwp_hv18_ms_global        = -6.67e-009    
+cjsp_hv18_ms_global        = 0.000102639    
+cjswsp_hv18_ms_global      = 6.60767e-012    
+cjswgsp_hv18_ms_global     = 6.12802e-012    
+cjdp_hv18_ms_global        = 4.935e-005    
+cjswdp_hv18_ms_global      = 2.254e-011    
+cjswgdp_hv18_ms_global     = 2.835e-011    
+cgdop_hv18_ms_global       = -1.83599e-012    
+cgsop_hv18_ms_global       = -6.74398e-012    
+cgdlp_hv18_ms_global       = -5.21504e-011    
+cgslp_hv18_ms_global       = -8.86949e-012    
+cfsp_hv18_ms_global        = -5.47487e-012    
+cfdsp_hv18_ms_global       = -9.92747e-013    
+dvthp_hv18_ms_global       = -0.0675    
+dlvthp_hv18_ms_global      = -2.2e-009    
+dwvthp_hv18_ms_global      = -7e-009    
+dpvthp_hv18_ms_global      = -5.5e-015    
+du0p_hv18_ms_global        = 0.00106    
+dlu0p_hv18_ms_global       = -3.7e-010    
+dwu0p_hv18_ms_global       = -1e-010    
+dpu0p_hv18_ms_global       = 1.2e-016    
+dvsatp_hv18_ms_global      = 0    
+dcitp_hv18_ms_global       = 5e-005    
+da0p_hv18_ms_global        = -0.005    
+dla0p_hv18_ms_global       = -1e-007    
+dwa0p_hv18_ms_global       = -2e-007    
+dpa0p_hv18_ms_global       = 6e-014    
+ss_flagp_hv18_ms_global    = 1    
+ff_flagp_hv18_ms_global    = 0    
+monte_flagp_hv18_ms_global = 0    
+sf_flagp_hv18_ms_global    = 0    
+fs_flagp_hv18_ms_global    = 0    
.param    
+toxn_hv18_ms_global        = 2e-010    
+dxln_hv18_ms_global        = 6.67e-009    
+dxwn_hv18_ms_global        = -6.67e-009    
+cjsn_hv18_ms_global        = 0.000101934    
+cjswsn_hv18_ms_global      = 7.1477e-012    
+cjswgsn_hv18_ms_global     = 8.6331e-012    
+cjdn_hv18_ms_global        = 1.106e-005    
+cjswdn_hv18_ms_global      = 3.871e-011    
+cjswgdn_hv18_ms_global     = 4.186e-011    
+cfsn_hv18_ms_global        = -5.58586e-012    
+cfdsn_hv18_ms_global       = -9.8889e-013    
+cgdln_hv18_ms_global       = -5.47995e-011    
+cgsln_hv18_ms_global       = -5.77017e-012    
+cgdon_hv18_ms_global       = -2.73588e-012    
+cgson_hv18_ms_global       = -1.02984e-011    
+dvthn_hv18_ms_global       = 0.0405    
+dlvthn_hv18_ms_global      = 1.25e-008    
+dwvthn_hv18_ms_global      = 1.16e-008    
+dpvthn_hv18_ms_global      = 4.5e-015    
+dcitn_hv18_ms_global       = 4e-005    
+du0n_hv18_ms_global        = 0.00111    
+dlu0n_hv18_ms_global       = -2.6e-010    
+dwu0n_hv18_ms_global       = 8.5e-010    
+dpu0n_hv18_ms_global       = -6.7e-016    
+dvsatn_hv18_ms_global      = -1500    
+dwvsatn_hv18_ms_global     = 0.008    
+dagsn_hv18_ms_global       = 0.19    
+dlagsn_hv18_ms_global      = 0    
+dwagsn_hv18_ms_global      = -3e-008    
+ss_flagn_hv18_ms_global    = 1    
+ff_flagn_hv18_ms_global    = 0    
+monte_flagn_hv18_ms_global = 0    
+sf_flagn_hv18_ms_global    = 0    
+fs_flagn_hv18_ms_global    = 0    
.ENDL ssg_hv18    
    
.LIB ffg_hv18    
.param    
+toxp_hv18_ms_global        = -2e-010    
+dxlp_hv18_ms_global        = -6.67e-009    
+dxwp_hv18_ms_global        = 6.67e-009    
+cjsp_hv18_ms_global        = -0.000102639    
+cjswsp_hv18_ms_global      = -6.60767e-012    
+cjswgsp_hv18_ms_global     = -6.12802e-012    
+cjdp_hv18_ms_global        = -4.935e-005    
+cjswdp_hv18_ms_global      = -2.254e-011    
+cjswgdp_hv18_ms_global     = -2.835e-011    
+cgdop_hv18_ms_global       = 1.83599e-012    
+cgsop_hv18_ms_global       = 6.74398e-012    
+cgdlp_hv18_ms_global       = 5.21504e-011    
+cgslp_hv18_ms_global       = 8.86949e-012    
+cfsp_hv18_ms_global        = 5.47487e-012    
+cfdsp_hv18_ms_global       = 9.92747e-013    
+dvthp_hv18_ms_global       = 0.0675    
+dlvthp_hv18_ms_global      = 2.4e-009    
+dwvthp_hv18_ms_global      = 7e-009    
+dpvthp_hv18_ms_global      = 5.7e-015    
+du0p_hv18_ms_global        = -0.00103    
+dlu0p_hv18_ms_global       = 3.7e-010    
+dwu0p_hv18_ms_global       = 5e-011    
+dpu0p_hv18_ms_global       = -1.2e-016    
+dvsatp_hv18_ms_global      = 0    
+dcitp_hv18_ms_global       = -7e-005    
+da0p_hv18_ms_global        = 0.08    
+dla0p_hv18_ms_global       = 1.48e-007    
+dwa0p_hv18_ms_global       = 2e-007    
+dpa0p_hv18_ms_global       = -5e-014    
+ss_flagp_hv18_ms_global    = 0    
+ff_flagp_hv18_ms_global    = 1    
+monte_flagp_hv18_ms_global = 0    
+sf_flagp_hv18_ms_global    = 0    
+fs_flagp_hv18_ms_global    = 0    
.param    
+toxn_hv18_ms_global        = -2e-010    
+dxln_hv18_ms_global        = -6.67e-009    
+dxwn_hv18_ms_global        = 6.67e-009    
+cjsn_hv18_ms_global        = -0.000101934    
+cjswsn_hv18_ms_global      = -7.1477e-012    
+cjswgsn_hv18_ms_global     = -8.6331e-012    
+cjdn_hv18_ms_global        = -1.106e-005    
+cjswdn_hv18_ms_global      = -3.871e-011    
+cjswgdn_hv18_ms_global     = -4.186e-011    
+cfsn_hv18_ms_global        = 5.58586e-012    
+cfdsn_hv18_ms_global       = 9.8889e-013    
+cgdln_hv18_ms_global       = 5.47995e-011    
+cgsln_hv18_ms_global       = 5.77017e-012    
+cgdon_hv18_ms_global       = 2.73588e-012    
+cgson_hv18_ms_global       = 1.02984e-011    
+dvthn_hv18_ms_global       = -0.042    
+dlvthn_hv18_ms_global      = -1.14e-008    
+dwvthn_hv18_ms_global      = -1.36e-008    
+dpvthn_hv18_ms_global      = -5.3e-015    
+dcitn_hv18_ms_global       = -9e-005    
+du0n_hv18_ms_global        = -0.00116    
+dlu0n_hv18_ms_global       = 3.2e-010    
+dwu0n_hv18_ms_global       = -8.5e-010    
+dpu0n_hv18_ms_global       = 7.5e-016    
+dvsatn_hv18_ms_global      = -10000    
+dwvsatn_hv18_ms_global     = -0.0075    
+dagsn_hv18_ms_global       = -0.2    
+dlagsn_hv18_ms_global      = 7.5e-008    
+dwagsn_hv18_ms_global      = -1.7e-007    
+ss_flagn_hv18_ms_global    = 0    
+ff_flagn_hv18_ms_global    = 1    
+monte_flagn_hv18_ms_global = 0    
+sf_flagn_hv18_ms_global    = 0    
+fs_flagn_hv18_ms_global    = 0    
.ENDL ffg_hv18    
    
.LIB sfg_hv18    
.param    
+toxp_hv18_ms_global        = '0*0.53000'    
+dxlp_hv18_ms_global        = '0*0.53000'    
+dxwp_hv18_ms_global        = '6.67e-009*0.53000'    
+cjsp_hv18_ms_global        = '-8.21111e-005*0.53000'    
+cjswsp_hv18_ms_global      = '-5.28614e-012*0.53000'    
+cjswgsp_hv18_ms_global     = '-4.90242e-012*0.53000'    
+cjdp_hv18_ms_global        = '-3.948e-005*0.53000'    
+cjswdp_hv18_ms_global      = '-1.8032e-011*0.53000'    
+cjswgdp_hv18_ms_global     = '-2.268e-011*0.53000'    
+cgdop_hv18_ms_global       = '0*0.53000'    
+cgsop_hv18_ms_global       = '0*0.53000'    
+cgdlp_hv18_ms_global       = '0*0.53000'    
+cgslp_hv18_ms_global       = '0*0.53000'    
+cfsp_hv18_ms_global        = '0*0.53000'    
+cfdsp_hv18_ms_global       = '0*0.53000'    
+dvthp_hv18_ms_global       = '0.0768*0.53000'    
+dlvthp_hv18_ms_global      = '2.24e-009*0.53000'    
+dwvthp_hv18_ms_global      = '6.4e-009*0.53000'    
+dpvthp_hv18_ms_global      = '5.6e-015*0.53000'    
+du0p_hv18_ms_global        = '-0.000616*0.53000'    
+dlu0p_hv18_ms_global       = '3.6e-010*0.53000'    
+dwu0p_hv18_ms_global       = '4.8e-012*0.53000'    
+dpu0p_hv18_ms_global       = '0*0.53000'    
+dvsatp_hv18_ms_global      = '0*0.53000'    
+dcitp_hv18_ms_global       = '0*0.53000'    
+da0p_hv18_ms_global        = '0.152*0.53000'    
+dla0p_hv18_ms_global       = '2.4e-008*0.53000'    
+dwa0p_hv18_ms_global       = '2.4e-007*0.53000'    
+dpa0p_hv18_ms_global       = '0*0.53000'    
+ss_flagp_hv18_ms_global    = '0*0.53000'    
+ff_flagp_hv18_ms_global    = '0*0.53000'    
+monte_flagp_hv18_ms_global = '0*0.53000'    
+sf_flagp_hv18_ms_global    = '1*0.53000'    
+fs_flagp_hv18_ms_global    = '0*0.53000'    
.param    
+toxn_hv18_ms_global        = '0*0.53000'    
+dxln_hv18_ms_global        = '0*0.53000'    
+dxwn_hv18_ms_global        = '-6.67e-009*0.53000'    
+cjsn_hv18_ms_global        = '8.15472e-005*0.53000'    
+cjswsn_hv18_ms_global      = '5.71816e-012*0.53000'    
+cjswgsn_hv18_ms_global     = '6.90648e-012*0.53000'    
+cjdn_hv18_ms_global        = '8.848e-006*0.53000'    
+cjswdn_hv18_ms_global      = '3.0968e-011*0.53000'    
+cjswgdn_hv18_ms_global     = '3.3488e-011*0.53000'    
+cfsn_hv18_ms_global        = '0*0.53000'    
+cfdsn_hv18_ms_global       = '0*0.53000'    
+cgdln_hv18_ms_global       = '0*0.53000'    
+cgsln_hv18_ms_global       = '0*0.53000'    
+cgdon_hv18_ms_global       = '0*0.53000'    
+cgson_hv18_ms_global       = '0*0.53000'    
+dvthn_hv18_ms_global       = '0.052*0.53000'    
+dlvthn_hv18_ms_global      = '1.456e-008*0.53000'    
+dwvthn_hv18_ms_global      = '6.88e-009*0.53000'    
+dpvthn_hv18_ms_global      = '5.2e-015*0.53000'    
+dcitn_hv18_ms_global       = '-4e-005*0.53000'    
+du0n_hv18_ms_global        = '0.0012*0.53000'    
+dlu0n_hv18_ms_global       = '-3.6e-010*0.53000'    
+dwu0n_hv18_ms_global       = '1.68e-010*0.53000'    
+dpu0n_hv18_ms_global       = '-3.6e-016*0.53000'    
+dvsatn_hv18_ms_global      = '800*0.53000'    
+dwvsatn_hv18_ms_global     = '0.0056*0.53000'    
+dagsn_hv18_ms_global       = '0.176*0.53000'    
+dlagsn_hv18_ms_global      = '1.6e-008*0.53000'    
+dwagsn_hv18_ms_global      = '0*0.53000'    
+ss_flagn_hv18_ms_global    = '0*0.53000'    
+ff_flagn_hv18_ms_global    = '0*0.53000'    
+monte_flagn_hv18_ms_global = '0*0.53000'    
+sf_flagn_hv18_ms_global    = '1*0.53000'    
+fs_flagn_hv18_ms_global    = '0*0.53000'    
.ENDL sfg_hv18    
    
.LIB fsg_hv18    
.param    
+toxp_hv18_ms_global        = '0*0.53000'    
+dxlp_hv18_ms_global        = '0*0.53000'    
+dxwp_hv18_ms_global        = '-6.67e-009*0.53000'    
+cjsp_hv18_ms_global        = '8.21111e-005*0.53000'    
+cjswsp_hv18_ms_global      = '5.28614e-012*0.53000'    
+cjswgsp_hv18_ms_global     = '4.90242e-012*0.53000'    
+cjdp_hv18_ms_global        = '3.948e-005*0.53000'    
+cjswdp_hv18_ms_global      = '1.8032e-011*0.53000'    
+cjswgdp_hv18_ms_global     = '2.268e-011*0.53000'    
+cgdop_hv18_ms_global       = '0*0.53000'    
+cgsop_hv18_ms_global       = '0*0.53000'    
+cgdlp_hv18_ms_global       = '0*0.53000'    
+cgslp_hv18_ms_global       = '0*0.53000'    
+cfsp_hv18_ms_global        = '0*0.53000'    
+cfdsp_hv18_ms_global       = '0*0.53000'    
+dvthp_hv18_ms_global       = '-0.0768*0.53000'    
+dlvthp_hv18_ms_global      = '0*0.53000'    
+dwvthp_hv18_ms_global      = '0*0.53000'    
+dpvthp_hv18_ms_global      = '-5.6e-015*0.53000'    
+du0p_hv18_ms_global        = '0.0006*0.53000'    
+dlu0p_hv18_ms_global       = '-3.6e-010*0.53000'    
+dwu0p_hv18_ms_global       = '-1.6e-011*0.53000'    
+dpu0p_hv18_ms_global       = '0*0.53000'    
+dvsatp_hv18_ms_global      = '0*0.53000'    
+dcitp_hv18_ms_global       = '0*0.53000'    
+da0p_hv18_ms_global        = '-0.08*0.53000'    
+dla0p_hv18_ms_global       = '0*0.53000'    
+dwa0p_hv18_ms_global       = '-1.6e-007*0.53000'    
+dpa0p_hv18_ms_global       = '0*0.53000'    
+ss_flagp_hv18_ms_global    = '0*0.53000'    
+ff_flagp_hv18_ms_global    = '0*0.53000'    
+monte_flagp_hv18_ms_global = '0*0.53000'    
+sf_flagp_hv18_ms_global    = '0*0.53000'    
+fs_flagp_hv18_ms_global    = '1*0.53000'    
.param    
+toxn_hv18_ms_global        = '0*0.53000'    
+dxln_hv18_ms_global        = '0*0.53000'    
+dxwn_hv18_ms_global        = '6.67e-009*0.53000'    
+cjsn_hv18_ms_global        = '-8.15472e-005*0.53000'    
+cjswsn_hv18_ms_global      = '-5.71816e-012*0.53000'    
+cjswgsn_hv18_ms_global     = '-6.90648e-012*0.53000'    
+cjdn_hv18_ms_global        = '-8.848e-006*0.53000'    
+cjswdn_hv18_ms_global      = '-3.0968e-011*0.53000'    
+cjswgdn_hv18_ms_global     = '-3.3488e-011*0.53000'    
+cfsn_hv18_ms_global        = '0*0.53000'    
+cfdsn_hv18_ms_global       = '0*0.53000'    
+cgdln_hv18_ms_global       = '0*0.53000'    
+cgsln_hv18_ms_global       = '0*0.53000'    
+cgdon_hv18_ms_global       = '0*0.53000'    
+cgson_hv18_ms_global       = '0*0.53000'    
+dvthn_hv18_ms_global       = '-0.0496*0.53000'    
+dlvthn_hv18_ms_global      = '-1.4e-008*0.53000'    
+dwvthn_hv18_ms_global      = '-8e-009*0.53000'    
+dpvthn_hv18_ms_global      = '-5.04e-015*0.53000'    
+dcitn_hv18_ms_global       = '0*0.53000'    
+du0n_hv18_ms_global        = '-0.00116*0.53000'    
+dlu0n_hv18_ms_global       = '4.64e-010*0.53000'    
+dwu0n_hv18_ms_global       = '-4.96e-010*0.53000'    
+dpu0n_hv18_ms_global       = '5.28e-016*0.53000'    
+dvsatn_hv18_ms_global      = '-3200*0.53000'    
+dwvsatn_hv18_ms_global     = '-0.00616*0.53000'    
+dagsn_hv18_ms_global       = '-0.12*0.53000'    
+dlagsn_hv18_ms_global      = '0*0.53000'    
+dwagsn_hv18_ms_global      = '6.4e-008*0.53000'    
+ss_flagn_hv18_ms_global    = '0*0.53000'    
+ff_flagn_hv18_ms_global    = '0*0.53000'    
+monte_flagn_hv18_ms_global = '0*0.53000'    
+sf_flagn_hv18_ms_global    = '0*0.53000'    
+fs_flagn_hv18_ms_global    = '1*0.53000'    
.ENDL fsg_hv18    
    
.LIB global_hv18    
.param    
+stretch1p_hv18=1.65    
+stretch2p_hv18='1/1.65'    
+a1p_hv18_ms='p1_io1p_hv*4.8651/stretch1p_hv18'    
+a2p_hv18_ms='p2_io1p_hv*2.3409/stretch1p_hv18'    
+a3p_hv18_ms='p3_io1p_hv*1.1736/stretch1p_hv18'    
+a4p_hv18_ms='p4_io1p_hv*1/stretch1p_hv18'    
+a5p_hv18_ms='p5_io1p_hv*0.68789/stretch1p_hv18'    
+toxp_hv18_ms_global='stretch1p_hv18*stretch2p_hv18*((1.8492e-011)*a1p_hv18_ms+(-4.6548e-011)*a2p_hv18_ms+(-1.4693e-012)*a3p_hv18_ms+(1.4142e-010)*a4p_hv18_ms+(7.9048e-012)*a5p_hv18_ms)'    
+dxlp_hv18_ms_global='stretch1p_hv18*stretch2p_hv18*((6.1672e-010)*a1p_hv18_ms+(-1.5524e-009)*a2p_hv18_ms+(-4.9001e-011)*a3p_hv18_ms+(-4.7164e-009)*a4p_hv18_ms+(2.6363e-010)*a5p_hv18_ms)'    
+dxwp_hv18_ms_global='stretch1p_hv18*stretch2p_hv18*((-7.6365e-010)*a1p_hv18_ms+(-1.4062e-009)*a2p_hv18_ms+(1.043e-010)*a3p_hv18_ms+(2.2871e-025)*a4p_hv18_ms+(-6.4744e-009)*a5p_hv18_ms)'    
+cjsp_hv18_ms_global='(1.0497e-005)*a1p_hv18_ms+(-2.112e-006)*a2p_hv18_ms+(-8.8855e-007)*a3p_hv18_ms+(7.149e-021)*a4p_hv18_ms+(-7.9369e-007)*a5p_hv18_ms'    
+cjswsp_hv18_ms_global='(6.7575e-013)*a1p_hv18_ms+(-1.3596e-013)*a2p_hv18_ms+(-5.7184e-014)*a3p_hv18_ms+(3.1335e-028)*a4p_hv18_ms+(-5.1095e-014)*a5p_hv18_ms'    
+cjswgsp_hv18_ms_global='(6.2669e-013)*a1p_hv18_ms+(-1.2609e-013)*a2p_hv18_ms+(-5.3027e-014)*a3p_hv18_ms+(1.108e-028)*a4p_hv18_ms+(-4.7386e-014)*a5p_hv18_ms'    
+cjdp_hv18_ms_global='(5.0469e-006)*a1p_hv18_ms+(-1.0155e-006)*a2p_hv18_ms+(-4.2704e-007)*a3p_hv18_ms+(8.663e-022)*a4p_hv18_ms+(-3.8161e-007)*a5p_hv18_ms'    
+cjswdp_hv18_ms_global='(2.3051e-012)*a1p_hv18_ms+(-4.638e-013)*a2p_hv18_ms+(-1.9505e-013)*a3p_hv18_ms+(5.4922e-028)*a4p_hv18_ms+(-1.743e-013)*a5p_hv18_ms'    
+cjswgdp_hv18_ms_global='(2.8993e-012)*a1p_hv18_ms+(-5.8335e-013)*a2p_hv18_ms+(-2.4532e-013)*a3p_hv18_ms+(5.167e-028)*a4p_hv18_ms+(-2.1922e-013)*a5p_hv18_ms'    
+cgdop_hv18_ms_global='(-1.8776e-013)*a1p_hv18_ms+(3.7778e-014)*a2p_hv18_ms+(1.5887e-014)*a3p_hv18_ms+(3.626e-029)*a4p_hv18_ms+(1.4197e-014)*a5p_hv18_ms'    
+cgsop_hv18_ms_global='(-6.8969e-013)*a1p_hv18_ms+(1.3877e-013)*a2p_hv18_ms+(5.8354e-014)*a3p_hv18_ms+(-1.0511e-028)*a4p_hv18_ms+(5.2149e-014)*a5p_hv18_ms'    
+cgdlp_hv18_ms_global='(-5.3333e-012)*a1p_hv18_ms+(1.0731e-012)*a2p_hv18_ms+(4.5127e-013)*a3p_hv18_ms+(9.4262e-028)*a4p_hv18_ms+(4.0326e-013)*a5p_hv18_ms'    
+cgslp_hv18_ms_global='(-9.0705e-013)*a1p_hv18_ms+(1.825e-013)*a2p_hv18_ms+(7.675e-014)*a3p_hv18_ms+(-2.0597e-028)*a4p_hv18_ms+(6.8585e-014)*a5p_hv18_ms'    
+cfsp_hv18_ms_global='(-5.599e-013)*a1p_hv18_ms+(1.1265e-013)*a2p_hv18_ms+(4.7376e-014)*a3p_hv18_ms+(-1.0015e-028)*a4p_hv18_ms+(4.2336e-014)*a5p_hv18_ms'    
+cfdsp_hv18_ms_global='(-1.0153e-013)*a1p_hv18_ms+(2.0427e-014)*a2p_hv18_ms+(8.5905e-015)*a3p_hv18_ms+(2.5743e-029)*a4p_hv18_ms+(7.6767e-015)*a5p_hv18_ms'    
+dvthp_hv18_ms_global='(-0.0074423)*a1p_hv18_ms+(-0.01028)*a2p_hv18_ms+(0.00065598)*a3p_hv18_ms+(-5.8228e-018)*a4p_hv18_ms+(0.0031211)*a5p_hv18_ms'    
+dlvthp_hv18_ms_global='(-2.8639e-010)*a1p_hv18_ms+(-1.0559e-009)*a2p_hv18_ms+(-1.0867e-011)*a3p_hv18_ms+(-2.2079e-025)*a4p_hv18_ms+(2.6294e-010)*a5p_hv18_ms'    
+dwvthp_hv18_ms_global='(-7.1587e-010)*a1p_hv18_ms+(1.4404e-010)*a2p_hv18_ms+(6.0573e-011)*a3p_hv18_ms+(1.9864e-025)*a4p_hv18_ms+(5.4129e-011)*a5p_hv18_ms'    
+dpvthp_hv18_ms_global='(-6.2681e-016)*a1p_hv18_ms+(-1.0517e-015)*a2p_hv18_ms+(1.8081e-017)*a3p_hv18_ms+(-6.5843e-032)*a4p_hv18_ms+(3.0264e-016)*a5p_hv18_ms'    
+du0p_hv18_ms_global='(0.00011959)*a1p_hv18_ms+(0.0002543)*a2p_hv18_ms+(-1.6376e-005)*a3p_hv18_ms+(-2.0787e-020)*a4p_hv18_ms+(-6.9601e-005)*a5p_hv18_ms'    
+dlu0p_hv18_ms_global='(-3.6858e-011)*a1p_hv18_ms+(2.8829e-011)*a2p_hv18_ms+(3.071e-012)*a3p_hv18_ms+(-1.671e-026)*a4p_hv18_ms+(-1.8646e-012)*a5p_hv18_ms'    
+dwu0p_hv18_ms_global='(-7.5251e-012)*a1p_hv18_ms+(3.6728e-012)*a2p_hv18_ms+(1.0027e-011)*a3p_hv18_ms+(-2.246e-027)*a4p_hv18_ms+(2.5142e-013)*a5p_hv18_ms'    
+dpu0p_hv18_ms_global='(1.3351e-017)*a1p_hv18_ms+(2.0869e-017)*a2p_hv18_ms+(-1.1822e-018)*a3p_hv18_ms+(1.5191e-034)*a4p_hv18_ms+(-6.1262e-018)*a5p_hv18_ms'    
+dvsatp_hv18_ms_global='(196.1)*a1p_hv18_ms+(4243.2)*a2p_hv18_ms+(-26.138)*a3p_hv18_ms+(5.8661e-013)*a4p_hv18_ms+(-945.14)*a5p_hv18_ms'    
+dcitp_hv18_ms_global='(6.1547e-006)*a1p_hv18_ms+(-1.2314e-006)*a2p_hv18_ms+(3.2373e-006)*a3p_hv18_ms+(-3.0098e-021)*a4p_hv18_ms+(-4.0635e-007)*a5p_hv18_ms'    
+da0p_hv18_ms_global='(-0.0044166)*a1p_hv18_ms+(0.00086256)*a2p_hv18_ms+(-0.013719)*a3p_hv18_ms+(3.28e-018)*a4p_hv18_ms+(0.00011258)*a5p_hv18_ms'    
+dla0p_hv18_ms_global='(-1.2726e-008)*a1p_hv18_ms+(2.5438e-009)*a2p_hv18_ms+(-7.9426e-009)*a3p_hv18_ms+(1.0732e-023)*a4p_hv18_ms+(8.2058e-010)*a5p_hv18_ms'    
+dwa0p_hv18_ms_global='(-2.0453e-008)*a1p_hv18_ms+(4.1153e-009)*a2p_hv18_ms+(1.7307e-009)*a3p_hv18_ms+(6.484e-024)*a4p_hv18_ms+(1.5465e-009)*a5p_hv18_ms'    
+dpa0p_hv18_ms_global='(5.6153e-015)*a1p_hv18_ms+(-1.1333e-015)*a2p_hv18_ms+(-2.3542e-015)*a3p_hv18_ms+(1.7323e-030)*a4p_hv18_ms+(-4.5411e-016)*a5p_hv18_ms'    
+ss_flagp_hv18_ms_global='(0.050197)*a1p_hv18_ms+(-0.010448)*a2p_hv18_ms+(-0.19215)*a3p_hv18_ms+(-1.6811e-017)*a4p_hv18_ms+(-0.0067471)*a5p_hv18_ms'    
+ff_flagp_hv18_ms_global='(-0.05207)*a1p_hv18_ms+(0.010129)*a2p_hv18_ms+(-0.1835)*a3p_hv18_ms+(1.115e-016)*a4p_hv18_ms+(0.00098562)*a5p_hv18_ms'    
+monte_flagp_hv18_ms_global='(0.0924618)*a1p_hv18_ms+(-0.232744)*a2p_hv18_ms+(-0.00734648)*a3p_hv18_ms+(-0.707106)*a4p_hv18_ms+(0.0395247)*a5p_hv18_ms'    
.param sf_flagp_hv18_ms_global = 0    
.param fs_flagp_hv18_ms_global = 0    
.param    
+stretch1n_hv18=1.63    
+stretch2n_hv18='1/1.63'    
+a1n_hv18_ms='p1_io1n_hv*4.8208/stretch1n_hv18'    
+a2n_hv18_ms='p2_io1n_hv*2.2021/stretch1n_hv18'    
+a3n_hv18_ms='p3_io1n_hv*1.5621/stretch1n_hv18'    
+a4n_hv18_ms='p4_io1n_hv*1/stretch1n_hv18'    
+a5n_hv18_ms='p5_io1n_hv*0.68556/stretch1n_hv18'    
+toxn_hv18_ms_global='stretch1n_hv18*stretch2n_hv18*((1.8558e-011)*a1n_hv18_ms+(-4.9098e-011)*a2n_hv18_ms+(-1.0439e-011)*a3n_hv18_ms+(1.4142e-010)*a4n_hv18_ms+(9.208e-012)*a5n_hv18_ms)'    
+dxln_hv18_ms_global='stretch1n_hv18*stretch2n_hv18*((6.1891e-010)*a1n_hv18_ms+(-1.6374e-009)*a2n_hv18_ms+(-3.4814e-010)*a3n_hv18_ms+(-4.7164e-009)*a4n_hv18_ms+(3.0709e-010)*a5n_hv18_ms)'    
+dxwn_hv18_ms_global='stretch1n_hv18*stretch2n_hv18*((-7.6865e-010)*a1n_hv18_ms+(-1.5194e-009)*a2n_hv18_ms+(9.167e-011)*a3n_hv18_ms+(-1.2175e-026)*a4n_hv18_ms+(-6.4483e-009)*a5n_hv18_ms)'    
+cjsn_hv18_ms_global='(1.0476e-005)*a1n_hv18_ms+(-2.0992e-006)*a2n_hv18_ms+(-3.217e-006)*a3n_hv18_ms+(-9.0878e-022)*a4n_hv18_ms+(-7.9987e-007)*a5n_hv18_ms'    
+cjswsn_hv18_ms_global='(7.3461e-013)*a1n_hv18_ms+(-1.472e-013)*a2n_hv18_ms+(-2.2559e-013)*a3n_hv18_ms+(3.5191e-030)*a4n_hv18_ms+(-5.609e-014)*a5n_hv18_ms'    
+cjswgsn_hv18_ms_global='(8.8727e-013)*a1n_hv18_ms+(-1.7779e-013)*a2n_hv18_ms+(-2.7247e-013)*a3n_hv18_ms+(4.0041e-030)*a4n_hv18_ms+(-6.7746e-014)*a5n_hv18_ms'    
+cjdn_hv18_ms_global='(1.1367e-006)*a1n_hv18_ms+(-2.2777e-007)*a2n_hv18_ms+(-3.4907e-007)*a3n_hv18_ms+(-3.7235e-023)*a4n_hv18_ms+(-8.6791e-008)*a5n_hv18_ms'    
+cjswdn_hv18_ms_global='(3.9784e-012)*a1n_hv18_ms+(-7.972e-013)*a2n_hv18_ms+(-1.2217e-012)*a3n_hv18_ms+(1.3208e-029)*a4n_hv18_ms+(-3.0377e-013)*a5n_hv18_ms'    
+cjswgdn_hv18_ms_global='(4.3022e-012)*a1n_hv18_ms+(-8.6208e-013)*a2n_hv18_ms+(-1.3212e-012)*a3n_hv18_ms+(-3.5906e-028)*a4n_hv18_ms+(-3.2849e-013)*a5n_hv18_ms'    
+cfsn_hv18_ms_global='(-5.7409e-013)*a1n_hv18_ms+(1.1504e-013)*a2n_hv18_ms+(1.763e-013)*a3n_hv18_ms+(9.1208e-029)*a4n_hv18_ms+(4.3834e-014)*a5n_hv18_ms'    
+cfdsn_hv18_ms_global='(-1.0163e-013)*a1n_hv18_ms+(2.0365e-014)*a2n_hv18_ms+(3.1211e-014)*a3n_hv18_ms+(8.5358e-030)*a4n_hv18_ms+(7.7601e-015)*a5n_hv18_ms'    
+cgdln_hv18_ms_global='(-5.632e-012)*a1n_hv18_ms+(1.1286e-012)*a2n_hv18_ms+(1.7295e-012)*a3n_hv18_ms+(5.1827e-028)*a4n_hv18_ms+(4.3003e-013)*a5n_hv18_ms'    
+cgsln_hv18_ms_global='(-5.9303e-013)*a1n_hv18_ms+(1.1883e-013)*a2n_hv18_ms+(1.8211e-013)*a3n_hv18_ms+(5.1301e-029)*a4n_hv18_ms+(4.528e-014)*a5n_hv18_ms'    
+cgdon_hv18_ms_global='(-2.8118e-013)*a1n_hv18_ms+(5.6343e-014)*a2n_hv18_ms+(8.6348e-014)*a3n_hv18_ms+(4.376e-029)*a4n_hv18_ms+(2.1469e-014)*a5n_hv18_ms'    
+cgson_hv18_ms_global='(-1.0584e-012)*a1n_hv18_ms+(2.1209e-013)*a2n_hv18_ms+(3.2503e-013)*a3n_hv18_ms+(1.639e-028)*a4n_hv18_ms+(8.0814e-014)*a5n_hv18_ms'    
+dvthn_hv18_ms_global='(0.004785)*a1n_hv18_ms+(0.011284)*a2n_hv18_ms+(2.2552e-005)*a3n_hv18_ms+(1.0157e-018)*a4n_hv18_ms+(-0.0032288)*a5n_hv18_ms'    
+dlvthn_hv18_ms_global='(1.3034e-009)*a1n_hv18_ms+(1.5611e-009)*a2n_hv18_ms+(-3.6626e-010)*a3n_hv18_ms+(1.6127e-025)*a4n_hv18_ms+(-5.284e-010)*a5n_hv18_ms'    
+dwvthn_hv18_ms_global='(1.3284e-009)*a1n_hv18_ms+(2.8817e-010)*a2n_hv18_ms+(-6.5777e-011)*a3n_hv18_ms+(6.6883e-026)*a4n_hv18_ms+(-2.2718e-010)*a5n_hv18_ms'    
+dpvthn_hv18_ms_global='(5.6689e-016)*a1n_hv18_ms+(1.2426e-015)*a2n_hv18_ms+(8.1276e-017)*a3n_hv18_ms+(1.0435e-031)*a4n_hv18_ms+(-3.5921e-016)*a5n_hv18_ms'    
+dcitn_hv18_ms_global='(6.8914e-006)*a1n_hv18_ms+(-1.7033e-006)*a2n_hv18_ms+(4.9563e-006)*a3n_hv18_ms+(-1.5529e-021)*a4n_hv18_ms+(-3.4967e-007)*a5n_hv18_ms'    
+du0n_hv18_ms_global='(0.00013484)*a1n_hv18_ms+(0.00038108)*a2n_hv18_ms+(8.3264e-006)*a3n_hv18_ms+(5.4535e-020)*a4n_hv18_ms+(-0.00010574)*a5n_hv18_ms'    
+dlu0n_hv18_ms_global='(-2.3567e-011)*a1n_hv18_ms+(1.5259e-010)*a2n_hv18_ms+(1.4155e-011)*a3n_hv18_ms+(2.3313e-026)*a4n_hv18_ms+(-3.2944e-011)*a5n_hv18_ms'    
+dwu0n_hv18_ms_global='(9.0355e-011)*a1n_hv18_ms+(4.9964e-011)*a2n_hv18_ms+(-2.0637e-011)*a3n_hv18_ms+(-2.0805e-027)*a4n_hv18_ms+(-2.2836e-011)*a5n_hv18_ms'    
+dpu0n_hv18_ms_global='(-7.3308e-017)*a1n_hv18_ms+(1.5205e-017)*a2n_hv18_ms+(1.1196e-017)*a3n_hv18_ms+(9.3101e-034)*a4n_hv18_ms+(5.3149e-018)*a5n_hv18_ms'    
+dvsatn_hv18_ms_global='(485.32)*a1n_hv18_ms+(-171.4)*a2n_hv18_ms+(1477.6)*a3n_hv18_ms+(1.3555e-012)*a4n_hv18_ms+(3.5421)*a5n_hv18_ms'    
+dwvsatn_hv18_ms_global='(0.0007944)*a1n_hv18_ms+(-0.00015596)*a2n_hv18_ms+(-0.00031468)*a3n_hv18_ms+(3.8828e-019)*a4n_hv18_ms+(-6.242e-005)*a5n_hv18_ms'    
+dagsn_hv18_ms_global='(0.020083)*a1n_hv18_ms+(-0.0040888)*a2n_hv18_ms+(-0.0047529)*a3n_hv18_ms+(-6.3478e-018)*a4n_hv18_ms+(-0.0014981)*a5n_hv18_ms'    
+dlagsn_hv18_ms_global='(-4.1705e-009)*a1n_hv18_ms+(1.3193e-009)*a2n_hv18_ms+(-9.3281e-009)*a3n_hv18_ms+(3.1986e-024)*a4n_hv18_ms+(5.3666e-011)*a5n_hv18_ms'    
+dwagsn_hv18_ms_global='(8.0381e-009)*a1n_hv18_ms+(-2.9004e-009)*a2n_hv18_ms+(2.5822e-008)*a3n_hv18_ms+(-7.6335e-024)*a4n_hv18_ms+(9.2308e-011)*a5n_hv18_ms'    
+ss_flagn_hv18_ms_global='(0.047169)*a1n_hv18_ms+(-0.0030033)*a2n_hv18_ms+(-0.15594)*a3n_hv18_ms+(9.3324e-018)*a4n_hv18_ms+(-0.0071317)*a5n_hv18_ms'    
+ff_flagn_hv18_ms_global='(-0.055607)*a1n_hv18_ms+(0.017591)*a2n_hv18_ms+(-0.12437)*a3n_hv18_ms+(4.676e-017)*a4n_hv18_ms+(0.00071555)*a5n_hv18_ms'    
+monte_flagn_hv18_ms_global='(0.0927901)*a1n_hv18_ms+(-0.245487)*a2n_hv18_ms+(-0.0521949)*a3n_hv18_ms+(-0.707106)*a4n_hv18_ms+(0.0460405)*a5n_hv18_ms'    
.param sf_flagn_hv18_ms_global = 0    
.param fs_flagn_hv18_ms_global = 0    
.ENDL global_hv18    
    
.LIB TT_hv18    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' setup_hv18    
.param    
+toxp_hv18       = 3.4e-09       dxlp_hv18       = 0             dxwp_hv18       = 0    
+cjsp_hv18        = 0.001466269   cjswsp_hv18      = 9.43953e-11   cjswgsp_hv18     = 8.75432e-11    
+cjdp_hv18        = 0.000705   cjswdp_hv18      = 3.22e-10   cjswgdp_hv18     = 4.05e-10    
+cgdop_hv18= '2.622839e-11 + 2.57901e-13*ccoflag_hv18'    
+cgsop_hv18= '9.63426e-11 + 2.4118e-11*ccoflag_hv18'    
+cgdlp_hv18= 7.45005e-10    
+cgslp_hv18= 1.26707e-10    
+ddlcp_hv18= 6.22093e-08    
+cfsp_hv18 = 7.82124e-11    
+cfdsp_hv18= '(9.23945e-11-7.82124e-11) - (9.23945e-11-7.82124e-11)*(1-ccoflag_hv18)'    
+dvthp_hv18      = 0             dlvthp_hv18     = 0    
+dwvthp_hv18     = 0             dpvthp_hv18     = 0             du0p_hv18       = 0    
+dlu0p_hv18      = 0             dwu0p_hv18      = 0             dpu0p_hv18      = 0    
+dvsatp_hv18     = 0             dlvsatp_hv18    = 0             dwvsatp_hv18    = 0    
+dpvsatp_hv18    = 0             deta0p_hv18     = 0             dweta0p_hv18    = 0    
+dnfactorp_hv18  = 0             dlnfactorp_hv18 = 0             dwnfactorp_hv18 = 0    
+dpnfactorp_hv18 = 0             dvoffp_hv18     = 0             dlvoffp_hv18    = 0    
+dwvoffp_hv18    = 0             dpvoffp_hv18    = 0             dcitp_hv18      = 0    
+dlcitp_hv18     = 0             dwcitp_hv18     = 0             dpcitp_hv18     = 0    
+da0p_hv18       = 0             dla0p_hv18      = 0             dwa0p_hv18      = 0    
+dpa0p_hv18      = 0             dagsp_hv18      = 0             dlagsp_hv18     = 0    
+dwagsp_hv18     = 0             dpagsp_hv18     = 0             dpdiblc2p_hv18  = 0    
+dlpdiblc2p_hv18 = 0             dwpdiblc2p_hv18 = 0             dppdiblc2p_hv18 = 0    
+dkt1p_hv18      = 0             dlkt1p_hv18     = 0             dwkt1p_hv18     = 0    
+dpkt1p_hv18     = 0             dua1p_hv18      = 0             dlua1p_hv18     = 0    
+dwua1p_hv18     = 0             dpua1p_hv18     = 0             datp_hv18       = 0    
+dlatp_hv18      = 0             dwatp_hv18      = 0             dpatp_hv18      = 0    
+ss_flagp_hv18    = 0            ff_flagp_hv18   = 0             sf_flagp_hv18   = 0    
+fs_flagp_hv18    = 0    
+ monte_flagp_hv18 = 0    
.param    
+toxn_hv18       = 3.36e-09      dxln_hv18       = 0             dxwn_hv18       = 0    
+cjsn_hv18        = 1.4562e-03     cjswsn_hv18       = 1.0211e-10    cjswgsn_hv18     = 1.2333e-10    
+cjdn_hv18        = 1.58e-04     cjswdn_hv18      = 5.53e-10    cjswgdn_hv18     = 5.98e-10    
+cfsn_hv18        =  7.9798e-11    
+cfdsn_hv18       = '(9.3925e-11-7.9798e-11)-(9.3925e-11-7.9798e-11)*(1-ccoflag_hv18)'    
+cgdln_hv18       =  7.8285e-10    
+cgsln_hv18       =  8.2431e-11    
+cgdon_hv18       = '3.9084e-11+2.5981e-13*ccoflag_hv18'    
+cgson_hv18       = '1.4712e-10+2.4058e-11*ccoflag_hv18'    
+ddlcn_hv18       =  5.5333e-08    
+dvthn_hv18      = 0             dlvthn_hv18     = 0    
+dwvthn_hv18     = 0             dpvthn_hv18     = 0             dk2n_hv18       = 0    
+dvoffn_hv18     = 0             dlvoffn_hv18    = 0             dwvoffn_hv18    = 0    
+dpvoffn_hv18    = 0             dcitn_hv18      = 0             dlcitn_hv18     = 0    
+dwcitn_hv18     = 0             dpcitn_hv18     = 0             deta0n_hv18     = 0    
+du0n_hv18       = 0             dlu0n_hv18      = 0             dwu0n_hv18      = 0    
+dpu0n_hv18      = 0             duan_hv18       = 0             dubn_hv18       = 0    
+dvsatn_hv18     = 0             dlvsatn_hv18    = 0             dwvsatn_hv18    = 0    
+dpvsatn_hv18    = 0             da0n_hv18       = 0             dla0n_hv18      = 0    
+dwa0n_hv18      = 0             dpa0n_hv18      = 0             dagsn_hv18      = 0    
+dlagsn_hv18     = 0             dwagsn_hv18     = 0             dpagsn_hv18     = 0    
+dkt1n_hv18      = 0             dtvoffn_hv18    = 0             dua1n_hv18      = 0    
+dub1n_hv18      = 0             datn_hv18       = 0             dlatn_hv18      = 0    
+dwatn_hv18      = 0             dpatn_hv18      = 0             ss_flagn_hv18   = 0    
+ff_flagn_hv18   = 0             sf_flagn_hv18   = 0             fs_flagn_hv18   = 0    
+ monte_flagn_hv18 = 0    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' MOS_hv18    
.ENDL TT_hv18    
    
.LIB SS_hv18    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' setup_hv18    
.param    
+a1n_hv18='-1*sigma_factor_hv18' a1p_hv18='-1*sigma_factor_hv18' a2n_hv18='-1*sigma_factor_hv18' a2p_hv18='-1*sigma_factor_hv18' a3n_hv18='1*sigma_factor_hv18' a3p_hv18='1*sigma_factor_hv18' a4np_hv18='-1*sigma_factor_hv18'    
+toxp_hv18 = '3.4e-09-2e-010*a4np_hv18'    
+dxlp_hv18 = '-6.67e-009*a2p_hv18'                dxwp_hv18 = '-6.67e-009*a3p_hv18'    
+cjsp_hv18 = '0.001466269*(1-0.07*a1p_hv18)'       cjswsp_hv18 = '9.43953e-11*(1-0.07*a1p_hv18)'     cjswgsp_hv18 = '8.75432e-11*(1-0.07*a1p_hv18)'    
+cjdp_hv18 = '0.000705*(1-0.07*a1p_hv18)'       cjswdp_hv18 = '3.22e-10*(1-0.07*a1p_hv18)'     cjswgdp_hv18 = '4.05e-10*(1-0.07*a1p_hv18)'    
+cgdop_hv18 = '2.622839e-11*(1+0.07*a4np_hv18) + 2.57901e-13*ccoflag_hv18'    
+cgsop_hv18 = '9.63426e-11*(1+0.07*a4np_hv18) + 2.4118e-11*ccoflag_hv18'    
+cgdlp_hv18 = '7.45005e-10*(1+0.07*a4np_hv18)'    
+cgslp_hv18 = '1.26707e-10*(1+0.07*a4np_hv18)'    
+ddlcp_hv18 = 6.22093e-08    
+cfsp_hv18 = '7.82124e-11*(1+0.07*a4np_hv18)'    
+cfdsp_hv18= '(9.23945e-11-7.82124e-11)*(1+0.07*a4np_hv18) - (9.23945e-11-7.82124e-11)*(1-ccoflag_hv18)'    
+dvthp_hv18 = '0.0675*a1p_hv18'                  dlvthp_hv18 = '2.2e-09*a1p_hv18'                dwvthp_hv18 = '7e-09*a1p_hv18'    
+dpvthp_hv18 = '5.5e-15*a1p_hv18'                du0p_hv18 = '-0.00106*a1p_hv18'                 dlu0p_hv18 = '3.7e-010*a1p_hv18'    
+dwu0p_hv18 = '1e-010*a1p_hv18'                  dpu0p_hv18 = '-1.2e-016*a1p_hv18'               dvsatp_hv18 = 0    
+dlvsatp_hv18 = 0                                dwvsatp_hv18 = 0                                dpvsatp_hv18 = 0    
+deta0p_hv18 = '0*a1p_hv18'                      dweta0p_hv18 = 0                                dnfactorp_hv18 = 0    
+dlnfactorp_hv18 = 0                             dwnfactorp_hv18 = 0                             dpnfactorp_hv18 = 0    
+dvoffp_hv18 = 0                                 dlvoffp_hv18 = 0                                dwvoffp_hv18 = 0    
+dpvoffp_hv18 = 0                                dcitp_hv18 = '-0.00005*a1p_hv18'                dlcitp_hv18 = 0    
+dwcitp_hv18 = 0                                 dpcitp_hv18 = 0                                 da0p_hv18 = '0.005*a1p_hv18'    
+dla0p_hv18 = '1e-07*a1p_hv18'                   dwa0p_hv18 = '2e-07*a1p_hv18'                   dpa0p_hv18 = '-6e-14*a1p_hv18'    
+dagsp_hv18 = 0                                  dlagsp_hv18 = 0                                 dwagsp_hv18 = 0    
+dpagsp_hv18 = 0                                 dpdiblc2p_hv18 = '0*a1p_hv18'                   dlpdiblc2p_hv18 = 0    
+dwpdiblc2p_hv18 = 0                             dppdiblc2p_hv18 = 0                             dkt1p_hv18 = 0    
+dlkt1p_hv18 = 0                                 dwkt1p_hv18 = 0                                 dpkt1p_hv18 = 0    
+dua1p_hv18 = 0                                  dlua1p_hv18 = 0                                 dwua1p_hv18 = 0    
+dpua1p_hv18 = 0                                 datp_hv18 = 0                                   dlatp_hv18 = 0    
+dwatp_hv18 = 0                                  dpatp_hv18 = 0    
+ss_flagp_hv18 = '1*sigma_factor_hv18'           ff_flagp_hv18 = 0                               sf_flagp_hv18 = 0    
+fs_flagp_hv18 = 0    
+ monte_flagp_hv18 = 0    
.param    
+toxn_hv18 = '3.36e-09-2e-010*a4np_hv18'    
+dxln_hv18 = '-6.67e-009*a2n_hv18'               dxwn_hv18 = '-6.67e-009*a3n_hv18'    
+cjsn_hv18 = '1.4562e-03*(1-0.07*a1n_hv18)'         cjswsn_hv18 = '1.0211e-10*(1-0.07*a1n_hv18)'     cjswgsn_hv18 = '1.2333e-10*(1-0.07*a1n_hv18)'    
+cjdn_hv18 = '1.58e-04*(1-0.07*a1n_hv18)'         cjswdn_hv18 = '5.53e-10*(1-0.07*a1n_hv18)'     cjswgdn_hv18 = '5.98e-10*(1-0.07*a1n_hv18)'    
+cfsn_hv18        = '7.9798e-11 *(1+0.07*a4np_hv18)'    
+cfdsn_hv18       = '(9.3925e-11-7.9798e-11)*(1+0.07*a4np_hv18)-(9.3925e-11-7.9798e-11)*(1-ccoflag_hv18)'    
+cgdln_hv18       = '7.8285e-10*(1+0.07*a4np_hv18)'    
+cgsln_hv18       = '8.2431e-11*(1+0.07*a4np_hv18)'    
+cgdon_hv18       = '3.9084e-11*(1+0.07*a4np_hv18)+2.5981e-13*ccoflag_hv18'    
+cgson_hv18       = '1.4712e-10 *(1+0.07*a4np_hv18)+ 2.4058e-11*ccoflag_hv18'    
+ddlcn_hv18       =  5.5333e-08    
+dvthn_hv18 = '-0.0405*a1n_hv18'                   dlvthn_hv18 = '-12.5e-009*a1n_hv18'              dwvthn_hv18 = '-11.6e-009*a1n_hv18'    
+dpvthn_hv18 = '-4.5e-015*a1n_hv18'               dk2n_hv18 = 0                                  dvoffn_hv18 = 0    
+dlvoffn_hv18 = 0                               dwvoffn_hv18 = 0    	                   dpvoffn_hv18 = 0    
+dcitn_hv18 = '-4.0e-005*a1n_hv18'                dlcitn_hv18 = 0                                dwcitn_hv18 = 0    
+dpcitn_hv18 = 0                                deta0n_hv18 = 0                                du0n_hv18 = '-0.00111*a1n_hv18'    
+dlu0n_hv18 = '2.6e-010*a1n_hv18'                 dwu0n_hv18 = '-8.5e-010*a1n_hv18'                dpu0n_hv18 = '6.7e-016*a1n_hv18'    
+duan_hv18 = 0                                  dubn_hv18 = 0                                  dvsatn_hv18 = '1500*a1n_hv18'    
+dlvsatn_hv18 = 0                               dwvsatn_hv18 = '-0.80e-002*a1n_hv18'            dpvsatn_hv18 = 0    
+da0n_hv18 = '0.6*a1n_hv18*0'                     dla0n_hv18 = 0                                 dwa0n_hv18 = '2.2e-007*a1n_hv18*0'    
+dpa0n_hv18 = 0                                 dagsn_hv18 = '-0.19*a1n_hv18'                    dlagsn_hv18 = 0    
+dwagsn_hv18 = '0.3e-007*a1n_hv18'                dpagsn_hv18 = 0                                dkt1n_hv18 = 0    
+dtvoffn_hv18 = 0                               dua1n_hv18 = 0                                 dub1n_hv18 = 0    
+datn_hv18 = 0                                  dlatn_hv18 = 0                                 dwatn_hv18 = 0    
+dpatn_hv18 = 0    
+ss_flagn_hv18   = '1*sigma_factor_hv18'          ff_flagn_hv18   = 0                            sf_flagn_hv18   = 0    
+fs_flagn_hv18   = 0    
+ monte_flagn_hv18 = 0    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' MOS_hv18    
.ENDL SS_hv18    
    
.LIB FF_hv18    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' setup_hv18    
.param    
+a1n_hv18='-1*sigma_factor_hv18' a1p_hv18='-1*sigma_factor_hv18' a2n_hv18='-1*sigma_factor_hv18' a2p_hv18='-1*sigma_factor_hv18' a3n_hv18='1*sigma_factor_hv18' a3p_hv18='1*sigma_factor_hv18' a4np_hv18='-1*sigma_factor_hv18'    
+toxp_hv18 = '3.4e-09+2.0000e-010*a4np_hv18'    
+dxlp_hv18 = '6.67e-009*a2p_hv18'                 dxwp_hv18 = '6.67e-009*a3p_hv18'    
+cjsp_hv18 = '0.001466269*(1+0.070*a1p_hv18)'      cjswsp_hv18 = '9.43953e-11*(1+0.070*a1p_hv18)'    cjswgsp_hv18 = '8.75432e-11*(1+0.070*a1p_hv18)'    
+cjdp_hv18 = '0.000705*(1+0.070*a1p_hv18)'      cjswdp_hv18 = '3.22e-10*(1+0.070*a1p_hv18)'    cjswgdp_hv18 = '4.05e-10*(1+0.070*a1p_hv18)'    
+cgdop_hv18 = '2.622839e-11*(1-0.07*a4np_hv18) + 2.57901e-13*ccoflag_hv18'    
+cgsop_hv18 = '9.63426e-11*(1-0.07*a4np_hv18) + 2.4118e-11*ccoflag_hv18'    
+cgdlp_hv18 = '7.45005e-10*(1-0.07*a4np_hv18)'    
+cgslp_hv18 = '1.26707e-10*(1-0.07*a4np_hv18)'    
+ddlcp_hv18 = 6.22093e-08    
+cfsp_hv18 = '7.82124e-11*(1-0.07*a4np_hv18)'    
+cfdsp_hv18= '(9.23945e-11-7.82124e-11)*(1-0.07*a4np_hv18) - (9.23945e-11-7.82124e-11)*(1-ccoflag_hv18)'    
+dvthp_hv18 = '-0.0675*a1p_hv18'                 dlvthp_hv18 = '-2.4e-09*a1p_hv18'               dwvthp_hv18 = '-7e-09*a1p_hv18'    
+dpvthp_hv18 = '-5.7e-015*a1p_hv18'              du0p_hv18 = '0.00103*a1p_hv18'                  dlu0p_hv18 = '-3.7e-010*a1p_hv18'    
+dwu0p_hv18 = '-5e-011*a1p_hv18'                 dpu0p_hv18 = '1.2e-016*a1p_hv18'                dvsatp_hv18 = 0    
+dlvsatp_hv18 = 0                                dwvsatp_hv18 = 0                                dpvsatp_hv18 = 0    
+deta0p_hv18 = '0*a1p_hv18'                      dweta0p_hv18 = 0                                dnfactorp_hv18 = 0    
+dlnfactorp_hv18 = 0                             dwnfactorp_hv18 = 0                             dpnfactorp_hv18 = 0    
+dvoffp_hv18 = 0                                 dlvoffp_hv18 = 0                                dwvoffp_hv18 = 0    
+dpvoffp_hv18 = 0                                dcitp_hv18 = '0.00007*a1p_hv18'                 dlcitp_hv18 = 0    
+dwcitp_hv18 = 0                                 dpcitp_hv18 = 0                                 da0p_hv18 = '-0.08*a1p_hv18'    
+dla0p_hv18 = '-1.48e-07*a1p_hv18'               dwa0p_hv18 = '-2e-07*a1p_hv18'                  dpa0p_hv18 = '5e-14*a1p_hv18'    
+dagsp_hv18 = 0                                  dlagsp_hv18 = 0                                 dwagsp_hv18 = 0    
+dpagsp_hv18 = 0                                 dpdiblc2p_hv18 = '0*a1p_hv18'                   dlpdiblc2p_hv18 = 0    
+dwpdiblc2p_hv18 = 0                             dppdiblc2p_hv18 = 0                             dkt1p_hv18 = 0    
+dlkt1p_hv18 = 0                                 dwkt1p_hv18 = 0                                 dpkt1p_hv18 = 0    
+dua1p_hv18 = 0                                  dlua1p_hv18 = 0                                 dwua1p_hv18 = 0    
+dpua1p_hv18 = 0                                 datp_hv18 = 0                                   dlatp_hv18 = 0    
+dwatp_hv18 = 0                                  dpatp_hv18 = 0    
+ss_flagp_hv18 = 0                               ff_flagp_hv18 = '1*sigma_factor_hv18'           sf_flagp_hv18 = 0    
+fs_flagp_hv18 = 0    
+ monte_flagp_hv18 = 0    
.param    
+toxn_hv18 = '3.36e-09+2.0000e-010*a4np_hv18'    
+dxln_hv18 = '6.67e-009*a2n_hv18'                dxwn_hv18 = '6.67e-009*a3n_hv18'    
+cjsn_hv18 = '1.4562e-03*(1+0.070*a1n_hv18)'       cjswsn_hv18 = '1.0211e-10*(1+0.070*a1n_hv18)'    cjswgsn_hv18 = '1.2333e-10*(1+0.070*a1n_hv18)'    
+cjdn_hv18 = '1.58e-04*(1+0.070*a1n_hv18)'       cjswdn_hv18 = '5.53e-10*(1+0.070*a1n_hv18)'    cjswgdn_hv18 = '5.98e-10*(1+0.070*a1n_hv18)'    
+cfsn_hv18        = '7.9798e-11 *(1-0.07*a4np_hv18)'    
+cfdsn_hv18       = '(9.3925e-11-7.9798e-11)*(1-0.07*a4np_hv18)-(9.3925e-11-7.9798e-11)*(1-ccoflag_hv18)'    
+cgdln_hv18       = '7.8285e-10*(1-0.07*a4np_hv18)'    
+cgsln_hv18       = '8.2431e-11*(1-0.07*a4np_hv18)'    
+cgdon_hv18       = '3.9084e-11*(1-0.07*a4np_hv18)+2.5981e-13*ccoflag_hv18'    
+cgson_hv18       = '1.4712e-10 *(1-0.07*a4np_hv18)+ 2.4058e-11*ccoflag_hv18'    
+ddlcn_hv18       =  5.5333e-08    
+dvthn_hv18 = '0.042*a1n_hv18'                    dlvthn_hv18 = '11.4e-009*a1n_hv18'               dwvthn_hv18 = '13.6e-009*a1n_hv18'    
+dpvthn_hv18 = '5.3e-015*a1n_hv18'              dk2n_hv18 = 0                                  dvoffn_hv18 = 0    
+dlvoffn_hv18 = 0                               dwvoffn_hv18 = 0                               dpvoffn_hv18 = 0    
+dcitn_hv18 = '9.0e-005*a1n_hv18'                dlcitn_hv18 = 0                                dwcitn_hv18 = 0    
+dpcitn_hv18 = 0                                deta0n_hv18 = 0                                du0n_hv18 = '0.00116*a1n_hv18'    
+dlu0n_hv18 = '-3.2e-010*a1n_hv18'                dwu0n_hv18 = '8.5e-010*a1n_hv18'              dpu0n_hv18 = '-7.5e-016*a1n_hv18'    
+duan_hv18 = 0                                  dubn_hv18 = 0                                  dvsatn_hv18 = '10000*a1n_hv18'    
+dlvsatn_hv18 = 0                               dwvsatn_hv18 = '0.75e-002*a1n_hv18'            dpvsatn_hv18 = 0    
+da0n_hv18 =  '-1.0*a1n_hv18*0'                   dla0n_hv18 = 0                                 dwa0n_hv18 = '-4.2e-007*a1n_hv18*0'    
+dpa0n_hv18 = 0                                 dagsn_hv18 = '0.20*a1n_hv18'                     dlagsn_hv18 = '-7.5e-008*a1n_hv18'    
+dwagsn_hv18 = '1.7e-007*a1n_hv18'               dpagsn_hv18 = 0                                dkt1n_hv18 = 0    
+dtvoffn_hv18 = 0                               dua1n_hv18 = 0                                 dub1n_hv18 = 0    
+datn_hv18 = 0                                  dlatn_hv18 = 0                                 dwatn_hv18 = 0    
+dpatn_hv18 = 0    
+ss_flagn_hv18   = 0                            ff_flagn_hv18   = '1*sigma_factor_hv18'          sf_flagn_hv18   = 0    
+fs_flagn_hv18   = 0    
+ monte_flagn_hv18 = 0    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' MOS_hv18    
.ENDL FF_hv18    
    
.LIB SF_hv18    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' setup_hv18    
.param    
+a1n_hv18='0.8*sigma_factor_hv18' a1p_hv18='-0.8*sigma_factor_hv18' a2n_hv18='0*sigma_factor_hv18' a2p_hv18='0*sigma_factor_hv18' a3n_hv18='-1*sigma_factor_hv18' a3p_hv18='1*sigma_factor_hv18' a4np_hv18='0*sigma_factor_hv18'    
+toxp_hv18 = '3.4e-09+2.0000e-010*a4np_hv18'    
+dxlp_hv18 = '6.67e-009*a2p_hv18'                 dxwp_hv18 = '6.67e-009*a3p_hv18'    
+cjsp_hv18 = '0.001466269*(1+0.070*a1p_hv18)'      cjswsp_hv18 = '9.43953e-11*(1+0.070*a1p_hv18)'    cjswgsp_hv18 = '8.75432e-11*(1+0.070*a1p_hv18)'    
+cjdp_hv18 = '0.000705*(1+0.070*a1p_hv18)'      cjswdp_hv18 = '3.22e-10*(1+0.070*a1p_hv18)'    cjswgdp_hv18 = '4.05e-10*(1+0.070*a1p_hv18)'    
+cgdop_hv18 = '2.622839e-11*(1-0.07*a4np_hv18) + 2.57901e-13*ccoflag_hv18'    
+cgsop_hv18 = '9.63426e-11*(1-0.07*a4np_hv18) + 2.4118e-11*ccoflag_hv18'    
+cgdlp_hv18 = '7.45005e-10*(1-0.07*a4np_hv18)'    
+cgslp_hv18 = '1.26707e-10*(1-0.07*a4np_hv18)'    
+ddlcp_hv18 = 6.22093e-08    
+cfsp_hv18 = '7.82124e-11*(1-0.07*a4np_hv18)'    
+cfdsp_hv18= '(9.23945e-11-7.82124e-11)*(1-0.07*a4np_hv18) - (9.23945e-11-7.82124e-11)*(1-ccoflag_hv18)'    
+dvthp_hv18 = '-0.096*a1p_hv18'                  dlvthp_hv18 = '-2.8e-009*a1p_hv18'              dwvthp_hv18 = '-8e-009*a1p_hv18'    
+dpvthp_hv18 = '-7e-015*a1p_hv18'                du0p_hv18 = '0.00077*a1p_hv18'                  dlu0p_hv18 = '-4.5e-010*a1p_hv18'    
+dwu0p_hv18 = '-6e-012*a1p_hv18'                 dpu0p_hv18 = 0                                  dvsatp_hv18 = 0    
+dlvsatp_hv18 = 0                                dwvsatp_hv18 = 0                                dpvsatp_hv18 = 0    
+deta0p_hv18 = '0*a1p_hv18'                      dweta0p_hv18 = 0                                dnfactorp_hv18 = 0    
+dlnfactorp_hv18 = 0                             dwnfactorp_hv18 = 0                             dpnfactorp_hv18 = 0    
+dvoffp_hv18 = 0                                 dlvoffp_hv18 = 0                                dwvoffp_hv18 = 0    
+dpvoffp_hv18 = 0                                dcitp_hv18 = 0                                  dlcitp_hv18 = 0    
+dwcitp_hv18 = 0                                 dpcitp_hv18 = 0                                 da0p_hv18 = '-0.19*a1p_hv18'    
+dla0p_hv18 = '-3e-08*a1p_hv18'                  dwa0p_hv18 = '-3e-07*a1p_hv18'                  dpa0p_hv18 = 0    
+dagsp_hv18 = 0                                  dlagsp_hv18 = 0                                 dwagsp_hv18 = 0    
+dpagsp_hv18 = 0                                 dpdiblc2p_hv18 = '0*a1p_hv18'                   dlpdiblc2p_hv18 = 0    
+dwpdiblc2p_hv18 = 0                             dppdiblc2p_hv18 = 0                             dkt1p_hv18 = 0    
+dlkt1p_hv18 = 0                                 dwkt1p_hv18 = 0                                 dpkt1p_hv18 = 0    
+dua1p_hv18 = 0                                  dlua1p_hv18 = 0                                 dwua1p_hv18 = 0    
+dpua1p_hv18 = 0                                 datp_hv18 = 0                                   dlatp_hv18 = 0    
+dwatp_hv18 = 0                                  dpatp_hv18 = 0    
+ss_flagp_hv18 = 0                               ff_flagp_hv18 = 0                               sf_flagp_hv18 = '1*sigma_factor_hv18'    
+fs_flagp_hv18 = 0    
+ monte_flagp_hv18 = 0    
.param    
+toxn_hv18 = '3.36e-09+2.0000e-010*a4np_hv18'    
+dxln_hv18 = '6.67e-009*a2n_hv18'                dxwn_hv18 = '6.67e-009*a3n_hv18'    
+cjsn_hv18 = '1.4562e-03*(1+0.070*a1n_hv18)'       cjswsn_hv18 = '1.0211e-10*(1+0.070*a1n_hv18)'    cjswgsn_hv18 = '1.2333e-10*(1+0.070*a1n_hv18)'    
+cjdn_hv18 = '1.58e-04*(1+0.070*a1n_hv18)'       cjswdn_hv18 = '5.53e-10*(1+0.070*a1n_hv18)'    cjswgdn_hv18 = '5.98e-10*(1+0.070*a1n_hv18)'    
+cfsn_hv18        = '7.9798e-11 *(1+0.07*a4np_hv18)'    
+cfdsn_hv18       = '(9.3925e-11-7.9798e-11)*(1+0.07*a4np_hv18)-(9.3925e-11-7.9798e-11)*(1-ccoflag_hv18)'    
+cgdln_hv18       = '7.8285e-10*(1+0.07*a4np_hv18)'    
+cgsln_hv18       = '8.2431e-11*(1+0.07*a4np_hv18)'    
+cgdon_hv18       = '3.9084e-11*(1+0.07*a4np_hv18)+2.5981e-13*ccoflag_hv18'    
+cgson_hv18       = '1.4712e-10 *(1+0.07*a4np_hv18)+ 2.4058e-11*ccoflag_hv18'    
+ddlcn_hv18       =  5.5333e-08    
+dvthn_hv18 = '0.065*a1n_hv18'                    dlvthn_hv18 = '18.2e-009*a1n_hv18'               dwvthn_hv18 = '8.6e-009*a1n_hv18'    
+dpvthn_hv18 = '6.5e-015*a1n_hv18'                dk2n_hv18 = 0                                  dvoffn_hv18 = 0    
+dlvoffn_hv18 = 0                               dwvoffn_hv18 = 0                               dpvoffn_hv18 = 0    
+dcitn_hv18 = '-5.0e-005*a1n_hv18'                dlcitn_hv18 = 0                                dwcitn_hv18 = 0    
+dpcitn_hv18 = 0                                deta0n_hv18 = 0                                du0n_hv18 = '0.00150*a1n_hv18'    
+dlu0n_hv18 = '-4.5e-010*a1n_hv18'                dwu0n_hv18 = '2.1e-010*a1n_hv18'                 dpu0n_hv18 = '-4.5e-016*a1n_hv18'    
+duan_hv18 = 0                                  dubn_hv18 = 0                                  dvsatn_hv18 = '1000*a1n_hv18'    
+dlvsatn_hv18 = 0                               dwvsatn_hv18 = '0.7e-002*a1n_hv18'              dpvsatn_hv18 = 0    
+da0n_hv18 = 0                                  dla0n_hv18 = 0                                 dwa0n_hv18 = 0    
+dpa0n_hv18 = 0                                 dagsn_hv18 = '0.22*a1n_hv18'                    dlagsn_hv18 = '2e-008*a1n_hv18'    
+dwagsn_hv18 = 0                                dpagsn_hv18 = 0                                dkt1n_hv18 = 0    
+dtvoffn_hv18 = 0                               dua1n_hv18 = 0                                 dub1n_hv18 = 0    
+datn_hv18 = 0                                  dlatn_hv18 = 0                                 dwatn_hv18 = 0    
+dpatn_hv18=0    
+ss_flagn_hv18=0                                ff_flagn_hv18 = 0                              sf_flagn_hv18 = '1*sigma_factor_hv18'    
+fs_flagn_hv18=0    
+ monte_flagn_hv18 = 0    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' MOS_hv18    
.ENDL SF_hv18    
    
.LIB FS_hv18    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' setup_hv18    
.param    
+a1n_hv18='-0.8*sigma_factor_hv18' a1p_hv18='0.8*sigma_factor_hv18' a2n_hv18='0*sigma_factor_hv18' a2p_hv18='0*sigma_factor_hv18' a3n_hv18='1*sigma_factor_hv18' a3p_hv18='-1*sigma_factor_hv18' a4np_hv18='0*sigma_factor_hv18'    
+toxp_hv18 = '3.4e-09+2.0000e-010*a4np_hv18'    
+dxlp_hv18 = '6.67e-009*a2p_hv18'                 dxwp_hv18 = '6.67e-009*a3p_hv18'    
+cjsp_hv18 = '0.001466269*(1+0.070*a1p_hv18)'      cjswsp_hv18 = '9.43953e-11*(1+0.070*a1p_hv18)'    cjswgsp_hv18 = '8.75432e-11*(1+0.070*a1p_hv18)'    
+cjdp_hv18 = '0.000705*(1+0.070*a1p_hv18)'      cjswdp_hv18 = '3.22e-10*(1+0.070*a1p_hv18)'    cjswgdp_hv18 = '4.05e-10*(1+0.070*a1p_hv18)'    
+cgdop_hv18 = '2.622839e-11*(1-0.07*a4np_hv18) + 2.57901e-13*ccoflag_hv18'    
+cgsop_hv18 = '9.63426e-11*(1-0.07*a4np_hv18) + 2.4118e-11*ccoflag_hv18'    
+cgdlp_hv18 = '7.45005e-10*(1-0.07*a4np_hv18)'    
+cgslp_hv18 = '1.26707e-10*(1-0.07*a4np_hv18)'    
+ddlcp_hv18 = 6.22093e-08    
+cfsp_hv18 = '7.82124e-11*(1-0.07*a4np_hv18)'    
+cfdsp_hv18= '(9.23945e-11-7.82124e-11)*(1-0.07*a4np_hv18) - (9.23945e-11-7.82124e-11)*(1-ccoflag_hv18)'    
+dvthp_hv18 = '-0.096*a1p_hv18'                  dlvthp_hv18 = '-2.8e-009*a1p_hv18*0'            dwvthp_hv18 = '-8e-009*a1p_hv18*0'    
+dpvthp_hv18 = '-7e-015*a1p_hv18'                du0p_hv18 = '0.00075*a1p_hv18'                  dlu0p_hv18 = '-4.5e-010*a1p_hv18'    
+dwu0p_hv18 = '-2e-011*a1p_hv18'                 dpu0p_hv18 = 0                                  dvsatp_hv18 = 0    
+dlvsatp_hv18 = 0                                dwvsatp_hv18 = 0                                dpvsatp_hv18 = 0    
+deta0p_hv18 = '0*a1p_hv18'                      dweta0p_hv18 = 0                                dnfactorp_hv18 = 0    
+dlnfactorp_hv18 = 0                             dwnfactorp_hv18 = 0                             dpnfactorp_hv18 = 0    
+dvoffp_hv18 = 0                                 dlvoffp_hv18 = 0                                dwvoffp_hv18 = 0    
+dpvoffp_hv18 = 0                                dcitp_hv18 = 0                                  dlcitp_hv18 = 0    
+dwcitp_hv18 = 0                                 dpcitp_hv18 = 0                                 da0p_hv18 = '-0.1*a1p_hv18'    
+dla0p_hv18 = 0                                  dwa0p_hv18 = '-2e-07*a1p_hv18'                  dpa0p_hv18 = 0    
+dagsp_hv18 = 0                                  dlagsp_hv18 = 0                                 dwagsp_hv18 = 0    
+dpagsp_hv18 = 0                                 dpdiblc2p_hv18 = '0*a1p_hv18'                   dlpdiblc2p_hv18 = 0    
+dwpdiblc2p_hv18 = 0                             dppdiblc2p_hv18 = 0                             dkt1p_hv18 = 0    
+dlkt1p_hv18 = 0                                 dwkt1p_hv18 = 0                                 dpkt1p_hv18 = 0    
+dua1p_hv18 = 0                                  dlua1p_hv18 = 0                                 dwua1p_hv18 = 0    
+dpua1p_hv18 = 0                                 datp_hv18 = 0                                   dlatp_hv18 = 0    
+dwatp_hv18 = 0                                  dpatp_hv18 = 0    
+ss_flagp_hv18 = 0                               ff_flagp_hv18 = 0                               sf_flagp_hv18=0    
+fs_flagp_hv18 = '1*sigma_factor_hv18'    
+ monte_flagp_hv18 = 0    
.param    
+toxn_hv18 = '3.36e-09+2.0000e-010*a4np_hv18'    
+dxln_hv18 = '6.67e-009*a2n_hv18'                dxwn_hv18 = '6.67e-009*a3n_hv18'    
+cjsn_hv18 = '1.4562e-03*(1+0.070*a1n_hv18)'       cjswsn_hv18 = '1.0211e-10*(1+0.070*a1n_hv18)'    cjswgsn_hv18 = '1.2333e-10*(1+0.070*a1n_hv18)'    
+cjdn_hv18 = '1.58e-04*(1+0.070*a1n_hv18)'       cjswdn_hv18 = '5.53e-10*(1+0.070*a1n_hv18)'    cjswgdn_hv18 = '5.98e-10*(1+0.070*a1n_hv18)'    
+cfsn_hv18        = '7.9798e-11 *(1+0.07*a4np_hv18)'    
+cfdsn_hv18       = '(9.3925e-11-7.9798e-11)*(1+0.07*a4np_hv18)-(9.3925e-11-7.9798e-11)*(1-ccoflag_hv18)'    
+cgdln_hv18       = '7.8285e-10*(1+0.07*a4np_hv18)'    
+cgsln_hv18       = '8.2431e-11*(1+0.07*a4np_hv18)'    
+cgdon_hv18       = '3.9084e-11*(1+0.07*a4np_hv18)+2.5981e-13*ccoflag_hv18'    
+cgson_hv18       = '1.4712e-10 *(1+0.07*a4np_hv18)+ 2.4058e-11*ccoflag_hv18'    
+ddlcn_hv18       =  5.5333e-08    
+dvthn_hv18 = '0.062*a1n_hv18'                    dlvthn_hv18 = '17.5e-009*a1n_hv18'               dwvthn_hv18 = '10.0e-009*a1n_hv18'    
+dpvthn_hv18 = '6.3e-015*a1n_hv18'                dk2n_hv18 = 0                                  dvoffn_hv18 = 0    
+dlvoffn_hv18 = 0                               dwvoffn_hv18 = 0                               dpvoffn_hv18 = 0    
+dcitn_hv18 = 0                                 dlcitn_hv18 = 0                                dwcitn_hv18 = 0    
+dpcitn_hv18 = 0                                deta0n_hv18 = 0                                du0n_hv18 = '0.00145*a1n_hv18'    
+dlu0n_hv18 = '-5.8e-010*a1n_hv18'               dwu0n_hv18 = '6.2e-010*a1n_hv18'                 dpu0n_hv18 = '-6.6e-016*a1n_hv18'    
+duan_hv18 = 0                                  dubn_hv18 = 0                                  dvsatn_hv18 = '4000*a1n_hv18'    
+dlvsatn_hv18 = 0                               dwvsatn_hv18 = '0.77e-002*a1n_hv18'              dpvsatn_hv18 = 0    
+da0n_hv18 =  '0.2*a1n_hv18*0'                    dla0n_hv18 = 0                                 dwa0n_hv18 = '3.0e-007*a1n_hv18*0'    
+dpa0n_hv18 = 0                                 dagsn_hv18 = '0.15*a1n_hv18'                     dlagsn_hv18 = 0    
+dwagsn_hv18 = '-0.8e-007*a1n_hv18'               dpagsn_hv18 = 0                                dkt1n_hv18 = 0    
+dtvoffn_hv18 = 0                               dua1n_hv18 = 0                                 dub1n_hv18 = 0    
+datn_hv18 = 0                                  dlatn_hv18 = 0                                 dwatn_hv18 = 0    
+dpatn_hv18 = 0    
+ss_flagn_hv18   = 0                            ff_flagn_hv18   = 0                            sf_flagn_hv18   = 0    
+fs_flagn_hv18   = '1*sigma_factor_hv18'    
+ monte_flagn_hv18 = 0    
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' MOS_hv18    
.ENDL FS_hv18    
    
.LIB Total_hv18    
.subckt nch_hv18_mac n1 n2 n3 n4 l=length w=width multi='1' nf='1' scale='scale_mos_hv18'    
+_dmcg='6.6e-008' _dmcg_d='7.1e-008' _dmci='6.6e-008' _xw2='1.5e-08+dxwn_hv18_ms' _xl2='1e-08+dxln_hv18_ms' _xw= '1.5e-08' _xl= '1e-08'    
+ad='(nf*_dmcg_d+_dmci)/scale*(wef/scale+_xw2/scale)' as='(nf*_dmcg+_dmci)/scale*(wef/scale+_xw2/scale)'    
+pd='2*(nf*_dmcg_d+_dmci)/scale+(nf+1)*(wef/scale+_xw2/scale)' ps='2*(nf*_dmcg+_dmci)/scale+(nf+1)*(wef/scale+_xw2/scale)'    
+nrd='_dmcg_d/scale/nf/(wef/scale+_xw2/scale)+_rc_nrsd*_rcoflag' nrs='_dmcg/scale/nf/(wef/scale+_xw2/scale)+_rc_nrsd*_rcoflag'    
+sd='2*_dmcg_d/scale'    
+sca='0' scb='0' scc='0'    
+sc=0    
+sa='saref/scale' sb='sbref/scale'    
+sa1=sa sb1=sb sa2=sa sb2=sb sa3=sa sb3=sb sa4=sa sa5=sa sa6=sa sa7=sa    
+spa='spavar/scale' spa1=spa  spa2=spa spa3=spa    
+sap='pwr((sa4*scale+1e-9)*pwr(spa*scale+1e-9,2),1/3)/scale'    
+spba='sqrt(spbvar-spavar)*sqrt(spa2*scale+0.1*lef)/scale'    
+spba1='sqrt((spa2*scale+0.1*lef)*(spbvar-spavar+0.1*lef))/scale'    
+sapb='pwr((sa4*scale+1e-9)*pwr(spbvar-spavar,3),0.25)/scale'    
+enx='2.0e-5/scale' eny='2.0e-5/scale' eny1=eny enx1=enx eny2=eny    
+rex='sqrt((enx1*scale+1e-9)*(4e-5-2.0e-5+lef))/scale'    
+rey='sqrt((eny2*scale+1e-9)*(4e-5-2.0e-5+lef))/scale'    
+sodx='0.18e-6/scale' sodxa='sodx' sodxb='sodx'    
+sodx1='pwr((sa5*scale+1.0e-7)*sqrt(sodx*scale),2/3)/scale'    
+sodx2='pwr((pwr(1e-6,3)+10*pwr(sa6*scale,3))*sqrt(sodx*scale),2/7)/scale'    
+sodx4='pwr(pwr(sa7*scale+1.0e-9,3)*sqrt(sodx*scale),2/7)/scale'    
+sody='0.5085e-6/scale'    
+spmt='spmref/scale' spomt='spomref/scale' spomt1='1/pwr((pwr(spomt*scale,0.5)/pwr(spmt*scale,1)+1e-30),2)/scale'    
+spmb='spmref/scale' spomb='spomref/scale' spomb1='1/pwr((pwr(spomb*scale,0.5)/pwr(spmb*scale,1)+1e-30),2)/scale'    
+_conum='max(1,int(((wef/scale-0.0945*1e-6*2/scale)-0.036*1e-6/scale)/(0.1125*1e-6/scale)+1))' _rc_nrsd='80/18.5/_conum/nf'    
+_delvto=0 _mulu0=1 _ccoflag='ccoflag_hv18' _rcoflag='rcoflag_hv18' _rgflag='rgflag_hv18'    
+mismatchflag='mismatchflag_mos_hv18' globalflag='globalflag_mos_hv18' totalflag='totalflag_mos_hv18'    
    
.param lef='(l)*scale'    
.param wef='(w/nf)*scale'  
   
**********************************************    
*       Mismatch Parameters                  *    
**********************************************    
.param    
+temp1='plo_tox_hv' temp2='plo_dxl_hv' temp3='plo_dxw_hv' temp4='parl1_hv' temp5='parl2_hv'    
    
+mis_a_1=0.0044 mis_a_2=-0.55 mis_a_3=0.1    
+mis_b_1=0.0025  mis_b_2=0.9   mis_b_3=0.12    
+mis_c_1=0.95 mis_c_2=0 mis_c_3=0    
+mis_d_1=0.0016 mis_d_2=0 mis_d_3=0    
+mis_e_1=0.007 mis_e_2=-1.2 mis_e_3=0.12 e_limit1=0.1 e_limit2=2    
+avtgm_min=0    
    
+a='mis_a_1*pwr(abs(lef*1e6),mis_a_2)*pwr(abs(wef*1e6),mis_a_3)'    
+b='mis_b_1*pwr(abs(lef*1e6),mis_b_2)*pwr(abs(wef*1e6),mis_b_3)'    
+c='mis_c_1*pwr(abs(lef*1e6),mis_c_2)*pwr(abs(wef*1e6),mis_c_3)'    
+d='mis_d_1*pwr(abs(lef*1e6),mis_d_2)*pwr(abs(wef*1e6),mis_d_3)'    
+e='mis_e_1*pwr(abs(lef*1e6),mis_e_2)*pwr(abs(wef*1e6),mis_e_3)'    
    
+fac1='temp1'    
+fac2='temp2'    
+fac3='temp3'    
+fac4='temp4'    
+fac5='c*temp4+sqrt(1-c*c)*temp5'    
    
+geo_fac ='1/sqrt(multi*nf*lef*wef*1e12)*mismatchflag*local_factor_hv18*sigma_factor_hv18*1'    
+toxn_hv18_ms_local='d*geo_fac*toxn_hv18*fac1'    
+dxln_hv18_ms_local='b*geo_fac*lef*fac2'    
+dxwn_hv18_ms_local='-b*geo_fac*wef*fac3'    
+dvthn_hv18_ms_local='(a*geo_fac+((1/sqrt(multi*nf))*avtgm_min*mismatchflag*local_factor_hv18*sigma_factor_hv18))*fac4'    
+fu0n_hv18_ms_local='max(e_limit1,min(e_limit2,1+e*geo_fac*fac5*(1-totalflag)))'    
+lmonte_flagn_hv18_ms='1/sqrt(multi*nf)*fac5*mismatchflag*local_factor_hv18*sigma_factor_hv18*(1-totalflag)'    
    
**********************************************    
*       End of Mismatch Parameters           *    
**********************************************    
.param _bidirectionflag=1    
.param _designflag=1    
    
+a_1=1 b_1=0 c_1=0 d_1=0 e_1_1=0 e_1_2=0 f_1_1=0 f_1_2=0 g_1_1=0 g_1_2=0    
+a_2=1 b_2=0 c_2=0 d_2=0 e_2_1=0 e_2_2=0 f_2_1=0 f_2_2=0 g_2_1=0 g_2_2=0    
+a_3=1 b_3=0 c_3=0 d_3=0 e_3_1=0 e_3_2=0 f_3_1=0 f_3_2=0 g_3_1=0 g_3_2=0    
+a_4=0.98 b_4=0 c_4=0 d_4=0 e_4_1=0 e_4_2=0 f_4_1=0 f_4_2=0 g_4_1=0 g_4_2=0    
+a_5=1 b_5=0 c_5=0 d_5=0 e_5_1=0 e_5_2=0 f_5_1=0 f_5_2=0 g_5_1=0 g_5_2=0    
    
+ratio_f1='min(1,a_1+b_1/(lef*1e6)+c_1/(wef*1e6)+d_1/(lef*1e6*wef*1e6)+e_1_1*pwr(lef*1e6,e_1_2)+f_1_1*pwr(wef*1e6,f_1_2)+g_1_1*pwr(lef*1e6*wef*1e6,g_1_2))'    
+ratio_f2='min(1,a_2+b_2/(lef*1e6)+c_2/(wef*1e6)+d_2/(lef*1e6*wef*1e6)+e_2_1*pwr(lef*1e6,e_2_2)+f_2_1*pwr(wef*1e6,f_2_2)+g_2_1*pwr(lef*1e6*wef*1e6,g_2_2))'    
+ratio_f3='min(1,a_3+b_3/(lef*1e6)+c_3/(wef*1e6)+d_3/(lef*1e6*wef*1e6)+e_3_1*pwr(lef*1e6,e_3_2)+f_3_1*pwr(wef*1e6,f_3_2)+g_3_1*pwr(lef*1e6*wef*1e6,g_3_2))'    
    
+ratio_wl_t='1*_bidirectionflag+ratio_f1*(1-_bidirectionflag)'    
+ratio_wl_d='ratio_f2*_bidirectionflag+ratio_f3*(1-_bidirectionflag)'    
+ratio_wl='ratio_wl_d*_designflag+ratio_wl_t*(1-_designflag)'    
    
+ratio_f4='min(1,a_4+b_4/(lef*1e6)+c_4/(wef*1e6)+d_4/(lef*1e6*wef*1e6)+e_4_1*pwr(lef*1e6,e_4_2)+f_4_1*pwr(wef*1e6,f_4_2)+g_4_1*pwr(lef*1e6*wef*1e6,g_4_2))'    
+ratio_f5='min(1,a_5+b_5/(lef*1e6)+c_5/(wef*1e6)+d_5/(lef*1e6*wef*1e6)+e_5_1*pwr(lef*1e6,e_5_2)+f_5_1*pwr(wef*1e6,f_5_2)+g_5_1*pwr(lef*1e6*wef*1e6,g_5_2))'    
+ratio_global='(ratio_f4*_bidirectionflag+ratio_f5*(1-_bidirectionflag))*globalflag*global_factor_hv18*sigma_factor_hv18*1'    
    
    
+toxn_hv18_ms          ='3.36e-09+(toxn_hv18_ms_global*ratio_global+toxn_hv18_ms_local)*(1-totalflag)+(toxn_hv18-3.36e-09)*totalflag*ratio_wl'    
+dxln_hv18_ms          ='(dxln_hv18_ms_global*ratio_global+dxln_hv18_ms_local)*(1-totalflag)+dxln_hv18*totalflag*ratio_wl'    
+dxwn_hv18_ms          ='(dxwn_hv18_ms_global*ratio_global+dxwn_hv18_ms_local)*(1-totalflag)+dxwn_hv18*totalflag*ratio_wl'    
+cjsn_hv18_ms          ='1.4562e-03+(cjsn_hv18_ms_global*ratio_global)*(1-totalflag)+(cjsn_hv18-1.4562e-03)*totalflag*ratio_wl'    
+cjswsn_hv18_ms        ='1.0211e-10+(cjswsn_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswsn_hv18-1.0211e-10)*totalflag*ratio_wl'    
+cjswgsn_hv18_ms       ='1.2333e-10+(cjswgsn_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswgsn_hv18-1.2333e-10)*totalflag*ratio_wl'    
+cjdn_hv18_ms          ='1.58e-04+(cjdn_hv18_ms_global*ratio_global)*(1-totalflag)+(cjdn_hv18-1.58e-04)*totalflag*ratio_wl'    
+cjswdn_hv18_ms        ='5.53e-10+(cjswdn_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswdn_hv18-5.53e-10)*totalflag*ratio_wl'    
+cjswgdn_hv18_ms       ='5.98e-10+(cjswgdn_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswgdn_hv18-5.98e-10)*totalflag*ratio_wl'    
+cfsn_hv18_ms          ='7.9798e-11+(cfsn_hv18_ms_global*ratio_global)*(1-totalflag)+(cfsn_hv18-7.9798e-11)*totalflag*ratio_wl'    
+cfdsn_hv18_ms         ='(9.3925e-11-7.9798e-11)-(9.3925e-11-7.9798e-11)*(1-_ccoflag)+(cfdsn_hv18_ms_global*ratio_global)*(1-totalflag)+(cfdsn_hv18-((9.3925e-11-7.9798e-11)-(9.3925e-11-7.9798e-11)*(1-ccoflag_hv18)))*totalflag*ratio_wl'    
+cgdln_hv18_ms         ='7.8285e-10+(cgdln_hv18_ms_global*ratio_global)*(1-totalflag)+(cgdln_hv18-7.8285e-10)*totalflag*ratio_wl'    
+cgsln_hv18_ms         ='8.2431e-11+(cgsln_hv18_ms_global*ratio_global)*(1-totalflag)+(cgsln_hv18-8.2431e-11)*totalflag*ratio_wl'    
+cgdon_hv18_ms         ='3.908400e-011+2.5981e-13*_ccoflag+(cgdon_hv18_ms_global*ratio_global)*(1-totalflag)+(cgdon_hv18-3.908400e-011-2.5981e-13*ccoflag_hv18)*totalflag*ratio_wl'    
+cgson_hv18_ms         ='1.471200e-010+2.4058e-11*_ccoflag+(cgson_hv18_ms_global*ratio_global)*(1-totalflag)+(cgson_hv18-1.471200e-010-2.4058e-11*ccoflag_hv18)*totalflag*ratio_wl'    
+dvthn_hv18_ms         ='(dvthn_hv18_ms_global*ratio_global+dvthn_hv18_ms_local)*(1-totalflag)+dvthn_hv18*totalflag*ratio_wl'    
+dlvthn_hv18_ms        ='(dlvthn_hv18_ms_global*ratio_global)*(1-totalflag)+dlvthn_hv18*totalflag*ratio_wl'    
+dwvthn_hv18_ms        ='(dwvthn_hv18_ms_global*ratio_global)*(1-totalflag)+dwvthn_hv18*totalflag*ratio_wl'    
+dpvthn_hv18_ms        ='(dpvthn_hv18_ms_global*ratio_global)*(1-totalflag)+dpvthn_hv18*totalflag*ratio_wl'    
+dcitn_hv18_ms         ='(dcitn_hv18_ms_global*ratio_global)*(1-totalflag)+dcitn_hv18*totalflag*ratio_wl'    
+du0n_hv18_ms          ='(du0n_hv18_ms_global*ratio_global)*(1-totalflag)+du0n_hv18*totalflag*ratio_wl'    
+dlu0n_hv18_ms         ='(dlu0n_hv18_ms_global*ratio_global)*(1-totalflag)+dlu0n_hv18*totalflag*ratio_wl'    
+dwu0n_hv18_ms         ='(dwu0n_hv18_ms_global*ratio_global)*(1-totalflag)+dwu0n_hv18*totalflag*ratio_wl'    
+dpu0n_hv18_ms         ='(dpu0n_hv18_ms_global*ratio_global)*(1-totalflag)+dpu0n_hv18*totalflag*ratio_wl'    
+dvsatn_hv18_ms        ='(dvsatn_hv18_ms_global*ratio_global)*(1-totalflag)+dvsatn_hv18*totalflag*ratio_wl'    
+dwvsatn_hv18_ms       ='(dwvsatn_hv18_ms_global*ratio_global)*(1-totalflag)+dwvsatn_hv18*totalflag*ratio_wl'    
+dagsn_hv18_ms         ='(dagsn_hv18_ms_global*ratio_global)*(1-totalflag)+dagsn_hv18*totalflag*ratio_wl'    
+dlagsn_hv18_ms        ='(dlagsn_hv18_ms_global*ratio_global)*(1-totalflag)+dlagsn_hv18*totalflag*ratio_wl'    
+dwagsn_hv18_ms        ='(dwagsn_hv18_ms_global*ratio_global)*(1-totalflag)+dwagsn_hv18*totalflag*ratio_wl'    
+ss_flagn_hv18_ms      ='(ss_flagn_hv18_ms_global*ratio_global)*(1-totalflag)+ss_flagn_hv18*totalflag*ratio_wl'    
+ff_flagn_hv18_ms      ='(ff_flagn_hv18_ms_global*ratio_global)*(1-totalflag)+ff_flagn_hv18*totalflag*ratio_wl'    
+monte_flagn_hv18_ms   ='(monte_flagn_hv18_ms_global*ratio_global)*(1-totalflag)+monte_flagn_hv18*totalflag*ratio_wl'    
+ddlcn_hv18_ms         ='5.5333e-08+(ddlcn_hv18-5.5333e-08)*totalflag*ratio_wl'    
+dk2n_hv18_ms          ='dk2n_hv18*totalflag*ratio_wl'    
+dvoffn_hv18_ms        ='dvoffn_hv18*totalflag*ratio_wl'    
+dlvoffn_hv18_ms       ='dlvoffn_hv18*totalflag*ratio_wl'    
+dwvoffn_hv18_ms       ='dwvoffn_hv18*totalflag*ratio_wl'    
+dpvoffn_hv18_ms       ='dpvoffn_hv18*totalflag*ratio_wl'    
+dlcitn_hv18_ms        ='dlcitn_hv18*totalflag*ratio_wl'    
+dwcitn_hv18_ms        ='dwcitn_hv18*totalflag*ratio_wl'    
+dpcitn_hv18_ms        ='dpcitn_hv18*totalflag*ratio_wl'    
+deta0n_hv18_ms        ='deta0n_hv18*totalflag*ratio_wl'    
+duan_hv18_ms          ='duan_hv18*totalflag*ratio_wl'    
+dubn_hv18_ms          ='dubn_hv18*totalflag*ratio_wl'    
+dlvsatn_hv18_ms       ='dlvsatn_hv18*totalflag*ratio_wl'    
+dpvsatn_hv18_ms       ='dpvsatn_hv18*totalflag*ratio_wl'    
+da0n_hv18_ms          ='da0n_hv18*totalflag*ratio_wl'    
+dla0n_hv18_ms         ='dla0n_hv18*totalflag*ratio_wl'    
+dwa0n_hv18_ms         ='dwa0n_hv18*totalflag*ratio_wl'    
+dpa0n_hv18_ms         ='dpa0n_hv18*totalflag*ratio_wl'    
+dpagsn_hv18_ms        ='dpagsn_hv18*totalflag*ratio_wl'    
+dkt1n_hv18_ms         ='dkt1n_hv18*totalflag*ratio_wl'    
+dtvoffn_hv18_ms       ='dtvoffn_hv18*totalflag*ratio_wl'    
+dua1n_hv18_ms         ='dua1n_hv18*totalflag*ratio_wl'    
+dub1n_hv18_ms         ='dub1n_hv18*totalflag*ratio_wl'    
+datn_hv18_ms          ='datn_hv18*totalflag*ratio_wl'    
+dlatn_hv18_ms         ='dlatn_hv18*totalflag*ratio_wl'    
+dwatn_hv18_ms         ='dwatn_hv18*totalflag*ratio_wl'    
+dpatn_hv18_ms         ='dpatn_hv18*totalflag*ratio_wl'    
+sf_flagn_hv18_ms      ='(sf_flagn_hv18_ms_global*ratio_global)*(1-totalflag)+sf_flagn_hv18*totalflag*ratio_wl'    
+fs_flagn_hv18_ms      ='(fs_flagn_hv18_ms_global*ratio_global)*(1-totalflag)+fs_flagn_hv18*totalflag*ratio_wl'    
    
main n1 n2 n3 n4 nch_hv18 w='w' l='(l)' ad=ad as=as pd=pd ps=ps nrd=nrd nrs=nrs m=multi nf=nf sa=sa sb=sb sd=sd sca=sca scb=scb scc=scc sc=sc delvto=_delvto mulu0=_mulu0    
    
******* size dependence tox *******    
.param    
+toxe0=0.0   llt=0.0    lltn=1.0    
+wwt=0.0     wwtn=1.0   lwt=0.0    
    
+nctx='toxe0+llt/pwr((lef+_xl)/1e-6,lltn)+wwt/pwr((wef+_xw)/1e-6,wwtn)+lwt/pwr((lef+_xl)/1e-6,lltn)/pwr((wef+_xw)/1e-6,wwtn)'    
    
******* rshg *******    
.param    
+rsheet=80 drsh=0 rshh=-160 rshn=1.070    
+deltar='drsh+rshh / pwr(l*scale*1e6, rshn)'    
+dlr=-1.60e-08 llr=-2.2  llnr=0.17    
+deltal='dlr+llr*1e-6 / pwr(l*scale*1e6, llnr)'    
+reff='rsheet - deltar'    
+rmain='reff * w/nf*scale / (l*scale - deltal)'    
+rmainsh='rmain / (w/nf*scale) * (l*scale)'    
    
******* iboff_wl *******    
.param    
+r_rjtsswg=1.0   l_rjtsswg=-0.1   ll_rjtsswg=1.0   w_rjtsswg=0.13   ww_rjtsswg=1.0   p_rjtsswg=0.0    
+r_ragidl=1.0    l_ragidl=0.0    ll_ragidl=0.0    w_ragidl=0.0    ww_ragidl=0.0    p_ragidl=0.0    
    
+jtsswg_wl='(r_rjtsswg+l_rjtsswg/pwr((lef*1e6),ll_rjtsswg)+w_rjtsswg/pwr((wef*1e6),ww_rjtsswg)+p_rjtsswg/(lef*1e6*wef*1e6))'    
+agidl_wl='(r_ragidl+l_ragidl/pwr((lef*1e6),ll_ragidl)+w_ragidl/pwr((wef*1e6),ww_ragidl)+p_ragidl/(lef*wef*1e12))'    
    
******* diode dc *******    
.param    
+dxti=0    
    
**********************************    
*       layout effect parameter  *    
**********************************    
+lodflag=1 pseflag=0 ceslflag=0 oseflag=1 wpeflag=1 mbeflag=0    
    
**********************************    
*       lod   parameter          *    
**********************************    
.param    
+saref1    = 0.4365e-6          sbref1    = 0.4365e-6         sabl=0    
+saref2    = 0.4365e-6          sbref2    = 0.4365e-6    
+samax     = 4.5945e-6          sbmax    = 4.5945e-6    
+samin     = 0.1395e-6          sbmin    = 0.1395e-6    
+rllodflag = 1                  lreflod  = 1e-6               llodref  = 2    
+lod_clamp = -1e99    
    
********************************************************************    
+wlod     = 0    
+ku0      = 0                   lku0     = 0                   wku0     = 0    
+pku0     = 0                   tku0     = 0                   llodku0  = 1    
+wlodku0  = 1                   kvsat    = 1    
+kvth0    = 0                   lkvth0   = 0                   wkvth0   = 0    
+pkvth0   = 0                   llodvth  = 1                   wlodvth  = 1    
+stk2     = 0                   lodk2    = 1                   steta0   = 0    
+lodeta0  = 1    
+wlod0    = 0    
+ku00     = 0                   lku00     = 0                  wku00    = 0e+5         pku00     = -0.6e-22    
+llodku00 = 1                   wlodku00  = 1    
+kvth00   = 0                   lkvth00   = 0                  wkvth00  = 0         pkvth00   = 0e-14    
+llodvth0 = 1                   wlodvth0  = 1                  steta00   = 0    
+stk20    = 0                   lodk20    = 1                  lodeta00  = 1    
    
********************************************************************    
+wlod1    = 0                   llod1    = 0    
+ku01     = 0                   lku01    = 0e-16               wku01    = 0    
+pku01    = 0                   llodku01 = 1    
+wlodku01 = 1                   kvsat1   = 0    
+kvth01   = 0                   lkvth01  = 0                   wkvth01  = 0    
+pkvth01  = 0                   llodvth1 = 1                   wlodvth1 = 1    
+steta01  = 0                   lodeta01 = 1    
+stk21    = 0                   lodk21   = 1    
    
+wlod2    = 0    
+ku02     = 0                   lku02    = 0e-7                wku02    = -1e-7    
+pku02    = 0                   tku02    = 0                   llodku02 = -1    
+wlodku02 = 1                   kvsat2   = 0.42    
+kvth02   = -0.00159            lkvth02  = 4.5e-8              wkvth02  =-1.2e-7    
+pkvth02  = -3.9e-16            llodvth2 = -1                   wlodvth2 = 1    
+stk22    = 0                   lodk22   = 1                   steta02  = 0    
+lodeta02 = 1    
+wlod02   = 0    
    
+ku002    = 0.02                lku002    = 0e+2               wku002   = 1e-15           pku002    = 0.7e-22    
+llodku002= 1                   wlodku002 = 2    
+kvth002  = 0.0003              lkvth002  = 0.2e+4             wkvth002 = 3e-10           pkvth002  = 6e-4    
+llodvth02= -1                  wlodvth02 = 1                  steta002 = 0    
+stk202   = 0                   lodk202   = 1    
+lodeta002= 1    
    
+wlod3    = 0    
+ku03     = -0.00               lku03     = 0e5                wku03    = -0e-8    
+pku03    = 0                   tku03     = 0                  llodku03 = 1    
+wlodku03 = 1                   kvsat3    = 0.6    
+kvth03   = 0                   lkvth03   = 0e-9               wkvth03  = 0e-10    
+pkvth03  = 0e-18               llodvth3  = 1                  wlodvth3 = 1    
+stk23    = 0                   lodk23    = 1                  steta03  = 0    
+lodeta03 = 1    
+wlod03   = 0    
    
+ku003    = 0                   lku003     = 0e-1              wku003   = 10      pku003    = 0e+9    
+llodku003= 1.0                 wlodku003  = -0.5    
+kvth003  = -0.00212   	        lkvth003   = 0e-11             wkvth003 = 8.03e-10            pkvth003 = -0.4e-16    
+llodvth03  = 1                 wlodvth03  =  1                steta003  = 0    
+stk203   = 0                   lodk203    = 1    
+lodeta003= 1    
    
**********************************    
*       pse   parameter          *    
**********************************    
    
*** pse bin selection ***    
+sa_b      = 2.61e-7             sa_b1     = 0.99e-7             dpdbinflag= 1    
+w_b       = 9e-7                w_b1      = 5.4e-7    
    
*** 1st dp 1-order parameter ***    
+spa_ins1  = 1.8e-07           spa_ins2  = 1.8e-07    
+sparef1   = 1.8e-7              sparef2   = 1.8e-7              spabl     = 1.0e-6    
+spamax    = 2.08e-7             spamin    = 1.00e-7    
+kvth0dpc  = 0.00                wkvth0dpc = 0.0e-8              wdpckvth0 = 1    
+lkvth0dpc = 0.0e-8              ldpckvth0 = 1                   pkvth0dpc = 0.0e-15    
+ku0dpc    = 0.00                wku0dpc   = 0.0e-8              wdpcku0   = 1    
+lku0dpc   = 0.0e-8              ldpcku0   = 1                   pku0dpc   = 0.0e-14    
+keta0dpc  = 0.000               wketa0dpc = 0e-9                wdpcketa0 = 1    
+kvsatdpc  = 0.00                wdpc      = 0    
    
+kvth0dpc_b1 = -0.000            kvth0dpc_b2 = -0.000            dpcbinflg = 0    
+ku0dpc_b1   = 0                 ku0dpc_b2   =0    
+keta0dpc_b1 =0                  keta0dpc_b2 =0    
    
*** 1st dp 2-order parameter ***    
+kvth0dpl  = '0.15*01'           wkvth0dpl = 0.0e-8              wdplkvth0 = 1    
+lkvth0dpl = '1.4e-12*1'         ldplkvth0 = 1.5                 pkvth0dpl = 0.0e-19    
+ku0dpl    = '0.50*0'            wku0dpl   = 0e-8                wdplku0   = 1    
+lku0dpl   = 5.0e-8              ldplku0   = 1.0                 pku0dpl   = 0.0e-11    
+keta0dpl  = '0.07*0'            wketa0dpl = 0e-7                wdplketa0 = 1    
+kvsatdpl  = 0.00                wdpl      = 0    
    
+kvth0dpl_b1 = -0.000            kvth0dpl_b2 = -0.000            dplbinflg = 0    
+ku0dpl_b1   = 0                 ku0dpl_b2   =0    
+keta0dpl_b1 =0                  keta0dpl_b2 =0    
    
*** 1st dp reverse 3-order parameter ***    
+kvth0dpx  = -0.000              wkvth0dpx = 0e-07               wdpxkvth0 = 1    
+lkvth0dpx = 0.0e-8              ldpxkvth0 = 1.0                 pkvth0dpx = 0.0e-18    
+ku0dpx    = '0.25*1'            wku0dpx   = 0e-9                wdpxku0   = 1    
+lku0dpx   = '1.0e-8*1'          ldpxku0   = 1.0                 pku0dpx   = 0.0e-18    
+keta0dpx  = 0.00                wketa0dpx = 0e-7                wdpxketa0 = 1    
+kvsatdpx  = 0.00                wdpx      = 0    
    
+kvth0dpx_b1 = -0.000            kvth0dpx_b2 = -0.000            dpxbinflg = 0    
+ku0dpx_b1   = 0                 ku0dpx_b2   =0    
+keta0dpx_b1 =0                  keta0dpx_b2 =0    
    
*** 1st dp 2-order wi l dependence parameter ***    
+kvth0dps  = '0.1*1'             wkvth0dps = 0                   wdpskvth0 = 1    
+lkvth0dps = -0.0e-9             ldpskvth0 = 1.0                 pkvth0dps = 0    
+ku0dps    = '-0.70*1'           wku0dps   = -0.0e-9             wdpsku0   = 1    
+lku0dps   = '9.0e-15*1'         ldpsku0   = 2.0                 pku0dps   = '-7.0e-23*0'    
+keta0dps  = 0.00                wketa0dps = 0                   wdpsketa0 = 1    
+kvsatdps  = '-0.3*0'            wdps      = 0    
    
+kvth0dps_b1 = -0.000            kvth0dps_b2 = -0.000            dpsbinflg = 0    
+ku0dps_b1   = 0                 ku0dps_b2   =0    
+keta0dps_b1 =0                  keta0dps_b2 =0    
    
*** 1st dp sa dependence parameter ***    
+kvth0dpa  = '0.01*0'            wkvth0dpa = -0.0e-10            wdpakvth0 = 1    
+lkvth0dpa = '1.0e-9*0'          ldpakvth0 = 1.0                 pkvth0dpa = 0.0e-19    
+ku0dpa    = '0.050*0'           wku0dpa   = 0e-7                wdpaku0   = 1    
+lku0dpa   = 0.0e-11             ldpaku0   = 1.0                 pku0dpa   = -0.0e-18    
+keta0dpa  = 0.00                wketa0dpa = 0e-7                wdpaketa0 = 1    
+ka0dpa    = -0.0                wka0dpa   = 0                   wdpaka0   = 1    
+lka0dpa   = -0.0e-7             ldpaka0   = 1.0                 pka0dpa   = 0.0e-14    
+kvsatdpa  = '1.5*0'             wdpa      = 0    
    
+kvth0dpa_b1 = 0.006             kvth0dpa_b2 = -0.006            dpabinflg = 0    
+ku0dpa_b1   = -0.04             ku0dpa_b2   =0.04    
+keta0dpa_b1 =0                  keta0dpa_b2 =0    
+ka0dpa_b1    =0                 ka0dpa_b2    =0    
    
*** 2nd dp parameter ***    
+spb_ins1  = 5.1e-7           spb_ins2  = 5.1e-7    
+spbref1   = 5.1e-7              spbref2   = 5.1e-7              spbbl     = 1.0e-6    
+spbmax    = 'spamax+3.7e-7'     spbmin    = 'spamin+0e-7'    
+pse_mode  = 1    
+kvth0dp2  = '0.005*1'           wkvth0dp2 = -0.0e-8             wdp2kvth0 = 1    
+lkvth0dp2 = '3e-9*1'            ldp2kvth0 = 1.0                 pkvth0dp2 = 0.0e-19    
+ku0dp2    = 0.000               wku0dp2   = -0.0e-8             wdp2ku0   = 1    
+lku0dp2   = '7.0e-5*1'          ldp2ku0   = 0.5                 pku0dp2   = 0    
+keta0dp2  = 0.00                wketa0dp2 = -0e-9               wdp2keta0 = 1    
+kvsatdp2  = '0.0'               wdp2      = 0    
    
*** 2nd dp parameter wi l dependence parameter ***    
+kvth0dp2l  = -0.00              wkvth0dp2l = -0.0e-8            wdp2lkvth0 = 1    
+lkvth0dp2l = 0.0e-9             ldp2lkvth0 = 1                  pkvth0dp2l = 0    
+ku0dp2l    = 0.00               wku0dp2l   = -0.0e-8            wdp2lku0   = 1    
+lku0dp2l   = 0.0e-9             ldp2lku0   = 1.0                pku0dp2l   = 0    
+keta0dp2l  = 0.00               wketa0dp2l = -0e-9              wdp2lketa0 = 1    
+kvsatdp2l  = 0                  wdp2l      = 0    
    
+kvth0dp2l_b1 = 0.016            kvth0dp2l_b2 = -0.016           dp2lbinflg = 0    
+ku0dp2l_b1   = -0.04            ku0dp2l_b2   =0.04    
+keta0dp2l_b1 =0                 keta0dp2l_b2 =0    
    
*** 2nd dp sa dependence parameter ***    
+kvth0dp2a  = 0.00               wkvth0dp2a = -0.0e-9            wdp2akvth0 = 1    
+lkvth0dp2a = 0.0e-9             ldp2akvth0 = 1.0                pkvth0dp2a = -0.0e-17    
+ku0dp2a    = 0.00               wku0dp2a   = 0e-9               wdp2aku0   = 1    
+lku0dp2a   = 0.0e-5             ldp2aku0   = 0.5                pku0dp2a   = -0.0e-18    
+keta0dp2a  = 0.00               wketa0dp2a = 0e-7               wdp2aketa0 = 1    
+ka0dp2a    = 0                  wka0dp2a   = 0                  wdp2aka0   = 1    
+lka0dp2a   = 0                  ldp2aka0   = 1.0                pka0dp2a   = 0.0e-14    
+kvsatdp2a  = 0.00               wdp2a      = 0    
    
+kvth0dp2a_b1 = -0.000           kvth0dp2a_b2 = -0.000           dp2abinflg = 0    
+ku0dp2a_b1   = 0                ku0dp2a_b2   =0    
+keta0dp2a_b1 =0                 keta0dp2a_b2 =0    
+ka0dp2a_b1   =0                 ka0dp2a_b2   =0    
    
*** enx parameter ***    
+enxref    = 2.0e-5              enxmax    = 2.0e-5              enxmin    = 0.295e-6    
+kvth0enx  = 0.12                wkvth0enx = 0e-8                wenxkvth0 = 1    
+lkvth0enx = 0.0e-4              lenxkvth0 = 1.0                 pkvth0enx = 0    
+ku0enx    = -0.6                wku0enx   = 0		         wenxku0   = 1    
+lku0enx   = 0	                 lenxku0   = 1.0                 pku0enx   = -8.5e-15    
+keta0enx  = 0.00                wketa0enx = 0                   wenxketa0 = 1    
+ka0enx    = -0.0                wka0enx   = 0                   wenxka0   = 1    
+lka0enx   = 0.0e-7              lenxka0   = 1.0                 pka0enx   = 0.0e-14    
+kvsatenx  = 0.5                 wenx      = 0                   ku0enx0   = 0.0    
    
*** eny parameter ***    
+enyref    = 2.0e-5              enymax    = 2.0e-5              enymin    = 0.02e-6    
+kvth0eny  = 0.1		 wkvth0eny = 6.0e-9              wenykvth0 = 1    
+lkvth0eny = 1.0e-6		 lenykvth0 = 1.0                 pkvth0eny = 1.0e-16    
+ku0eny    = -0.04		 wku0eny   = -3.0e-8             wenyku0   = 1    
+ku0eny0   = 0.00		 wku0eny0  = 0                   weny0ku0  = 1    
+lku0eny   = -0.0e-10		 lenyku0   = 1.0                 pku0eny   = 1.0e-15    
+keta0eny  = 0.00                wketa0eny = 0                   wenyketa0 = 1    
+ka0eny    = -0.00               wka0eny   = -0.0e-8             wenyka0   = 1    
+lka0eny   = -0.0e-8             lenyka0   = 1.0                 pka0eny   = 0.0e-14    
+kvsateny  = 0.1                 weny      = 0    
+kvth0eny1  = 0.000              wkvth0eny1 = 0.0e-9             weny1kvth0 = 1    
+lkvth0eny1 = 0.0e-6             leny1kvth0 = 1.0                pkvth0eny1 = 0    
+ku0eny1    = 0.0                wku0eny1   = 0.0e-8             weny1ku0   = 1    
+lku0eny1   = 0.0e-5             leny1ku0   = 1.0                pku0eny1   = -0.0e-14    
+keta0eny1  = 0.00               wketa0eny1 = 0                  weny1keta0 = 1    
+ka0eny1    = 0                  wka0eny1   = 0                  weny1ka0   = 1    
+lka0eny1   = 0                  leny1ka0   = 1.0                pka0eny1   = 0    
+kvsateny1  = -0.0               weny1      = 0    
    
*** rx parameter ***    
+rxref     = 4e-5                ringxmax  = 4e-5                ringxmin  = 0.495e-6    
+rx_mode   = 0    
+kvth0rx   = -0.06               wkvth0rx  = -0.0e-5             wrxkvth0  = 1.0    
+lkvth0rx  = 0.0e-9              lrxkvth0  = 1.0                 pkvth0rx  = 2.0e-16    
+ku0rx     = 1.2                 wku0rx    = 0.0e-8              wrxku0    = 1.0    
+lku0rx    = 6.0e-8              lrxku0    = 1                   pku0rx    = -0.0e-15    
+keta0rx   = 0.00                wketa0rx  = 0                   wrxketa0  = 1    
+kvsatrx   = 0.5                 wrx       = 0                   ku0rx0    = 0    
    
*** ry parameter ***    
+ryref     = 4e-5                ringymax  = 4e-5                ringymin  = 0.22e-6    
+ry_mode   = 0    
+kvth0ry   = -0.002              wkvth0ry  = -0.0e-5             wrykvth0  = 1.0    
+lkvth0ry  = -2.7e-8             lrykvth0  = 1.0                 pkvth0ry  = -0.8e-16    
+ku0ry     = 0.01                wku0ry    = -0.0e-8             wryku0    = 1.0    
+lku0ry    = -0.0e-8             lryku0    = 1.0                 pku0ry    = 5.0e-16    
+keta0ry   = 0.00                wketa0ry  = 0                   wryketa0  = 1    
+kvsatry   = 0                   wry       = 0    
+kvth0ry0  = 0.00                ku0ry0    = 0.00    
    
*** sfx parameter ***    
+sfxref      = 0.18e-6           sfxmax     = 2.556e-6           minwodx     = 0.0e-6    
+sfxmin     = 0.135e-6           sfxmax4     = 2.556e-6           wodx        = 0e-6    
    
*** sfx set 1 ***    
+lrefodx     = 5e-8              lodxref     = 1    
+kvth0odxa   = '-0.16*0'         lkvth0odxa  = '0*1.5e-6'        lodxakvth0  = 1.0    
+wkvth0odxa  = 0.0e-7            wodxakvth0  = 1.0               pkvth0odxa  = 0.0e-16    
+ku0odxa     = '-0.001*0'        lku0odxa    = '0*-1.0e-6'       lodxaku0    = 1.0    
+wku0odxa    = '5.0e-7*0'        wodxaku0    = 1.0               pku0odxa    = 0.0e-16    
+keta0odx    = 0.00              wketa0odx   = 0                 wodxketa0   = 1    
+kvsatodx    = 0.2    
    
+kvth0odxb   = '-0.022'          lkvth0odxb  = '0.03e-8'            lodxbkvth0  = 1    
+wkvth0odxb  = -0.1e-8           wodxbkvth0  = 1.0               pkvth0odxb  = 0    
+ku0odxb     = -0.050             lku0odxb    = '-0.4e-7*0.75'          lodxbku0    = 1    
+wku0odxb    = 1e-5              wodxbku0    = -1.0               pku0odxb    = '1.0e-3*0'    
    
*** sfx set 2 ***    
+lrefodx1    = 5e-8              lodx1ref    = 1                 r_sodx1     = 0    
+kvth0odx1a  = '-0.001'          lkvth0odx1a = '1.5e-8'        lodx1akvth0 = 1.0    
+wkvth0odx1a = 0.0e-7            wodx1akvth0 = 1.0               pkvth0odx1a = 0.0e-16    
+ku0odx1a    = '-0.02'           lku0odx1a   = '1.0e-7'          lodx1aku0   = 1.0    
+wku0odx1a   = '5.5e-7*0'        wodx1aku0   = 1.0               pku0odx1a   = '1e-15*0'    
+keta0odx1   = 0.00              wketa0odx1  = 0                 wodx1keta0  = 1    
+kvsatodx1   = 0    
    
+kvth0odx1b  = '-0.002*0'       lkvth0odx1b = '0*0.22e-9'       lodx1bkvth0 = 1.0    
+wkvth0odx1b = '0*-1.0e-9'       wodx1bkvth0 = 1.0               pkvth0odx1b = '0.2e-16*0'    
+ku0odx1b    = '-0.001*0'          lku0odx1b   = '1.0e-9*0.15'       lodx1bku0   = 1.0    
+wku0odx1b   = -0.0e-5           wodx1bku0   = 1.0               pku0odx1b   = '0*-1.5e-16'    
    
*** sfx set 3 ***    
+csaodx3     = 0               csfxodx3    = 0              sfxpeak     = 0    
+kvth0odx3b  = 0               lkvth0odx3b = 0              lodx3bkvth0 = 1.0    
+wkvth0odx3b = -0.0e-5           wodx3bkvth0 = 1.0          pkvth0odx3b = 0    
+ku0odx3b    = 0                lku0odx3b   = 0            lodx3bku0   = 0.5    
+wku0odx3b   = 0.0e-10           wodx3bku0   = 1.0               pku0odx3b   = 0    
+keta0odx3   = 0e-5              kvsatodx3   = 0    
    
************************************************    
+kvth0odx4b  = 0.0               lkvth0odx4b = 0e-16           lodx4bkvth0 = 1    
+wkvth0odx4b = -0.0e-5           wodx4bkvth0 = 1.0               pkvth0odx4b = 0.0e-16    
+ku0odx4b    = -0                lku0odx4b   = -0.0e-8           lodx4bku0   = 1.0    
+wku0odx4b   = 0.0e-10           wodx4bku0   = 1.0               pku0odx4b   = 0.0e-18    
+keta0odx4   = 0              kvsatodx4   = 0    
    
+wketa0odx4  = 0                 wodx4keta0  = 1    
    
+lrefodx4    = 5e-8            lodx4ref    = 1    
+kvth0odx4a  = 0               lkvth0odx4a = 0           lodx4akvth0 = 1    
+wkvth0odx4a = 0               wodx4akvth0 = 1           pkvth0odx4a = 0    
+ku0odx4a    = 0               lku0odx4a   = 0           lodx4aku0   = 1    
+wku0odx4a   = 0               wodx4aku0   = 1           pku0odx4a   = 0    
    
************************************************    
+sfxmax5= 1.5e-6    
    
+kvth0odx5b  = 0             lkvth0odx5b = 0               lodx5bkvth0 = 1    
+wkvth0odx5b = 0             wodx5bkvth0 = 1.0             pkvth0odx5b = 0    
    
+kvtmax_sodx= 0.00    
+kvth0_a_lsodx     = 0      kvth0_b_lsodx = 0    
+kvth0_a_sa1sodx   = 0       kvth0_b_sa1sodx = 0    
+kvth0_a_sa2sodx   = 0         kvth0_b_sa2sodx = 0    
    
+ku0odx5b     = 0             lku0odx5b    = 0            lodx5bku0    = 1.00    
+wku0odx5b    = 0             wodx5bku0    = 1.0          pku0odx5b    = 0    
    
+ku0max_sodx= 0    
+ku0_a_lsodx     = 0      ku0_b_lsodx = 0    
+ku0_a_sa1sodx   = 0        ku0_b_sa1sodx = 0    
+ku0_a_sa2sodx   = 0         ku0_b_sa2sodx = 0    
    
+kvsatodx5   = 0    
    
************************************************    
*** sfy parameter ***    
+sfyref      = 0.5085e-6    
+sfymin      = 0.135e-6    
+sfymax      = 2.7e-6             minwody     = 0e-6            wody        = 5e-7    
    
*** sfy set 1 ***    
    
+kvth0odya   = '0'             lkvth0odya  = 0.0e-13           lodyakvth0  = 1.0    
+wkvth0odya  = -0.0e-6           wodyakvth0  = 0.5               pkvth0odya  = 0.0e-16    
+ku0odya     = 0.0001             lku0odya    = -2.0e-8          lodyaku0    = 1.0    
+wku0odya    = -1.0e-2            wodyaku0    = 1               pku0odya    = 0.0e-16    
+keta0ody    = -0.03              wketa0ody   = 0                 wodyketa0   = 1    
+kvsatody    = -0.15    
+lrefody     = 5e-8              lodyref     = 1    
    
+kvth0odyb   = '0.001'       lkvth0odyb  = '-0.4e-8'         lodybkvth0  = 1.0    
+wkvth0odyb  = 0             wodybkvth0  = 1.0               pkvth0odyb  = '-0.24e-13'    
+ku0odyb     = -0.02         lku0odyb    = '-0.4e-14'        lodybku0    = 2.0    
+wku0odyb    = '-0.4e-7*2'       wodybku0    = 1.0               pku0odyb    = '5e-20*0.2'    
    
*** sfy set 2 ***    
    
+expody1     = 2    
+kvth0ody1a  = 0.0               lkvth0ody1a = 0.0               lody1akvth0 = 1.0    
+wkvth0ody1a = 0.0               wody1akvth0 = 1.0               pkvth0ody1a = 0.0    
+ku0ody1a    = '0'         lku0ody1a   = '0'       lody1aku0   = 1.0    
+wku0ody1a   = '0'          wody1aku0   = 1.0               pku0ody1a   = 0.0    
+keta0ody1   = '0.001*0'         wketa0ody1  = 0.0               wody1keta0  = 1.0    
+kvsatody1   = 0.05    
+lrefody1    = 5e-8              lody1ref    = 1.0    
    
+kvth0ody1b  = '-0.000026'        lkvth0ody1b = '0.000025e-7*3.2'   lody1bkvth0 = 1.0    
+wkvth0ody1b = '0.00016e-7*0.5'         wody1bkvth0 = 1.0              pkvth0ody1b = '0.0003e-13*1.5'    
+ku0ody1b    = '0.00024*2'           lku0ody1b   = '0.00008e-13*1.0'            lody1bku0   = 2.0    
+wku0ody1b   = '-0.018e-8*0.03'        wody1bku0   = 1              pku0ody1b   = '-0.00006e-19'    
    
**********************************    
*       mbe   parameter          *    
**********************************    
+spmref  = 0.2115e-6    spmmax  = 0.2115e-6     spmmin  = 0.0585e-6    
+spomref = 0            spommax = 0.4725e-6     spommin = 0    
+mbe_clamp= -1e99    
    
***********************************************************    
    
+wspom1 = 0    
    
+kvth0spom1 = 0               lkvth0spom1 = 0              wkvth0spom1 = 0               pkvth0spom1 = 0    
+lspom1vth0 = 1               wspom1vth0  = 1    
+ku0spom1   = 0               lku0spom1   = 0              wku0spom1   = 0               pku0spom1   = 0    
+lspom1ku0  = 1               wspom1ku0   = 1    
+kvsatspom1 = 0               tku0spom1   = 0    
+spom1eta0  = 1               steta0spom1 = 0    
    
***********************************************************    
    
+wspm = 0    
    
+kvth0spm = 0                lkvth0spm = 0                 wkvth0spm = 0                 pkvth0spm = 0    
+lspmvth0 = 1                wspmvth0  = 1    
+ku0spm   = 0                lku0spm   = 0                 wku0spm   = 0                 pku0spm   = 0    
+lspmku0  = 1                wspmku0   = 1    
+kvsatspm = 0                tku0spm   = 0    
+spmeta0  = 1                steta0spm = 0    
    
*** wpe vsat parameter ***    
+web_mac=369.833  wec_mac=-2895.46    
+kvsatwe=-0.0035    
+keta0we=-0.0000    
    
**********************************    
*       lod   model              *    
**********************************    
.param    
+rllod='1/(1+pwr((lef+_xl)/lreflod,llodref)*rllodflag)'    
+saref='saref1+(saref2-saref1)*(min(max(lef,sabl),sabl+1e-10)-sabl)/1e-10'    
+sbref='sbref1+(sbref2-sbref1)*(min(max(lef,sabl),sabl+1e-10)-sabl)/1e-10'    
    
+sel1_sa='min(sa*scale,samax)'    
+sel1_sb='min(sb*scale,sbmax)'    
+sel_sa='max(sel1_sa,samin)'    
+sel_sb='max(sel1_sb,sbmin)'    
+inv_sa='1/(sel_sa+0.5*lef)'    
+inv_sb='1/(sel_sb+0.5*lef)'    
+inv_saref='1/(saref+0.5*lef)'    
+inv_sbref='1/(sbref+0.5*lef)'    
+kstress_u0='(1+lku0/pwr((lef+_xl),llodku0)+wku0/pwr((wef+_xw+wlod),wlodku0)+pku0/pwr((lef+_xl),llodku0)/pwr((wef+_xw+wlod),wlodku0))*(1+tku0*(temper/25-1))'    
+kstress_vth0='1+lkvth0/pwr((lef+_xl),llodvth)+wkvth0/pwr((wef+_xw+wlod),wlodvth)+pkvth0/pwr((lef+_xl),llodvth)/pwr((wef+_xw+wlod),wlodvth)'    
+kstress_u00='(ku00+lku00/pwr((lef+_xl),llodku00)+wku00/pwr((wef+_xw+wlod0),wlodku00)+pku00/pwr((lef+_xl),llodku00)/pwr((wef+_xw+wlod0),wlodku00))*(1+tku0*(temper/25-1))'    
+kstress_vth00='kvth00+lkvth00/pwr((lef+_xl),llodvth0)+wkvth00/pwr((wef+_xw+wlod0),wlodvth0)+pkvth00/pwr((lef+_xl),llodvth0)/pwr((wef+_xw+wlod0),wlodvth0)'    
+rho_ueff='(ku0/kstress_u0+kstress_u00)*(inv_sa+inv_sb)'    
+rho_ueffref='(ku0/kstress_u0+kstress_u00)*(inv_saref+inv_sbref)'    
    
+sel1_sa1='min(sa1*scale,samax)'    
+sel1_sb1='min(sb1*scale,sbmax)'    
+sel_sa1='max(sel1_sa1,samin)'    
+sel_sb1='max(sel1_sb1,sbmin)'    
+inv_sa1='1/pwr((sel_sa1+0.1*lef),3)'    
+inv_sb1='1/pwr((sel_sb1+0.1*lef),3)'    
+inv_saref1='1/pwr((saref+0.1*lef),3)'    
+inv_sbref1='1/pwr((sbref+0.1*lef),3)'    
+kstress_u01='1e-15*(ku01+lku01/pwr((lef+_xl+llod1),llodku01)+wku01/pwr((wef+_xw+wlod1),wlodku01)+pku01/pwr((lef+_xl+llod1),llodku01)/pwr((wef+_xw+wlod1),wlodku01))/(1+tku0*(temper/25-1))'    
+kstress_vth01='1e-15*(kvth01+lkvth01/pwr((lef+_xl+llod1),llodvth1)+wkvth01/pwr((wef+_xw+wlod1),wlodvth1)+pkvth01/pwr((lef+_xl+llod1),llodvth1)/pwr((wef+_xw+wlod1),wlodvth1))'    
+rho_ueff1='kstress_u01*(inv_sa1+inv_sb1)'    
+rho_ueffref1='kstress_u01*(inv_saref1+inv_sbref1)'    
    
+sel1_sa2='min(sa2*scale,samax)'    
+sel1_sb2='min(sb2*scale,sbmax)'    
+sel_sa2='max(sel1_sa2,samin)'    
+sel_sb2='max(sel1_sb2,sbmin)'    
+inv_sa2='pwr((pwr(5e-7/(sel_sa2+0.5*lef),2)+1),0.5)'    
+inv_sb2='pwr((pwr(5e-7/(sel_sb2+0.5*lef),2)+1),0.5)'    
+inv_saref2='pwr((pwr(5e-7/(saref+0.5*lef),2)+1),0.5)'    
+inv_sbref2='pwr((pwr(5e-7/(sbref+0.5*lef),2)+1),0.5)'    
+kstress_u02='(1+lku02/pwr((lef+_xl),llodku02)+wku02/pwr((wef+_xw+wlod2),wlodku02)+pku02/pwr((lef+_xl),llodku02)/pwr((wef+_xw+wlod2),wlodku02))*(1+tku02*(temper/25-1))'    
+kstress_vth02='1+lkvth02/pwr((lef+_xl),llodvth2)+wkvth02/pwr((wef+_xw+wlod2),wlodvth2)+pkvth02/pwr((lef+_xl),llodvth2)/pwr((wef+_xw+wlod2),wlodvth2)'    
+kstress_u002='(ku002+lku002/pwr((lef+_xl),llodku002)+wku002/pwr((wef+_xw+wlod02),wlodku002)+pku002/pwr((lef+_xl),llodku002)/pwr((wef+_xw+wlod02),wlodku002))*(1+tku02*(temper/25-1))'    
+kstress_vth002='kvth002+lkvth002/pwr((lef+_xl),llodvth02)+wkvth002/pwr((wef+_xw+wlod02),wlodvth02)+pkvth002/pwr((lef+_xl),llodvth02)/pwr((wef+_xw+wlod02),wlodvth02)'    
+rho_ueff2='(ku02/kstress_u02+kstress_u002)*(inv_sa2+inv_sb2)'    
+rho_ueffref2='(ku02/kstress_u02+kstress_u002)*(inv_saref2+inv_sbref2)'    
    
+sel1_sa3='min(sa3*scale,samax)'    
+sel1_sb3='min(sb3*scale,sbmax)'    
+sel_sa3='max(sel1_sa3,samin)'    
+sel_sb3='max(sel1_sb3,sbmin)'    
+inv_sa3='1/(1+pwr((5e-7/(sel_sa3+0.1*lef)),3))'    
+inv_sb3='1/(1+pwr((5e-7/(sel_sb3+0.1*lef)),3))'    
+inv_saref3='1/(1+pwr((5e-7/(saref+0.1*lef)),3))'    
+inv_sbref3='1/(1+pwr((5e-7/(sbref+0.1*lef)),3))'    
+kstress_u03='(1+lku03/pwr((lef+_xl),llodku03)+wku03/pwr((wef+_xw+wlod3),wlodku03)+pku03/pwr((lef+_xl),llodku03)/pwr((wef+_xw+wlod3),wlodku03))*(1+tku03*(temper/25-1))'    
+kstress_vth03='1+lkvth03/pwr((lef+_xl),llodvth3)+wkvth03/pwr((wef+_xw+wlod3),wlodvth3)+pkvth03/pwr((lef+_xl),llodvth3)/pwr((wef+_xw+wlod3),wlodvth3)'    
+kstress_u003='(ku003+lku003/pwr((lef+_xl),llodku003)+wku003/pwr((wef+_xw+wlod03),wlodku003)+pku003/pwr((lef+_xl),llodku003)/pwr((wef+_xw+wlod03),wlodku003))*(1+tku03*(temper/25-1))'    
+kstress_vth003='kvth003+lkvth003/pwr((lef+_xl),llodvth03)+wkvth003/pwr((wef+_xw+wlod03),wlodvth03)+pkvth003/pwr((lef+_xl),llodvth03)/pwr((wef+_xw+wlod03),wlodvth03)'    
+rho_ueff3='(ku03/kstress_u03+kstress_u003)*(inv_sa3+inv_sb3)'    
+rho_ueffref3='(ku03/kstress_u03+kstress_u003)*(inv_saref3+inv_sbref3)'    
    
**********************************    
*       pse   model              *    
**********************************    
+spavar='spa_ins1+(spa_ins2-spa_ins1)*(min(max(lef,spabl),spabl+1e-10)-spabl)/1e-10'    
+spbvar='spb_ins1+(spb_ins2-spb_ins1)*(min(max(lef,spbbl),spbbl+1e-10)-spbbl)/1e-10'    
+sparef='sparef1+(sparef2-sparef1)*(min(max(lef,spabl),spabl+1e-10)-spabl)/1e-10'    
+spbref='spbref1+(spbref2-spbref1)*(min(max(lef,spbbl),spbbl+1e-10)-spbbl)/1e-10'    
    
+sa_b2='min(max(max(sel_sa,sel_spa),sa_b1+1e-10)/(dpdbinflag+1e-20),sa_b)'    
+sa_b3='max((sa_b2-1e-10)*dpdbinflag,sa_b1)'    
+pse_wbin='(max(min(wef,w_b),w_b1)-w_b)/(w_b1-w_b+1e-10)'    
+pse_sabin='(max(min(sa4*scale,sa_b2),sa_b3)-sa_b2)/(sa_b3-sa_b2)'    
    
+sel1_spa='min(spa*scale,spamax)'    
+sel_spa='max(sel1_spa,spamin)'    
+inv_spa='-1e-7/pwr(sel_spa+3e-7,1)'    
+inv_sparef='-1e-7/pwr(sparef+3e-7,1)'    
+kdpc_vth0_0='kvth0dpc+lkvth0dpc/pwr((lef+_xl),ldpckvth0)+wkvth0dpc/pwr((wef+_xw+wdpc),wdpckvth0)+pkvth0dpc/pwr((lef+_xl),ldpckvth0)/pwr((wef+_xw+wdpc),wdpckvth0)'    
+kdpc_eta0_0='keta0dpc+wketa0dpc/pwr((wef+_xw+wdpc),wdpcketa0)'    
+kdpc_u0_0='ku0dpc+lku0dpc/pwr((lef+_xl),ldpcku0)+wku0dpc/pwr((wef+_xw+wdpc),wdpcku0)+pku0dpc/pwr((lef+_xl),ldpcku0)/pwr((wef+_xw+wdpc),wdpcku0)'    
+kdpc_vth0_1='kvth0dpc_b1+(kvth0dpc_b2-kvth0dpc_b1)*pse_wbin'    
+kdpc_eta0_1='keta0dpc_b1+(keta0dpc_b2-keta0dpc_b1)*pse_wbin'    
+kdpc_u0_1='ku0dpc_b1+(ku0dpc_b2-ku0dpc_b1)*pse_wbin'    
+kdpc_vth0='kdpc_vth0_0+((kdpc_vth0_1-kdpc_vth0_0)*pse_sabin)*dpcbinflg'    
+kdpc_eta0='kdpc_eta0_0+((kdpc_eta0_1-kdpc_eta0_0)*pse_sabin)*dpcbinflg'    
+kdpc_u0='kdpc_u0_0+((kdpc_u0_1-kdpc_u0_0)*pse_sabin)*dpcbinflg'    
+dinv_spa='inv_spa-inv_sparef'    
+rho_ueffdpc='kdpc_u0*(inv_spa)'    
+rho_ueffrefdpc='kdpc_u0*(inv_sparef)'    
    
+sel1_spa1='min(spa1*scale,spamax)'    
+sel_spa1='max(sel1_spa1,spamin)'    
+inv_spa1='-1e-14/pwr(sel_spa1+3e-7,2)'    
+inv_spa1ref='-1e-14/pwr(sparef+3e-7,2)'    
+kdpl_vth0_0='kvth0dpl+lkvth0dpl/pwr((lef+_xl),ldplkvth0)+wkvth0dpl/pwr((wef+_xw+wdpl),wdplkvth0)+pkvth0dpl/pwr((lef+_xl),ldplkvth0)/pwr((wef+_xw+wdpl),wdplkvth0)'    
+kdpl_eta0_0='keta0dpl+wketa0dpl/pwr((wef+_xw+wdpl),wdplketa0)'    
+kdpl_u0_0='ku0dpl+lku0dpl/pwr((lef+_xl),ldplku0)+wku0dpl/pwr((wef+_xw+wdpl),wdplku0)+pku0dpl/pwr((lef+_xl),ldplku0)/pwr((wef+_xw+wdpl),wdplku0)'    
+kdpl_vth0_1='kvth0dpl_b1+(kvth0dpl_b2-kvth0dpl_b1)*pse_wbin'    
+kdpl_eta0_1='keta0dpl_b1+(keta0dpl_b2-keta0dpl_b1)*pse_wbin'    
+kdpl_u0_1='ku0dpl_b1+(ku0dpl_b2-ku0dpl_b1)*pse_wbin'    
+kdpl_vth0='kdpl_vth0_0+((kdpl_vth0_1-kdpl_vth0_0)*pse_sabin)*dplbinflg'    
+kdpl_eta0='kdpl_eta0_0+((kdpl_eta0_1-kdpl_eta0_0)*pse_sabin)*dplbinflg'    
+kdpl_u0='kdpl_u0_0+((kdpl_u0_1-kdpl_u0_0)*pse_sabin)*dplbinflg'    
+dinv_spa1='inv_spa1-inv_spa1ref'    
+rho_ueffdpl='kdpl_u0*(inv_spa1)'    
+rho_ueffrefdpl='kdpl_u0*(inv_spa1ref)'    
    
+sel1_spa2='min(spa2*scale,spamax)'    
+sel_spa2='max(sel1_spa2,spamin)'    
+inv_spa2='-1e-21/pwr(sel_spa2+0.1*lef,3)'    
+inv_spa2ref='-1e-21/pwr(sparef+0.1*lef,3)'    
+kvth0dpx_dn='1+lkvth0dpx/pwr((lef+_xl),ldpxkvth0)+wkvth0dpx/pwr((wef+_xw+wdpx),wdpxkvth0)+pkvth0dpx/pwr((lef+_xl),ldpxkvth0)/pwr((wef+_xw+wdpx),wdpxkvth0)'    
+kdpx_vth0_0='kvth0dpx/kvth0dpx_dn'    
+keta0dpx_dn='1+wketa0dpx/pwr((wef+_xw+wdpx),wdpxketa0)'    
+kdpx_eta0_0='keta0dpx/keta0dpx_dn'    
+ku0dpx_dn='1+lku0dpx/pwr((lef+_xl),ldpxku0)+wku0dpx/pwr((wef+_xw+wdpx),wdpxku0)+pku0dpx/pwr((lef+_xl),ldpxku0)/pwr((wef+_xw+wdpx),wdpxku0)'    
+kdpx_u0_0='ku0dpx/ku0dpx_dn'    
+kdpx_vth0_1='kvth0dpx_b1+(kvth0dpx_b2-kvth0dpx_b1)*pse_wbin'    
+kdpx_eta0_1='keta0dpx_b1+(keta0dpx_b2-keta0dpx_b1)*pse_wbin'    
+kdpx_u0_1='ku0dpx_b1+(ku0dpx_b2-ku0dpx_b1)*pse_wbin'    
+kdpx_vth0='kdpx_vth0_0+((kdpx_vth0_1-kdpx_vth0_0)*pse_sabin)*dpxbinflg'    
+kdpx_eta0='kdpx_eta0_0+((kdpx_eta0_1-kdpx_eta0_0)*pse_sabin)*dpxbinflg'    
+kdpx_u0='kdpx_u0_0+((kdpx_u0_1-kdpx_u0_0)*pse_sabin)*dpxbinflg'    
+dinv_spa2='inv_spa2-inv_spa2ref'    
+rho_ueffdpx='kdpx_u0*(inv_spa2)'    
+rho_ueffrefdpx='kdpx_u0*(inv_spa2ref)'    
    
+sel1_spa3='min(spa3*scale,spamax)'    
+sel_spa3='max(sel1_spa3,spamin)'    
+inv_spa3='-1e-14/pwr(sel_spa3+0.5*lef,2)'    
+inv_spa3ref='-1e-14/pwr(sparef+0.5*lef,2)'    
+kvth0dps_dn='1+lkvth0dps/pwr((lef+_xl),ldpskvth0)+wkvth0dps/pwr((wef+_xw+wdps),wdpskvth0)+pkvth0dps/pwr((lef+_xl),ldpskvth0)/pwr((wef+_xw+wdps),wdpskvth0)'    
+kdps_vth0_0='kvth0dps/kvth0dps_dn'    
+keta0dps_dn='1+wketa0dps/pwr((wef+_xw+wdps),wdpsketa0)'    
+kdps_eta0_0='keta0dps/keta0dps_dn'    
+ku0dps_dn='1+lku0dps/pwr((lef+_xl),ldpsku0)+wku0dps/pwr((wef+_xw+wdps),wdpsku0)+pku0dps/pwr((lef+_xl),ldpsku0)/pwr((wef+_xw+wdps),wdpsku0)'    
+kdps_u0_0='ku0dps/ku0dps_dn'    
+kdps_vth0_1='kvth0dps_b1+(kvth0dps_b2-kvth0dps_b1)*pse_wbin'    
+kdps_eta0_1='keta0dps_b1+(keta0dps_b2-keta0dps_b1)*pse_wbin'    
+kdps_u0_1='ku0dps_b1+(ku0dps_b2-ku0dps_b1)*pse_wbin'    
+kdps_vth0='kdps_vth0_0+((kdps_vth0_1-kdps_vth0_0)*pse_sabin)*dpsbinflg'    
+kdps_eta0='kdps_eta0_0+((kdps_eta0_1-kdps_eta0_0)*pse_sabin)*dpsbinflg'    
+kdps_u0='kdps_u0_0+((kdps_u0_1-kdps_u0_0)*pse_sabin)*dpsbinflg'    
+dinv_spa3='inv_spa3-inv_spa3ref'    
+rho_ueffdps='kdps_u0*(inv_spa3)'    
+rho_ueffrefdps='kdps_u0*(inv_spa3ref)'    
    
+sel1_sap='max(pwr(sap*scale,3),(sa4*scale+1e-9)*pwr(spamin+1e-9,2))'    
+sel2_sap='min(sel1_sap,(sa4*scale+1e-9)*pwr(spamax+1e-9,2))'    
+sel_sap='sel2_sap/(sa4*scale+1e-9)*(min(max(sa4*scale,samin),samax)+1e-9)'    
+inv_sap='-1e-21/sel_sap'    
+inv_sapref='-1e-21/(min(max(sa4*scale,samin),samax)+1e-9)/pwr(sparef+1e-9,2)'    
+kdpa_vth0_0='kvth0dpa+lkvth0dpa/pwr((lef+_xl),ldpakvth0)+wkvth0dpa/pwr((wef+_xw+wdpa),wdpakvth0)+pkvth0dpa/pwr((lef+_xl),ldpakvth0)/pwr((wef+_xw+wdpa),wdpakvth0)'    
+kdpa_eta0_0='keta0dpa+wketa0dpa/pwr((wef+_xw+wdpa),wdpaketa0)'    
+kdpa_u0_0='ku0dpa+lku0dpa/pwr((lef+_xl),ldpaku0)+wku0dpa/pwr((wef+_xw+wdpa),wdpaku0)+pku0dpa/pwr((lef+_xl),ldpaku0)/pwr((wef+_xw+wdpa),wdpaku0)'    
+kdpa_a0_0='ka0dpa+lka0dpa/pwr((lef+_xl),ldpaka0)+wka0dpa/pwr((wef+_xw+wdpa),wdpaka0)+pka0dpa/pwr((lef+_xl),ldpaka0)/pwr((wef+_xw+wdpa),wdpaka0)'    
+kdpa_vth0_1='kvth0dpa_b1+(kvth0dpa_b2-kvth0dpa_b1)*pse_wbin'    
+kdpa_eta0_1='keta0dpa_b1+(keta0dpa_b2-keta0dpa_b1)*pse_wbin'    
+kdpa_u0_1='ku0dpa_b1+(ku0dpa_b2-ku0dpa_b1)*pse_wbin'    
+kdpa_a0_1='ka0dpa_b1+(ka0dpa_b2-ka0dpa_b1)*pse_wbin'    
+kdpa_vth0='kdpa_vth0_0+((kdpa_vth0_1-kdpa_vth0_0)*pse_sabin)*dpabinflg'    
+kdpa_eta0='kdpa_eta0_0+((kdpa_eta0_1-kdpa_eta0_0)*pse_sabin)*dpabinflg'    
+kdpa_u0='kdpa_u0_0+((kdpa_u0_1-kdpa_u0_0)*pse_sabin)*dpabinflg'    
+kdpa_a0='kdpa_a0_0+((kdpa_a0_1-kdpa_a0_0)*pse_sabin)*dpabinflg'    
+dinv_sap='inv_sap-inv_sapref'    
+rho_ueffdpa='kdpa_u0*(inv_sap)'    
+rho_ueffrefdpa='kdpa_u0*(inv_sapref)'    
    
+sel1_spba='max(pwr(spba*scale*1e4,6),pwr((spa2*scale+0.1*lef),3)*pwr(spbmin-spamin,3)*1e24)'    
+sel2_spba='min(sel1_spba,pwr((spa2*scale+0.1*lef),3)*pwr(spbmax-spamax,3)*1e24)'    
+sel_spba='sel2_spba/pwr((spa2*scale+0.1*lef),3)*pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)'    
+inv_spba_c='-1e-21*pwr(sparef+0.1*lef,3)*(1-pse_mode+pse_mode*pwr(min(max(spa2*scale,spamin),spamax),2.5)/pwr(sparef+0.1*lef,2.5))'    
+inv_spba='inv_spba_c/sel_spba*1e24'    
+inv_spbaref='inv_spba_c/pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)/pwr(spbref-sparef,3)'    
+kdp2_vth0='kvth0dp2+lkvth0dp2/pwr((lef+_xl),ldp2kvth0)+wkvth0dp2/pwr((wef+_xw+wdp2),wdp2kvth0)+pkvth0dp2/pwr((lef+_xl),ldp2kvth0)/pwr((wef+_xw+wdp2),wdp2kvth0)'    
+kdp2_eta0='keta0dp2+wketa0dp2/pwr((wef+_xw+wdp2),wdp2keta0)'    
+kdp2_u0='ku0dp2+lku0dp2/pwr((lef+_xl),ldp2ku0)+wku0dp2/pwr((wef+_xw+wdp2),wdp2ku0)+pku0dp2/pwr((lef+_xl),ldp2ku0)/pwr((wef+_xw+wdp2),wdp2ku0)'    
+dinv_spba='inv_spba-inv_spbaref'    
+rho_ueffdp2='kdp2_u0*(inv_spba)'    
+rho_ueffrefdp2='kdp2_u0*(inv_spbaref)'    
    
+sel1_spba1='max(pwr(spba1*scale*1e4,6),pwr((spa2*scale+0.1*lef),3)*pwr(spbmin-spamin+0.1*lef,3)*1e24)'    
+sel2_spba1='min(sel1_spba1,pwr((spa2*scale+0.1*lef),3)*pwr(spbmax-spamax+0.1*lef,3)*1e24)'    
+sel_spba1='sel2_spba1/pwr((spa2*scale+0.1*lef),3)*pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)'    
+inv_spba1_c='-1e-21*pwr(sparef+0.1*lef,3)*(1-pse_mode+pse_mode*pwr(min(max(spa2*scale,spamin),spamax),2.5)/pwr(sparef+0.1*lef,2.5))'    
+inv_spba1='inv_spba1_c/sel_spba1*1e24'    
+inv_spba1ref='inv_spba1_c/pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)/pwr(spbref-sparef+0.1*lef,3)'    
+kvth0dp2l_dn='1+lkvth0dp2l/pwr((lef+_xl),ldp2lkvth0)+wkvth0dp2l/pwr((wef+_xw+wdp2l),wdp2lkvth0)+pkvth0dp2l/pwr((lef+_xl),ldp2lkvth0)/pwr((wef+_xw+wdp2l),wdp2lkvth0)'    
+kdp2l_vth0_0='kvth0dp2l/kvth0dp2l_dn'    
+keta0dp2l_dn='1+wketa0dp2l/pwr((wef+_xw+wdp2l),wdp2lketa0)'    
+kdp2l_eta0_0='keta0dp2l/keta0dp2l_dn'    
+ku0dp2l_dn='1+lku0dp2l/pwr((lef+_xl),ldp2lku0)+wku0dp2l/pwr((wef+_xw+wdp2l),wdp2lku0)+pku0dp2l/pwr((lef+_xl),ldp2lku0)/pwr((wef+_xw+wdp2l),wdp2lku0)'    
+kdp2l_u0_0='ku0dp2l/ku0dp2l_dn'    
+kdp2l_vth0_1='kvth0dp2l_b1+(kvth0dp2l_b2-kvth0dp2l_b1)*pse_wbin'    
+kdp2l_eta0_1='keta0dp2l_b1+(keta0dp2l_b2-keta0dp2l_b1)*pse_wbin'    
+kdp2l_u0_1='ku0dp2l_b1+(ku0dp2l_b2-ku0dp2l_b1)*pse_wbin'    
+kdp2l_vth0='kdp2l_vth0_0+((kdp2l_vth0_1-kdp2l_vth0_0)*pse_sabin)*dp2lbinflg'    
+kdp2l_eta0='kdp2l_eta0_0+((kdp2l_eta0_1-kdp2l_eta0_0)*pse_sabin)*dp2lbinflg'    
+kdp2l_u0='kdp2l_u0_0+((kdp2l_u0_1-kdp2l_u0_0)*pse_sabin)*dp2lbinflg'    
+dinv_spba1='inv_spba1-inv_spba1ref'    
+rho_ueffdp2l='kdp2l_u0*(inv_spba1)'    
+rho_ueffrefdp2l='kdp2l_u0*(inv_spba1ref)'    
    
+sel1_sapb='max(pwr(sapb*scale,4),(sa4*scale+1e-9)*pwr(spbmin-spamin+1e-9,3))'    
+sel2_sapb='min(sel1_sapb,(sa4*scale+1e-9)*pwr(spbmax-spamax+1e-9,3))'    
+sel_sapb='sel2_sapb/(sa4*scale+1e-9)*(min(max(sa4*scale,samin),samax)+1e-9)'    
+inv_sapb='-1e-28/sel_sapb'    
+inv_sapbref='-1e-28/(min(max(sa4*scale,samin),samax)+1e-9)/pwr(spbref-sparef+1e-9,3)'    
+kdp2a_vth0_0='kvth0dp2a+lkvth0dp2a/pwr((lef+_xl),ldp2akvth0)+wkvth0dp2a/pwr((wef+_xw+wdp2a),wdp2akvth0)+pkvth0dp2a/pwr((lef+_xl),ldp2akvth0)/pwr((wef+_xw+wdp2a),wdp2akvth0)'    
+kdp2a_eta0_0='keta0dp2a+wketa0dp2a/pwr((wef+_xw+wdp2a),wdp2aketa0)'    
+kdp2a_u0_0='ku0dp2a+lku0dp2a/pwr((lef+_xl),ldp2aku0)+wku0dp2a/pwr((wef+_xw+wdp2a),wdp2aku0)+pku0dp2a/pwr((lef+_xl),ldp2aku0)/pwr((wef+_xw+wdp2a),wdp2aku0)'    
+kdp2a_a0_0='ka0dp2a+lka0dp2a/pwr((lef+_xl),ldp2aka0)+wka0dp2a/pwr((wef+_xw+wdp2a),wdp2aka0)+pka0dp2a/pwr((lef+_xl),ldp2aka0)/pwr((wef+_xw+wdp2a),wdp2aka0)'    
+kdp2a_vth0_1='kvth0dp2a_b1+(kvth0dp2a_b2-kvth0dp2a_b1)*pse_wbin'    
+kdp2a_eta0_1='keta0dp2a_b1+(keta0dp2a_b2-keta0dp2a_b1)*pse_wbin'    
+kdp2a_u0_1='ku0dp2a_b1+(ku0dp2a_b2-ku0dp2a_b1)*pse_wbin'    
+kdp2a_a0_1='ka0dp2a_b1+(ka0dp2a_b2-ka0dp2a_b1)*pse_wbin'    
+kdp2a_vth0='kdp2a_vth0_0+((kdp2a_vth0_1-kdp2a_vth0_0)*pse_sabin)*dp2abinflg'    
+kdp2a_eta0='kdp2a_eta0_0+((kdp2a_eta0_1-kdp2a_eta0_0)*pse_sabin)*dp2abinflg'    
+kdp2a_u0='kdp2a_u0_0+((kdp2a_u0_1-kdp2a_u0_0)*pse_sabin)*dp2abinflg'    
+kdp2a_a0='kdp2a_a0_0+((kdp2a_a0_1-kdp2a_a0_0)*pse_sabin)*dp2abinflg'    
+dinv_sapb='inv_sapb-inv_sapbref'    
+rho_ueffdp2a='kdp2a_u0*(inv_sapb)'    
+rho_ueffrefdp2a='kdp2a_u0*(inv_sapbref)'    
    
**********************************    
*       cesl   model             *    
**********************************    
+sel1_enx='max(enx*scale,enxmin)'    
+sel_enx='min(sel1_enx,enxmax)'    
+inv_enx='1e-4/pwr(sel_enx+1.0*lef,0.5)'    
+inv_enxref='1e-4/pwr(enxref+1.0*lef,0.5)'    
+kvth0enx_dn='1+lkvth0enx/pwr((lef+_xl),lenxkvth0)'    
+kenx_vth0='kvth0enx/kvth0enx_dn+wkvth0enx/pwr((wef+_xw+wenx),wenxkvth0)+pkvth0enx/pwr((lef+_xl),lenxkvth0)/pwr((wef+_xw+wenx),wenxkvth0)'    
+kenx_eta0='keta0enx+wketa0enx/pwr((wef+_xw+wenx),wenxketa0)'    
+ku0enx_dn='1+lku0enx/pwr((lef+_xl),lenxku0)'    
+kenx_u0='ku0enx0+ku0enx/ku0enx_dn+wku0enx/pwr((wef+_xw+wenx),wenxku0)+pku0enx/pwr((lef+_xl),lenxku0)/pwr((wef+_xw+wenx),wenxku0)'    
+kenx_a0='ka0enx+lka0enx/pwr((lef+_xl),lenxka0)+wka0enx/pwr((wef+_xw+wenx),wenxka0)+pka0enx/pwr((lef+_xl),lenxka0)/pwr((wef+_xw+wenx),wenxka0)'    
+dinv_enx='inv_enx-inv_enxref'    
+rho_ueffenx='kenx_u0*(inv_enx)'    
+rho_ueffrefenx='kenx_u0*(inv_enxref)'    
    
+sel1_eny='max(eny*scale,enymin)'    
+sel_eny='min(sel1_eny,enymax)'    
+inv_eny='1e-7/pwr(sel_eny+1.0*lef,1)'    
+inv_enyref='1e-7/pwr(enyref+1.0*lef,1)'    
+kvth0eny_dn='1+lkvth0eny/pwr((lef+_xl),lenykvth0)'    
+keny_vth0='kvth0eny/kvth0eny_dn+wkvth0eny/pwr((wef+_xw+weny),wenykvth0)+pkvth0eny/pwr((lef+_xl),lenykvth0)/pwr((wef+_xw+weny),wenykvth0)'    
+keny_eta0='keta0eny+wketa0eny/pwr((wef+_xw)+weny,wenyketa0)'    
+ku0eny_dn='1+lku0eny/pwr((lef+_xl),lenyku0)+wku0eny0/pwr((wef+_xw+weny),weny0ku0)'    
+keny_u0='ku0eny0+ku0eny/ku0eny_dn+wku0eny/pwr((wef+_xw+weny),wenyku0)+pku0eny/pwr((lef+_xl),lenyku0)/pwr((wef+_xw+weny),wenyku0)'    
+keny_a0='ka0eny+lka0eny/pwr((lef+_xl),lenyka0)+wka0eny/pwr((wef+_xw+weny),wenyka0)+pka0eny/pwr((lef+_xl),lenyka0)/pwr((wef+_xw+weny),wenyka0)'    
+dinv_eny='inv_eny-inv_enyref'    
+rho_ueffeny='keny_u0*(inv_eny)'    
+rho_ueffrefeny='keny_u0*(inv_enyref)'    
    
+sel1_eny1='max(eny1*scale,enymin)'    
+sel_eny1='min(sel1_eny1,enymax)'    
+inv_eny1='1e-21/pwr(sel_eny1+0.05*lef,3)'    
+inv_eny1ref='1e-21/pwr(enyref+0.05*lef,3)'    
+kvth0eny1_dn='1+lkvth0eny1/pwr((lef+_xl),leny1kvth0)'    
+keny1_vth0='kvth0eny1/kvth0eny1_dn+wkvth0eny1/pwr((wef+_xw+weny1),weny1kvth0)+pkvth0eny1/pwr((lef+_xl),leny1kvth0)/pwr((wef+_xw+weny1),weny1kvth0)'    
+keta0eny1_dn='1+wketa0eny1/pwr((wef+_xw+weny1),weny1keta0)'    
+keny1_eta0='keta0eny1/keta0eny1_dn'    
+ku0eny1_dn='1+lku0eny1/pwr((lef+_xl),leny1ku0)'    
+keny1_u0='ku0eny1/ku0eny1_dn+wku0eny1/pwr((wef+_xw+weny1),weny1ku0)+pku0eny1/pwr((lef+_xl),leny1ku0)/pwr((wef+_xw+weny1),weny1ku0)'    
+keny1_a0='ka0eny1+lka0eny1/pwr((lef+_xl),leny1ka0)+wka0eny1/pwr((wef+_xw+weny1),weny1ka0)+pka0eny1/pwr((lef+_xl),leny1ka0)/pwr((wef+_xw+weny1),weny1ka0)'    
+dinv_eny1='inv_eny1-inv_eny1ref'    
+rho_ueffeny1='keny1_u0*(inv_eny1)'    
+rho_ueffrefeny1='keny1_u0*(inv_eny1ref)'    
    
+sel1_rex='max(pwr(rex*scale,2),(enx1*scale+1e-9)*(ringxmin+1.0*lef))'    
+sel2_rex='min(sel1_rex,(enx1*scale+1e-9)*(ringxmax+1.0*lef))'    
+sel_rex='sel2_rex/(enx1*scale+1e-9)*(min(max(enx1*scale,enxmin),enxmax)+1e-9)'    
+inv_rex_c='pwr(min(max(enx1*scale,enxmin),enxmax)+1e-9,0.5)*1e4*rx_mode+1-rx_mode'    
+inv_rex='1e-14*inv_rex_c/sel_rex'    
+inv_rexref='1e-14*inv_rex_c/(min(max(enx1*scale,enxmin),enxmax)+1e-9)/(rxref-enxref+1.0*lef)'    
+kvth0rx_dn='1+lkvth0rx/pwr((lef+_xl),lrxkvth0)'    
+krex_vth0='kvth0rx/kvth0rx_dn+wkvth0rx/pwr((wef+_xw+wrx),wrxkvth0)+pkvth0rx/pwr((lef+_xl),lrxkvth0)/pwr((wef+_xw+wrx),wrxkvth0)'    
+krex_eta0='keta0rx+wketa0rx/pwr((wef+_xw+wrx),wrxketa0)'    
+ku0rx_dn='1+lku0rx/pwr((lef+_xl),lrxku0)'    
+krex_u0='ku0rx0+ku0rx/ku0rx_dn+wku0rx/pwr((wef+_xw+wrx),wrxku0)+pku0rx/pwr((lef+_xl),lrxku0)/pwr((wef+_xw+wrx),wrxku0)'    
+dinv_rex='inv_rex-inv_rexref'    
+rho_ueffrex='krex_u0*(inv_rex)'    
+rho_ueffrefrex='krex_u0*(inv_rexref)'    
    
+sel1_rey='max(pwr(rey*scale,2),(eny2*scale+1e-9)*(ringymin+1.0*lef))'    
+sel2_rey='min(sel1_rey,(eny2*scale+1e-9)*(ringymax+1.0*lef))'    
+sel_rey='sel2_rey/(eny2*scale+1e-9)*(min(max(eny2*scale,enymin),enymax)+1e-9)'    
+inv_rey_c='pwr(min(max(eny2*scale,enymin),enymax)+1e-9,0.8)*1e5*ry_mode+1-ry_mode'    
+inv_rey='1e-14*inv_rey_c/sel_rey'    
+inv_reyref='1e-14*inv_rey_c/(min(max(eny2*scale,enymin),enymax)+1e-9)/(ryref-enyref+1.0*lef)'    
+kvth0ry_dn='1+lkvth0ry/pwr((lef+_xl),lrykvth0)'    
+krey_vth0='kvth0ry0+kvth0ry/kvth0ry_dn+wkvth0ry/pwr((wef+_xw+wry),wrykvth0)+pkvth0ry/pwr((lef+_xl),lrykvth0)/pwr((wef+_xw+wry),wrykvth0)'    
+krey_eta0='keta0ry+wketa0ry/pwr((wef+_xw+wry),wryketa0)'    
+ku0ry_dn='1+lku0ry/pwr((lef+_xl),lryku0)'    
+krey_u0='ku0ry0+ku0ry/ku0ry_dn+wku0ry/pwr((wef+_xw+wry),wryku0)+pku0ry/pwr((lef+_xl),lryku0)/pwr((wef+_xw+wry),wryku0)'    
+dinv_rey='inv_rey-inv_reyref'    
+rho_ueffrey='krey_u0*(inv_rey)'    
+rho_ueffrefrey='krey_u0*(inv_reyref)'    
    
**********************************    
*       ose   model              *    
**********************************    
+sel1_sodx='min(sodx*scale,sfxmax)'    
+sel_sodx='max(sel1_sodx,sfxmin)'    
+inv_sodx='-1e-4/pwr(sel_sodx,0.5)'    
+inv_sodxref='-1e-4/pwr(sfxref,0.5)'    
    
+sel1_sodx1='min(pwr(sodx1*scale,1.5),(sa5*scale+1.0e-7)*pwr(sfxmax,0.5))'    
+sel2_sodx1='max(sel1_sodx1,(sa5*scale+1.0e-7)*pwr(sfxmin,0.5))'    
+sel_sodx1='sel2_sodx1/(sa5*scale+1.0e-7)*(min(max(sa5*scale,samin),samax)+1.0e-7)'    
+inv_sodx1='-1e-9/sel_sodx1*r_sodx1'    
+inv_sodx1ref='-1e-9/(min(max(sa5*scale,samin),samax)+1.0e-7)/pwr(sfxref,0.5)*r_sodx1'    
    
+sel1_sodx2='min(pwr(sodx2*scale,3.5),(1e-18+10*pwr(sa6*scale,3))*pwr(sfxmax,0.5))'    
+sel2_sodx2='max(sel1_sodx2,(1e-18+10*pwr(sa6*scale,3))*pwr(sfxmin,0.5))'    
+sel_sodx2='sel2_sodx2/(1e-18+10*pwr(sa6*scale,3))*(1e-18+10*pwr(min(max(sa6*scale,samin),samax),3))'    
+inv_sodx2='-1e-20/sel_sodx2*(1-r_sodx1)'    
+inv_sodx2ref='-1e-20/(1e-18+10*pwr(min(max(sa6*scale,samin),samax),3))/pwr(sfxref,0.5)*(1-r_sodx1)'    
    
+wmax_sodx='max(wef,minwodx)+_xw+wodx'    
+kvth0odxa_dn='1+lkvth0odxa/pwr((lef+_xl),lodxakvth0)'    
+ksodx_vth0a='kvth0odxa/kvth0odxa_dn*(1+wkvth0odxa/pwr(wmax_sodx,wodxakvth0))+pkvth0odxa/pwr((lef+_xl),lodxakvth0)/pwr(wmax_sodx,wodxakvth0)'    
+ksodx_vth0b='kvth0odxb+lkvth0odxb/pwr((lef+_xl),lodxbkvth0)+wkvth0odxb/pwr(wmax_sodx,wodxbkvth0)+pkvth0odxb/pwr((lef+_xl),lodxbkvth0)/pwr(wmax_sodx,wodxbkvth0)'    
+ku0odxa_dn='1+lku0odxa/pwr((lef+_xl),lodxaku0)'    
+ksodx_u0a='ku0odxa/ku0odxa_dn*(1+wku0odxa/pwr(wmax_sodx,wodxaku0))+pku0odxa/pwr((lef+_xl),lodxaku0)/pwr(wmax_sodx,wodxaku0)'    
+ksodx_u0b='ku0odxb+lku0odxb/pwr((lef+_xl),lodxbku0)+wku0odxb/pwr(wmax_sodx,wodxbku0)+pku0odxb/pwr((lef+_xl),lodxbku0)/pwr(wmax_sodx,wodxbku0)'    
+ksodx_eta0='keta0odx+wketa0odx/pwr(wmax_sodx,wodxketa0)'    
+dinv_sodx='inv_sodx-inv_sodxref'    
+rlsodx='pwr(lrefodx/(lrefodx+lef),lodxref)'    
+rho_ueffsodx='(ksodx_u0a*rlsodx+ksodx_u0b)*inv_sodx'    
+rho_ueffrefsodx='(ksodx_u0a*rlsodx+ksodx_u0b)*inv_sodxref'    
+kvth0odx1a_dn='1+lkvth0odx1a/pwr((lef+_xl),lodx1akvth0)'    
+ksodx1_vth0a='kvth0odx1a/kvth0odx1a_dn*(1+wkvth0odx1a/pwr(wmax_sodx,wodx1akvth0))+pkvth0odx1a/pwr((lef+_xl),lodx1akvth0)/pwr(wmax_sodx,wodx1akvth0)'    
+ksodx1_vth0b='kvth0odx1b+lkvth0odx1b/pwr((lef+_xl),lodx1bkvth0)+wkvth0odx1b/pwr(wmax_sodx,wodx1bkvth0)+pkvth0odx1b/pwr((lef+_xl),lodx1bkvth0)/pwr(wmax_sodx,wodx1bkvth0)'    
+ku0odx1a_dn='1+lku0odx1a/pwr((lef+_xl),lodx1aku0)'    
+ksodx1_u0a='ku0odx1a/ku0odx1a_dn*(1+wku0odx1a/pwr(wmax_sodx,wodx1aku0))+pku0odx1a/pwr((lef+_xl),lodx1aku0)/pwr(wmax_sodx,wodx1aku0)'    
+ksodx1_u0b='ku0odx1b+lku0odx1b/pwr((lef+_xl),lodx1bku0)+wku0odx1b/pwr(wmax_sodx,wodx1bku0)+pku0odx1b/pwr((lef+_xl),lodx1bku0)/pwr(wmax_sodx,wodx1bku0)'    
+ksodx1_eta0='keta0odx1+wketa0odx1/pwr(wmax_sodx,wodx1keta0)'    
+dinv_sodx1='(inv_sodx1-inv_sodx1ref)'    
+dinv_sodx2='(inv_sodx2-inv_sodx2ref)'    
+rlsodx1='pwr(lrefodx1/(lrefodx1+lef),lodx1ref)'    
+rho_ueffsodx1='(ksodx1_u0a*rlsodx1+ksodx1_u0b)*(inv_sodx1+inv_sodx2)'    
+rho_ueffrefsodx1='(ksodx1_u0a*rlsodx1+ksodx1_u0b)*(inv_sodx1ref+inv_sodx2ref)'    
    
+inv_sodx3_c='1e-9/(min(max(sa5*scale,samin),samax)+csaodx3)/(sel_sodx+csfxodx3)'    
+inv_sodx3='inv_sodx3_c*min(sel_sodx,sfxpeak)'    
+inv_sodx3ref='inv_sodx3_c*sfxref'    
+ksodx3_vth0b='kvth0odx3b+lkvth0odx3b/pwr((lef+_xl),lodx3bkvth0)+wkvth0odx3b/pwr(wef+_xw+wodx,wodx3bkvth0)+pkvth0odx3b/pwr((lef+_xl),lodx3bkvth0)/pwr(wef+_xw+wodx,wodx3bkvth0)'    
+ksodx3_u0b='ku0odx3b+lku0odx3b/pwr((lef+_xl),lodx3bku0)+wku0odx3b/pwr(wef+_xw+wodx,wodx3bku0)+pku0odx3b/pwr((lef+_xl),lodx3bku0)/pwr(wef+_xw+wodx,wodx3bku0)'    
+ksodx3_eta0='keta0odx3'    
+dinv_sodx3='(inv_sodx3-inv_sodx3ref)'    
+rho_ueffsodx3='(ksodx3_u0b)*inv_sodx3'    
+rho_ueffrefsodx3='(ksodx3_u0b)*inv_sodx3ref'    
    
+sel1_sodx4='min(pwr(sodx4*scale,3.5),pwr(sa7*scale+1.0e-9,3)*pwr(sfxmax4,0.5))'    
+sel2_sodx4='max(sel1_sodx4,pwr(sa7*scale+1.0e-9,3)*pwr(sfxmin,0.5))'    
+sel_sodx4='sel2_sodx4/pwr(sa7*scale+1.0e-9,3)*pwr(min(max(sa7*scale,samin),samax)+1.0e-9,3)'    
+inv_sodx4='-1e-26/sel_sodx4'    
+inv_sodx4ref='-1e-26/pwr(min(max(sa7*scale,samin),samax)+1.0e-9,3)/pwr(sfxref,0.5)'    
+kvth0odx4a_dn='1+lkvth0odx4a/pwr((lef+_xl),lodx4akvth0)'    
+ksodx4_vth0a='kvth0odx4a/kvth0odx4a_dn*(1+wkvth0odx4a/pwr(wef+_xw+wodx,wodx4akvth0))+pkvth0odx4a/pwr((lef+_xl),lodx4akvth0)/pwr(wef+_xw+wodx,wodx4akvth0)'    
+ku0odx4a_dn='1+lku0odx4a/pwr((lef+_xl),lodx4aku0)'    
+ksodx4_u0a='ku0odx4a/ku0odx4a_dn*(1+wku0odx4a/pwr(wef+_xw+wodx,wodx4aku0))+pku0odx4a/pwr((lef+_xl),lodx4aku0)/pwr(wef+_xw+wodx,wodx4aku0)'    
+ksodx4_vth0b='kvth0odx4b+lkvth0odx4b/pwr((lef+_xl),lodx4bkvth0)+wkvth0odx4b/pwr(wef+_xw+wodx,wodx4bkvth0)+pkvth0odx4b/pwr((lef+_xl),lodx4bkvth0)/pwr(wef+_xw+wodx,wodx4bkvth0)'    
+ksodx4_u0b='ku0odx4b+lku0odx4b/pwr((lef+_xl),lodx4bku0)+wku0odx4b/pwr(wef+_xw+wodx,wodx4bku0)+pku0odx4b/pwr((lef+_xl),lodx4bku0)/pwr(wef+_xw+wodx,wodx4bku0)'    
+ksodx4_eta0='keta0odx4+wketa0odx4/pwr(wef+_xw+wodx,wodx4keta0)'    
+dinv_sodx4='(inv_sodx4-inv_sodx4ref)'    
+rlsodx4='pwr(lrefodx4/(lrefodx4+lef),lodx4ref)'    
+rho_ueffsodx4='(ksodx4_u0a*rlsodx4+ksodx4_u0b)*inv_sodx4'    
+rho_ueffrefsodx4='(ksodx4_u0a*rlsodx4+ksodx4_u0b)*inv_sodx4ref'    
    
+inv_sodxa5='min(sel_sodxa5,sfxmax5)'    
+inv_sodxb5='min(sel_sodxb5,sfxmax5)'    
+dinv_sodx5='abs((inv_sodxb5-inv_sodxa5))'    
    
+sel1_sa9='min(sa*scale,samax)'    
+sel1_sb9='min(sb*scale,sbmax)'    
+sel_sa9='max(sel1_sa9,samin)'    
+sel_sb9='max(sel1_sb9,sbmin)'    
    
+sel1_sodxa5='min(sodxa*scale,sfxmax)'    
+sel1_sodxb5='min(sodxb*scale,sfxmax)'    
+sel_sodxa5='max(sel1_sodxa5,sfxmin)'    
+sel_sodxb5='max(sel1_sodxb5,sfxmin)'    
+dsodxflag='sgn(abs(sodxa*scale-sodxb*scale))'    
    
+ksodx5_vth0b='kvth0odx5b+lkvth0odx5b/pwr((lef+_xl),lodx5bkvth0)+wkvth0odx5b/pwr(wef+_xw+wodx,wodx5bkvth0)+pkvth0odx5b/pwr((lef+_xl),lodx5bkvth0)/pwr(wef+_xw+wodx,wodx5bkvth0)'    
+ksodx5_vth5max='((kvth0_a_lsodx/lef)*1e-6+kvth0_b_lsodx)*(max(kvtmax_sodx,max((kvth0_a_sa1sodx*sel_sa9*1e6+kvth0_b_sa1sodx),(kvth0_a_sa2sodx*sel_sa9*1e6+kvth0_b_sa2sodx))+max((kvth0_a_sa1sodx*sel_sb9*1e6+kvth0_b_sa1sodx),(kvth0_a_sa2sodx*sel_sb9*1e6+kvth0_b_sa2sodx))))'    
+ksodx5_vth5='(sfxmin/min(sodxa*scale,sodxb*scale))*(ksodx5_vth0b*ksodx5_vth5max)'    
    
+ksodx5_u0b='ku0odx5b+lku0odx5b/pwr((lef+_xl),lodx5bku0)+wku0odx5b/pwr(wmax_sodx,wodx5bku0)+pku0odx5b/pwr((lef+_xl),lodx5bku0)/pwr(wmax_sodx,wodx5bku0)'    
+rho_ueffsodx5max='((ku0_a_lsodx/lef)*1e-6+ku0_b_lsodx)*(min(ku0max_sodx,min((ku0_a_sa1sodx*sel_sa9*1e6+ku0_b_sa1sodx),(ku0_a_sa2sodx*sel_sa9*1e6+ku0_b_sa2sodx))+min((ku0_a_sa1sodx*sel_sb9*1e6+ku0_b_sa1sodx),(ku0_a_sa2sodx*sel_sb9*1e6+ku0_b_sa2sodx))))'    
+rho_ueffsodx5='(sfxmin/min(sodxa*scale,sodxb*scale))*(max(ksodx5_u0b*dinv_sodx5,rho_ueffsodx5max))'    
    
+sel1_sody='max(sody*scale,sfymin)'    
+sel_sody='min(sel1_sody,sfymax)'    
+inv_sody='-1e-4/pwr(sel_sody,0.5)'    
+inv_sodyref='-1e-4/pwr(sfyref,0.5)'    
+wmax_sody='max(wef,minwody)+_xw+wody'    
+kvth0odya_dn='1+lkvth0odya/pwr((lef+_xl),lodyakvth0)'    
+ksody_vth0a='kvth0odya/kvth0odya_dn*(1+wkvth0odya/pwr(wmax_sody,wodyakvth0))+pkvth0odya/pwr((lef+_xl),lodyakvth0)/pwr(wmax_sody,wodyakvth0)'    
+ksody_vth0b='kvth0odyb+lkvth0odyb/pwr((lef+_xl),lodybkvth0)+wkvth0odyb/pwr(wmax_sody,wodybkvth0)+pkvth0odyb/pwr((lef+_xl),lodybkvth0)/pwr(wmax_sody,wodybkvth0)'    
+ku0odya_dn='1+lku0odya/pwr((lef+_xl),lodyaku0)'    
+ksody_u0a='ku0odya/ku0odya_dn*(1+wku0odya/pwr(wmax_sody,wodyaku0))+pku0odya/pwr((lef+_xl),lodyaku0)/pwr(wmax_sody,wodyaku0)'    
+ksody_u0b='ku0odyb+lku0odyb/pwr((lef+_xl),lodybku0)+wku0odyb/pwr(wmax_sody,wodybku0)+pku0odyb/pwr((lef+_xl),lodybku0)/pwr(wmax_sody,wodybku0)'    
+ksody_eta0='keta0ody+wketa0ody/pwr((wef+_xw+wody),wodyketa0)'    
+dinv_sody='inv_sody-inv_sodyref'    
+rlsody='pwr(lrefody/(lrefody+lef),lodyref)'    
+rho_ueffsody='(ksody_u0a*rlsody+ksody_u0b)*(inv_sody)'    
+rho_ueffrefsody='(ksody_u0a*rlsody+ksody_u0b)*(inv_sodyref)'    
    
+inv_sody1='-1*pwr(1e-6/min(sel_sody,sfyref),expody1)'    
+inv_sody1ref='-1*pwr(1e-6/sfyref,expody1)'    
+kvth0ody1a_dn='1+lkvth0ody1a/pwr((lef+_xl),lody1akvth0)'    
+ksody1_vth0a='kvth0ody1a/kvth0ody1a_dn*(1+wkvth0ody1a/pwr(wmax_sody,wody1akvth0))+pkvth0ody1a/pwr((lef+_xl),lody1akvth0)/pwr(wmax_sody,wody1akvth0)'    
+ksody1_vth0b='kvth0ody1b+lkvth0ody1b/pwr((lef+_xl),lody1bkvth0)+wkvth0ody1b/pwr(wmax_sody,wody1bkvth0)+pkvth0ody1b/pwr((lef+_xl),lody1bkvth0)/pwr(wmax_sody,wody1bkvth0)'    
+ku0ody1a_dn='1+lku0ody1a/pwr((lef+_xl),lody1aku0)'    
+ksody1_u0a='ku0ody1a/ku0ody1a_dn*(1+wku0ody1a/pwr(wmax_sody,wody1aku0))+pku0ody1a/pwr((lef+_xl),lody1aku0)/pwr(wmax_sody,wody1aku0)'    
+ksody1_u0b='ku0ody1b+lku0ody1b/pwr((lef+_xl),lody1bku0)+wku0ody1b/pwr(wmax_sody,wody1bku0)+pku0ody1b/pwr((lef+_xl),lody1bku0)/pwr(wmax_sody,wody1bku0)'    
+ksody1_eta0='keta0ody1+wketa0ody1/pwr(wmax_sody,wody1keta0)'    
+dinv_sody1='inv_sody1-inv_sody1ref'    
+rlsody1='pwr(lrefody1/(lrefody1+lef),lody1ref)'    
+rho_ueffsody1='(ksody1_u0a*rlsody1+ksody1_u0b)*(inv_sody1)'    
+rho_ueffrefsody1='(ksody1_u0a*rlsody1+ksody1_u0b)*(inv_sody1ref)'    
    
**********************************    
*       mbe   model              *    
**********************************    
+selmbet='max(0,sgn(spomt*scale))'    
+selmbeb='max(0,sgn(spomb*scale))'    
    
+sel1_spmt='min(spmt*scale,spmmax)'    
+sel_spmt='max(sel1_spmt,spmmin)'    
+inv_spmt='1/pwr(sel_spmt,2)'    
+sel1_spmb='min(spmb*scale,spmmax)'    
+sel_spmb='max(sel1_spmb,spmmin)'    
+inv_spmb='1/pwr(sel_spmb,2)'    
+inv_spmref='1/pwr(spmref,2)'    
    
+sel1_spomt1='min(pwr(spomt1*scale,0.5),pwr(spmmax,1)/pwr(max(spomt*scale,1e-30),0.5))'    
+sel2_spomt1='max(sel1_spomt1,pwr(spmmin,1)/pwr(max(spomt*scale,1e-30),0.5))'    
+sel_spomt1='sel2_spomt1*pwr(max(spomt*scale,1e-30),0.5)/pwr(min(max(max(spomt*scale,1e-30),spommin),spommax),0.5)'    
+inv_spomt1='1/sel_spomt1'    
+sel1_spomb1='min(pwr(spomb1*scale,0.5),pwr(spmmax,1)/pwr(max(spomb*scale,1e-30),0.5))'    
+sel2_spomb1='max(sel1_spomb1,pwr(spmmin,1)/pwr(max(spomb*scale,1e-30),0.5))'    
+sel_spomb1='sel2_spomb1*pwr(max(spomb*scale,1e-30),0.5)/pwr(min(max(max(spomb*scale,1e-30),spommin),spommax),0.5)'    
+inv_spomb1='1/sel_spomb1'    
+inv_spom1ref='pwr(spomref,0.5)/spmref'    
    
+kspom1_u0='(ku0spom1+lku0spom1/pwr((lef+_xl),lspom1ku0)+wku0spom1/pwr((wef+_xw+wspom1),wspom1ku0)+pku0spom1/pwr((lef+_xl),lspom1ku0)/pwr((wef+_xw+wspom1),wspom1ku0))*(1+tku0spom1*(temper/25-1))'    
+kspom1_vth0='kvth0spom1+lkvth0spom1/pwr((lef+_xl),lspom1vth0)+wkvth0spom1/pwr((wef+_xw+wspom1),wspom1vth0)+pkvth0spom1/pwr((lef+_xl),lspom1vth0)/pwr((wef+_xw+wspom1),wspom1vth0)'    
+rho_ueffspomt1='kspom1_u0*inv_spomt1'    
+rho_ueffspomb1='kspom1_u0*inv_spomb1'    
+rho_ueffrefspom1='kspom1_u0*inv_spom1ref'    
    
+kspm_u0='(ku0spm+lku0spm/pwr((lef+_xl),lspmku0)+wku0spm/pwr((wef+_xw+wspm),wspmku0)+pku0spm/pwr((lef+_xl),lspmku0)/pwr((wef+_xw+wspm),wspmku0))*(1+tku0spm*(temper/25-1))'    
+kspm_vth0='kvth0spm+lkvth0spm/pwr((lef+_xl),lspmvth0)+wkvth0spm/pwr((wef+_xw+wspm),wspmvth0)+pkvth0spm/pwr((lef+_xl),lspmvth0)/pwr((wef+_xw+wspm),wspmvth0)'    
+rho_ueffspmt='kspm_u0*inv_spmt'    
+rho_ueffspmb='kspm_u0*inv_spmb'    
+rho_ueffrefspm='kspm_u0*inv_spmref'    
    
**********************************    
*       total lde model          *    
**********************************    
    
+dvths_sa='((kvth0/kstress_vth0+kstress_vth00)*(inv_sa+inv_sb-inv_saref-inv_sbref)+kstress_vth01*(inv_sa1+inv_sb1-inv_saref1-inv_sbref1)+(kvth02/kstress_vth02+kstress_vth002)*(inv_sa2+inv_sb2-inv_saref2-inv_sbref2)+(kvth03/kstress_vth03+kstress_vth003)*(inv_sa3+inv_sb3-inv_saref3-inv_sbref3))*rllod'    
+dvths_dp='-kdpc_vth0*dinv_spa-kdpl_vth0*dinv_spa1-kdpx_vth0*dinv_spa2-kdps_vth0*dinv_spa3-kdpa_vth0*dinv_sap-kdp2_vth0*dinv_spba-kdp2l_vth0*dinv_spba1-kdp2a_vth0*dinv_sapb'    
+dvths_enxy='kenx_vth0*dinv_enx+keny_vth0*dinv_eny+keny1_vth0*dinv_eny1+selmin(krex_vth0*inv_rex,kenx_vth0*inv_enx)-krex_vth0*inv_rexref+selmin(krey_vth0*inv_rey,keny_vth0*inv_eny+keny1_vth0*inv_eny1)-krey_vth0*inv_reyref'    
+dvths_odod='-1*(ksodx_vth0a*rlsodx+ksodx_vth0b)*dinv_sodx-(ksodx1_vth0a*rlsodx1+ksodx1_vth0b)*(dinv_sodx1+dinv_sodx2)-(ksodx3_vth0b)*(dinv_sodx3)-(ksodx4_vth0a*rlsodx4+ksodx4_vth0b)*(dinv_sodx4)-(ksodx5_vth5)*(dinv_sodx5)*dsodxflag-(ksody_vth0a*rlsody+ksody_vth0b)*dinv_sody-(ksody1_vth0a*rlsody1+ksody1_vth0b)*dinv_sody1'    
+dvths_spomt1='kspom1_vth0*(inv_spomt1-inv_spom1ref)'    
+dvths_spomb1='kspom1_vth0*(inv_spomb1-inv_spom1ref)'    
+dvths_spmt='kspm_vth0*(inv_spmt-inv_spmref)'    
+dvths_spmb='kspm_vth0*(inv_spmb-inv_spmref)'    
+dvths_mbe='(dvths_spomt1+dvths_spmt)*selmbet+(dvths_spomb1+dvths_spmb)*selmbeb'    
+dvths_lod='dvths_sa*lodflag+dvths_dp*pseflag+dvths_enxy*ceslflag+dvths_odod*oseflag+dvths_mbe*mbeflag'    
    
+fu0_sa_nu='max((1+(rho_ueff+rho_ueff1+rho_ueff2+rho_ueff3)*rllod*lodflag),lod_clamp)'    
+fu0_sa_dn='max((1+(rho_ueffref+rho_ueffref1+rho_ueffref2+rho_ueffref3)*rllod*lodflag),lod_clamp)'    
+fu0_sa='fu0_sa_nu/fu0_sa_dn'    
+fu0_dp_nu='(1+(rho_ueffdpc+rho_ueffdpl+rho_ueffdpx+rho_ueffdps+rho_ueffdpa)*pseflag)*(1+(rho_ueffdp2+rho_ueffdp2l+rho_ueffdp2a)*pseflag)'    
+fu0_dp_dn='(1+(rho_ueffrefdpc+rho_ueffrefdpl+rho_ueffrefdpx+rho_ueffrefdps+rho_ueffrefdpa)*pseflag)*(1+(rho_ueffrefdp2+rho_ueffrefdp2l+rho_ueffrefdp2a)*pseflag)'    
+fu0_dp='fu0_dp_nu/fu0_dp_dn'    
+fu0_enxy_nu='(1+(rho_ueffenx+rho_ueffeny+rho_ueffeny1+selmin(rho_ueffrex,rho_ueffenx)+selmin(rho_ueffrey,rho_ueffeny+rho_ueffeny1))*ceslflag)'    
+fu0_enxy_dn='(1+(rho_ueffrefenx+rho_ueffrefeny+rho_ueffrefeny1+rho_ueffrefrex+rho_ueffrefrey)*ceslflag)'    
+fu0_enxy='fu0_enxy_nu/fu0_enxy_dn'    
+fu0_odod_nu='(1+(rho_ueffsodx+rho_ueffsodx1+rho_ueffsodx3+rho_ueffsodx4+rho_ueffsodx5*dsodxflag+rho_ueffsody+rho_ueffsody1)*oseflag)'    
+fu0_odod_dn='(1+(rho_ueffrefsodx+rho_ueffrefsodx1+rho_ueffrefsodx3+rho_ueffrefsodx4+rho_ueffrefsody+rho_ueffrefsody1)*oseflag)'    
+fu0_odod='fu0_odod_nu/fu0_odod_dn'    
+fu0_spomt1_nu='max((1+rho_ueffspomt1*mbeflag*selmbet),mbe_clamp)'    
+fu0_spomt1_dn='max((1+rho_ueffrefspom1*mbeflag*selmbet),mbe_clamp)'    
+fu0_spomt1='fu0_spomt1_nu/fu0_spomt1_dn'    
+fu0_spomb1_nu='max((1+rho_ueffspomb1*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spomb1_dn='max((1+rho_ueffrefspom1*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spomb1='fu0_spomb1_nu/fu0_spomb1_dn'    
+fu0_spmt_nu='max((1+rho_ueffspmt*mbeflag*selmbet),mbe_clamp)'    
+fu0_spmt_dn='max((1+rho_ueffrefspm*mbeflag*selmbet),mbe_clamp)'    
+fu0_spmt='fu0_spmt_nu/fu0_spmt_dn'    
+fu0_spmb_nu='max((1+rho_ueffspmb*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spmb_dn='max((1+rho_ueffrefspm*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spmb='fu0_spmb_nu/fu0_spmb_dn'    
+fu0_mbe='fu0_spomt1*fu0_spomb1*fu0_spmt*fu0_spmb'    
+fu0_lod='max(1e-1,fu0_sa*fu0_dp*fu0_enxy*fu0_odod*fu0_mbe)'    
    
+fvsat_sa_nu='max((1+(kvsat*rho_ueff+kvsat1*rho_ueff1+kvsat2*rho_ueff2+kvsat3*rho_ueff3)*rllod*lodflag),lod_clamp)'    
+fvsat_sa_dn='max((1+(kvsat*rho_ueffref+kvsat1*rho_ueffref1+kvsat2*rho_ueffref2+kvsat3*rho_ueffref3)*rllod*lodflag),lod_clamp)'    
+fvsat_sa='fvsat_sa_nu/fvsat_sa_dn'    
+fvsat_dp_nu='(1+(kvsatdpc*rho_ueffdpc+kvsatdpl*rho_ueffdpl+kvsatdps*rho_ueffdps+kvsatdpx*rho_ueffdpx+kvsatdpa*rho_ueffdpa)*pseflag)*(1+(kvsatdp2*rho_ueffdp2+kvsatdp2l*rho_ueffdp2l+kvsatdp2a*rho_ueffdp2a)*pseflag)'    
+fvsat_dp_dn='(1+(kvsatdpc*rho_ueffrefdpc+kvsatdpl*rho_ueffrefdpl+kvsatdps*rho_ueffrefdps+kvsatdpx*rho_ueffrefdpx+kvsatdpa*rho_ueffrefdpa)*pseflag)*(1+(kvsatdp2*rho_ueffrefdp2+kvsatdp2l*rho_ueffrefdp2l+kvsatdp2a*rho_ueffrefdp2a)*pseflag)'    
+fvsat_dp='fvsat_dp_nu/fvsat_dp_dn'    
+fvsat_enxy_nu='(1+(kvsatenx*rho_ueffenx+kvsateny*rho_ueffeny+kvsateny1*rho_ueffeny1+selmin(kvsatrx*rho_ueffrex,kvsatenx*rho_ueffenx)+selmin(kvsatry*rho_ueffrey,kvsateny*rho_ueffeny+kvsateny1*rho_ueffeny1))*ceslflag)'    
+fvsat_enxy_dn='(1+(kvsatenx*rho_ueffrefenx+kvsateny*rho_ueffrefeny+kvsateny1*rho_ueffrefeny1+kvsatrx*rho_ueffrefrex+kvsatry*rho_ueffrefrey)*ceslflag)'    
+fvsat_enxy='fvsat_enxy_nu/fvsat_enxy_dn'    
+fvsat_odod_nu='(1+(kvsatodx*rho_ueffsodx+kvsatodx1*rho_ueffsodx1+kvsatodx3*rho_ueffsodx3+kvsatodx4*inv_sodx4+kvsatodx5*rho_ueffsodx5*dsodxflag+kvsatody*rho_ueffsody+kvsatody1*rho_ueffsody1)*oseflag)'    
+fvsat_odod_dn='(1+(kvsatodx*rho_ueffrefsodx+kvsatodx1*rho_ueffrefsodx1+kvsatodx3*rho_ueffrefsodx3+kvsatodx4*inv_sodx4ref+kvsatody*rho_ueffrefsody+kvsatody1*rho_ueffrefsody1)*oseflag)'    
+fvsat_odod='fvsat_odod_nu/fvsat_odod_dn'    
+fvsat_spomt1_nu='max((1+(kvsatspom1*rho_ueffspomt1)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spomt1_dn='max((1+(kvsatspom1*rho_ueffrefspom1)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spomt1='fvsat_spomt1_nu/fvsat_spomt1_dn'    
+fvsat_spomb1_nu='max((1+(kvsatspom1*rho_ueffspomb1)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spomb1_dn='max((1+(kvsatspom1*rho_ueffrefspom1)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spomb1='fvsat_spomb1_nu/fvsat_spomb1_dn'    
+fvsat_spmt_nu='max((1+(kvsatspm*rho_ueffspmt)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spmt_dn='max((1+(kvsatspm*rho_ueffrefspm)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spmt='fvsat_spmt_nu/fvsat_spmt_dn'    
+fvsat_spmb_nu='max((1+(kvsatspm*rho_ueffspmb)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spmb_dn='max((1+(kvsatspm*rho_ueffrefspm)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spmb='fvsat_spmb_nu/fvsat_spmb_dn'    
+fvsat_mbe='fvsat_spomt1*fvsat_spomb1*fvsat_spmt*fvsat_spmb'    
+fvsat_lod='max(1e-1,fvsat_sa*fvsat_dp*fvsat_enxy*fvsat_odod*fvsat_mbe+kvsatwe*(sca+web_mac*scb+wec_mac*scc)*wpeflag)'    
    
+da0_dp='kdpa_a0*dinv_sap+kdp2a_a0*dinv_sapb'    
+da0_enxy='kenx_a0*dinv_enx+keny_a0*dinv_eny+keny1_a0*dinv_eny1'    
+da0_lod='da0_dp*pseflag+da0_enxy*ceslflag'    
    
+deta0_sa='((steta0/pwr(kstress_vth0,lodeta0)+steta00*pwr(kstress_vth00,lodeta00))*(inv_sa+inv_sb-inv_saref-inv_sbref)+steta01*pwr(kstress_vth01,lodeta01)*(inv_sa1+inv_sb1-inv_saref1-inv_sbref1)+(steta02/pwr(kstress_vth02,lodeta02)+steta002*pwr(kstress_vth002,lodeta002))*(inv_sa2+inv_sb2-inv_saref2-inv_sbref2)+(steta03/pwr(kstress_vth03,lodeta03)+steta003*pwr(kstress_vth003,lodeta003))*(inv_sa3+inv_sb3-inv_saref3-inv_sbref3))*rllod'    
+deta0_dp='kdpc_eta0*dinv_spa+kdpl_eta0*dinv_spa1+kdpx_eta0*dinv_spa2+kdps_eta0*dinv_spa3+kdpa_eta0*dinv_sap+kdp2_eta0*dinv_spba+kdp2l_eta0*dinv_spba1+kdp2a_eta0*dinv_sapb'    
+deta0_enxy='kenx_eta0*dinv_enx+keny_eta0*dinv_eny+keny1_eta0*dinv_eny1+krex_eta0*dinv_rex+krey_eta0*dinv_rey'    
+deta0_odod='ksodx_eta0*dinv_sodx+ksodx1_eta0*(dinv_sodx1+dinv_sodx2)+ksodx3_eta0*dinv_sodx3+ksodx4_eta0*dinv_sodx4+ksody_eta0*dinv_sody+ksody1_eta0*dinv_sody1'    
+deta0_spomt1='(steta0spom1*pwr(kspom1_vth0,spom1eta0))*(inv_spomt1-inv_spom1ref)'    
+deta0_spomb1='(steta0spom1*pwr(kspom1_vth0,spom1eta0))*(inv_spomb1-inv_spom1ref)'    
+deta0_spmt='(steta0spm*pwr(kspm_vth0,spmeta0))*(inv_spmt-inv_spmref)'    
+deta0_spmb='(steta0spm*pwr(kspm_vth0,spmeta0))*(inv_spmb-inv_spmref)'    
+deta0_mbe='(deta0_spomt1+deta0_spmt)*selmbet+(deta0_spomb1+deta0_spmb)*selmbeb'    
+deta0_lod='deta0_sa*lodflag+deta0_dp*pseflag+deta0_enxy*ceslflag+deta0_odod*oseflag+deta0_mbe*mbeflag+keta0we*(sca+web_mac*scb+wec_mac*scc)*wpeflag'    
    
+dk2_lod='((stk2/pwr(kstress_vth0,lodk2)+stk20*pwr(kstress_vth00,lodk20))*(inv_sa+inv_sb-inv_saref-inv_sbref)+stk21*pwr(kstress_vth01,lodk21)*(inv_sa1+inv_sb1-inv_saref1-inv_sbref1)+(stk22/pwr(kstress_vth02,lodk22)+stk202*pwr(kstress_vth002,lodk202))*(inv_sa2+inv_sb2-inv_saref2-inv_sbref2)+(stk23/pwr(kstress_vth03,lodk23)+stk203*pwr(kstress_vth003,lodk203))*(inv_sa3+inv_sb3-inv_saref3-inv_sbref3))*lodflag*rllod'    
+selmin(par1_hv,par2_hv)='abs(par1_hv)<abs(par2_hv) ? par1_hv : (par2_hv*-1)'    
    
* ver_090b0809010v_020101010102    
    
.model nch_hv18.1 nmos	(	level      = 54                  lmin       = '6.3e-007-dxln_hv18_ms'    
+lmax       = 1.0801e-06          wmin       = '1.8e-006-dxwn_hv18_ms' wmax       = 4.5001e-06    
+version    = 4.5                 binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rbodymod   = 0                   rgeomod    = 1    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxn_hv18_ms+nctx'    
+toxm       = '3.36e-009+nctx'    
+dtox       = 2.95e-010           epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.196e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxln_hv18_ms'    xw         = '1.5e-08+dxwn_hv18_ms'  dlc        = 'ddlcn_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '0.4134974+dvthn_hv18_ms+dvths_lod'    
+lvth0      = '1.4037661e-008+dlvthn_hv18_ms'    
+wvth0      = '2.8591834e-009+dwvthn_hv18_ms'    
+pvth0      = '2.9736274e-015+dpvthn_hv18_ms'    
+k1         = 0.2969              k2         = '0.0028605039+dk2n_hv18_ms+dk2_lod'    
+lk2        = 1.1389323e-009      wk2        = -8.9864032e-010     pk2        = -5.9085976e-016    
+k3         = -5.9775             k3b        = 3.24                w0         = 1.548e-007    
+dvt0       = 9.1976              dvt1       = 0.17                dvt2       = -0.01899    
+dvt0w      = 0                   dvt1w      = 0                   dvt2w      = 0    
+dsub       = 0.33                minv       = -0.0686             voffl      = 0    
+dvtp0      = 4.386e-009          dvtp1      = 0.1                 lambda     = 0    
+vtl        = 0                   xn         = 3                   lpe0       = 6.5288e-007    
+lpeb       = 5.237e-007          vbm        = -3                  xj         = 7e-008    
+ngate      = 8.981e+020          ndep       = 2.07e+017           nsd        = 1e+020    
+phin       = 0.1                 cdsc       = 1.96465e-007        ud         = 0    
+ud1        = 0                   up         = 0.506867            lp         = 1.89837e-009    
+cdscb      = -2.8215986e-007     cdscd      = 2.19483e-007        cit        = '-0.0010456386+dcitn_hv18_ms'    
+lcit       = '1.51414e-009+dlcitn_hv18_ms'    
+wcit       = '7.3458427e-010+dwcitn_hv18_ms'    
+pcit       = '-1.2843097e-015+dpcitn_hv18_ms'    
+voff       = '-0.12923744+dvoffn_hv18_ms'    
+lvoff      = '1.0118656e-008+dlvoffn_hv18_ms'    
+wvoff      = '-1.5351317e-008+dwvoffn_hv18_ms'    
+pvoff      = '2.9736274e-015+dpvoffn_hv18_ms'    
+nfactor    = 0.501               eta0       = '0.07642682+deta0n_hv18_ms+deta0_lod'    
+leta0      = -1.7600221e-008     weta0      = -1.4246043e-008     peta0      = 4.245091e-016    
+etab       = -0.035    
+u0         = '((0.021267656+du0n_hv18_ms+0.000211544*ff_flagn_hv18_ms+0.000105772*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+lu0        = '((1.7302357e-009+dlu0n_hv18_ms-1.95928e-10*ff_flagn_hv18_ms-9.79639e-11*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+wu0        = '((-7.7384697e-010+dwu0n_hv18_ms+4.2e-16*ff_flagn_hv18_ms+2.1e-16*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+pu0        = '((7.166442e-016+dpu0n_hv18_ms+3e-22*ff_flagn_hv18_ms-3.5e-22*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+ua         = '-1.795221e-009+duan_hv18_ms'    
+lua        = -2.9238506e-017     wua        = -3.0442166e-016     pua        = 3.7973222e-022    
+ub         = '2.232308e-018+dubn_hv18_ms'    
+lub        = 1.5155122e-025      wub        = 2.890751e-025       pub        = -6.3338263e-031    
+uc         = 1.2745673e-010      luc        = -8.5047327e-019     wuc        = -4.0184824e-017    
+puc        = -2.0312849e-023     eu         = 1.67    
+vsat       = '(491929.05+dvsatn_hv18_ms+17669.6*ff_flagn_hv18_ms+13785.5*fs_flagn_hv18_ms)*fvsat_lod'    
+lvsat      = '(-0.093260267+dlvsatn_hv18_ms-0.0163652*ff_flagn_hv18_ms-0.0127679*fs_flagn_hv18_ms)*fvsat_lod'    
+wvsat      = '(-0.17575991+dwvsatn_hv18_ms-0.0224715*ff_flagn_hv18_ms-0.0192613*fs_flagn_hv18_ms)*fvsat_lod'    
+pvsat      = '(-3.2058701e-009+dpvsatn_hv18_ms+2.08128e-08*ff_flagn_hv18_ms+1.78395e-08*fs_flagn_hv18_ms)*fvsat_lod'    
+a0         = '1.8625889+da0n_hv18_ms+da0_lod'    
+la0        = '-1.1678961e-006+dla0n_hv18_ms'    
+wa0        = '1.3014529e-006+dwa0n_hv18_ms'    
+pa0        = '-6.7281293e-013+dpa0n_hv18_ms'    
+ags        = '-0.57556458+dagsn_hv18_ms-0.172046*ff_flagn_hv18_ms'    
+lags       = '1.3540523e-006+dlagsn_hv18_ms+8.19075e-08*ff_flagn_hv18_ms'    
+wags       = '2.1580358e-007+dwagsn_hv18_ms+3.12263e-07*ff_flagn_hv18_ms'    
+pags       = '-3.1211193e-013+dpagsn_hv18_ms-1.48662e-13*ff_flagn_hv18_ms'    
+a1         = 0                   a2         = 1                   b0         = 1.8037378e-009    
+b1         = 0                   keta       = -0.078463697        lketa      = 4.0145643e-009    
+wketa      = 4.179255e-008       pketa      = -1.7948815e-014     dwg        = 8.10878e-009    
+dwb        = 7.00117e-009        pclm       = 0.14543158          lpclm      = -4.2073275e-008    
+wpclm      = -6.3256419e-008     ppclm      = 5.8580504e-014      pdiblc1    = 0    
+pdiblc2    = 1.637e-005          pdiblcb    = 0                   drout      = 0.71026057    
+pvag       = 0.045008429         delta      = 0.013132722         pscbe1     = 1e+009    
+pscbe2     = 5.1919273e-007      fprout     = 10                  pdits      = 3.4633e-005    
+pditsd     = 0                   pditsl     = 0                   rsh        = 18.5    
+rsw        = 70                  rdw        = 1223                prwg       = 0    
+prwb       = 0                   wr         = 1                   alpha0     = 1.3e-006    
+alpha1     = 0.3                 beta0      = 29.2                agidl      = '(1e-012)*agidl_wl'    
+bgidl      = 4.3063056e+008      wbgidl     = -198.79796          cgidl      = 0.031242    
+egidl      = 5                   aigbacc    = 0.01238             bigbacc    = 0.006109    
+cigbacc    = 0.2809              nigbacc    = 4.05                aigbinv    = 0.35    
+bigbinv    = 0.03                cigbinv    = 0.006               eigbinv    = 1.1    
+nigbinv    = 1                   aigc       = 0.009898            bigc       = 0.001383    
+cigc       = 1.515e-005          aigsd      = 0.0086              bigsd      = 0.0004353    
+cigsd      = 3.925e-020          nigc       = 1                   poxedge    = 1    
+pigcd      = 1.672               ntox       = 1                   vfbsdoff   = 0.1    
+cgso       = 'cgson_hv18_ms'          cgdo       = 'cgdon_hv18_ms+cfdsn_hv18_ms'          cgbo       = 0    
+cgdl       = 'cgdln_hv18_ms'          cgsl       = 'cgsln_hv18_ms'          clc        = 1e-007    
+cle        = 0.6                 cf         = 'cfsn_hv18_ms'    
+ckappas    = 0.6    
+ckappad    = 0.6                 acde       = 0.305               moin       = 5.318    
+noff       = 2.4762              voffcv     = -0.071408           tvoff      = '0.00295206+dtvoffn_hv18_ms'    
+ltvoff     = -3.2604e-010        wtvoff     = 3.21098e-010        ptvoff     = -2.97363e-016    
+tvfbsdoff  = 0.01015             kt1        = '-0.23214638+dkt1n_hv18_ms'    
+lkt1       = -2.5794679e-008     wkt1       = 3.2109833e-009      pkt1       = -2.9736274e-015    
+kt1l       = 0                   kt2        = -0.030635756        lkt2       = -6.0614557e-009    
+wkt2       = 5.1219009e-009      pkt2       = 5.5636568e-015      ute        = -1.0166317    
+wute       = -2.5585752e-007     ua1        = '-0.0032450383+dua1n_hv18_ms'    
+lua1       = 2.5687397e-010      wua1       = -1.8995281e-009     pua1       = 1.8763588e-016    
+ub1        = '-0.002034403+dub1n_hv18_ms+0.000142199*ff_flagn_hv18_ms'    
+lub1       = '1.6142429e-010-1.31702e-10*ff_flagn_hv18_ms'    
+wub1       = '-3.8390051e-009-6.42044e-10*ff_flagn_hv18_ms'    
+pub1       = '6.1392187e-016+5.94649e-16*ff_flagn_hv18_ms'    
+uc1        = 0.00010867735       luc1       = -2.66528e-010       wuc1       = -4.3883162e-009    
+puc1       = -1.7324353e-016     prt        = 0.0017                   at         = '2e-006+datn_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 9.300000e-01    
+noia       = 1.750000e+42    
+noib       = 6.660000e+22    
+noic       = 3.070000e+06    
+lintnoi    = 5.100000e-08    
+jss        = 2.000000e-07    
+jsws       = 6.520000e-14    
+jswgs      = 7.690000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 8.300000e+00    
+xjbvs      = 1    
+jsd        = 9.500000e-07    
+jswd       = 2.870000e-13    
+jswgd      = 2.870000e-13    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.430000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(7e-009)*jtsswg_wl'    
+jtsswgd    = '(7e-009)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 18    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.69                xtsswgd    = 0.69    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 2    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1.1                 vtsswgd    = 1.1    
+pbs        = 5.910000e-01    
+cjs        = 'cjsn_hv18_ms'    
+mjs        = 2.750000e-01    
+pbsws      = 5.980000e-01    
+cjsws      = 'cjswsn_hv18_ms'    
+mjsws      = 8.000000e-02    
+pbswgs     = 5.000000e-01    
+cjswgs     = 'cjswgsn_hv18_ms'    
+mjswgs     = 3.500000e-01    
+pbd        = 4.980000e-01    
+cjd        = 'cjdn_hv18_ms'    
+mjd        = 2.540000e-01    
+pbswd      = 6.670000e-01    
+cjswd      = 'cjswdn_hv18_ms'    
+mjswd      = 3.140000e-01    
+pbswgd     = 6.670000e-01    
+cjswgd     = 'cjswgdn_hv18_ms'    
+mjswgd     = 3.140000e-01    
+tpb        = 2.300000e-03    
+tcj        = 1.700000e-03    
+tpbsw      = 1.800000e-03    
+tcjsw      = 1.150000e-03    
+tpbswg     = 1.800000e-03    
+tcjswg     = 1.150000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+web        = 1.479332e+02    
+wec        = -2.937276e+03    
+scref      = 1e-6    
+kvth0we    = 6.438330e-03    
+k2we       = 0.0027    
+ku0we      = 2.500000e-04    
+lat        = '0+dlatn_hv18_ms'       wat        = '0+dwatn_hv18_ms'       pat        = '0+dpatn_hv18_ms'    
+rbpb       = 50                  rbpd       = 50                  rbps       = 50    
+rbdb       = 50                  rbsb       = 50                  ngcon      = 1    
+lk2we    = -0.8e-10    
+wk2we    = 0.25e-10    
+pk2we    = 0.0e-18    
+lku0we   = 2.800000e-10    
+wku0we   = -1.000000e-10    
+pku0we   = -1.900000e-17    
+lkvth0we = -2.304370e-10    
+wkvth0we = -3.189880e-10    
+pkvth0we = 3.80992e-17    
+rshg     = 'rmainsh' )    
    
.model nch_hv18.2 nmos	(	level      = 54                  lmin       = '5.4e-007-dxln_hv18_ms'    
+lmax       = '6.3e-007-dxln_hv18_ms' wmin       = '1.8e-006-dxwn_hv18_ms' wmax       = 4.5001e-06    
+version    = 4.5                 binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rbodymod   = 0                   rgeomod    = 1    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxn_hv18_ms+nctx'    
+toxm       = '3.36e-009+nctx'    
+dtox       = 2.95e-010           epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.196e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxln_hv18_ms'    xw         = '1.5e-08+dxwn_hv18_ms'  dlc        = 'ddlcn_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '0.4301855+dvthn_hv18_ms+dvths_lod'    
+lvth0      = '6.0927943e-009+dlvthn_hv18_ms'    
+wvth0      = '-2.9954249e-008+dwvthn_hv18_ms'    
+pvth0      = '1.8595446e-014+dpvthn_hv18_ms'    
+k1         = 0.2969              k2         = '0.016588807+dk2n_hv18_ms+dk2_lod'    
+lk2        = -5.3968383e-009     wk2        = -7.0430029e-009     pk2        = 2.3343484e-015    
+k3         = -5.9775             k3b        = 3.24                w0         = 1.548e-007    
+dvt0       = 9.1976              dvt1       = 0.17                dvt2       = -0.01899    
+dvt0w      = 0                   dvt1w      = 0                   dvt2w      = 0    
+dsub       = 0.33                minv       = -0.0686             voffl      = 0    
+dvtp0      = 4.386e-009          dvtp1      = 0.1                 lambda     = 0    
+vtl        = 0                   xn         = 3                   lpe0       = 6.5288e-007    
+lpeb       = 5.237e-007          vbm        = -3                  xj         = 7e-008    
+ngate      = 8.981e+020          ndep       = 2.07e+017           nsd        = 1e+020    
+phin       = 0.1                 cdsc       = 1.96465e-007        ud         = 0    
+ud1        = 0                   up         = 0.506867            lp         = 1.89837e-009    
+cdscb      = -2.8215986e-007     cdscd      = 2.19483e-007        cit        = '0.0064088229+dcitn_hv18_ms'    
+lcit       = '-2.03478e-009+dlcitn_hv18_ms'    
+wcit       = '-1.2420622e-008+dwcitn_hv18_ms'    
+pcit       = '4.9786208e-015+dpcitn_hv18_ms'    
+voff       = '-0.11086702+dvoffn_hv18_ms'    
+lvoff      = '1.3728643e-009+dlvoffn_hv18_ms'    
+wvoff      = '3.914583e-009+dwvoffn_hv18_ms'    
+pvoff      = '-6.1984821e-015+dpvoffn_hv18_ms'    
+nfactor    = 0.501               eta0       = '0.1085804+deta0n_hv18_ms+deta0_lod'    
+leta0      = -3.2907897e-008     weta0      = -4.4601966e-008     peta0      = 1.4876357e-014    
+etab       = -0.035    
+u0         = '((0.023490157+du0n_hv18_ms+0.000805692*ff_flagn_hv18_ms+0.000905693*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+lu0        = '((6.7214753e-010+dlu0n_hv18_ms-4.78791e-10*ff_flagn_hv18_ms-4.7879e-10*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+wu0        = '((-1.3386984e-009+dwu0n_hv18_ms-2.60393e-09*ff_flagn_hv18_ms-2.60393e-09*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+pu0        = '((9.8555866e-016+dpu0n_hv18_ms+1.23968e-15*ff_flagn_hv18_ms+1.23968e-15*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+ua         = '-2.2082072e-009+duan_hv18_ms'    
+lua        = 1.6737598e-016      wua        = 1.4045893e-015      pua        = -4.3389375e-022    
+ub         = '2.7712413e-018+dubn_hv18_ms'    
+lub        = -1.0502412e-025     wub        = -2.0373543e-024     pub        = 4.7418388e-031    
+uc         = 2.128332e-010       luc        = -4.1496501e-017     wuc        = -1.2754879e-016    
+puc        = 2.1279389e-023      eu         = 1.67    
+vsat       = '(503399.86+dvsatn_hv18_ms-52643.7*ff_flagn_hv18_ms-31505.8*ss_flagn_hv18_ms-56109*fs_flagn_hv18_ms-31505.8*sf_flagn_hv18_ms)*fvsat_lod'    
+lvsat      = '(-0.098721287+dlvsatn_hv18_ms+0.0171093*ff_flagn_hv18_ms+0.0149992*ss_flagn_hv18_ms+0.0205075*fs_flagn_hv18_ms+0.0149992*sf_flagn_hv18_ms)*fvsat_lod'    
+wvsat      = '(-0.42268499+dwvsatn_hv18_ms+0.125402*ff_flagn_hv18_ms+0.0260392*ss_flagn_hv18_ms+0.115857*fs_flagn_hv18_ms+0.0260392*sf_flagn_hv18_ms)*fvsat_lod'    
+pvsat      = '(1.1435022e-007+dpvsatn_hv18_ms-4.95871e-08*ff_flagn_hv18_ms-1.23967e-08*ss_flagn_hv18_ms-4.64878e-08*fs_flagn_hv18_ms-1.23967e-08*sf_flagn_hv18_ms)*fvsat_lod'    
+a0         = '1.1312887+da0n_hv18_ms+da0_lod'    
+la0        = '-8.1973872e-007+dla0n_hv18_ms'    
+wa0        = '2.1116148e-006+dwa0n_hv18_ms'    
+pa0        = '-1.0585148e-012+dpa0n_hv18_ms'    
+ags        = '2.4814209+dagsn_hv18_ms'    
+lags       = '-1.0131738e-007+dlagsn_hv18_ms'    
+wags       = '-1.1662903e-006+dwagsn_hv18_ms'    
+pags       = '3.458753e-013+dpagsn_hv18_ms'    
+a1         = 0                   a2         = 1                   b0         = 1.8037378e-009    
+b1         = 0                   keta       = -0.11363527         lketa      = 2.0759046e-008    
+wketa      = -1.7026877e-008     pketa      = 1.0053938e-014      dwg        = 8.10878e-009    
+dwb        = 7.00117e-009        pclm       = -0.37048361         lpclm      = 2.0354363e-007    
+wpclm      = 4.4648042e-007      ppclm      = -1.8409501e-013     pdiblc1    = 0    
+pdiblc2    = 1.637e-005          pdiblcb    = 0                   drout      = 0.71026057    
+pvag       = 0.045008429         delta      = 0.013132722         pscbe1     = 1e+009    
+pscbe2     = 5.1919273e-007      fprout     = 10                  pdits      = 3.4633e-005    
+pditsd     = 0                   pditsl     = 0                   rsh        = 18.5    
+rsw        = 70                  rdw        = 1223                prwg       = 0    
+prwb       = 0                   wr         = 1                   alpha0     = 1.3e-006    
+alpha1     = 0.3                 beta0      = 29.2                agidl      = '(1e-012)*agidl_wl'    
+bgidl      = 4.3063056e+008      wbgidl     = -198.79796          cgidl      = 0.031242    
+egidl      = 5                   aigbacc    = 0.01238             bigbacc    = 0.006109    
+cigbacc    = 0.2809              nigbacc    = 4.05                aigbinv    = 0.35    
+bigbinv    = 0.03                cigbinv    = 0.006               eigbinv    = 1.1    
+nigbinv    = 1                   aigc       = 0.009898            bigc       = 0.001383    
+cigc       = 1.515e-005          aigsd      = 0.0086              bigsd      = 0.0004353    
+cigsd      = 3.925e-020          nigc       = 1                   poxedge    = 1    
+pigcd      = 1.672               ntox       = 1                   vfbsdoff   = 0.1    
+cgso       = 'cgson_hv18_ms'          cgdo       = 'cgdon_hv18_ms+cfdsn_hv18_ms'          cgbo       = 0    
+cgdl       = 'cgdln_hv18_ms'          cgsl       = 'cgsln_hv18_ms'          clc        = 1e-007    
+cle        = 0.6                 cf         = 'cfsn_hv18_ms'    
+ckappas    = 0.6    
+ckappad    = 0.6                 acde       = 0.305               moin       = 5.318    
+noff       = 2.4762              voffcv     = -0.071408           tvoff      = '0.00415615+dtvoffn_hv18_ms'    
+ltvoff     = -8.99283e-010       wtvoff     = -1.0847e-009        ptvoff     = 3.71909e-016    
+tvfbsdoff  = 0.01015             kt1        = '-0.28499318+dkt1n_hv18_ms'    
+lkt1       = -6.3537519e-010     wkt1       = 4.9044249e-008      pkt1       = -2.4793928e-014    
+kt1l       = 0                   kt2        = -0.043367767        wkt2       = 1.6808292e-008    
+ute        = -1.0176731          lute       = 4.9581957e-010      wute       = -7.024378e-007    
+pute       = 2.1260794e-013      ua1        = '-0.0035940814+dua1n_hv18_ms'    
+lua1       = 4.2304642e-010      wua1       = -4.0572886e-009     pua1       = 1.2149025e-015    
+ub1        = '-0.0029234672+dub1n_hv18_ms+0.000442276*ff_flagn_hv18_ms'    
+lub1       = '5.8468999e-010-2.74562e-10*ff_flagn_hv18_ms'    
+wub1       = '-6.5491639e-009-1.99692e-09*ff_flagn_hv18_ms'    
+pub1       = '1.9041743e-015+1.23968e-15*ff_flagn_hv18_ms'    
+uc1        = -0.0019597048       luc1       = 7.1818739e-010      wuc1       = -1.8148075e-009    
+puc1       = -1.3984396e-015     prt        = 0.0017                   at         = '2e-006+datn_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 9.300000e-01    
+noia       = 1.750000e+42    
+noib       = 6.660000e+22    
+noic       = 3.070000e+06    
+lintnoi    = 5.100000e-08    
+jss        = 2.000000e-07    
+jsws       = 6.520000e-14    
+jswgs      = 7.690000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 8.300000e+00    
+xjbvs      = 1    
+jsd        = 9.500000e-07    
+jswd       = 2.870000e-13    
+jswgd      = 2.870000e-13    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.430000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(7e-009)*jtsswg_wl'    
+jtsswgd    = '(7e-009)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 18    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.69                xtsswgd    = 0.69    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 2    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1.1                 vtsswgd    = 1.1    
+pbs        = 5.910000e-01    
+cjs        = 'cjsn_hv18_ms'    
+mjs        = 2.750000e-01    
+pbsws      = 5.980000e-01    
+cjsws      = 'cjswsn_hv18_ms'    
+mjsws      = 8.000000e-02    
+pbswgs     = 5.000000e-01    
+cjswgs     = 'cjswgsn_hv18_ms'    
+mjswgs     = 3.500000e-01    
+pbd        = 4.980000e-01    
+cjd        = 'cjdn_hv18_ms'    
+mjd        = 2.540000e-01    
+pbswd      = 6.670000e-01    
+cjswd      = 'cjswdn_hv18_ms'    
+mjswd      = 3.140000e-01    
+pbswgd     = 6.670000e-01    
+cjswgd     = 'cjswgdn_hv18_ms'    
+mjswgd     = 3.140000e-01    
+tpb        = 2.300000e-03    
+tcj        = 1.700000e-03    
+tpbsw      = 1.800000e-03    
+tcjsw      = 1.150000e-03    
+tpbswg     = 1.800000e-03    
+tcjswg     = 1.150000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+web        = 1.479332e+02    
+wec        = -2.937276e+03    
+scref      = 1e-6    
+kvth0we    = 6.438330e-03    
+k2we       = 0.0027    
+ku0we      = 2.500000e-04    
+lat        = '0+dlatn_hv18_ms'       wat        = '0+dwatn_hv18_ms'       pat        = '0+dpatn_hv18_ms'    
+rbpb       = 50                  rbpd       = 50                  rbps       = 50    
+rbdb       = 50                  rbsb       = 50                  ngcon      = 1    
+lk2we    = -0.8e-10    
+wk2we    = 0.25e-10    
+pk2we    = 0.0e-18    
+lku0we   = 2.800000e-10    
+wku0we   = -1.000000e-10    
+pku0we   = -1.900000e-17    
+lkvth0we = -2.304370e-10    
+wkvth0we = -3.189880e-10    
+pkvth0we = 3.80992e-17    
+rshg     = 'rmainsh' )    
    
.model nch_hv18.3 nmos	(	level      = 54                  lmin       = 4.95e-07    
+lmax       = '5.4e-007-dxln_hv18_ms' wmin       = '1.8e-006-dxwn_hv18_ms' wmax       = 4.5001e-06    
+version    = 4.5                 binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rbodymod   = 0                   rgeomod    = 1    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxn_hv18_ms+nctx'    
+toxm       = '3.36e-009+nctx'    
+dtox       = 2.95e-010           epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.196e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxln_hv18_ms'    xw         = '1.5e-08+dxwn_hv18_ms'  dlc        = 'ddlcn_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '0.43838711+dvthn_hv18_ms+dvths_lod'    
+lvth0      = '2.9263148e-009+dlvthn_hv18_ms'    
+wvth0      = '1.82105e-008+dwvthn_hv18_ms'    
+k1         = 0.2969              k2         = '0.017037025+dk2n_hv18_ms+dk2_lod'    
+lk2        = -5.5698863e-009     wk2        = -9.7437539e-009     pk2        = 3.3770543e-015    
+k3         = -5.9775             k3b        = 3.24                w0         = 1.548e-007    
+dvt0       = 9.1976              dvt1       = 0.17                dvt2       = -0.01899    
+dvt0w      = 0                   dvt1w      = 0                   dvt2w      = 0    
+dsub       = 0.33                minv       = -0.0686             voffl      = 0    
+dvtp0      = 4.386e-009          dvtp1      = 0.1                 lambda     = 0    
+vtl        = 0                   xn         = 3                   lpe0       = 6.5288e-007    
+lpeb       = 5.237e-007          vbm        = -3                  xj         = 7e-008    
+ngate      = 8.981e+020          ndep       = 2.07e+017           nsd        = 1e+020    
+phin       = 0.1                 cdsc       = 1.96465e-007        ud         = 0    
+ud1        = 0                   up         = 0.506867            lp         = 1.89837e-009    
+cdscb      = -2.8215986e-007     cdscd      = 2.19483e-007        cit        = '-0.0048858547+dcitn_hv18_ms'    
+lcit       = '2.3258691e-009+dlcitn_hv18_ms'    
+wcit       = '5.906069e-009+dwcitn_hv18_ms'    
+pcit       = '-2.096948e-015+dpcitn_hv18_ms'    
+voff       = '-0.093394205+dvoffn_hv18_ms'    
+lvoff      = '-5.3730391e-009+dlvoffn_hv18_ms'    
+wvoff      = '-2.3642625e-008+dwvoffn_hv18_ms'    
+pvoff      = '4.4408046e-015+dpvoffn_hv18_ms'    
+nfactor    = 0.501               eta0       = '0.061115896+deta0n_hv18_ms+deta0_lod'    
+leta0      = -1.4582802e-008     weta0      = 6.2943582e-008      peta0      = -2.6644828e-014    
+etab       = -0.035    
+u0         = '((0.019570573+du0n_hv18_ms-0.0027083*ff_flagn_hv18_ms-0.00152849*ss_flagn_hv18_ms-0.00185035*fs_flagn_hv18_ms+0.00151591*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+lu0        = '((2.1854207e-009+dlu0n_hv18_ms+8.77888e-10*ff_flagn_hv18_ms+5.90118e-10*ss_flagn_hv18_ms+5.85263e-10*fs_flagn_hv18_ms-5.85263e-10*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+wu0        = '((8.7365319e-009+dwu0n_hv18_ms+6.07002e-10*ff_flagn_hv18_ms+6.90127e-09*ss_flagn_hv18_ms+6.07012e-10*fs_flagn_hv18_ms-2e-15*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+pu0        = '((-2.9042862e-015+dpu0n_hv18_ms+5.4e-21*ff_flagn_hv18_ms-2.66444e-15*ss_flagn_hv18_ms-4.6e-21*fs_flagn_hv18_ms+4.6e-21*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+ua         = '-2.181509e-009+duan_hv18_ms'    
+lua        = 1.5706832e-016      wua        = 4.5097912e-016      pua        = -6.5723909e-023    
+ub         = '2.9103043e-018+dubn_hv18_ms'    
+lub        = -1.5871356e-025     wub        = -1.3281848e-025     pub        = -2.6111931e-031    
+uc         = 2.4463627e-010      luc        = -5.3775034e-017     wuc        = 3.3710881e-017    
+puc        = -4.0979745e-023     eu         = 1.67    
+vsat       = '(793323.31+dvsatn_hv18_ms-45973.7*ff_flagn_hv18_ms+70465.3*ss_flagn_hv18_ms-10382.6*fs_flagn_hv18_ms+70465.3*sf_flagn_hv18_ms)*fvsat_lod'    
+lvsat      = '(-0.21065493+dlvsatn_hv18_ms+0.0145345*ff_flagn_hv18_ms-0.0243698*ss_flagn_hv18_ms+0.00285349*fs_flagn_hv18_ms-0.0243698*sf_flagn_hv18_ms)*fvsat_lod'    
+wvsat      = '(-0.37393956+dwvsatn_hv18_ms-0.14106*ff_flagn_hv18_ms+0.0169334*ss_flagn_hv18_ms-0.108072*fs_flagn_hv18_ms+0.0169334*sf_flagn_hv18_ms)*fvsat_lod'    
+pvsat      = '(9.553059e-008+dpvsatn_hv18_ms+5.32889e-08*ff_flagn_hv18_ms-8.88146e-09*ss_flagn_hv18_ms+3.99666e-08*fs_flagn_hv18_ms-8.88146e-09*sf_flagn_hv18_ms)*fvsat_lod'    
+a0         = '-0.82187027+da0n_hv18_ms+da0_lod'    
+la0        = '-6.5663095e-008+dla0n_hv18_ms'    
+wa0        = '-7.8882182e-007+dwa0n_hv18_ms'    
+pa0        = '6.1285769e-014+dpa0n_hv18_ms'    
+ags        = '-0.53142359+dagsn_hv18_ms'    
+lags       = '1.0618816e-006+dlagsn_hv18_ms'    
+wags       = '7.0726369e-006+dwagsn_hv18_ms'    
+pags       = '-2.8350097e-012+dpagsn_hv18_ms'    
+a1         = 0                   a2         = 1                   b0         = 1.8037378e-009    
+b1         = 0                   keta       = -0.28868435         lketa      = 8.8341998e-008    
+wketa      = 6.7633113e-007      pketa      = -2.5763772e-013     dwg        = 8.10878e-009    
+dwb        = 7.00117e-009        pclm       = -0.11908938         lpclm      = 1.0648534e-007    
+wpclm      = -1.18058e-006       ppclm      = 4.4408046e-013      pdiblc1    = 0    
+pdiblc2    = 1.637e-005          pdiblcb    = 0                   drout      = 0.71026057    
+pvag       = 0.045008429         delta      = 0.013132722         pscbe1     = 1e+009    
+pscbe2     = 5.1919273e-007      fprout     = 10                  pdits      = 3.4633e-005    
+pditsd     = 0                   pditsl     = 0                   rsh        = 18.5    
+rsw        = 70                  rdw        = 1223                prwg       = 0    
+prwb       = 0                   wr         = 1                   alpha0     = 1.3e-006    
+alpha1     = 0.3                 beta0      = 29.2                agidl      = '(1e-012)*agidl_wl'    
+bgidl      = 4.3063056e+008      wbgidl     = -198.79796          cgidl      = 0.031242    
+egidl      = 5                   aigbacc    = 0.01238             bigbacc    = 0.006109    
+cigbacc    = 0.2809              nigbacc    = 4.05                aigbinv    = 0.35    
+bigbinv    = 0.03                cigbinv    = 0.006               eigbinv    = 1.1    
+nigbinv    = 1                   aigc       = 0.009898            bigc       = 0.001383    
+cigc       = 1.515e-005          aigsd      = 0.0086              bigsd      = 0.0004353    
+cigsd      = 3.925e-020          nigc       = 1                   poxedge    = 1    
+pigcd      = 1.672               ntox       = 1                   vfbsdoff   = 0.1    
+cgso       = 'cgson_hv18_ms'          cgdo       = 'cgdon_hv18_ms+cfdsn_hv18_ms'          cgbo       = 0    
+cgdl       = 'cgdln_hv18_ms'          cgsl       = 'cgsln_hv18_ms'          clc        = 1e-007    
+cle        = 0.6                 cf         = 'cfsn_hv18_ms'    
+ckappas    = 0.6    
+ckappad    = 0.6                 acde       = 0.305               moin       = 5.318    
+noff       = 2.4762              voffcv     = -0.071408           tvoff      = '0.00885229+dtvoffn_hv18_ms'    
+ltvoff     = -2.71237e-009       wtvoff     = -1.04159e-009       ptvoff     = 3.55264e-016    
+tvfbsdoff  = 0.01015             kt1        = '-0.11976234+dkt1n_hv18_ms'    
+lkt1       = -6.4427698e-008     wkt1       = -8.4189165e-008     pkt1       = 2.6644828e-014    
+kt1l       = 0                   kt2        = -0.031950766        lkt2       = -4.4078755e-009    
+wkt2       = 1.4231778e-008      pkt2       = 9.9474024e-016      ute        = -1.4511059    
+lute       = 1.6783553e-007      wute       = 6.2350027e-007      pute       = -2.9931023e-013    
+ua1        = '-0.0029783002+dua1n_hv18_ms'    
+lua1       = 1.8530563e-010      wua1       = 3.8813295e-009      pua1       = -1.8500392e-015    
+ub1        = '-0.0035908695+dub1n_hv18_ms-0.000778373*ff_flagn_hv18_ms'    
+lub1       = '8.4236064e-010+1.96706e-10*ff_flagn_hv18_ms'    
+wub1       = '5.9341643e-009+3.51443e-09*ff_flagn_hv18_ms'    
+pub1       = '-2.9153891e-015-8.88147e-16*ff_flagn_hv18_ms'    
+uc1        = -0.014315379        luc1       = 5.488466e-009       wuc1       = 3.1370375e-008    
+puc1       = -1.4210575e-014     prt        = 0.0017    
+at         = '-0.0030146631+datn_hv18_ms-0.000662344*monte_flagn_hv18_ms'    
+lat        = '1.1646733e-009+dlatn_hv18_ms+2.55718e-10*monte_flagn_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 9.300000e-01    
+noia       = 1.750000e+42    
+noib       = 6.660000e+22    
+noic       = 3.070000e+06    
+lintnoi    = 5.100000e-08    
+jss        = 2.000000e-07    
+jsws       = 6.520000e-14    
+jswgs      = 7.690000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 8.300000e+00    
+xjbvs      = 1    
+jsd        = 9.500000e-07    
+jswd       = 2.870000e-13    
+jswgd      = 2.870000e-13    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.430000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(7e-009)*jtsswg_wl'    
+jtsswgd    = '(7e-009)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 18    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.69                xtsswgd    = 0.69    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 2    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1.1                 vtsswgd    = 1.1    
+pbs        = 5.910000e-01    
+cjs        = 'cjsn_hv18_ms'    
+mjs        = 2.750000e-01    
+pbsws      = 5.980000e-01    
+cjsws      = 'cjswsn_hv18_ms'    
+mjsws      = 8.000000e-02    
+pbswgs     = 5.000000e-01    
+cjswgs     = 'cjswgsn_hv18_ms'    
+mjswgs     = 3.500000e-01    
+pbd        = 4.980000e-01    
+cjd        = 'cjdn_hv18_ms'    
+mjd        = 2.540000e-01    
+pbswd      = 6.670000e-01    
+cjswd      = 'cjswdn_hv18_ms'    
+mjswd      = 3.140000e-01    
+pbswgd     = 6.670000e-01    
+cjswgd     = 'cjswgdn_hv18_ms'    
+mjswgd     = 3.140000e-01    
+tpb        = 2.300000e-03    
+tcj        = 1.700000e-03    
+tpbsw      = 1.800000e-03    
+tcjsw      = 1.150000e-03    
+tpbswg     = 1.800000e-03    
+tcjswg     = 1.150000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+web        = 1.479332e+02    
+wec        = -2.937276e+03    
+scref      = 1e-6    
+kvth0we    = 6.438330e-03    
+k2we       = 0.0027    
+ku0we      = 2.500000e-04    
+pvth0      = '0+dpvthn_hv18_ms'    
+wat        = '0+dwatn_hv18_ms+2.99055e-09*monte_flagn_hv18_ms'    
+pat        = '0+dpatn_hv18_ms-1.15459e-15*monte_flagn_hv18_ms'    
+rbpb       = 50                  rbpd       = 50                  rbps       = 50    
+rbdb       = 50                  rbsb       = 50                  ngcon      = 1    
+lk2we    = -0.8e-10    
+wk2we    = 0.25e-10    
+pk2we    = 0.0e-18    
+lku0we   = 2.800000e-10    
+wku0we   = -1.000000e-10    
+pku0we   = -1.900000e-17    
+lkvth0we = -2.304370e-10    
+wkvth0we = -3.189880e-10    
+pkvth0we = 3.80992e-17    
+rshg     = 'rmainsh' )    
    
.model nch_hv18.4 nmos	(	level      = 54                  lmin       = '6.3e-007-dxln_hv18_ms'    
+lmax       = 1.0801e-06          wmin       = 9e-07               wmax       = '1.8e-006-dxwn_hv18_ms'    
+version    = 4.5                 binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rbodymod   = 0                   rgeomod    = 1    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxn_hv18_ms+nctx'    
+toxm       = '3.36e-009+nctx'    
+dtox       = 2.95e-010           epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.196e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxln_hv18_ms'    xw         = '1.5e-08+dxwn_hv18_ms'  dlc        = 'ddlcn_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '0.41303938+dvthn_hv18_ms+dvths_lod'    
+lvth0      = '1.5676024e-008+dlvthn_hv18_ms'    
+wvth0      = '3.6905e-009+dwvthn_hv18_ms'    
+pvth0      = '1.0886136e-027+dpvthn_hv18_ms'    
+k1         = 0.2969              k2         = '0.001937579+dk2n_hv18_ms+dk2_lod'    
+lk2        = 1.5368431e-009      wk2        = 7.764685e-010       pk2        = -1.3130679e-015    
+k3         = -5.9775             k3b        = 3.24                w0         = 1.548e-007    
+dvt0       = 9.1976              dvt1       = 0.17                dvt2       = -0.01899    
+dvt0w      = 0                   dvt1w      = 0                   dvt2w      = 0    
+dsub       = 0.33                minv       = -0.0686             voffl      = 0    
+dvtp0      = 4.386e-009          dvtp1      = 0.1                 lambda     = 0    
+vtl        = 0                   xn         = 3                   lpe0       = 6.5288e-007    
+lpeb       = 5.237e-007          vbm        = -3                  xj         = 7e-008    
+ngate      = 8.981e+020          ndep       = 2.07e+017           nsd        = 1e+020    
+phin       = 0.1                 cdsc       = 1.96465e-007        ud         = 0    
+ud1        = 0                   up         = 0.506867            lp         = 1.89837e-009    
+cdscb      = -2.8215986e-007     cdscd      = 2.19483e-007        cit        = '-0.0016333395+dcitn_hv18_ms'    
+lcit       = '1.1819144e-009+dlcitn_hv18_ms'    
+wcit       = '1.8012613e-009+dwcitn_hv18_ms'    
+pcit       = '-6.8132008e-016+dpcitn_hv18_ms'    
+voff       = '-0.14307341+dvoffn_hv18_ms'    
+lvoff      = '1.6737421e-008+dlvoffn_hv18_ms'    
+wvoff      = '9.7609624e-009+dwvoffn_hv18_ms'    
+pvoff      = '-9.0394321e-015+dpvoffn_hv18_ms'    
+nfactor    = 0.501               eta0       = '0.067809956+deta0n_hv18_ms+deta0_lod'    
+leta0      = -1.2112248e-008     weta0      = 1.3935652e-009      peta0      = -9.5361634e-015    
+etab       = -0.035    
+u0         = '((0.020992952+du0n_hv18_ms+0.000104009*ff_flagn_hv18_ms+0.000105772*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+lu0        = '((1.9846336e-009+dlu0n_hv18_ms-9.63309e-11*ff_flagn_hv18_ms-9.79643e-11*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+wu0        = '((-2.7525914e-010+dwu0n_hv18_ms+1.95176e-10*ff_flagn_hv18_ms-1.2e-16*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+pu0        = '((2.5491198e-016+dpu0n_hv18_ms-1.80768e-16*ff_flagn_hv18_ms+1e-23*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+ua         = '-1.9558956e-009+duan_hv18_ms'    
+lua        = 1.1921943e-016      wua        = -1.2797342e-017     pua        = 1.1028107e-022    
+ub         = '2.3094929e-018+dubn_hv18_ms'    
+lub        = -3.3465045e-026     wub        = 1.4898453e-025      pub        = -2.9757811e-031    
+uc         = 1.00694e-010        luc        = 2.9200023e-018      wuc        = 8.3895221e-018    
+puc        = -2.7156262e-023     eu         = 1.67    
+vsat       = '(421481.35+dvsatn_hv18_ms+449.483*ff_flagn_hv18_ms+3173.16*fs_flagn_hv18_ms)*fvsat_lod'    
+lvsat      = '(-0.089074607+dlvsatn_hv18_ms-0.000416344*ff_flagn_hv18_ms-0.00293892*fs_flagn_hv18_ms)*fvsat_lod'    
+wvsat      = '(-0.047897327+dwvsatn_hv18_ms+0.00878292*ff_flagn_hv18_ms-3.7e-09*fs_flagn_hv18_ms)*fvsat_lod'    
+pvsat      = '(-1.0802843e-008+dpvsatn_hv18_ms-8.13456e-09*ff_flagn_hv18_ms+2e-16*fs_flagn_hv18_ms)*fvsat_lod'    
+a0         = '2.5331868+da0n_hv18_ms+da0_lod'    
+la0        = '-1.4350493e-006+dla0n_hv18_ms'    
+wa0        = '8.4317739e-008+dwa0n_hv18_ms'    
+pa0        = '-1.8792979e-013+dpa0n_hv18_ms'    
+ags        = '-0.97928561+dagsn_hv18_ms+0.0313802*ff_flagn_hv18_ms+0.104601*fs_flagn_hv18_ms'    
+lags       = '1.5999655e-006+dlagsn_hv18_ms-1.49395e-08*ff_flagn_hv18_ms-4.97983e-08*fs_flagn_hv18_ms'    
+wags       = '9.4855725e-007+dwagsn_hv18_ms-5.69551e-08*ff_flagn_hv18_ms-1.8985e-07*fs_flagn_hv18_ms'    
+pags       = '-7.5844451e-013+dpagsn_hv18_ms+2.71152e-14*ff_flagn_hv18_ms+9.0384e-14*fs_flagn_hv18_ms'    
+a1         = 0                   a2         = 1                   b0         = 1.8037378e-009    
+b1         = 0                   keta       = -0.066500167        lketa      = 3.8242476e-009    
+wketa      = 2.0078743e-008      pketa      = -1.760339e-014      dwg        = 8.10878e-009    
+dwb        = 7.00117e-009        pclm       = 0.14225799          lpclm      = -2.9719128e-008    
+wpclm      = -5.749635e-008      ppclm      = 3.6157728e-014      pdiblc1    = 0    
+pdiblc2    = 1.637e-005          pdiblcb    = 0                   drout      = 0.71026057    
+pvag       = 0.045008429         delta      = 0.013132722         pscbe1     = 1e+009    
+pscbe2     = 5.1919273e-007      fprout     = 10                  pdits      = 3.4633e-005    
+pditsd     = 0                   pditsl     = 0                   rsh        = 18.5    
+rsw        = 70                  rdw        = 1223                prwg       = 0    
+prwb       = 0                   wr         = 1                   alpha0     = 1.3e-006    
+alpha1     = 0.3                 beta0      = 29.2                agidl      = '(1e-012)*agidl_wl'    
+bgidl      = 3.4259233e+008      wbgidl     = -39.008585          cgidl      = 0.031242    
+egidl      = 5                   aigbacc    = 0.01238             bigbacc    = 0.006109    
+cigbacc    = 0.2809              nigbacc    = 4.05                aigbinv    = 0.35    
+bigbinv    = 0.03                cigbinv    = 0.006               eigbinv    = 1.1    
+nigbinv    = 1                   aigc       = 0.009898            bigc       = 0.001383    
+cigc       = 1.515e-005          aigsd      = 0.0086              bigsd      = 0.0004353    
+cigsd      = 3.925e-020          nigc       = 1                   poxedge    = 1    
+pigcd      = 1.672               ntox       = 1                   vfbsdoff   = 0.1    
+cgso       = 'cgson_hv18_ms'          cgdo       = 'cgdon_hv18_ms+cfdsn_hv18_ms'          cgbo       = 0    
+cgdl       = 'cgdln_hv18_ms'          cgsl       = 'cgsln_hv18_ms'          clc        = 1e-007    
+cle        = 0.6                 cf         = 'cfsn_hv18_ms'    
+ckappas    = 0.6    
+ckappad    = 0.6                 acde       = 0.305               moin       = 5.318    
+noff       = 2.4762              voffcv     = -0.071408           tvoff      = '0.00312898+dtvoffn_hv18_ms'    
+ltvoff     = -4.89876e-010       tvfbsdoff  = 0.01015             kt1        = '-0.22177254+dkt1n_hv18_ms'    
+lkt1       = -3.5401687e-008     wkt1       = -1.561754e-008      pkt1       = 1.4463091e-014    
+kt1l       = 0                   kt2        = -0.02856733         lkt2       = -4.9862492e-009    
+wkt2       = 1.3677082e-009      pkt2       = 3.6121571e-015      ute        = -1.0637617    
+wute       = -1.7031658e-007     ua1        = '-0.0036738526+dua1n_hv18_ms'    
+lua1       = 2.6692185e-010      wua1       = -1.1212301e-009     pua1       = 1.6939897e-016    
+ub1        = '-0.0032184141+dub1n_hv18_ms-0.000426614*ff_flagn_hv18_ms'    
+lub1       = '5.223839e-010+3.95121e-10*ff_flagn_hv18_ms'    
+wub1       = '-1.690025e-009+3.90352e-10*ff_flagn_hv18_ms'    
+pub1       = '-4.121981e-017-3.61536e-16*ff_flagn_hv18_ms'    
+uc1        = -0.0022152408       luc1       = 9.633462e-010       wuc1       = -1.7040481e-010    
+puc1       = -2.4054652e-015     prt        = 0.0017                   at         = '2e-006+datn_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 9.300000e-01    
+noia       = 1.750000e+42    
+noib       = 6.660000e+22    
+noic       = 3.070000e+06    
+lintnoi    = 5.100000e-08    
+jss        = 2.000000e-07    
+jsws       = 6.520000e-14    
+jswgs      = 7.690000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 8.300000e+00    
+xjbvs      = 1    
+jsd        = 9.500000e-07    
+jswd       = 2.870000e-13    
+jswgd      = 2.870000e-13    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.430000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(7e-009)*jtsswg_wl'    
+jtsswgd    = '(7e-009)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 18    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.69                xtsswgd    = 0.69    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 2    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1.1                 vtsswgd    = 1.1    
+pbs        = 5.910000e-01    
+cjs        = 'cjsn_hv18_ms'    
+mjs        = 2.750000e-01    
+pbsws      = 5.980000e-01    
+cjsws      = 'cjswsn_hv18_ms'    
+mjsws      = 8.000000e-02    
+pbswgs     = 5.000000e-01    
+cjswgs     = 'cjswgsn_hv18_ms'    
+mjswgs     = 3.500000e-01    
+pbd        = 4.980000e-01    
+cjd        = 'cjdn_hv18_ms'    
+mjd        = 2.540000e-01    
+pbswd      = 6.670000e-01    
+cjswd      = 'cjswdn_hv18_ms'    
+mjswd      = 3.140000e-01    
+pbswgd     = 6.670000e-01    
+cjswgd     = 'cjswgdn_hv18_ms'    
+mjswgd     = 3.140000e-01    
+tpb        = 2.300000e-03    
+tcj        = 1.700000e-03    
+tpbsw      = 1.800000e-03    
+tcjsw      = 1.150000e-03    
+tpbswg     = 1.800000e-03    
+tcjswg     = 1.150000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+web        = 1.479332e+02    
+wec        = -2.937276e+03    
+scref      = 1e-6    
+kvth0we    = 6.438330e-03    
+k2we       = 0.0027    
+ku0we      = 2.500000e-04    
+lat        = '0+dlatn_hv18_ms'       wat        = '0+dwatn_hv18_ms'       pat        = '0+dpatn_hv18_ms'    
+rbpb       = 50                  rbpd       = 50                  rbps       = 50    
+rbdb       = 50                  rbsb       = 50                  ngcon      = 1    
+lk2we    = -0.8e-10    
+wk2we    = 0.25e-10    
+pk2we    = 0.0e-18    
+lku0we   = 2.800000e-10    
+wku0we   = -1.000000e-10    
+pku0we   = -1.900000e-17    
+lkvth0we = -2.304370e-10    
+wkvth0we = -3.189880e-10    
+pkvth0we = 3.80992e-17    
+rshg     = 'rmainsh' )    
    
.model nch_hv18.5 nmos	(	level      = 54                  lmin       = '5.4e-007-dxln_hv18_ms'    
+lmax       = '6.3e-007-dxln_hv18_ms' wmin       = 9e-07               wmax       = '1.8e-006-dxwn_hv18_ms'    
+version    = 4.5                 binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rbodymod   = 0                   rgeomod    = 1    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxn_hv18_ms+nctx'    
+toxm       = '3.36e-009+nctx'    
+dtox       = 2.95e-010           epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.196e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxln_hv18_ms'    xw         = '1.5e-08+dxwn_hv18_ms'  dlc        = 'ddlcn_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '0.43345482+dvthn_hv18_ms+dvths_lod'    
+lvth0      = '5.9566424e-009+dlvthn_hv18_ms'    
+wvth0      = '-3.5888062e-008+dwvthn_hv18_ms'    
+pvth0      = '1.8842562e-014+dpvthn_hv18_ms'    
+k1         = 0.2969              k2         = '0.018217261+dk2n_hv18_ms+dk2_lod'    
+lk2        = -6.2135882e-009     wk2        = -9.9986475e-009     pk2        = 3.8167493e-015    
+k3         = -5.9775             k3b        = 3.24                w0         = 1.548e-007    
+dvt0       = 9.1976              dvt1       = 0.17                dvt2       = -0.01899    
+dvt0w      = 0                   dvt1w      = 0                   dvt2w      = 0    
+dsub       = 0.33                minv       = -0.0686             voffl      = 0    
+dvtp0      = 4.386e-009          dvtp1      = 0.1                 lambda     = 0    
+vtl        = 0                   xn         = 3                   lpe0       = 6.5288e-007    
+lpeb       = 5.237e-007          vbm        = -3                  xj         = 7e-008    
+ngate      = 8.981e+020          ndep       = 2.07e+017           nsd        = 1e+020    
+phin       = 0.1                 cdsc       = 1.96465e-007        ud         = 0    
+ud1        = 0                   up         = 0.506867            lp         = 1.89837e-009    
+cdscb      = -2.8215986e-007     cdscd      = 2.19483e-007        cit        = '-0.00040729074+dcitn_hv18_ms'    
+lcit       = '5.9821709e-010+dlcitn_hv18_ms'    
+wcit       = '-4.937561e-011+dwcitn_hv18_ms'    
+pcit       = '1.9973116e-016+dpcitn_hv18_ms'    
+voff       = '-0.10798816+dvoffn_hv18_ms'    
+lvoff      = '3.4037957e-011+dlvoffn_hv18_ms'    
+wvoff      = '-1.3105376e-009+dwvoffn_hv18_ms'    
+pvoff      = '-3.7685124e-015+dpvoffn_hv18_ms'    
+nfactor    = 0.501               eta0       = '0.094710772+deta0n_hv18_ms+deta0_lod'    
+leta0      = -2.4919188e-008     weta0      = -1.9428596e-008     peta0      = 3.7685124e-016    
+etab       = -0.035    
+u0         = '((0.022866547+du0n_hv18_ms-0.000527303*ff_flagn_hv18_ms-0.000528976*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+lu0        = '((1.0926525e-009+dlu0n_hv18_ms+2.04228e-10*ff_flagn_hv18_ms+2.04227e-10*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+wu0        = '((-2.0684678e-010+dwu0n_hv18_ms-1.84528e-10*ff_flagn_hv18_ms-2.4e-16*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+pu0        = '((2.2234223e-016+dpu0n_hv18_ms+5.2e-22*ff_flagn_hv18_ms+2.4e-22*fs_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+ua         = '-1.5078037e-009+duan_hv18_ms'    
+lua        = -9.4108143e-017     wua        = 1.3335696e-016      pua        = 4.0699934e-023    
+ub         = '1.8294762e-018+dubn_hv18_ms'    
+lub        = 1.9506132e-025      wub        = -3.2805068e-025     pub        = -7.0471182e-032    
+uc         = 1.5021346e-010      luc        = -2.0655219e-017     wuc        = -1.3893968e-017    
+puc        = -1.6547538e-023     eu         = 1.67    
+vsat       = '(303189.03+dvsatn_hv18_ms+46755.3*ff_flagn_hv18_ms-17159.1*ss_flagn_hv18_ms+7288.27*fs_flagn_hv18_ms-17159.1*sf_flagn_hv18_ms)*fvsat_lod'    
+lvsat      = '(-0.032757998+dlvsatn_hv18_ms-0.0224616*ff_flagn_hv18_ms+0.00816914*ss_flagn_hv18_ms-0.00489803*fs_flagn_hv18_ms+0.00816914*sf_flagn_hv18_ms)*fvsat_lod'    
+wvsat      = '(-0.059302339+dwvsatn_hv18_ms-0.0550059*ff_flagn_hv18_ms+5e-08*ss_flagn_hv18_ms+0.00079159*fs_flagn_hv18_ms+5e-08*sf_flagn_hv18_ms)*fvsat_lod'    
+pvsat      = '(-5.3731453e-009+dpvsatn_hv18_ms+2.22342e-08*ff_flagn_hv18_ms-5e-14*ss_flagn_hv18_ms-3.76769e-10*fs_flagn_hv18_ms-5e-14*sf_flagn_hv18_ms)*fvsat_lod'    
+a0         = '2.2438887+da0n_hv18_ms+da0_lod'    
+la0        = '-1.2973203e-006+dla0n_hv18_ms'    
+wa0        = '9.2245884e-008+dwa0n_hv18_ms'    
+pa0        = '-1.9170423e-013+dpa0n_hv18_ms'    
+ags        = '2.10368+dagsn_hv18_ms' lags       = '1.3222725e-007+dlagsn_hv18_ms'    
+wags       = '-4.8069058e-007+dwagsn_hv18_ms'    
+pags       = '-7.8008206e-014+dpagsn_hv18_ms'    
+a1         = 0                   a2         = 1                   b0         = 1.8037378e-009    
+b1         = 0                   keta       = -0.20001647         lketa      = 6.7388687e-008    
+wketa      = 1.39755e-007        pketa      = -7.457886e-014      dwg        = 8.10878e-009    
+dwb        = 7.00117e-009        pclm       = 0.039795407         lpclm      = 1.9061256e-008    
+wpclm      = -2.98176e-007       ppclm      = 1.5074049e-013      pdiblc1    = 0    
+pdiblc2    = 1.637e-005          pdiblcb    = 0                   drout      = 0.71026057    
+pvag       = 0.045008429         delta      = 0.013132722         pscbe1     = 1e+009    
+pscbe2     = 5.1919273e-007      fprout     = 10                  pdits      = 3.4633e-005    
+pditsd     = 0                   pditsl     = 0                   rsh        = 18.5    
+rsw        = 70                  rdw        = 1223                prwg       = 0    
+prwb       = 0                   wr         = 1                   alpha0     = 1.3e-006    
+alpha1     = 0.3                 beta0      = 29.2                agidl      = '(1e-012)*agidl_wl'    
+bgidl      = 3.4259233e+008      wbgidl     = -39.008585          cgidl      = 0.031242    
+egidl      = 5                   aigbacc    = 0.01238             bigbacc    = 0.006109    
+cigbacc    = 0.2809              nigbacc    = 4.05                aigbinv    = 0.35    
+bigbinv    = 0.03                cigbinv    = 0.006               eigbinv    = 1.1    
+nigbinv    = 1                   aigc       = 0.009898            bigc       = 0.001383    
+cigc       = 1.515e-005          aigsd      = 0.0086              bigsd      = 0.0004353    
+cigsd      = 3.925e-020          nigc       = 1                   poxedge    = 1    
+pigcd      = 1.672               ntox       = 1                   vfbsdoff   = 0.1    
+cgso       = 'cgson_hv18_ms'          cgdo       = 'cgdon_hv18_ms+cfdsn_hv18_ms'          cgbo       = 0    
+cgdl       = 'cgdln_hv18_ms'          cgsl       = 'cgsln_hv18_ms'          clc        = 1e-007    
+cle        = 0.6                 cf         = 'cfsn_hv18_ms'    
+ckappas    = 0.6    
+ckappad    = 0.6                 acde       = 0.305               moin       = 5.318    
+noff       = 2.4762              voffcv     = -0.071408           tvoff      = '0.00286072+dtvoffn_hv18_ms'    
+ltvoff     = -3.62164e-010       wtvoff     = 1.26651e-009        ptvoff     = -6.02962e-016    
+tvfbsdoff  = 0.01015             kt1        = '-0.32280145+dkt1n_hv18_ms'    
+lkt1       = 1.2696158e-008      wkt1       = 1.1766626e-007      pkt1       = -4.8990661e-014    
+kt1l       = 0                   kt2        = -0.039040883        wkt2       = 8.9549983e-009    
+ute        = -1.5620623          lute       = 2.3723094e-007      wute       = 2.8562846e-007    
+pute       = -2.1706631e-013     ua1        = '-0.0077406343+dua1n_hv18_ms'    
+lua1       = 2.2030353e-009      wua1       = 3.4687049e-009      pua1       = -2.0157773e-015    
+ub1        = '-0.008574902+dub1n_hv18_ms-0.00132688*ff_flagn_hv18_ms'    
+lub1       = '3.0725006e-009+8.23718e-10*ff_flagn_hv18_ms'    
+wub1       = '3.7081901e-009+1.2141e-09*ff_flagn_hv18_ms'    
+pub1       = '-2.611202e-015-7.53703e-16*ff_flagn_hv18_ms'    
+uc1        = -0.021776561        luc1       = 1.02761e-008        wuc1       = 3.4152787e-008    
+puc1       = -1.874605e-014      prt        = 0.0017                   at         = '2e-006+datn_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 9.300000e-01    
+noia       = 1.750000e+42    
+noib       = 6.660000e+22    
+noic       = 3.070000e+06    
+lintnoi    = 5.100000e-08    
+jss        = 2.000000e-07    
+jsws       = 6.520000e-14    
+jswgs      = 7.690000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 8.300000e+00    
+xjbvs      = 1    
+jsd        = 9.500000e-07    
+jswd       = 2.870000e-13    
+jswgd      = 2.870000e-13    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.430000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(7e-009)*jtsswg_wl'    
+jtsswgd    = '(7e-009)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 18    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.69                xtsswgd    = 0.69    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 2    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1.1                 vtsswgd    = 1.1    
+pbs        = 5.910000e-01    
+cjs        = 'cjsn_hv18_ms'    
+mjs        = 2.750000e-01    
+pbsws      = 5.980000e-01    
+cjsws      = 'cjswsn_hv18_ms'    
+mjsws      = 8.000000e-02    
+pbswgs     = 5.000000e-01    
+cjswgs     = 'cjswgsn_hv18_ms'    
+mjswgs     = 3.500000e-01    
+pbd        = 4.980000e-01    
+cjd        = 'cjdn_hv18_ms'    
+mjd        = 2.540000e-01    
+pbswd      = 6.670000e-01    
+cjswd      = 'cjswdn_hv18_ms'    
+mjswd      = 3.140000e-01    
+pbswgd     = 6.670000e-01    
+cjswgd     = 'cjswgdn_hv18_ms'    
+mjswgd     = 3.140000e-01    
+tpb        = 2.300000e-03    
+tcj        = 1.700000e-03    
+tpbsw      = 1.800000e-03    
+tcjsw      = 1.150000e-03    
+tpbswg     = 1.800000e-03    
+tcjswg     = 1.150000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+web        = 1.479332e+02    
+wec        = -2.937276e+03    
+scref      = 1e-6    
+kvth0we    = 6.438330e-03    
+k2we       = 0.0027    
+ku0we      = 2.500000e-04    
+lat        = '0+dlatn_hv18_ms'       wat        = '0+dwatn_hv18_ms'       pat        = '0+dpatn_hv18_ms'    
+rbpb       = 50                  rbpd       = 50                  rbps       = 50    
+rbdb       = 50                  rbsb       = 50                  ngcon      = 1    
+lk2we    = -0.8e-10    
+wk2we    = 0.25e-10    
+pk2we    = 0.0e-18    
+lku0we   = 2.800000e-10    
+wku0we   = -1.000000e-10    
+pku0we   = -1.900000e-17    
+lkvth0we = -2.304370e-10    
+wkvth0we = -3.189880e-10    
+pkvth0we = 3.80992e-17    
+rshg     = 'rmainsh' )    
    
.model nch_hv18.6 nmos	(	level      = 54                  lmin       = 4.95e-07    
+lmax       = '5.4e-007-dxln_hv18_ms' wmin       = 9e-07               wmax       = '1.8e-006-dxwn_hv18_ms'    
+version    = 4.5                 binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rbodymod   = 0                   rgeomod    = 1    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxn_hv18_ms+nctx'    
+toxm       = '3.36e-009+nctx'    
+dtox       = 2.95e-010           epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.196e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxln_hv18_ms'    xw         = '1.5e-08+dxwn_hv18_ms'  dlc        = 'ddlcn_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '0.44130378+dvthn_hv18_ms+dvths_lod'    
+lvth0      = '2.9263148e-009+dlvthn_hv18_ms'    
+wvth0      = '1.291675e-008+dwvthn_hv18_ms'    
+pvth0      = '3.2371494e-027+dpvthn_hv18_ms'    
+k1         = 0.2969              k2         = '0.011682291+dk2n_hv18_ms+dk2_lod'    
+lk2        = -3.6905668e-009     wk2        = -2.4911597e-011     pk2        = -3.3910634e-017    
+k3         = -5.9775             k3b        = 3.24                w0         = 1.548e-007    
+dvt0       = 9.1976              dvt1       = 0.17                dvt2       = -0.01899    
+dvt0w      = 0                   dvt1w      = 0                   dvt2w      = 0    
+dsub       = 0.33                minv       = -0.0686             voffl      = 0    
+dvtp0      = 4.386e-009          dvtp1      = 0.1                 lambda     = 0    
+vtl        = 0                   xn         = 3                   lpe0       = 6.5288e-007    
+lpeb       = 5.237e-007          vbm        = -3                  xj         = 7e-008    
+ngate      = 8.981e+020          ndep       = 2.07e+017           nsd        = 1e+020    
+phin       = 0.1                 cdsc       = 1.96465e-007        ud         = 0    
+ud1        = 0                   up         = 0.506867            lp         = 1.89837e-009    
+cdscb      = -2.8215986e-007     cdscd      = 2.19483e-007        cit        = '-0.0046144486+dcitn_hv18_ms'    
+lcit       = '2.2225166e-009+dlcitn_hv18_ms'    
+wcit       = '5.4134668e-009+dwcitn_hv18_ms'    
+pcit       = '-1.9093631e-015+dpcitn_hv18_ms'    
+voff       = '-0.084908681+dvoffn_hv18_ms'    
+lvoff      = '-8.8764882e-009+dlvoffn_hv18_ms'    
+wvoff      = '-3.904385e-008+dwvoffn_hv18_ms'    
+pvoff      = '1.0799565e-014+dpvoffn_hv18_ms'    
+nfactor    = 0.501               eta0       = '0.18302104+deta0n_hv18_ms+deta0_lod'    
+leta0      = -5.9014015e-008     weta0      = -1.5831425e-007     peta0      = 5.3997824e-014    
+etab       = -0.035    
+u0         = '((0.023024873+du0n_hv18_ms-0.00304279*ff_flagn_hv18_ms+0.00381504*ss_flagn_hv18_ms-0.00305709*fs_flagn_hv18_ms+0.00151591*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+lu0        = '((1.031526e-009+dlu0n_hv18_ms+1.1754e-09*ff_flagn_hv18_ms-1.47291e-09*ss_flagn_hv18_ms+1.18028e-09*fs_flagn_hv18_ms-5.85263e-10*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+wu0        = '((2.4669762e-009+dwu0n_hv18_ms+1.2141e-09*ff_flagn_hv18_ms-2.79723e-09*ss_flagn_hv18_ms+2.79724e-09*fs_flagn_hv18_ms-5e-15*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+pu0        = '((-8.0996736e-016+dpu0n_hv18_ms-5.39974e-16*ff_flagn_hv18_ms+1.07995e-15*ss_flagn_hv18_ms-1.07996e-15*fs_flagn_hv18_ms+3.5e-21*sf_flagn_hv18_ms)*fu0_lod)*fu0n_hv18_ms_local'    
+ua         = '-2.1555217e-009+duan_hv18_ms'    
+lua        = 1.5596282e-016      wua        = 4.0381221e-016      pua        = -6.3717432e-023    
+ub         = '3.2586847e-018+dubn_hv18_ms'    
+lub        = -3.5672753e-025     wub        = -7.6512906e-025     pub        = 9.827604e-032    
+uc         = 3.982699e-010       luc        = -1.1642485e-016     wuc        = -2.4513414e-016    
+puc        = 7.2729669e-023      eu         = 1.67    
+vsat       = '(880236.13+dvsatn_hv18_ms-178287*ff_flagn_hv18_ms+126031*ss_flagn_hv18_ms-92171.7*fs_flagn_hv18_ms+126031*sf_flagn_hv18_ms)*fvsat_lod'    
+lvsat      = '(-0.25554434+dlvsatn_hv18_ms+0.0644228*ff_flagn_hv18_ms-0.0471137*ss_flagn_hv18_ms+0.0335014*fs_flagn_hv18_ms-0.0471137*sf_flagn_hv18_ms)*fvsat_lod'    
+wvsat      = '(-0.53168633+dwvsatn_hv18_ms+0.0990879*ff_flagn_hv18_ms-0.0839173*ss_flagn_hv18_ms+0.040375*fs_flagn_hv18_ms-0.0839173*sf_flagn_hv18_ms)*fvsat_lod'    
+pvsat      = '(1.7700487e-007+dpvsatn_hv18_ms-3.72585e-08*ff_flagn_hv18_ms+3.23987e-08*ss_flagn_hv18_ms-1.56593e-08*fs_flagn_hv18_ms+3.23987e-08*sf_flagn_hv18_ms)*fvsat_lod'    
+a0         = '-0.6553724+da0n_hv18_ms+da0_lod'    
+la0        = '-1.7797359e-007+dla0n_hv18_ms'    
+wa0        = '-1.0910155e-006+dwa0n_hv18_ms'    
+pa0        = '2.6512932e-013+dpa0n_hv18_ms'    
+ags        = '5.518489+dagsn_hv18_ms'    
+lags       = '-1.1861622e-006+dlagsn_hv18_ms'    
+wags       = '-3.9079544e-006+dwagsn_hv18_ms'    
+pags       = '1.2451898e-012+dpagsn_hv18_ms'    
+a1         = 0                   a2         = 1                   b0         = 1.8037378e-009    
+b1         = 0                   keta       = 0.29976148          lketa      = -1.2556558e-007    
+wketa      = -3.9169806e-007     pketa      = 1.3060454e-013      dwg        = 8.10878e-009    
+dwb        = 7.00117e-009        pclm       = -1.2827329          lpclm      = 5.2966298e-007    
+wpclm      = 9.3143299e-007      ppclm      = -3.2398694e-013     pdiblc1    = 0    
+pdiblc2    = 1.637e-005          pdiblcb    = 0                   drout      = 0.71026057    
+pvag       = 0.045008429         delta      = 0.013132722         pscbe1     = 1e+009    
+pscbe2     = 5.1919273e-007      fprout     = 10                  pdits      = 3.4633e-005    
+pditsd     = 0                   pditsl     = 0                   rsh        = 18.5    
+rsw        = 70                  rdw        = 1223                prwg       = 0    
+prwb       = 0                   wr         = 1                   alpha0     = 1.3e-006    
+alpha1     = 0.3                 beta0      = 29.2                agidl      = '(1e-012)*agidl_wl'    
+bgidl      = 3.4259233e+008      wbgidl     = -39.008585          cgidl      = 0.031242    
+egidl      = 5                   aigbacc    = 0.01238             bigbacc    = 0.006109    
+cigbacc    = 0.2809              nigbacc    = 4.05                aigbinv    = 0.35    
+bigbinv    = 0.03                cigbinv    = 0.006               eigbinv    = 1.1    
+nigbinv    = 1                   aigc       = 0.009898            bigc       = 0.001383    
+cigc       = 1.515e-005          aigsd      = 0.0086              bigsd      = 0.0004353    
+cigsd      = 3.925e-020          nigc       = 1                   poxedge    = 1    
+pigcd      = 1.672               ntox       = 1                   vfbsdoff   = 0.1    
+cgso       = 'cgson_hv18_ms'          cgdo       = 'cgdon_hv18_ms+cfdsn_hv18_ms'          cgbo       = 0    
+cgdl       = 'cgdln_hv18_ms'          cgsl       = 'cgsln_hv18_ms'          clc        = 1e-007    
+cle        = 0.6                 cf         = 'cfsn_hv18_ms'    
+ckappas    = 0.6    
+ckappad    = 0.6                 acde       = 0.305               moin       = 5.318    
+noff       = 2.4762              voffcv     = -0.071408           tvoff      = '0.0104446+dtvoffn_hv18_ms'    
+ltvoff     = -3.29015e-009       wtvoff     = -3.93165e-009       ptvoff     = 1.40394e-015    
+tvfbsdoff  = 0.01015             kt1        = '-0.10712305+dkt1n_hv18_ms'    
+lkt1       = -7.0572959e-008     wkt1       = -1.0712947e-007     pkt1       = 3.7798477e-014    
+kt1l       = 0                   kt2        = -0.027710332        lkt2       = -4.3744992e-009    
+wkt2       = 6.53539e-009        pkt2       = 9.3416236e-016      ute        = -0.69703419    
+lute       = -9.673909e-008      wute       = -7.4513983e-007     pute       = 1.8089271e-013    
+ua1        = '0.0046937481+dua1n_hv18_ms'    
+lua1       = -2.5976311e-009     wua1       = -1.0043438e-008     pua1       = 3.200991e-015    
+ub1        = '0.0061145395+dub1n_hv18_ms+0.00233521*ff_flagn_hv18_ms'    
+lub1       = '-2.5987989e-009-5.9014e-10*ff_flagn_hv18_ms'    
+wub1       = '-1.1681153e-008-2.13672e-09*ff_flagn_hv18_ms'    
+pub1       = '3.3303155e-015+5.39975e-16*ff_flagn_hv18_ms'    
+uc1        = 0.0093624103        luc1       = -1.7460345e-009     wuc1       = -1.1604812e-008    
+puc1       = -1.0799565e-015     prt        = 0.0017    
+at         = '-0.0030146631+datn_hv18_ms+0.000368867*monte_flagn_hv18_ms'    
+lat        = '1.1646733e-009+dlatn_hv18_ms-1.42414e-10*monte_flagn_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 9.300000e-01    
+noia       = 1.750000e+42    
+noib       = 6.660000e+22    
+noic       = 3.070000e+06    
+lintnoi    = 5.100000e-08    
+jss        = 2.000000e-07    
+jsws       = 6.520000e-14    
+jswgs      = 7.690000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 8.300000e+00    
+xjbvs      = 1    
+jsd        = 9.500000e-07    
+jswd       = 2.870000e-13    
+jswgd      = 2.870000e-13    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.430000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(7e-009)*jtsswg_wl'    
+jtsswgd    = '(7e-009)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 18    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.69                xtsswgd    = 0.69    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 2    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1.1                 vtsswgd    = 1.1    
+pbs        = 5.910000e-01    
+cjs        = 'cjsn_hv18_ms'    
+mjs        = 2.750000e-01    
+pbsws      = 5.980000e-01    
+cjsws      = 'cjswsn_hv18_ms'    
+mjsws      = 8.000000e-02    
+pbswgs     = 5.000000e-01    
+cjswgs     = 'cjswgsn_hv18_ms'    
+mjswgs     = 3.500000e-01    
+pbd        = 4.980000e-01    
+cjd        = 'cjdn_hv18_ms'    
+mjd        = 2.540000e-01    
+pbswd      = 6.670000e-01    
+cjswd      = 'cjswdn_hv18_ms'    
+mjswd      = 3.140000e-01    
+pbswgd     = 6.670000e-01    
+cjswgd     = 'cjswgdn_hv18_ms'    
+mjswgd     = 3.140000e-01    
+tpb        = 2.300000e-03    
+tcj        = 1.700000e-03    
+tpbsw      = 1.800000e-03    
+tcjsw      = 1.150000e-03    
+tpbswg     = 1.800000e-03    
+tcjswg     = 1.150000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+web        = 1.479332e+02    
+wec        = -2.937276e+03    
+scref      = 1e-6    
+kvth0we    = 6.438330e-03    
+k2we       = 0.0027    
+ku0we      = 2.500000e-04    
+wat        = '0+dwatn_hv18_ms+1.1189e-09*monte_flagn_hv18_ms'    
+pat        = '0+dpatn_hv18_ms-4.31978e-16*monte_flagn_hv18_ms'    
+rbpb       = 50    
+rbpd       = 50                  rbps       = 50                  rbdb       = 50    
+rbsb       = 50                  ngcon      = 1    
+lk2we    = -0.8e-10    
+wk2we    = 0.25e-10    
+pk2we    = 0.0e-18    
+lku0we   = 2.800000e-10    
+wku0we   = -1.000000e-10    
+pku0we   = -1.900000e-17    
+lkvth0we = -2.304370e-10    
+wkvth0we = -3.189880e-10    
+pkvth0we = 3.80992e-17    
+rshg     = 'rmainsh' )    
    
.ends nch_hv18_mac    
    
    
.subckt pch_hv18_mac n1 n2 n3 n4 l=length w=width multi='1' nf='1' scale='scale_mos_hv18'    
+_dmcg='6.6e-008' _dmcg_d='7.5e-008' _dmci='6.6e-008' _xw2='1.5e-08+dxwp_hv18_ms' _xl2='1e-08+dxlp_hv18_ms' _xw= '1.5e-08' _xl= '1e-08'    
+ad='(nf*_dmcg_d+_dmci)/scale*(wef/scale+_xw2/scale)' as='(nf*_dmcg+_dmci)/scale*(wef/scale+_xw2/scale)'    
+pd='2*(nf*_dmcg_d+_dmci)/scale+(nf+1)*(wef/scale+_xw2/scale)' ps='2*(nf*_dmcg+_dmci)/scale+(nf+1)*(wef/scale+_xw2/scale)'    
+nrd='_dmcg_d/scale/nf/(wef/scale+_xw2/scale)+_rc_nrsd*_rcoflag' nrs='_dmcg/scale/nf/(wef/scale+_xw2/scale)+_rc_nrsd*_rcoflag'    
+sd='2*_dmcg_d/scale'    
+sca='0' scb='0' scc='0'    
+sc=0    
+sa='saref/scale' sb='sbref/scale'    
+sa1=sa sb1=sb sa2=sa sb2=sb sa3=sa sb3=sb sa4=sa sa5=sa sa6=sa sa7=sa    
+spa='spavar/scale' spa1=spa  spa2=spa spa3=spa    
+sap='pwr((sa4*scale+1e-9)*pwr(spa*scale+1e-9,2),1/3)/scale'    
+spba='sqrt(spbvar-spavar)*sqrt(spa2*scale+0.1*lef)/scale'    
+spba1='sqrt((spa2*scale+0.1*lef)*(spbvar-spavar+0.1*lef))/scale'    
+sapb='pwr((sa4*scale+1e-9)*pwr(spbvar-spavar,3),0.25)/scale'    
+enx='2.0e-5/scale' eny='2.0e-5/scale' eny1=eny enx1=enx eny2=eny    
+rex='sqrt((enx1*scale+1e-9)*(4e-5-2.0e-5+lef))/scale'    
+rey='sqrt((eny2*scale+1e-9)*(4e-5-2.0e-5+lef))/scale'    
+sodx='0.18e-6/scale' sodxa='sodx' sodxb='sodx'    
+sodx1='pwr((sa5*scale+1.0e-7)*sqrt(sodx*scale),2/3)/scale'    
+sodx2='pwr((pwr(1e-6,3)+10*pwr(sa6*scale,3))*sqrt(sodx*scale),2/7)/scale'    
+sodx4='pwr(pwr(sa7*scale+1.0e-9,3)*sqrt(sodx*scale),2/7)/scale'    
+sody='0.5085e-6/scale'    
+spmt='spmref/scale' spomt='spomref/scale' spomt1='1/pwr((pwr(spomt*scale,0.5)/pwr(spmt*scale,1)+1e-30),2)/scale'    
+spmb='spmref/scale' spomb='spomref/scale' spomb1='1/pwr((pwr(spomb*scale,0.5)/pwr(spmb*scale,1)+1e-30),2)/scale'    
+_conum='max(1,int(((wef/scale-0.0945*1e-6*2/scale)-0.036*1e-6/scale)/(0.1125*1e-6/scale)+1))' _rc_nrsd='90/22.5/_conum/nf'    
+_delvto=0 _mulu0=1 _ccoflag='ccoflag_hv18' _rcoflag='rcoflag_hv18' _rgflag='rgflag_hv18'    
+mismatchflag='mismatchflag_mos_hv18' globalflag='globalflag_mos_hv18' totalflag='totalflag_mos_hv18'    
    
.param lef='(l)*scale'    
.param wef='(w/nf)*scale'    
    
**********************************************    
*       Mismatch Parameters                  *    
**********************************************    
.param    
+temp1='plo_tox_hv' temp2='plo_dxl_hv' temp3='plo_dxw_hv' temp4='parl1_hv' temp5='parl2_hv'    
    
+mis_a_1=-5.0e-3 mis_a_2=-4.4e-1 mis_a_3=2.0e-1    
+mis_b_1=1.0e-3 mis_b_2=0 mis_b_3=0    
+mis_c_1=0.72 mis_c_2=0 mis_c_3=0    
+mis_d_1=1.63e-3 mis_d_2=0 mis_d_3=0    
+mis_e_1=0.0075 mis_e_2=-0.3 mis_e_3=0.3 e_limit1=0.1 e_limit2=2    
+avtgm_min=0    
    
+a='mis_a_1*pwr(abs(lef*1e6),mis_a_2)*pwr(abs(wef*1e6),mis_a_3)'    
+b='mis_b_1*pwr(abs(lef*1e6),mis_b_2)*pwr(abs(wef*1e6),mis_b_3)'    
+c='mis_c_1*pwr(abs(lef*1e6),mis_c_2)*pwr(abs(wef*1e6),mis_c_3)'    
+d='mis_d_1*pwr(abs(lef*1e6),mis_d_2)*pwr(abs(wef*1e6),mis_d_3)'    
+e='mis_e_1*pwr(abs(lef*1e6),mis_e_2)*pwr(abs(wef*1e6),mis_e_3)'    
    
+fac1='temp1'    
+fac2='temp2'    
+fac3='temp3'    
+fac4='temp4'    
+fac5='c*temp4+sqrt(1-c*c)*temp5'    
    
+geo_fac ='1/sqrt(multi*nf*lef*wef*1e12)*mismatchflag*local_factor_hv18*sigma_factor_hv18*1'    
+toxp_hv18_ms_local='d*geo_fac*toxp_hv18*fac1'    
+dxlp_hv18_ms_local='b*geo_fac*lef*fac2'    
+dxwp_hv18_ms_local='-b*geo_fac*wef*fac3'    
+dvthp_hv18_ms_local='(a*geo_fac+((1/sqrt(multi*nf))*avtgm_min*mismatchflag*local_factor_hv18*sigma_factor_hv18))*fac4'    
+fu0p_hv18_ms_local='max(e_limit1,min(e_limit2,1+e*geo_fac*fac5*(1-totalflag)))'    
+lmonte_flagp_hv18_ms='1/sqrt(multi*nf)*fac5*mismatchflag*local_factor_hv18*sigma_factor_hv18*(1-totalflag)'    
    
**********************************************    
*       End of Mismatch Parameters           *    
**********************************************    
.param _bidirectionflag=1    
.param _designflag=1    
    
+a_1=1 b_1=0 c_1=0 d_1=0 e_1_1=0 e_1_2=0 f_1_1=0 f_1_2=0 g_1_1=0 g_1_2=0    
+a_2=1 b_2=0 c_2=0 d_2=0 e_2_1=0 e_2_2=0 f_2_1=0 f_2_2=0 g_2_1=0 g_2_2=0    
+a_3=1 b_3=0 c_3=0 d_3=0 e_3_1=0 e_3_2=0 f_3_1=0 f_3_2=0 g_3_1=0 g_3_2=0    
+a_4=0.98 b_4=0 c_4=0 d_4=0 e_4_1=0 e_4_2=0 f_4_1=0 f_4_2=0 g_4_1=0 g_4_2=0    
+a_5=1 b_5=0 c_5=0 d_5=0 e_5_1=0 e_5_2=0 f_5_1=0 f_5_2=0 g_5_1=0 g_5_2=0    
    
+ratio_f1='min(1,a_1+b_1/(lef*1e6)+c_1/(wef*1e6)+d_1/(lef*1e6*wef*1e6)+e_1_1*pwr(lef*1e6,e_1_2)+f_1_1*pwr(wef*1e6,f_1_2)+g_1_1*pwr(lef*1e6*wef*1e6,g_1_2))'    
+ratio_f2='min(1,a_2+b_2/(lef*1e6)+c_2/(wef*1e6)+d_2/(lef*1e6*wef*1e6)+e_2_1*pwr(lef*1e6,e_2_2)+f_2_1*pwr(wef*1e6,f_2_2)+g_2_1*pwr(lef*1e6*wef*1e6,g_2_2))'    
+ratio_f3='min(1,a_3+b_3/(lef*1e6)+c_3/(wef*1e6)+d_3/(lef*1e6*wef*1e6)+e_3_1*pwr(lef*1e6,e_3_2)+f_3_1*pwr(wef*1e6,f_3_2)+g_3_1*pwr(lef*1e6*wef*1e6,g_3_2))'    
    
+ratio_wl_t='1*_bidirectionflag+ratio_f1*(1-_bidirectionflag)'    
+ratio_wl_d='ratio_f2*_bidirectionflag+ratio_f3*(1-_bidirectionflag)'    
+ratio_wl='ratio_wl_d*_designflag+ratio_wl_t*(1-_designflag)'    
    
+ratio_f4='min(1,a_4+b_4/(lef*1e6)+c_4/(wef*1e6)+d_4/(lef*1e6*wef*1e6)+e_4_1*pwr(lef*1e6,e_4_2)+f_4_1*pwr(wef*1e6,f_4_2)+g_4_1*pwr(lef*1e6*wef*1e6,g_4_2))'    
+ratio_f5='min(1,a_5+b_5/(lef*1e6)+c_5/(wef*1e6)+d_5/(lef*1e6*wef*1e6)+e_5_1*pwr(lef*1e6,e_5_2)+f_5_1*pwr(wef*1e6,f_5_2)+g_5_1*pwr(lef*1e6*wef*1e6,g_5_2))'    
+ratio_global='(ratio_f4*_bidirectionflag+ratio_f5*(1-_bidirectionflag))*globalflag*global_factor_hv18*sigma_factor_hv18*1'    
    
+toxp_hv18_ms          ='3.4e-09+(toxp_hv18_ms_global*ratio_global+toxp_hv18_ms_local)*(1-totalflag)+(toxp_hv18-3.4e-09)*totalflag*ratio_wl'    
+dxlp_hv18_ms          ='(dxlp_hv18_ms_global*ratio_global+dxlp_hv18_ms_local)*(1-totalflag)+dxlp_hv18*totalflag*ratio_wl'    
+dxwp_hv18_ms          ='(dxwp_hv18_ms_global*ratio_global+dxwp_hv18_ms_local)*(1-totalflag)+dxwp_hv18*totalflag*ratio_wl'    
+cjsp_hv18_ms          ='0.001466269+(cjsp_hv18_ms_global*ratio_global)*(1-totalflag)+(cjsp_hv18-0.001466269)*totalflag*ratio_wl'    
+cjswsp_hv18_ms        ='9.43953e-11+(cjswsp_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswsp_hv18-9.43953e-11)*totalflag*ratio_wl'    
+cjswgsp_hv18_ms       ='8.75432e-11+(cjswgsp_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswgsp_hv18-8.75432e-11)*totalflag*ratio_wl'    
+cjdp_hv18_ms          ='0.000705+(cjdp_hv18_ms_global*ratio_global)*(1-totalflag)+(cjdp_hv18-0.000705)*totalflag*ratio_wl'    
+cjswdp_hv18_ms        ='3.22e-10+(cjswdp_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswdp_hv18-3.22e-10)*totalflag*ratio_wl'    
+cjswgdp_hv18_ms       ='4.05e-10+(cjswgdp_hv18_ms_global*ratio_global)*(1-totalflag)+(cjswgdp_hv18-4.05e-10)*totalflag*ratio_wl'    
+cgdop_hv18_ms         ='2.622839e-011+2.57901e-13*_ccoflag+(cgdop_hv18_ms_global*ratio_global)*(1-totalflag)+(cgdop_hv18-2.622839e-011-2.57901e-13*ccoflag_hv18)*totalflag*ratio_wl'    
+cgsop_hv18_ms         ='9.634260e-011+2.4118e-11*_ccoflag+(cgsop_hv18_ms_global*ratio_global)*(1-totalflag)+(cgsop_hv18-9.634260e-011-2.4118e-11*ccoflag_hv18)*totalflag*ratio_wl'    
+cgdlp_hv18_ms         ='7.45005e-10+(cgdlp_hv18_ms_global*ratio_global)*(1-totalflag)+(cgdlp_hv18-7.45005e-10)*totalflag*ratio_wl'    
+cgslp_hv18_ms         ='1.26707e-10+(cgslp_hv18_ms_global*ratio_global)*(1-totalflag)+(cgslp_hv18-1.26707e-10)*totalflag*ratio_wl'    
+cfsp_hv18_ms          ='7.82124e-11+(cfsp_hv18_ms_global*ratio_global)*(1-totalflag)+(cfsp_hv18-7.82124e-11)*totalflag*ratio_wl'    
+cfdsp_hv18_ms         ='(9.23945e-11-7.82124e-11)-(9.23945e-11-7.82124e-11)*(1-_ccoflag)+(cfdsp_hv18_ms_global*ratio_global)*(1-totalflag)+(cfdsp_hv18-((9.23945e-11-7.82124e-11)-(9.23945e-11-7.82124e-11)*(1-ccoflag_hv18)))*totalflag*ratio_wl'    
+dvthp_hv18_ms         ='(dvthp_hv18_ms_global*ratio_global+dvthp_hv18_ms_local)*(1-totalflag)+dvthp_hv18*totalflag*ratio_wl'    
+dlvthp_hv18_ms        ='(dlvthp_hv18_ms_global*ratio_global)*(1-totalflag)+dlvthp_hv18*totalflag*ratio_wl'    
+dwvthp_hv18_ms        ='(dwvthp_hv18_ms_global*ratio_global)*(1-totalflag)+dwvthp_hv18*totalflag*ratio_wl'    
+dpvthp_hv18_ms        ='(dpvthp_hv18_ms_global*ratio_global)*(1-totalflag)+dpvthp_hv18*totalflag*ratio_wl'    
+du0p_hv18_ms          ='(du0p_hv18_ms_global*ratio_global)*(1-totalflag)+du0p_hv18*totalflag*ratio_wl'    
+dlu0p_hv18_ms         ='(dlu0p_hv18_ms_global*ratio_global)*(1-totalflag)+dlu0p_hv18*totalflag*ratio_wl'    
+dwu0p_hv18_ms         ='(dwu0p_hv18_ms_global*ratio_global)*(1-totalflag)+dwu0p_hv18*totalflag*ratio_wl'    
+dpu0p_hv18_ms         ='(dpu0p_hv18_ms_global*ratio_global)*(1-totalflag)+dpu0p_hv18*totalflag*ratio_wl'    
+dvsatp_hv18_ms        ='(dvsatp_hv18_ms_global*ratio_global)*(1-totalflag)+dvsatp_hv18*totalflag*ratio_wl'    
+dcitp_hv18_ms         ='(dcitp_hv18_ms_global*ratio_global)*(1-totalflag)+dcitp_hv18*totalflag*ratio_wl'    
+da0p_hv18_ms          ='(da0p_hv18_ms_global*ratio_global)*(1-totalflag)+da0p_hv18*totalflag*ratio_wl'    
+dla0p_hv18_ms         ='(dla0p_hv18_ms_global*ratio_global)*(1-totalflag)+dla0p_hv18*totalflag*ratio_wl'    
+dwa0p_hv18_ms         ='(dwa0p_hv18_ms_global*ratio_global)*(1-totalflag)+dwa0p_hv18*totalflag*ratio_wl'    
+dpa0p_hv18_ms         ='(dpa0p_hv18_ms_global*ratio_global)*(1-totalflag)+dpa0p_hv18*totalflag*ratio_wl'    
+ss_flagp_hv18_ms      ='(ss_flagp_hv18_ms_global*ratio_global)*(1-totalflag)+ss_flagp_hv18*totalflag*ratio_wl'    
+ff_flagp_hv18_ms      ='(ff_flagp_hv18_ms_global*ratio_global)*(1-totalflag)+ff_flagp_hv18*totalflag*ratio_wl'    
+monte_flagp_hv18_ms   ='(monte_flagp_hv18_ms_global*ratio_global)*(1-totalflag)+monte_flagp_hv18*totalflag*ratio_wl'    
+ddlcp_hv18_ms         ='6.22093e-08+(ddlcp_hv18-6.22093e-08)*totalflag*ratio_wl'    
+dlvsatp_hv18_ms       ='dlvsatp_hv18*totalflag*ratio_wl'    
+dwvsatp_hv18_ms       ='dwvsatp_hv18*totalflag*ratio_wl'    
+dpvsatp_hv18_ms       ='dpvsatp_hv18*totalflag*ratio_wl'    
+deta0p_hv18_ms        ='deta0p_hv18*totalflag*ratio_wl'    
+dweta0p_hv18_ms       ='dweta0p_hv18*totalflag*ratio_wl'    
+dnfactorp_hv18_ms     ='dnfactorp_hv18*totalflag*ratio_wl'    
+dlnfactorp_hv18_ms    ='dlnfactorp_hv18*totalflag*ratio_wl'    
+dwnfactorp_hv18_ms    ='dwnfactorp_hv18*totalflag*ratio_wl'    
+dpnfactorp_hv18_ms    ='dpnfactorp_hv18*totalflag*ratio_wl'    
+dvoffp_hv18_ms        ='dvoffp_hv18*totalflag*ratio_wl'    
+dlvoffp_hv18_ms       ='dlvoffp_hv18*totalflag*ratio_wl'    
+dwvoffp_hv18_ms       ='dwvoffp_hv18*totalflag*ratio_wl'    
+dpvoffp_hv18_ms       ='dpvoffp_hv18*totalflag*ratio_wl'    
+dlcitp_hv18_ms        ='dlcitp_hv18*totalflag*ratio_wl'    
+dwcitp_hv18_ms        ='dwcitp_hv18*totalflag*ratio_wl'    
+dpcitp_hv18_ms        ='dpcitp_hv18*totalflag*ratio_wl'    
+dagsp_hv18_ms         ='dagsp_hv18*totalflag*ratio_wl'    
+dlagsp_hv18_ms        ='dlagsp_hv18*totalflag*ratio_wl'    
+dwagsp_hv18_ms        ='dwagsp_hv18*totalflag*ratio_wl'    
+dpagsp_hv18_ms        ='dpagsp_hv18*totalflag*ratio_wl'    
+dpdiblc2p_hv18_ms     ='dpdiblc2p_hv18*totalflag*ratio_wl'    
+dlpdiblc2p_hv18_ms    ='dlpdiblc2p_hv18*totalflag*ratio_wl'    
+dwpdiblc2p_hv18_ms    ='dwpdiblc2p_hv18*totalflag*ratio_wl'    
+dppdiblc2p_hv18_ms    ='dppdiblc2p_hv18*totalflag*ratio_wl'    
+dkt1p_hv18_ms         ='dkt1p_hv18*totalflag*ratio_wl'    
+dlkt1p_hv18_ms        ='dlkt1p_hv18*totalflag*ratio_wl'    
+dwkt1p_hv18_ms        ='dwkt1p_hv18*totalflag*ratio_wl'    
+dpkt1p_hv18_ms        ='dpkt1p_hv18*totalflag*ratio_wl'    
+dua1p_hv18_ms         ='dua1p_hv18*totalflag*ratio_wl'    
+dlua1p_hv18_ms        ='dlua1p_hv18*totalflag*ratio_wl'    
+dwua1p_hv18_ms        ='dwua1p_hv18*totalflag*ratio_wl'    
+dpua1p_hv18_ms        ='dpua1p_hv18*totalflag*ratio_wl'    
+datp_hv18_ms          ='datp_hv18*totalflag*ratio_wl'    
+dlatp_hv18_ms         ='dlatp_hv18*totalflag*ratio_wl'    
+dwatp_hv18_ms         ='dwatp_hv18*totalflag*ratio_wl'    
+dpatp_hv18_ms         ='dpatp_hv18*totalflag*ratio_wl'    
+sf_flagp_hv18_ms      ='(sf_flagp_hv18_ms_global*ratio_global)*(1-totalflag)+sf_flagp_hv18*totalflag*ratio_wl'    
+fs_flagp_hv18_ms      ='(fs_flagp_hv18_ms_global*ratio_global)*(1-totalflag)+fs_flagp_hv18*totalflag*ratio_wl'    
    
main n1 n2 n3 n4 pch_hv18 w='w' l='(l)' ad=ad as=as pd=pd ps=ps nrd=nrd nrs=nrs m=multi nf=nf sa=sa sb=sb sd=sd sca=sca scb=scb scc=scc sc=sc delvto=_delvto mulu0=_mulu0    
    
******* size dependence tox *******    
.param    
+toxe0=0.0   llt=0.0    lltn=1.0    
+wwt=0.0     wwtn=1.0   lwt=0.0    
    
+nctx='toxe0+llt/pwr((lef+_xl)/1e-6,lltn)+wwt/pwr((wef+_xw)/1e-6,wwtn)+lwt/pwr((lef+_xl)/1e-6,lltn)/pwr((wef+_xw)/1e-6,wwtn)'    
    
******* rshg *******    
.param    
+rsheet=75 drsh=-10 rshh=-125 rshn=1.26    
+deltar='drsh + rshh / pwr(l*scale*1e6, rshn)'    
+dlr=0.0 llr=-2.0  llnr=0.2    
+deltal='dlr + llr*1e-6 / pwr(l*scale*1e6, llnr)'    
+reff='rsheet - deltar'    
+rmain='reff * w/nf*scale / (l*scale - deltal)'    
+rmainsh='rmain / (w/nf*scale) * (l*scale)'    
    
******* iboff_wl *******    
.param    
+r_rjtsswg=1.0   l_rjtsswg=0.0   ll_rjtsswg=1.0   w_rjtsswg=0.0   ww_rjtsswg=1.0   p_rjtsswg=0.0    
+r_ragidl=1.36    l_ragidl=0.0    ll_ragidl=1.0    w_ragidl=0.0    ww_ragidl=1.0    p_ragidl=0.0    
    
+jtsswg_wl='(r_rjtsswg+l_rjtsswg/pwr((lef*1e6),ll_rjtsswg)+w_rjtsswg/pwr((wef*1e6),ww_rjtsswg)+p_rjtsswg/(lef*1e6*wef*1e6))'    
+agidl_wl='(r_ragidl+l_ragidl/pwr((lef*1e6),ll_ragidl)+w_ragidl/pwr((wef*1e6),ww_ragidl)+p_ragidl/(lef*wef*1e12))'    
    
******* diode dc *******    
.param    
+dxti=0    
    
**********************************    
*       layout effect parameter  *    
**********************************    
+lodflag=1 pseflag=0 ceslflag=0 oseflag=1 wpeflag=1 mbeflag=0    
    
**********************************    
*       lod   parameter          *    
**********************************    
.param    
+saref1    = 0.4365e-6            sbref1    = 0.4365e-6         sabl=0.081e-6    
+saref2    = 0.4365e-6            sbref2    = 0.4365e-6    
+samax    = 5.105e-6              sbmax    = 5.105e-6    
+samin    = 0.1395e-6            sbmin    = 0.1395e-6    
+rllodflag= 1                    lreflod  = 1e-6                llodref  = 1    
+lod_clamp= -1e99    
+wlod     = 0    
+ku0      = 0                   lku0     = 0                   wku0     = 0    
+pku0     = 0                   tku0     = 0                   llodku0  = 1    
+wlodku0  = 1                   kvsat    = 1    
+kvth0    = 0                   lkvth0   = 0                   wkvth0   = 0    
+pkvth0   = 0                   llodvth  = 1                   wlodvth  = 1    
+stk2     = 0                   lodk2    = 1                   steta0   = 0    
+lodeta0  = 1    
+wlod0    = 0    
+ku00     = 0                   lku00     = 0                  wku00    = 0         pku00     = 0    
+llodku00 = 1                   wlodku00  = 1    
+kvth00   = 0                   lkvth00   = 0                  wkvth00  = 0         pkvth00   = 0    
+llodvth0 = 1                   wlodvth0  = 1                  steta00   = 0    
+stk20    = 0                   lodk20    = 1                  lodeta00  = 1    
    
+wlod1    = 0                   llod1    = 0    
+ku01     = 0	                lku01    = 2.0e-14	       wku01    = 2e-14    
+pku01    = -5e-22              llodku01 = 1    
+wlodku01 = 1                   kvsat1   = 0    
+kvth01   = -0.1e-9             lkvth01  = 0	               wkvth01  = 0    
+pkvth01  = 0	                llodvth1 = 1                   wlodvth1 = 1    
+steta01  = 0                   lodeta01 = 1    
+stk21    = 0                   lodk21   = 1    
    
+wlod2    = 0    
+ku02     = 0		            lku02    = 0		           wku02    = 0    
+pku02    = 0                   tku02    = 0                   llodku02 = 1    
+wlodku02 = 1                   kvsat2   = 0    
+kvth02   = 0.355377608         lkvth02  = -1.71288e-09        wkvth02  = '-1.28878e-09*0'    
+pkvth02  = 2.73984e-17         llodvth2 = 1                   wlodvth2 = 1    
    
+stk22    = 0                   lodk22   = 1                   steta02  = 0    
+lodeta02 = 1    
+wlod02   = 0    
+ku002    = 0.01                lku002    = 0                  wku002   = '0.01e-7*0'    
+pku002    = 0    
+llodku002= 1                   wlodku002 = 1    
+kvth002  = -0.353902161        lkvth002  = -6.21382e-10       wkvth002 = 0    
+pkvth002  = -1.19318e-17    
    
+llodvth02= 1                   wlodvth02 = 1                  steta002  = 0    
+stk202   = 0                   lodk202   = 1    
+lodeta002= 1    
    
+wlod3    = 0    
+ku03     = 0		            lku03     = 0	               wku03    = 0    
+pku03    = 0                   tku03     = 0                  llodku03 = 1    
+wlodku03 = 1                   kvsat3    = 0    
    
+kvth03   = '0.099835375*0.99'  lkvth03   = -1.13498e-09       wkvth03  = 2.5725e-10    
+pkvth03  = 6.37252e-18         llodvth3  = 1                  wlodvth3 = 1    
    
+stk23    = 0                   lodk23    = 1                  steta03  = 0    
+lodeta03 = 1    
+wlod03   = 0    
+ku003    = 0		         lku003    = -3e4              wku003   = '7e-9*2.0'	    
+pku003   = 1e-2    
+llodku003= -1                   wlodku003  = 1    
+kvth003  = '-0.100610964*0.98'  lkvth003   = '-2.4928e3*2.0'  wkvth003 = '9.70666e-10*0'    
+pkvth003 = '9.03612e-3*0.231'    
    
+llodvth03  = -1                 wlodvth03=  1                  steta003  = 0    
+stk203   = 0                   lodk203   = 1    
+lodeta003= 1    
    
**********************************    
*       pse   parameter          *    
**********************************    
    
*** pse bin selection ***    
+sa_b      = 2.61e-7             sa_b1     = 0.99e-7             dpdbinflag= 1    
+w_b       = 9e-7                w_b1      = 5.4e-7    
    
*** 1st dp 1-order parameter ***    
+spa_ins1  = 1.8e-07           spa_ins2  = 1.8e-07    
+sparef1   = 1.8e-7              sparef2   = 1.8e-7              spabl     = 1.0e-6    
+spamax    = 2.08e-7             spamin    = 1.00e-7    
+kvth0dpc  = 0.00                wkvth0dpc = 0.0e-8              wdpckvth0 = 1    
+lkvth0dpc = 0.0e-8              ldpckvth0 = 1                   pkvth0dpc = 0.0e-15    
+ku0dpc    = 0.00                wku0dpc   = 0.0e-8              wdpcku0   = 1    
+lku0dpc   = 0.0e-8              ldpcku0   = 1                   pku0dpc   = 0.0e-14    
+keta0dpc  = 0.000               wketa0dpc = 0e-9                wdpcketa0 = 1    
+kvsatdpc  = 0.00                wdpc      = 0    
    
+kvth0dpc_b1 = -0.000            kvth0dpc_b2 = -0.000            dpcbinflg = 0    
+ku0dpc_b1   = 0                 ku0dpc_b2   =0    
+keta0dpc_b1 =0                  keta0dpc_b2 =0    
    
*** 1st dp 2-order parameter ***    
+kvth0dpl  = '0.15*0'           wkvth0dpl = 0.0e-8              wdplkvth0 = 1    
+lkvth0dpl = '1.4e-12*0'         ldplkvth0 = 1.5                 pkvth0dpl = 0.0e-19    
+ku0dpl    = '0.50*0'            wku0dpl   = 0e-8                wdplku0   = 1    
+lku0dpl   = 0.0e-8              ldplku0   = 1.0                 pku0dpl   = 0.0e-11    
+keta0dpl  = '0.07*0'            wketa0dpl = 0e-7                wdplketa0 = 1    
+kvsatdpl  = 0.00                wdpl      = 0    
    
+kvth0dpl_b1 = -0.000            kvth0dpl_b2 = -0.000            dplbinflg = 0    
+ku0dpl_b1   = 0                 ku0dpl_b2   =0    
+keta0dpl_b1 =0                  keta0dpl_b2 =0    
    
*** 1st dp reverse 3-order parameter ***    
+kvth0dpx  = -0.000              wkvth0dpx = 0e-07               wdpxkvth0 = 1    
+lkvth0dpx = 0.0e-8              ldpxkvth0 = 1.0                 pkvth0dpx = 0.0e-18    
+ku0dpx    = '0.25*0'            wku0dpx   = 0e-9                wdpxku0   = 1    
+lku0dpx   = '1.0e-8*0'          ldpxku0   = 1.0                 pku0dpx   = 0.0e-18    
+keta0dpx  = 0.00                wketa0dpx = 0e-7                wdpxketa0 = 1    
+kvsatdpx  = 0.00                wdpx      = 0    
    
+kvth0dpx_b1 = -0.000            kvth0dpx_b2 = -0.000            dpxbinflg = 0    
+ku0dpx_b1   = 0                 ku0dpx_b2   =0    
+keta0dpx_b1 =0                  keta0dpx_b2 =0    
    
*** 1st dp 2-order wi l dependence parameter ***    
+kvth0dps  = '0.1*0'             wkvth0dps = 0                   wdpskvth0 = 1    
+lkvth0dps = -0.0e-9             ldpskvth0 = 1.0                 pkvth0dps = 0    
+ku0dps    = '-0.70*0'           wku0dps   = -0.0e-9             wdpsku0   = 1    
+lku0dps   = '9.0e-15*0'         ldpsku0   = 2.0                 pku0dps   = '-7.0e-23*0'    
+keta0dps  = 0.00                wketa0dps = 0                   wdpsketa0 = 1    
+kvsatdps  = '-0.3*0'            wdps      = 0    
    
+kvth0dps_b1 = -0.000            kvth0dps_b2 = -0.000            dpsbinflg = 0    
+ku0dps_b1   = 0                 ku0dps_b2   =0    
+keta0dps_b1 =0                  keta0dps_b2 =0    
    
*** 1st dp sa dependence parameter ***    
+kvth0dpa  = '0.01*0'            wkvth0dpa = -0.0e-10            wdpakvth0 = 1    
+lkvth0dpa = '1.0e-9*0'          ldpakvth0 = 1.0                 pkvth0dpa = 0e-19    
+ku0dpa    = '0.050*0'           wku0dpa   = 0e-7                wdpaku0   = 1    
+lku0dpa   = 0e-11             ldpaku0   = 1.0                 pku0dpa   = 0e-18    
+keta0dpa  = 0                wketa0dpa = 0e-7                wdpaketa0 = 1    
+ka0dpa    = -0                wka0dpa   = 0                   wdpaka0   = 1    
+lka0dpa   = -0.0e-7             ldpaka0   = 1.0                 pka0dpa   = 0.0e-14    
+kvsatdpa  = '1.5*0'             wdpa      = 0    
    
+kvth0dpa_b1 = 0.006             kvth0dpa_b2 = -0.006            dpabinflg = 0    
+ku0dpa_b1   = -0.04             ku0dpa_b2   =0.04    
+keta0dpa_b1 =0                  keta0dpa_b2 =0    
+ka0dpa_b1    =0                 ka0dpa_b2    =0    
    
*** 2nd dp parameter ***    
+spb_ins1  = 5.1e-7           spb_ins2  = 5.1e-7    
+spbref1   = 5.1e-7              spbref2   = 5.1e-7              spbbl     = 1.0e-6    
+spbmax    = 'spamax+3.7e-7'     spbmin    = 'spamin+0e-7'    
+pse_mode  = 1    
+kvth0dp2  = '0.005*0'           wkvth0dp2 = -0.0e-8             wdp2kvth0 = 1    
+lkvth0dp2 = '3e-9*0'            ldp2kvth0 = 1.0                 pkvth0dp2 = 0.0e-19    
+ku0dp2    = 0.000               wku0dp2   = -0.0e-8             wdp2ku0   = 1    
+lku0dp2   = '7.0e-5*0'          ldp2ku0   = 0.5                 pku0dp2   = 0    
+keta0dp2  = 0.00                wketa0dp2 = -0e-9               wdp2keta0 = 1    
+kvsatdp2  = '0.0'               wdp2      = 0    
    
*** 2nd dp parameter wi l dependence parameter ***    
+kvth0dp2l  = -0.00              wkvth0dp2l = -0.0e-8            wdp2lkvth0 = 1    
+lkvth0dp2l = 0.0e-9             ldp2lkvth0 = 1                  pkvth0dp2l = 0    
+ku0dp2l    = 0.00               wku0dp2l   = -0.0e-8            wdp2lku0   = 1    
+lku0dp2l   = 0.0e-9             ldp2lku0   = 1.0                pku0dp2l   = 0    
+keta0dp2l  = 0.00               wketa0dp2l = -0e-9              wdp2lketa0 = 1    
+kvsatdp2l  = 0                  wdp2l      = 0    
    
+kvth0dp2l_b1 = 0.000            kvth0dp2l_b2 = -0.000           dp2lbinflg = 0    
+ku0dp2l_b1   = -0.04            ku0dp2l_b2   =0.04    
+keta0dp2l_b1 =0                 keta0dp2l_b2 =0    
    
*** 2nd dp sa dependence parameter ***    
+kvth0dp2a  = 0.00               wkvth0dp2a = -0.0e-9            wdp2akvth0 = 1    
+lkvth0dp2a = 0.0e-9             ldp2akvth0 = 1.0                pkvth0dp2a = -0.0e-17    
+ku0dp2a    = 0.00               wku0dp2a   = 0e-9               wdp2aku0   = 1    
+lku0dp2a   = 0.0e-5             ldp2aku0   = 0.5                pku0dp2a   = -0.0e-18    
+keta0dp2a  = 0.00               wketa0dp2a = 0e-7               wdp2aketa0 = 1    
+ka0dp2a    = 0                  wka0dp2a   = 0                  wdp2aka0   = 1    
+lka0dp2a   = 0                  ldp2aka0   = 1.0                pka0dp2a   = 0.0e-14    
+kvsatdp2a  = 0.00               wdp2a      = 0    
    
+kvth0dp2a_b1 = -0.000           kvth0dp2a_b2 = -0.000           dp2abinflg = 0    
+ku0dp2a_b1   = 0                ku0dp2a_b2   =0    
+keta0dp2a_b1 =0                 keta0dp2a_b2 =0    
+ka0dp2a_b1   =0                 ka0dp2a_b2   =0    
    
*** enx parameter ***    
+enxref    = 2.0e-5              enxmax    = 2.0e-5              enxmin    = 0.295e-6    
+kvth0enx  = '-0.00'		 wkvth0enx = '-0e-9'		 wenxkvth0 = 1    
+lkvth0enx = 0			 lenxkvth0 = 1.0                 pkvth0enx = 0    
+ku0enx    = '-0.0'		 wku0enx   = 0		         wenxku0   = 1    
+lku0enx   = 0		         lenxku0   = 1.0                 pku0enx   = 0    
+keta0enx  = 0.00                wketa0enx = 0                   wenxketa0 = 1    
+ka0enx    = 0.0                 wka0enx   = 0                   wenxka0   = 1    
+lka0enx   = 0		         lenxka0   = 1.0                 pka0enx   = 0    
+kvsatenx  = -0.0                wenx      = 0                   ku0enx0   = 0    
    
*** eny parameter ***    
+enyref    = 2.0e-5              enymax    = 2.0e-5              enymin    = 0.02e-6    
+kvth0eny  = '0.000'		  wkvth0eny = '-0e-9'		wenykvth0 = 1    
+lkvth0eny = 0			  lenykvth0 = 1.0               pkvth0eny = 0    
+ku0eny    = 0.0		  wku0eny   = 0.0e-7		wenyku0   = 1    
+ku0eny0   = 0			  wku0eny0  = 0		        weny0ku0  = 1    
+lku0eny   = 0e-7		  lenyku0   = 1                 pku0eny   = -0e-15    
+keta0eny  = 0.00		  wketa0eny = 0			wenyketa0 = 1    
+ka0eny    = -0.00		  wka0eny   = -0e-8             wenyka0   = 1    
+lka0eny   = 0		          lenyka0   = 1			pka0eny   = 0e-14    
+kvsateny  = -0.0		  weny      = 0    
+kvth0eny1  = 0.000		  wkvth0eny1 = 0.0e-9             weny1kvth0 = 1    
+lkvth0eny1 = 0.0e-6             leny1kvth0 = 1.0                pkvth0eny1 = 0    
+ku0eny1    = '0.00'         wku0eny1   = 0.0e-8             weny1ku0   = 1    
+lku0eny1   = '0.0e-1'       leny1ku0   = 1.0                pku0eny1   = -0.0e-14    
+keta0eny1  = 0.00               wketa0eny1 = 0                  weny1keta0 = 1    
+ka0eny1    = 0                  wka0eny1   = 0                  weny1ka0   = 1    
+lka0eny1   = 0                  leny1ka0   = 1.0                pka0eny1   = 0    
+kvsateny1  = -0.0               weny1      = 0    
    
*** rx parameter ***    
+rxref     = 4e-5                ringxmax  = 4e-5                ringxmin  = 0.495e-6    
+rx_mode   = 0    
+kvth0rx   = -0.00               wkvth0rx  = -0.0e-9             wrxkvth0  = 1.0    
+lkvth0rx  = -0e-9               lrxkvth0  = 1.0                 pkvth0rx  = -0.0e-17    
+ku0rx     = 0.0                 wku0rx    = 0.0e-8              wrxku0    = 1.0    
+lku0rx    = 0e-8		 lrxku0    = 1                   pku0rx    = 0.0e-15    
+keta0rx   = -0.00               wketa0rx  = -0e-7               wrxketa0  = 1    
+kvsatrx   = 0.0                 wrx       = 0                   ku0rx0    = 0    
    
*** ry parameter ***    
+ryref     = 4e-5                ringymax  = 4e-5                ringymin  = 0.22e-6    
+ry_mode   = 0    
+kvth0ry   = -0.000               wkvth0ry  = 0.0e-6             wrykvth0  = 1.0    
+lkvth0ry  = 0.0e-7              lrykvth0  = 1.0                 pkvth0ry  = 0e-16    
+ku0ry     = -0.00               wku0ry    = 0e-7                wryku0    = 1.0    
+lku0ry    = -0.0e-7             lryku0    = 1.0                 pku0ry    = 0.0e-16    
+keta0ry   = 0.00                wketa0ry  = 0                   wryketa0  = 1    
+kvsatry   = 0                   wry       = 0    
+kvth0ry0  = 0.00                ku0ry0    = 0.00    
    
*** sfx parameter ***    
+sfxref      = 0.18e-6       sfxmax      = 2.556e-6      minwodx     = 0.0e-6    
+sfxmin      = 0.135e-6      sfxmax4      = 2.556e-6    
+lrefodx     = 5e-8          lodxref     = 1             wodx        = 0e-6    
+kvth0odxa   = 0	      lkvth0odxa  = 0	         lodxakvth0  = 1    
+wkvth0odxa  = 0	      wodxakvth0  = 1	         pkvth0odxa  = 0    
+ku0odxa     = 0	      lku0odxa    = 0	         lodxaku0    = 1    
+wku0odxa    = 0	      wodxaku0    = 1	         pku0odxa    = 0    
+keta0odx    = 0	      wketa0odx   = 0            wodxketa0   = 1    
+kvsatodx    = 0    
+kvth0odxb   = -0.0007	      lkvth0odxb  = -0.3e-9	 lodxbkvth0  = 1    
+wkvth0odxb  = 0.16e-9	      wodxbkvth0  = 1	         pkvth0odxb  = 0    
+ku0odxb     = 0.115	      lku0odxb    = -0.2e-8      lodxbku0    = 1    
+wku0odxb    = 0	      wodxbku0    = 1	         pku0odxb    = 0    
    
+lrefodx1    = 5e-8           lodx1ref    = 1            r_sodx1     = 0.4    
+kvth0odx1a  = -0.00138       lkvth0odx1a = 1e-14	 lodx1akvth0 = 2    
+wkvth0odx1a = -2.1e-7	      wodx1akvth0 = 1	         pkvth0odx1a = 0    
+ku0odx1a    = 0.2	      lku0odx1a   = 1.332e-13	 lodx1aku0   = 2.07    
+wku0odx1a   = -1.05e-7	      wodx1aku0   = 1            pku0odx1a   = 0    
    
+keta0odx1   = 0 	      wketa0odx1  = 0            wodx1keta0  = 1    
+kvsatodx1   = -0.1    
+kvth0odx1b  = 0	      lkvth0odx1b = -0.2e-11    lodx1bkvth0 = 1	    
+wkvth0odx1b = 0.4e-11	      wodx1bkvth0 = 1           pkvth0odx1b = 0.7e-18    
+ku0odx1b    = 0              lku0odx1b   = 0.212e-15   lodx1bku0   = 1    
+wku0odx1b   = 0.262e-15      wodx1bku0   = 2	        pku0odx1b   = 0.7e-23    
    
+csaodx3     = 0              csfxodx3    = 0           sfxpeak     = 0    
+kvth0odx3b  = 0              lkvth0odx3b = 0           lodx3bkvth0 = 1    
+wkvth0odx3b = 0              wodx3bkvth0 = 1           pkvth0odx3b = 0    
+ku0odx3b    = 0              lku0odx3b   = 0           lodx3bku0   = 1    
+wku0odx3b   = 0              wodx3bku0   = 1           pku0odx3b   = 0    
+keta0odx3   = 0              kvsatodx3   = 0    
************************************************    
+kvth0odx4b  = 0                 lkvth0odx4b = 0               lodx4bkvth0 = 1    
+wkvth0odx4b = 0                 wodx4bkvth0 = 1               pkvth0odx4b = 0    
+ku0odx4b    = 0                 lku0odx4b   = 0               lodx4bku0   = 1    
+wku0odx4b   = 0                 wodx4bku0   = 1               pku0odx4b   = 0    
+keta0odx4   = 0                 kvsatodx4   = 0    
+wketa0odx4  = 0                 wodx4keta0  = 1    
+lrefodx4    = 5e-8              lodx4ref    = 1    
+kvth0odx4a  = 0                 lkvth0odx4a = 0               lodx4akvth0 = 1    
+wkvth0odx4a = 0                 wodx4akvth0 = 1               pkvth0odx4a = 0    
+ku0odx4a    = 0                 lku0odx4a   = 0               lodx4aku0   = 1    
+wku0odx4a   = 0                 wodx4aku0   = 1               pku0odx4a   = 0    
    
************************************************    
+sfxmax5= 1.5e-6    
    
+kvth0odx5b  = 0             lkvth0odx5b = 0               lodx5bkvth0 = 1    
+wkvth0odx5b = 0             wodx5bkvth0 = 1.0             pkvth0odx5b = 0    
    
+kvtmax_sodx= 0.00    
+kvth0_a_lsodx     = 0      kvth0_b_lsodx = 0    
+kvth0_a_sa1sodx   = 0       kvth0_b_sa1sodx = 0    
+kvth0_a_sa2sodx   = 0         kvth0_b_sa2sodx = 0    
    
+ku0odx5b     = 0             lku0odx5b    = 0            lodx5bku0    = 1.00    
+wku0odx5b    = 0             wodx5bku0    = 1.0          pku0odx5b    = 0    
    
+ku0max_sodx= 0    
+ku0_a_lsodx     = 0      ku0_b_lsodx = 0    
+ku0_a_sa1sodx   = 0        ku0_b_sa1sodx = 0    
+ku0_a_sa2sodx   = 0         ku0_b_sa2sodx = 0    
    
+kvsatodx5   = 0    
************************************************    
*** sfy parameter ***    
+sfyref      = 0.5085e-6    
+sfymin      = 0.135e-6    
+sfymax      = 2.7e-6           minwody     = 0.9e-6            wody        = 5e-7    
+kvth0odya   = 0.2              lkvth0odya  = 1.0e-6            lodyakvth0  = 1.0    
+wkvth0odya  = 1.0e-6           wodyakvth0  = 1                 pkvth0odya  = 0.0e-16    
+ku0odya     = -4.5             lku0odya    = 4.5e-6            lodyaku0    = 1.0    
+wku0odya    = 1.6e-5           wodyaku0    = 1.0               pku0odya    = 1.0e-16    
+keta0ody    = 0.00             wketa0ody   = 0                 wodyketa0   = 1    
+kvsatody    = 0    
+lrefody     = 5e-8             lodyref     = 1    
+kvth0odyb   = 0                lkvth0odyb  = 0                 lodybkvth0  = 1.0    
+wkvth0odyb  = 0                wodybkvth0  = 1.0               pkvth0odyb  = 0    
+ku0odyb     = 0                lku0odyb    = 0                 lodybku0    = 1.0    
+wku0odyb    = -1.75e-7         wodybku0    = 1.0               pku0odyb    = 0    
    
+expody1     = 4.0    
+kvth0ody1a  = 0                lkvth0ody1a = 2.0e-12           lody1akvth0 = 2.0    
+wkvth0ody1a = 0                wody1akvth0 = 1.0               pkvth0ody1a = 0    
+ku0ody1a    = 0                lku0ody1a   = 1.5e-13           lody1aku0   = 2.0    
+wku0ody1a   = 4.5e-6           wody1aku0   = 1.0               pku0ody1a   = 0    
+keta0ody1   = 0                wketa0ody1  = 0                 wody1keta0  = 1.0    
+kvsatody1   = 0    
+lrefody1    = 5e-8             lody1ref    = 1.0    
+kvth0ody1b  = 0                lkvth0ody1b = 0                 lody1bkvth0 = 1.0    
+wkvth0ody1b = 0.8e-12          wody1bkvth0 = 1.0               pkvth0ody1b = 0    
+ku0ody1b    = 1.5e-6           lku0ody1b   = 0                 lody1bku0   = 0.5    
+wku0ody1b   = 0.0252e-9        wody1bku0   = 1.0               pku0ody1b   = 0    
    
**********************************    
*       mbe   parameter          *    
**********************************    
+spmref  = 0.2115e-6    spmmax  = 0.2115e-6     spmmin  = 0.0585e-6    
+spomref = 0            spommax = 0.4725e-6     spommin = 0    
+mbe_clamp= -1e99    
    
***********************************************************    
    
+wspom1 = 0    
    
+kvth0spom1 = 0               lkvth0spom1 = 0              wkvth0spom1 = 0               pkvth0spom1 = 0    
+lspom1vth0 = 1               wspom1vth0  = 1    
+ku0spom1   = 0               lku0spom1   = 0              wku0spom1   = 0               pku0spom1   = 0    
+lspom1ku0  = 1               wspom1ku0   = 1    
+kvsatspom1 = 0               tku0spom1   = 0    
+spom1eta0  = 1               steta0spom1 = 0    
    
***********************************************************    
    
+wspm = 0    
    
+kvth0spm = 0                lkvth0spm = 0                 wkvth0spm = 0                 pkvth0spm = 0    
+lspmvth0 = 1                wspmvth0  = 1    
+ku0spm   = 0                lku0spm   = 0                 wku0spm   = 0                 pku0spm   = 0    
+lspmku0  = 1                wspmku0   = 1    
+kvsatspm = 0                tku0spm   = 0    
+spmeta0  = 1                steta0spm = 0    
*** wpe vsat parameter ***    
+web_mac=1041.77  wec_mac=-7538.6    
+kvsatwe=-0.0010    
+keta0we=-0.0000    
    
**********************************    
*       lod   model              *    
**********************************    
.param    
+rllod='1/(1+pwr((lef+_xl)/lreflod,llodref)*rllodflag)'    
+saref='saref1+(saref2-saref1)*(min(max(lef,sabl),sabl+1e-10)-sabl)/1e-10'    
+sbref='sbref1+(sbref2-sbref1)*(min(max(lef,sabl),sabl+1e-10)-sabl)/1e-10'    
    
+sel1_sa='min(sa*scale,samax)'    
+sel1_sb='min(sb*scale,sbmax)'    
+sel_sa='max(sel1_sa,samin)'    
+sel_sb='max(sel1_sb,sbmin)'    
+inv_sa='1/(sel_sa+0.5*lef)'    
+inv_sb='1/(sel_sb+0.5*lef)'    
+inv_saref='1/(saref+0.5*lef)'    
+inv_sbref='1/(sbref+0.5*lef)'    
+kstress_u0='(1+lku0/pwr((lef+_xl),llodku0)+wku0/pwr((wef+_xw+wlod),wlodku0)+pku0/pwr((lef+_xl),llodku0)/pwr((wef+_xw+wlod),wlodku0))*(1+tku0*(temper/25-1))'    
+kstress_vth0='1+lkvth0/pwr((lef+_xl),llodvth)+wkvth0/pwr((wef+_xw+wlod),wlodvth)+pkvth0/pwr((lef+_xl),llodvth)/pwr((wef+_xw+wlod),wlodvth)'    
+kstress_u00='(ku00+lku00/pwr((lef+_xl),llodku00)+wku00/pwr((wef+_xw+wlod0),wlodku00)+pku00/pwr((lef+_xl),llodku00)/pwr((wef+_xw+wlod0),wlodku00))*(1+tku0*(temper/25-1))'    
+kstress_vth00='kvth00+lkvth00/pwr((lef+_xl),llodvth0)+wkvth00/pwr((wef+_xw+wlod0),wlodvth0)+pkvth00/pwr((lef+_xl),llodvth0)/pwr((wef+_xw+wlod0),wlodvth0)'    
+rho_ueff='(ku0/kstress_u0+kstress_u00)*(inv_sa+inv_sb)'    
+rho_ueffref='(ku0/kstress_u0+kstress_u00)*(inv_saref+inv_sbref)'    
    
+sel1_sa1='min(sa1*scale,samax)'    
+sel1_sb1='min(sb1*scale,sbmax)'    
+sel_sa1='max(sel1_sa1,samin)'    
+sel_sb1='max(sel1_sb1,sbmin)'    
+inv_sa1='1/pwr((sel_sa1+0.1*lef),3)'    
+inv_sb1='1/pwr((sel_sb1+0.1*lef),3)'    
+inv_saref1='1/pwr((saref+0.1*lef),3)'    
+inv_sbref1='1/pwr((sbref+0.1*lef),3)'    
+kstress_u01='1e-15*(ku01+lku01/pwr((lef+_xl+llod1),llodku01)+wku01/pwr((wef+_xw+wlod1),wlodku01)+pku01/pwr((lef+_xl+llod1),llodku01)/pwr((wef+_xw+wlod1),wlodku01))/(1+tku0*(temper/25-1))'    
+kstress_vth01='1e-15*(kvth01+lkvth01/pwr((lef+_xl+llod1),llodvth1)+wkvth01/pwr((wef+_xw+wlod1),wlodvth1)+pkvth01/pwr((lef+_xl+llod1),llodvth1)/pwr((wef+_xw+wlod1),wlodvth1))'    
+rho_ueff1='kstress_u01*(inv_sa1+inv_sb1)'    
+rho_ueffref1='kstress_u01*(inv_saref1+inv_sbref1)'    
    
+sel1_sa2='min(sa2*scale,samax)'    
+sel1_sb2='min(sb2*scale,sbmax)'    
+sel_sa2='max(sel1_sa2,samin)'    
+sel_sb2='max(sel1_sb2,sbmin)'    
+inv_sa2='pwr((pwr(5e-7/(sel_sa2+0.5*lef),2)+1),0.5)'    
+inv_sb2='pwr((pwr(5e-7/(sel_sb2+0.5*lef),2)+1),0.5)'    
+inv_saref2='pwr((pwr(5e-7/(saref+0.5*lef),2)+1),0.5)'    
+inv_sbref2='pwr((pwr(5e-7/(sbref+0.5*lef),2)+1),0.5)'    
+kstress_u02='(1+lku02/pwr((lef+_xl),llodku02)+wku02/pwr((wef+_xw+wlod2),wlodku02)+pku02/pwr((lef+_xl),llodku02)/pwr((wef+_xw+wlod2),wlodku02))*(1+tku02*(temper/25-1))'    
+kstress_vth02='1+lkvth02/pwr((lef+_xl),llodvth2)+wkvth02/pwr((wef+_xw+wlod2),wlodvth2)+pkvth02/pwr((lef+_xl),llodvth2)/pwr((wef+_xw+wlod2),wlodvth2)'    
+kstress_u002='(ku002+lku002/pwr((lef+_xl),llodku002)+wku002/pwr((wef+_xw+wlod02),wlodku002)+pku002/pwr((lef+_xl),llodku002)/pwr((wef+_xw+wlod02),wlodku002))*(1+tku02*(temper/25-1))'    
+kstress_vth002='kvth002+lkvth002/pwr((lef+_xl),llodvth02)+wkvth002/pwr((wef+_xw+wlod02),wlodvth02)+pkvth002/pwr((lef+_xl),llodvth02)/pwr((wef+_xw+wlod02),wlodvth02)'    
+rho_ueff2='(ku02/kstress_u02+kstress_u002)*(inv_sa2+inv_sb2)'    
+rho_ueffref2='(ku02/kstress_u02+kstress_u002)*(inv_saref2+inv_sbref2)'    
    
+sel1_sa3='min(sa3*scale,samax)'    
+sel1_sb3='min(sb3*scale,sbmax)'    
+sel_sa3='max(sel1_sa3,samin)'    
+sel_sb3='max(sel1_sb3,sbmin)'    
+inv_sa3='1/(1+pwr((5e-7/(sel_sa3+0.1*lef)),3))'    
+inv_sb3='1/(1+pwr((5e-7/(sel_sb3+0.1*lef)),3))'    
+inv_saref3='1/(1+pwr((5e-7/(saref+0.1*lef)),3))'    
+inv_sbref3='1/(1+pwr((5e-7/(sbref+0.1*lef)),3))'    
+kstress_u03='(1+lku03/pwr((lef+_xl),llodku03)+wku03/pwr((wef+_xw+wlod3),wlodku03)+pku03/pwr((lef+_xl),llodku03)/pwr((wef+_xw+wlod3),wlodku03))*(1+tku03*(temper/25-1))'    
+kstress_vth03='1+lkvth03/pwr((lef+_xl),llodvth3)+wkvth03/pwr((wef+_xw+wlod3),wlodvth3)+pkvth03/pwr((lef+_xl),llodvth3)/pwr((wef+_xw+wlod3),wlodvth3)'    
+kstress_u003='(ku003+lku003/pwr((lef+_xl),llodku003)+wku003/pwr((wef+_xw+wlod03),wlodku003)+pku003/pwr((lef+_xl),llodku003)/pwr((wef+_xw+wlod03),wlodku003))*(1+tku03*(temper/25-1))'    
+kstress_vth003='kvth003+lkvth003/pwr((lef+_xl),llodvth03)+wkvth003/pwr((wef+_xw+wlod03),wlodvth03)+pkvth003/pwr((lef+_xl),llodvth03)/pwr((wef+_xw+wlod03),wlodvth03)'    
+rho_ueff3='(ku03/kstress_u03+kstress_u003)*(inv_sa3+inv_sb3)'    
+rho_ueffref3='(ku03/kstress_u03+kstress_u003)*(inv_saref3+inv_sbref3)'    
    
**********************************    
*       pse   model              *    
**********************************    
+spavar='spa_ins1+(spa_ins2-spa_ins1)*(min(max(lef,spabl),spabl+1e-10)-spabl)/1e-10'    
+spbvar='spb_ins1+(spb_ins2-spb_ins1)*(min(max(lef,spbbl),spbbl+1e-10)-spbbl)/1e-10'    
+sparef='sparef1+(sparef2-sparef1)*(min(max(lef,spabl),spabl+1e-10)-spabl)/1e-10'    
+spbref='spbref1+(spbref2-spbref1)*(min(max(lef,spbbl),spbbl+1e-10)-spbbl)/1e-10'    
    
+sa_b2='min(max(max(sel_sa,sel_spa),sa_b1+1e-10)/(dpdbinflag+1e-20),sa_b)'    
+sa_b3='max((sa_b2-1e-10)*dpdbinflag,sa_b1)'    
+pse_wbin='(max(min(wef,w_b),w_b1)-w_b)/(w_b1-w_b+1e-10)'    
+pse_sabin='(max(min(sa4*scale,sa_b2),sa_b3)-sa_b2)/(sa_b3-sa_b2)'    
    
+sel1_spa='min(spa*scale,spamax)'    
+sel_spa='max(sel1_spa,spamin)'    
+inv_spa='-1e-7/pwr(sel_spa+3e-7,1)'    
+inv_sparef='-1e-7/pwr(sparef+3e-7,1)'    
+kdpc_vth0_0='kvth0dpc+lkvth0dpc/pwr((lef+_xl),ldpckvth0)+wkvth0dpc/pwr((wef+_xw+wdpc),wdpckvth0)+pkvth0dpc/pwr((lef+_xl),ldpckvth0)/pwr((wef+_xw+wdpc),wdpckvth0)'    
+kdpc_eta0_0='keta0dpc+wketa0dpc/pwr((wef+_xw+wdpc),wdpcketa0)'    
+kdpc_u0_0='ku0dpc+lku0dpc/pwr((lef+_xl),ldpcku0)+wku0dpc/pwr((wef+_xw+wdpc),wdpcku0)+pku0dpc/pwr((lef+_xl),ldpcku0)/pwr((wef+_xw+wdpc),wdpcku0)'    
+kdpc_vth0_1='kvth0dpc_b1+(kvth0dpc_b2-kvth0dpc_b1)*pse_wbin'    
+kdpc_eta0_1='keta0dpc_b1+(keta0dpc_b2-keta0dpc_b1)*pse_wbin'    
+kdpc_u0_1='ku0dpc_b1+(ku0dpc_b2-ku0dpc_b1)*pse_wbin'    
+kdpc_vth0='kdpc_vth0_0+((kdpc_vth0_1-kdpc_vth0_0)*pse_sabin)*dpcbinflg'    
+kdpc_eta0='kdpc_eta0_0+((kdpc_eta0_1-kdpc_eta0_0)*pse_sabin)*dpcbinflg'    
+kdpc_u0='kdpc_u0_0+((kdpc_u0_1-kdpc_u0_0)*pse_sabin)*dpcbinflg'    
+dinv_spa='inv_spa-inv_sparef'    
+rho_ueffdpc='kdpc_u0*(inv_spa)'    
+rho_ueffrefdpc='kdpc_u0*(inv_sparef)'    
    
+sel1_spa1='min(spa1*scale,spamax)'    
+sel_spa1='max(sel1_spa1,spamin)'    
+inv_spa1='-1e-14/pwr(sel_spa1+3e-7,2)'    
+inv_spa1ref='-1e-14/pwr(sparef+3e-7,2)'    
+kdpl_vth0_0='kvth0dpl+lkvth0dpl/pwr((lef+_xl),ldplkvth0)+wkvth0dpl/pwr((wef+_xw+wdpl),wdplkvth0)+pkvth0dpl/pwr((lef+_xl),ldplkvth0)/pwr((wef+_xw+wdpl),wdplkvth0)'    
+kdpl_eta0_0='keta0dpl+wketa0dpl/pwr((wef+_xw+wdpl),wdplketa0)'    
+kdpl_u0_0='ku0dpl+lku0dpl/pwr((lef+_xl),ldplku0)+wku0dpl/pwr((wef+_xw+wdpl),wdplku0)+pku0dpl/pwr((lef+_xl),ldplku0)/pwr((wef+_xw+wdpl),wdplku0)'    
+kdpl_vth0_1='kvth0dpl_b1+(kvth0dpl_b2-kvth0dpl_b1)*pse_wbin'    
+kdpl_eta0_1='keta0dpl_b1+(keta0dpl_b2-keta0dpl_b1)*pse_wbin'    
+kdpl_u0_1='ku0dpl_b1+(ku0dpl_b2-ku0dpl_b1)*pse_wbin'    
+kdpl_vth0='kdpl_vth0_0+((kdpl_vth0_1-kdpl_vth0_0)*pse_sabin)*dplbinflg'    
+kdpl_eta0='kdpl_eta0_0+((kdpl_eta0_1-kdpl_eta0_0)*pse_sabin)*dplbinflg'    
+kdpl_u0='kdpl_u0_0+((kdpl_u0_1-kdpl_u0_0)*pse_sabin)*dplbinflg'    
+dinv_spa1='inv_spa1-inv_spa1ref'    
+rho_ueffdpl='kdpl_u0*(inv_spa1)'    
+rho_ueffrefdpl='kdpl_u0*(inv_spa1ref)'    
    
+sel1_spa2='min(spa2*scale,spamax)'    
+sel_spa2='max(sel1_spa2,spamin)'    
+inv_spa2='-1e-21/pwr(sel_spa2+0.1*lef,3)'    
+inv_spa2ref='-1e-21/pwr(sparef+0.1*lef,3)'    
+kvth0dpx_dn='1+lkvth0dpx/pwr((lef+_xl),ldpxkvth0)+wkvth0dpx/pwr((wef+_xw+wdpx),wdpxkvth0)+pkvth0dpx/pwr((lef+_xl),ldpxkvth0)/pwr((wef+_xw+wdpx),wdpxkvth0)'    
+kdpx_vth0_0='kvth0dpx/kvth0dpx_dn'    
+keta0dpx_dn='1+wketa0dpx/pwr((wef+_xw+wdpx),wdpxketa0)'    
+kdpx_eta0_0='keta0dpx/keta0dpx_dn'    
+ku0dpx_dn='1+lku0dpx/pwr((lef+_xl),ldpxku0)+wku0dpx/pwr((wef+_xw+wdpx),wdpxku0)+pku0dpx/pwr((lef+_xl),ldpxku0)/pwr((wef+_xw+wdpx),wdpxku0)'    
+kdpx_u0_0='ku0dpx/ku0dpx_dn'    
+kdpx_vth0_1='kvth0dpx_b1+(kvth0dpx_b2-kvth0dpx_b1)*pse_wbin'    
+kdpx_eta0_1='keta0dpx_b1+(keta0dpx_b2-keta0dpx_b1)*pse_wbin'    
+kdpx_u0_1='ku0dpx_b1+(ku0dpx_b2-ku0dpx_b1)*pse_wbin'    
+kdpx_vth0='kdpx_vth0_0+((kdpx_vth0_1-kdpx_vth0_0)*pse_sabin)*dpxbinflg'    
+kdpx_eta0='kdpx_eta0_0+((kdpx_eta0_1-kdpx_eta0_0)*pse_sabin)*dpxbinflg'    
+kdpx_u0='kdpx_u0_0+((kdpx_u0_1-kdpx_u0_0)*pse_sabin)*dpxbinflg'    
+dinv_spa2='inv_spa2-inv_spa2ref'    
+rho_ueffdpx='kdpx_u0*(inv_spa2)'    
+rho_ueffrefdpx='kdpx_u0*(inv_spa2ref)'    
    
+sel1_spa3='min(spa3*scale,spamax)'    
+sel_spa3='max(sel1_spa3,spamin)'    
+inv_spa3='-1e-14/pwr(sel_spa3+0.5*lef,2)'    
+inv_spa3ref='-1e-14/pwr(sparef+0.5*lef,2)'    
+kvth0dps_dn='1+lkvth0dps/pwr((lef+_xl),ldpskvth0)+wkvth0dps/pwr((wef+_xw+wdps),wdpskvth0)+pkvth0dps/pwr((lef+_xl),ldpskvth0)/pwr((wef+_xw+wdps),wdpskvth0)'    
+kdps_vth0_0='kvth0dps/kvth0dps_dn'    
+keta0dps_dn='1+wketa0dps/pwr((wef+_xw+wdps),wdpsketa0)'    
+kdps_eta0_0='keta0dps/keta0dps_dn'    
+ku0dps_dn='1+lku0dps/pwr((lef+_xl),ldpsku0)+wku0dps/pwr((wef+_xw+wdps),wdpsku0)+pku0dps/pwr((lef+_xl),ldpsku0)/pwr((wef+_xw+wdps),wdpsku0)'    
+kdps_u0_0='ku0dps/ku0dps_dn'    
+kdps_vth0_1='kvth0dps_b1+(kvth0dps_b2-kvth0dps_b1)*pse_wbin'    
+kdps_eta0_1='keta0dps_b1+(keta0dps_b2-keta0dps_b1)*pse_wbin'    
+kdps_u0_1='ku0dps_b1+(ku0dps_b2-ku0dps_b1)*pse_wbin'    
+kdps_vth0='kdps_vth0_0+((kdps_vth0_1-kdps_vth0_0)*pse_sabin)*dpsbinflg'    
+kdps_eta0='kdps_eta0_0+((kdps_eta0_1-kdps_eta0_0)*pse_sabin)*dpsbinflg'    
+kdps_u0='kdps_u0_0+((kdps_u0_1-kdps_u0_0)*pse_sabin)*dpsbinflg'    
+dinv_spa3='inv_spa3-inv_spa3ref'    
+rho_ueffdps='kdps_u0*(inv_spa3)'    
+rho_ueffrefdps='kdps_u0*(inv_spa3ref)'    
    
+sel1_sap='max(pwr(sap*scale,3),(sa4*scale+1e-9)*pwr(spamin+1e-9,2))'    
+sel2_sap='min(sel1_sap,(sa4*scale+1e-9)*pwr(spamax+1e-9,2))'    
+sel_sap='sel2_sap/(sa4*scale+1e-9)*(min(max(sa4*scale,samin),samax)+1e-9)'    
+inv_sap='-1e-21/sel_sap'    
+inv_sapref='-1e-21/(min(max(sa4*scale,samin),samax)+1e-9)/pwr(sparef+1e-9,2)'    
+kdpa_vth0_0='kvth0dpa+lkvth0dpa/pwr((lef+_xl),ldpakvth0)+wkvth0dpa/pwr((wef+_xw+wdpa),wdpakvth0)+pkvth0dpa/pwr((lef+_xl),ldpakvth0)/pwr((wef+_xw+wdpa),wdpakvth0)'    
+kdpa_eta0_0='keta0dpa+wketa0dpa/pwr((wef+_xw+wdpa),wdpaketa0)'    
+kdpa_u0_0='ku0dpa+lku0dpa/pwr((lef+_xl),ldpaku0)+wku0dpa/pwr((wef+_xw+wdpa),wdpaku0)+pku0dpa/pwr((lef+_xl),ldpaku0)/pwr((wef+_xw+wdpa),wdpaku0)'    
+kdpa_a0_0='ka0dpa+lka0dpa/pwr((lef+_xl),ldpaka0)+wka0dpa/pwr((wef+_xw+wdpa),wdpaka0)+pka0dpa/pwr((lef+_xl),ldpaka0)/pwr((wef+_xw+wdpa),wdpaka0)'    
+kdpa_vth0_1='kvth0dpa_b1+(kvth0dpa_b2-kvth0dpa_b1)*pse_wbin'    
+kdpa_eta0_1='keta0dpa_b1+(keta0dpa_b2-keta0dpa_b1)*pse_wbin'    
+kdpa_u0_1='ku0dpa_b1+(ku0dpa_b2-ku0dpa_b1)*pse_wbin'    
+kdpa_a0_1='ka0dpa_b1+(ka0dpa_b2-ka0dpa_b1)*pse_wbin'    
+kdpa_vth0='kdpa_vth0_0+((kdpa_vth0_1-kdpa_vth0_0)*pse_sabin)*dpabinflg'    
+kdpa_eta0='kdpa_eta0_0+((kdpa_eta0_1-kdpa_eta0_0)*pse_sabin)*dpabinflg'    
+kdpa_u0='kdpa_u0_0+((kdpa_u0_1-kdpa_u0_0)*pse_sabin)*dpabinflg'    
+kdpa_a0='kdpa_a0_0+((kdpa_a0_1-kdpa_a0_0)*pse_sabin)*dpabinflg'    
+dinv_sap='inv_sap-inv_sapref'    
+rho_ueffdpa='kdpa_u0*(inv_sap)'    
+rho_ueffrefdpa='kdpa_u0*(inv_sapref)'    
    
+sel1_spba='max(pwr(spba*scale*1e4,6),pwr((spa2*scale+0.1*lef),3)*pwr(spbmin-spamin,3)*1e24)'    
+sel2_spba='min(sel1_spba,pwr((spa2*scale+0.1*lef),3)*pwr(spbmax-spamax,3)*1e24)'    
+sel_spba='sel2_spba/pwr((spa2*scale+0.1*lef),3)*pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)'    
+inv_spba_c='-1e-21*pwr(sparef+0.1*lef,3)*(1-pse_mode+pse_mode*pwr(min(max(spa2*scale,spamin),spamax),2.5)/pwr(sparef+0.1*lef,2.5))'    
+inv_spba='inv_spba_c/sel_spba*1e24'    
+inv_spbaref='inv_spba_c/pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)/pwr(spbref-sparef,3)'    
+kdp2_vth0='kvth0dp2+lkvth0dp2/pwr((lef+_xl),ldp2kvth0)+wkvth0dp2/pwr((wef+_xw+wdp2),wdp2kvth0)+pkvth0dp2/pwr((lef+_xl),ldp2kvth0)/pwr((wef+_xw+wdp2),wdp2kvth0)'    
+kdp2_eta0='keta0dp2+wketa0dp2/pwr((wef+_xw+wdp2),wdp2keta0)'    
+kdp2_u0='ku0dp2+lku0dp2/pwr((lef+_xl),ldp2ku0)+wku0dp2/pwr((wef+_xw+wdp2),wdp2ku0)+pku0dp2/pwr((lef+_xl),ldp2ku0)/pwr((wef+_xw+wdp2),wdp2ku0)'    
+dinv_spba='inv_spba-inv_spbaref'    
+rho_ueffdp2='kdp2_u0*(inv_spba)'    
+rho_ueffrefdp2='kdp2_u0*(inv_spbaref)'    
    
+sel1_spba1='max(pwr(spba1*scale*1e4,6),pwr((spa2*scale+0.1*lef),3)*pwr(spbmin-spamin+0.1*lef,3)*1e24)'    
+sel2_spba1='min(sel1_spba1,pwr((spa2*scale+0.1*lef),3)*pwr(spbmax-spamax+0.1*lef,3)*1e24)'    
+sel_spba1='sel2_spba1/pwr((spa2*scale+0.1*lef),3)*pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)'    
+inv_spba1_c='-1e-21*pwr(sparef+0.1*lef,3)*(1-pse_mode+pse_mode*pwr(min(max(spa2*scale,spamin),spamax),2.5)/pwr(sparef+0.1*lef,2.5))'    
+inv_spba1='inv_spba1_c/sel_spba1*1e24'    
+inv_spba1ref='inv_spba1_c/pwr((min(max(spa2*scale,spamin),spamax)+0.1*lef),3)/pwr(spbref-sparef+0.1*lef,3)'    
+kvth0dp2l_dn='1+lkvth0dp2l/pwr((lef+_xl),ldp2lkvth0)+wkvth0dp2l/pwr((wef+_xw+wdp2l),wdp2lkvth0)+pkvth0dp2l/pwr((lef+_xl),ldp2lkvth0)/pwr((wef+_xw+wdp2l),wdp2lkvth0)'    
+kdp2l_vth0_0='kvth0dp2l/kvth0dp2l_dn'    
+keta0dp2l_dn='1+wketa0dp2l/pwr((wef+_xw+wdp2l),wdp2lketa0)'    
+kdp2l_eta0_0='keta0dp2l/keta0dp2l_dn'    
+ku0dp2l_dn='1+lku0dp2l/pwr((lef+_xl),ldp2lku0)+wku0dp2l/pwr((wef+_xw+wdp2l),wdp2lku0)+pku0dp2l/pwr((lef+_xl),ldp2lku0)/pwr((wef+_xw+wdp2l),wdp2lku0)'    
+kdp2l_u0_0='ku0dp2l/ku0dp2l_dn'    
+kdp2l_vth0_1='kvth0dp2l_b1+(kvth0dp2l_b2-kvth0dp2l_b1)*pse_wbin'    
+kdp2l_eta0_1='keta0dp2l_b1+(keta0dp2l_b2-keta0dp2l_b1)*pse_wbin'    
+kdp2l_u0_1='ku0dp2l_b1+(ku0dp2l_b2-ku0dp2l_b1)*pse_wbin'    
+kdp2l_vth0='kdp2l_vth0_0+((kdp2l_vth0_1-kdp2l_vth0_0)*pse_sabin)*dp2lbinflg'    
+kdp2l_eta0='kdp2l_eta0_0+((kdp2l_eta0_1-kdp2l_eta0_0)*pse_sabin)*dp2lbinflg'    
+kdp2l_u0='kdp2l_u0_0+((kdp2l_u0_1-kdp2l_u0_0)*pse_sabin)*dp2lbinflg'    
+dinv_spba1='inv_spba1-inv_spba1ref'    
+rho_ueffdp2l='kdp2l_u0*(inv_spba1)'    
+rho_ueffrefdp2l='kdp2l_u0*(inv_spba1ref)'    
    
+sel1_sapb='max(pwr(sapb*scale,4),(sa4*scale+1e-9)*pwr(spbmin-spamin+1e-9,3))'    
+sel2_sapb='min(sel1_sapb,(sa4*scale+1e-9)*pwr(spbmax-spamax+1e-9,3))'    
+sel_sapb='sel2_sapb/(sa4*scale+1e-9)*(min(max(sa4*scale,samin),samax)+1e-9)'    
+inv_sapb='-1e-28/sel_sapb'    
+inv_sapbref='-1e-28/(min(max(sa4*scale,samin),samax)+1e-9)/pwr(spbref-sparef+1e-9,3)'    
+kdp2a_vth0_0='kvth0dp2a+lkvth0dp2a/pwr((lef+_xl),ldp2akvth0)+wkvth0dp2a/pwr((wef+_xw+wdp2a),wdp2akvth0)+pkvth0dp2a/pwr((lef+_xl),ldp2akvth0)/pwr((wef+_xw+wdp2a),wdp2akvth0)'    
+kdp2a_eta0_0='keta0dp2a+wketa0dp2a/pwr((wef+_xw+wdp2a),wdp2aketa0)'    
+kdp2a_u0_0='ku0dp2a+lku0dp2a/pwr((lef+_xl),ldp2aku0)+wku0dp2a/pwr((wef+_xw+wdp2a),wdp2aku0)+pku0dp2a/pwr((lef+_xl),ldp2aku0)/pwr((wef+_xw+wdp2a),wdp2aku0)'    
+kdp2a_a0_0='ka0dp2a+lka0dp2a/pwr((lef+_xl),ldp2aka0)+wka0dp2a/pwr((wef+_xw+wdp2a),wdp2aka0)+pka0dp2a/pwr((lef+_xl),ldp2aka0)/pwr((wef+_xw+wdp2a),wdp2aka0)'    
+kdp2a_vth0_1='kvth0dp2a_b1+(kvth0dp2a_b2-kvth0dp2a_b1)*pse_wbin'    
+kdp2a_eta0_1='keta0dp2a_b1+(keta0dp2a_b2-keta0dp2a_b1)*pse_wbin'    
+kdp2a_u0_1='ku0dp2a_b1+(ku0dp2a_b2-ku0dp2a_b1)*pse_wbin'    
+kdp2a_a0_1='ka0dp2a_b1+(ka0dp2a_b2-ka0dp2a_b1)*pse_wbin'    
+kdp2a_vth0='kdp2a_vth0_0+((kdp2a_vth0_1-kdp2a_vth0_0)*pse_sabin)*dp2abinflg'    
+kdp2a_eta0='kdp2a_eta0_0+((kdp2a_eta0_1-kdp2a_eta0_0)*pse_sabin)*dp2abinflg'    
+kdp2a_u0='kdp2a_u0_0+((kdp2a_u0_1-kdp2a_u0_0)*pse_sabin)*dp2abinflg'    
+kdp2a_a0='kdp2a_a0_0+((kdp2a_a0_1-kdp2a_a0_0)*pse_sabin)*dp2abinflg'    
+dinv_sapb='inv_sapb-inv_sapbref'    
+rho_ueffdp2a='kdp2a_u0*(inv_sapb)'    
+rho_ueffrefdp2a='kdp2a_u0*(inv_sapbref)'    
    
**********************************    
*       cesl   model             *    
**********************************    
+sel1_enx='max(enx*scale,enxmin)'    
+sel_enx='min(sel1_enx,enxmax)'    
+inv_enx='1e-4/pwr(sel_enx+1.0*lef,0.5)'    
+inv_enxref='1e-4/pwr(enxref+1.0*lef,0.5)'    
+kvth0enx_dn='1+lkvth0enx/pwr((lef+_xl),lenxkvth0)'    
+kenx_vth0='kvth0enx/kvth0enx_dn+wkvth0enx/pwr((wef+_xw+wenx),wenxkvth0)+pkvth0enx/pwr((lef+_xl),lenxkvth0)/pwr((wef+_xw+wenx),wenxkvth0)'    
+kenx_eta0='keta0enx+wketa0enx/pwr((wef+_xw+wenx),wenxketa0)'    
+ku0enx_dn='1+lku0enx/pwr((lef+_xl),lenxku0)'    
+kenx_u0='ku0enx0+ku0enx/ku0enx_dn+wku0enx/pwr((wef+_xw+wenx),wenxku0)+pku0enx/pwr((lef+_xl),lenxku0)/pwr((wef+_xw+wenx),wenxku0)'    
+kenx_a0='ka0enx+lka0enx/pwr((lef+_xl),lenxka0)+wka0enx/pwr((wef+_xw+wenx),wenxka0)+pka0enx/pwr((lef+_xl),lenxka0)/pwr((wef+_xw+wenx),wenxka0)'    
+dinv_enx='inv_enx-inv_enxref'    
+rho_ueffenx='kenx_u0*(inv_enx)'    
+rho_ueffrefenx='kenx_u0*(inv_enxref)'    
    
+sel1_eny='max(eny*scale,enymin)'    
+sel_eny='min(sel1_eny,enymax)'    
+inv_eny='1e-7/pwr(sel_eny+1.0*lef,1)'    
+inv_enyref='1e-7/pwr(enyref+1.0*lef,1)'    
+kvth0eny_dn='1+lkvth0eny/pwr((lef+_xl),lenykvth0)'    
+keny_vth0='kvth0eny/kvth0eny_dn+wkvth0eny/pwr((wef+_xw+weny),wenykvth0)+pkvth0eny/pwr((lef+_xl),lenykvth0)/pwr((wef+_xw+weny),wenykvth0)'    
+keny_eta0='keta0eny+wketa0eny/pwr((wef+_xw)+weny,wenyketa0)'    
+ku0eny_dn='1+lku0eny/pwr((lef+_xl),lenyku0)+wku0eny0/pwr((wef+_xw+weny),weny0ku0)'    
+keny_u0='ku0eny0+ku0eny/ku0eny_dn+wku0eny/pwr((wef+_xw+weny),wenyku0)+pku0eny/pwr((lef+_xl),lenyku0)/pwr((wef+_xw+weny),wenyku0)'    
+keny_a0='ka0eny+lka0eny/pwr((lef+_xl),lenyka0)+wka0eny/pwr((wef+_xw+weny),wenyka0)+pka0eny/pwr((lef+_xl),lenyka0)/pwr((wef+_xw+weny),wenyka0)'    
+dinv_eny='inv_eny-inv_enyref'    
+rho_ueffeny='keny_u0*(inv_eny)'    
+rho_ueffrefeny='keny_u0*(inv_enyref)'    
    
+sel1_eny1='max(eny1*scale,enymin)'    
+sel_eny1='min(sel1_eny1,enymax)'    
+inv_eny1='1e-21/pwr(sel_eny1+0.05*lef,3)'    
+inv_eny1ref='1e-21/pwr(enyref+0.05*lef,3)'    
+kvth0eny1_dn='1+lkvth0eny1/pwr((lef+_xl),leny1kvth0)'    
+keny1_vth0='kvth0eny1/kvth0eny1_dn+wkvth0eny1/pwr((wef+_xw+weny1),weny1kvth0)+pkvth0eny1/pwr((lef+_xl),leny1kvth0)/pwr((wef+_xw+weny1),weny1kvth0)'    
+keta0eny1_dn='1+wketa0eny1/pwr((wef+_xw+weny1),weny1keta0)'    
+keny1_eta0='keta0eny1/keta0eny1_dn'    
+ku0eny1_dn='1+lku0eny1/pwr((lef+_xl),leny1ku0)'    
+keny1_u0='ku0eny1/ku0eny1_dn+wku0eny1/pwr((wef+_xw+weny1),weny1ku0)+pku0eny1/pwr((lef+_xl),leny1ku0)/pwr((wef+_xw+weny1),weny1ku0)'    
+keny1_a0='ka0eny1+lka0eny1/pwr((lef+_xl),leny1ka0)+wka0eny1/pwr((wef+_xw+weny1),weny1ka0)+pka0eny1/pwr((lef+_xl),leny1ka0)/pwr((wef+_xw+weny1),weny1ka0)'    
+dinv_eny1='inv_eny1-inv_eny1ref'    
+rho_ueffeny1='keny1_u0*(inv_eny1)'    
+rho_ueffrefeny1='keny1_u0*(inv_eny1ref)'    
    
+sel1_rex='max(pwr(rex*scale,2),(enx1*scale+1e-9)*(ringxmin+1.0*lef))'    
+sel2_rex='min(sel1_rex,(enx1*scale+1e-9)*(ringxmax+1.0*lef))'    
+sel_rex='sel2_rex/(enx1*scale+1e-9)*(min(max(enx1*scale,enxmin),enxmax)+1e-9)'    
+inv_rex_c='pwr(min(max(enx1*scale,enxmin),enxmax)+1e-9,0.5)*1e4*rx_mode+1-rx_mode'    
+inv_rex='1e-14*inv_rex_c/sel_rex'    
+inv_rexref='1e-14*inv_rex_c/(min(max(enx1*scale,enxmin),enxmax)+1e-9)/(rxref-enxref+1.0*lef)'    
+kvth0rx_dn='1+lkvth0rx/pwr((lef+_xl),lrxkvth0)'    
+krex_vth0='kvth0rx/kvth0rx_dn+wkvth0rx/pwr((wef+_xw+wrx),wrxkvth0)+pkvth0rx/pwr((lef+_xl),lrxkvth0)/pwr((wef+_xw+wrx),wrxkvth0)'    
+krex_eta0='keta0rx+wketa0rx/pwr((wef+_xw+wrx),wrxketa0)'    
+ku0rx_dn='1+lku0rx/pwr((lef+_xl),lrxku0)'    
+krex_u0='ku0rx0+ku0rx/ku0rx_dn+wku0rx/pwr((wef+_xw+wrx),wrxku0)+pku0rx/pwr((lef+_xl),lrxku0)/pwr((wef+_xw+wrx),wrxku0)'    
+dinv_rex='inv_rex-inv_rexref'    
+rho_ueffrex='krex_u0*(inv_rex)'    
+rho_ueffrefrex='krex_u0*(inv_rexref)'    
    
+sel1_rey='max(pwr(rey*scale,2),(eny2*scale+1e-9)*(ringymin+1.0*lef))'    
+sel2_rey='min(sel1_rey,(eny2*scale+1e-9)*(ringymax+1.0*lef))'    
+sel_rey='sel2_rey/(eny2*scale+1e-9)*(min(max(eny2*scale,enymin),enymax)+1e-9)'    
+inv_rey_c='pwr(min(max(eny2*scale,enymin),enymax)+1e-9,0.8)*1e5*ry_mode+1-ry_mode'    
+inv_rey='1e-14*inv_rey_c/sel_rey'    
+inv_reyref='1e-14*inv_rey_c/(min(max(eny2*scale,enymin),enymax)+1e-9)/(ryref-enyref+1.0*lef)'    
+kvth0ry_dn='1+lkvth0ry/pwr((lef+_xl),lrykvth0)'    
+krey_vth0='kvth0ry0+kvth0ry/kvth0ry_dn+wkvth0ry/pwr((wef+_xw+wry),wrykvth0)+pkvth0ry/pwr((lef+_xl),lrykvth0)/pwr((wef+_xw+wry),wrykvth0)'    
+krey_eta0='keta0ry+wketa0ry/pwr((wef+_xw+wry),wryketa0)'    
+ku0ry_dn='1+lku0ry/pwr((lef+_xl),lryku0)'    
+krey_u0='ku0ry0+ku0ry/ku0ry_dn+wku0ry/pwr((wef+_xw+wry),wryku0)+pku0ry/pwr((lef+_xl),lryku0)/pwr((wef+_xw+wry),wryku0)'    
+dinv_rey='inv_rey-inv_reyref'    
+rho_ueffrey='krey_u0*(inv_rey)'    
+rho_ueffrefrey='krey_u0*(inv_reyref)'    
    
**********************************    
*       ose   model              *    
**********************************    
+sel1_sodx='min(sodx*scale,sfxmax)'    
+sel_sodx='max(sel1_sodx,sfxmin)'    
+inv_sodx='-1e-4/pwr(sel_sodx,0.5)'    
+inv_sodxref='-1e-4/pwr(sfxref,0.5)'    
    
+sel1_sodx1='min(pwr(sodx1*scale,1.5),(sa5*scale+1.0e-7)*pwr(sfxmax,0.5))'    
+sel2_sodx1='max(sel1_sodx1,(sa5*scale+1.0e-7)*pwr(sfxmin,0.5))'    
+sel_sodx1='sel2_sodx1/(sa5*scale+1.0e-7)*(min(max(sa5*scale,samin),samax)+1.0e-7)'    
+inv_sodx1='-1e-9/sel_sodx1*r_sodx1'    
+inv_sodx1ref='-1e-9/(min(max(sa5*scale,samin),samax)+1.0e-7)/pwr(sfxref,0.5)*r_sodx1'    
    
+sel1_sodx2='min(pwr(sodx2*scale,3.5),(1e-18+10*pwr(sa6*scale,3))*pwr(sfxmax,0.5))'    
+sel2_sodx2='max(sel1_sodx2,(1e-18+10*pwr(sa6*scale,3))*pwr(sfxmin,0.5))'    
+sel_sodx2='sel2_sodx2/(1e-18+10*pwr(sa6*scale,3))*(1e-18+10*pwr(min(max(sa6*scale,samin),samax),3))'    
+inv_sodx2='-1e-20/sel_sodx2*(1-r_sodx1)'    
+inv_sodx2ref='-1e-20/(1e-18+10*pwr(min(max(sa6*scale,samin),samax),3))/pwr(sfxref,0.5)*(1-r_sodx1)'    
    
+wmax_sodx='max(wef,minwodx)+_xw+wodx'    
+kvth0odxa_dn='1+lkvth0odxa/pwr((lef+_xl),lodxakvth0)'    
+ksodx_vth0a='kvth0odxa/kvth0odxa_dn*(1+wkvth0odxa/pwr(wmax_sodx,wodxakvth0))+pkvth0odxa/pwr((lef+_xl),lodxakvth0)/pwr(wmax_sodx,wodxakvth0)'    
+ksodx_vth0b='kvth0odxb+lkvth0odxb/pwr((lef+_xl),lodxbkvth0)+wkvth0odxb/pwr(wmax_sodx,wodxbkvth0)+pkvth0odxb/pwr((lef+_xl),lodxbkvth0)/pwr(wmax_sodx,wodxbkvth0)'    
+ku0odxa_dn='1+lku0odxa/pwr((lef+_xl),lodxaku0)'    
+ksodx_u0a='ku0odxa/ku0odxa_dn*(1+wku0odxa/pwr(wmax_sodx,wodxaku0))+pku0odxa/pwr((lef+_xl),lodxaku0)/pwr(wmax_sodx,wodxaku0)'    
+ksodx_u0b='ku0odxb+lku0odxb/pwr((lef+_xl),lodxbku0)+wku0odxb/pwr(wmax_sodx,wodxbku0)+pku0odxb/pwr((lef+_xl),lodxbku0)/pwr(wmax_sodx,wodxbku0)'    
+ksodx_eta0='keta0odx+wketa0odx/pwr(wmax_sodx,wodxketa0)'    
+dinv_sodx='inv_sodx-inv_sodxref'    
+rlsodx='pwr(lrefodx/(lrefodx+lef),lodxref)'    
+rho_ueffsodx='(ksodx_u0a*rlsodx+ksodx_u0b)*inv_sodx'    
+rho_ueffrefsodx='(ksodx_u0a*rlsodx+ksodx_u0b)*inv_sodxref'    
+kvth0odx1a_dn='1+lkvth0odx1a/pwr((lef+_xl),lodx1akvth0)'    
+ksodx1_vth0a='kvth0odx1a/kvth0odx1a_dn*(1+wkvth0odx1a/pwr(wmax_sodx,wodx1akvth0))+pkvth0odx1a/pwr((lef+_xl),lodx1akvth0)/pwr(wmax_sodx,wodx1akvth0)'    
+ksodx1_vth0b='kvth0odx1b+lkvth0odx1b/pwr((lef+_xl),lodx1bkvth0)+wkvth0odx1b/pwr(wmax_sodx,wodx1bkvth0)+pkvth0odx1b/pwr((lef+_xl),lodx1bkvth0)/pwr(wmax_sodx,wodx1bkvth0)'    
+ku0odx1a_dn='1+lku0odx1a/pwr((lef+_xl),lodx1aku0)'    
+ksodx1_u0a='ku0odx1a/ku0odx1a_dn*(1+wku0odx1a/pwr(wmax_sodx,wodx1aku0))+pku0odx1a/pwr((lef+_xl),lodx1aku0)/pwr(wmax_sodx,wodx1aku0)'    
+ksodx1_u0b='ku0odx1b+lku0odx1b/pwr((lef+_xl),lodx1bku0)+wku0odx1b/pwr(wmax_sodx,wodx1bku0)+pku0odx1b/pwr((lef+_xl),lodx1bku0)/pwr(wmax_sodx,wodx1bku0)'    
+ksodx1_eta0='keta0odx1+wketa0odx1/pwr(wmax_sodx,wodx1keta0)'    
+dinv_sodx1='(inv_sodx1-inv_sodx1ref)'    
+dinv_sodx2='(inv_sodx2-inv_sodx2ref)'    
+rlsodx1='pwr(lrefodx1/(lrefodx1+lef),lodx1ref)'    
+rho_ueffsodx1='(ksodx1_u0a*rlsodx1+ksodx1_u0b)*(inv_sodx1+inv_sodx2)'    
+rho_ueffrefsodx1='(ksodx1_u0a*rlsodx1+ksodx1_u0b)*(inv_sodx1ref+inv_sodx2ref)'    
    
+inv_sodx3_c='1e-9/(min(max(sa5*scale,samin),samax)+csaodx3)/(sel_sodx+csfxodx3)'    
+inv_sodx3='inv_sodx3_c*min(sel_sodx,sfxpeak)'    
+inv_sodx3ref='inv_sodx3_c*sfxref'    
+ksodx3_vth0b='kvth0odx3b+lkvth0odx3b/pwr((lef+_xl),lodx3bkvth0)+wkvth0odx3b/pwr(wef+_xw+wodx,wodx3bkvth0)+pkvth0odx3b/pwr((lef+_xl),lodx3bkvth0)/pwr(wef+_xw+wodx,wodx3bkvth0)'    
+ksodx3_u0b='ku0odx3b+lku0odx3b/pwr((lef+_xl),lodx3bku0)+wku0odx3b/pwr(wef+_xw+wodx,wodx3bku0)+pku0odx3b/pwr((lef+_xl),lodx3bku0)/pwr(wef+_xw+wodx,wodx3bku0)'    
+ksodx3_eta0='keta0odx3'    
+dinv_sodx3='(inv_sodx3-inv_sodx3ref)'    
+rho_ueffsodx3='(ksodx3_u0b)*inv_sodx3'    
+rho_ueffrefsodx3='(ksodx3_u0b)*inv_sodx3ref'    
    
+sel1_sodx4='min(pwr(sodx4*scale,3.5),pwr(sa7*scale+1.0e-9,3)*pwr(sfxmax4,0.5))'    
+sel2_sodx4='max(sel1_sodx4,pwr(sa7*scale+1.0e-9,3)*pwr(sfxmin,0.5))'    
+sel_sodx4='sel2_sodx4/pwr(sa7*scale+1.0e-9,3)*pwr(min(max(sa7*scale,samin),samax)+1.0e-9,3)'    
+inv_sodx4='-1e-26/sel_sodx4'    
+inv_sodx4ref='-1e-26/pwr(min(max(sa7*scale,samin),samax)+1.0e-9,3)/pwr(sfxref,0.5)'    
+kvth0odx4a_dn='1+lkvth0odx4a/pwr((lef+_xl),lodx4akvth0)'    
+ksodx4_vth0a='kvth0odx4a/kvth0odx4a_dn*(1+wkvth0odx4a/pwr(wef+_xw+wodx,wodx4akvth0))+pkvth0odx4a/pwr((lef+_xl),lodx4akvth0)/pwr(wef+_xw+wodx,wodx4akvth0)'    
+ku0odx4a_dn='1+lku0odx4a/pwr((lef+_xl),lodx4aku0)'    
+ksodx4_u0a='ku0odx4a/ku0odx4a_dn*(1+wku0odx4a/pwr(wef+_xw+wodx,wodx4aku0))+pku0odx4a/pwr((lef+_xl),lodx4aku0)/pwr(wef+_xw+wodx,wodx4aku0)'    
+ksodx4_vth0b='kvth0odx4b+lkvth0odx4b/pwr((lef+_xl),lodx4bkvth0)+wkvth0odx4b/pwr(wef+_xw+wodx,wodx4bkvth0)+pkvth0odx4b/pwr((lef+_xl),lodx4bkvth0)/pwr(wef+_xw+wodx,wodx4bkvth0)'    
+ksodx4_u0b='ku0odx4b+lku0odx4b/pwr((lef+_xl),lodx4bku0)+wku0odx4b/pwr(wef+_xw+wodx,wodx4bku0)+pku0odx4b/pwr((lef+_xl),lodx4bku0)/pwr(wef+_xw+wodx,wodx4bku0)'    
+ksodx4_eta0='keta0odx4+wketa0odx4/pwr(wef+_xw+wodx,wodx4keta0)'    
+dinv_sodx4='(inv_sodx4-inv_sodx4ref)'    
+rlsodx4='pwr(lrefodx4/(lrefodx4+lef),lodx4ref)'    
+rho_ueffsodx4='(ksodx4_u0a*rlsodx4+ksodx4_u0b)*inv_sodx4'    
+rho_ueffrefsodx4='(ksodx4_u0a*rlsodx4+ksodx4_u0b)*inv_sodx4ref'    
    
+inv_sodxa5='min(sel_sodxa5,sfxmax5)'    
+inv_sodxb5='min(sel_sodxb5,sfxmax5)'    
+dinv_sodx5='abs((inv_sodxb5-inv_sodxa5))'    
    
+sel1_sa9='min(sa*scale,samax)'    
+sel1_sb9='min(sb*scale,sbmax)'    
+sel_sa9='max(sel1_sa9,samin)'    
+sel_sb9='max(sel1_sb9,sbmin)'    
    
+sel1_sodxa5='min(sodxa*scale,sfxmax)'    
+sel1_sodxb5='min(sodxb*scale,sfxmax)'    
+sel_sodxa5='max(sel1_sodxa5,sfxmin)'    
+sel_sodxb5='max(sel1_sodxb5,sfxmin)'    
+dsodxflag='sgn(abs(sodxa*scale-sodxb*scale))'    
    
+ksodx5_vth0b='kvth0odx5b+lkvth0odx5b/pwr((lef+_xl),lodx5bkvth0)+wkvth0odx5b/pwr(wef+_xw+wodx,wodx5bkvth0)+pkvth0odx5b/pwr((lef+_xl),lodx5bkvth0)/pwr(wef+_xw+wodx,wodx5bkvth0)'    
+ksodx5_vth5max='((kvth0_a_lsodx/lef)*1e-6+kvth0_b_lsodx)*(max(kvtmax_sodx,max((kvth0_a_sa1sodx*sel_sa9*1e6+kvth0_b_sa1sodx),(kvth0_a_sa2sodx*sel_sa9*1e6+kvth0_b_sa2sodx))+max((kvth0_a_sa1sodx*sel_sb9*1e6+kvth0_b_sa1sodx),(kvth0_a_sa2sodx*sel_sb9*1e6+kvth0_b_sa2sodx))))'    
+ksodx5_vth5='(sfxmin/min(sodxa*scale,sodxb*scale))*(ksodx5_vth0b*ksodx5_vth5max)'    
    
+ksodx5_u0b='ku0odx5b+lku0odx5b/pwr((lef+_xl),lodx5bku0)+wku0odx5b/pwr(wmax_sodx,wodx5bku0)+pku0odx5b/pwr((lef+_xl),lodx5bku0)/pwr(wmax_sodx,wodx5bku0)'    
+rho_ueffsodx5max='((ku0_a_lsodx/lef)*1e-6+ku0_b_lsodx)*(min(ku0max_sodx,min((ku0_a_sa1sodx*sel_sa9*1e6+ku0_b_sa1sodx),(ku0_a_sa2sodx*sel_sa9*1e6+ku0_b_sa2sodx))+min((ku0_a_sa1sodx*sel_sb9*1e6+ku0_b_sa1sodx),(ku0_a_sa2sodx*sel_sb9*1e6+ku0_b_sa2sodx))))'    
+rho_ueffsodx5='(sfxmin/min(sodxa*scale,sodxb*scale))*(max(ksodx5_u0b*dinv_sodx5,rho_ueffsodx5max))'    
    
+sel1_sody='max(sody*scale,sfymin)'    
+sel_sody='min(sel1_sody,sfymax)'    
+inv_sody='-1e-4/pwr(sel_sody,0.5)'    
+inv_sodyref='-1e-4/pwr(sfyref,0.5)'    
+wmax_sody='max(wef,minwody)+_xw+wody'    
+kvth0odya_dn='1+lkvth0odya/pwr((lef+_xl),lodyakvth0)'    
+ksody_vth0a='kvth0odya/kvth0odya_dn*(1+wkvth0odya/pwr(wmax_sody,wodyakvth0))+pkvth0odya/pwr((lef+_xl),lodyakvth0)/pwr(wmax_sody,wodyakvth0)'    
+ksody_vth0b='kvth0odyb+lkvth0odyb/pwr((lef+_xl),lodybkvth0)+wkvth0odyb/pwr(wmax_sody,wodybkvth0)+pkvth0odyb/pwr((lef+_xl),lodybkvth0)/pwr(wmax_sody,wodybkvth0)'    
+ku0odya_dn='1+lku0odya/pwr((lef+_xl),lodyaku0)'    
+ksody_u0a='ku0odya/ku0odya_dn*(1+wku0odya/pwr(wmax_sody,wodyaku0))+pku0odya/pwr((lef+_xl),lodyaku0)/pwr(wmax_sody,wodyaku0)'    
+ksody_u0b='ku0odyb+lku0odyb/pwr((lef+_xl),lodybku0)+wku0odyb/pwr(wmax_sody,wodybku0)+pku0odyb/pwr((lef+_xl),lodybku0)/pwr(wmax_sody,wodybku0)'    
+ksody_eta0='keta0ody+wketa0ody/pwr((wef+_xw+wody),wodyketa0)'    
+dinv_sody='inv_sody-inv_sodyref'    
+rlsody='pwr(lrefody/(lrefody+lef),lodyref)'    
+rho_ueffsody='(ksody_u0a*rlsody+ksody_u0b)*(inv_sody)'    
+rho_ueffrefsody='(ksody_u0a*rlsody+ksody_u0b)*(inv_sodyref)'    
    
+inv_sody1='-1*pwr(1e-6/min(sel_sody,sfyref),expody1)'    
+inv_sody1ref='-1*pwr(1e-6/sfyref,expody1)'    
+kvth0ody1a_dn='1+lkvth0ody1a/pwr((lef+_xl),lody1akvth0)'    
+ksody1_vth0a='kvth0ody1a/kvth0ody1a_dn*(1+wkvth0ody1a/pwr(wmax_sody,wody1akvth0))+pkvth0ody1a/pwr((lef+_xl),lody1akvth0)/pwr(wmax_sody,wody1akvth0)'    
+ksody1_vth0b='kvth0ody1b+lkvth0ody1b/pwr((lef+_xl),lody1bkvth0)+wkvth0ody1b/pwr(wmax_sody,wody1bkvth0)+pkvth0ody1b/pwr((lef+_xl),lody1bkvth0)/pwr(wmax_sody,wody1bkvth0)'    
+ku0ody1a_dn='1+lku0ody1a/pwr((lef+_xl),lody1aku0)'    
+ksody1_u0a='ku0ody1a/ku0ody1a_dn*(1+wku0ody1a/pwr(wmax_sody,wody1aku0))+pku0ody1a/pwr((lef+_xl),lody1aku0)/pwr(wmax_sody,wody1aku0)'    
+ksody1_u0b='ku0ody1b+lku0ody1b/pwr((lef+_xl),lody1bku0)+wku0ody1b/pwr(wmax_sody,wody1bku0)+pku0ody1b/pwr((lef+_xl),lody1bku0)/pwr(wmax_sody,wody1bku0)'    
+ksody1_eta0='keta0ody1+wketa0ody1/pwr(wmax_sody,wody1keta0)'    
+dinv_sody1='inv_sody1-inv_sody1ref'    
+rlsody1='pwr(lrefody1/(lrefody1+lef),lody1ref)'    
+rho_ueffsody1='(ksody1_u0a*rlsody1+ksody1_u0b)*(inv_sody1)'    
+rho_ueffrefsody1='(ksody1_u0a*rlsody1+ksody1_u0b)*(inv_sody1ref)'    
    
**********************************    
*       mbe   model              *    
**********************************    
+selmbet='max(0,sgn(spomt*scale))'    
+selmbeb='max(0,sgn(spomb*scale))'    
    
+sel1_spmt='min(spmt*scale,spmmax)'    
+sel_spmt='max(sel1_spmt,spmmin)'    
+inv_spmt='1/pwr(sel_spmt,2)'    
+sel1_spmb='min(spmb*scale,spmmax)'    
+sel_spmb='max(sel1_spmb,spmmin)'    
+inv_spmb='1/pwr(sel_spmb,2)'    
+inv_spmref='1/pwr(spmref,2)'    
    
+sel1_spomt1='min(pwr(spomt1*scale,0.5),pwr(spmmax,1)/pwr(max(spomt*scale,1e-30),0.5))'    
+sel2_spomt1='max(sel1_spomt1,pwr(spmmin,1)/pwr(max(spomt*scale,1e-30),0.5))'    
+sel_spomt1='sel2_spomt1*pwr(max(spomt*scale,1e-30),0.5)/pwr(min(max(max(spomt*scale,1e-30),spommin),spommax),0.5)'    
+inv_spomt1='1/sel_spomt1'    
+sel1_spomb1='min(pwr(spomb1*scale,0.5),pwr(spmmax,1)/pwr(max(spomb*scale,1e-30),0.5))'    
+sel2_spomb1='max(sel1_spomb1,pwr(spmmin,1)/pwr(max(spomb*scale,1e-30),0.5))'    
+sel_spomb1='sel2_spomb1*pwr(max(spomb*scale,1e-30),0.5)/pwr(min(max(max(spomb*scale,1e-30),spommin),spommax),0.5)'    
+inv_spomb1='1/sel_spomb1'    
+inv_spom1ref='pwr(spomref,0.5)/spmref'    
    
+kspom1_u0='(ku0spom1+lku0spom1/pwr((lef+_xl),lspom1ku0)+wku0spom1/pwr((wef+_xw+wspom1),wspom1ku0)+pku0spom1/pwr((lef+_xl),lspom1ku0)/pwr((wef+_xw+wspom1),wspom1ku0))*(1+tku0spom1*(temper/25-1))'    
+kspom1_vth0='kvth0spom1+lkvth0spom1/pwr((lef+_xl),lspom1vth0)+wkvth0spom1/pwr((wef+_xw+wspom1),wspom1vth0)+pkvth0spom1/pwr((lef+_xl),lspom1vth0)/pwr((wef+_xw+wspom1),wspom1vth0)'    
+rho_ueffspomt1='kspom1_u0*inv_spomt1'    
+rho_ueffspomb1='kspom1_u0*inv_spomb1'    
+rho_ueffrefspom1='kspom1_u0*inv_spom1ref'    
    
+kspm_u0='(ku0spm+lku0spm/pwr((lef+_xl),lspmku0)+wku0spm/pwr((wef+_xw+wspm),wspmku0)+pku0spm/pwr((lef+_xl),lspmku0)/pwr((wef+_xw+wspm),wspmku0))*(1+tku0spm*(temper/25-1))'    
+kspm_vth0='kvth0spm+lkvth0spm/pwr((lef+_xl),lspmvth0)+wkvth0spm/pwr((wef+_xw+wspm),wspmvth0)+pkvth0spm/pwr((lef+_xl),lspmvth0)/pwr((wef+_xw+wspm),wspmvth0)'    
+rho_ueffspmt='kspm_u0*inv_spmt'    
+rho_ueffspmb='kspm_u0*inv_spmb'    
+rho_ueffrefspm='kspm_u0*inv_spmref'    
    
**********************************    
*       total lde model          *    
**********************************    
    
+dvths_sa='((kvth0/kstress_vth0+kstress_vth00)*(inv_sa+inv_sb-inv_saref-inv_sbref)+kstress_vth01*(inv_sa1+inv_sb1-inv_saref1-inv_sbref1)+(kvth02/kstress_vth02+kstress_vth002)*(inv_sa2+inv_sb2-inv_saref2-inv_sbref2)+(kvth03/kstress_vth03+kstress_vth003)*(inv_sa3+inv_sb3-inv_saref3-inv_sbref3))*rllod'    
+dvths_dp='-kdpc_vth0*dinv_spa-kdpl_vth0*dinv_spa1-kdpx_vth0*dinv_spa2-kdps_vth0*dinv_spa3-kdpa_vth0*dinv_sap-kdp2_vth0*dinv_spba-kdp2l_vth0*dinv_spba1-kdp2a_vth0*dinv_sapb'    
+dvths_enxy='kenx_vth0*dinv_enx+keny_vth0*dinv_eny+keny1_vth0*dinv_eny1+selmin(krex_vth0*inv_rex,kenx_vth0*inv_enx)-krex_vth0*inv_rexref+selmin(krey_vth0*inv_rey,keny_vth0*inv_eny+keny1_vth0*inv_eny1)-krey_vth0*inv_reyref'    
+dvths_odod='-1*(ksodx_vth0a*rlsodx+ksodx_vth0b)*dinv_sodx-(ksodx1_vth0a*rlsodx1+ksodx1_vth0b)*(dinv_sodx1+dinv_sodx2)-(ksodx3_vth0b)*(dinv_sodx3)-(ksodx4_vth0a*rlsodx4+ksodx4_vth0b)*(dinv_sodx4)-(ksodx5_vth5)*(dinv_sodx5)*dsodxflag-(ksody_vth0a*rlsody+ksody_vth0b)*dinv_sody-(ksody1_vth0a*rlsody1+ksody1_vth0b)*dinv_sody1'    
+dvths_spomt1='kspom1_vth0*(inv_spomt1-inv_spom1ref)'    
+dvths_spomb1='kspom1_vth0*(inv_spomb1-inv_spom1ref)'    
+dvths_spmt='kspm_vth0*(inv_spmt-inv_spmref)'    
+dvths_spmb='kspm_vth0*(inv_spmb-inv_spmref)'    
+dvths_mbe='(dvths_spomt1+dvths_spmt)*selmbet+(dvths_spomb1+dvths_spmb)*selmbeb'    
+dvths_lod='dvths_sa*lodflag+dvths_dp*pseflag+dvths_enxy*ceslflag+dvths_odod*oseflag+dvths_mbe*mbeflag'    
    
+fu0_sa_nu='max((1+(rho_ueff+rho_ueff1+rho_ueff2+rho_ueff3)*rllod*lodflag),lod_clamp)'    
+fu0_sa_dn='max((1+(rho_ueffref+rho_ueffref1+rho_ueffref2+rho_ueffref3)*rllod*lodflag),lod_clamp)'    
+fu0_sa='fu0_sa_nu/fu0_sa_dn'    
+fu0_dp_nu='(1+(rho_ueffdpc+rho_ueffdpl+rho_ueffdpx+rho_ueffdps+rho_ueffdpa)*pseflag)*(1+(rho_ueffdp2+rho_ueffdp2l+rho_ueffdp2a)*pseflag)'    
+fu0_dp_dn='(1+(rho_ueffrefdpc+rho_ueffrefdpl+rho_ueffrefdpx+rho_ueffrefdps+rho_ueffrefdpa)*pseflag)*(1+(rho_ueffrefdp2+rho_ueffrefdp2l+rho_ueffrefdp2a)*pseflag)'    
+fu0_dp='fu0_dp_nu/fu0_dp_dn'    
+fu0_enxy_nu='(1+(rho_ueffenx+rho_ueffeny+rho_ueffeny1+selmin(rho_ueffrex,rho_ueffenx)+selmin(rho_ueffrey,rho_ueffeny+rho_ueffeny1))*ceslflag)'    
+fu0_enxy_dn='(1+(rho_ueffrefenx+rho_ueffrefeny+rho_ueffrefeny1+rho_ueffrefrex+rho_ueffrefrey)*ceslflag)'    
+fu0_enxy='fu0_enxy_nu/fu0_enxy_dn'    
+fu0_odod_nu='(1+(rho_ueffsodx+rho_ueffsodx1+rho_ueffsodx3+rho_ueffsodx4+rho_ueffsodx5*dsodxflag+rho_ueffsody+rho_ueffsody1)*oseflag)'    
+fu0_odod_dn='(1+(rho_ueffrefsodx+rho_ueffrefsodx1+rho_ueffrefsodx3+rho_ueffrefsodx4+rho_ueffrefsody+rho_ueffrefsody1)*oseflag)'    
+fu0_odod='fu0_odod_nu/fu0_odod_dn'    
+fu0_spomt1_nu='max((1+rho_ueffspomt1*mbeflag*selmbet),mbe_clamp)'    
+fu0_spomt1_dn='max((1+rho_ueffrefspom1*mbeflag*selmbet),mbe_clamp)'    
+fu0_spomt1='fu0_spomt1_nu/fu0_spomt1_dn'    
+fu0_spomb1_nu='max((1+rho_ueffspomb1*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spomb1_dn='max((1+rho_ueffrefspom1*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spomb1='fu0_spomb1_nu/fu0_spomb1_dn'    
+fu0_spmt_nu='max((1+rho_ueffspmt*mbeflag*selmbet),mbe_clamp)'    
+fu0_spmt_dn='max((1+rho_ueffrefspm*mbeflag*selmbet),mbe_clamp)'    
+fu0_spmt='fu0_spmt_nu/fu0_spmt_dn'    
+fu0_spmb_nu='max((1+rho_ueffspmb*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spmb_dn='max((1+rho_ueffrefspm*mbeflag*selmbeb),mbe_clamp)'    
+fu0_spmb='fu0_spmb_nu/fu0_spmb_dn'    
+fu0_mbe='fu0_spomt1*fu0_spomb1*fu0_spmt*fu0_spmb'    
+fu0_lod='max(1e-1,fu0_sa*fu0_dp*fu0_enxy*fu0_odod*fu0_mbe)'    
    
+fvsat_sa_nu='max((1+(kvsat*rho_ueff+kvsat1*rho_ueff1+kvsat2*rho_ueff2+kvsat3*rho_ueff3)*rllod*lodflag),lod_clamp)'    
+fvsat_sa_dn='max((1+(kvsat*rho_ueffref+kvsat1*rho_ueffref1+kvsat2*rho_ueffref2+kvsat3*rho_ueffref3)*rllod*lodflag),lod_clamp)'    
+fvsat_sa='fvsat_sa_nu/fvsat_sa_dn'    
+fvsat_dp_nu='(1+(kvsatdpc*rho_ueffdpc+kvsatdpl*rho_ueffdpl+kvsatdps*rho_ueffdps+kvsatdpx*rho_ueffdpx+kvsatdpa*rho_ueffdpa)*pseflag)*(1+(kvsatdp2*rho_ueffdp2+kvsatdp2l*rho_ueffdp2l+kvsatdp2a*rho_ueffdp2a)*pseflag)'    
+fvsat_dp_dn='(1+(kvsatdpc*rho_ueffrefdpc+kvsatdpl*rho_ueffrefdpl+kvsatdps*rho_ueffrefdps+kvsatdpx*rho_ueffrefdpx+kvsatdpa*rho_ueffrefdpa)*pseflag)*(1+(kvsatdp2*rho_ueffrefdp2+kvsatdp2l*rho_ueffrefdp2l+kvsatdp2a*rho_ueffrefdp2a)*pseflag)'    
+fvsat_dp='fvsat_dp_nu/fvsat_dp_dn'    
+fvsat_enxy_nu='(1+(kvsatenx*rho_ueffenx+kvsateny*rho_ueffeny+kvsateny1*rho_ueffeny1+selmin(kvsatrx*rho_ueffrex,kvsatenx*rho_ueffenx)+selmin(kvsatry*rho_ueffrey,kvsateny*rho_ueffeny+kvsateny1*rho_ueffeny1))*ceslflag)'    
+fvsat_enxy_dn='(1+(kvsatenx*rho_ueffrefenx+kvsateny*rho_ueffrefeny+kvsateny1*rho_ueffrefeny1+kvsatrx*rho_ueffrefrex+kvsatry*rho_ueffrefrey)*ceslflag)'    
+fvsat_enxy='fvsat_enxy_nu/fvsat_enxy_dn'    
+fvsat_odod_nu='(1+(kvsatodx*rho_ueffsodx+kvsatodx1*rho_ueffsodx1+kvsatodx3*rho_ueffsodx3+kvsatodx4*inv_sodx4+kvsatodx5*rho_ueffsodx5*dsodxflag+kvsatody*rho_ueffsody+kvsatody1*rho_ueffsody1)*oseflag)'    
+fvsat_odod_dn='(1+(kvsatodx*rho_ueffrefsodx+kvsatodx1*rho_ueffrefsodx1+kvsatodx3*rho_ueffrefsodx3+kvsatodx4*inv_sodx4ref+kvsatody*rho_ueffrefsody+kvsatody1*rho_ueffrefsody1)*oseflag)'    
+fvsat_odod='fvsat_odod_nu/fvsat_odod_dn'    
+fvsat_spomt1_nu='max((1+(kvsatspom1*rho_ueffspomt1)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spomt1_dn='max((1+(kvsatspom1*rho_ueffrefspom1)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spomt1='fvsat_spomt1_nu/fvsat_spomt1_dn'    
+fvsat_spomb1_nu='max((1+(kvsatspom1*rho_ueffspomb1)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spomb1_dn='max((1+(kvsatspom1*rho_ueffrefspom1)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spomb1='fvsat_spomb1_nu/fvsat_spomb1_dn'    
+fvsat_spmt_nu='max((1+(kvsatspm*rho_ueffspmt)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spmt_dn='max((1+(kvsatspm*rho_ueffrefspm)*mbeflag*selmbet),mbe_clamp)'    
+fvsat_spmt='fvsat_spmt_nu/fvsat_spmt_dn'    
+fvsat_spmb_nu='max((1+(kvsatspm*rho_ueffspmb)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spmb_dn='max((1+(kvsatspm*rho_ueffrefspm)*mbeflag*selmbeb),mbe_clamp)'    
+fvsat_spmb='fvsat_spmb_nu/fvsat_spmb_dn'    
+fvsat_mbe='fvsat_spomt1*fvsat_spomb1*fvsat_spmt*fvsat_spmb'    
+fvsat_lod='max(1e-1,fvsat_sa*fvsat_dp*fvsat_enxy*fvsat_odod*fvsat_mbe+kvsatwe*(sca+web_mac*scb+wec_mac*scc)*wpeflag)'    
    
+da0_dp='kdpa_a0*dinv_sap+kdp2a_a0*dinv_sapb'    
+da0_enxy='kenx_a0*dinv_enx+keny_a0*dinv_eny+keny1_a0*dinv_eny1'    
+da0_lod='da0_dp*pseflag+da0_enxy*ceslflag'    
    
+deta0_sa='((steta0/pwr(kstress_vth0,lodeta0)+steta00*pwr(kstress_vth00,lodeta00))*(inv_sa+inv_sb-inv_saref-inv_sbref)+steta01*pwr(kstress_vth01,lodeta01)*(inv_sa1+inv_sb1-inv_saref1-inv_sbref1)+(steta02/pwr(kstress_vth02,lodeta02)+steta002*pwr(kstress_vth002,lodeta002))*(inv_sa2+inv_sb2-inv_saref2-inv_sbref2)+(steta03/pwr(kstress_vth03,lodeta03)+steta003*pwr(kstress_vth003,lodeta003))*(inv_sa3+inv_sb3-inv_saref3-inv_sbref3))*rllod'    
+deta0_dp='kdpc_eta0*dinv_spa+kdpl_eta0*dinv_spa1+kdpx_eta0*dinv_spa2+kdps_eta0*dinv_spa3+kdpa_eta0*dinv_sap+kdp2_eta0*dinv_spba+kdp2l_eta0*dinv_spba1+kdp2a_eta0*dinv_sapb'    
+deta0_enxy='kenx_eta0*dinv_enx+keny_eta0*dinv_eny+keny1_eta0*dinv_eny1+krex_eta0*dinv_rex+krey_eta0*dinv_rey'    
+deta0_odod='ksodx_eta0*dinv_sodx+ksodx1_eta0*(dinv_sodx1+dinv_sodx2)+ksodx3_eta0*dinv_sodx3+ksodx4_eta0*dinv_sodx4+ksody_eta0*dinv_sody+ksody1_eta0*dinv_sody1'    
+deta0_spomt1='(steta0spom1*pwr(kspom1_vth0,spom1eta0))*(inv_spomt1-inv_spom1ref)'    
+deta0_spomb1='(steta0spom1*pwr(kspom1_vth0,spom1eta0))*(inv_spomb1-inv_spom1ref)'    
+deta0_spmt='(steta0spm*pwr(kspm_vth0,spmeta0))*(inv_spmt-inv_spmref)'    
+deta0_spmb='(steta0spm*pwr(kspm_vth0,spmeta0))*(inv_spmb-inv_spmref)'    
+deta0_mbe='(deta0_spomt1+deta0_spmt)*selmbet+(deta0_spomb1+deta0_spmb)*selmbeb'    
+deta0_lod='deta0_sa*lodflag+deta0_dp*pseflag+deta0_enxy*ceslflag+deta0_odod*oseflag+deta0_mbe*mbeflag+keta0we*(sca+web_mac*scb+wec_mac*scc)*wpeflag'    
    
+dk2_lod='((stk2/pwr(kstress_vth0,lodk2)+stk20*pwr(kstress_vth00,lodk20))*(inv_sa+inv_sb-inv_saref-inv_sbref)+stk21*pwr(kstress_vth01,lodk21)*(inv_sa1+inv_sb1-inv_saref1-inv_sbref1)+(stk22/pwr(kstress_vth02,lodk22)+stk202*pwr(kstress_vth002,lodk202))*(inv_sa2+inv_sb2-inv_saref2-inv_sbref2)+(stk23/pwr(kstress_vth03,lodk23)+stk203*pwr(kstress_vth003,lodk203))*(inv_sa3+inv_sb3-inv_saref3-inv_sbref3))*lodflag*rllod'    
+selmin(par1_hv,par2_hv)='abs(par1_hv)<abs(par2_hv) ? par1_hv : (par2_hv*-1)'    
    
* ver_090b0809010v_020101010102    
    
.model pch_hv18.1 pmos	(	level      = 54                  lmin       = '6.3e-007-dxlp_hv18_ms'    
+lmax       = 1.0801e-06          wmin       = '1.8e-006-dxwp_hv18_ms' wmax       = 4.501e-06    
+version    = 4.5                 gbmin      = 1.00e-12            rbsb       = 50    
+rbdb       = 50                  xrcrg1     = 12                  rbpb       = 50    
+xrcrg2     = 1                   rbps       = 50                  rbpd       = 50    
+ngcon      = 1                   binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rgeomod    = 1                   rbodymod   = 0    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxp_hv18_ms+nctx'    
+toxm       = '3.4e-009+nctx'    
+dtox       = 3.1726e-10    
+epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.646e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxlp_hv18_ms'    xw         = '1.5e-08+dxwp_hv18_ms'  dlc        = 'ddlcp_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '-0.47295109+dvthp_hv18_ms+dvths_lod'    
+lvth0      = '-1.8744796e-009+dlvthp_hv18_ms'    
+wvth0      = '-8.2071675e-009+dwvthp_hv18_ms'    
+pvth0      = '1.1729585e-014+dpvthp_hv18_ms'    
+k1         = 0.27581             k2         = '0.013647507+dk2_lod'    
+lk2        = 4.6936395e-009    
+wk2        = 2.7641243e-009      pk2        = -5.3072037e-015     k3         = -3.2349542    
+k3b        = 0.53944             w0         = 1.548e-007          dvt0       = 10.8    
+dvt1       = 0.16                dvt2       = -0.11               dvt0w      = 1.05401    
+dvt1w      = 714044              dvt2w      = 0.112267            dsub       = 0.37    
+minv       = -0.36543            voffl      = 0                   dvtp0      = 5.1e-008    
+dvtp1      = 0.01                lambda     = 0                   vtl        = 0    
+xn         = 3                   lpe0       = 2.3688e-007         lpeb       = 4.3981e-007    
+vbm        = -3                  xj         = 7e-008              ngate      = 3e+021    
+ndep       = 6e+017              nsd        = 1e+020              phin       = 0.15086    
+cdsc       = 2e-005              ud         = 0                   ud1        = 0    
+up         = 0.201021            lp         = 3.05955e-010        cdscb      = -1.0027437e-005    
+cdscd      = 1e-005    
+cit        = '-3.4444444e-005+dcitp_hv18_ms-0.000188963*ff_flagp_hv18_ms'    
+wcit       = '6.0701667e-010+dwcitp_hv18_ms+3.42968e-10*ff_flagp_hv18_ms'    
+voff       = '-0.14564613+dvoffp_hv18_ms'    
+lvoff      = '1.7909826e-008+dlvoffp_hv18_ms'    
+wvoff      = '9.8848464e-009+dwvoffp_hv18_ms'    
+pvoff      = '7.7744611e-015+dpvoffp_hv18_ms'    
+nfactor    = '0.82766+dnfactorp_hv18_ms'    
+eta0       = '0.01+deta0p_hv18_ms+deta0_lod'    
+etab       = -0.09724    
+u0         = '((0.01893988+du0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+lu0        = '((7.2068519e-010+dlu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+wu0        = '((-1.8975044e-009+dwu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+pu0        = '((-1.964561e-015+dpu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+ua         = 2.4845044e-009      lua        = -1.8390482e-017     wua        = 1.0065113e-016    
+pua        = -3.0161789e-022     ub         = 1.4467532e-019      lub        = 5.7652965e-026    
+wub        = 2.6355483e-025      pub        = -9.0283133e-032     uc         = 2.5067e-011    
+eu         = 1                   vsat       = '(131010+dvsatp_hv18_ms)*fvsat_lod'    
+a0         = '0.76942648+da0p_hv18_ms+da0_lod'    
+la0        = '-5.0801273e-007+dla0p_hv18_ms'    
+wa0        = '8.6871195e-006+dwa0p_hv18_ms'    
+pa0        = '3.932011e-013+dpa0p_hv18_ms'    
+ags        = '0.39456736+dagsp_hv18_ms'    
+lags       = '-1.045203e-007+dlagsp_hv18_ms'    
+wags       = '-2.6278723e-007+dwagsp_hv18_ms'    
+pags       = '1.0909091e-013+dpagsp_hv18_ms'    
+a1         = 0                   a2         = 0.80299             b0         = -7e-006    
+b1         = 0                   keta       = -0.0032510581       lketa      = -5.225487e-008    
+wketa      = -1.6294484e-008     pketa      = 3.415447e-014       dwg        = -3.5628e-009    
+dwb        = 6.5366e-009         pclm       = 0.037855193         lpclm      = 1.4415079e-007    
+wpclm      = 2.184916e-007       ppclm      = -8.6671808e-014     pdiblc1    = 0    
+pdiblc2    = '0.0001+dpdiblc2p_hv18_ms'    
+pdiblcb    = 0                   drout      = 0.23168846          pvag       = 9.9607623e-005    
+delta      = 0.0130199           pscbe1     = 2.5512e+008         pscbe2     = 2.3801e-010    
+fprout     = 9.886e-005          pdits      = 9.8993e-007         pditsd     = 0    
+pditsl     = 0                   rsh        = 22.5                rsw        = 249.32    
+rdw        = 2600.4              rdswmin    = 0                   rdwmin     = 0    
+rswmin     = 0                   prwg       = 0                   prwb       = 0    
+wr         = 0.95773321          alpha0     = 4.6919e-008         alpha1     = 0.0070432    
+beta0      = 28                  agidl      = '(1.501e-012)*agidl_wl'    
+bgidl      = 4.609e+009    
+cgidl      = 1.8713              egidl      = 0.046385            aigbacc    = 0.01238    
+bigbacc    = 0.006109            cigbacc    = 0.2809              nigbacc    = 4.05    
+aigbinv    = 0.35                bigbinv    = 0.03                cigbinv    = 0.006    
+eigbinv    = 1.1                 nigbinv    = 1                   aigc       = 0.009898    
+bigc       = 0.001383            cigc       = 1.515e-005          aigsd      = 0.0086    
+bigsd      = 0.0004353           cigsd      = 3.925e-020          nigc       = 1    
+poxedge    = 1                   pigcd      = 1.672               ntox       = 1    
+vfbsdoff   = 0.1                 cgso       = 'cgsop_hv18_ms'          cgdo       = 'cgdop_hv18_ms+cfdsp_hv18_ms'    
+cgbo       = 0                   cgdl       = 'cgdlp_hv18_ms'          cgsl       = 'cgslp_hv18_ms'    
+clc        = 1e-007              cle        = 0.6                 cf         = 'cfsp_hv18_ms'    
+ckappas    = 0.6                 ckappad    = 0.6                 acde       = 0.3    
+moin       = 6.41                noff       = 2.5                 voffcv     = -0.029164    
+tvoff      = 0.0014609           tvfbsdoff  = 0.01015             kt1        = '-0.22995518+dkt1p_hv18_ms'    
+lkt1       = '-2.7569752e-008+dlkt1p_hv18_ms'    
+wkt1       = '-4.663851e-008+dwkt1p_hv18_ms'    
+pkt1       = '-1.7912174e-015+dpkt1p_hv18_ms'    
+kt1l       = 0                   kt2        = -0.040719059        lkt2       = 1.4252507e-008    
+wkt2       = 2.0646748e-008      pkt2       = -9.6436831e-015     ute        = -1.7967174    
+lute       = 1.0860125e-007      wute       = 1.5079917e-006      pute       = -1.8218414e-013    
+ua1        = '-0.0033023226+dua1p_hv18_ms'    
+lua1       = '1.4017663e-009+dlua1p_hv18_ms'    
+wua1       = '1.8202142e-008+dwua1p_hv18_ms'    
+pua1       = '-3.065306e-015+dpua1p_hv18_ms'    
+ub1        = -0.012163792        lub1       = -7.7110897e-009     wub1       = -1.0632687e-007    
+pub1       = 3.2465639e-014      uc1        = 0.020785768         luc1       = -1.3329696e-008    
+wuc1       = -6.3356947e-008     puc1       = 2.3448769e-014      prt        = 0.0013912    
+at         = '0.00016072+datp_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 1.140000e+00    
+noia       = 1.210000e+42    
+noib       = 2.210000e+25    
+noic       = 3.940000e+09    
+lintnoi    = 1.050000e-11    
+jss        = 4.400000e-07    
+jsws       = 2.940000e-13    
+jswgs      = 5.070000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 7.600000e+00    
+xjbvs      = 1    
+jsd        = 1.730000e-07    
+jswd       = 1.080000e-13    
+jswgd      = 8.660000e-14    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.370000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(1e-010)*jtsswg_wl'    
+jtsswgd    = '(1e-010)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 7.8536    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.893               xtsswgd    = 0.893    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 1    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1                   vtsswgd    = 1    
+pbs        = 6.130000e-01    
+cjs        = 'cjsp_hv18_ms'    
+mjs        = 7.230000e-01    
+pbsws      = 9.160000e-01    
+cjsws      = 'cjswsp_hv18_ms'    
+mjsws      = 6.970000e-01    
+pbswgs     = 8.790000e-01    
+cjswgs     = 'cjswgsp_hv18_ms'    
+mjswgs     = 6.060000e-01    
+pbd        = 7.000000e-01    
+cjd        = 'cjdp_hv18_ms'    
+mjd        = 3.250000e-01    
+pbswd      = 5.670000e-01    
+cjswd      = 'cjswdp_hv18_ms'    
+mjswd      = 2.210000e-01    
+pbswgd     = 8.210000e-01    
+cjswgd     = 'cjswgdp_hv18_ms'    
+mjswgd     = 3.850000e-01    
+tpb        = 5.910000e-04    
+tcj        = 5.800000e-04    
+tpbsw      = 1.100000e-03    
+tcjsw      = 6.900000e-04    
+tpbswg     = 1.110000e-03    
+tcjswg     = 1.000000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+rshg       = 'rmainsh'    
+lcit       = '0+dlcitp_hv18_ms+1.27308e-10*ff_flagp_hv18_ms'    
+weta0      = '0+dweta0p_hv18_ms'    
+lnfactor   = '0+dlnfactorp_hv18_ms'  wnfactor   = '0+dwnfactorp_hv18_ms'  pnfactor   = '0+dpnfactorp_hv18_ms'    
+lvsat      = '(0+dlvsatp_hv18_ms)*fvsat_lod'    
+lpdiblc2   = '0+dlpdiblc2p_hv18_ms'  lat        = '0+dlatp_hv18_ms'    
+wpdiblc2   = '0+dwpdiblc2p_hv18_ms'  ppdiblc2   = '0+dppdiblc2p_hv18_ms'    
+pcit       = '0+dpcitp_hv18_ms-2.31064e-16*ff_flagp_hv18_ms'    
+wvsat      = '(0+dwvsatp_hv18_ms)*fvsat_lod'    
+pvsat      = '(0+dpvsatp_hv18_ms)*fvsat_lod'    
+wat        = '0+dwatp_hv18_ms'    
+pat        = '0+dpatp_hv18_ms'    
+lk2we    = -2.0e-11    
+wk2we    = 5.0e-11    
+pk2we    = 0.0e-18    
+k2we     = 0.0006    
+lku0we   = 0.9e-10    
+wku0we   = 0.0e-10    
+pku0we   = 0.5e-17    
+ku0we    = -0.0010    
+lkvth0we = -5.35044e-011    
+wkvth0we = -1.01749e-010    
+pkvth0we = 1.33965e-017    
+kvth0we  = -0.000575476    
+scref    = 1e-6    
+wec      = -7538.6    
+web      = 1041.77 )    
    
.model pch_hv18.2 pmos	(	level      = 54                  lmin       = '5.4e-007-dxlp_hv18_ms'    
+lmax       = '6.3e-007-dxlp_hv18_ms' wmin       = '1.8e-006-dxwp_hv18_ms' wmax       = 4.501e-06    
+version    = 4.5                 gbmin      = 1.00e-12            rbsb       = 50    
+rbdb       = 50                  xrcrg1     = 12                  rbpb       = 50    
+xrcrg2     = 1                   rbps       = 50                  rbpd       = 50    
+ngcon      = 1                   binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rgeomod    = 1                   rbodymod   = 0    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxp_hv18_ms+nctx'    
+toxm       = '3.4e-009+nctx'    
+dtox       = 3.1726e-10    
+epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.646e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxlp_hv18_ms'    xw         = '1.5e-08+dxwp_hv18_ms'  dlc        = 'ddlcp_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '-0.46934889+dvthp_hv18_ms+dvths_lod'    
+lvth0      = '-3.5569948e-009+dlvthp_hv18_ms'    
+wvth0      = '7.1138441e-009+dwvthp_hv18_ms'    
+pvth0      = '4.5734465e-015+dpvthp_hv18_ms'    
+k1         = 0.27581             k2         = '0.0093959259+dk2_lod'    
+lk2        = 6.679468e-009    
+wk2        = 1.699957e-008       pk2        = -1.1956296e-014     k3         = -3.2349542    
+k3b        = 0.53944             w0         = 1.548e-007          dvt0       = 10.8    
+dvt1       = 0.16                dvt2       = -0.11               dvt0w      = 1.05401    
+dvt1w      = 714044              dvt2w      = 0.112267            dsub       = 0.37    
+minv       = -0.36543            voffl      = 0                   dvtp0      = 5.1e-008    
+dvtp1      = 0.01                lambda     = 0                   vtl        = 0    
+xn         = 3                   lpe0       = 2.3688e-007         lpeb       = 4.3981e-007    
+vbm        = -3                  xj         = 7e-008              ngate      = 3e+021    
+ndep       = 6e+017              nsd        = 1e+020              phin       = 0.15086    
+cdsc       = 2e-005              ud         = 0                   ud1        = 0    
+up         = 0.201021            lp         = 3.05955e-010        cdscb      = -1.0027437e-005    
+cdscd      = 1e-005    
+cit        = '-3.4444444e-005+dcitp_hv18_ms+0.000433859*ff_flagp_hv18_ms'    
+wcit       = '6.0701667e-010+dwcitp_hv18_ms-7.87453e-10*ff_flagp_hv18_ms'    
+voff       = '-0.097677719+dvoffp_hv18_ms'    
+lvoff      = '-4.4952599e-009+dlvoffp_hv18_ms'    
+wvoff      = '4.2633789e-009+dwvoffp_hv18_ms'    
+pvoff      = '1.0400136e-014+dpvoffp_hv18_ms'    
+nfactor    = '0.82766+dnfactorp_hv18_ms'    
+eta0       = '0.01+deta0p_hv18_ms+deta0_lod'    
+etab       = -0.09724    
+u0         = '((0.020543428+du0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+lu0        = '((-2.8299836e-011+dlu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+wu0        = '((-6.396028e-009+dwu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+pu0        = '((1.3660944e-016+dpu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+ua         = 2.573322e-009       lua        = -5.9875409e-017     wua        = -4.5990159e-016    
+pua        = -3.9794924e-023     ub         = 2.309573e-019       lub        = 1.7352377e-026    
+wub        = -2.8162174e-026     pub        = 4.5972047e-032      uc         = 2.5067e-011    
+eu         = 1                   vsat       = '(131010+dvsatp_hv18_ms)*fvsat_lod'    
+a0         = '0.094912511+da0p_hv18_ms+da0_lod'    
+la0        = '-1.9296074e-007+dla0p_hv18_ms'    
+wa0        = '8.5319878e-006+dwa0p_hv18_ms'    
+pa0        = '4.6566001e-013+dpa0p_hv18_ms'    
+ags        = '0.22292807+dagsp_hv18_ms'    
+lags       = '-2.4351014e-008+dlagsp_hv18_ms'    
+wags       = '-5.1990074e-008+dwagsp_hv18_ms'    
+pags       = '1.0631778e-014+dpagsp_hv18_ms'    
+a1         = 0                   a2         = 0.80299             b0         = -7e-006    
+b1         = 0                   keta       = -0.041257881        lketa      = -3.4502643e-008    
+wketa      = -2.0423725e-007     pketa      = 1.2193878e-013      dwg        = -3.5628e-009    
+dwb        = 6.5366e-009         pclm       = 0.20698286          lpclm      = 6.5154638e-008    
+wpclm      = -8.0498962e-008     ppclm      = 5.2980705e-014      pdiblc1    = 0    
+pdiblc2    = '0.0001+dpdiblc2p_hv18_ms'    
+pdiblcb    = 0                   drout      = 0.23168846          pvag       = 9.9607623e-005    
+delta      = 0.0130199           pscbe1     = 2.5512e+008         pscbe2     = 2.3801e-010    
+fprout     = 9.886e-005          pdits      = 9.8993e-007         pditsd     = 0    
+pditsl     = 0                   rsh        = 22.5                rsw        = 249.32    
+rdw        = 2600.4              rdswmin    = 0                   rdwmin     = 0    
+rswmin     = 0                   prwg       = 0                   prwb       = 0    
+wr         = 0.95773321          alpha0     = 4.6919e-008         alpha1     = 0.0070432    
+beta0      = 28                  agidl      = '(1.501e-012)*agidl_wl'    
+bgidl      = 4.609e+009    
+cgidl      = 1.8713              egidl      = 0.046385            aigbacc    = 0.01238    
+bigbacc    = 0.006109            cigbacc    = 0.2809              nigbacc    = 4.05    
+aigbinv    = 0.35                bigbinv    = 0.03                cigbinv    = 0.006    
+eigbinv    = 1.1                 nigbinv    = 1                   aigc       = 0.009898    
+bigc       = 0.001383            cigc       = 1.515e-005          aigsd      = 0.0086    
+bigsd      = 0.0004353           cigsd      = 3.925e-020          nigc       = 1    
+poxedge    = 1                   pigcd      = 1.672               ntox       = 1    
+vfbsdoff   = 0.1                 cgso       = 'cgsop_hv18_ms'          cgdo       = 'cgdop_hv18_ms+cfdsp_hv18_ms'    
+cgbo       = 0                   cgdl       = 'cgdlp_hv18_ms'          cgsl       = 'cgslp_hv18_ms'    
+clc        = 1e-007              cle        = 0.6                 cf         = 'cfsp_hv18_ms'    
+ckappas    = 0.6                 ckappad    = 0.6                 acde       = 0.3    
+moin       = 6.41                noff       = 2.5                 voffcv     = -0.029164    
+tvoff      = 0.0014609           tvfbsdoff  = 0.01015             kt1        = '-0.23566302+dkt1p_hv18_ms'    
+lkt1       = '-2.4903734e-008+dlkt1p_hv18_ms'    
+wkt1       = '-7.1200918e-008+dwkt1p_hv18_ms'    
+pkt1       = '9.6813923e-015+dpkt1p_hv18_ms'    
+kt1l       = 0                   kt2        = -0.028671203        lkt2       = 8.6251943e-009    
+wkt2       = -5.3205103e-009     pkt2       = 2.4851039e-015      ute        = -2.3764616    
+lute       = 3.7938821e-007      wute       = 2.1539419e-006      pute       = -4.8389458e-013    
+ua1        = '-0.0084746827+dua1p_hv18_ms'    
+lua1       = '3.8176722e-009+dlua1p_hv18_ms'    
+wua1       = '1.3213393e-008+dwua1p_hv18_ms'    
+pua1       = '-7.3516075e-016+dpua1p_hv18_ms'    
+ub1        = 0.011043383         lub1       = -1.8550697e-008     wub1       = -4.4564413e-008    
+pub1       = 3.6176286e-015      uc1        = -0.02721804         luc1       = 9.0919231e-009    
+wuc1       = 4.6981448e-008      puc1       = -2.8088089e-014     prt        = 0.0013912    
+at         = '0.00016072+datp_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 1.140000e+00    
+noia       = 1.210000e+42    
+noib       = 2.210000e+25    
+noic       = 3.940000e+09    
+lintnoi    = 1.050000e-11    
+jss        = 4.400000e-07    
+jsws       = 2.940000e-13    
+jswgs      = 5.070000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 7.600000e+00    
+xjbvs      = 1    
+jsd        = 1.730000e-07    
+jswd       = 1.080000e-13    
+jswgd      = 8.660000e-14    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.370000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(1e-010)*jtsswg_wl'    
+jtsswgd    = '(1e-010)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 7.8536    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.893               xtsswgd    = 0.893    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 1    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1                   vtsswgd    = 1    
+pbs        = 6.130000e-01    
+cjs        = 'cjsp_hv18_ms'    
+mjs        = 7.230000e-01    
+pbsws      = 9.160000e-01    
+cjsws      = 'cjswsp_hv18_ms'    
+mjsws      = 6.970000e-01    
+pbswgs     = 8.790000e-01    
+cjswgs     = 'cjswgsp_hv18_ms'    
+mjswgs     = 6.060000e-01    
+pbd        = 7.000000e-01    
+cjd        = 'cjdp_hv18_ms'    
+mjd        = 3.250000e-01    
+pbswd      = 5.670000e-01    
+cjswd      = 'cjswdp_hv18_ms'    
+mjswd      = 2.210000e-01    
+pbswgd     = 8.210000e-01    
+cjswgd     = 'cjswgdp_hv18_ms'    
+mjswgd     = 3.850000e-01    
+tpb        = 5.910000e-04    
+tcj        = 5.800000e-04    
+tpbsw      = 1.100000e-03    
+tcjsw      = 6.900000e-04    
+tpbswg     = 1.110000e-03    
+tcjswg     = 1.000000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+rshg       = 'rmainsh'    
+lcit       = '0+dlcitp_hv18_ms-1.63599e-10*ff_flagp_hv18_ms'    
+weta0      = '0+dweta0p_hv18_ms'    
+lnfactor   = '0+dlnfactorp_hv18_ms'  wnfactor   = '0+dwnfactorp_hv18_ms'  pnfactor   = '0+dpnfactorp_hv18_ms'    
+lvsat      = '(0+dlvsatp_hv18_ms)*fvsat_lod'    
+lpdiblc2   = '0+dlpdiblc2p_hv18_ms'  lat        = '0+dlatp_hv18_ms'    
+wpdiblc2   = '0+dwpdiblc2p_hv18_ms'  ppdiblc2   = '0+dppdiblc2p_hv18_ms'    
+pcit       = '0+dpcitp_hv18_ms+2.96933e-16*ff_flagp_hv18_ms'    
+wvsat      = '(0+dwvsatp_hv18_ms)*fvsat_lod'    
+pvsat      = '(0+dpvsatp_hv18_ms)*fvsat_lod'    
+wat        = '0+dwatp_hv18_ms'    
+pat        = '0+dpatp_hv18_ms'    
+lk2we    = -2.0e-11    
+wk2we    = 5.0e-11    
+pk2we    = 0.0e-18    
+k2we     = 0.0006    
+lku0we   = 0.9e-10    
+wku0we   = 0.0e-10    
+pku0we   = 0.5e-17    
+ku0we    = -0.0010    
+lkvth0we = -5.35044e-011    
+wkvth0we = -1.01749e-010    
+pkvth0we = 1.33965e-017    
+kvth0we  = -0.000575476    
+scref    = 1e-6    
+wec      = -7538.6    
+web      = 1041.77 )    
    
.model pch_hv18.3 pmos	(	level      = 54                  lmin       = 0.486e-06    
+lmax       = '5.4e-007-dxlp_hv18_ms' wmin       = '1.8e-006-dxwp_hv18_ms' wmax       = 4.501e-06    
+version    = 4.5                 gbmin      = 1.00e-12            rbsb       = 50    
+rbdb       = 50                  xrcrg1     = 12                  rbpb       = 50    
+xrcrg2     = 1                   rbps       = 50                  rbpd       = 50    
+ngcon      = 1                   binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rgeomod    = 1                   rbodymod   = 0    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxp_hv18_ms+nctx'    
+toxm       = '3.4e-009+nctx'    
+dtox       = 3.1726e-10    
+epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.646e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxlp_hv18_ms'    xw         = '1.5e-08+dxwp_hv18_ms'  dlc        = 'ddlcp_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '-0.50123961+dvthp_hv18_ms+dvths_lod'    
+lvth0      = '8.4683557e-009+dlvthp_hv18_ms'    
+wvth0      = '8.5522016e-008+dwvthp_hv18_ms'    
+pvth0      = '-2.4992707e-014+dpvthp_hv18_ms'    
+k1         = 0.27581             k2         = '0.024623601+dk2_lod'    
+lk2        = 9.374162e-010    
+wk2        = -3.3738427e-008     pk2        = 7.1759882e-015      k3         = -3.2349542    
+k3b        = 0.53944             w0         = 1.548e-007          dvt0       = 10.8    
+dvt1       = 0.16                dvt2       = -0.11               dvt0w      = 1.05401    
+dvt1w      = 714044              dvt2w      = 0.112267            dsub       = 0.37    
+minv       = -0.36543            voffl      = 0                   dvtp0      = 5.1e-008    
+dvtp1      = 0.01                lambda     = 0                   vtl        = 0    
+xn         = 3                   lpe0       = 2.3688e-007         lpeb       = 4.3981e-007    
+vbm        = -3                  xj         = 7e-008              ngate      = 3e+021    
+ndep       = 6e+017              nsd        = 1e+020              phin       = 0.15086    
+cdsc       = 2e-005              ud         = 0                   ud1        = 0    
+up         = 0.201021            lp         = 3.05955e-010        cdscb      = -1.0027437e-005    
+cdscd      = 1e-005    
+cit        = '-0.0016332251+dcitp_hv18_ms-0.0028804*ff_flagp_hv18_ms+0.0018006*ss_flagp_hv18_ms'    
+lcit       = '6.0286821e-010+dlcitp_hv18_ms+1.08614e-09*ff_flagp_hv18_ms-6.78972e-10*ss_flagp_hv18_ms'    
+wcit       = '2.4228958e-009+dwcitp_hv18_ms+4.90215e-09*ff_flagp_hv18_ms-3.2681e-09*ss_flagp_hv18_ms'    
+pcit       = '-6.847317e-016+dpcitp_hv18_ms-1.8485e-15*ff_flagp_hv18_ms+1.23233e-15*ss_flagp_hv18_ms'    
+voff       = '-0.18009714+dvoffp_hv18_ms'    
+lvoff      = '2.6583455e-008+dlvoffp_hv18_ms'    
+wvoff      = '1.7725969e-007+dwvoffp_hv18_ms'    
+pvoff      = '-5.4833314e-014+dpvoffp_hv18_ms'    
+nfactor    = '0.82766+dnfactorp_hv18_ms'    
+eta0       = '0.01+deta0p_hv18_ms+deta0_lod'    
+etab       = -0.09724    
+u0         = '((0.020864151+du0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+lu0        = '((-1.4923808e-010+dlu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+wu0        = '((-6.524033e-009+dwu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+pu0        = '((1.8487756e-016+dpu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+ua         = 3.1283557e-009      lua        = -2.691675e-016      wua        = -1.0303011e-015    
+pua        = 1.7529131e-022      ub         = -2.9245743e-019     lub        = 2.147216e-025    
+wub        = 5.0450558e-025      pub        = -1.5488631e-031     uc         = 2.5067e-011    
+eu         = 1                   vsat       = '(131010+dvsatp_hv18_ms)*fvsat_lod'    
+a0         = '-0.7720994+da0p_hv18_ms+da0_lod'    
+la0        = '1.3397211e-007+dla0p_hv18_ms'    
+wa0        = '1.0366138e-005+dwa0p_hv18_ms'    
+pa0        = '-2.2596146e-013+dpa0p_hv18_ms'    
+ags        = '0.32216441+dagsp_hv18_ms'    
+lags       = '-6.1771055e-008+dlagsp_hv18_ms'    
+wags       = '-1.3262954e-008+dwagsp_hv18_ms'    
+pags       = '-3.9714439e-015+dpagsp_hv18_ms'    
+a1         = 0                   a2         = 0.80299             b0         = -7e-006    
+b1         = 0                   keta       = -0.25363613         lketa      = 4.5580948e-008    
+wketa      = 3.3537405e-007      pketa      = -8.153785e-014      dwg        = -3.5628e-009    
+dwb        = 6.5366e-009         pclm       = 0.25614055          lpclm      = 4.6618257e-008    
+wpclm      = -2.3326088e-007     ppclm      = 1.1058417e-013      pdiblc1    = 0    
+pdiblc2    = '0.0001+dpdiblc2p_hv18_ms'    
+pdiblcb    = 0                   drout      = 0.23168846          pvag       = 9.9607623e-005    
+delta      = 0.0130199           pscbe1     = 2.5512e+008         pscbe2     = 2.3801e-010    
+fprout     = 9.886e-005          pdits      = 9.8993e-007         pditsd     = 0    
+pditsl     = 0                   rsh        = 22.5                rsw        = 249.32    
+rdw        = 2600.4              rdswmin    = 0                   rdwmin     = 0    
+rswmin     = 0                   prwg       = 0                   prwb       = 0    
+wr         = 0.95773321          alpha0     = 4.6919e-008         alpha1     = 0.0070432    
+beta0      = 28                  agidl      = '(1.501e-012)*agidl_wl'    
+bgidl      = 4.609e+009    
+cgidl      = 1.8713              egidl      = 0.046385            aigbacc    = 0.01238    
+bigbacc    = 0.006109            cigbacc    = 0.2809              nigbacc    = 4.05    
+aigbinv    = 0.35                bigbinv    = 0.03                cigbinv    = 0.006    
+eigbinv    = 1.1                 nigbinv    = 1                   aigc       = 0.009898    
+bigc       = 0.001383            cigc       = 1.515e-005          aigsd      = 0.0086    
+bigsd      = 0.0004353           cigsd      = 3.925e-020          nigc       = 1    
+poxedge    = 1                   pigcd      = 1.672               ntox       = 1    
+vfbsdoff   = 0.1                 cgso       = 'cgsop_hv18_ms'          cgdo       = 'cgdop_hv18_ms+cfdsp_hv18_ms'    
+cgbo       = 0                   cgdl       = 'cgdlp_hv18_ms'          cgsl       = 'cgslp_hv18_ms'    
+clc        = 1e-007              cle        = 0.6                 cf         = 'cfsp_hv18_ms'    
+ckappas    = 0.6                 ckappad    = 0.6                 acde       = 0.3    
+moin       = 6.41                noff       = 2.5                 voffcv     = -0.029164    
+tvoff      = 0.0014609           tvfbsdoff  = 0.01015             kt1        = '-0.15163396+dkt1p_hv18_ms'    
+lkt1       = '-5.6589412e-008+dlkt1p_hv18_ms'    
+wkt1       = '-3.1790833e-007+dwkt1p_hv18_ms'    
+pkt1       = '1.0270982e-013+dpkt1p_hv18_ms'    
+kt1l       = 0                   kt2        = -0.0084052787       lkt2       = 9.8331941e-010    
+wkt2       = 8.8675171e-009      pkt2       = -2.8649174e-015     ute        = -5.014658    
+lute       = 1.3741993e-006      wute       = 7.1438095e-006      pute       = -2.3654738e-012    
+ua1        = '-0.023780536+dua1p_hv18_ms'    
+lua1       = '9.5892035e-009+dlua1p_hv18_ms'    
+wua1       = '5.4502317e-008+dwua1p_hv18_ms'    
+pua1       = '-1.6304388e-014+dpua1p_hv18_ms'    
+ub1        = -0.081231484        lub1       = 1.624431e-008       wub1       = -4.2490671e-008    
+pub1       = 2.8356619e-015      uc1        = -0.031944628        luc1       = 1.0874225e-008    
+wuc1       = -1.7103789e-008     puc1       = -3.9228279e-015     prt        = 0.0013912    
+at         = '0.00016072+datp_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 1.140000e+00    
+noia       = 1.210000e+42    
+noib       = 2.210000e+25    
+noic       = 3.940000e+09    
+lintnoi    = 1.050000e-11    
+jss        = 4.400000e-07    
+jsws       = 2.940000e-13    
+jswgs      = 5.070000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 7.600000e+00    
+xjbvs      = 1    
+jsd        = 1.730000e-07    
+jswd       = 1.080000e-13    
+jswgd      = 8.660000e-14    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.370000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(1e-010)*jtsswg_wl'    
+jtsswgd    = '(1e-010)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 7.8536    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.893               xtsswgd    = 0.893    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 1    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1                   vtsswgd    = 1    
+pbs        = 6.130000e-01    
+cjs        = 'cjsp_hv18_ms'    
+mjs        = 7.230000e-01    
+pbsws      = 9.160000e-01    
+cjsws      = 'cjswsp_hv18_ms'    
+mjsws      = 6.970000e-01    
+pbswgs     = 8.790000e-01    
+cjswgs     = 'cjswgsp_hv18_ms'    
+mjswgs     = 6.060000e-01    
+pbd        = 7.000000e-01    
+cjd        = 'cjdp_hv18_ms'    
+mjd        = 3.250000e-01    
+pbswd      = 5.670000e-01    
+cjswd      = 'cjswdp_hv18_ms'    
+mjswd      = 2.210000e-01    
+pbswgd     = 8.210000e-01    
+cjswgd     = 'cjswgdp_hv18_ms'    
+mjswgd     = 3.850000e-01    
+tpb        = 5.910000e-04    
+tcj        = 5.800000e-04    
+tpbsw      = 1.100000e-03    
+tcjsw      = 6.900000e-04    
+tpbswg     = 1.110000e-03    
+tcjswg     = 1.000000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+rshg       = 'rmainsh'    
+weta0      = '0+dweta0p_hv18_ms'     lnfactor   = '0+dlnfactorp_hv18_ms'    
+wnfactor   = '0+dwnfactorp_hv18_ms'  pnfactor   = '0+dpnfactorp_hv18_ms'  lvsat      = '(0+dlvsatp_hv18_ms)*fvsat_lod'    
+lpdiblc2   = '0+dlpdiblc2p_hv18_ms'  lat        = '0+dlatp_hv18_ms'       wpdiblc2   = '0+dwpdiblc2p_hv18_ms'    
+ppdiblc2   = '0+dppdiblc2p_hv18_ms'  wvsat      = '(0+dwvsatp_hv18_ms)*fvsat_lod'    
+pvsat      = '(0+dpvsatp_hv18_ms)*fvsat_lod'    
+wat        = '0+dwatp_hv18_ms'       pat        = '0+dpatp_hv18_ms'    
+lk2we    = -2.0e-11    
+wk2we    = 5.0e-11    
+pk2we    = 0.0e-18    
+k2we     = 0.0006    
+lku0we   = 0.9e-10    
+wku0we   = 0.0e-10    
+pku0we   = 0.5e-17    
+ku0we    = -0.0010    
+lkvth0we = -5.35044e-011    
+wkvth0we = -1.01749e-010    
+pkvth0we = 1.33965e-017    
+kvth0we  = -0.000575476    
+scref    = 1e-6    
+wec      = -7538.6    
+web      = 1041.77 )    
    
.model pch_hv18.4 pmos	(	level      = 54                  lmin       = '6.3e-007-dxlp_hv18_ms'    
+lmax       = 1.0801e-06          wmin       = 0.9e-06             wmax       = '1.8e-006-dxwp_hv18_ms'    
+version    = 4.5                 gbmin      = 1.00e-12            rbsb       = 50    
+rbdb       = 50                  xrcrg1     = 12                  rbpb       = 50    
+xrcrg2     = 1                   rbps       = 50                  rbpd       = 50    
+ngcon      = 1                   binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rgeomod    = 1                   rbodymod   = 0    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxp_hv18_ms+nctx'    
+toxm       = '3.4e-009+nctx'    
+dtox       = 3.1726e-10    
+epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.646e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxlp_hv18_ms'    xw         = '1.5e-08+dxwp_hv18_ms'  dlc        = 'ddlcp_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '-0.49266432+dvthp_hv18_ms+dvths_lod'    
+lvth0      = '1.5880669e-009+dlvthp_hv18_ms'    
+wvth0      = '2.7572349e-008+dwvthp_hv18_ms'    
+pvth0      = '5.4450627e-015+dpvthp_hv18_ms'    
+k1         = 0.27581             k2         = '0.016345528+dk2_lod'    
+lk2        = 2.4624715e-009    
+wk2        = -2.1327839e-009     pk2        = -1.2576338e-015     k3         = -3.2349542    
+k3b        = 0.53944             w0         = 1.548e-007          dvt0       = 10.8    
+dvt1       = 0.16                dvt2       = -0.11               dvt0w      = 1.05401    
+dvt1w      = 714044              dvt2w      = 0.112267            dsub       = 0.37    
+minv       = -0.36543            voffl      = 0                   dvtp0      = 5.1e-008    
+dvtp1      = 0.01                lambda     = 0                   vtl        = 0    
+xn         = 3                   lpe0       = 2.3688e-007         lpeb       = 4.3981e-007    
+vbm        = -3                  xj         = 7e-008              ngate      = 3e+021    
+ndep       = 6e+017              nsd        = 1e+020              phin       = 0.15086    
+cdsc       = 2e-005              ud         = 0                   ud1        = 0    
+up         = 0.201021            lp         = 3.05955e-010        cdscb      = -1.0027437e-005    
+cdscd      = 1e-005              cit        = '0.00010052548+dcitp_hv18_ms'    
+lcit       = '-9.6775309e-011+dlcitp_hv18_ms'    
+wcit       = '3.6204625e-010+dwcitp_hv18_ms'    
+pcit       = '1.7564718e-016+dpcitp_hv18_ms'    
+voff       = '-0.15904251+dvoffp_hv18_ms'    
+lvoff      = '2.6035255e-008+dlvoffp_hv18_ms'    
+wvoff      = '3.419928e-008+dwvoffp_hv18_ms'    
+pvoff      = '-6.9731932e-015+dpvoffp_hv18_ms'    
+nfactor    = '0.82766+dnfactorp_hv18_ms'    
+eta0       = '0.01+deta0p_hv18_ms+deta0_lod'    
+etab       = -0.09724    
+u0         = '((0.019415328+du0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+lu0        = '((-4.884932e-010+dlu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+wu0        = '((-2.7604427e-009+dwu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+pu0        = '((2.3009781e-016+dpu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+ua         = 2.7274004e-009      lua        = -2.6789468e-016     wua        = -3.40205e-016    
+pua        = 1.5123223e-022      ub         = 2.1762304e-019      lub        = 2.8484622e-026    
+wub        = 1.3115471e-025      pub        = -3.7342591e-032     uc         = 2.5067e-011    
+eu         = 1                   vsat       = '(131010+dvsatp_hv18_ms)*fvsat_lod'    
+a0         = '0.4706068+da0p_hv18_ms+da0_lod'    
+la0        = '-5.2469827e-007+dla0p_hv18_ms'    
+wa0        = '9.2294772e-006+dwa0p_hv18_ms'    
+pa0        = '4.2348536e-013+dpa0p_hv18_ms'    
+ags        = '0.29378951+dagsp_hv18_ms'    
+lags       = '-6.5502447e-008+dlagsp_hv18_ms'    
+wags       = '-7.9875432e-008+dwagsp_hv18_ms'    
+pags       = '3.8273522e-014+dpagsp_hv18_ms'    
+a1         = 0                   a2         = 0.80299             b0         = -7e-006    
+b1         = 0                   keta       = -0.01234364         lketa      = -4.3482257e-008    
+wketa      = 2.0855262e-010      pketa      = 1.8232178e-014      dwg        = -3.5628e-009    
+dwb        = 6.5366e-009         pclm       = 0.027409254         lpclm      = 1.5382419e-007    
+wpclm      = 2.3745098e-007      ppclm      = -1.0422904e-013     pdiblc1    = 0    
+pdiblc2    = '0.0001+dpdiblc2p_hv18_ms'    
+pdiblcb    = 0                   drout      = 0.23168846          pvag       = 9.9607623e-005    
+delta      = 0.0130199           pscbe1     = 2.5512e+008         pscbe2     = 2.3801e-010    
+fprout     = 9.886e-005          pdits      = 9.8993e-007         pditsd     = 0    
+pditsl     = 0                   rsh        = 22.5                rsw        = 249.32    
+rdw        = 2600.4              rdswmin    = 0                   rdwmin     = 0    
+rswmin     = 0                   prwg       = 0                   prwb       = 0    
+wr         = 0.95773321          alpha0     = 4.6919e-008         alpha1     = 0.0070432    
+beta0      = 28                  agidl      = '(1.501e-012)*agidl_wl'    
+bgidl      = 4.609e+009    
+cgidl      = 1.8713              egidl      = 0.046385            aigbacc    = 0.01238    
+bigbacc    = 0.006109            cigbacc    = 0.2809              nigbacc    = 4.05    
+aigbinv    = 0.35                bigbinv    = 0.03                cigbinv    = 0.006    
+eigbinv    = 1.1                 nigbinv    = 1                   aigc       = 0.009898    
+bigc       = 0.001383            cigc       = 1.515e-005          aigsd      = 0.0086    
+bigsd      = 0.0004353           cigsd      = 3.925e-020          nigc       = 1    
+poxedge    = 1                   pigcd      = 1.672               ntox       = 1    
+vfbsdoff   = 0.1                 cgso       = 'cgsop_hv18_ms'          cgdo       = 'cgdop_hv18_ms+cfdsp_hv18_ms'    
+cgbo       = 0                   cgdl       = 'cgdlp_hv18_ms'          cgsl       = 'cgslp_hv18_ms'    
+clc        = 1e-007              cle        = 0.6                 cf         = 'cfsp_hv18_ms'    
+ckappas    = 0.6                 ckappad    = 0.6                 acde       = 0.3    
+moin       = 6.41                noff       = 2.5                 voffcv     = -0.029164    
+tvoff      = 0.0026977           wtvoff     = -2.24478e-009       tvfbsdoff  = 0.01015    
+kt1        = '-0.20840423+dkt1p_hv18_ms'    
+lkt1       = '-3.9840649e-008+dlkt1p_hv18_ms'    
+wkt1       = '-8.5753495e-008+dwkt1p_hv18_ms'    
+pkt1       = '2.0480462e-014+dpkt1p_hv18_ms'    
+kt1l       = 0                   kt2        = -0.023053087        lkt2       = 6.0010845e-009    
+wkt2       = -1.1416992e-008     pkt2       = 5.3326485e-015      ute        = -0.93057989    
+lute       = -1.1389642e-007     wute       = -6.4047835e-008     pute       = 2.2164914e-013    
+ua1        = '0.0054363355+dua1p_hv18_ms'    
+lua1       = '-5.2573607e-010+dlua1p_hv18_ms'    
+wua1       = '2.341478e-009+dwua1p_hv18_ms'    
+pua1       = '4.3311078e-016+dpua1p_hv18_ms'    
+ub1        = -0.073631305        lub1       = 1.0854381e-008      wub1       = 5.236663e-009    
+pub1       = -1.2306906e-015     uc1        = -0.013228643        luc1       = -8.2736543e-010    
+wuc1       = -1.6207917e-009     puc1       = 7.5703937e-016      prt        = 0.0013912    
+at         = '0.00016072+datp_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 1.140000e+00    
+noia       = 1.210000e+42    
+noib       = 2.210000e+25    
+noic       = 3.940000e+09    
+lintnoi    = 1.050000e-11    
+jss        = 4.400000e-07    
+jsws       = 2.940000e-13    
+jswgs      = 5.070000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 7.600000e+00    
+xjbvs      = 1    
+jsd        = 1.730000e-07    
+jswd       = 1.080000e-13    
+jswgd      = 8.660000e-14    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.370000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(1e-010)*jtsswg_wl'    
+jtsswgd    = '(1e-010)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 7.8536    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.893               xtsswgd    = 0.893    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 1    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1                   vtsswgd    = 1    
+pbs        = 6.130000e-01    
+cjs        = 'cjsp_hv18_ms'    
+mjs        = 7.230000e-01    
+pbsws      = 9.160000e-01    
+cjsws      = 'cjswsp_hv18_ms'    
+mjsws      = 6.970000e-01    
+pbswgs     = 8.790000e-01    
+cjswgs     = 'cjswgsp_hv18_ms'    
+mjswgs     = 6.060000e-01    
+pbd        = 7.000000e-01    
+cjd        = 'cjdp_hv18_ms'    
+mjd        = 3.250000e-01    
+pbswd      = 5.670000e-01    
+cjswd      = 'cjswdp_hv18_ms'    
+mjswd      = 2.210000e-01    
+pbswgd     = 8.210000e-01    
+cjswgd     = 'cjswgdp_hv18_ms'    
+mjswgd     = 3.850000e-01    
+tpb        = 5.910000e-04    
+tcj        = 5.800000e-04    
+tpbsw      = 1.100000e-03    
+tcjsw      = 6.900000e-04    
+tpbswg     = 1.110000e-03    
+tcjswg     = 1.000000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+rshg       = 'rmainsh'    
+weta0      = '0+dweta0p_hv18_ms'     lnfactor   = '0+dlnfactorp_hv18_ms'    
+wnfactor   = '0+dwnfactorp_hv18_ms'  pnfactor   = '0+dpnfactorp_hv18_ms'  lvsat      = '(0+dlvsatp_hv18_ms)*fvsat_lod'    
+lpdiblc2   = '0+dlpdiblc2p_hv18_ms'  lat        = '0+dlatp_hv18_ms'       wpdiblc2   = '0+dwpdiblc2p_hv18_ms'    
+ppdiblc2   = '0+dppdiblc2p_hv18_ms'  wvsat      = '(0+dwvsatp_hv18_ms)*fvsat_lod'    
+pvsat      = '(0+dpvsatp_hv18_ms)*fvsat_lod'    
+wat        = '0+dwatp_hv18_ms'       pat        = '0+dpatp_hv18_ms'    
+lk2we    = -2.0e-11    
+wk2we    = 5.0e-11    
+pk2we    = 0.0e-18    
+k2we     = 0.0006    
+lku0we   = 0.9e-10    
+wku0we   = 0.0e-10    
+pku0we   = 0.5e-17    
+ku0we    = -0.0010    
+lkvth0we = -5.35044e-011    
+wkvth0we = -1.01749e-010    
+pkvth0we = 1.33965e-017    
+kvth0we  = -0.000575476    
+scref    = 1e-6    
+wec      = -7538.6    
+web      = 1041.77 )    
    
.model pch_hv18.5 pmos	(	level      = 54                  lmin       = '5.4e-007-dxlp_hv18_ms'    
+lmax       = '6.3e-007-dxlp_hv18_ms' wmin       = 0.9e-06             wmax       = '1.8e-006-dxwp_hv18_ms'    
+version    = 4.5                 gbmin      = 1.00e-12            rbsb       = 50    
+rbdb       = 50                  xrcrg1     = 12                  rbpb       = 50    
+xrcrg2     = 1                   rbps       = 50                  rbpd       = 50    
+ngcon      = 1                   binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rgeomod    = 1                   rbodymod   = 0    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxp_hv18_ms+nctx'    
+toxm       = '3.4e-009+nctx'    
+dtox       = 3.1726e-10    
+epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.646e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxlp_hv18_ms'    xw         = '1.5e-08+dxwp_hv18_ms'  dlc        = 'ddlcp_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '-0.49262384+dvthp_hv18_ms+dvths_lod'    
+lvth0      = '1.5691569e-009+dlvthp_hv18_ms'    
+wvth0      = '4.9357871e-008+dwvthp_hv18_ms'    
+pvth0      = '-4.7305188e-015+dpvthp_hv18_ms'    
+k1         = 0.27581             k2         = '0.022370556+dk2_lod'    
+lk2        = -3.5169858e-010    
+wk2        = -6.5493836e-009     pk2        = 8.0527152e-016      k3         = -3.2349542    
+k3b        = 0.53944             w0         = 1.548e-007          dvt0       = 10.8    
+dvt1       = 0.16                dvt2       = -0.11               dvt0w      = 1.05401    
+dvt1w      = 714044              dvt2w      = 0.112267            dsub       = 0.37    
+minv       = -0.36543            voffl      = 0                   dvtp0      = 5.1e-008    
+dvtp1      = 0.01                lambda     = 0                   vtl        = 0    
+xn         = 3                   lpe0       = 2.3688e-007         lpeb       = 4.3981e-007    
+vbm        = -3                  xj         = 7e-008              ngate      = 3e+021    
+ndep       = 6e+017              nsd        = 1e+020              phin       = 0.15086    
+cdsc       = 2e-005              ud         = 0                   ud1        = 0    
+up         = 0.201021            lp         = 3.05955e-010        cdscb      = -1.0027437e-005    
+cdscd      = 1e-005              cit        = '-0.00010666667+dcitp_hv18_ms'    
+wcit       = '7.381e-010+dwcitp_hv18_ms'    
+voff       = '-0.10411843+dvoffp_hv18_ms'    
+lvoff      = '3.8131393e-010+dlvoffp_hv18_ms'    
+wvoff      = '1.5953266e-008+dwvoffp_hv18_ms'    
+pvoff      = '1.5491546e-015+dpvoffp_hv18_ms'    
+nfactor    = '0.82766+dnfactorp_hv18_ms'    
+eta0       = '0.01+deta0p_hv18_ms+deta0_lod'    
+etab       = -0.09724    
+u0         = '((0.017076238+du0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+lu0        = '((6.0404871e-10+dlu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+wu0        = '((-1.030798e-10+dwu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+pu0        = '((-1.0111033e-15+dpu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+ua         = 2.0853315e-009      lua        = 3.2002842e-017      wua        = 4.258012e-016    
+pua        = -2.0655395e-022     ub         = 1.8492826e-019      lub        = 4.37557e-026    
+wub        = 5.5380529e-026      pub        = -1.9499848e-033     uc         = 2.5067e-011    
+eu         = 1                   vsat       = '(131010+dvsatp_hv18_ms)*fvsat_lod'    
+a0         = '-1.1573755+da0p_hv18_ms+da0_lod'    
+la0        = '2.3569969e-007+dla0p_hv18_ms'    
+wa0        = '1.080489e-005+dwa0p_hv18_ms'    
+pa0        = '-3.1235868e-013+dpa0p_hv18_ms'    
+ags        = '0.12375573+dagsp_hv18_ms'    
+lags       = '1.3916931e-008+dlagsp_hv18_ms'    
+wags       = '1.2800772e-007+dwagsp_hv18_ms'    
+pags       = '-5.8824543e-014+dpagsp_hv18_ms'    
+a1         = 0                   a2         = 0.80299             b0         = -7e-006    
+b1         = 0                   keta       = -0.19441737         lketa      = 4.1560739e-008    
+wketa      = 7.3747221e-008      pketa      = -1.6116264e-014     dwg        = -3.5628e-009    
+dwb        = 6.5366e-009         pclm       = 0.1650599           lpclm      = 8.9530332e-008    
+wpclm      = -4.4087861e-009     ppclm      = 8.7388209e-015      pdiblc1    = 0    
+pdiblc2    = '0.0001+dpdiblc2p_hv18_ms'    
+pdiblcb    = 0                   drout      = 0.23168846          pvag       = 9.9607623e-005    
+delta      = 0.0130199           pscbe1     = 2.5512e+008         pscbe2     = 2.3801e-010    
+fprout     = 9.886e-005          pdits      = 9.8993e-007         pditsd     = 0    
+pditsl     = 0                   rsh        = 22.5                rsw        = 249.32    
+rdw        = 2600.4              rdswmin    = 0                   rdwmin     = 0    
+rswmin     = 0                   prwg       = 0                   prwb       = 0    
+wr         = 0.95773321          alpha0     = 4.6919e-008         alpha1     = 0.0070432    
+beta0      = 28                  agidl      = '(1.501e-012)*agidl_wl'    
+bgidl      = 4.609e+009    
+cgidl      = 1.8713              egidl      = 0.046385            aigbacc    = 0.01238    
+bigbacc    = 0.006109            cigbacc    = 0.2809              nigbacc    = 4.05    
+aigbinv    = 0.35                bigbinv    = 0.03                cigbinv    = 0.006    
+eigbinv    = 1.1                 nigbinv    = 1                   aigc       = 0.009898    
+bigc       = 0.001383            cigc       = 1.515e-005          aigsd      = 0.0086    
+bigsd      = 0.0004353           cigsd      = 3.925e-020          nigc       = 1    
+poxedge    = 1                   pigcd      = 1.672               ntox       = 1    
+vfbsdoff   = 0.1                 cgso       = 'cgsop_hv18_ms'          cgdo       = 'cgdop_hv18_ms+cfdsp_hv18_ms'    
+cgbo       = 0                   cgdl       = 'cgdlp_hv18_ms'          cgsl       = 'cgslp_hv18_ms'    
+clc        = 1e-007              cle        = 0.6                 cf         = 'cfsp_hv18_ms'    
+ckappas    = 0.6                 ckappad    = 0.6                 acde       = 0.3    
+moin       = 6.41                noff       = 2.5                 voffcv     = -0.029164    
+tvoff      = 0.0026977           wtvoff     = -2.24478e-009       tvfbsdoff  = 0.01015    
+kt1        = '-0.2218586+dkt1p_hv18_ms'    
+lkt1       = '-3.3556383e-008+dlkt1p_hv18_ms'    
+wkt1       = '-9.6255952e-008+dwkt1p_hv18_ms'    
+pkt1       = '2.538595e-014+dpkt1p_hv18_ms'    
+kt1l       = 0                   kt2        = -0.053356855        lkt2       = 2.0155368e-008    
+wkt2       = 3.9483947e-008      pkt2       = -1.8442162e-014     ute        = -2.4899443    
+lute       = 6.1445152e-007      wute       = 2.359913e-006       pute       = -9.1053448e-013    
+ua1        = '-0.014648995+dua1p_hv18_ms'    
+lua1       = '8.8557198e-009+dlua1p_hv18_ms'    
+wua1       = '2.4419769e-008+dwua1p_hv18_ms'    
+pua1       = '-9.8792172e-015+dpua1p_hv18_ms'    
+ub1        = 0.027240752         lub1       = -3.6260939e-008     wub1       = -7.3962638e-008    
+pub1       = 3.5761719e-014      uc1        = 0.012561894         luc1       = -1.287361e-008    
+wuc1       = -2.5219133e-008     puc1       = 1.1779353e-014      prt        = 0.0013912    
+at         = '0.00016072+datp_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 1.140000e+00    
+noia       = 1.210000e+42    
+noib       = 2.210000e+25    
+noic       = 3.940000e+09    
+lintnoi    = 1.050000e-11    
+jss        = 4.400000e-07    
+jsws       = 2.940000e-13    
+jswgs      = 5.070000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 7.600000e+00    
+xjbvs      = 1    
+jsd        = 1.730000e-07    
+jswd       = 1.080000e-13    
+jswgd      = 8.660000e-14    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.370000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(1e-010)*jtsswg_wl'    
+jtsswgd    = '(1e-010)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 7.8536    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.893               xtsswgd    = 0.893    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 1    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1                   vtsswgd    = 1    
+pbs        = 6.130000e-01    
+cjs        = 'cjsp_hv18_ms'    
+mjs        = 7.230000e-01    
+pbsws      = 9.160000e-01    
+cjsws      = 'cjswsp_hv18_ms'    
+mjsws      = 6.970000e-01    
+pbswgs     = 8.790000e-01    
+cjswgs     = 'cjswgsp_hv18_ms'    
+mjswgs     = 6.060000e-01    
+pbd        = 7.000000e-01    
+cjd        = 'cjdp_hv18_ms'    
+mjd        = 3.250000e-01    
+pbswd      = 5.670000e-01    
+cjswd      = 'cjswdp_hv18_ms'    
+mjswd      = 2.210000e-01    
+pbswgd     = 8.210000e-01    
+cjswgd     = 'cjswgdp_hv18_ms'    
+mjswgd     = 3.850000e-01    
+tpb        = 5.910000e-04    
+tcj        = 5.800000e-04    
+tpbsw      = 1.100000e-03    
+tcjsw      = 6.900000e-04    
+tpbswg     = 1.110000e-03    
+tcjswg     = 1.000000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+rshg       = 'rmainsh'    
+lcit       = '0+dlcitp_hv18_ms'      weta0      = '0+dweta0p_hv18_ms'    
+lnfactor   = '0+dlnfactorp_hv18_ms'  wnfactor   = '0+dwnfactorp_hv18_ms'  pnfactor   = '0+dpnfactorp_hv18_ms'    
+lvsat      = '(0+dlvsatp_hv18_ms)*fvsat_lod'    
+lpdiblc2   = '0+dlpdiblc2p_hv18_ms'  lat        = '0+dlatp_hv18_ms'    
+wpdiblc2   = '0+dwpdiblc2p_hv18_ms'  ppdiblc2   = '0+dppdiblc2p_hv18_ms'  pcit       = '0+dpcitp_hv18_ms'    
+wvsat      = '(0+dwvsatp_hv18_ms)*fvsat_lod'    
+pvsat      = '(0+dpvsatp_hv18_ms)*fvsat_lod'    
+wat        = '0+dwatp_hv18_ms'    
+pat        = '0+dpatp_hv18_ms'    
+lk2we    = -2.0e-11    
+wk2we    = 5.0e-11    
+pk2we    = 0.0e-18    
+k2we     = 0.0006    
+lku0we   = 0.9e-10    
+wku0we   = 0.0e-10    
+pku0we   = 0.5e-17    
+ku0we    = -0.0010    
+lkvth0we = -5.35044e-011    
+wkvth0we = -1.01749e-010    
+pkvth0we = 1.33965e-017    
+kvth0we  = -0.000575476    
+scref    = 1e-6    
+wec      = -7538.6    
+web      = 1041.77 )    
    
.model pch_hv18.6 pmos	(	level      = 54                  lmin       = 0.486e-06    
+lmax       = '5.4e-007-dxlp_hv18_ms' wmin       = 0.9e-06             wmax       = '1.8e-006-dxwp_hv18_ms'    
+version    = 4.5                 gbmin      = 1.00e-12            rbsb       = 50    
+rbdb       = 50                  xrcrg1     = 12                  rbpb       = 50    
+xrcrg2     = 1                   rbps       = 50                  rbpd       = 50    
+ngcon      = 1                   binunit    = 2                   paramchk   = 1    
+mobmod     = 0                   capmod     = 2                   igcmod     = 0    
+igbmod     = 0                   geomod     = 0                   diomod     = 1    
+rdsmod     = 1                   rgeomod    = 1                   rbodymod   = 0    
+rgatemod   = '1*_rgflag'    
+permod     = 1                   acnqsmod   = 0    
+trnqsmod   = 0                   tempmod    = 1                   wpemod     = '1*wpeflag'    
+tnom       = 25                  toxe       = 'toxp_hv18_ms+nctx'    
+toxm       = '3.4e-009+nctx'    
+dtox       = 3.1726e-10    
+epsrox     = 3.9                 toxref     = 3e-009    
+wint       = 0                   lint       = 8.646e-008          ll         = 0    
+wl         = 0                   lln        = 1                   wln        = 1    
+lw         = 0                   ww         = 0                   lwn        = 1    
+wwn        = 1                   lwl        = 0                   wwl        = 0    
+llc        = 0                   wlc        = 0                   lwc        = 0    
+wwc        = 0                   lwlc       = 0                   wwlc       = 0    
+xl         = '1e-08+dxlp_hv18_ms'    xw         = '1.5e-08+dxwp_hv18_ms'  dlc        = 'ddlcp_hv18_ms'    
+dwc        = 0                   dlcig      = 2.5e-009            xpart      = 1    
+vth0       = '-0.49161652+dvthp_hv18_ms+dvths_lod'    
+lvth0      = '1.1893174e-009+dlvthp_hv18_ms'    
+wvth0      = '6.8056114e-008+dwvthp_hv18_ms'    
+pvth0      = '-1.1781252e-014+dpvthp_hv18_ms'    
+k1         = 0.27581             k2         = '0.013478931+dk2_lod'    
+lk2        = 3.0011557e-009    
+wk2        = -1.3510849e-008     pk2        = 3.4303011e-015      k3         = -3.2349542    
+k3b        = 0.53944             w0         = 1.548e-007          dvt0       = 10.8    
+dvt1       = 0.16                dvt2       = -0.11               dvt0w      = 1.05401    
+dvt1w      = 714044              dvt2w      = 0.112267            dsub       = 0.37    
+minv       = -0.36543            voffl      = 0                   dvtp0      = 5.1e-008    
+dvtp1      = 0.01                lambda     = 0                   vtl        = 0    
+xn         = 3                   lpe0       = 2.3688e-007         lpeb       = 4.3981e-007    
+vbm        = -3                  xj         = 7e-008              ngate      = 3e+021    
+ndep       = 6e+017              nsd        = 1e+020              phin       = 0.15086    
+cdsc       = 2e-005              ud         = 0                   ud1        = 0    
+up         = 0.201021            lp         = 3.05955e-010        cdscb      = -1.0027437e-005    
+cdscd      = 1e-005    
+cit        = '-0.0013132309+dcitp_hv18_ms-0.000361969*ff_flagp_hv18_ms'    
+lcit       = '4.5497123e-010+dlcitp_hv18_ms+1.36491e-10*ff_flagp_hv18_ms'    
+wcit       = '1.8421062e-009+dwcitp_hv18_ms+3.31202e-10*ff_flagp_hv18_ms'    
+pcit       = '-4.1629867e-016+dpcitp_hv18_ms-1.2489e-16*ff_flagp_hv18_ms'    
+voff       = '-0.12522602+dvoffp_hv18_ms'    
+lvoff      = '8.3405626e-009+dlvoffp_hv18_ms'    
+wvoff      = '7.7668604e-008+dwvoffp_hv18_ms'    
+pvoff      = '-2.1722465e-014+dpvoffp_hv18_ms'    
+nfactor    = '0.82766+dnfactorp_hv18_ms'    
+eta0       = '0.01+deta0p_hv18_ms+deta0_lod'    
+etab       = -0.09724    
+u0         = '((0.016644441+du0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+lu0        = '((7.6687092e-10+dlu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+wu0        = '((1.1347399e-09+dwu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+pu0        = '((-1.4778603e-15+dpu0p_hv18_ms)*fu0_lod)*fu0p_hv18_ms_local'    
+ua         = 2.3213313e-009      lua        = -5.6987966e-017     wua        = 4.3444812e-016    
+pua        = -2.0981453e-022     ub         = -2.5699665e-019     lub        = 2.1039674e-025    
+wub        = 4.4014426e-025      pub        = -1.4703669e-031     uc         = 2.5067e-011    
+eu         = 1                   vsat       = '(131010+dvsatp_hv18_ms)*fvsat_lod'    
+a0         = '-0.18152888+da0p_hv18_ms+da0_lod'    
+la0        = '-1.3227254e-007+dla0p_hv18_ms'    
+wa0        = '9.2942528e-006+dwa0p_hv18_ms'    
+pa0        = '2.5727258e-013+dpa0p_hv18_ms'    
+ags        = '0.29262805+dagsp_hv18_ms'    
+lags       = '-4.9761444e-008+dlagsp_hv18_ms'    
+wags       = '4.0345544e-008+dwagsp_hv18_ms'    
+pags       = '-2.5768888e-014+dpagsp_hv18_ms'    
+a1         = 0                   a2         = 0.80299             b0         = -7e-006    
+b1         = 0                   keta       = 0.021272191         lketa      = -3.9771479e-008    
+wketa      = -1.6358456e-007     pketa      = 7.3376804e-014      dwg        = -3.5628e-009    
+dwb        = 6.5366e-009         pclm       = 0.14501967          lpclm      = 9.70871e-008    
+wpclm      = -3.1576492e-008     ppclm      = 1.898322e-014       pdiblc1    = 0    
+pdiblc2    = '0.0001+dpdiblc2p_hv18_ms'    
+pdiblcb    = 0                   drout      = 0.23168846          pvag       = 9.9607623e-005    
+delta      = 0.0130199           pscbe1     = 2.5512e+008         pscbe2     = 2.3801e-010    
+fprout     = 9.886e-005          pdits      = 9.8993e-007         pditsd     = 0    
+pditsl     = 0                   rsh        = 22.5                rsw        = 249.32    
+rdw        = 2600.4              rdswmin    = 0                   rdwmin     = 0    
+rswmin     = 0                   prwg       = 0                   prwb       = 0    
+wr         = 0.95773321          alpha0     = 4.6919e-008         alpha1     = 0.0070432    
+beta0      = 28                  agidl      = '(1.501e-012)*agidl_wl'    
+bgidl      = 4.609e+009    
+cgidl      = 1.8713              egidl      = 0.046385            aigbacc    = 0.01238    
+bigbacc    = 0.006109            cigbacc    = 0.2809              nigbacc    = 4.05    
+aigbinv    = 0.35                bigbinv    = 0.03                cigbinv    = 0.006    
+eigbinv    = 1.1                 nigbinv    = 1                   aigc       = 0.009898    
+bigc       = 0.001383            cigc       = 1.515e-005          aigsd      = 0.0086    
+bigsd      = 0.0004353           cigsd      = 3.925e-020          nigc       = 1    
+poxedge    = 1                   pigcd      = 1.672               ntox       = 1    
+vfbsdoff   = 0.1                 cgso       = 'cgsop_hv18_ms'          cgdo       = 'cgdop_hv18_ms+cfdsp_hv18_ms'    
+cgbo       = 0                   cgdl       = 'cgdlp_hv18_ms'          cgsl       = 'cgslp_hv18_ms'    
+clc        = 1e-007              cle        = 0.6                 cf         = 'cfsp_hv18_ms'    
+ckappas    = 0.6                 ckappad    = 0.6                 acde       = 0.3    
+moin       = 6.41                noff       = 2.5                 voffcv     = -0.029164    
+tvoff      = 0.0026977           wtvoff     = -2.24478e-009       tvfbsdoff  = 0.01015    
+kt1        = '-0.29679782+dkt1p_hv18_ms'    
+lkt1       = '-5.2983012e-009+dlkt1p_hv18_ms'    
+wkt1       = '-5.4435935e-008+dwkt1p_hv18_ms'    
+pkt1       = '9.6164577e-015+dpkt1p_hv18_ms'    
+kt1l       = 0                   kt2        = 0.037815903         lkt2       = -1.4224055e-008    
+wkt2       = -7.5023927e-008     pkt2       = 2.4736467e-014      ute        = -1.0479427    
+lute       = 7.0701525e-008      wute       = -5.5778876e-008     pute       = 3.7460636e-016    
+ua1        = '0.0041952039+dua1p_hv18_ms'    
+lua1       = '1.7499495e-009+dlua1p_hv18_ms'    
+wua1       = '3.726348e-009+dwua1p_hv18_ms'    
+pua1       = '-2.0761421e-015+dpua1p_hv18_ms'    
+ub1        = -0.11047111         lub1       = 1.5667451e-008      wub1       = 1.0579255e-008    
+pub1       = 3.8826618e-015      uc1        = -0.037652384        luc1       = 6.0611906e-009    
+wuc1       = -6.7442107e-009     puc1       = 4.812829e-015       prt        = 0.0013912    
+at         = '0.00016072+datp_hv18_ms'    
+fnoimod    = 1.000000e+00    
+tnoimod    = 0    
+em         = 4.100000e+07    
+ef         = 1.140000e+00    
+noia       = 1.210000e+42    
+noib       = 2.210000e+25    
+noic       = 3.940000e+09    
+lintnoi    = 1.050000e-11    
+jss        = 4.400000e-07    
+jsws       = 2.940000e-13    
+jswgs      = 5.070000e-14    
+njs        = 1.020000e+00    
+ijthsfwd   = 0.01                ijthsrev   = 0.01    
+bvs        = 7.600000e+00    
+xjbvs      = 1    
+jsd        = 1.730000e-07    
+jswd       = 1.080000e-13    
+jswgd      = 8.660000e-14    
+njd        = 1.020000e+00    
+ijthdfwd   = 0.01    
+ijthdrev   = 0.01    
+bvd        = 1.370000e+01    
+xjbvd      = 1    
+jtss       = 0                   jtsd       = 0                   jtssws     = 0    
+jtsswd     = 0                   jtsswgs    = '(1e-010)*jtsswg_wl'    
+jtsswgd    = '(1e-010)*jtsswg_wl'    
+njts       = 20                  njtssw     = 20                  njtsswg    = 7.8536    
+xtss       = 0.02                xtsd       = 0.02                xtssws     = 0.02    
+xtsswd     = 0.02                xtsswgs    = 0.893               xtsswgd    = 0.893    
+tnjts      = 0                   tnjtssw    = 0                   tnjtsswg   = 1    
+vtss       = 10                  vtsd       = 10                  vtssws     = 10    
+vtsswd     = 10                  vtsswgs    = 1                   vtsswgd    = 1    
+pbs        = 6.130000e-01    
+cjs        = 'cjsp_hv18_ms'    
+mjs        = 7.230000e-01    
+pbsws      = 9.160000e-01    
+cjsws      = 'cjswsp_hv18_ms'    
+mjsws      = 6.970000e-01    
+pbswgs     = 8.790000e-01    
+cjswgs     = 'cjswgsp_hv18_ms'    
+mjswgs     = 6.060000e-01    
+pbd        = 7.000000e-01    
+cjd        = 'cjdp_hv18_ms'    
+mjd        = 3.250000e-01    
+pbswd      = 5.670000e-01    
+cjswd      = 'cjswdp_hv18_ms'    
+mjswd      = 2.210000e-01    
+pbswgd     = 8.210000e-01    
+cjswgd     = 'cjswgdp_hv18_ms'    
+mjswgd     = 3.850000e-01    
+tpb        = 5.910000e-04    
+tcj        = 5.800000e-04    
+tpbsw      = 1.100000e-03    
+tcjsw      = 6.900000e-04    
+tpbswg     = 1.110000e-03    
+tcjswg     = 1.000000e-03    
+xtis       = '3+dxti'    
+xtid       = '3+dxti'    
+dmcg       = 6.6e-008    
+dmci       = 6.6e-008            dmdg       = 0                   dmcgt      = 0    
+dwj        = 0                   xgw        = 0                   xgl        = 0    
+rshg       = 'rmainsh'    
+weta0      = '0+dweta0p_hv18_ms'     lnfactor   = '0+dlnfactorp_hv18_ms'    
+wnfactor   = '0+dwnfactorp_hv18_ms'  pnfactor   = '0+dpnfactorp_hv18_ms'  lvsat      = '(0+dlvsatp_hv18_ms)*fvsat_lod'    
+lpdiblc2   = '0+dlpdiblc2p_hv18_ms'  lat        = '0+dlatp_hv18_ms'       wpdiblc2   = '0+dwpdiblc2p_hv18_ms'    
+ppdiblc2   = '0+dppdiblc2p_hv18_ms'  wvsat      = '(0+dwvsatp_hv18_ms)*fvsat_lod'    
+pvsat      = '(0+dpvsatp_hv18_ms)*fvsat_lod'    
+wat        = '0+dwatp_hv18_ms'       pat        = '0+dpatp_hv18_ms'    
+lk2we    = -2.0e-11    
+wk2we    = 5.0e-11    
+pk2we    = 0.0e-18    
+k2we     = 0.0006    
+lku0we   = 0.9e-10    
+wku0we   = 0.0e-10    
+pku0we   = 0.5e-17    
+ku0we    = -0.0010    
+lkvth0we = -5.35044e-011    
+wkvth0we = -1.01749e-010    
+pkvth0we = 1.33965e-017    
+kvth0we  = -0.000575476    
+scref    = 1e-6    
+wec      = -7538.6    
+web      = 1041.77 )    
    
.ends pch_hv18_mac    
.ENDL Total_hv18    
    
.LIB MOS_hv18    
    
*** for backward compatible with conventional format ***    
    
*#.model pch_hv18.1 pmos    
    
    
*** for backward compatible with conventional format ***    
    
*#.model nch_hv18.1 nmos    
    
.ENDL MOS_hv18    
    
