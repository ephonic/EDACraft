########################################################################################
######  DCICC FLOW - Version 3.10.0 (2015-05-06), For T40
######  support DC&&ICC 2013.12
######  Owner : zhangx, Dep-1
########################################################################################
#---------------------------------------------------------------------------------------
#	Library Definitions
#---------------------------------------------------------------------------------------
set lib_common	{
	alib_path	""
	ant_rule	/home/Library/SMIC_40LL/ROUTE/milkyway/1P9M_2TM/antenna_rules.tcl
	tf		/home/Library/SMIC_40LL/ROUTE/milkyway/1P9M_2TM/sc12mc_tech.tf
	tech_lef	/home/Library/SMIC_40LL/ROUTE/lef/1P9M_2TM/sc12mc_tech.lef
	tlu	{
		typical		/home/Library/SMIC_40LL/ROUTE/synopsys_tluplus/1P9M_2TM/typ.tluplus
		cbest		/home/Library/SMIC_40LL/ROUTE/synopsys_tluplus/1P9M_2TM/cmin.tluplus
		cworst		/home/Library/SMIC_40LL/ROUTE/synopsys_tluplus/1P9M_2TM/cmax.tluplus
		rcbest		/home/Library/SMIC_40LL/ROUTE/synopsys_tluplus/1P9M_2TM/rcmin.tluplus
		rcworst		/home/Library/SMIC_40LL/ROUTE/synopsys_tluplus/1P9M_2TM/rcmax.tluplus
	}
	mapfile	{
		itfmap		/home/Library/SMIC_40LL/ROUTE/synopsys_tluplus/1P9M_2TM/tluplus.map
		gdsmap		/home/Library/SMIC_40LL/ROUTE/milkyway/1P9M_2TM/stream_out_layer_map
	}
	operating_conditions	{
		ff_typical_min_1p21v_125c	ff_typical_min_1p21v_125c
		ff_typical_min_1p21v_0c		ff_typical_min_1p21v_0c
		ff_typical_min_1p21v_m40c	ff_typical_min_1p21v_m40c
		ss_typical_max_0p99v_125c	ss_typical_max_0p99v_125c
		ss_typical_max_0p99v_0c		ss_typical_max_0p99v_0c
		ss_typical_max_0p99v_m40c	ss_typical_max_0p99v_m40c
		tt_typical_max_1p10v_85c	tt_typical_max_1p10v_85c
                tt_typical_max_1p10v_125c	tt_typical_max_1p10v_125c
	}
        lib_track       {
                dir     {M1 H M2 H M3 V M4 H M5 V M6 H M7 V TM1 H TM2 V ALPA H}
                offset  {M1 0.07 M2 0.07 M3 0.07 M4 0.07 M5 0.07 M6 0.07 M7 0.07 TM1 0.42 TM2 0.42 ALPA 2.31}
        }
	metal_layers	{
		all	{M1 M2 M3 M4 M5 M6 M7 TM1 TM2 ALPA}
		start	M3
	}
	autofp_script	{
		SW4C	../CMD/autofp_sw4c.tcl
		SW4B	../CMD/autofp_sw4c.tcl
		ICH2	../CMD/autofp_tpns.tcl
		default ../CMD/autofp_tpns.tcl
	}
	icv {
		HOME_DIR	/disc/Icvalidator2014.06-SP2
		EXE_PATH	/disc/Icvalidator2014.06-SP2/bin/AMD.64
		DRC_RUNSET	/home/Library/SMIC_40LL/SMIC_40LL/icv/TD-LO40-DI-2001v2/SmicDR4_icv40_log_ll_sali_p1mx_xtm_V1.10_0/SmicDR4_icv40_log_ll_sali_p1mx_2tm_V1.10_0.drc
		GMAP_SCRIPT	/disc/Icvalidator2014.06-SP2/contrib/generate_layer_rule_map.pl
		DPLOG_FILE	signoff_drc_run/run_details/_icv_pcl.dp.log
	}
	pt {
		eco_power_priority	{TR40 TL40}
	}
}
#---------------------------------------------------------------------------------------
#	HS && ECO Libraries, 12 Track
#---------------------------------------------------------------------------------------
# HS40LVT 	: HS 12 track 40nm Channel LVT
# HS40SVT 	: HS 12 track 40nm Channel SVT
# HS40SVT_ECO	: HS 12 track 40nm Channel SVT ECO
set lib_define {
	HS40LVT	{
		db	{
                ff_typical_min_1p21v_125c       /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_ff_typical_min_1p21v_125c.db_ccs_tn
                ff_typical_min_1p21v_0c         /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_ff_typical_min_1p21v_0c.db_ccs_tn
                ff_typical_min_1p21v_m40c       /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_ff_typical_min_1p21v_m40c.db_ccs_tn
                ss_typical_max_0p99v_125c       /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_ss_typical_max_0p99v_125c.db_ccs_tn
                ss_typical_max_0p99v_0c         /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_ss_typical_max_0p99v_0c.db_ccs_tn
                ss_typical_max_0p99v_m40c       /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_ss_typical_max_0p99v_m40c.db_ccs_tn
                tt_typical_max_1p10v_85c        /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_tt_typical_max_1p10v_85c.db_ccs_tn
                tt_typical_max_1p10v_125c       /home/Library/SMIC_40LL/sc12mc_base_lvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_lvt_c40_tt_typical_max_1p10v_125c.db_ccs_tn
		}
		mw		/home/Library/SMIC_40LL/sc12mc_base_lvt_c40/milkyway/1P9M_2TM/sc12mc_logic0040ll_base_lvt_c40
		lef		/home/Library/SMIC_40LL/sc12mc_base_lvt_c40/lef/sc12mc_logic0040ll_base_lvt_c40.lef
		lib_title	sc12mc_logic0040ll_base_lvt_c40*
		dontuse	{
			dc_list		../CMD/S40LL/lvt_dc_dontuse.tcl
			icc_list	../CMD/S40LL/lvt_icc_dontuse.tcl
			param_define	40gphs_lvt_bancell
		}
		function_cell	{
			endcap		FILL1_A12TL40
			antenna		ANTENNA1_A12TL40
			fill_no_metal 	{FILL128_A12TL40 FILL64_A12TL40 FILL32_A12TL40 FILL16_A12TL40 FILL8_A12TL40 FILL4_A12TL40 FILL2_A12TL40 FILL1_A12TL40}
			fill_metal	{FILLCAP128_A12TL40 FILLCAP64_A12TL40 FILLCAP32_A12TL40 FILLCAP16_A12TL40 FILLCAP8_A12TL40 FILLCAP4_A12TL40}
			predecap	FILLCAP8_A12TL40
			listdecap	{*X16*_A12TL40}
			welltap		{FILLTIE4_A12TL40 40}
			driver_inv	{INV_X4M_A12TL40 A Y}
			tie1		TIEHI_X1M_A12TL40
			tie0		TIELO_X1M_A12TL40
			ctsbuf		{sc12mc_logic0040ll_*/INV_*B_A12TL40}
			ctsboundcell	BUF_X4B_A12TL40
			delay_cell	DLY*
		}
		spare	{{NAND2_X4M_A12TL40 0.01 1 VDD} \
                        {AND2_X4M_A12TL40 0.005 1 VDD} \
                        {NOR2_X4M_A12TL40 0.01 1 VSS} \
                        {OR2_X4M_A12TL40 0.005 1 VSS} \
                        {XOR2_X2M_A12TL40 0.004 1 VSS} \
                        {INV_X4M_A12TL40 0.005 1 VSS} \
                        {BUF_X4M_A12TL40 0.005 1 VSS} \
                        {DFFSRPQ_X2M_A12TL40 0.003 1 VDD} \
                        {DFFRPQ_X2M_A12TL40 0.015 1 VDD} \
                        {DFFSQ_X2M_A12TL40 0.015 1 VDD}
		}
		eco_lib	HS40LVT_ECO
	}
	HS40SVT	{
                db      {
                ff_typical_min_1p21v_125c       /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_ff_typical_min_1p21v_125c.db_ccs_tn
                ff_typical_min_1p21v_0c         /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_ff_typical_min_1p21v_0c.db_ccs_tn
                ff_typical_min_1p21v_m40c       /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_ff_typical_min_1p21v_m40c.db_ccs_tn
                ss_typical_max_0p99v_125c       /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_ss_typical_max_0p99v_125c.db_ccs_tn
                ss_typical_max_0p99v_0c         /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_ss_typical_max_0p99v_0c.db_ccs_tn
                ss_typical_max_0p99v_m40c       /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_ss_typical_max_0p99v_m40c.db_ccs_tn
                tt_typical_max_1p10v_85c        /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_tt_typical_max_1p10v_85c.db_ccs_tn
                tt_typical_max_1p10v_125c       /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_base_rvt_c40_tt_typical_max_1p10v_125c.db_ccs_tn
                }
                mw              /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/milkyway/1P9M_2TM/sc12mc_logic0040ll_base_rvt_c40
                lef             /home/Library/SMIC_40LL/sc12mc_base_rvt_c40/lef/sc12mc_logic0040ll_base_rvt_c40.lef
                lib_title       sc12mc_logic0040ll_base_rvt_c40*
                dontuse {
                        dc_list         ../CMD/S40LL/rvt_dc_dontuse.tcl
                        icc_list        ../CMD/S40LL/rvt_icc_dontuse.tcl
                        param_define    40gphs_rvt_bancell
                }
                function_cell   {
                        endcap          FILL1_A12TR40
                        antenna         ANTENNA1_A12TR40
                        fill_no_metal   {FILL128_A12TR40 FILL64_A12TR40 FILL32_A12TR40 FILL16_A12TR40 FILL8_A12TR40 FILL4_A12TR40 FILL2_A12TR40 FILL1_A12TR40}
                        fill_metal      {FILLCAP128_A12TR40 FILLCAP64_A12TR40 FILLCAP32_A12TR40 FILLCAP16_A12TR40 FILLCAP8_A12TR40 FILLCAP4_A12TR40}
                        predecap        FILLCAP8_A12TR40
                        listdecap       {*X16*_A12TR40}
                        welltap         {FILLTIE4_A12TR40 40}
                        driver_inv      {INV_X4M_A12TR40 A Y}
                        tie1            TIEHI_X1M_A12TR40
                        tie0            TIELO_X1M_A12TR40
                        ctsbuf          {sc12mc_logic0040ll_*/INV_*B_A12TR40}
                        ctsboundcell    BUF_X4B_A12TR40
                        delay_cell      DLY*
                }
                spare   {{NAND2_X4M_A12TR40 0.01 1 VDD} \
                        {AND2_X4M_A12TR40 0.005 1 VDD} \
                        {NOR2_X4M_A12TR40 0.01 1 VSS} \
                        {OR2_X4M_A12TR40 0.005 1 VSS} \
                        {XOR2_X2M_A12TR40 0.004 1 VSS} \
                        {INV_X4M_A12TR40 0.005 1 VSS} \
                        {BUF_X4M_A12TR40 0.005 1 VSS} \
                        {DFFSRPQ_X2M_A12TR40 0.003 1 VDD} \
                        {DFFRPQ_X2M_A12TR40 0.015 1 VDD} \
                        {DFFSQ_X2M_A12TR40 0.015 1 VDD}

		}
		eco_lib	HS40SVT_ECO
	}
	HS40SVT_ECO {
		db	{
                ff_typical_min_1p21v_125c       /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_ff_typical_min_1p21v_125c.db_ccs_tn
                ff_typical_min_1p21v_0c         /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_ff_typical_min_1p21v_0c.db_ccs_tn
                ff_typical_min_1p21v_m40c       /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_ff_typical_min_1p21v_m40c.db_ccs_tn
                ss_typical_max_0p99v_125c       /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_ss_typical_max_0p99v_125c.db_ccs_tn
                ss_typical_max_0p99v_0c         /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_ss_typical_max_0p99v_0c.db_ccs_tn
                ss_typical_max_0p99v_m40c       /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_ss_typical_max_0p90v_m40c.db_ccs_tn
                tt_typical_max_1p10v_85c        /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_tt_typical_max_1p10v_25c.db_ccs_tn
                tt_typical_max_1p10v_125c       /home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/db-ccs-tn/sc12mc_logic0040ll_eco_rvt_c40_tt_typical_max_1p10v_85c.db_ccs_tn
		}
		mw		/home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/milkyway/1P9M_2TM/sc12mc_logic0040ll_eco_rvt_c40
		lef		/home/Library/SMIC_40LL/sc12mc_eco_rvt_c40/lef/sc12mc_logic0040ll_eco_rvt_c40.lef
		lib_title	sc12mc_logic0040ll_eco_rvt_c40*
                function_cell   {
                        endcap          FILL1_A12TR40
                        antenna         ANTENNA1_A12TR40
                        fill_no_metal   {FILL128_A12TR40 FILL64_A12TR40 FILL32_A12TR40 FILL16_A12TR40 FILL8_A12TR40 FILL4_A12TR40 FILL2_A12TR40 FILL1_A12TR40}
                        fill_metal      {FILLCAP128_A12TR40 FILLCAP64_A12TR40 FILLCAP32_A12TR40 FILLCAP16_A12TR40 FILLCAP8_A12TR40 FILLCAP4_A12TR40}
                        predecap        FILLCAP8_A12TR40
                        listdecap       {*X16*_A12TR40}
                        welltap         {FILLTIE4_A12TR40 40}
                        driver_inv      {INV_X4M_A12TR40 A Y}
                        tie1            TIEHI_X1M_A12TR40
                        tie0            TIELO_X1M_A12TR40
                        ctsbuf          {sc12mc_logic0040ll_*/INV_*B_A12TR40}
                        ctsboundcell    BUF_X4B_A12TR40
                        delay_cell      DLY*
                }
		ref_eco	HS40SVT_ECO
	}
	PEK_LVT    {
        db    {
                ff_typical_min_1p21v_125c       /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ff_v1p21_125c_ccs.db
                ff_typical_min_1p21v_0c         /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ff_v1p21_0c_ccs.db
                ff_typical_min_1p21v_m40c       /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ff_v1p21_-40c_ccs.db
                ff_typical_min_1p10v_m40c       /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ff_v1p1_-40c_ccs.db
                ss_typical_max_0p99v_125c       /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ss_v0p99_125c_ccs.db
                ss_typical_max_0p99v_0c         /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ss_v0p99_0c_ccs.db
                ss_typical_max_0p99v_m40c       /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ss_v0p99_-40c_ccs.db
                ss_typical_max_1p08v_125c       /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_ss_v1p08_125c_ccs.db
                tt_typical_max_1p10v_85c        /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_tt_v1p1_85c_ccs.db
                tt_typical_max_1p10v_125c       /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_tt_v1p2_125c_ccs.db
                tt_typical_max_1p10v_25c        /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/liberty/1.1v/scip40nll_a12t_pek_lvt_tt_v1p1_25c_ccs.db
        }
        pocv    {
        }
        aocv    {
        }
        ndm             /home/public_data/44G/library/SCIP40NLL_A12T_PEK_LVT.ndm_now
 	mw              /home/Library/SMIC_40LL/40nm_PEK/STD_ARM/SCIP40NLL_A12T_PEK_LVT_V0p5a/astro/scip40nll_a12t_pek_lvt
        lef             /home/public_data/44G/IP/std/SCIP40NLL_A12T_PEK_LVT/lef/macro/scip40nll_a12t_pek_lvt.lef
        lib_title       scip40nll_a12t_pek_lvt_tt_v1p1_25c_ccs.*
                function_cell   {
                        endcap          FILL1_A12TR40
                        antenna         ANTENNA1_A12TR40
                        fill_no_metal   {FILL128_A12TR40 FILL64_A12TR40 FILL32_A12TR40 FILL16_A12TR40 FILL8_A12TR40 FILL4_A12TR40 FILL2_A12TR40 FILL1_A12TR40}
                        fill_metal      {FILLCAP128_A12TR40 FILLCAP64_A12TR40 FILLCAP32_A12TR40 FILLCAP16_A12TR40 FILLCAP8_A12TR40 FILLCAP4_A12TR40}
                        predecap        FILLCAP8_A12TR40
                        listdecap       {*X16*_A12TR40}
                        welltap         {FILLTIE4_A12TR40 40}
                        driver_inv      {INV_X4M_A12TR40 A Y}
                        tie1            TIEHI_X1M_A12TR40
                        tie0            TIELO_X1M_A12TR40
                        ctsbuf          {sc12mc_logic0040ll_*/INV_*B_A12TR40}
                        ctsboundcell    BUF_X4B_A12TR40
                        delay_cell      DLY*
                }
        lib_title_ndm   *a12t_pek_lvt*
        vt_type         low_vt
        cell_prefix     test
        site            unit
        extracted       {
        }

	}
}
