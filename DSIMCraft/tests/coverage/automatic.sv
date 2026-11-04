module top;
 bit [2:0] value;int observed;
 covergroup cg;
  option.per_instance=1;
  cp: coverpoint value { option.auto_bin_max=4; }
 endgroup
 cg a,b;
 initial begin
  a=new();b=new();value=0;a.sample();value=2;a.sample();
  if(a.get_inst_coverage()!=50.0||b.get_inst_coverage()!=0.0||b.get_coverage()!=50.0)$fatal(1,"automatic bins");
  value=4;b.sample();value=6;b.sample();
  if(a.get_coverage()!=100.0)$fatal(1,"type coverage");
  observed=int'(a.get_coverage());$display("TRACE automatic %0d",observed);$finish;
 end
endmodule
