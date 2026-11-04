module top;
 import "DPI-C" function int bump();
 import "DPI-C" function int count();
 import "DPI-C" pure function int pure_twice(input int x);
 int observed=0;
 initial begin
  #2;observed=bump();$display("TRACE bump %0d",observed);
  #2;observed=pure_twice(observed);$display("TRACE count %0d %0d",observed,count());
  #2;observed=pure_twice(observed);$display("TRACE final %0d",observed);$finish;
 end
endmodule
