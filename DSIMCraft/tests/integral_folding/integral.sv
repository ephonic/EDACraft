module top;
 function automatic int factorial(input int n);int r;int i;r=1;for(i=1;i<=n;i=i+1)r=r*i;return r;endfunction
 function automatic int selected(input int n);return n>3?24:7;endfunction
 localparam int WIDTH=factorial(4);
 localparam int CHOICE=selected(5);
 logic [WIDTH-1:0] bits_value;
 int calls=0;
 function automatic int next_value();calls++;return calls;endfunction
 int first=next_value();
 initial begin
  bits_value='1;
  if(WIDTH!=24||CHOICE!=24||$bits(bits_value)!=24||first!=1||calls!=1)$fatal(1,"constant or runtime initializer");
  if(next_value()!=2||calls!=2)$fatal(1,"side effect folded");
  $display("TRACE integral %0d %0d %0d %0d",WIDTH,CHOICE,$bits(bits_value),calls);
  $finish;
 end
endmodule
