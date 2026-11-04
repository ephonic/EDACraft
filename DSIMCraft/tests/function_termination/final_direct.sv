module top;
 initial #1 $finish;
 final begin $display("TRACE final before");$finish;$display("TRACE final after");end
 endmodule
