###	Run full DCT/DCG flow
dc_shell -64 -topo -f ../CMD/rundc.tcl | tee -i dc.log ;

###	Run full ICC
icc_shell -64 -f ../CMD/runicc.tcl | tee -i icc.log ;

###	ICC finalopt flow
#icc_shell -64 -f ../CMD/try_finalopt.tcl | tee -i finalopt.log ;

###	PT analysis && ECO flow.
#pt_shell -f ../CMD/runpt.tcl | tee -i pt.log ;

###	PT-DMSA analysis && ECO flow.
#pt_shell -multi_scenario -f ../CMD/runpt_dmsa.tcl | tee -i pt_dmsa.log ;

###	ICC ECO flow.
#icc_shell -64 -f ../CMD/try_eco.tcl | tee -i eco.log ;

###     ICV In-Design DRC Check && AutoFixing
#icc_shell -64 -f ../CMD/try_signoff_drc.tcl | tee -i signoff_drc.log ;

###     ICV In-Design Metal Fill Insertion
#icc_shell -64 -f ../CMD/try_signoff_metal_fill.tcl | tee -i signoff_metal_fill.log ;
