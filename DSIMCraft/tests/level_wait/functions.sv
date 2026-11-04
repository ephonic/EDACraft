`timescale 1ns/1ps
module top;
 logic a=0,b=0;integer explicit_done,hidden_done,wide_done,reg_done,calls;
 logic signed[7:0]negative;logic[129:0]wide_result;
 function automatic logic ready(input logic v);begin calls=calls+1;ready=v;end endfunction
 function automatic logic hidden();hidden=b;endfunction
 function automatic logic unsigned[129:0]wide(input logic v);
   wide=v?130'h200000000000000000000000000000000:130'd0;
 endfunction
 function reg signed[7:0]neg(input logic v);neg=v?8'h80:8'h00;endfunction
 function reg unsigned flag(input logic v);flag=v;endfunction
 initial begin explicit_done=0;calls=0;wait(ready(a));explicit_done=1;end
 initial begin hidden_done=0;wait(hidden());hidden_done=1;end
 initial begin wide_done=0;wait(wide(a));wide_result=wide(a);wide_done=1;end
 initial begin reg_done=0;wait(neg(a)<0);negative=neg(a);wait(flag(a));reg_done=1;end
 initial begin #1;b=1;#1;
   if(explicit_done!==0||hidden_done!==0||wide_done!==0||reg_done!==0)$fatal(1,"function sensitivity");
   a=1;#1;
   if(explicit_done!==1||hidden_done!==0||wide_done!==1||reg_done!==1||calls!==2||negative!==-128||wide_result!==130'h200000000000000000000000000000000)$fatal(1,"function wait");
   $display("TRACE functions %0d %0d %0d %0d %0d %0d",explicit_done,hidden_done,wide_done,reg_done,calls,negative);$finish;
 end
endmodule
