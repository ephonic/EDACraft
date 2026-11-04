module top;
 function automatic int fractional_compare();return 0.5>0.25;endfunction
 function automatic int fractional_local();real r=0.75;return r>0.5;endfunction
 function automatic real fraction();return 1.25;endfunction
 int compared=fractional_compare();
 int local_result=fractional_local();
 real r=fraction();
 initial begin
  if(compared!=1||local_result!=1||r!=1.25)$fatal(1,"real folding");
  $display("TRACE real %0d %0d %0.2f",compared,local_result,r);
  $finish;
 end
endmodule
