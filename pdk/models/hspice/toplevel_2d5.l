*  **************************************************************
*  *  TSMC SPICE MODEL --- Security B - TSMC Restricted Secret  *
*  **************************************************************
*
*    PROCESS :  0.028um Mixed Signal RF LC Tank HIGH PERFORMANCE COMPACT MOBILE COMPUTING PLUS (0.9V/2.5V)(CRN28HT LCT)
*    MODEL   :  BSIM4 ( V4.5 )   
*    DOC. NO.:  T-N28-CR-SP-023
*    VERSION :  v1.0_2p1
*    DATE    :  02:00PM, Feb. 02, 2016
*    HSPICE VERSION : K-2015.06-SP1-2 
*
************************************************************************************
*       THIS INCLUDE HEADER CONTAINS :                                             *
*                                                                              	   *
*    Total Corner :                                                            	   *
*	TOP_TT   totalflag_xx=1 globalflag_xx=1 mismatchflag_xx=1              	   *
*	TOP_SS   totalflag_xx=1 globalflag_xx=1 mismatchflag_xx=1              	   *
*	TOP_FF   totalflag_xx=1 globalflag_xx=1 mismatchflag_xx=1              	   *
*	TOP_FS   totalflag_xx=1 globalflag_xx=1 mismatchflag_xx=1              	   *
*	TOP_SF   totalflag_xx=1 globalflag_xx=1 mismatchflag_xx=1              	   *
*                                                                              	   *
************************************************************************************

.lib TOP_TT
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TTMacro_MOS_MOSCAP
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_RES_BIP_DIO_DISRES
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_MOM
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_R_METAL
.endl TOP_TT

.lib TOP_SS
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' SSMacro_MOS_MOSCAP
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' SS_RES_BIP_DIO_DISRES
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' SS_MOM
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' SS_R_METAL
.endl TOP_SS

.lib TOP_FF
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' FFMacro_MOS_MOSCAP
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' FF_RES_BIP_DIO_DISRES
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' FF_MOM
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' FF_R_METAL
.endl TOP_FF

.lib TOP_FS
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' FSMacro_MOS_MOSCAP
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_RES_BIP_DIO_DISRES
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_MOM
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_R_METAL
.endl TOP_FS

.lib TOP_SF
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' SFMacro_MOS_MOSCAP
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_RES_BIP_DIO_DISRES
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_MOM
.lib './crn28hpcp_lct_2d5_elk_v1d0_2p1_shrink0d9_embedded_usage.l' TT_R_METAL
.endl TOP_SF

