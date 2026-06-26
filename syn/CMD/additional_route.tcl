########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	CUSTOM Routing SETTING
########################################################################################
#Usage: set_optimization_strategy    # set optimization strategy
#        [-default]             (reset all optimization strategy to default value)
#        [-tns_effort string]   (TNS optimization effort level. (medium|high))
#        [-high_resistance boolean-string]
#                               (High R Flow for advanced node. (true/false))
#
#Usage: set_net_routing_layer_constraints    # Set routing layer constraints for net(s)
#        -min_layer_name min_layer_name
#                               (Minimum routing layer name)
#        -max_layer_name max_layer_name
#                               (Maximum routing layer name)
#        [-min_layer_mode soft|allow_pin_connection|hard]
#                               (control strength of net-based min layer constraint)
#        [-max_layer_mode soft|allow_pin_connection|hard]
#                               (control strength of net-based max layer constraint)
#        [-min_layer_mode_soft_cost low|medium|high]
#                               (control cost penalty of net-based soft min layer constraint)
#        [-max_layer_mode_soft_cost low|medium|high]
#                               (control cost penalty of net-based soft max layer constraint)
#        object_list            (nets)
