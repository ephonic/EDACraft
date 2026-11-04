`timescale 1ns/1ps
module top;
 logic[7:0] a[2]='{3,4},d[];integer fixed_result,open_result,dynamic_result,suspended;
 function automatic integer fixed_sum(input logic[7:0] data[2],input integer bias);
  return data.sum(x) with(int'(x)+bias);
 endfunction
 function automatic integer open_sum(input logic[7:0] data[]);
  logic[7:0] local_data[2]='{5,6};
  return data.sum with(int'(item))+local_data.product with(int'(item));
 endfunction
 function automatic integer dynamic_sum(const ref logic[7:0] data[]);
  return data.sum with(int'(item)*2);
 endfunction
 task automatic later(input logic[7:0] data[2],output integer result);
  logic[7:0] local_data[2]='{5,6};
  #2;result=data.sum with(int'(item))+local_data.product with(int'(item));
 endtask
 initial begin
  d=new[2];d[0]=8;d[1]=9;
  fixed_result=fixed_sum(a,1);open_result=open_sum(a);dynamic_result=dynamic_sum(d);
  later(a,suspended);#1;
  $display("TRACE automatic %0d %0d %0d %0d",fixed_result,open_result,dynamic_result,suspended);
 end
endmodule
