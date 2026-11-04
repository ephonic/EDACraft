module top;
 int count=0,result=17;
 function automatic int recurse(input int depth);count++;if(depth==0)begin $display("TRACE leaf %0d",count);$finish;end return recurse(depth-1)+1;endfunction
 initial begin #1;result=recurse(5);$display("BAD return");end
 final $display("TRACE final %0d %0d",count,result);
 endmodule
