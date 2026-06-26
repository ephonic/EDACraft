########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  support DC/ICC(2016.03), PT/ICV/STARRC(2015.06)
######  Owner : Anonymous , rc
########################################################################################
#---------------------------------------------------------------------------------------
#	Design Variables
#---------------------------------------------------------------------------------------
set var(design_name)		Cluster_Top ; # [DCICC]: set DESIGN_NAME
set var(libs)		{ RVT LVT ULVT}	; # [PB][DCICC]: set libraries, the last library will be used as main library.
								; #          libs : T40G : 'HS40LVT HS40HVT HS40SVT'
								; #          libs : T28HPM : 'HS35HVT HS35SVT HS35LVT HS31ULVT HS31LVT HS31SVT'
								; #          libs : T16FFP : 'US16ULVT US16SVT US16LVT'
set var(libs_finalopt)		{}				; # [ICC]:   set libraries for just final timing && power optimization!
set var(lib_eco)		LVT_ECO				; # [PB][ICC]:   define eco lib for var(insert,eco), support : 
								; #          lib_eco : T40G : HS40SVT_ECO, HS40LVT_ECO, HS40HVT_ECO.
								; #          lib_eco : T28HPM : HS31SVT_ECO, HS35SVT_ECO
								; #          lib_eco : T16FFP : US16LVT, US16SVT, US16ULVT
set var(libs_vth_cons)		{}				; # [PB][DCICC]: set lvt percentage constratints, such as {HS40LVT 5} or {{HS31LVT HS35SVT} 2.0},
set var(top_layer)		TM2				; # [DCICC]: set top metal layer
set var(bottom_layer)		M2				; # [DCICC]: set bottom metal layer
set var(global_max_layer_mode)	hard				; # [DCICC]: Controls the application of the maximum routing layer constraint.(soft|allow_pin_connection|hard)
set var(global_min_layer_mode)	allow_pin_connection		; # [DCICC]: Controls the application of the minimum routing layer constraint.(soft|allow_pin_connection|hard)
set var(num_cpus)		4				; # [DCICC]: set the maximum number of cpu cores
set var(dc_loop_nums)		0				; # [DC]:    set the max loop nums for compile_ultra -incremental, default is 0, no use.
set var(icc_load_dc_ddc)	./DC/out/$var(design_name).ddc	; # [ICC]    set which ddc file will be used for ICC,
								; #          only work if $var(dc2icc_datatype) is 0.
set var(icc_load_dc_mw)		s00_DCout			; # [ICC]:   set which milkyway cel are used for ICC, such as 's00_DCout' or 'l25_DCout', 
								; #          only work if $var(dc2icc_datatype) is 2.
set var(use_def_track)		true				; # [ICC]:   whether use the track rules defined in DEF file, default is false.
set var(create_pg_strap_with_pin_def)	false			; # [ICC]:   if def file only contains "die size" && "pin locations", plz set this variable to ture,
								; #          scripts will auto create pg straps.
set var(insert,endcap)		true				; # [ICC]:   whether insert endcap before placement.
set var(insert,welltap)		true				; # [ICC]:   whether insert welltap cells.
set var(insert,predecap) 	true				; # [ICC]:   whether insert DCAP cells before placement.
set var(insert,postdecap) 	true				; # [ICC]:   whether insert DCAP cells after P&&R.
set var(insert,listdecap) 	true				; # [ICC]:   whether insert DCAP cells base on specified cell list.
set var(insert,spare)		false				; # [ICC]:   whether insert spare cells
set var(insert,eco)		true				; # [ICC]:   whether insert ECO DCAP&&FILLs
set var(autofp,width,height)	{}				; # [ICC]:   for auto floorplan flow, syntax shows as : {200 300} , if not set this value, autofp use $var(autofp,ratio,util)
set var(autofp,ratio,util)	{1 0.5}				; # [ICC]:   define 'ratio' and 'utilization' for auto floorplan flow.
set var(autofp,flip)		false				; # [ICC]:   auto floorplan flow, whether to flip the 1st site row.
								; #          Variable 'var(autofp,*)' works only if $var(def) file doesn't exists!
set var(autofp,metal_respect_keepout)	{M1 M2 M3 M4}		; # [ICC]:   define metal list for auto creating pg-strips, which will follow the macro keepout constraints.
set var(input,diode)		0				; # [ICC]:   set the number of diode cells which are inserted to all input ports, default is 0.
set var(max_net_length)		250				; # [ICC]:   set max net length constraint.
set var(dpt_utilization)	{{M2 75.0} {M3 80.0}}		; # [DCICC]: set -double_pattern_utilization_by_layer_name for 'set_route_zrt_global_options', only for 16nm.
set var(cong_max_utli)		0.85				; # [DCICC]: set max utilization constraint for congestion optimization, can be set 0 -> 1.0
set var(placer_max_cell_density_threshold)  -1			; # [DCICC]: sets the threshold of how tightly the cells are allowed to clump, should between 0 ~ 1.0
set var(cts,stop_pin_on_macro)	true				; # [ICC]:   whether set clock pins of macro as stop_pins
set var(cts,inter_clock_balance) false				; # [ICC]:   if set true, please write detail options in 'additional_cts.tcl'
set var(cts,target_early_delay) 0				; # [ICC]:   set minimum insertion delay, only for CTS/CCOPT.
set var(power_net)		VDD				; # [ICC]:   set default Power net.
set var(ground_net)		VSS				; # [ICC]:   set default Ground net.
set var(message_limit)		10				; # [DCICC]: set the maximum number of occurrences for specified message_ids.
set var(dc2icc_datatype)   	0				; # [ICC]:   use which way to transfer data from DC => ICC.
								; # 	     support : 0 -- use ddc. (default)
								; # 	               1 -- use verilog/sdc/def.
								; # 	               2 -- use milkyway.
set var(quit)			true				; # [DCICC]: whether quit dc_shell && icc_shell.
set var(custom_set_dontuse)	{}				; # [DCICC]: define custom dontuse list,such as {STN_EN3_3 *_EO3_*}
set var(custom_remove_dontuse)	{}				; # [DCICC]: define custom release list which have been defined as dontuse previously, include var(custom_set_dontuse).
								; #          such as {*_S_* STL_LDPQ_2 *_EO3_*}
set var(insert_port_buffer)	{}				; # [DCICC]: force to insert BUF to specified ports(input or output), support Key words : 'ALL_INPUTS' && 'ALL_OUTPUTS'.
								; #          syntax shows as : {{port_list1 buffer_name1 [magnet_level]} {port_list2 buffer_name2 [magnet_level]} ...}
set var(mark_magnet_fixed)	true				; # [DCICC]: whether mark cells as fixed after 'magnet_placement', only work when [magnet_level] >= 1.
set var(default_corner)		ss_v1p08_125c			; # [PB][DCICC]: define which corner used for non-mcmm flow, all support list plz see file 'define_libraries.tcl'.
								; #          default_corner : T40G : ttdb0p9v25c
								; #          default_corner : T28HPM : tt0p9v25c
								; #          default_corner : T16FFP : tt0p8v25c
set var(default_rctype)		rcworst				; # [DCICC]: define which rctype used for non-mcmm flow, now support : typical, cbest, cworst, rcbest, rcworst
set var(netlist2gds_flow)	false				; # [ICC]:   run "netlist => gds" flow, only run icc. you need add blockname.v to DC/out first! only non-mcmm mode.
set var(netlist2gds_opt)	false				; # [ICC]:   whether do optimization for netlist2gds_flow, default is dont_touch!
set var(icv,signoff_drc)	true				; # [ICC]:   whether do in-design signoff drc check.
set var(icv,signoff_autofix_drc) false				; # [ICC]:   whether do in-design signoff drc check && autofix.
set var(icv,signoff_metal_fill)		false			; # [ICC]:   whether do in-design signoff metal fill generation.
set var(icv,signoff_metal_fill,flat)	true			; # [ICC]:   whether to generate flattened fill.
set var(icv,signoff_metal_fill,setup_slack_threshold) off	; # [ICC]:   whether do timing-driven metal fill insertion. default is off, can set custom slack value, such as: 0 or 0.02.
set var(icv,signoff_metal_fill,selected_layers)	{}		; # [ICC]:   such as: {M2 M3 M4}, metal fill will only be generated by these layers, default is all available layers.
set var(output,splitgds)	false				; # [ICC]:   while output final gds, whether write different layer to different gds file. only for huge design.

#---------------------------------------------------------------------------------------
#	Optimization
#---------------------------------------------------------------------------------------
set var(flatten)		false				; # [DC]:    whether to flatten design
set var(keepHier)		{}				; # [DC]:    such as {instA instB}, these two instances will not be flattened,
								; #          these and only these two level will be keeped, all others will be flattend.
set var(top_no_new_cell)	false				; # [DCICC]: whether the compile command adds new cells to the top-level.
set var(ideal_sources)		{}				; # [DC]:    define ideal signals if needed.
set var(autobound_effort)	medium				; # [DC]:    set the effort level (low|medium|high|ultra) for 'auto-bounding', 
								; #          only work if 'designopt(autobound)' set to true.
set var(automesh_region)	off				; # [DCICC]: set the effort for auto-mesh regions (off|low|medium|high|ultra).
set var(preroute_focal_opt)	medium				; # [ICC]:   set the effort for preroute_focal_opt (medium|high).
set var(route_after_focal_opt)	false				; # [ICC]:   whether do "route_opt -incremental" after s05: focal_opt
set var(delay,awe_effort)	high				; # [ICC]:   set the effort for awe (low|medium|high).
set var(delay,arnoldi_effort)	high				; # [ICC]:   set the effort for arnoldi (low|medium|high|hybrid).
set var(extend,groups)		true				; # [DC]:    auto create path groups between different clocks.
set designopt(power)		true				; # [DCICC]: whether to optimize power, default is true.
set designopt(gate_clock)	false				; # [DC]:    Enables clock gating optimization, use *CKGTP* cells.
set designopt(self_gating)	false				; # [DC]:    Enables the execution of XOR self-gating insertion, use *CKGTP* cells.
set designopt(timing)		false				; # [DC]:    whether to do high-effort timing optimization in DC Ultra and Design Compiler Graphical.(more runtime)
set designopt(spg)		false				; # [DCICC]: whether to use SPG-Flow, default is true. If no DEF or Floorplan file is given,
								; #          this variable will be set to 'false' automatically, so don't worry about it.
set designopt(register_replication)	false			; # [DC]     whether to do automatic register replication in SPG-Flow(only work in 2013.12).
set designopt(icg_replication)	false				; # [ICC]    whether do ICG cell replication.
set designopt(autobound)	true				; # [DC]:    whether to use 'auto-bounding' flow to optimize timing, default is true.
set designopt(autoweight)	true				; # [DCICC]: whether to use 'auto-weight' flow to optimize timing, default it true.
set designopt(cong)		false				; # [DCICC]: whether to optimize congestions, default is false.
set designopt(auto_ndr_rule)	true				; # [ICC]:   whether do "Preroute Automatic Nondefault Routing Rule".
set designopt(focal_opt)	true				; # [ICC]:   whether to do final s05 focal opt!!!
set var(focal,xtalk)		0				; # [ICC]:   set delta_delay margin for xtalk_reduction of route_opt && focal_opt , such as 0.03. default is off.
set var(focal,drc)		false				; # [ICC]:   whether do focal_opt DRC fix.
set var(focal,fix_setup_group)	{*}				; # [ICC]:   define path group list for setup fixing
set var(focal,fix_hold_group)	{*}				; # [ICC]:   define path group list for hold fixing
set var(focal,power_critical_range)	0			; # [ICC]:   define critical range for focal_opt -power, such as : 0.010
set designopt(zrt_crt_prior)	false				; # [ICC]:   whether to route critical nets first, this can significantly improve QoR in some DESIGN!
set var(zrt_crt_slack)		0.1				; # [ICC]:   slack threshold for designopt(zrt_crt_prior), such as : 0.05 or 0.1
set var(sizing_seq_onroute)	false				; # [ICC]:   whether enable sequential cell sizing, only for 2013.12
set var(use_ceff)		false				; # [ICC]:   whether use Native Effective Capacitance for postroute DRC Fixing, only for 2013.12
set designopt(ccdopt)		false				; # [ICC]:   whether performing 'Concurrent Clock and Data Optimization', instead of traditional CTS. 
								; #          Only work when all clock are 'CTS' type, only for 2013.12(beta feature).
set var(ccdopt,ignored_groups)	{D-O D-L C-O}			; # [ICC]:   set ignored path groups while doing ccdopt. only work if '$designopt(ccdopt)' is 'true'.
set designopt(split_mesh)	true				; # [ICC]:   whether do seperated mesh split automatically, default is do it.
set designopt(fast_mode)	false				; # [DCICC]: Disable some advanced strategy of optimization, just run a basic quick flow, only for Quick estimation!
set designopt(create_abut_rules)	false			; # [ICC]:   whether apply abutment rule base on the value of 'var(abut_rules,*)' settings. only for T16FFP
set var(abut_rules,abut_rule)		6			; # [ICC]:   apply abutment rule base on cell pin density, can be set between 1~6.
								; #          only work if 'designopt(create_abut_rules)" is true.
set var(abut_rules,soft_keepout)	1			; # [ICC]:   apply abutment rule base on cost function, can be set between 1~6,
								; #          only work if 'designopt(create_abut_rules)" is true.
set designopt(high_resistance)	true				; # [ICC]:   High-resistance optimization for routing and postroute optimization. Only work for T16FF+.
set designopt(optimize_vias)	true				; # [ICC]:   whether do post-route via optimization.

#---------------------------------------------------------------------------------------
#	Design Constraints
#---------------------------------------------------------------------------------------
set var(max_tran_icc)		0.150				; # [DCICC]: set max transtion for icc
set var(max_tran_dc)		[expr {$var(max_tran_icc)*0.7}]	; # [DC]:    set max transtion for dc
set var(dc_clock_factor)	1.0				; # [DC]:    define clock period factor for DC, such as : 0.85~1.0
set var(clock_recover_phase)    s04                             ; # [ICC]:   recover clock period at which icc phase, only suport: s01, s02, s03, s04
set var(max_fanout)		32				; # [DCICC]: set max fanout
set var(default_input_delay) 	{0.050  0.050}			; # [DCICC]: set default input delay for all non-clock inputs,  {max_value min_value}
set var(default_output_delay) 	{0.050 -0.050}			; # [DCICC]: set default output delay for all outputs,		{max_value min_value}
set var(timing_preserve_slack_setup) 0.05
set var(timing_preserve_slack_hold) 0.05
set var(timing_derate_max)	1.0				; # [DCICC]: set timing derate for setup timing analysis, such as : 1.05 or 1.1
set var(timing_derate_min)	1.0				; # [DCICC]: set timing derate for hold timing analysis, such as : 0.95 or 0.9
set var(critical_range)		0				; # [DCICC]: set default critical range for current_design.
set var(physopt_area_critical_range)	0.020			; # [DCICC]: set critical range for physopt area optimization
set var(physopt_power_critical_range)	0.020			; # [DCICC]: set critical range for physopt power optimization

#---------------------------------------------------------------------------------------
#	Flow Structure
#---------------------------------------------------------------------------------------
set var(mw_lib_name,dc)		SYN_DC					; # [DCICC]: set default milkyway library name
set var(mw_lib_name,icc)	SYN					; # [DCICC]: set default milkyway library name
set var(src_list)		{}					; # [DC]:    set rtl file list, set this to instead the path '$var(src_path)'.
set var(src_path)		{../SRC/ }				; # [DC]:    set RTL paths, such as {path1 path2}, these values will also be added to 'search_path'
set var(analyze_lib)		{./work}				; # [DC]:    set default rtl analyze directory.
set var(dc_dp,flag)		${var(design_name)}_dc_icc_dp.flag	; # [DC]:    dc floorplan exploration flag file.
set var(dc_dp,dir)		DC_DP					; # [DC]:    directory for dc floorplan exploration.
set setting(design)		../CMD/common_setting_design.tcl	; # [ICC]:   common design setting
set setting(clock)		../CMD/common_setting_clock.tcl		; # [ICC]:   common CTS setting
set setting(route)		../CMD/common_setting_route.tcl		; # [DCICC]:   common route setting
set var(def)			../DEF/${var(design_name)}.def		; # [DCICC]: set one or more DEF files, such as {block.def block_components.def block_pin.def}.
set var(obs)			../DEF/${var(design_name)}.obs		; # [DCICC]: set obs file, which extracted by "getdef"
set var(dc_obs)			../DEF/${var(design_name)}_dc.obs	; # [DCICC]: set dc obs file, which extracted by "getdef"
set var(floorplan)		../DEF/${var(design_name)}.fp		; # [DCICC]: ICC Floorplan file
set var(phy_cons)		../CMD/${var(design_name)}.phy_cons.tcl ; # [DCICC]: physical constraint(floorplan) file
set var(phy_setting)		../CMD/additional_dc_phy.tcl		; # [DC]:    Custom DC physical constraints, before Compiler
set var(compile,constraints)	../CMD/additional_compile.tcl		; # [DC]:    Custom design constraints between 'compile_ultra' and 'compile_ultra -incremental'.
set var(place,constraints) 	../CMD/additional_place.tcl		; # [DCICC]: Custom Placement constraints(macro/blockage/guide), before placement
set var(netNDR,constraints)	../CMD/additional_netNDR.tcl		; # [DCICC]: Custom NDR for nets or net search patterns.
set var(route,constraints) 	../CMD/additional_route.tcl		; # [ICC]:   Custom Routing constraints, before routing
set var(focal,constraints) 	../CMD/additional_focal.tcl		; # [ICC]:   Custom focal_opt constraints, before focal_opt 
set var(cts,constraints) 	../CMD/additional_cts.tcl		; # [ICC]:   Custom CTS Settings.
set var(autofp,pin_cons)	../CMD/additional_autopin.tcl		; # [ICC]:   constraints for auto place pins, it works only if no DEF or Floorplan file is given.
set var(sdc_dc)			../CMD/additional_dc.sdc		; # [DC]:    set additional DC SDC.
set var(sdc_icc)		../CMD/additional_icc.sdc		; # [ICC]:   set additional ICC SDC.
set var(sdc_full)		../CMD/${var(design_name)}.sdc		; # [DCICC]: set FULL DC SDC, if this file exists, DC will ignore all others default SDC settings.
set var(eco_netlist)		{}					; # [ICC]:   set eco netlist files, only work with try_eco.tcl

#---------------------------------------------------------------------------------------
#	PT Options
#---------------------------------------------------------------------------------------
set var(pt,power_mode)		time_based                      		; # [PT/DMSA]:    averaged,  time_based,  leakage_variation
set var(pt,report_path)		PT						; # [PT/DMSA]:    define pt output directory.
set var(pt,netlist)		ICC/out/$var(design_name).v			; # [PT]:         define the default netlist file.
set var(pt,sdc)			ICC/out/$var(design_name).sdc			; # [PT]:         define the default full sdc constratints.
set var(pt,spef)		ICC/out/$var(design_name).spef			; # [PT]:         define the default spef file.
set var(pt,saif)		ICC/out/$var(design_name).saif			; # [PT/DMSA]:    define the default saif file.
set var(pt,final_def)		ICC/out/$var(design_name).def			; # [PT/DMSA]:    define the default full def file for physical-aware eco flow.
set var(pt,vcd_file)		{}                              		; # [PT/DMSA]:    {strip_path VCD_file}
set var(pt,vcd_time)		{}                              		; # [PT/DMSA]:    time window, {start_point end_point}
set var(pt,mkmodel)		false						; # [PT/DMSA]:    whether extract model
set var(pt,enable_eco)		false						; # [PT/DMSA]:    whether enable PT ECO Flow
set var(pt,eco_physical_mode)	open_site					; # [PT/DMSA]:    mode for Physically-Aware Fixing, support: 'none', 'open_site', 'occupied_site'
set var(pt,fix_stage_power)	false						; # [PT/DMSA]:    whether do eco power optimization
set var(pt,fix_stage_drc)	false						; # [PT/DMSA]:    whether do DRC fixing
set var(pt,fix_stage_timing,setup) true						; # [PT/DMSA]:    whether do setup timing fixing
set var(pt,fix_stage_timing,hold)  true						; # [PT/DMSA]:    whether do hold timing fixing
set var(pt,fix_drc_buf_list)	{*/*_BUF_*}					; # [PT/DMSA]:    define buffer list for drc fixing
set var(pt,fix_setup_group)	{*}						; # [PT/DMSA]:    define path group list for setup fixing
set var(pt,fix_hold_group)	{*}						; # [PT/DMSA]:    define path group list for hold fixing
set var(pt,fix_hold_buf_list)	{*/*_DEL_* */*_BUF_*}				; # [PT/DMSA]:    define buffer list for hold fixing
set var(pt,power_opt_margin)	0.000						; # [PT/DMSA]:    define setup margin for power optimization
set var(pt,setup_opt_slack)	0.000						; # [PT/DMSA]:    define setup target slack for timing optimization.
set var(pt,setup_opt_margin)	0.000						; # [PT/DMSA]:    define setup margin for timing optimization
set var(pt,hold_opt_slack)	0.000						; # [PT/DMSA]:    define hold target slack for timing optimization.
set var(pt,hold_opt_margin)	0.000						; # [PT/DMSA]:    define hold margin for timing optimization
set var(eco_scripts)		./$var(pt,report_path)/eco/eco_script.tcl	; # [PT/DMSA/ICC]: set eco script files, only work with try_eco.tcl
set var(pt,dmsa,path)           PT_DMSA						; # [DMSA]:       define pt dmsa-flow output directory.
set var(pt,dmsa,icc_path)	ICC						; # [DMSA]:       set default ICC dir for PT-DMSA flow.
set var(pt,dmsa,custom_verilog) {}						; # [DMSA]:       set custom verilog file for PT-DMSA flow,
										; #               default use "$var(pt,dmsa,icc_path)/out/$var(design_name).v"

#---------------------------------------------------------------------------------------
#	MCMM Definitions
#---------------------------------------------------------------------------------------
set var(use_mcmm_flow)		false						; # [DCICC]	whether use mcmm flow, default is non-mcmm flow.
										; # 		if set this to 'true', plz modify mcmm.tcl file as your need!
set var(use_aocvm)		false						; # [ICC]	only work when 'var(use_mcmm_flow)' is true
set var(aocvm_analysis_mode)	""						; # [ICC]	support :'','clock_network_only','separate_data_and_clock_metrics',
										; #			'combined_launch_capture_depth'
source ../CMD/mcmm.tcl
#---------------------------------------------------------------------------------------
#	Clock Definitions
#---------------------------------------------------------------------------------------
source ../CMD/clock.tcl

#---------------------------------------------------------------------------------------
#	Library Definitions
#---------------------------------------------------------------------------------------
source ../CMD/define_structure.tcl
source ../CMD/lib_macro.tcl

#---------------------------------------------------------------------------------------
#	Custom Definitions
#---------------------------------------------------------------------------------------
#source cus_value.tcl
