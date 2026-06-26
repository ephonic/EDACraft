`timescale 1ns / 1ps
module FullSystem_wrapper#(
    parameter BP_NUM = 'd256,
    parameter Sel_Width = 'd8,
    parameter Instruction_Width = 'd96,
    parameter Addr_Width = 'd7
) 
(
    input pad_sys_clk,
    input pad_sys_rst,
    input [Instruction_Width-1:0] pad_MOSI,
    input [Sel_Width-1:0] pad_CS,  
    input [Sel_Width-1:0] pad_CS_2,
    input pad_flag,          
    input [Addr_Width-1:0] pad_pc,
    output pad_MISO_rData      
    );
    wire sys_clk, sys_clk_pll;
    wire sys_rst;
    wire [Instruction_Width-1:0] MOSI;
    wire [Sel_Width-1:0] CS;
    wire [Sel_Width-1:0] CS_2;
    wire flag;         
    wire [Addr_Width-1:0] pc;  
    wire MISO_rData; 
    
    PLLTS28HPMFRAC  PLLTS28HPMFRAC_inst (
    .FREF(sys_clk),
    .REFDIV(6'd8),
    .FBDIV(12'd100),
    .FRAC(24'd0),
    .POSTDIV1(3'd1),
    .POSTDIV2(3'd1),
    .PD(1'b0),
    .DACPD(1'b0),
    .DSMPD(1'b0),
    .FOUTPOSTDIVPD(1'b0),
    .FOUT4PHASEPD(1'b0),
    .FOUTVCOPD(1'b0),
    .BYPASS(1'b1),
    .FOUTVCO(),
    .FOUTPOSTDIV(),
    .FOUT1PH0(sys_clk_pll),
    .FOUT1PH90(),
    .FOUT1PH180(),
    .FOUT1PH270(),
    .FOUT2(),
    .FOUT3(),
    .FOUT4(),
    .LOCK(),
    .CLKSSCG()
  );

    FullSystem uFullSystem(.sys_clk(sys_clk_pll),.sys_rst(sys_rst),.MOSI(MOSI),.MISO_rData(MISO_rData),.CS(CS),.CS_2(CS_2),.flag(flag),.pc(pc));
    
PRUW12DGZ_V_G u_pad_clk     (.REN(1'b1),.C(sys_clk),.I(1'b0),.OEN(1'b1),.PAD(pad_sys_clk));
PRUW12DGZ_V_G u_pad_rst     (.REN(1'b1),.C(sys_rst),.I(1'b0),.OEN(1'b1),.PAD(pad_sys_rst));
PRUW12DGZ_V_G u_pad_MOSI_0  (.REN(1'b1),.C(MOSI[0]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[0]));
PRUW12DGZ_V_G u_pad_MOSI_1	(.REN(1'b1),.C(MOSI[1]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[1]));
PRUW12DGZ_V_G u_pad_MOSI_2	(.REN(1'b1),.C(MOSI[2]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[2]));
PRUW12DGZ_V_G u_pad_MOSI_3	(.REN(1'b1),.C(MOSI[3]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[3]));
PRUW12DGZ_V_G u_pad_MOSI_4	(.REN(1'b1),.C(MOSI[4]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[4]));
PRUW12DGZ_V_G u_pad_MOSI_5	(.REN(1'b1),.C(MOSI[5]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[5]));
PRUW12DGZ_V_G u_pad_MOSI_6	(.REN(1'b1),.C(MOSI[6]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[6]));
PRUW12DGZ_V_G u_pad_MOSI_7	(.REN(1'b1),.C(MOSI[7]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[7]));
PRUW12DGZ_V_G u_pad_MOSI_8	(.REN(1'b1),.C(MOSI[8]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[8]));
PRUW12DGZ_V_G u_pad_MOSI_9	(.REN(1'b1),.C(MOSI[9]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[9]));
PRUW12DGZ_V_G u_pad_MOSI_10	(.REN(1'b1),.C(MOSI[10]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[10]));
PRUW12DGZ_V_G u_pad_MOSI_11	(.REN(1'b1),.C(MOSI[11]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[11]));
PRUW12DGZ_V_G u_pad_MOSI_12	(.REN(1'b1),.C(MOSI[12]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[12]));
PRUW12DGZ_V_G u_pad_MOSI_13	(.REN(1'b1),.C(MOSI[13]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[13]));
PRUW12DGZ_V_G u_pad_MOSI_14	(.REN(1'b1),.C(MOSI[14]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[14]));
PRUW12DGZ_V_G u_pad_MOSI_15	(.REN(1'b1),.C(MOSI[15]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[15]));
PRUW12DGZ_V_G u_pad_MOSI_16	(.REN(1'b1),.C(MOSI[16]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[16]));
PRUW12DGZ_V_G u_pad_MOSI_17	(.REN(1'b1),.C(MOSI[17]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[17]));
PRUW12DGZ_V_G u_pad_MOSI_18	(.REN(1'b1),.C(MOSI[18]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[18]));
PRUW12DGZ_V_G u_pad_MOSI_19	(.REN(1'b1),.C(MOSI[19]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[19]));
PRUW12DGZ_V_G u_pad_MOSI_20	(.REN(1'b1),.C(MOSI[20]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[20]));
PRUW12DGZ_V_G u_pad_MOSI_21	(.REN(1'b1),.C(MOSI[21]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[21]));
PRUW12DGZ_V_G u_pad_MOSI_22	(.REN(1'b1),.C(MOSI[22]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[22]));
PRUW12DGZ_V_G u_pad_MOSI_23	(.REN(1'b1),.C(MOSI[23]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[23]));
PRUW12DGZ_V_G u_pad_MOSI_24	(.REN(1'b1),.C(MOSI[24]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[24]));
PRUW12DGZ_V_G u_pad_MOSI_25	(.REN(1'b1),.C(MOSI[25]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[25]));
PRUW12DGZ_V_G u_pad_MOSI_26	(.REN(1'b1),.C(MOSI[26]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[26]));
PRUW12DGZ_V_G u_pad_MOSI_27	(.REN(1'b1),.C(MOSI[27]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[27]));
PRUW12DGZ_V_G u_pad_MOSI_28	(.REN(1'b1),.C(MOSI[28]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[28]));
PRUW12DGZ_V_G u_pad_MOSI_29	(.REN(1'b1),.C(MOSI[29]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[29]));
PRUW12DGZ_V_G u_pad_MOSI_30	(.REN(1'b1),.C(MOSI[30]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[30]));
PRUW12DGZ_V_G u_pad_MOSI_31	(.REN(1'b1),.C(MOSI[31]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[31]));
PRUW12DGZ_V_G u_pad_MOSI_32	(.REN(1'b1),.C(MOSI[32]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[32]));
PRUW12DGZ_V_G u_pad_MOSI_33	(.REN(1'b1),.C(MOSI[33]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[33]));
PRUW12DGZ_V_G u_pad_MOSI_34	(.REN(1'b1),.C(MOSI[34]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[34]));
PRUW12DGZ_V_G u_pad_MOSI_35	(.REN(1'b1),.C(MOSI[35]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[35]));
PRUW12DGZ_V_G u_pad_MOSI_36	(.REN(1'b1),.C(MOSI[36]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[36]));
PRUW12DGZ_V_G u_pad_MOSI_37	(.REN(1'b1),.C(MOSI[37]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[37]));
PRUW12DGZ_V_G u_pad_MOSI_38	(.REN(1'b1),.C(MOSI[38]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[38]));
PRUW12DGZ_V_G u_pad_MOSI_39	(.REN(1'b1),.C(MOSI[39]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[39]));
PRUW12DGZ_V_G u_pad_MOSI_40	(.REN(1'b1),.C(MOSI[40]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[40]));
PRUW12DGZ_V_G u_pad_MOSI_41	(.REN(1'b1),.C(MOSI[41]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[41]));
PRUW12DGZ_V_G u_pad_MOSI_42	(.REN(1'b1),.C(MOSI[42]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[42]));
PRUW12DGZ_V_G u_pad_MOSI_43	(.REN(1'b1),.C(MOSI[43]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[43]));
PRUW12DGZ_V_G u_pad_MOSI_44	(.REN(1'b1),.C(MOSI[44]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[44]));
PRUW12DGZ_V_G u_pad_MOSI_45	(.REN(1'b1),.C(MOSI[45]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[45]));
PRUW12DGZ_V_G u_pad_MOSI_46	(.REN(1'b1),.C(MOSI[46]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[46]));
PRUW12DGZ_V_G u_pad_MOSI_47	(.REN(1'b1),.C(MOSI[47]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[47]));
PRUW12DGZ_V_G u_pad_MOSI_48	(.REN(1'b1),.C(MOSI[48]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[48]));
PRUW12DGZ_V_G u_pad_MOSI_49	(.REN(1'b1),.C(MOSI[49]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[49]));
PRUW12DGZ_V_G u_pad_MOSI_50	(.REN(1'b1),.C(MOSI[50]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[50]));
PRUW12DGZ_V_G u_pad_MOSI_51	(.REN(1'b1),.C(MOSI[51]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[51]));
PRUW12DGZ_V_G u_pad_MOSI_52	(.REN(1'b1),.C(MOSI[52]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[52]));
PRUW12DGZ_V_G u_pad_MOSI_53	(.REN(1'b1),.C(MOSI[53]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[53]));
PRUW12DGZ_V_G u_pad_MOSI_54	(.REN(1'b1),.C(MOSI[54]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[54]));
PRUW12DGZ_V_G u_pad_MOSI_55	(.REN(1'b1),.C(MOSI[55]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[55]));
PRUW12DGZ_V_G u_pad_MOSI_56	(.REN(1'b1),.C(MOSI[56]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[56]));
PRUW12DGZ_V_G u_pad_MOSI_57	(.REN(1'b1),.C(MOSI[57]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[57]));
PRUW12DGZ_V_G u_pad_MOSI_58	(.REN(1'b1),.C(MOSI[58]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[58]));
PRUW12DGZ_V_G u_pad_MOSI_59	(.REN(1'b1),.C(MOSI[59]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[59]));
PRUW12DGZ_V_G u_pad_MOSI_60	(.REN(1'b1),.C(MOSI[60]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[60]));
PRUW12DGZ_V_G u_pad_MOSI_61	(.REN(1'b1),.C(MOSI[61]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[61]));
PRUW12DGZ_V_G u_pad_MOSI_62	(.REN(1'b1),.C(MOSI[62]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[62]));
PRUW12DGZ_V_G u_pad_MOSI_63	(.REN(1'b1),.C(MOSI[63]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[63]));
PRUW12DGZ_V_G u_pad_MOSI_64	(.REN(1'b1),.C(MOSI[64]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[64]));
PRUW12DGZ_V_G u_pad_MOSI_65	(.REN(1'b1),.C(MOSI[65]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[65]));
PRUW12DGZ_V_G u_pad_MOSI_66	(.REN(1'b1),.C(MOSI[66]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[66]));
PRUW12DGZ_V_G u_pad_MOSI_67	(.REN(1'b1),.C(MOSI[67]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[67]));
PRUW12DGZ_V_G u_pad_MOSI_68	(.REN(1'b1),.C(MOSI[68]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[68]));
PRUW12DGZ_V_G u_pad_MOSI_69	(.REN(1'b1),.C(MOSI[69]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[69]));
PRUW12DGZ_V_G u_pad_MOSI_70	(.REN(1'b1),.C(MOSI[70]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[70]));
PRUW12DGZ_V_G u_pad_MOSI_71	(.REN(1'b1),.C(MOSI[71]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[71]));
PRUW12DGZ_V_G u_pad_MOSI_72	(.REN(1'b1),.C(MOSI[72]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[72]));
PRUW12DGZ_V_G u_pad_MOSI_73	(.REN(1'b1),.C(MOSI[73]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[73]));
PRUW12DGZ_V_G u_pad_MOSI_74	(.REN(1'b1),.C(MOSI[74]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[74]));
PRUW12DGZ_V_G u_pad_MOSI_75	(.REN(1'b1),.C(MOSI[75]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[75]));
PRUW12DGZ_V_G u_pad_MOSI_76	(.REN(1'b1),.C(MOSI[76]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[76]));
PRUW12DGZ_V_G u_pad_MOSI_77	(.REN(1'b1),.C(MOSI[77]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[77]));
PRUW12DGZ_V_G u_pad_MOSI_78	(.REN(1'b1),.C(MOSI[78]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[78]));
PRUW12DGZ_V_G u_pad_MOSI_79	(.REN(1'b1),.C(MOSI[79]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[79]));
PRUW12DGZ_V_G u_pad_MOSI_80	(.REN(1'b1),.C(MOSI[80]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[80]));
PRUW12DGZ_V_G u_pad_MOSI_81	(.REN(1'b1),.C(MOSI[81]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[81]));
PRUW12DGZ_V_G u_pad_MOSI_82	(.REN(1'b1),.C(MOSI[82]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[82]));
PRUW12DGZ_V_G u_pad_MOSI_83	(.REN(1'b1),.C(MOSI[83]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[83]));
PRUW12DGZ_V_G u_pad_MOSI_84	(.REN(1'b1),.C(MOSI[84]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[84]));
PRUW12DGZ_V_G u_pad_MOSI_85	(.REN(1'b1),.C(MOSI[85]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[85]));
PRUW12DGZ_V_G u_pad_MOSI_86	(.REN(1'b1),.C(MOSI[86]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[86]));
PRUW12DGZ_V_G u_pad_MOSI_87	(.REN(1'b1),.C(MOSI[87]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[87]));
PRUW12DGZ_V_G u_pad_MOSI_88	(.REN(1'b1),.C(MOSI[88]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[88]));
PRUW12DGZ_V_G u_pad_MOSI_89	(.REN(1'b1),.C(MOSI[89]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[89]));
PRUW12DGZ_V_G u_pad_MOSI_90	(.REN(1'b1),.C(MOSI[90]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[90]));
PRUW12DGZ_V_G u_pad_MOSI_91	(.REN(1'b1),.C(MOSI[91]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[91]));
PRUW12DGZ_V_G u_pad_MOSI_92	(.REN(1'b1),.C(MOSI[92]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[92]));
PRUW12DGZ_V_G u_pad_MOSI_93	(.REN(1'b1),.C(MOSI[93]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[93]));
PRUW12DGZ_V_G u_pad_MOSI_94	(.REN(1'b1),.C(MOSI[94]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[94]));
PRUW12DGZ_V_G u_pad_MOSI_95	(.REN(1'b1),.C(MOSI[95]),.I(1'b0),.OEN(1'b1),.PAD(pad_MOSI[95]));
PRUW12DGZ_V_G u_pad_CS_0	(.REN(1'b1),.C(CS[0]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[0]));
PRUW12DGZ_V_G u_pad_CS_1	(.REN(1'b1),.C(CS[1]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[1]));
PRUW12DGZ_V_G u_pad_CS_2	(.REN(1'b1),.C(CS[2]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[2]));
PRUW12DGZ_V_G u_pad_CS_3	(.REN(1'b1),.C(CS[3]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[3]));
PRUW12DGZ_V_G u_pad_CS_4	(.REN(1'b1),.C(CS[4]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[4]));
PRUW12DGZ_V_G u_pad_CS_5	(.REN(1'b1),.C(CS[5]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[5]));
PRUW12DGZ_V_G u_pad_CS_6	(.REN(1'b1),.C(CS[6]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[6]));
PRUW12DGZ_V_G u_pad_CS_7	(.REN(1'b1),.C(CS[7]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS[7]));
PRUW12DGZ_V_G u_pad_CS_2_0	(.REN(1'b1),.C(CS_2[0]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[0]));
PRUW12DGZ_V_G u_pad_CS_2_1	(.REN(1'b1),.C(CS_2[1]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[1]));
PRUW12DGZ_V_G u_pad_CS_2_2	(.REN(1'b1),.C(CS_2[2]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[2]));
PRUW12DGZ_V_G u_pad_CS_2_3	(.REN(1'b1),.C(CS_2[3]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[3]));
PRUW12DGZ_V_G u_pad_CS_2_4	(.REN(1'b1),.C(CS_2[4]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[4]));
PRUW12DGZ_V_G u_pad_CS_2_5	(.REN(1'b1),.C(CS_2[5]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[5]));
PRUW12DGZ_V_G u_pad_CS_2_6	(.REN(1'b1),.C(CS_2[6]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[6]));
PRUW12DGZ_V_G u_pad_CS_2_7	(.REN(1'b1),.C(CS_2[7]),.I(1'b0),.OEN(1'b1),.PAD(pad_CS_2[7]));
PRUW12DGZ_V_G u_pad_flag	(.REN(1'b1),.C(flag),.I(1'b0),.OEN(1'b1),.PAD(pad_flag));
PRUW12DGZ_V_G u_pad_pc_0	(.REN(1'b1),.C(pc[0]),.I(1'b0),.OEN(1'b1),.PAD(pad_pc[0]));
PRUW12DGZ_V_G u_pad_pc_1	(.REN(1'b1),.C(pc[1]),.I(1'b0),.OEN(1'b1),.PAD(pad_pc[1]));
PRUW12DGZ_V_G u_pad_pc_2	(.REN(1'b1),.C(pc[2]),.I(1'b0),.OEN(1'b1),.PAD(pad_pc[2]));
PRUW12DGZ_V_G u_pad_pc_3	(.REN(1'b1),.C(pc[3]),.I(1'b0),.OEN(1'b1),.PAD(pad_pc[3]));
PRUW12DGZ_V_G u_pad_pc_4	(.REN(1'b1),.C(pc[4]),.I(1'b0),.OEN(1'b1),.PAD(pad_pc[4]));
PRUW12DGZ_V_G u_pad_pc_5	(.REN(1'b1),.C(pc[5]),.I(1'b0),.OEN(1'b1),.PAD(pad_pc[5]));
PRUW12DGZ_V_G u_pad_pc_6	(.REN(1'b1),.C(pc[6]),.I(1'b0),.OEN(1'b1),.PAD(pad_pc[6]));
PRUW12DGZ_V_G u_pad_MISO	(.REN(1'b0),.C(),.I(MISO_rData),.OEN(1'b0),.PAD(pad_MISO_rData));
endmodule
