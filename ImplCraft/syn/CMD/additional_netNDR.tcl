########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	Define&&Apply net NDR rules, search pattern
########################################################################################
#Usage: define_routing_rule 	# define routing rule
#			[rule_name]
#			[-reference_rule_name ref_rule_name | -default_reference_rule]
#			[-widths {layer_name_and_width_pairs}]
#			[-spacings {layer_name_and_spacing_pairs}]
#			[-multiplier_width layer_width]
#			[-multiplier_spacing layer_spacing]
#
#Usage: set_net_routing_rule    # set net routing rule
#        [-rule rule]           (either name of a nondefault routing rule to set, or -default-  to set the default routing rule)
#        [-reroute normal|minorchange|freeze]
#                               (Net flag, default is normal)
#        [-timing_driven_spacing]
#                               (Enable Timing-Driven Spacing)
#        [-top_layer_probe AnyPort|OutPort|AllPort]
#                               (Top layer probe type)
#        nets                   (collection of nets)
#
#Usage: create_net_search_pattern    # Create net pattern
#        [-fanout_lower_limit number] (nets with fanouts equal or greater than lower limit)
#        [-fanout_upper_limit number] (nets with fanouts less than upper limit)
#        [-bbox_half_perimeter_lower_limit length] (bbox half perimeter equal or greater than lower limit)
#        [-bbox_half_perimeter_upper_limit length] (bbox half perimeter less than upper limit)
#        [-net_length_lower_limit length] (net length equal or greater than lower limit)
#        [-net_length_upper_limit length] (net length less than upper limit)
#        [-blocked_area_ratio_lower_limit percentage] (placement blockage coverage ratio equal or greater than lower limit: 
#                                Range: 0 to 1) [-blocked_area_ratio_upper_limit percentage]
#                               (placement blockage coverage ratio less than upper limit: Range: 0 to 1)
#        [-centered_within {llx lly urx ury}] (region)
#        [-setup_slack_lower_limit slack] (net slack equal or greater than lower limit)
#        [-setup_slack_upper_limit slack] (net slack less than upper limit)
#        [-aspect_ratio_lower_limit ratio] (bbox shape (horizontal width/vertical height) ratio equal or greater than lower limit)
#        [-aspect_ratio_upper_limit ratio] (bbox shape (horizontal width/vertical height) ratio less than upper limit)
#        [-connect_to_port]     (nets connect to IO ports)
#        [-connect_to_macro]    (nets connect to macro)
#
#Usage: set_net_search_pattern_delay_estimation_options    # set delay estimation options for pattern(s)
#        -pattern id            (pattern id: Value >= 1)
#        [-default]             (restore to the default)
#        [-rule rule_name]      (rule name)
#        [-min_layer_name layer_name] (Minimum routing layer name)
#        [-max_layer_name layer_name] (Maximum routing layer name)
#
#Usage: set_net_search_pattern_priority    # set net pattern match priority
#        -default               (Set to default pattern match priority)
#        id list                (options to be passed to net pattern matching)
#
#Usage: get_matching_nets_for_pattern    # Get matched nets for a certain net pattern
#---------------------------------------------------------------------------------------
#	Method1: Applying nondefault routing rules on specific nets:
#	Method2: Applying nondefault routing rules on nets identified by a net pattern
#---------------------------------------------------------------------------------------
#
#set_net_routing_rule -rule rule_name list_of_nets
#
#set id [create_net_search_pattern ...]
#set_net_search_pattern_delay_estimation_options -pattern id [-rule rule_name]
