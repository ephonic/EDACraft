########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	Clock Setting
########################################################################################
###     define mesh clock setting
set var(mesh_trunk_multiple_pitch)      8                       ; # set default Mesh Trunk width
set var(mesh_trunk_spacing)             {40 40}                 ; # set trunk spacing, {"spacing between horizontal metals" "spacing between vertical metals"}
set var(mesh_spacing_scalar)		1			; # 0.6~1.0
###     var(mesh_trunk_multiple_pitch) && var(mesh_trunk_spacing) are common variables, they effect all clocks.
###     if some have special needs, plz set custom_mesh_trunk_setting variable follow the example shows below.
###     example : you have 5 clocks : ck1 ck2 ck3 ck4 ck5 ck6, and all top metals have been set as 'M5',
###     then also add these setting
###     syntax: 
###     set custom_mesh_trunk_setting(clockname)        {trunk_multi {hori_trunk_num vert_trunk_num}}
###
###     set custom_mesh_trunk_setting(ck2)      {6}
###     set custom_mesh_trunk_setting(ck4)      {12}
###     set custom_mesh_trunk_setting(ck6)      {8 {1 3}}
###
###     so ck1,ck3,ck5 use 0.05(M5 defaultWidth)*10=0.5u as mesh trunk width.
###     ck2 use 0.05*6=0.3u as mesh trunk.
###     ck4 use 0.05*12=0.6u as width.
###     ck6 use 0.05*8=0.4u as width and 1 horizontal trunk with 3 vertical trunks

######  Default virtual clock
set var(ref_clock)      {ref_ck 0.625}

######	Define Custom Clocks, the syntax shows as below:
###	clock(name)     {period(ns) setup(ns) hold(ns) transition(ns) TopMetal 'CTS/MESH' {region points}}
###	for example     {0.666  0.083   0.165   0.100   M5 MESH {p1_llx p1_lly p1_urx p1_ury}}		; # define simple rectangle
###	                {0.666  0.083   0.165   0.100   M5 MESH {p1_llx p1_lly p1_urx p1_ury \
###								 p2_llx p2_lly p2_urx p2_ury \
###								 ...}}					; # define complex polygon shapes
###                     {0.666  0.083   0.165   0.100   M5 CTS}

#set clock(CTS_CLOCK)			{0.625 0.083 0.165 0.100 M5 CTS}
#set clock(MESH_CLOCK)			{0.625 0.083 0.165 0.100 M5 MESH}
#set clock(MESH_CLOCK_WITH_REGION)	{0.625 0.083 0.165 0.100 M5 MESH {100 100 200 200}}

######  if the name of the clock port/pin isn't equal to the clock name, you need also define variable 'clock_pin'.
###     clock_pin(clock_name)   {clock pin/port list}
###     for example     :
#set clock_pin(GClk)    {GClk_rf GClk_xf}
#set clock_pin(refck1)  Xinst1/refck1

######  Define gater area if needed, scripts will auto set PLACEMENT && SIGNAL ROUTING Blockage in these areas!
### such as : set clock_gater_area {{llx lly urx ury [{obs metal list..}]} {...} ... }
### for example :
###     (1): set placement blockage and routing blockage for all layers(M1~M10)
###     set clock_gater_area    {
###     {10 12.5 40 50}
###     {100 125 120 165}
###     {50 50 60 60}
###     }
###
###     (2): set placement blockage and routing blockage for special layers, utilization is optional(0~100).
###     set clock_gater_area    {
###     {10 12.5 40 50          {M1 M2 M3 M4}           }
###     {100 125 120 165        {M1 M2 {M3 40} {M4 60}} }
###     {50 50 60 60            {M1 M2 {M3 M4 40}}
###     }
