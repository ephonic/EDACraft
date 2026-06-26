########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
#---------------------------------------------------------------------------------------
#       define Structure
#---------------------------------------------------------------------------------------
set tech_structure {
	project_params	{
		PCIE	{
			process		T40G
			autofp_script	../CMD/T40G/autofp_sw4c.tcl
		}
		default	{
			process		S40
			autofp_script	../CMD/T16FFP/autofp_tpns.tcl
		}
	}
	process2file	{
		S40	{
			define_library		../CMD/S40/define_libraries.tcl
			file_create_track	../CMD/S40/cmd_create_track.tcl
		}
	}
}
