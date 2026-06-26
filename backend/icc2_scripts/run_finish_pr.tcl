

####### add GDCAP
#create_stdcell_fillers -lib_cells {*/FILLECOCAP12_A9TR40 */FILLECOCAP24_A9TR40 */FILLECOCAP3_A9TR40 */FILLECOCAP48_A9TR40 */FILLECOCAP6_A9TR40}
#remove_stdcell_fillers_with_violation

####### add DCAP
remove_placement_spacing_rules -all

create_stdcell_fillers -lib_cells {*/DCAP64BWP30P140UHVT */DCAP32BWP30P140UHVT */DCAP16BWP30P140UHVT */DCAP8BWP30P140UHVT */DCAP4BWP30P140UHVT} -rules no_1x
remove_stdcell_fillers_with_violation

####### add filler
create_stdcell_fillers -lib_cells {*/FILL64BWP30P140UHVT */FILL32BWP30P140UHVT */FILL16BWP30P140UHVT */FILL8BWP30P140UHVT */FILL4BWP30P140UHVT */FILL3BWP30P140UHVT */FILL2BWP30P140UHVT */GFILLBWP30P140UHVT} -rules no_1x






source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl

####### save
save_lib
save_block
save_block -as 11_finish_pr

####### write netlist
write_verilog -compress gzip -exclude {scalar_wire_declaration leaf_module_declarations pg_objects end_cap_cells well_taps filler_cells pad_spacer_cells physical_only_cells cover_cells} -hierarchy all ./out/top.v

####### write def
write_def -include_tech_via_definitions -version 5.8 -compress gzip./db_out/mcu_top.def

####### write gds
set mapping_file "/share/home/limuhan/Libraries/TSMC28/gdsout_7X2Z.map"
set gds_file "./output/top.gds"
set_app_options -name file.gds.contact_prefix -value top
#write_gds -unit 1000 -compress -fill include -keep_data_type -layer_map $mapping_file -output_pin all -long_names -layer_   icc_default ./db_out/mcu_top.gds

write_gds -unit 1000 -long_names -design top -lib_cell_view frame -compress -layer_map $mapping_file -keep_data_type -output_pin geometry -fill include $gds_file

####### write pg netlist
remove_cells {u_pvd u_power_switch u_por u_voltage_regulator u_adc_wrapper/u_adc u_pll_wrapper/u_pll}
write_verilog -split_bus -hierarchy all -force_no_reference {*/PFILL* */PCORNER*} -exclude {flip_chip_pad_cells pad_space} ./db_out/mcu_top.pg.v
