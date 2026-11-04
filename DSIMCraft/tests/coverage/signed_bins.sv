module top;
 int value;int observed;
 covergroup cg;
  option.per_instance=1;
  cp:coverpoint value { bins neg={[-3:-1]}; bins pos={[0:3]}; ignore_bins skip={0}; }
 endgroup
 cg c;
 initial begin
  c=new();value=0;c.sample();if(c.get_inst_coverage()!=0.0)$fatal(1,"ignore");
  value=-2;c.sample();if(c.get_inst_coverage()!=50.0)$fatal(1,"signed");
  value=2;c.sample();observed=int'(c.get_inst_coverage());
  if(observed!=100)$fatal(1,"positive");$display("TRACE signed %0d",observed);$finish;
 end
endmodule
