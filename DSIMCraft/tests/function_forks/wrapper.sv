module top;
 int total=0,hits=0,stage=0;
 function automatic void delayed(ref int value);
  fork begin #1;value++;total+=value;hits++;end join_none
 endfunction
 function automatic void middle(input int seed);
  int saved=seed;
  delayed(saved);
 endfunction
 function automatic void outer(input int seed);middle(seed);endfunction
 initial begin outer(3);outer(8);wait fork;stage++;#1;$display("TRACE wrapper %0d %0d",hits,total);$finish;end
endmodule
