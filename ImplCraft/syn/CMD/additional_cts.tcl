########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	CUSTOM CTS SETTING
########################################################################################
#Usage: set_clock_tree_options    # set clock tree options
#        [-clock_trees <clock>] (list of clock )
#        [-layer_list <list>]   (layers enabled for clock tree routing)
#        [-layer_list_for_sinks <list>]
#                               (layers enabled for clock tree routing)
#        [-target_skew <value>] (skew constraint)
#        [-target_early_delay <value>]
#                               (minimum insertion delay)
#        [-max_capacitance <value>]
#                               (maximum capacitance DRC constraint)
#        [-max_transition <value>]
#                               (maximum transition DRC constraint)
#        [-leaf_max_transition <value>]
#                               (Leaf maximum transition DRC constraint)
#        [-use_leaf_max_transition_on_macros <true|false>]
#                               (allow macro pin to be treated as leaf pin.)
#        [-use_leaf_max_transition_on_exceptions <true|false>]
#                               (allow CTS exception pins to be treated as leaf pin.)
#        [-max_rc_delay_constraint <value in time unit>]
#                               (maximum RC delay constraint)
#        [-max_rc_scale_factor <rc scale factor>]
#                               (maximum RC delay constraint using a scale factor)
#        [-max_fanout <value>]  (maximum fanout DRC constraint)
#        [-routing_rule <rule_name>]
#                               (name of a non-default routing rule to use for clock tree nets)
#        [-routing_rule_for_sinks <rule_name>]
#                               (name of a non-default routing rule to use for clock tree nets)
#        [-use_default_routing_for_sinks <value>]
#                               (use default rules for sinks at bottom k-1 levels)
#        [-use_leaf_routing_rule_for_sinks <value>]
#                               (use sink rules for sinks at bottom k-1 levels)
#        [-buffer_relocation <true|false>]
#                               (allow to relocate buffers during optimization)
#        [-gate_sizing <true|false>]
#                               (allow to size gates during optimization)
#        [-gate_relocation <true|false>]
#                               (allow to relocate gates during optimization)
#        [-buffer_sizing <true|false>]
#                               (whether buffers in one level may have different sizes)
#        [-insert_boundary_cell <true|false>]
#                               (Insert boundary cell near clock input port)
#        [-logic_level_balance <true|false>]
#                               (build logic level balanced clock tree)
#        [-ocv_clustering <true|false>]
#                               (use OCV aware clustering)
#        [-ocv_path_sharing <true|false>]
#                               (making more clock path sharing for ocv tolerance)
#        [-advanced_drc_fixing <true|false>]
#                               (enable advanced drc fixing)
#        [-operating_condition <string>]
#                               (min | max (default) | min_max)
#        [-config_file_read <file_name>]
#                               (name of config file to be used for guiding clock tree synthesis)
#        [-config_file_write <file_name>]
#                               (name of config file to write the configuration of the synthesized clock tree)
#
#
#Usage: set_latency_adjustment_options    # User Specified Latency Adjustment Directives
#        [-from_clock <clock_name>]
#                               (a clock name or clock object)
#        [-to_clock <collection_or_string_list>]
#                               (list of clock names or collection of clock objects)
#        [-exclude_clock <collection_or_string_list>]
#                               (list of clock names or collection of clock objects)
#        [-latency float]       (user specified latency)
#
#
#Usage: set_inter_clock_delay_options    # set inter clock delay balance options
#        [-balance_group source_objects]
#                               (set a list of clocks as a group for balancing)
#        [-balance_group_name string]
#                               (clock group name for clocks under -balance_group)
#        [-delay_offset float]  (delay offset)
#        [-offset_to source_objects]
#                               (list of clock the offset applies to)
#        [-offset_from offset_from_obj]
#                               (clock the offset applies from)
#        [-offset_from_group string]
#                               (clock the offset applies from a balance group)
#        [-target_delay_clock target_clock_obj]
#                               (list of clocks to get a target delay)
#        [-target_delay_value float]
#                               (target delay value)
#        [-honor_sdc boolean-string]
#                               (honor latencey defined in SDC)
#
#
#Usage: set_instance_based_routing_rule    # set_instance_based_routing_rule
#        -routing_rule <rule_name>
#                               (Name of the non-default routing rule compatible with specified pin)
#        [-layer_list <list>]   (layers enabled for routing)
#        <list>                 (pins to be processed)
########################################################################################
