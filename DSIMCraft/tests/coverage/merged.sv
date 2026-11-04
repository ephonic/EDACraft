module top;
 bit [1:0] value;int observed;
 covergroup cg;
  option.per_instance=1;
  type_option.merge_instances=1;
  cp: coverpoint value { bins each[]={0,1,2,3}; }
 endgroup
 cg a,b;
 initial begin
  a=new();b=new();value=0;a.sample();value=1;a.sample();value=2;b.sample();value=3;b.sample();
  if(a.get_inst_coverage()!=50.0||b.get_inst_coverage()!=50.0||a.get_coverage()!=100.0)$fatal(1,"merged bins");
  observed=int'(a.get_coverage());$display("TRACE merged %0d",observed);$finish;
 end
endmodule
