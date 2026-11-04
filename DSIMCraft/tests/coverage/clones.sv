module leaf #(parameter int N=1,W=3);
 bit [W-1:0] value;
 covergroup cg;
  option.per_instance=1;
  cp:coverpoint value {bins low={0};bins high={1};}
 endgroup
 cg c;
 initial begin c=new();#1;for(int i=0;i<N;i++)begin value=i;c.sample();end end
endmodule
module top;
 leaf #(2,3) a();leaf #(1,4) b();int observed;
 initial begin
  #2;if(a.c.get_inst_coverage()!=100.0||b.c.get_inst_coverage()!=50.0)$fatal(1,"cloned state");
  observed=int'(b.c.get_inst_coverage());$display("TRACE clones %0d",observed);$finish;
 end
endmodule
