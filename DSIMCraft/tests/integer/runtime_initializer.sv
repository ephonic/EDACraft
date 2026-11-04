module top;
 integer a=19,calls=0;
 function automatic integer next_value();
  integer local_value=5;
  calls++;
  return local_value+calls;
 endfunction
 integer first=next_value(),second=next_value();
 initial begin : block
  integer b=a;
  if(b!==19)$fatal(1,"static block initializer must run before initial processes");
  if(calls!=2||first!=6||second!=7)$fatal(1,"initializer function effects and automatic local storage");
  a=0;#1;if(b!==19)$fatal(1,"static initializer repeated");
  $display("TRACE runtime initializer");$finish;
 end
endmodule
