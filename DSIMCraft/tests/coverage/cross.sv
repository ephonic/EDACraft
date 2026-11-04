module top;
 bit a,b,enable=1;int observed;
 covergroup cg;
  option.per_instance=1;
  cp_a:coverpoint a{option.weight=0;bins z={0};bins o={1};}
  cp_b:coverpoint b{option.weight=0;bins z={0};bins o={1};}
  pairs:cross cp_a,cp_b iff(enable);
 endgroup
 cg c;
 initial begin
  c=new();a=0;b=0;c.sample();a=1;b=1;c.sample();
  if(c.get_inst_coverage()!=50.0)$fatal(1,"cross half");
  enable=0;a=0;b=1;c.sample();if(c.get_inst_coverage()!=50.0)$fatal(1,"cross iff");
  enable=1;c.sample();if(c.get_inst_coverage()!=75.0)$fatal(1,"cross third");
  a=1;b=0;c.sample();observed=int'(c.get_inst_coverage());
  if(observed!=100)$fatal(1,"cross full");$display("TRACE cross %0d",observed);$finish;
 end
endmodule
