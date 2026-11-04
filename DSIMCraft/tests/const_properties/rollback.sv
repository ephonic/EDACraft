`timescale 1ps/1ps
module top;
 class Token;
  const int id;
  function new(int n);id=n;endfunction
 endclass
 Token c;
 int observed;
 initial begin
  c=new(1);observed=c.id;
  #2;c=new(3);observed=c.id;
  #1;c=new(9);observed=c.id;
  #2;if(observed!=9)$fatal(1,"const allocation after restore");
  $display("TRACE const rollback value=%0d",observed);$finish;
 end
endmodule
