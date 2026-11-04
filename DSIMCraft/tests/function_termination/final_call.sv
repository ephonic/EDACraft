module top;
 int count=0;
 function automatic void die();count++;$display("TRACE function");$finish;$display("TRACE function after");endfunction
 initial #1 $finish;
 final begin $display("TRACE final before");die();$display("TRACE final after");end
 endmodule
