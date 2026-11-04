module top;
 bit clk=0;logic v=0;
 always @(posedge clk)v<=~v;
 covergroup cg @(posedge clk);
  option.per_instance=1;
  cp:coverpoint v{bins zero={0};}
 endgroup
 cg c;
 initial begin
  c=new();#1;clk=1;#1;
  $display("TRACE event nba %0f %0d",c.get_inst_coverage(),v);$finish;
 end
endmodule
