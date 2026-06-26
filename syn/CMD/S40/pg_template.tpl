########################################################################################
######  DCICC FLOW - Version 4.1.0 (2015-10-15), For T40 PG Templates
######  Owner : Anonymous , rc
########################################################################################
template : sw4c_pg_mesh_vertical(p_layer,p_width,p_spacing,p_pitch,p_offset) {
	layer : @p_layer {
		direction : vertical
		width : @p_width
		spacing : @p_spacing
		pitch : @p_pitch
		offset_type : centerline
		offset_start : boundary
		offset : @p_offset
		trim_strap : true
	}
	advanced_rule : on {
		stack_vias : adjacent
		honor_advanced_via_rules : on
	}
}
template : sw4c_pg_mesh_horizontal(p_layer,p_width,p_spacing,p_pitch,p_offset) {
	layer : @p_layer {
		direction : horizontal
		width : @p_width
		spacing : @p_spacing
		pitch : @p_pitch
		offset_type : centerline
		offset_start :  boundary
		offset : @p_offset
		trim_strap : true
	}
	advanced_rule : on {
		stack_vias : adjacent
		honor_advanced_via_rules : on
	}
}
