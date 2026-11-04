module endpoint #(parameter int BASE=0);
 import "DPI-C" context function int nested(input int x);
 export "DPI-C" function hook;
 export "DPI-C" function inner;
 import "DPI-C" context callback = function int start(input int x);
 int calls=0;int result=0;
 initial if(BASE==10)begin #1;result=start(4);#2;result=start(1);end
 function automatic int hook(input int x);
  calls++;return nested(x)+BASE;
 endfunction
 function automatic int inner(input int x);
  return x*3;
 endfunction
endmodule
module top;
 endpoint #(.BASE(10)) a();endpoint #(.BASE(100)) b();
 initial begin
  #2;$display("TRACE callback %0d %0d %0d",a.result,a.calls,b.calls);
  #2;$display("TRACE again %0d %0d %0d",a.result,a.calls,b.calls);$finish;
 end
endmodule
