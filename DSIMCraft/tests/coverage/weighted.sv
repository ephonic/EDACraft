module top;
 bit a,b;int observed;
 covergroup cg;
  option.per_instance=1;
  x:coverpoint a {option.weight=1;bins z={0};bins o={1};}
  y:coverpoint b {option.weight=3;bins z={0};bins o={1};}
 endgroup
 cg c;
 initial begin
  c=new();a=0;b=0;c.sample();a=1;c.sample();
  if(c.get_inst_coverage()!=62.5)$fatal(1,"weighted coverage");
  observed=int'(c.get_inst_coverage());$display("TRACE weighted %0d",observed);$finish;
 end
endmodule
