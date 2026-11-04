module top;
 bit a,b;int observed;
 covergroup cg;
  option.per_instance=1;
  x:coverpoint a{bins z={0};bins o={1};}
  y:coverpoint b{bins z={0};bins o={1};}
  xy:cross x,y;
 endgroup
 cg c,d;
 initial begin
  c=new();d=new();a=0;b=0;c.sample();a=1;c.sample();
  if(c.x.get_inst_coverage()!=100.0||c.y.get_inst_coverage()!=50.0||c.xy.get_inst_coverage()!=50.0)$fatal(1,"point coverage");
  if(d.x.get_inst_coverage()!=0.0||d.x.get_coverage()!=100.0)$fatal(1,"point type coverage");
  observed=int'(c.xy.get_inst_coverage());$display("TRACE point queries %0d",observed);$finish;
 end
endmodule
