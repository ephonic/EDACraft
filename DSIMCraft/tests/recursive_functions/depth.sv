module top;
 function automatic int recurse(int n);return recurse(n+1)+n;endfunction
 int value;
 initial value=recurse(0);
endmodule
