module top;
 bit value;int observed;
 covergroup cg;
  option.per_instance=1;
  cp:coverpoint value {option.at_least=2;bins z={0};bins o={1};}
 endgroup
 cg c;
 initial begin
  c=new();value=0;c.sample();
  #2;c.sample();if(c.get_inst_coverage()!=50.0)$fatal(1,"second hit");
  observed=9;value=1;
  #1;c.sample();observed=7;
  #2;if(c.get_inst_coverage()!=50.0)$fatal(1,"rollback leaked hits");c.sample();
  if(c.get_inst_coverage()!=100.0)$fatal(1,"committed bins");
  $display("TRACE rollback %0d",observed);$finish;
 end
endmodule
