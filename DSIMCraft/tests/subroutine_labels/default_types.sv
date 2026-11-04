module top;
 typedef enum int {LOW=3,HIGH=7} level_t;
 typedef struct packed {bit[3:0] clean;logic[3:0] raw;} mixed_t;
 typedef logic[128:0] wide_t;
 function automatic wide_t wide(input wide_t a,input wide_t b=a+1);return b;endfunction : wide
 function automatic string text_value(input string a,input string b={a,"!"});return b;endfunction : text_value
 function automatic real real_value(input real a,input real b=a+0.5);return b;endfunction : real_value
 function automatic int enum_value(input level_t a,input int b=(a==HIGH)?11:5);return b;endfunction : enum_value
 function automatic mixed_t mixed(input mixed_t a,input mixed_t b=a);return b;endfunction : mixed
 function automatic int select_value(input logic[0:7] a,input int index,input int b=a[index+:3]);return b;endfunction : select_value
 function automatic int signed_value(input bit signed[3:0] a,input int b=a);return b;endfunction : signed_value
 mixed_t m;wide_t observed;string text_out;real real_out;
 initial begin
  observed=wide(129'h10000000000000000);text_out=text_value("hello");real_out=real_value(1.25);
  m=mixed(8'bx1z1_10xz);
  if(observed!=129'h10000000000000001||text_out!="hello!"||real_out!=1.75||m!==8'bx1z1_10xz)$fatal(1,"typed defaults");
  $display("TRACE defaults types %0h %s %0.2f %0d %0d %b",observed,text_out,real_out,enum_value(HIGH),enum_value(LOW),m);
  $display("TRACE defaults select %0d %0d",select_value(8'b10110101,2),select_value(8'b10110101,5));
  $display("TRACE defaults signed %0d",signed_value(31));
  #1;$finish;
 end
endmodule
