*  **************************************************************
*  *  TSMC SPICE MODEL --- Security B - TSMC Restricted Secret  *
*  **************************************************************
.lib pre_simu
.option geoshrink=0.9
.param ccoflag=1
.param ccoflag_18=1
.param ccoflag_18ud12=1
.param ccoflag_18ud15=1
.param ccoflag_avt=1
.param ccoflag_cap=1
.param ccoflag_cap_18=1
.param ccoflag_ehvt=1
.param ccoflag_hia=1
.param ccoflag_hia18=1
.param ccoflag_hvt=1
.param ccoflag_lvt=1
.param ccoflag_na=1
.param ccoflag_na18=1
.param ccoflag_uhvt=1
.param ccoflag_ulvt=1
.param rcoflag=1
.param rcoflag_18=1
.param rcoflag_18ud12=1
.param rcoflag_18ud15=1
.param rcoflag_avt=1
.param rcoflag_ehvt=1
.param rcoflag_hia=1
.param rcoflag_hia18=1
.param rcoflag_hvt=1
.param rcoflag_lvt=1
.param rcoflag_na=1
.param rcoflag_na18=1
.param rcoflag_uhvt=1
.param rcoflag_ulvt=1
.param rgflag=1
.param rgflag_18=1
.param rgflag_18ud12=1
.param rgflag_18ud15=1
.param rgflag_avt=1
.param rgflag_ehvt=1
.param rgflag_hia=1
.param rgflag_hia18=1
.param rgflag_hvt=1
.param rgflag_lvt=1
.param rgflag_na=1
.param rgflag_na18=1
.param rgflag_uhvt=1
.param rgflag_ulvt=1
.endl pre_simu


.lib noise_typical
.option geoshrink=0.9
.param noiseflagn=0
.param noiseflagp=0
.param noiseflagn_18=0
.param noiseflagp_18=0
.param noiseflagn_18ud12=0
.param noiseflagp_18ud12=0
.param noiseflagn_18ud15=0
.param noiseflagp_18ud15=0
.param noiseflagn_hvt=0
.param noiseflagp_hvt=0
.param noiseflagn_lvt=0
.param noiseflagp_lvt=0
.param rnoiseflag_res=0
.param rnoiseflag_disres=0
.endl noise_typical

.lib noise_worst
.option geoshrink=0.9
.param noiseflagn=1
.param noiseflagp=1
.param noiseflagn_18=1
.param noiseflagp_18=1
.param noiseflagn_18ud12=1
.param noiseflagp_18ud12=1
.param noiseflagn_18ud15=1
.param noiseflagp_18ud15=1
.param noiseflagn_hvt=1
.param noiseflagp_hvt=1
.param noiseflagn_lvt=1
.param noiseflagp_lvt=1
.param rnoiseflag_res=1
.param rnoiseflag_disres=1
.endl noise_worst

.lib noise_best
.option geoshrink=0.9
.param noiseflagn=-1
.param noiseflagp=-1
.param noiseflagn_18=-1
.param noiseflagp_18=-1
.param noiseflagn_18ud12=-1
.param noiseflagp_18ud12=-1
.param noiseflagn_18ud15=-1
.param noiseflagp_18ud15=-1
.param noiseflagn_hvt=-1
.param noiseflagp_hvt=-1
.param noiseflagn_lvt=-1
.param noiseflagp_lvt=-1
.param rnoiseflag_res=-1
.param rnoiseflag_disres=-1
.endl noise_best

.lib noise_mc
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2_shrink0d9_embedded_usage.l' noise_typical
.param noiseflagn_mc=1
.param noiseflagp_mc=1
.param noiseflagn_18_mc=1
.param noiseflagp_18_mc=1
.param noiseflagn_18ud12_mc=1
.param noiseflagp_18ud12_mc=1
.param noiseflagn_18ud15_mc=1
.param noiseflagp_18ud15_mc=1
.param noiseflagn_hvt_mc=1
.param noiseflagp_hvt_mc=1
.param noiseflagn_lvt_mc=1
.param noiseflagp_lvt_mc=1
.endl noise_mc


.lib TTMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.endl TTMacro_MOS_MOSCAP

.lib SSMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.endl SSMacro_MOS_MOSCAP

.lib FFMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.endl FFMacro_MOS_MOSCAP

.lib SFMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.endl SFMacro_MOS_MOSCAP

.lib FSMacro_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.endl FSMacro_MOS_MOSCAP

.lib TTGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ttg_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.param totalflag_mos=0
.param totalflag_mos_18=0
.param totalflag_mos_18ud12=0
.param totalflag_mos_18ud15=0
.param totalflag_mos_avt=0
.param totalflag_mos_ehvt=0
.param totalflag_mos_hvt=0
.param totalflag_mos_lvt=0
.param totalflag_mos_na18=0
.param totalflag_mos_na=0
.param totalflag_mos_uhvt=0
.param totalflag_mos_ulvt=0
.endl TTGlobalCorner_LocalMC_MOS_MOSCAP

.lib SSGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ssg_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.param totalflag_mos=0
.param totalflag_mos_18=0
.param totalflag_mos_18ud12=0
.param totalflag_mos_18ud15=0
.param totalflag_mos_avt=0
.param totalflag_mos_ehvt=0
.param totalflag_mos_hvt=0
.param totalflag_mos_lvt=0
.param totalflag_mos_na18=0
.param totalflag_mos_na=0
.param totalflag_mos_uhvt=0
.param totalflag_mos_ulvt=0
.endl SSGlobalCorner_LocalMC_MOS_MOSCAP

.lib FFGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ffg_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.param totalflag_mos=0
.param totalflag_mos_18=0
.param totalflag_mos_18ud12=0
.param totalflag_mos_18ud15=0
.param totalflag_mos_avt=0
.param totalflag_mos_ehvt=0
.param totalflag_mos_hvt=0
.param totalflag_mos_lvt=0
.param totalflag_mos_na18=0
.param totalflag_mos_na=0
.param totalflag_mos_uhvt=0
.param totalflag_mos_ulvt=0
.endl FFGlobalCorner_LocalMC_MOS_MOSCAP

.lib SFGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sf_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' sfg_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.param totalflag_mos=0
.param totalflag_mos_18=0
.param totalflag_mos_18ud12=0
.param totalflag_mos_18ud15=0
.param totalflag_mos_avt=0
.param totalflag_mos_ehvt=0
.param totalflag_mos_hvt=0
.param totalflag_mos_lvt=0
.param totalflag_mos_na18=0
.param totalflag_mos_na=0
.param totalflag_mos_uhvt=0
.param totalflag_mos_ulvt=0
.endl SFGlobalCorner_LocalMC_MOS_MOSCAP

.lib FSGlobalCorner_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fs_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' fsg_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.param totalflag_mos=0
.param totalflag_mos_18=0
.param totalflag_mos_18ud12=0
.param totalflag_mos_18ud15=0
.param totalflag_mos_avt=0
.param totalflag_mos_ehvt=0
.param totalflag_mos_hvt=0
.param totalflag_mos_lvt=0
.param totalflag_mos_na18=0
.param totalflag_mos_na=0
.param totalflag_mos_uhvt=0
.param totalflag_mos_ulvt=0
.endl FSGlobalCorner_LocalMC_MOS_MOSCAP

.lib LocalMCOnly_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.param globalflag_mos=0
.param globalflag_mos_18=0
.param globalflag_mos_18ud12=0
.param globalflag_mos_18ud15=0
.param globalflag_mos_avt=0
.param globalflag_mos_ehvt=0
.param globalflag_mos_hvt=0
.param globalflag_mos_lvt=0
.param globalflag_mos_na18=0
.param globalflag_mos_na=0
.param globalflag_mos_uhvt=0
.param globalflag_mos_ulvt=0
.param totalflag_mos=0
.param totalflag_mos_18=0
.param totalflag_mos_18ud12=0
.param totalflag_mos_18ud15=0
.param totalflag_mos_avt=0
.param totalflag_mos_ehvt=0
.param totalflag_mos_hvt=0
.param totalflag_mos_lvt=0
.param totalflag_mos_na18=0
.param totalflag_mos_na=0
.param totalflag_mos_uhvt=0
.param totalflag_mos_ulvt=0
.endl LocalMCOnly_MOS_MOSCAP

.lib GlobalMC_LocalMC_MOS_MOSCAP
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hia18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' global_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_rfmvar
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_rfmvar_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_mos_cap
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_mos_cap_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat
.param totalflag_mos=0
.param totalflag_mos_18=0
.param totalflag_mos_18ud12=0
.param totalflag_mos_18ud15=0
.param totalflag_mos_avt=0
.param totalflag_mos_ehvt=0
.param totalflag_mos_hvt=0
.param totalflag_mos_lvt=0
.param totalflag_mos_na18=0
.param totalflag_mos_na=0
.param totalflag_mos_uhvt=0
.param totalflag_mos_ulvt=0
.endl GlobalMC_LocalMC_MOS_MOSCAP

.lib TT_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_res
.param mismatchflag_bip=0
.param mismatchflag_bip_npn=0
.param mismatchflag_disres=0
.param mismatchflag_res=0
.endl TT_RES_BIP_DIO_DISRES

.lib SS_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_res
.param mismatchflag_bip=0
.param mismatchflag_bip_npn=0
.param mismatchflag_disres=0
.param mismatchflag_res=0
.endl SS_RES_BIP_DIO_DISRES

.lib FF_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_res
.param mismatchflag_bip=0
.param mismatchflag_bip_npn=0
.param mismatchflag_disres=0
.param mismatchflag_res=0
.endl FF_RES_BIP_DIO_DISRES

.lib TTGlobalCorner_LocalMC_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_res
.endl TTGlobalCorner_LocalMC_RES_BIP_DIO_DISRES

.lib SSGlobalCorner_LocalMC_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_res
.endl SSGlobalCorner_LocalMC_RES_BIP_DIO_DISRES

.lib FFGlobalCorner_LocalMC_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_res
.endl FFGlobalCorner_LocalMC_RES_BIP_DIO_DISRES

.lib LocalMCOnly_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_res
.endl LocalMCOnly_RES_BIP_DIO_DISRES

.lib GlobalMC_LocalMC_RES_BIP_DIO_DISRES
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_dio_hia
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_bip
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_bip_npn
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_18ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_18ud12
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_18ud15
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_avt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_dnw
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_ehvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_esd
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_hvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_ll
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_lvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_na
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_na18
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_uhvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_dio_ulvt
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_disres
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_res
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat_bip_dio
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat_res
.endl GlobalMC_LocalMC_RES_BIP_DIO_DISRES

.lib TT_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_fmom
.param mismatchflag_fmom=0
.param mismatchflag_rffmom=0
.endl TT_MOM

.lib SS_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_fmom
.param mismatchflag_fmom=0
.param mismatchflag_rffmom=0
.endl SS_MOM

.lib FF_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_fmom
.param mismatchflag_fmom=0
.param mismatchflag_rffmom=0
.endl FF_MOM

.lib TTGlobalCorner_LocalMC_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_fmom
.endl TTGlobalCorner_LocalMC_MOM

.lib SSGlobalCorner_LocalMC_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ss_fmom
.endl SSGlobalCorner_LocalMC_MOM

.lib FFGlobalCorner_LocalMC_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' ff_fmom
.endl FFGlobalCorner_LocalMC_MOM

.lib LocalMCOnly_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' tt_fmom
.endl LocalMCOnly_MOM

.lib GlobalMC_LocalMC_MOM
.option geoshrink=0.9
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_rffmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' total_fmom
.lib 'crn28hpcp_lct_1d8_elk_v1d0_2p2.l' stat_mom
.endl GlobalMC_LocalMC_MOM

.lib TT_R_METAL
.option geoshrink=0.9
.lib 'res_metal.l' TT_res_metal
.endl TT_R_METAL

.lib SS_R_METAL
.option geoshrink=0.9
.lib 'res_metal.l' SS_res_metal
.endl SS_R_METAL

.lib FF_R_METAL
.option geoshrink=0.9
.lib 'res_metal.l' FF_res_metal
.endl FF_R_METAL
