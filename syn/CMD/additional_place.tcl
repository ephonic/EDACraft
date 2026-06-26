########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
########################################################################################
#---------------------------------------------------------------------------------------
#	define macro placement
#---------------------------------------------------------------------------------------
#set_keepout_margin		# Creates keepout margin around cells/masters
#create_placement_blockage	# Create placement blockage
#create_route_guide		# Create route guide
#---------------------------------------------------------------------------------------
#	for example:
#	Constraints for both DCG && ICC
#---------------------------------------------------------------------------------------
###	define macro cell placement
#set_attribute [get_cells -all m_mc_maq_synqdatbuf_inst_inst] orientation FN
#set_attribute [get_cells -all m_mc_maq_synqdatbuf_inst_inst] origin {2816 208.8}
#set_attribute [get_cells -all m_mc_maq_synqdatbuf_inst_inst] is_fixed true
#set_keepout_margin -type hard -outer {5 5 5 5} [get_cells m_mc_maq_synqdatbuf_inst_inst]
#set_keepout_margin -type hard -outer {5 5 5 5} -all_macros
#set_keepout_margin -type hard -outer {5 5 5 5} -macro_masters {RF2P256W136B2M1bc_HD RF2P512W136B2M1bc_HD}
#set_keepout_margin -type hard -outer {5 5 5 5} -macro_instances {u_gmac_rx_fifo_m_rf2p512w136b2m1bc u_gmac_tx_fifo_m_rf2p256w136b2m1bc}

###	define custom placement constraints

###	define placement blockage
#create_placement_blockage -coordinate {{97.300 89.040} {116.760 129.360}} -name placement_blockage_0 -type hard
#create_route_guide -no_preroute_layers {M1 M2} -no_signal_layers {M1 M2} -coordinate {{97.300 88.970} {116.830 129.430}}

#---------------------------------------------------------------------------------------
#	Constraints for ICC Only! (Important!!!)
#---------------------------------------------------------------------------------------
###	such as below
#if {$synopsys_program_name == "icc_shell"} {
#	set_fp_macro_options -legal_orientations {E W FE FW} [all_macro_cells]
#	set_fp_placement_strategy -macros_on_edge auto -auto_grouping high -sliver_size 15 -congestion_effort high
#}
