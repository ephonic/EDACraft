########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  CUSTOM DC PHYSICAL SETTING
########################################################################################
###	Usage: create_route_guide    # create route guide
###        [-name string]         (route guide name)
###        [-no_signal_layers string]
###                               (layers on which signal routing isn't allowed)
###        [-no_preroute_layers string]
###                               (layers on which preroute isn't allowed)
###        [-preferred_direction_only_layers string]
###                               (layers on which non-preferred wire isn't allowed)
###        -coordinate rect       (route guide bounding box)
###        [-zero_min_spacing]    (allow zero min spacing)
###        [-repair_as_single_sbox]
###                               (repair as single sbox)
###        [-horizontal_track_utilization integer]
###                               (horizontal track utilization: 
###                                Range: 0 to 100)
###        [-vertical_track_utilization integer]
###                               (vertical track utilization: 
###                                Range: 0 to 100)
########################################################################################
###	Usage: create_placement_blockage    # Create placement blockage
###	        [-name name]           (name for the placement keepout)
###	        [-blocked_percentage integer]
###	                               (blockaged percentage:: 
###	                                Range: 0 to 100)
###	        [-type <hard|soft|partial>]
###	                               (hard|soft|partial type)
###	        -bbox {X1 Y1 X2 Y2}    (blockage bounding box)
###	        [-no_register]         (block register cell)
###	        [-no_rp_group]         (block relative placement cell)
###	        [-no_pin]              (block pin assignment)
###	        [-no_hard_macro]       (block hard macro)
###	        [-buffer_only]         (allow only buffers)
###	        [-category attr name]  (user-defined attribute name)
###	        [-blocked_layers string]
###	                               (blocked layers)
########################################################################################
###	Usage: create_bounds    # create bounds
###	        [-name string]         ( name of the bound)
###	        [-type string]         (to specify the type of the bound (soft|hard), default is soft)
###	        [-exclusive]           (exclusive move bound)
###	        [-coordinate list]     (list of lower-left and upper-right coordinates: {llx1 lly1 urx1 ury1 ...})
###	        [-polygon list]        ({{x_0 y_0} {x_1 y_1} ... {x_n y_n}})
###	        [-dimension list]      (specify the width and height of the bounding box {W H})
###	        [-effort string]       (the effort level (low|medium|high|ultra) to bring cells closer in a group bound (default is medium))
###	        [-cycle_color]         (allows tool assign a color)
###	        [-color 0-63]          (color of the move bound. string or index)
###	        [cell name(s)]         (the list of cells)
########################################################################################
###	Usage: create_rp_group    # Create rp groups
###	        [-design owning_design]
###	                               (design in which to create the rp group)
###	        [-columns num_columns] (number of columns for the rp group: 
###	                                Value >= 1)
###	        [-rows num_rows]       (number of rows for the rp group: 
###	                                Value >= 1)
###	        [-alignment alignment_type]
###	                               (Alignment type to be used for this rp group.)
###	        [-move_effort <low | medium | high>]
###	                               (Effort level to be used for this rp group.)
###	        [-pin_align_name pin_align_name]
###	                               (default name for pin alignment)
###	        [-utilization utilization_value]
###	                               (utilization for rp group: 
###	                                Range: 0 to 1)
###	        [-ignore]              (ignore this RP group)
###	        [-x_offset x_offset_microns]
###	                               (The x offset in microns to place this group relative to the origin of the chip)
###	        [-y_offset y_offset_microns]
###	                               (The y offset in microns to place this group relative to the origin of the chip)
###	        [-cts_option <fixed_placement | size_only>]
###	                               (RP cells to be made fixed during clock_opt)
###	        [-route_opt_option <fixed_placement | in_place_size_only >]
###	                               (RP cells to be made fixed during route_opt)
###	        [-psynopt_option <fixed_placement | size_only | all_optimization>]
###	                               (RP cells to be made fixed during psynopt)
###	        [-allow_keepout_over_tapcell <false|true>]
###	                               (Allow RP hard keepout to be overlapped with tap cells)
###	        [-allow_non_rp_cells]  (allow non RP cells in unutilized space of RP during refine_placement)
###	        [-group_orient <default | N | FN | S | FS>]
###	                               (Orientation to be used for this RP group)
###	        [-cell_orient_opt]     (Allow orientation optimization of the RP cells)
###	        [-auto_blockage]       (Disallow buffer insertion within RP regions during psynopt and route_opt)
###	        [-disable_buffering]   (Disallow buffer insertion on RP nets during psynopt and route_opt)
###	        [-anchor_corner bottom-left | bottom-right | top-left | top-right | rp-location]
###	                               (Anchor corner to be used for this rp group.)
###	        [-place_around_fixed_cells  none | all | standard | physical_only]
###	                               (Options to place RP group around fixed cells.)
###	        [-placement_type  bit_slice | compression | vertical_compression ]
###	                               (Options for how to tile)
###	        [-ignore_rows site rows to be ignored]
###	                               (rp_ignore_row_name of site rows to be ignored)
###	        [-anchor_column column number]
###	                               (anchor column for rp-location anchor_type: 
###	                                Value >= 0)
###	        [-anchor_row row number]
###	                               (anchor row for rp-location anchor_type: 
###	                                Value >= 0)
###	        list of group_names    (list of names of rp groups to create)
########################################################################################
#create_bounds -name m_ro -dimension {100 100} [get_cells m_ro*]
#create_bounds -cycle_color [get_cells m_ro]
#create_bounds -cycle_color [get_cells m_wb]
#create_bounds -cycle_color [get_cells m_exe0]
#create_bounds -cycle_color [get_cells m_exe1]
#create_bounds -cycle_color [get_cells m_spcl]
#create_bounds -cycle_color [get_cells m_io]
