########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
#---------------------------------------------------------------------------------------
#	Define db&&mw for macros, default corner key can see variable : var(default_corner)
#	plz define attributes(origin/orientation/fix_or_not/keepout_margin ...) 
#	in file : 'addtional_place.tcl', or add them in def file as components.
#	add optional key 'lef', only for PT-ECO.
#---------------------------------------------------------------------------------------
set lib_macro {
	db	{
		ss_v1p08_125c	"  \
		/mnt/Data/Project/Cluster/DCICC/WORK_rc001_1/DC_netlist/DB/sadrlsck42p256x32m2b1w0c0p0d0t0.db \
                /mnt/Data/Project/Cluster/DCICC/WORK_rc001_1/DC_netlist/DB/sadrlsck42p512x32m2b1w0c0p0d0t0.db \
                /mnt/Data/Project/Cluster/DCICC/WORK_rc001_1/DC_netlist/DB/sadrlsck42p512x64m2b1w0c0p0d0t0.db \
                /mnt/Data/Project/Cluster/DCICC/WORK_rc001_1/DC_netlist/DB/sasrlsck41p512x64m2b1w0c0p0d0t0.db \
		/mnt/Data/Project/Cluster/MEM_lib/mc/sram_256_32_ss_1p08v_1p08v_125c.db \
		/mnt/Data/Project/Cluster/MEM_lib/mc/sram_512_32_ss_1p08v_1p08v_125c.db \
		/mnt/Data/Project/Cluster/MEM_lib/mc/sram_512_64_ss_1p08v_1p08v_125c.db \
			"

	}
	mw	"/mnt/Data/Project/Cluster/MEM_lib/mem.mdb"
	lef	" \
		/mnt/Data/Project/Cluster/MEM_lib/lef/sram_256_32.lef \
		/mnt/Data/Project/Cluster/MEM_lib/lef/sram_512_32.lef \
		/mnt/Data/Project/Cluster/MEM_lib/lef/sram_512_64.lef \
		"
}
