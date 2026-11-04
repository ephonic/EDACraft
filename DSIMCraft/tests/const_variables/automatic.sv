module top;
 function automatic int compute(input int n);
  const int value=n+1;const string label="local";
  if(label!="local")return -100;return value;
 endfunction
 int observed;
 initial begin observed=compute(3)+compute(7);if(observed!=12)$fatal(1,"automatic initialization");
 #1;$display("TRACE const automatic %0d",observed);$finish;end
endmodule
