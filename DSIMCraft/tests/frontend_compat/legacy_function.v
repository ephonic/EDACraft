module top;
 integer value;
 function integer new;
  input integer n;
  begin new=n+1;end
 endfunction
 initial begin value=new(4);$display("TRACE legacy function=%0d",value);$finish;end
endmodule
