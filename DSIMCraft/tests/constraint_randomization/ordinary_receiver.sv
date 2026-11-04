interface Link;
 int value;
 function int randomize(input int n);value=n;return value+1;endfunction
endinterface
module top;
 Link link();
 int observed;
 initial begin
  observed=link.randomize(6);
  if(observed!=7||link.value!=6)$fatal(1,"ordinary interface method binding");
  $display("TRACE constraints ordinary receiver randomize method pass");$finish;
 end
endmodule
