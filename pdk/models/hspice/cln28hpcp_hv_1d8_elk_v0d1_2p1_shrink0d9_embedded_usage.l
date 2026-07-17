**************************************************************
*  TSMC SPICE MODEL --- Security B - TSMC Restricted Secret  *
**************************************************************
.lib pre_simu
.option geoshrink=0.9
.param ccoflag_hv18=1
.param rgflag_hv18=1
.param rcoflag_hv18=1
.endl pre_simu

.lib TTMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' global_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.endl TTMacro_MOS_MOSCAP

.lib SSMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' SS_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' global_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.endl SSMacro_MOS_MOSCAP

.lib FFMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' FF_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' global_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.endl FFMacro_MOS_MOSCAP

.lib SFMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' SF_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' global_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.endl SFMacro_MOS_MOSCAP

.lib FSMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' FS_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' global_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.endl FSMacro_MOS_MOSCAP

.lib TTGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' ttg_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.param totalflag_mos_hv18=0
.endl TTGlobalCorner_LocalMC_MOS_MOSCAP

.lib SSGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' ssg_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.param totalflag_mos_hv18=0
.endl SSGlobalCorner_LocalMC_MOS_MOSCAP

.lib FFGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' ffg_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.param totalflag_mos_hv18=0
.endl FFGlobalCorner_LocalMC_MOS_MOSCAP

.lib SFGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' sfg_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.param totalflag_mos_hv18=0
.endl SFGlobalCorner_LocalMC_MOS_MOSCAP

.lib FSGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' fsg_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.param totalflag_mos_hv18=0
.endl FSGlobalCorner_LocalMC_MOS_MOSCAP

.lib LocalMCOnly_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' global_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.param totalflag_mos_hv18=0
.param globalflag_mos_hv18=0
.endl LocalMCOnly_MOS_MOSCAP

.lib GlobalMC_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' TT_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' global_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' Total_hv18
.lib 'cln28hpcp_hv_1d8_elk_v0d1_2p1.l' stat_hv
.param totalflag_mos_hv18=0
.endl GlobalMC_LocalMC_MOS_MOSCAP
