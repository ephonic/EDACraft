module top;
 time a=64'h1234567800000013;
 initial begin : block
  time b=a;
  if(b!==64'h1234567800000013)$fatal(1,"static block initializer must run before initial processes");
  a=0;#1;if(b!==64'h1234567800000013)$fatal(1,"static initializer repeated");
  $display("TRACE runtime initializer");$finish;
 end
endmodule
