module top;
 bit [3:0] value; bit enable=1; int observed;
 covergroup cg;
  option.per_instance=1;
  cp: coverpoint value iff(enable) {
   option.at_least=2;
   bins low={[0:3]}; bins high={[8:11]};
   ignore_bins skip={15}; bins other=default;
  }
 endgroup
 cg c;
 initial begin
  c=new();c.set_inst_name("manual");
  if(c.get_inst_coverage()!=0.0)$fatal(1,"initial coverage");
  value=1;c.sample();if(c.get_inst_coverage()!=0.0)$fatal(1,"threshold");
  c.sample();if(c.get_inst_coverage()!=50.0)$fatal(1,"one bin");
  value=8;enable=0;c.sample();c.sample();enable=1;
  c.stop();c.sample();c.sample();c.start();
  if(c.get_inst_coverage()!=50.0)$fatal(1,"disabled sample");
  value=15;c.sample();value=8;c.sample();c.sample();
  if(c.get_inst_coverage()!=100.0)$fatal(1,"full coverage");
  observed=int'(c.get_coverage());$display("TRACE manual %0d",observed);$finish;
 end
endmodule
