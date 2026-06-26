########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
########################################################################################
###	common setup
########################################################################################
close_mw_lib
set source_mw_cel	$var(design_name)
set target_mw_cel	$var(design_name)

copy_mw_cel -overwrite	-from_library ../WORK/SYN -from $source_mw_cel \
			-to_library   SYN         -to   $target_mw_cel

exit
