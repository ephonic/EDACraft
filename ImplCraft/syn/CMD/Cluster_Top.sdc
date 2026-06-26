###################################################################

# Created by write_sdc on Wed Jan 27 04:55:43 2021

###################################################################
set sdc_version 2.1

set_units -time ns -resistance kOhm -capacitance pF -voltage V -current mA
set_wire_load_mode top
set_max_capacitance 0.0066474 [current_design]
set_max_area 0
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports clk]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports RESET]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_North_clk]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_South_clk]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_East_clk]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_West_clk]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports CinFIFO_clk]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports CoutFIFO_clk]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports PCore_push_clk_bak_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports SoC_CinFIFO_push_req_n_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{SoC_CinFIFO_push_data_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports SoC_CCi_Sourcesel_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports SoC_CoutFIFO_pop_req_n_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports SoC_CCo_Sourcesel_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports SoC_CCo_Intcflag_Reset_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports DMA_State_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_state_Rsel_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Flag_set_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Flag_set_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Flag_set_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Flag_set_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Flag_set_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Block_Wsel_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Block_Wsel_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Block_Wsel_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Block_Wsel_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports CrossMemory_Wen_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data1_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data1_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data2_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data2_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data3_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data3_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data4_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data4_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data5_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data5_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data6_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data6_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data7_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data7_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{CrossMemory_Data8_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {CrossMemory_Data8_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_North_full_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[38]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[37]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[36]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[35]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[34]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[33]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[32]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_North_data_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_North_wen_n_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_North_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_North_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_South_full_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[38]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[37]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[36]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[35]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[34]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[33]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[32]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_South_data_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_South_wen_n_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_South_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_South_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_East_full_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[38]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[37]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[36]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[35]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[34]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[33]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[32]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_East_data_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_East_wen_n_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_East_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_East_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_West_full_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[38]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[37]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[36]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[35]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[34]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[33]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[32]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_West_data_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports NoC_West_wen_n_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_West_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{Neighborstate_West_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_Router_XY_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_Router_XY_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_Router_XY_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {NoC_Router_XY_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports Back_en_n_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {PCore_sel_bak_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {PCore_sel_bak_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports PCore_push_req_n_bak_i]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {PCore_A_bak_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {PCore_A_bak_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {PCore_A_bak_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {PCore_A_bak_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports {PCore_A_bak_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[31]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[30]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[29]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[28]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[27]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[26]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[25]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[24]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[23]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[22]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[21]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[20]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[19]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[18]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[17]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[16]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[15]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[14]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[13]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[12]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[11]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[10]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[9]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[8]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[7]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[6]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[5]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[4]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[3]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[2]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[1]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports                          \
{PCore_push_data_bak_i[0]}]
set_driving_cell -lib_cell BUFV10RD_12TL40 [get_ports PCore_pop_req_n_i]
set_load -pin_load 0.0099711 [get_ports SoC_CinFIFO_push_af_o]
set_load -pin_load 0.0099711 [get_ports SoC_CinFIFO_push_full_o]
set_load -pin_load 0.0099711 [get_ports SoC_CinFIFO_push_empty_o]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[31]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[30]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[29]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[28]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[27]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[26]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[25]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[24]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[23]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[22]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[21]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[20]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[19]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[18]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[17]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[16]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[15]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[14]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[13]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[12]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[11]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[10]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[9]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[8]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[7]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[6]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[5]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[4]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[3]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[2]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[1]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CoutFIFO_pop_data_o[0]}]
set_load -pin_load 0.0099711 [get_ports SoC_CoutFIFO_pop_ae_o]
set_load -pin_load 0.0099711 [get_ports SoC_CoutFIFO_pop_empty_o]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[8]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[7]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[6]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[5]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[4]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[3]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[2]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[1]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Length_o[0]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Psrflag_o[3]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Psrflag_o[2]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Psrflag_o[1]}]
set_load -pin_load 0.0099711 [get_ports {SoC_CCo_Psrflag_o[0]}]
set_load -pin_load 0.0099711 [get_ports SoC_CCo_Intcflag_o]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[15]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[14]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[13]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[12]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[11]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[10]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[9]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[8]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[7]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[6]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[5]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[4]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[3]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[2]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[1]}]
set_load -pin_load 0.0099711 [get_ports {DMA_State_Rsel_o[0]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Flag_set_o[4]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Flag_set_o[3]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Flag_set_o[2]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Flag_set_o[1]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Flag_set_o[0]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Block_Wsel_o[3]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Block_Wsel_o[2]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Block_Wsel_o[1]}]
set_load -pin_load 0.0099711 [get_ports {DMA_Block_Wsel_o[0]}]
set_load -pin_load 0.0099711 [get_ports DMA_Wen_o]
set_load -pin_load 0.0099711 [get_ports CrossMemory_state_o]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data1_o[0]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data2_o[0]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data3_o[0]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data4_o[0]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data5_o[0]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data6_o[0]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data7_o[0]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[31]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[30]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[29]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[28]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[27]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[26]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[25]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[24]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[23]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[22]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[21]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[20]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[19]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[18]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[17]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[16]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[15]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[14]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[13]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[12]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[11]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[10]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[9]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[8]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[7]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[6]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[5]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[4]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[3]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[2]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[1]}]
set_load -pin_load 0.0099711 [get_ports {CrossMemory_Data8_o[0]}]
set_load -pin_load 0.0099711 [get_ports NoC_North_full_o]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[38]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[37]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[36]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[35]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[34]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[33]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[32]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[31]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[30]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[29]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[28]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[27]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[26]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[25]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[24]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[23]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[22]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[21]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[20]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[19]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[18]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[17]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[16]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[15]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[14]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[13]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[12]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[11]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[10]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[9]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[8]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[7]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[6]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[5]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[4]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[3]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[2]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[1]}]
set_load -pin_load 0.0099711 [get_ports {NoC_North_data_o[0]}]
set_load -pin_load 0.0099711 [get_ports NoC_North_wen_n_o]
set_load -pin_load 0.0099711 [get_ports NoC_South_full_o]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[38]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[37]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[36]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[35]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[34]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[33]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[32]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[31]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[30]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[29]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[28]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[27]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[26]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[25]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[24]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[23]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[22]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[21]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[20]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[19]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[18]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[17]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[16]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[15]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[14]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[13]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[12]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[11]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[10]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[9]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[8]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[7]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[6]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[5]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[4]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[3]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[2]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[1]}]
set_load -pin_load 0.0099711 [get_ports {NoC_South_data_o[0]}]
set_load -pin_load 0.0099711 [get_ports NoC_South_wen_n_o]
set_load -pin_load 0.0099711 [get_ports NoC_East_full_o]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[38]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[37]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[36]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[35]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[34]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[33]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[32]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[31]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[30]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[29]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[28]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[27]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[26]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[25]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[24]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[23]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[22]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[21]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[20]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[19]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[18]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[17]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[16]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[15]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[14]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[13]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[12]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[11]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[10]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[9]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[8]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[7]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[6]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[5]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[4]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[3]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[2]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[1]}]
set_load -pin_load 0.0099711 [get_ports {NoC_East_data_o[0]}]
set_load -pin_load 0.0099711 [get_ports NoC_East_wen_n_o]
set_load -pin_load 0.0099711 [get_ports NoC_West_full_o]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[38]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[37]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[36]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[35]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[34]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[33]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[32]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[31]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[30]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[29]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[28]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[27]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[26]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[25]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[24]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[23]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[22]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[21]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[20]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[19]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[18]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[17]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[16]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[15]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[14]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[13]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[12]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[11]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[10]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[9]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[8]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[7]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[6]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[5]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[4]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[3]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[2]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[1]}]
set_load -pin_load 0.0099711 [get_ports {NoC_West_data_o[0]}]
set_load -pin_load 0.0099711 [get_ports NoC_West_wen_n_o]
set_load -pin_load 0.0099711 [get_ports PCore_push_full_bak_o]
set_load -pin_load 0.0099711 [get_ports PCore_push_af_bak_o]
set_load -pin_load 0.0099711 [get_ports PCore_push_empty_bak_o]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[31]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[30]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[29]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[28]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[27]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[26]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[25]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[24]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[23]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[22]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[21]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[20]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[19]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[18]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[17]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[16]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[15]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[14]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[13]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[12]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[11]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[10]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[9]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[8]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[7]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[6]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[5]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[4]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[3]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[2]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[1]}]
set_load -pin_load 0.0099711 [get_ports {PCore_pop_data_bak_o[0]}]
set_load -pin_load 0.0099711 [get_ports PCore_pop_full_o]
set_load -pin_load 0.0099711 [get_ports PCore_pop_empty_o]
set_load -pin_load 0.0099711 [get_ports PCore_pop_ae_o]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[10]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[9]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[8]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[7]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[6]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_IW_Addr_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_inMCU_state_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_inMCU_state_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_inMCU_state_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_inMCU_state_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_inMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_inMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_outMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore0_outMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Busy_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Sclfinish_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Data_Valid_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Psr4_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Psr5_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Psr6_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Psr7_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore0_Psr8_o]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[9]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[8]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[7]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[6]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_IW_Addr_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_inMCU_state_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_inMCU_state_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_inMCU_state_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_inMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_inMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_outMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore1_outMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Busy_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Sclfinish_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Data_Valid_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Psr4_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Psr5_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Psr6_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Psr7_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore1_Psr8_o]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[10]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[9]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[8]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[7]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[6]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_IW_Addr_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_inMCU_state_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_inMCU_state_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_inMCU_state_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_inMCU_state_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_inMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_inMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_outMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore2_outMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Busy_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Sclfinish_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Data_Valid_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Psr4_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Psr5_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Psr6_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Psr7_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore2_Psr8_o]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[10]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[9]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[8]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[7]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[6]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_IW_Addr_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_inMCU_state_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_inMCU_state_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_inMCU_state_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_inMCU_state_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_inMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_inMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_outMCU_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_PCore3_outMCU_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Busy_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Sclfinish_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Data_Valid_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Psr4_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Psr5_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Psr6_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Psr7_o]
set_load -pin_load 0.0099711 [get_ports Test_PCore3_Psr8_o]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[9]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[8]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[7]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[6]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_IW_Addr_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_DMA_state_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_DMA_state_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_DMA_state_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_DMA_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCi_DMA_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[9]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[8]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[7]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[6]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[5]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[4]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[3]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_IW_Addr_o[0]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_DMA_state_o[2]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_DMA_state_o[1]}]
set_load -pin_load 0.0099711 [get_ports {Test_CCo_DMA_state_o[0]}]
set_load -pin_load 0.0099711 [get_ports PCore0_infifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore0_infifo_pop_empty]
set_load -pin_load 0.0099711 [get_ports PCore0_outfifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore0_outfifo_pop_empty]
set_load -pin_load 0.0099711 [get_ports PCore1_infifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore1_infifo_pop_empty]
set_load -pin_load 0.0099711 [get_ports PCore1_outfifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore1_outfifo_pop_empty]
set_load -pin_load 0.0099711 [get_ports PCore2_infifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore2_infifo_pop_empty]
set_load -pin_load 0.0099711 [get_ports PCore2_outfifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore2_outfifo_pop_empty]
set_load -pin_load 0.0099711 [get_ports PCore3_infifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore3_infifo_pop_empty]
set_load -pin_load 0.0099711 [get_ports PCore3_outfifo_push_full]
set_load -pin_load 0.0099711 [get_ports PCore3_outfifo_pop_empty]
set_ideal_network [get_ports clk]
set_ideal_network [get_ports RESET]
set_ideal_network [get_ports NoC_North_clk]
set_ideal_network [get_ports NoC_South_clk]
set_ideal_network [get_ports NoC_East_clk]
set_ideal_network [get_ports NoC_West_clk]
set_ideal_network [get_ports CinFIFO_clk]
set_ideal_network [get_ports CoutFIFO_clk]
set_ideal_network [get_ports PCore_push_clk_bak_i]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_EccMatrix/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_NOC/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_DMA/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_CrossMemory/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_KeyPool_G4/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_KeyPool_G3/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_KeyPool_G2/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_KeyPool_G1/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_PCore3/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_PCore2/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_PCore1/Q]
set_ideal_network -no_propagate  [get_pins Clock_Manager_map/CLK_Control_PCore0/Q]
set_ideal_network -no_propagate  [get_pins Reset_Unit_map/C119/Z]
set_ideal_network -no_propagate  [get_pins Reset_Unit_map/C123/Z]
set_ideal_network -no_propagate  [get_pins Reset_Unit_map/C121/Z]
set_ideal_network -no_propagate  [get_pins Reset_Unit_map/C120/Z]
set_ideal_network -no_propagate  [get_pins Reset_Unit_map/C122/Z]
set_ideal_network -no_propagate  [get_pins Reset_Unit_map/C125/Z]
set_ideal_network -no_propagate  [get_pins Reset_Unit_map/C124/Z]
create_clock [get_ports clk]  -period 3.2  -waveform {0 1.6}
set_clock_latency 0.1  [get_clocks clk]
set_clock_uncertainty 0.2  [get_clocks clk]
create_clock [get_ports NoC_North_clk]  -period 3.2  -waveform {0 1.6}
create_clock [get_ports NoC_South_clk]  -period 3.2  -waveform {0 1.6}
create_clock [get_ports NoC_East_clk]  -period 3.2  -waveform {0 1.6}
create_clock [get_ports NoC_West_clk]  -period 3.2  -waveform {0 1.6}
create_clock [get_ports CinFIFO_clk]  -period 3.2  -waveform {0 1.6}
create_clock [get_ports CoutFIFO_clk]  -period 3.2  -waveform {0 1.6}
create_clock [get_ports PCore_push_clk_bak_i]  -period 3.2  -waveform {0 1.6}
create_generated_clock [get_pins Backup_Unit_map/PCore3_CKMUX/Z]  -name clk_PCore3_inFIFO  -source [get_ports clk]  -divide_by 1
create_generated_clock [get_pins Backup_Unit_map/PCore2_CKMUX/Z]  -name clk_PCore2_inFIFO  -source [get_ports clk]  -divide_by 1
create_generated_clock [get_pins Backup_Unit_map/PCore1_CKMUX/Z]  -name clk_PCore1_inFIFO  -source [get_ports clk]  -divide_by 1
create_generated_clock [get_pins Backup_Unit_map/PCore0_CKMUX/Z]  -name clk_PCore0_inFIFO  -source [get_ports clk]  -divide_by 1
group_path -name INPUTS  -from [get_ports clk]
group_path -name INPUTS  -from [get_ports RESET]
group_path -name INPUTS  -from [list [get_ports NoC_North_clk] [get_ports NoC_South_clk] [get_ports    \
NoC_East_clk] [get_ports NoC_West_clk] [get_ports CinFIFO_clk] [get_ports      \
CoutFIFO_clk] [get_ports PCore_push_clk_bak_i] [get_ports                      \
SoC_CinFIFO_push_req_n_i] [get_ports {SoC_CinFIFO_push_data_i[31]}] [get_ports \
{SoC_CinFIFO_push_data_i[30]}] [get_ports {SoC_CinFIFO_push_data_i[29]}]       \
[get_ports {SoC_CinFIFO_push_data_i[28]}] [get_ports                           \
{SoC_CinFIFO_push_data_i[27]}] [get_ports {SoC_CinFIFO_push_data_i[26]}]       \
[get_ports {SoC_CinFIFO_push_data_i[25]}] [get_ports                           \
{SoC_CinFIFO_push_data_i[24]}] [get_ports {SoC_CinFIFO_push_data_i[23]}]       \
[get_ports {SoC_CinFIFO_push_data_i[22]}] [get_ports                           \
{SoC_CinFIFO_push_data_i[21]}] [get_ports {SoC_CinFIFO_push_data_i[20]}]       \
[get_ports {SoC_CinFIFO_push_data_i[19]}] [get_ports                           \
{SoC_CinFIFO_push_data_i[18]}] [get_ports {SoC_CinFIFO_push_data_i[17]}]       \
[get_ports {SoC_CinFIFO_push_data_i[16]}] [get_ports                           \
{SoC_CinFIFO_push_data_i[15]}] [get_ports {SoC_CinFIFO_push_data_i[14]}]       \
[get_ports {SoC_CinFIFO_push_data_i[13]}] [get_ports                           \
{SoC_CinFIFO_push_data_i[12]}] [get_ports {SoC_CinFIFO_push_data_i[11]}]       \
[get_ports {SoC_CinFIFO_push_data_i[10]}] [get_ports                           \
{SoC_CinFIFO_push_data_i[9]}] [get_ports {SoC_CinFIFO_push_data_i[8]}]         \
[get_ports {SoC_CinFIFO_push_data_i[7]}] [get_ports                            \
{SoC_CinFIFO_push_data_i[6]}] [get_ports {SoC_CinFIFO_push_data_i[5]}]         \
[get_ports {SoC_CinFIFO_push_data_i[4]}] [get_ports                            \
{SoC_CinFIFO_push_data_i[3]}] [get_ports {SoC_CinFIFO_push_data_i[2]}]         \
[get_ports {SoC_CinFIFO_push_data_i[1]}] [get_ports                            \
{SoC_CinFIFO_push_data_i[0]}] [get_ports SoC_CCi_Sourcesel_i] [get_ports       \
SoC_CoutFIFO_pop_req_n_i] [get_ports SoC_CCo_Sourcesel_i] [get_ports           \
SoC_CCo_Intcflag_Reset_i] [get_ports DMA_State_i] [get_ports                   \
{CrossMemory_state_Rsel_i[15]}] [get_ports {CrossMemory_state_Rsel_i[14]}]     \
[get_ports {CrossMemory_state_Rsel_i[13]}] [get_ports                          \
{CrossMemory_state_Rsel_i[12]}] [get_ports {CrossMemory_state_Rsel_i[11]}]     \
[get_ports {CrossMemory_state_Rsel_i[10]}] [get_ports                          \
{CrossMemory_state_Rsel_i[9]}] [get_ports {CrossMemory_state_Rsel_i[8]}]       \
[get_ports {CrossMemory_state_Rsel_i[7]}] [get_ports                           \
{CrossMemory_state_Rsel_i[6]}] [get_ports {CrossMemory_state_Rsel_i[5]}]       \
[get_ports {CrossMemory_state_Rsel_i[4]}] [get_ports                           \
{CrossMemory_state_Rsel_i[3]}] [get_ports {CrossMemory_state_Rsel_i[2]}]       \
[get_ports {CrossMemory_state_Rsel_i[1]}] [get_ports                           \
{CrossMemory_state_Rsel_i[0]}] [get_ports {CrossMemory_Flag_set_i[4]}]         \
[get_ports {CrossMemory_Flag_set_i[3]}] [get_ports                             \
{CrossMemory_Flag_set_i[2]}] [get_ports {CrossMemory_Flag_set_i[1]}]           \
[get_ports {CrossMemory_Flag_set_i[0]}] [get_ports                             \
{CrossMemory_Block_Wsel_i[3]}] [get_ports {CrossMemory_Block_Wsel_i[2]}]       \
[get_ports {CrossMemory_Block_Wsel_i[1]}] [get_ports                           \
{CrossMemory_Block_Wsel_i[0]}] [get_ports CrossMemory_Wen_i] [get_ports        \
{CrossMemory_Data1_i[31]}] [get_ports {CrossMemory_Data1_i[30]}] [get_ports    \
{CrossMemory_Data1_i[29]}] [get_ports {CrossMemory_Data1_i[28]}] [get_ports    \
{CrossMemory_Data1_i[27]}] [get_ports {CrossMemory_Data1_i[26]}] [get_ports    \
{CrossMemory_Data1_i[25]}] [get_ports {CrossMemory_Data1_i[24]}] [get_ports    \
{CrossMemory_Data1_i[23]}] [get_ports {CrossMemory_Data1_i[22]}] [get_ports    \
{CrossMemory_Data1_i[21]}] [get_ports {CrossMemory_Data1_i[20]}] [get_ports    \
{CrossMemory_Data1_i[19]}] [get_ports {CrossMemory_Data1_i[18]}] [get_ports    \
{CrossMemory_Data1_i[17]}] [get_ports {CrossMemory_Data1_i[16]}] [get_ports    \
{CrossMemory_Data1_i[15]}] [get_ports {CrossMemory_Data1_i[14]}] [get_ports    \
{CrossMemory_Data1_i[13]}] [get_ports {CrossMemory_Data1_i[12]}] [get_ports    \
{CrossMemory_Data1_i[11]}] [get_ports {CrossMemory_Data1_i[10]}] [get_ports    \
{CrossMemory_Data1_i[9]}] [get_ports {CrossMemory_Data1_i[8]}] [get_ports      \
{CrossMemory_Data1_i[7]}] [get_ports {CrossMemory_Data1_i[6]}] [get_ports      \
{CrossMemory_Data1_i[5]}] [get_ports {CrossMemory_Data1_i[4]}] [get_ports      \
{CrossMemory_Data1_i[3]}] [get_ports {CrossMemory_Data1_i[2]}] [get_ports      \
{CrossMemory_Data1_i[1]}] [get_ports {CrossMemory_Data1_i[0]}] [get_ports      \
{CrossMemory_Data2_i[31]}] [get_ports {CrossMemory_Data2_i[30]}] [get_ports    \
{CrossMemory_Data2_i[29]}] [get_ports {CrossMemory_Data2_i[28]}] [get_ports    \
{CrossMemory_Data2_i[27]}] [get_ports {CrossMemory_Data2_i[26]}] [get_ports    \
{CrossMemory_Data2_i[25]}] [get_ports {CrossMemory_Data2_i[24]}] [get_ports    \
{CrossMemory_Data2_i[23]}] [get_ports {CrossMemory_Data2_i[22]}] [get_ports    \
{CrossMemory_Data2_i[21]}] [get_ports {CrossMemory_Data2_i[20]}] [get_ports    \
{CrossMemory_Data2_i[19]}] [get_ports {CrossMemory_Data2_i[18]}] [get_ports    \
{CrossMemory_Data2_i[17]}] [get_ports {CrossMemory_Data2_i[16]}] [get_ports    \
{CrossMemory_Data2_i[15]}] [get_ports {CrossMemory_Data2_i[14]}] [get_ports    \
{CrossMemory_Data2_i[13]}] [get_ports {CrossMemory_Data2_i[12]}] [get_ports    \
{CrossMemory_Data2_i[11]}] [get_ports {CrossMemory_Data2_i[10]}] [get_ports    \
{CrossMemory_Data2_i[9]}] [get_ports {CrossMemory_Data2_i[8]}] [get_ports      \
{CrossMemory_Data2_i[7]}] [get_ports {CrossMemory_Data2_i[6]}] [get_ports      \
{CrossMemory_Data2_i[5]}] [get_ports {CrossMemory_Data2_i[4]}] [get_ports      \
{CrossMemory_Data2_i[3]}] [get_ports {CrossMemory_Data2_i[2]}] [get_ports      \
{CrossMemory_Data2_i[1]}] [get_ports {CrossMemory_Data2_i[0]}] [get_ports      \
{CrossMemory_Data3_i[31]}] [get_ports {CrossMemory_Data3_i[30]}] [get_ports    \
{CrossMemory_Data3_i[29]}] [get_ports {CrossMemory_Data3_i[28]}] [get_ports    \
{CrossMemory_Data3_i[27]}] [get_ports {CrossMemory_Data3_i[26]}] [get_ports    \
{CrossMemory_Data3_i[25]}] [get_ports {CrossMemory_Data3_i[24]}] [get_ports    \
{CrossMemory_Data3_i[23]}] [get_ports {CrossMemory_Data3_i[22]}] [get_ports    \
{CrossMemory_Data3_i[21]}] [get_ports {CrossMemory_Data3_i[20]}] [get_ports    \
{CrossMemory_Data3_i[19]}] [get_ports {CrossMemory_Data3_i[18]}] [get_ports    \
{CrossMemory_Data3_i[17]}] [get_ports {CrossMemory_Data3_i[16]}] [get_ports    \
{CrossMemory_Data3_i[15]}] [get_ports {CrossMemory_Data3_i[14]}] [get_ports    \
{CrossMemory_Data3_i[13]}] [get_ports {CrossMemory_Data3_i[12]}] [get_ports    \
{CrossMemory_Data3_i[11]}] [get_ports {CrossMemory_Data3_i[10]}] [get_ports    \
{CrossMemory_Data3_i[9]}] [get_ports {CrossMemory_Data3_i[8]}] [get_ports      \
{CrossMemory_Data3_i[7]}] [get_ports {CrossMemory_Data3_i[6]}] [get_ports      \
{CrossMemory_Data3_i[5]}] [get_ports {CrossMemory_Data3_i[4]}] [get_ports      \
{CrossMemory_Data3_i[3]}] [get_ports {CrossMemory_Data3_i[2]}] [get_ports      \
{CrossMemory_Data3_i[1]}] [get_ports {CrossMemory_Data3_i[0]}] [get_ports      \
{CrossMemory_Data4_i[31]}] [get_ports {CrossMemory_Data4_i[30]}] [get_ports    \
{CrossMemory_Data4_i[29]}] [get_ports {CrossMemory_Data4_i[28]}] [get_ports    \
{CrossMemory_Data4_i[27]}] [get_ports {CrossMemory_Data4_i[26]}] [get_ports    \
{CrossMemory_Data4_i[25]}] [get_ports {CrossMemory_Data4_i[24]}] [get_ports    \
{CrossMemory_Data4_i[23]}] [get_ports {CrossMemory_Data4_i[22]}] [get_ports    \
{CrossMemory_Data4_i[21]}] [get_ports {CrossMemory_Data4_i[20]}] [get_ports    \
{CrossMemory_Data4_i[19]}] [get_ports {CrossMemory_Data4_i[18]}] [get_ports    \
{CrossMemory_Data4_i[17]}] [get_ports {CrossMemory_Data4_i[16]}] [get_ports    \
{CrossMemory_Data4_i[15]}] [get_ports {CrossMemory_Data4_i[14]}] [get_ports    \
{CrossMemory_Data4_i[13]}] [get_ports {CrossMemory_Data4_i[12]}] [get_ports    \
{CrossMemory_Data4_i[11]}] [get_ports {CrossMemory_Data4_i[10]}] [get_ports    \
{CrossMemory_Data4_i[9]}] [get_ports {CrossMemory_Data4_i[8]}] [get_ports      \
{CrossMemory_Data4_i[7]}] [get_ports {CrossMemory_Data4_i[6]}] [get_ports      \
{CrossMemory_Data4_i[5]}] [get_ports {CrossMemory_Data4_i[4]}] [get_ports      \
{CrossMemory_Data4_i[3]}] [get_ports {CrossMemory_Data4_i[2]}] [get_ports      \
{CrossMemory_Data4_i[1]}] [get_ports {CrossMemory_Data4_i[0]}] [get_ports      \
{CrossMemory_Data5_i[31]}] [get_ports {CrossMemory_Data5_i[30]}] [get_ports    \
{CrossMemory_Data5_i[29]}] [get_ports {CrossMemory_Data5_i[28]}] [get_ports    \
{CrossMemory_Data5_i[27]}] [get_ports {CrossMemory_Data5_i[26]}] [get_ports    \
{CrossMemory_Data5_i[25]}] [get_ports {CrossMemory_Data5_i[24]}] [get_ports    \
{CrossMemory_Data5_i[23]}] [get_ports {CrossMemory_Data5_i[22]}] [get_ports    \
{CrossMemory_Data5_i[21]}] [get_ports {CrossMemory_Data5_i[20]}] [get_ports    \
{CrossMemory_Data5_i[19]}] [get_ports {CrossMemory_Data5_i[18]}] [get_ports    \
{CrossMemory_Data5_i[17]}] [get_ports {CrossMemory_Data5_i[16]}] [get_ports    \
{CrossMemory_Data5_i[15]}] [get_ports {CrossMemory_Data5_i[14]}] [get_ports    \
{CrossMemory_Data5_i[13]}] [get_ports {CrossMemory_Data5_i[12]}] [get_ports    \
{CrossMemory_Data5_i[11]}] [get_ports {CrossMemory_Data5_i[10]}] [get_ports    \
{CrossMemory_Data5_i[9]}] [get_ports {CrossMemory_Data5_i[8]}] [get_ports      \
{CrossMemory_Data5_i[7]}] [get_ports {CrossMemory_Data5_i[6]}] [get_ports      \
{CrossMemory_Data5_i[5]}] [get_ports {CrossMemory_Data5_i[4]}] [get_ports      \
{CrossMemory_Data5_i[3]}] [get_ports {CrossMemory_Data5_i[2]}] [get_ports      \
{CrossMemory_Data5_i[1]}] [get_ports {CrossMemory_Data5_i[0]}] [get_ports      \
{CrossMemory_Data6_i[31]}] [get_ports {CrossMemory_Data6_i[30]}] [get_ports    \
{CrossMemory_Data6_i[29]}] [get_ports {CrossMemory_Data6_i[28]}] [get_ports    \
{CrossMemory_Data6_i[27]}] [get_ports {CrossMemory_Data6_i[26]}] [get_ports    \
{CrossMemory_Data6_i[25]}] [get_ports {CrossMemory_Data6_i[24]}] [get_ports    \
{CrossMemory_Data6_i[23]}] [get_ports {CrossMemory_Data6_i[22]}] [get_ports    \
{CrossMemory_Data6_i[21]}] [get_ports {CrossMemory_Data6_i[20]}] [get_ports    \
{CrossMemory_Data6_i[19]}] [get_ports {CrossMemory_Data6_i[18]}] [get_ports    \
{CrossMemory_Data6_i[17]}] [get_ports {CrossMemory_Data6_i[16]}] [get_ports    \
{CrossMemory_Data6_i[15]}] [get_ports {CrossMemory_Data6_i[14]}] [get_ports    \
{CrossMemory_Data6_i[13]}] [get_ports {CrossMemory_Data6_i[12]}] [get_ports    \
{CrossMemory_Data6_i[11]}] [get_ports {CrossMemory_Data6_i[10]}] [get_ports    \
{CrossMemory_Data6_i[9]}] [get_ports {CrossMemory_Data6_i[8]}] [get_ports      \
{CrossMemory_Data6_i[7]}] [get_ports {CrossMemory_Data6_i[6]}] [get_ports      \
{CrossMemory_Data6_i[5]}] [get_ports {CrossMemory_Data6_i[4]}] [get_ports      \
{CrossMemory_Data6_i[3]}] [get_ports {CrossMemory_Data6_i[2]}] [get_ports      \
{CrossMemory_Data6_i[1]}] [get_ports {CrossMemory_Data6_i[0]}] [get_ports      \
{CrossMemory_Data7_i[31]}] [get_ports {CrossMemory_Data7_i[30]}] [get_ports    \
{CrossMemory_Data7_i[29]}] [get_ports {CrossMemory_Data7_i[28]}] [get_ports    \
{CrossMemory_Data7_i[27]}] [get_ports {CrossMemory_Data7_i[26]}] [get_ports    \
{CrossMemory_Data7_i[25]}] [get_ports {CrossMemory_Data7_i[24]}] [get_ports    \
{CrossMemory_Data7_i[23]}] [get_ports {CrossMemory_Data7_i[22]}] [get_ports    \
{CrossMemory_Data7_i[21]}] [get_ports {CrossMemory_Data7_i[20]}] [get_ports    \
{CrossMemory_Data7_i[19]}] [get_ports {CrossMemory_Data7_i[18]}] [get_ports    \
{CrossMemory_Data7_i[17]}] [get_ports {CrossMemory_Data7_i[16]}] [get_ports    \
{CrossMemory_Data7_i[15]}] [get_ports {CrossMemory_Data7_i[14]}] [get_ports    \
{CrossMemory_Data7_i[13]}] [get_ports {CrossMemory_Data7_i[12]}] [get_ports    \
{CrossMemory_Data7_i[11]}] [get_ports {CrossMemory_Data7_i[10]}] [get_ports    \
{CrossMemory_Data7_i[9]}] [get_ports {CrossMemory_Data7_i[8]}] [get_ports      \
{CrossMemory_Data7_i[7]}] [get_ports {CrossMemory_Data7_i[6]}] [get_ports      \
{CrossMemory_Data7_i[5]}] [get_ports {CrossMemory_Data7_i[4]}] [get_ports      \
{CrossMemory_Data7_i[3]}] [get_ports {CrossMemory_Data7_i[2]}] [get_ports      \
{CrossMemory_Data7_i[1]}] [get_ports {CrossMemory_Data7_i[0]}] [get_ports      \
{CrossMemory_Data8_i[31]}] [get_ports {CrossMemory_Data8_i[30]}] [get_ports    \
{CrossMemory_Data8_i[29]}] [get_ports {CrossMemory_Data8_i[28]}] [get_ports    \
{CrossMemory_Data8_i[27]}] [get_ports {CrossMemory_Data8_i[26]}] [get_ports    \
{CrossMemory_Data8_i[25]}] [get_ports {CrossMemory_Data8_i[24]}] [get_ports    \
{CrossMemory_Data8_i[23]}] [get_ports {CrossMemory_Data8_i[22]}] [get_ports    \
{CrossMemory_Data8_i[21]}] [get_ports {CrossMemory_Data8_i[20]}] [get_ports    \
{CrossMemory_Data8_i[19]}] [get_ports {CrossMemory_Data8_i[18]}] [get_ports    \
{CrossMemory_Data8_i[17]}] [get_ports {CrossMemory_Data8_i[16]}] [get_ports    \
{CrossMemory_Data8_i[15]}] [get_ports {CrossMemory_Data8_i[14]}] [get_ports    \
{CrossMemory_Data8_i[13]}] [get_ports {CrossMemory_Data8_i[12]}] [get_ports    \
{CrossMemory_Data8_i[11]}] [get_ports {CrossMemory_Data8_i[10]}] [get_ports    \
{CrossMemory_Data8_i[9]}] [get_ports {CrossMemory_Data8_i[8]}] [get_ports      \
{CrossMemory_Data8_i[7]}] [get_ports {CrossMemory_Data8_i[6]}] [get_ports      \
{CrossMemory_Data8_i[5]}] [get_ports {CrossMemory_Data8_i[4]}] [get_ports      \
{CrossMemory_Data8_i[3]}] [get_ports {CrossMemory_Data8_i[2]}] [get_ports      \
{CrossMemory_Data8_i[1]}] [get_ports {CrossMemory_Data8_i[0]}] [get_ports      \
NoC_North_full_i] [get_ports {NoC_North_data_i[38]}] [get_ports                \
{NoC_North_data_i[37]}] [get_ports {NoC_North_data_i[36]}] [get_ports          \
{NoC_North_data_i[35]}] [get_ports {NoC_North_data_i[34]}] [get_ports          \
{NoC_North_data_i[33]}] [get_ports {NoC_North_data_i[32]}] [get_ports          \
{NoC_North_data_i[31]}] [get_ports {NoC_North_data_i[30]}] [get_ports          \
{NoC_North_data_i[29]}] [get_ports {NoC_North_data_i[28]}] [get_ports          \
{NoC_North_data_i[27]}] [get_ports {NoC_North_data_i[26]}] [get_ports          \
{NoC_North_data_i[25]}] [get_ports {NoC_North_data_i[24]}] [get_ports          \
{NoC_North_data_i[23]}] [get_ports {NoC_North_data_i[22]}] [get_ports          \
{NoC_North_data_i[21]}] [get_ports {NoC_North_data_i[20]}] [get_ports          \
{NoC_North_data_i[19]}] [get_ports {NoC_North_data_i[18]}] [get_ports          \
{NoC_North_data_i[17]}] [get_ports {NoC_North_data_i[16]}] [get_ports          \
{NoC_North_data_i[15]}] [get_ports {NoC_North_data_i[14]}] [get_ports          \
{NoC_North_data_i[13]}] [get_ports {NoC_North_data_i[12]}] [get_ports          \
{NoC_North_data_i[11]}] [get_ports {NoC_North_data_i[10]}] [get_ports          \
{NoC_North_data_i[9]}] [get_ports {NoC_North_data_i[8]}] [get_ports            \
{NoC_North_data_i[7]}] [get_ports {NoC_North_data_i[6]}] [get_ports            \
{NoC_North_data_i[5]}] [get_ports {NoC_North_data_i[4]}] [get_ports            \
{NoC_North_data_i[3]}] [get_ports {NoC_North_data_i[2]}] [get_ports            \
{NoC_North_data_i[1]}] [get_ports {NoC_North_data_i[0]}] [get_ports            \
NoC_North_wen_n_i] [get_ports {Neighborstate_North_i[1]}] [get_ports           \
{Neighborstate_North_i[0]}] [get_ports NoC_South_full_i] [get_ports            \
{NoC_South_data_i[38]}] [get_ports {NoC_South_data_i[37]}] [get_ports          \
{NoC_South_data_i[36]}] [get_ports {NoC_South_data_i[35]}] [get_ports          \
{NoC_South_data_i[34]}] [get_ports {NoC_South_data_i[33]}] [get_ports          \
{NoC_South_data_i[32]}] [get_ports {NoC_South_data_i[31]}] [get_ports          \
{NoC_South_data_i[30]}] [get_ports {NoC_South_data_i[29]}] [get_ports          \
{NoC_South_data_i[28]}] [get_ports {NoC_South_data_i[27]}] [get_ports          \
{NoC_South_data_i[26]}] [get_ports {NoC_South_data_i[25]}] [get_ports          \
{NoC_South_data_i[24]}] [get_ports {NoC_South_data_i[23]}] [get_ports          \
{NoC_South_data_i[22]}] [get_ports {NoC_South_data_i[21]}] [get_ports          \
{NoC_South_data_i[20]}] [get_ports {NoC_South_data_i[19]}] [get_ports          \
{NoC_South_data_i[18]}] [get_ports {NoC_South_data_i[17]}] [get_ports          \
{NoC_South_data_i[16]}] [get_ports {NoC_South_data_i[15]}] [get_ports          \
{NoC_South_data_i[14]}] [get_ports {NoC_South_data_i[13]}] [get_ports          \
{NoC_South_data_i[12]}] [get_ports {NoC_South_data_i[11]}] [get_ports          \
{NoC_South_data_i[10]}] [get_ports {NoC_South_data_i[9]}] [get_ports           \
{NoC_South_data_i[8]}] [get_ports {NoC_South_data_i[7]}] [get_ports            \
{NoC_South_data_i[6]}] [get_ports {NoC_South_data_i[5]}] [get_ports            \
{NoC_South_data_i[4]}] [get_ports {NoC_South_data_i[3]}] [get_ports            \
{NoC_South_data_i[2]}] [get_ports {NoC_South_data_i[1]}] [get_ports            \
{NoC_South_data_i[0]}] [get_ports NoC_South_wen_n_i] [get_ports                \
{Neighborstate_South_i[1]}] [get_ports {Neighborstate_South_i[0]}] [get_ports  \
NoC_East_full_i] [get_ports {NoC_East_data_i[38]}] [get_ports                  \
{NoC_East_data_i[37]}] [get_ports {NoC_East_data_i[36]}] [get_ports            \
{NoC_East_data_i[35]}] [get_ports {NoC_East_data_i[34]}] [get_ports            \
{NoC_East_data_i[33]}] [get_ports {NoC_East_data_i[32]}] [get_ports            \
{NoC_East_data_i[31]}] [get_ports {NoC_East_data_i[30]}] [get_ports            \
{NoC_East_data_i[29]}] [get_ports {NoC_East_data_i[28]}] [get_ports            \
{NoC_East_data_i[27]}] [get_ports {NoC_East_data_i[26]}] [get_ports            \
{NoC_East_data_i[25]}] [get_ports {NoC_East_data_i[24]}] [get_ports            \
{NoC_East_data_i[23]}] [get_ports {NoC_East_data_i[22]}] [get_ports            \
{NoC_East_data_i[21]}] [get_ports {NoC_East_data_i[20]}] [get_ports            \
{NoC_East_data_i[19]}] [get_ports {NoC_East_data_i[18]}] [get_ports            \
{NoC_East_data_i[17]}] [get_ports {NoC_East_data_i[16]}] [get_ports            \
{NoC_East_data_i[15]}] [get_ports {NoC_East_data_i[14]}] [get_ports            \
{NoC_East_data_i[13]}] [get_ports {NoC_East_data_i[12]}] [get_ports            \
{NoC_East_data_i[11]}] [get_ports {NoC_East_data_i[10]}] [get_ports            \
{NoC_East_data_i[9]}] [get_ports {NoC_East_data_i[8]}] [get_ports              \
{NoC_East_data_i[7]}] [get_ports {NoC_East_data_i[6]}] [get_ports              \
{NoC_East_data_i[5]}] [get_ports {NoC_East_data_i[4]}] [get_ports              \
{NoC_East_data_i[3]}] [get_ports {NoC_East_data_i[2]}] [get_ports              \
{NoC_East_data_i[1]}] [get_ports {NoC_East_data_i[0]}] [get_ports              \
NoC_East_wen_n_i] [get_ports {Neighborstate_East_i[1]}] [get_ports             \
{Neighborstate_East_i[0]}] [get_ports NoC_West_full_i] [get_ports              \
{NoC_West_data_i[38]}] [get_ports {NoC_West_data_i[37]}] [get_ports            \
{NoC_West_data_i[36]}] [get_ports {NoC_West_data_i[35]}] [get_ports            \
{NoC_West_data_i[34]}] [get_ports {NoC_West_data_i[33]}] [get_ports            \
{NoC_West_data_i[32]}] [get_ports {NoC_West_data_i[31]}] [get_ports            \
{NoC_West_data_i[30]}] [get_ports {NoC_West_data_i[29]}] [get_ports            \
{NoC_West_data_i[28]}] [get_ports {NoC_West_data_i[27]}] [get_ports            \
{NoC_West_data_i[26]}] [get_ports {NoC_West_data_i[25]}] [get_ports            \
{NoC_West_data_i[24]}] [get_ports {NoC_West_data_i[23]}] [get_ports            \
{NoC_West_data_i[22]}] [get_ports {NoC_West_data_i[21]}] [get_ports            \
{NoC_West_data_i[20]}] [get_ports {NoC_West_data_i[19]}] [get_ports            \
{NoC_West_data_i[18]}] [get_ports {NoC_West_data_i[17]}] [get_ports            \
{NoC_West_data_i[16]}] [get_ports {NoC_West_data_i[15]}] [get_ports            \
{NoC_West_data_i[14]}] [get_ports {NoC_West_data_i[13]}] [get_ports            \
{NoC_West_data_i[12]}] [get_ports {NoC_West_data_i[11]}] [get_ports            \
{NoC_West_data_i[10]}] [get_ports {NoC_West_data_i[9]}] [get_ports             \
{NoC_West_data_i[8]}] [get_ports {NoC_West_data_i[7]}] [get_ports              \
{NoC_West_data_i[6]}] [get_ports {NoC_West_data_i[5]}] [get_ports              \
{NoC_West_data_i[4]}] [get_ports {NoC_West_data_i[3]}] [get_ports              \
{NoC_West_data_i[2]}] [get_ports {NoC_West_data_i[1]}] [get_ports              \
{NoC_West_data_i[0]}] [get_ports NoC_West_wen_n_i] [get_ports                  \
{Neighborstate_West_i[1]}] [get_ports {Neighborstate_West_i[0]}] [get_ports    \
{NoC_Router_XY_i[3]}] [get_ports {NoC_Router_XY_i[2]}] [get_ports              \
{NoC_Router_XY_i[1]}] [get_ports {NoC_Router_XY_i[0]}] [get_ports Back_en_n_i] \
[get_ports {PCore_sel_bak_i[1]}] [get_ports {PCore_sel_bak_i[0]}] [get_ports   \
PCore_push_req_n_bak_i] [get_ports {PCore_A_bak_i[4]}] [get_ports              \
{PCore_A_bak_i[3]}] [get_ports {PCore_A_bak_i[2]}] [get_ports                  \
{PCore_A_bak_i[1]}] [get_ports {PCore_A_bak_i[0]}] [get_ports                  \
{PCore_push_data_bak_i[31]}] [get_ports {PCore_push_data_bak_i[30]}]           \
[get_ports {PCore_push_data_bak_i[29]}] [get_ports                             \
{PCore_push_data_bak_i[28]}] [get_ports {PCore_push_data_bak_i[27]}]           \
[get_ports {PCore_push_data_bak_i[26]}] [get_ports                             \
{PCore_push_data_bak_i[25]}] [get_ports {PCore_push_data_bak_i[24]}]           \
[get_ports {PCore_push_data_bak_i[23]}] [get_ports                             \
{PCore_push_data_bak_i[22]}] [get_ports {PCore_push_data_bak_i[21]}]           \
[get_ports {PCore_push_data_bak_i[20]}] [get_ports                             \
{PCore_push_data_bak_i[19]}] [get_ports {PCore_push_data_bak_i[18]}]           \
[get_ports {PCore_push_data_bak_i[17]}] [get_ports                             \
{PCore_push_data_bak_i[16]}] [get_ports {PCore_push_data_bak_i[15]}]           \
[get_ports {PCore_push_data_bak_i[14]}] [get_ports                             \
{PCore_push_data_bak_i[13]}] [get_ports {PCore_push_data_bak_i[12]}]           \
[get_ports {PCore_push_data_bak_i[11]}] [get_ports                             \
{PCore_push_data_bak_i[10]}] [get_ports {PCore_push_data_bak_i[9]}] [get_ports \
{PCore_push_data_bak_i[8]}] [get_ports {PCore_push_data_bak_i[7]}] [get_ports  \
{PCore_push_data_bak_i[6]}] [get_ports {PCore_push_data_bak_i[5]}] [get_ports  \
{PCore_push_data_bak_i[4]}] [get_ports {PCore_push_data_bak_i[3]}] [get_ports  \
{PCore_push_data_bak_i[2]}] [get_ports {PCore_push_data_bak_i[1]}] [get_ports  \
{PCore_push_data_bak_i[0]}] [get_ports PCore_pop_req_n_i]]
group_path -name OUTPUTS  -to [list [get_ports SoC_CinFIFO_push_af_o] [get_ports                        \
SoC_CinFIFO_push_full_o] [get_ports SoC_CinFIFO_push_empty_o] [get_ports       \
{SoC_CoutFIFO_pop_data_o[31]}] [get_ports {SoC_CoutFIFO_pop_data_o[30]}]       \
[get_ports {SoC_CoutFIFO_pop_data_o[29]}] [get_ports                           \
{SoC_CoutFIFO_pop_data_o[28]}] [get_ports {SoC_CoutFIFO_pop_data_o[27]}]       \
[get_ports {SoC_CoutFIFO_pop_data_o[26]}] [get_ports                           \
{SoC_CoutFIFO_pop_data_o[25]}] [get_ports {SoC_CoutFIFO_pop_data_o[24]}]       \
[get_ports {SoC_CoutFIFO_pop_data_o[23]}] [get_ports                           \
{SoC_CoutFIFO_pop_data_o[22]}] [get_ports {SoC_CoutFIFO_pop_data_o[21]}]       \
[get_ports {SoC_CoutFIFO_pop_data_o[20]}] [get_ports                           \
{SoC_CoutFIFO_pop_data_o[19]}] [get_ports {SoC_CoutFIFO_pop_data_o[18]}]       \
[get_ports {SoC_CoutFIFO_pop_data_o[17]}] [get_ports                           \
{SoC_CoutFIFO_pop_data_o[16]}] [get_ports {SoC_CoutFIFO_pop_data_o[15]}]       \
[get_ports {SoC_CoutFIFO_pop_data_o[14]}] [get_ports                           \
{SoC_CoutFIFO_pop_data_o[13]}] [get_ports {SoC_CoutFIFO_pop_data_o[12]}]       \
[get_ports {SoC_CoutFIFO_pop_data_o[11]}] [get_ports                           \
{SoC_CoutFIFO_pop_data_o[10]}] [get_ports {SoC_CoutFIFO_pop_data_o[9]}]        \
[get_ports {SoC_CoutFIFO_pop_data_o[8]}] [get_ports                            \
{SoC_CoutFIFO_pop_data_o[7]}] [get_ports {SoC_CoutFIFO_pop_data_o[6]}]         \
[get_ports {SoC_CoutFIFO_pop_data_o[5]}] [get_ports                            \
{SoC_CoutFIFO_pop_data_o[4]}] [get_ports {SoC_CoutFIFO_pop_data_o[3]}]         \
[get_ports {SoC_CoutFIFO_pop_data_o[2]}] [get_ports                            \
{SoC_CoutFIFO_pop_data_o[1]}] [get_ports {SoC_CoutFIFO_pop_data_o[0]}]         \
[get_ports SoC_CoutFIFO_pop_ae_o] [get_ports SoC_CoutFIFO_pop_empty_o]         \
[get_ports {SoC_CCo_Length_o[8]}] [get_ports {SoC_CCo_Length_o[7]}] [get_ports \
{SoC_CCo_Length_o[6]}] [get_ports {SoC_CCo_Length_o[5]}] [get_ports            \
{SoC_CCo_Length_o[4]}] [get_ports {SoC_CCo_Length_o[3]}] [get_ports            \
{SoC_CCo_Length_o[2]}] [get_ports {SoC_CCo_Length_o[1]}] [get_ports            \
{SoC_CCo_Length_o[0]}] [get_ports {SoC_CCo_Psrflag_o[3]}] [get_ports           \
{SoC_CCo_Psrflag_o[2]}] [get_ports {SoC_CCo_Psrflag_o[1]}] [get_ports          \
{SoC_CCo_Psrflag_o[0]}] [get_ports SoC_CCo_Intcflag_o] [get_ports              \
{DMA_State_Rsel_o[15]}] [get_ports {DMA_State_Rsel_o[14]}] [get_ports          \
{DMA_State_Rsel_o[13]}] [get_ports {DMA_State_Rsel_o[12]}] [get_ports          \
{DMA_State_Rsel_o[11]}] [get_ports {DMA_State_Rsel_o[10]}] [get_ports          \
{DMA_State_Rsel_o[9]}] [get_ports {DMA_State_Rsel_o[8]}] [get_ports            \
{DMA_State_Rsel_o[7]}] [get_ports {DMA_State_Rsel_o[6]}] [get_ports            \
{DMA_State_Rsel_o[5]}] [get_ports {DMA_State_Rsel_o[4]}] [get_ports            \
{DMA_State_Rsel_o[3]}] [get_ports {DMA_State_Rsel_o[2]}] [get_ports            \
{DMA_State_Rsel_o[1]}] [get_ports {DMA_State_Rsel_o[0]}] [get_ports            \
{DMA_Flag_set_o[4]}] [get_ports {DMA_Flag_set_o[3]}] [get_ports                \
{DMA_Flag_set_o[2]}] [get_ports {DMA_Flag_set_o[1]}] [get_ports                \
{DMA_Flag_set_o[0]}] [get_ports {DMA_Block_Wsel_o[3]}] [get_ports              \
{DMA_Block_Wsel_o[2]}] [get_ports {DMA_Block_Wsel_o[1]}] [get_ports            \
{DMA_Block_Wsel_o[0]}] [get_ports DMA_Wen_o] [get_ports CrossMemory_state_o]   \
[get_ports {CrossMemory_Data1_o[31]}] [get_ports {CrossMemory_Data1_o[30]}]    \
[get_ports {CrossMemory_Data1_o[29]}] [get_ports {CrossMemory_Data1_o[28]}]    \
[get_ports {CrossMemory_Data1_o[27]}] [get_ports {CrossMemory_Data1_o[26]}]    \
[get_ports {CrossMemory_Data1_o[25]}] [get_ports {CrossMemory_Data1_o[24]}]    \
[get_ports {CrossMemory_Data1_o[23]}] [get_ports {CrossMemory_Data1_o[22]}]    \
[get_ports {CrossMemory_Data1_o[21]}] [get_ports {CrossMemory_Data1_o[20]}]    \
[get_ports {CrossMemory_Data1_o[19]}] [get_ports {CrossMemory_Data1_o[18]}]    \
[get_ports {CrossMemory_Data1_o[17]}] [get_ports {CrossMemory_Data1_o[16]}]    \
[get_ports {CrossMemory_Data1_o[15]}] [get_ports {CrossMemory_Data1_o[14]}]    \
[get_ports {CrossMemory_Data1_o[13]}] [get_ports {CrossMemory_Data1_o[12]}]    \
[get_ports {CrossMemory_Data1_o[11]}] [get_ports {CrossMemory_Data1_o[10]}]    \
[get_ports {CrossMemory_Data1_o[9]}] [get_ports {CrossMemory_Data1_o[8]}]      \
[get_ports {CrossMemory_Data1_o[7]}] [get_ports {CrossMemory_Data1_o[6]}]      \
[get_ports {CrossMemory_Data1_o[5]}] [get_ports {CrossMemory_Data1_o[4]}]      \
[get_ports {CrossMemory_Data1_o[3]}] [get_ports {CrossMemory_Data1_o[2]}]      \
[get_ports {CrossMemory_Data1_o[1]}] [get_ports {CrossMemory_Data1_o[0]}]      \
[get_ports {CrossMemory_Data2_o[31]}] [get_ports {CrossMemory_Data2_o[30]}]    \
[get_ports {CrossMemory_Data2_o[29]}] [get_ports {CrossMemory_Data2_o[28]}]    \
[get_ports {CrossMemory_Data2_o[27]}] [get_ports {CrossMemory_Data2_o[26]}]    \
[get_ports {CrossMemory_Data2_o[25]}] [get_ports {CrossMemory_Data2_o[24]}]    \
[get_ports {CrossMemory_Data2_o[23]}] [get_ports {CrossMemory_Data2_o[22]}]    \
[get_ports {CrossMemory_Data2_o[21]}] [get_ports {CrossMemory_Data2_o[20]}]    \
[get_ports {CrossMemory_Data2_o[19]}] [get_ports {CrossMemory_Data2_o[18]}]    \
[get_ports {CrossMemory_Data2_o[17]}] [get_ports {CrossMemory_Data2_o[16]}]    \
[get_ports {CrossMemory_Data2_o[15]}] [get_ports {CrossMemory_Data2_o[14]}]    \
[get_ports {CrossMemory_Data2_o[13]}] [get_ports {CrossMemory_Data2_o[12]}]    \
[get_ports {CrossMemory_Data2_o[11]}] [get_ports {CrossMemory_Data2_o[10]}]    \
[get_ports {CrossMemory_Data2_o[9]}] [get_ports {CrossMemory_Data2_o[8]}]      \
[get_ports {CrossMemory_Data2_o[7]}] [get_ports {CrossMemory_Data2_o[6]}]      \
[get_ports {CrossMemory_Data2_o[5]}] [get_ports {CrossMemory_Data2_o[4]}]      \
[get_ports {CrossMemory_Data2_o[3]}] [get_ports {CrossMemory_Data2_o[2]}]      \
[get_ports {CrossMemory_Data2_o[1]}] [get_ports {CrossMemory_Data2_o[0]}]      \
[get_ports {CrossMemory_Data3_o[31]}] [get_ports {CrossMemory_Data3_o[30]}]    \
[get_ports {CrossMemory_Data3_o[29]}] [get_ports {CrossMemory_Data3_o[28]}]    \
[get_ports {CrossMemory_Data3_o[27]}] [get_ports {CrossMemory_Data3_o[26]}]    \
[get_ports {CrossMemory_Data3_o[25]}] [get_ports {CrossMemory_Data3_o[24]}]    \
[get_ports {CrossMemory_Data3_o[23]}] [get_ports {CrossMemory_Data3_o[22]}]    \
[get_ports {CrossMemory_Data3_o[21]}] [get_ports {CrossMemory_Data3_o[20]}]    \
[get_ports {CrossMemory_Data3_o[19]}] [get_ports {CrossMemory_Data3_o[18]}]    \
[get_ports {CrossMemory_Data3_o[17]}] [get_ports {CrossMemory_Data3_o[16]}]    \
[get_ports {CrossMemory_Data3_o[15]}] [get_ports {CrossMemory_Data3_o[14]}]    \
[get_ports {CrossMemory_Data3_o[13]}] [get_ports {CrossMemory_Data3_o[12]}]    \
[get_ports {CrossMemory_Data3_o[11]}] [get_ports {CrossMemory_Data3_o[10]}]    \
[get_ports {CrossMemory_Data3_o[9]}] [get_ports {CrossMemory_Data3_o[8]}]      \
[get_ports {CrossMemory_Data3_o[7]}] [get_ports {CrossMemory_Data3_o[6]}]      \
[get_ports {CrossMemory_Data3_o[5]}] [get_ports {CrossMemory_Data3_o[4]}]      \
[get_ports {CrossMemory_Data3_o[3]}] [get_ports {CrossMemory_Data3_o[2]}]      \
[get_ports {CrossMemory_Data3_o[1]}] [get_ports {CrossMemory_Data3_o[0]}]      \
[get_ports {CrossMemory_Data4_o[31]}] [get_ports {CrossMemory_Data4_o[30]}]    \
[get_ports {CrossMemory_Data4_o[29]}] [get_ports {CrossMemory_Data4_o[28]}]    \
[get_ports {CrossMemory_Data4_o[27]}] [get_ports {CrossMemory_Data4_o[26]}]    \
[get_ports {CrossMemory_Data4_o[25]}] [get_ports {CrossMemory_Data4_o[24]}]    \
[get_ports {CrossMemory_Data4_o[23]}] [get_ports {CrossMemory_Data4_o[22]}]    \
[get_ports {CrossMemory_Data4_o[21]}] [get_ports {CrossMemory_Data4_o[20]}]    \
[get_ports {CrossMemory_Data4_o[19]}] [get_ports {CrossMemory_Data4_o[18]}]    \
[get_ports {CrossMemory_Data4_o[17]}] [get_ports {CrossMemory_Data4_o[16]}]    \
[get_ports {CrossMemory_Data4_o[15]}] [get_ports {CrossMemory_Data4_o[14]}]    \
[get_ports {CrossMemory_Data4_o[13]}] [get_ports {CrossMemory_Data4_o[12]}]    \
[get_ports {CrossMemory_Data4_o[11]}] [get_ports {CrossMemory_Data4_o[10]}]    \
[get_ports {CrossMemory_Data4_o[9]}] [get_ports {CrossMemory_Data4_o[8]}]      \
[get_ports {CrossMemory_Data4_o[7]}] [get_ports {CrossMemory_Data4_o[6]}]      \
[get_ports {CrossMemory_Data4_o[5]}] [get_ports {CrossMemory_Data4_o[4]}]      \
[get_ports {CrossMemory_Data4_o[3]}] [get_ports {CrossMemory_Data4_o[2]}]      \
[get_ports {CrossMemory_Data4_o[1]}] [get_ports {CrossMemory_Data4_o[0]}]      \
[get_ports {CrossMemory_Data5_o[31]}] [get_ports {CrossMemory_Data5_o[30]}]    \
[get_ports {CrossMemory_Data5_o[29]}] [get_ports {CrossMemory_Data5_o[28]}]    \
[get_ports {CrossMemory_Data5_o[27]}] [get_ports {CrossMemory_Data5_o[26]}]    \
[get_ports {CrossMemory_Data5_o[25]}] [get_ports {CrossMemory_Data5_o[24]}]    \
[get_ports {CrossMemory_Data5_o[23]}] [get_ports {CrossMemory_Data5_o[22]}]    \
[get_ports {CrossMemory_Data5_o[21]}] [get_ports {CrossMemory_Data5_o[20]}]    \
[get_ports {CrossMemory_Data5_o[19]}] [get_ports {CrossMemory_Data5_o[18]}]    \
[get_ports {CrossMemory_Data5_o[17]}] [get_ports {CrossMemory_Data5_o[16]}]    \
[get_ports {CrossMemory_Data5_o[15]}] [get_ports {CrossMemory_Data5_o[14]}]    \
[get_ports {CrossMemory_Data5_o[13]}] [get_ports {CrossMemory_Data5_o[12]}]    \
[get_ports {CrossMemory_Data5_o[11]}] [get_ports {CrossMemory_Data5_o[10]}]    \
[get_ports {CrossMemory_Data5_o[9]}] [get_ports {CrossMemory_Data5_o[8]}]      \
[get_ports {CrossMemory_Data5_o[7]}] [get_ports {CrossMemory_Data5_o[6]}]      \
[get_ports {CrossMemory_Data5_o[5]}] [get_ports {CrossMemory_Data5_o[4]}]      \
[get_ports {CrossMemory_Data5_o[3]}] [get_ports {CrossMemory_Data5_o[2]}]      \
[get_ports {CrossMemory_Data5_o[1]}] [get_ports {CrossMemory_Data5_o[0]}]      \
[get_ports {CrossMemory_Data6_o[31]}] [get_ports {CrossMemory_Data6_o[30]}]    \
[get_ports {CrossMemory_Data6_o[29]}] [get_ports {CrossMemory_Data6_o[28]}]    \
[get_ports {CrossMemory_Data6_o[27]}] [get_ports {CrossMemory_Data6_o[26]}]    \
[get_ports {CrossMemory_Data6_o[25]}] [get_ports {CrossMemory_Data6_o[24]}]    \
[get_ports {CrossMemory_Data6_o[23]}] [get_ports {CrossMemory_Data6_o[22]}]    \
[get_ports {CrossMemory_Data6_o[21]}] [get_ports {CrossMemory_Data6_o[20]}]    \
[get_ports {CrossMemory_Data6_o[19]}] [get_ports {CrossMemory_Data6_o[18]}]    \
[get_ports {CrossMemory_Data6_o[17]}] [get_ports {CrossMemory_Data6_o[16]}]    \
[get_ports {CrossMemory_Data6_o[15]}] [get_ports {CrossMemory_Data6_o[14]}]    \
[get_ports {CrossMemory_Data6_o[13]}] [get_ports {CrossMemory_Data6_o[12]}]    \
[get_ports {CrossMemory_Data6_o[11]}] [get_ports {CrossMemory_Data6_o[10]}]    \
[get_ports {CrossMemory_Data6_o[9]}] [get_ports {CrossMemory_Data6_o[8]}]      \
[get_ports {CrossMemory_Data6_o[7]}] [get_ports {CrossMemory_Data6_o[6]}]      \
[get_ports {CrossMemory_Data6_o[5]}] [get_ports {CrossMemory_Data6_o[4]}]      \
[get_ports {CrossMemory_Data6_o[3]}] [get_ports {CrossMemory_Data6_o[2]}]      \
[get_ports {CrossMemory_Data6_o[1]}] [get_ports {CrossMemory_Data6_o[0]}]      \
[get_ports {CrossMemory_Data7_o[31]}] [get_ports {CrossMemory_Data7_o[30]}]    \
[get_ports {CrossMemory_Data7_o[29]}] [get_ports {CrossMemory_Data7_o[28]}]    \
[get_ports {CrossMemory_Data7_o[27]}] [get_ports {CrossMemory_Data7_o[26]}]    \
[get_ports {CrossMemory_Data7_o[25]}] [get_ports {CrossMemory_Data7_o[24]}]    \
[get_ports {CrossMemory_Data7_o[23]}] [get_ports {CrossMemory_Data7_o[22]}]    \
[get_ports {CrossMemory_Data7_o[21]}] [get_ports {CrossMemory_Data7_o[20]}]    \
[get_ports {CrossMemory_Data7_o[19]}] [get_ports {CrossMemory_Data7_o[18]}]    \
[get_ports {CrossMemory_Data7_o[17]}] [get_ports {CrossMemory_Data7_o[16]}]    \
[get_ports {CrossMemory_Data7_o[15]}] [get_ports {CrossMemory_Data7_o[14]}]    \
[get_ports {CrossMemory_Data7_o[13]}] [get_ports {CrossMemory_Data7_o[12]}]    \
[get_ports {CrossMemory_Data7_o[11]}] [get_ports {CrossMemory_Data7_o[10]}]    \
[get_ports {CrossMemory_Data7_o[9]}] [get_ports {CrossMemory_Data7_o[8]}]      \
[get_ports {CrossMemory_Data7_o[7]}] [get_ports {CrossMemory_Data7_o[6]}]      \
[get_ports {CrossMemory_Data7_o[5]}] [get_ports {CrossMemory_Data7_o[4]}]      \
[get_ports {CrossMemory_Data7_o[3]}] [get_ports {CrossMemory_Data7_o[2]}]      \
[get_ports {CrossMemory_Data7_o[1]}] [get_ports {CrossMemory_Data7_o[0]}]      \
[get_ports {CrossMemory_Data8_o[31]}] [get_ports {CrossMemory_Data8_o[30]}]    \
[get_ports {CrossMemory_Data8_o[29]}] [get_ports {CrossMemory_Data8_o[28]}]    \
[get_ports {CrossMemory_Data8_o[27]}] [get_ports {CrossMemory_Data8_o[26]}]    \
[get_ports {CrossMemory_Data8_o[25]}] [get_ports {CrossMemory_Data8_o[24]}]    \
[get_ports {CrossMemory_Data8_o[23]}] [get_ports {CrossMemory_Data8_o[22]}]    \
[get_ports {CrossMemory_Data8_o[21]}] [get_ports {CrossMemory_Data8_o[20]}]    \
[get_ports {CrossMemory_Data8_o[19]}] [get_ports {CrossMemory_Data8_o[18]}]    \
[get_ports {CrossMemory_Data8_o[17]}] [get_ports {CrossMemory_Data8_o[16]}]    \
[get_ports {CrossMemory_Data8_o[15]}] [get_ports {CrossMemory_Data8_o[14]}]    \
[get_ports {CrossMemory_Data8_o[13]}] [get_ports {CrossMemory_Data8_o[12]}]    \
[get_ports {CrossMemory_Data8_o[11]}] [get_ports {CrossMemory_Data8_o[10]}]    \
[get_ports {CrossMemory_Data8_o[9]}] [get_ports {CrossMemory_Data8_o[8]}]      \
[get_ports {CrossMemory_Data8_o[7]}] [get_ports {CrossMemory_Data8_o[6]}]      \
[get_ports {CrossMemory_Data8_o[5]}] [get_ports {CrossMemory_Data8_o[4]}]      \
[get_ports {CrossMemory_Data8_o[3]}] [get_ports {CrossMemory_Data8_o[2]}]      \
[get_ports {CrossMemory_Data8_o[1]}] [get_ports {CrossMemory_Data8_o[0]}]      \
[get_ports NoC_North_full_o] [get_ports {NoC_North_data_o[38]}] [get_ports     \
{NoC_North_data_o[37]}] [get_ports {NoC_North_data_o[36]}] [get_ports          \
{NoC_North_data_o[35]}] [get_ports {NoC_North_data_o[34]}] [get_ports          \
{NoC_North_data_o[33]}] [get_ports {NoC_North_data_o[32]}] [get_ports          \
{NoC_North_data_o[31]}] [get_ports {NoC_North_data_o[30]}] [get_ports          \
{NoC_North_data_o[29]}] [get_ports {NoC_North_data_o[28]}] [get_ports          \
{NoC_North_data_o[27]}] [get_ports {NoC_North_data_o[26]}] [get_ports          \
{NoC_North_data_o[25]}] [get_ports {NoC_North_data_o[24]}] [get_ports          \
{NoC_North_data_o[23]}] [get_ports {NoC_North_data_o[22]}] [get_ports          \
{NoC_North_data_o[21]}] [get_ports {NoC_North_data_o[20]}] [get_ports          \
{NoC_North_data_o[19]}] [get_ports {NoC_North_data_o[18]}] [get_ports          \
{NoC_North_data_o[17]}] [get_ports {NoC_North_data_o[16]}] [get_ports          \
{NoC_North_data_o[15]}] [get_ports {NoC_North_data_o[14]}] [get_ports          \
{NoC_North_data_o[13]}] [get_ports {NoC_North_data_o[12]}] [get_ports          \
{NoC_North_data_o[11]}] [get_ports {NoC_North_data_o[10]}] [get_ports          \
{NoC_North_data_o[9]}] [get_ports {NoC_North_data_o[8]}] [get_ports            \
{NoC_North_data_o[7]}] [get_ports {NoC_North_data_o[6]}] [get_ports            \
{NoC_North_data_o[5]}] [get_ports {NoC_North_data_o[4]}] [get_ports            \
{NoC_North_data_o[3]}] [get_ports {NoC_North_data_o[2]}] [get_ports            \
{NoC_North_data_o[1]}] [get_ports {NoC_North_data_o[0]}] [get_ports            \
NoC_North_wen_n_o] [get_ports NoC_South_full_o] [get_ports                     \
{NoC_South_data_o[38]}] [get_ports {NoC_South_data_o[37]}] [get_ports          \
{NoC_South_data_o[36]}] [get_ports {NoC_South_data_o[35]}] [get_ports          \
{NoC_South_data_o[34]}] [get_ports {NoC_South_data_o[33]}] [get_ports          \
{NoC_South_data_o[32]}] [get_ports {NoC_South_data_o[31]}] [get_ports          \
{NoC_South_data_o[30]}] [get_ports {NoC_South_data_o[29]}] [get_ports          \
{NoC_South_data_o[28]}] [get_ports {NoC_South_data_o[27]}] [get_ports          \
{NoC_South_data_o[26]}] [get_ports {NoC_South_data_o[25]}] [get_ports          \
{NoC_South_data_o[24]}] [get_ports {NoC_South_data_o[23]}] [get_ports          \
{NoC_South_data_o[22]}] [get_ports {NoC_South_data_o[21]}] [get_ports          \
{NoC_South_data_o[20]}] [get_ports {NoC_South_data_o[19]}] [get_ports          \
{NoC_South_data_o[18]}] [get_ports {NoC_South_data_o[17]}] [get_ports          \
{NoC_South_data_o[16]}] [get_ports {NoC_South_data_o[15]}] [get_ports          \
{NoC_South_data_o[14]}] [get_ports {NoC_South_data_o[13]}] [get_ports          \
{NoC_South_data_o[12]}] [get_ports {NoC_South_data_o[11]}] [get_ports          \
{NoC_South_data_o[10]}] [get_ports {NoC_South_data_o[9]}] [get_ports           \
{NoC_South_data_o[8]}] [get_ports {NoC_South_data_o[7]}] [get_ports            \
{NoC_South_data_o[6]}] [get_ports {NoC_South_data_o[5]}] [get_ports            \
{NoC_South_data_o[4]}] [get_ports {NoC_South_data_o[3]}] [get_ports            \
{NoC_South_data_o[2]}] [get_ports {NoC_South_data_o[1]}] [get_ports            \
{NoC_South_data_o[0]}] [get_ports NoC_South_wen_n_o] [get_ports                \
NoC_East_full_o] [get_ports {NoC_East_data_o[38]}] [get_ports                  \
{NoC_East_data_o[37]}] [get_ports {NoC_East_data_o[36]}] [get_ports            \
{NoC_East_data_o[35]}] [get_ports {NoC_East_data_o[34]}] [get_ports            \
{NoC_East_data_o[33]}] [get_ports {NoC_East_data_o[32]}] [get_ports            \
{NoC_East_data_o[31]}] [get_ports {NoC_East_data_o[30]}] [get_ports            \
{NoC_East_data_o[29]}] [get_ports {NoC_East_data_o[28]}] [get_ports            \
{NoC_East_data_o[27]}] [get_ports {NoC_East_data_o[26]}] [get_ports            \
{NoC_East_data_o[25]}] [get_ports {NoC_East_data_o[24]}] [get_ports            \
{NoC_East_data_o[23]}] [get_ports {NoC_East_data_o[22]}] [get_ports            \
{NoC_East_data_o[21]}] [get_ports {NoC_East_data_o[20]}] [get_ports            \
{NoC_East_data_o[19]}] [get_ports {NoC_East_data_o[18]}] [get_ports            \
{NoC_East_data_o[17]}] [get_ports {NoC_East_data_o[16]}] [get_ports            \
{NoC_East_data_o[15]}] [get_ports {NoC_East_data_o[14]}] [get_ports            \
{NoC_East_data_o[13]}] [get_ports {NoC_East_data_o[12]}] [get_ports            \
{NoC_East_data_o[11]}] [get_ports {NoC_East_data_o[10]}] [get_ports            \
{NoC_East_data_o[9]}] [get_ports {NoC_East_data_o[8]}] [get_ports              \
{NoC_East_data_o[7]}] [get_ports {NoC_East_data_o[6]}] [get_ports              \
{NoC_East_data_o[5]}] [get_ports {NoC_East_data_o[4]}] [get_ports              \
{NoC_East_data_o[3]}] [get_ports {NoC_East_data_o[2]}] [get_ports              \
{NoC_East_data_o[1]}] [get_ports {NoC_East_data_o[0]}] [get_ports              \
NoC_East_wen_n_o] [get_ports NoC_West_full_o] [get_ports                       \
{NoC_West_data_o[38]}] [get_ports {NoC_West_data_o[37]}] [get_ports            \
{NoC_West_data_o[36]}] [get_ports {NoC_West_data_o[35]}] [get_ports            \
{NoC_West_data_o[34]}] [get_ports {NoC_West_data_o[33]}] [get_ports            \
{NoC_West_data_o[32]}] [get_ports {NoC_West_data_o[31]}] [get_ports            \
{NoC_West_data_o[30]}] [get_ports {NoC_West_data_o[29]}] [get_ports            \
{NoC_West_data_o[28]}] [get_ports {NoC_West_data_o[27]}] [get_ports            \
{NoC_West_data_o[26]}] [get_ports {NoC_West_data_o[25]}] [get_ports            \
{NoC_West_data_o[24]}] [get_ports {NoC_West_data_o[23]}] [get_ports            \
{NoC_West_data_o[22]}] [get_ports {NoC_West_data_o[21]}] [get_ports            \
{NoC_West_data_o[20]}] [get_ports {NoC_West_data_o[19]}] [get_ports            \
{NoC_West_data_o[18]}] [get_ports {NoC_West_data_o[17]}] [get_ports            \
{NoC_West_data_o[16]}] [get_ports {NoC_West_data_o[15]}] [get_ports            \
{NoC_West_data_o[14]}] [get_ports {NoC_West_data_o[13]}] [get_ports            \
{NoC_West_data_o[12]}] [get_ports {NoC_West_data_o[11]}] [get_ports            \
{NoC_West_data_o[10]}] [get_ports {NoC_West_data_o[9]}] [get_ports             \
{NoC_West_data_o[8]}] [get_ports {NoC_West_data_o[7]}] [get_ports              \
{NoC_West_data_o[6]}] [get_ports {NoC_West_data_o[5]}] [get_ports              \
{NoC_West_data_o[4]}] [get_ports {NoC_West_data_o[3]}] [get_ports              \
{NoC_West_data_o[2]}] [get_ports {NoC_West_data_o[1]}] [get_ports              \
{NoC_West_data_o[0]}] [get_ports NoC_West_wen_n_o] [get_ports                  \
PCore_push_full_bak_o] [get_ports PCore_push_af_bak_o] [get_ports              \
PCore_push_empty_bak_o] [get_ports {PCore_pop_data_bak_o[31]}] [get_ports      \
{PCore_pop_data_bak_o[30]}] [get_ports {PCore_pop_data_bak_o[29]}] [get_ports  \
{PCore_pop_data_bak_o[28]}] [get_ports {PCore_pop_data_bak_o[27]}] [get_ports  \
{PCore_pop_data_bak_o[26]}] [get_ports {PCore_pop_data_bak_o[25]}] [get_ports  \
{PCore_pop_data_bak_o[24]}] [get_ports {PCore_pop_data_bak_o[23]}] [get_ports  \
{PCore_pop_data_bak_o[22]}] [get_ports {PCore_pop_data_bak_o[21]}] [get_ports  \
{PCore_pop_data_bak_o[20]}] [get_ports {PCore_pop_data_bak_o[19]}] [get_ports  \
{PCore_pop_data_bak_o[18]}] [get_ports {PCore_pop_data_bak_o[17]}] [get_ports  \
{PCore_pop_data_bak_o[16]}] [get_ports {PCore_pop_data_bak_o[15]}] [get_ports  \
{PCore_pop_data_bak_o[14]}] [get_ports {PCore_pop_data_bak_o[13]}] [get_ports  \
{PCore_pop_data_bak_o[12]}] [get_ports {PCore_pop_data_bak_o[11]}] [get_ports  \
{PCore_pop_data_bak_o[10]}] [get_ports {PCore_pop_data_bak_o[9]}] [get_ports   \
{PCore_pop_data_bak_o[8]}] [get_ports {PCore_pop_data_bak_o[7]}] [get_ports    \
{PCore_pop_data_bak_o[6]}] [get_ports {PCore_pop_data_bak_o[5]}] [get_ports    \
{PCore_pop_data_bak_o[4]}] [get_ports {PCore_pop_data_bak_o[3]}] [get_ports    \
{PCore_pop_data_bak_o[2]}] [get_ports {PCore_pop_data_bak_o[1]}] [get_ports    \
{PCore_pop_data_bak_o[0]}] [get_ports PCore_pop_full_o] [get_ports             \
PCore_pop_empty_o] [get_ports PCore_pop_ae_o] [get_ports                       \
{Test_PCore0_IW_Addr_o[10]}] [get_ports {Test_PCore0_IW_Addr_o[9]}] [get_ports \
{Test_PCore0_IW_Addr_o[8]}] [get_ports {Test_PCore0_IW_Addr_o[7]}] [get_ports  \
{Test_PCore0_IW_Addr_o[6]}] [get_ports {Test_PCore0_IW_Addr_o[5]}] [get_ports  \
{Test_PCore0_IW_Addr_o[4]}] [get_ports {Test_PCore0_IW_Addr_o[3]}] [get_ports  \
{Test_PCore0_IW_Addr_o[2]}] [get_ports {Test_PCore0_IW_Addr_o[1]}] [get_ports  \
{Test_PCore0_IW_Addr_o[0]}] [get_ports {Test_PCore0_inMCU_state_o[5]}]         \
[get_ports {Test_PCore0_inMCU_state_o[4]}] [get_ports                          \
{Test_PCore0_inMCU_state_o[3]}] [get_ports {Test_PCore0_inMCU_state_o[2]}]     \
[get_ports {Test_PCore0_inMCU_state_o[1]}] [get_ports                          \
{Test_PCore0_inMCU_state_o[0]}] [get_ports {Test_PCore0_outMCU_state_o[1]}]    \
[get_ports {Test_PCore0_outMCU_state_o[0]}] [get_ports Test_PCore0_Busy_o]     \
[get_ports Test_PCore0_Sclfinish_o] [get_ports Test_PCore0_Data_Valid_o]       \
[get_ports Test_PCore0_Psr4_o] [get_ports Test_PCore0_Psr5_o] [get_ports       \
Test_PCore0_Psr6_o] [get_ports Test_PCore0_Psr7_o] [get_ports                  \
Test_PCore0_Psr8_o] [get_ports {Test_PCore1_IW_Addr_o[9]}] [get_ports          \
{Test_PCore1_IW_Addr_o[8]}] [get_ports {Test_PCore1_IW_Addr_o[7]}] [get_ports  \
{Test_PCore1_IW_Addr_o[6]}] [get_ports {Test_PCore1_IW_Addr_o[5]}] [get_ports  \
{Test_PCore1_IW_Addr_o[4]}] [get_ports {Test_PCore1_IW_Addr_o[3]}] [get_ports  \
{Test_PCore1_IW_Addr_o[2]}] [get_ports {Test_PCore1_IW_Addr_o[1]}] [get_ports  \
{Test_PCore1_IW_Addr_o[0]}] [get_ports {Test_PCore1_inMCU_state_o[4]}]         \
[get_ports {Test_PCore1_inMCU_state_o[3]}] [get_ports                          \
{Test_PCore1_inMCU_state_o[2]}] [get_ports {Test_PCore1_inMCU_state_o[1]}]     \
[get_ports {Test_PCore1_inMCU_state_o[0]}] [get_ports                          \
{Test_PCore1_outMCU_state_o[1]}] [get_ports {Test_PCore1_outMCU_state_o[0]}]   \
[get_ports Test_PCore1_Busy_o] [get_ports Test_PCore1_Sclfinish_o] [get_ports  \
Test_PCore1_Data_Valid_o] [get_ports Test_PCore1_Psr4_o] [get_ports            \
Test_PCore1_Psr5_o] [get_ports Test_PCore1_Psr6_o] [get_ports                  \
Test_PCore1_Psr7_o] [get_ports Test_PCore1_Psr8_o] [get_ports                  \
{Test_PCore2_IW_Addr_o[10]}] [get_ports {Test_PCore2_IW_Addr_o[9]}] [get_ports \
{Test_PCore2_IW_Addr_o[8]}] [get_ports {Test_PCore2_IW_Addr_o[7]}] [get_ports  \
{Test_PCore2_IW_Addr_o[6]}] [get_ports {Test_PCore2_IW_Addr_o[5]}] [get_ports  \
{Test_PCore2_IW_Addr_o[4]}] [get_ports {Test_PCore2_IW_Addr_o[3]}] [get_ports  \
{Test_PCore2_IW_Addr_o[2]}] [get_ports {Test_PCore2_IW_Addr_o[1]}] [get_ports  \
{Test_PCore2_IW_Addr_o[0]}] [get_ports {Test_PCore2_inMCU_state_o[5]}]         \
[get_ports {Test_PCore2_inMCU_state_o[4]}] [get_ports                          \
{Test_PCore2_inMCU_state_o[3]}] [get_ports {Test_PCore2_inMCU_state_o[2]}]     \
[get_ports {Test_PCore2_inMCU_state_o[1]}] [get_ports                          \
{Test_PCore2_inMCU_state_o[0]}] [get_ports {Test_PCore2_outMCU_state_o[1]}]    \
[get_ports {Test_PCore2_outMCU_state_o[0]}] [get_ports Test_PCore2_Busy_o]     \
[get_ports Test_PCore2_Sclfinish_o] [get_ports Test_PCore2_Data_Valid_o]       \
[get_ports Test_PCore2_Psr4_o] [get_ports Test_PCore2_Psr5_o] [get_ports       \
Test_PCore2_Psr6_o] [get_ports Test_PCore2_Psr7_o] [get_ports                  \
Test_PCore2_Psr8_o] [get_ports {Test_PCore3_IW_Addr_o[10]}] [get_ports         \
{Test_PCore3_IW_Addr_o[9]}] [get_ports {Test_PCore3_IW_Addr_o[8]}] [get_ports  \
{Test_PCore3_IW_Addr_o[7]}] [get_ports {Test_PCore3_IW_Addr_o[6]}] [get_ports  \
{Test_PCore3_IW_Addr_o[5]}] [get_ports {Test_PCore3_IW_Addr_o[4]}] [get_ports  \
{Test_PCore3_IW_Addr_o[3]}] [get_ports {Test_PCore3_IW_Addr_o[2]}] [get_ports  \
{Test_PCore3_IW_Addr_o[1]}] [get_ports {Test_PCore3_IW_Addr_o[0]}] [get_ports  \
{Test_PCore3_inMCU_state_o[5]}] [get_ports {Test_PCore3_inMCU_state_o[4]}]     \
[get_ports {Test_PCore3_inMCU_state_o[3]}] [get_ports                          \
{Test_PCore3_inMCU_state_o[2]}] [get_ports {Test_PCore3_inMCU_state_o[1]}]     \
[get_ports {Test_PCore3_inMCU_state_o[0]}] [get_ports                          \
{Test_PCore3_outMCU_state_o[1]}] [get_ports {Test_PCore3_outMCU_state_o[0]}]   \
[get_ports Test_PCore3_Busy_o] [get_ports Test_PCore3_Sclfinish_o] [get_ports  \
Test_PCore3_Data_Valid_o] [get_ports Test_PCore3_Psr4_o] [get_ports            \
Test_PCore3_Psr5_o] [get_ports Test_PCore3_Psr6_o] [get_ports                  \
Test_PCore3_Psr7_o] [get_ports Test_PCore3_Psr8_o] [get_ports                  \
{Test_CCi_IW_Addr_o[9]}] [get_ports {Test_CCi_IW_Addr_o[8]}] [get_ports        \
{Test_CCi_IW_Addr_o[7]}] [get_ports {Test_CCi_IW_Addr_o[6]}] [get_ports        \
{Test_CCi_IW_Addr_o[5]}] [get_ports {Test_CCi_IW_Addr_o[4]}] [get_ports        \
{Test_CCi_IW_Addr_o[3]}] [get_ports {Test_CCi_IW_Addr_o[2]}] [get_ports        \
{Test_CCi_IW_Addr_o[1]}] [get_ports {Test_CCi_IW_Addr_o[0]}] [get_ports        \
{Test_CCi_DMA_state_o[4]}] [get_ports {Test_CCi_DMA_state_o[3]}] [get_ports    \
{Test_CCi_DMA_state_o[2]}] [get_ports {Test_CCi_DMA_state_o[1]}] [get_ports    \
{Test_CCi_DMA_state_o[0]}] [get_ports {Test_CCo_IW_Addr_o[9]}] [get_ports      \
{Test_CCo_IW_Addr_o[8]}] [get_ports {Test_CCo_IW_Addr_o[7]}] [get_ports        \
{Test_CCo_IW_Addr_o[6]}] [get_ports {Test_CCo_IW_Addr_o[5]}] [get_ports        \
{Test_CCo_IW_Addr_o[4]}] [get_ports {Test_CCo_IW_Addr_o[3]}] [get_ports        \
{Test_CCo_IW_Addr_o[2]}] [get_ports {Test_CCo_IW_Addr_o[1]}] [get_ports        \
{Test_CCo_IW_Addr_o[0]}] [get_ports {Test_CCo_DMA_state_o[2]}] [get_ports      \
{Test_CCo_DMA_state_o[1]}] [get_ports {Test_CCo_DMA_state_o[0]}] [get_ports    \
PCore0_infifo_push_full] [get_ports PCore0_infifo_pop_empty] [get_ports        \
PCore0_outfifo_push_full] [get_ports PCore0_outfifo_pop_empty] [get_ports      \
PCore1_infifo_push_full] [get_ports PCore1_infifo_pop_empty] [get_ports        \
PCore1_outfifo_push_full] [get_ports PCore1_outfifo_pop_empty] [get_ports      \
PCore2_infifo_push_full] [get_ports PCore2_infifo_pop_empty] [get_ports        \
PCore2_outfifo_push_full] [get_ports PCore2_outfifo_pop_empty] [get_ports      \
PCore3_infifo_push_full] [get_ports PCore3_infifo_pop_empty] [get_ports        \
PCore3_outfifo_push_full] [get_ports PCore3_outfifo_pop_empty]]
set_false_path   -from [get_ports clk]
set_false_path   -from [get_ports RESET]
set_false_path   -from [get_pins Reset_Unit_map/RESET_PCore0]
set_false_path   -from [get_pins Reset_Unit_map/RESET_PCore1]
set_false_path   -from [get_pins Reset_Unit_map/RESET_PCore2]
set_false_path   -from [get_pins Reset_Unit_map/RESET_PCore3]
set_false_path   -from [get_pins Reset_Unit_map/RESET_CrossMemory]
set_false_path   -from [get_pins Reset_Unit_map/RESET_DMA]
set_false_path   -from [get_pins Reset_Unit_map/RESET_NoC]
set_false_path   -from [get_clocks clk]  -to [get_clocks NoC_East_clk]
set_false_path   -from [get_clocks NoC_East_clk]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_clocks NoC_North_clk]
set_false_path   -from [get_clocks NoC_North_clk]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_clocks NoC_West_clk]
set_false_path   -from [get_clocks NoC_West_clk]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_clocks NoC_South_clk]
set_false_path   -from [get_clocks NoC_South_clk]  -to [get_clocks clk]
set_false_path   -from [get_pins Clock_Manager_map/clkout_NoC]  -to [get_clocks NoC_East_clk]
set_false_path   -from [get_clocks NoC_East_clk]  -to [get_pins Clock_Manager_map/clkout_NoC]
set_false_path   -from [get_pins Clock_Manager_map/clkout_NoC]  -to [get_clocks NoC_North_clk]
set_false_path   -from [get_clocks NoC_North_clk]  -to [get_pins Clock_Manager_map/clkout_NoC]
set_false_path   -from [get_pins Clock_Manager_map/clkout_NoC]  -to [get_clocks NoC_South_clk]
set_false_path   -from [get_clocks NoC_South_clk]  -to [get_pins Clock_Manager_map/clkout_NoC]
set_false_path   -from [get_pins Clock_Manager_map/clkout_NoC]  -to [get_clocks NoC_West_clk]
set_false_path   -from [get_clocks NoC_West_clk]  -to [get_pins Clock_Manager_map/clkout_NoC]
set_false_path   -from [get_clocks clk]  -to [get_clocks PCore_push_clk_bak_i]
set_false_path   -from [get_clocks PCore_push_clk_bak_i]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_clocks clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore0]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore0]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore1]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore1]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore2]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore2]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore3]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore3]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_KeyPool_G1]
set_false_path   -from [get_pins Clock_Manager_map/clkout_KeyPool_G1]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_KeyPool_G2]
set_false_path   -from [get_pins Clock_Manager_map/clkout_KeyPool_G2]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_KeyPool_G3]
set_false_path   -from [get_pins Clock_Manager_map/clkout_KeyPool_G3]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_KeyPool_G4]
set_false_path   -from [get_pins Clock_Manager_map/clkout_KeyPool_G4]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_NoC]
set_false_path   -from [get_pins Clock_Manager_map/clkout_NoC]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_EccMatrix]
set_false_path   -from [get_pins Clock_Manager_map/clkout_EccMatrix]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_clocks clk_PCore0_inFIFO]
set_false_path   -from [get_clocks clk_PCore0_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_clocks clk_PCore1_inFIFO]
set_false_path   -from [get_clocks clk_PCore1_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_clocks clk_PCore2_inFIFO]
set_false_path   -from [get_clocks clk_PCore2_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_clocks clk_PCore3_inFIFO]
set_false_path   -from [get_clocks clk_PCore3_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore0_inFIFO]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_pins Backup_Unit_map/clk_PCore0_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore1_inFIFO]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_pins Backup_Unit_map/clk_PCore1_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore2_inFIFO]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_pins Backup_Unit_map/clk_PCore2_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore3_inFIFO]  -to [get_clocks clk]
set_false_path   -from [get_clocks clk]  -to [get_pins Backup_Unit_map/clk_PCore3_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore0_inFIFO]  -to [get_pins Clock_Manager_map/clkout_PCore0]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore0]  -to [get_pins Backup_Unit_map/clk_PCore0_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore1_inFIFO]  -to [get_pins Clock_Manager_map/clkout_PCore1]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore1]  -to [get_pins Backup_Unit_map/clk_PCore1_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore2_inFIFO]  -to [get_pins Clock_Manager_map/clkout_PCore2]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore2]  -to [get_pins Backup_Unit_map/clk_PCore2_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore3_inFIFO]  -to [get_pins Clock_Manager_map/clkout_PCore3]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore3]  -to [get_pins Backup_Unit_map/clk_PCore3_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore0_inFIFO]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore0_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore1_inFIFO]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore1_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore2_inFIFO]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore2_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore3_inFIFO]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore3_inFIFO]
set_false_path   -from [get_clocks clk]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_clocks clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore0]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore0]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore1]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore1]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore2]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore2]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_PCore3]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore3]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CoutFIFO_clk]  -to [get_pins Clock_Manager_map/clkout_NoC]
set_false_path   -from [get_pins Clock_Manager_map/clkout_NoC]  -to [get_clocks CoutFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore0_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore0_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore1_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore1_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore2_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore2_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_clocks CinFIFO_clk]  -to [get_pins Backup_Unit_map/clk_PCore3_inFIFO]
set_false_path   -from [get_pins Backup_Unit_map/clk_PCore3_inFIFO]  -to [get_clocks CinFIFO_clk]
set_false_path   -from [get_pins Clock_Manager_map/clkout_PCore1]  -to [get_pins Clock_Manager_map/clkout_EccMatrix]
set_false_path   -from [get_pins Clock_Manager_map/clkout_EccMatrix]  -to [get_pins Clock_Manager_map/clkout_PCore1]
set_input_delay -clock NoC_North_clk  0.8  [get_ports NoC_North_wen_n_i]
set_input_delay -clock NoC_South_clk  0.8  [get_ports NoC_South_wen_n_i]
set_input_delay -clock NoC_East_clk  0.8  [get_ports NoC_East_wen_n_i]
set_input_delay -clock NoC_West_clk  0.8  [get_ports NoC_West_wen_n_i]
