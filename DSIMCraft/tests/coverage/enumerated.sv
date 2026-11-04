module top;
 typedef enum bit[2:0] {RED=1,GREEN=3,BLUE=7} color;
 color value;int observed;
 covergroup cg;
  option.per_instance=1;
  cp:coverpoint value;
 endgroup
 cg c;
 initial begin
  c=new();value=RED;c.sample();value=GREEN;c.sample();
  observed=int'(c.get_inst_coverage());if(observed!=67)$fatal(1,"enum automatic bins");
  value=BLUE;c.sample();if(c.get_inst_coverage()!=100.0)$fatal(1,"enum full");
  $display("TRACE enum bins %0d",observed);$finish;
 end
endmodule
