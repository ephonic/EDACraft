create_cell {cornerul cornerur cornerll cornerlr} PCORNER_G
#power and ground i/o/core pad
create_cell {vddcore_left_1   vddcore_left_2} PVDD1DGZ_H_G 
create_cell {vddcore_right_1  vddcore_right_2} PVDD1DGZ_H_G 
create_cell {vddcore_top_1    vddcore_top_2} PVDD1DGZ_V_G
create_cell {vddcore_bottom_1 vddcore_bottom_2} PVDD1DGZ_V_G 

create_cell {vsscore_left_1} PVSS1DGZ_H_G 
create_cell {vsscore_right_1} PVSS1DGZ_H_G 
create_cell {vsscore_top_1} PVSS1DGZ_V_G
create_cell {vsscore_bottom_1} PVSS1DGZ_V_G 

create_cell {vddio_left_1} PVDD2DGZ_H_G 
create_cell {vddio_right_1} PVDD2DGZ_H_G 
create_cell {vddio_top_1} PVDD2DGZ_V_G
create_cell {vddio_bottom_1} PVDD2DGZ_V_G 

create_cell {vssio_left_1}   PVSS2DGZ_H_G 
create_cell {vssio_right_1}   PVSS2DGZ_H_G 
create_cell {vssio_top_1}   PVSS2DGZ_V_G
create_cell {vssio_bottom_1}   PVSS2DGZ_V_G 
# Dummy IO VSS Cells
create_cell {vssio_dummy_left_1 vssio_dummy_left_2} PVSS2DGZ_H_G
create_cell {vssio_dummy_right_1 vssio_dummy_right_2} PVSS2DGZ_H_G
create_cell {vssio_dummy_top_1 vssio_dummy_top_2} PVSS2DGZ_V_G
create_cell {vssio_dummy_bottom_1 vssio_dummy_bottom_2} PVSS2DGZ_V_G
#POC
create_cell {poc_cell} PVDD2POC_H_G

# ====================== ¶¨ÒåËÄ±ßPadÁÐ±í ======================
set left_ios {
    u_pad_MOSI_0
    u_pad_MOSI_1
    u_pad_MOSI_2
    u_pad_MOSI_3
    u_pad_MOSI_4
    u_pad_MOSI_5
    u_pad_MOSI_6
    u_pad_MOSI_7
    u_pad_MOSI_8
    u_pad_MOSI_9
    u_pad_MOSI_10
    u_pad_MOSI_11
    u_pad_MOSI_12
    u_pad_MOSI_13
    u_pad_MOSI_14
    vssio_left_1
    vssio_dummy_left_1
    vddcore_left_1
    vsscore_left_1
    vddcore_left_2
    vssio_dummy_left_2
    vddio_left_1
    u_pad_MOSI_15
    u_pad_MOSI_16
    u_pad_MOSI_17
    u_pad_MOSI_18
    u_pad_MOSI_19
    u_pad_MOSI_20
    u_pad_MOSI_21
    u_pad_MOSI_22
    u_pad_MOSI_23
    u_pad_CS_0
    u_pad_CS_1
    u_pad_CS_2
    u_pad_CS_3
    u_pad_CS_4
    u_pad_CS_5
    u_pad_CS_6
}

set top_ios {
    u_pad_MOSI_24
    u_pad_MOSI_25
    u_pad_MOSI_26
    u_pad_MOSI_27
    u_pad_MOSI_28
    u_pad_MOSI_29
    u_pad_MOSI_30
    u_pad_MOSI_31
    u_pad_MOSI_32
    u_pad_MOSI_33
    u_pad_MOSI_34
    u_pad_MOSI_35
    u_pad_MOSI_36
    u_pad_MOSI_37
    u_pad_MOSI_38
    vssio_top_1
    vssio_dummy_top_1
    vddcore_top_1
    vsscore_top_1
    vddcore_top_2
    vssio_dummy_top_2
    vddio_top_1
    u_pad_MOSI_39
    u_pad_MOSI_40
    u_pad_MOSI_41
    u_pad_MOSI_42
    u_pad_MOSI_43
    u_pad_MOSI_44
    u_pad_MOSI_45
    u_pad_MOSI_46
    u_pad_MOSI_47
    u_pad_CS_2_0
    u_pad_CS_2_1
    u_pad_CS_2_2
    u_pad_CS_2_3
    u_pad_CS_2_4
    u_pad_CS_2_5
    u_pad_CS_2_6
}

set right_ios {
    u_pad_MOSI_48
    u_pad_MOSI_49
    u_pad_MOSI_50
    u_pad_MOSI_51
    u_pad_MOSI_52
    u_pad_MOSI_53
    u_pad_MOSI_54
    u_pad_MOSI_55
    u_pad_MOSI_56
    u_pad_MOSI_57
    u_pad_MOSI_58
    u_pad_MOSI_59
    u_pad_MOSI_60
    u_pad_MOSI_61
    u_pad_MOSI_62
    vssio_right_1
    vssio_dummy_right_1
    vddcore_right_1
    poc_cell
    vsscore_right_1
    u_pad_clk
    vddcore_right_2
    vssio_dummy_right_2
    vddio_right_1
    u_pad_MOSI_63
    u_pad_MOSI_64
    u_pad_MOSI_65
    u_pad_MOSI_66
    u_pad_MOSI_67
    u_pad_MOSI_68
    u_pad_MOSI_69
    u_pad_MOSI_70
    u_pad_MOSI_71
    u_pad_flag
    u_pad_pc_0
    u_pad_pc_1
    u_pad_pc_2
    u_pad_pc_3
}

set bottom_ios {
    u_pad_MOSI_72
    u_pad_MOSI_73
    u_pad_MOSI_74
    u_pad_MOSI_75
    u_pad_MOSI_76
    u_pad_MOSI_77
    u_pad_MOSI_78
    u_pad_MOSI_79
    u_pad_MOSI_80
    u_pad_MOSI_81
    u_pad_MOSI_82
    u_pad_MOSI_83
    u_pad_MOSI_84
    u_pad_MOSI_85
    u_pad_MOSI_86
    vssio_bottom_1
    vssio_dummy_bottom_1
    vddcore_bottom_1
    u_pad_rst
    vsscore_bottom_1
    vddcore_bottom_2
    vssio_dummy_bottom_2
    vddio_bottom_1
    u_pad_MOSI_87
    u_pad_MOSI_88
    u_pad_MOSI_89
    u_pad_MOSI_90
    u_pad_MOSI_91
    u_pad_MOSI_92
    u_pad_MOSI_93
    u_pad_MOSI_94
    u_pad_MOSI_95
    u_pad_pc_4
    u_pad_pc_5
}

# ====================== ´´½¨IO Guide ======================
remove_io_guides -all

# ´´½¨ËÄ±ßIO guide£¨Çë¸ù¾ÝÊµ¼ÊÐ¾Æ¬³ß´çÐÞ¸Ä×ø±ê£©
create_io_guide -name left_guide   -side left   -pad_cells $left_ios   -line {{0 110} 1690} -min_pitch 10
create_io_guide -name top_guide    -side top    -pad_cells $top_ios    -line {{110 1900} 2790} -min_pitch 20
create_io_guide -name right_guide  -side right  -pad_cells $right_ios  -line {{2900 1790} 1790} -min_pitch 10
create_io_guide -name bottom_guide -side bottom -pad_cells $bottom_ios -line {{2900 0} 2790} -min_pitch 20

# ´´½¨½Çµ¥Ôª£¨Çë¸ù¾Ý¹¤ÒÕ¿âÐÞ¸Äcorner cellÃû³Æ£©
create_io_corner_cell -reference_cell PCORNER_G {left_guide top_guide}
create_io_corner_cell -reference_cell PCORNER_G {right_guide top_guide}
create_io_corner_cell -reference_cell PCORNER_G {left_guide bottom_guide}
create_io_corner_cell -reference_cell PCORNER_G {right_guide bottom_guide}

place_io
