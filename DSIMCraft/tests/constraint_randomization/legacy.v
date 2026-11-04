module top;
 integer randc;
 function integer randomize;
  input integer value;
  begin randomize=value+3;end
 endfunction
 initial begin
  randc=8;if(randc!=8)$fatal(1,"Verilog identifier randc");
  if(randomize(4)!=7)$fatal(1,"Verilog function name randomize");
  $display("TRACE legacy Verilog randomize identifier pass");$finish;
 end
endmodule
