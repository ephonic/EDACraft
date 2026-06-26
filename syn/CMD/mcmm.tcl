########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  MCMM setting
########################################################################################
###	There are three scenarios example, and you can add new or modify them as your need!
###	Syntax explanation:
###	set lib_mcmm {
###		SCENARIO1	{
###			key1	value1
###			key2	value2
###			...
###		}
###		SCENARIO2	{
###			...
###		}
###		...
###	}
###	PS:(VERY IMPORTANT!)
###	1.'pt_custom_*' only works for PT-DMSA FLOW.
###	2.different corner for different process, such as :
###	   T40G:   ttdb0p9v25c,ssdb0p81v125c,ffqb0p99vn40c
###        T28HPM: tt0p9v25c,ss0p81v125c,ff0p99vn40c
###        T16FFP: tt0p8v25c,ssgnp0p72v125c,ffgnp0p88vn40c
########################################################################################
set var(mcmm_default_view)			mode.ssgnp0p72v125c.rcworst		; # [DCICC]	define default scenario view.

set lib_mcmm	{
	mode.ss0p81v125c.rcworst {
		corner		ssgnp0p72v125c
		rctype		rcworst
		analysis_type	on_chip_variation
		setup		true
		hold		true
		cts		true
		dynamic_power	true
		leakage_power	true
		active		true
		clock_file	../CMD/clock_ss.tcl
		dc_sdc		../CMD/additional_dc.ss.sdc
		icc_sdc		../CMD/additional_icc.ss.sdc
		full_sdc	../CMD/full.ss.sdc
		pt_custom_sdc	{}
		pt_custom_spf	{}
	}
	mode.ff0p99vn40c.rcbest {
		corner		ffgnp0p88vn40c
		rctype		rcbest
		analysis_type	on_chip_variation
		setup		false
		hold		true
		cts		false
		dynamic_power	true
		leakage_power	false
		active		true
		clock_file	../CMD/clock_ff.tcl
		dc_sdc		../CMD/additional_dc.ff.sdc
		icc_sdc		../CMD/additional_icc.ff.sdc
		full_sdc	../CMD/full.ff.sdc
		pt_custom_sdc	{}
		pt_custom_spf	{}
	}
}
