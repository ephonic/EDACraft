`timescale 1ns/1ps
interface counter #(parameter W=7,START=3);
 logic signed[W-1:0] value=START;
 function automatic logic signed[W-1:0] get(input integer delta=START);return value-delta;endfunction
 function integer count();static integer calls=0;calls++;return calls;endfunction
 task automatic update(input integer n);#1;value=n;endtask
 modport use_api(import function logic signed[W-1:0] get(input integer delta=START), function integer count(), task update(input integer n),input value);
endinterface
module consumer #(parameter ID=0)(counter.use_api b);
 integer before_value,after_value,first,second;
 initial begin before_value=b.get();first=b.count();second=b.count();b.update(ID+10);after_value=b.get(20);
  if(before_value!=0||first!=1||second!=2||after_value!=ID-10)$fatal(1,"FAIL clones");
  #(ID);$display("TRACE clones %0d %0d %0d %0d %0d",ID,before_value,after_value,first,second);end
endmodule
module top;
 counter #(7,3) a();counter #(13,5) b();consumer #(1) c(a);consumer #(2) d(b.use_api);
 for(genvar i=0;i<2;i++)begin:g
  counter #(8+i,7+i) local_bus();consumer #(3+i) u(local_bus);
 end
 initial begin #7;$finish;end
endmodule
