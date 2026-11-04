`timescale 1ps/1ps
module top;
 class Counter;
  int value;
  function new;value=1;endfunction
  function void bump;value++;value++;endfunction
  function int get;return value;endfunction
 endclass
 Counter c;
 int observed;
 function void update; c.bump();observed=c.get();endfunction
 initial begin
  c=new;observed=c.get();
  #2;update();
  #1;update();update();update();
  #2;if(observed!=9)$fatal(1,"restored no-argument call");
  $display("TRACE nonansi rollback value=%0d",observed);$finish;
 end
endmodule
