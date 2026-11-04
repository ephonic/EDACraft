`timescale 1ns/1ps
module top;
 logic[7:0] a[2]='{3,4};logic[7:0] d[];
 integer fixed_result,open_result,dynamic_result;logic[7:0] suspended;
 function automatic integer fixed_sum(input logic[7:0] data[2]);return data.sum();endfunction
 function automatic integer open_sum(input logic[7:0] data[]);return data.sum();endfunction
 function automatic integer dynamic_product(const ref logic[7:0] data[]);return data.product();endfunction
 task automatic later(input logic[7:0] data[2],output logic[7:0] result);
  logic[7:0] local_data[2]='{5,6};
  #2;result=data.sum()+local_data.product();
 endtask
 initial begin
  d=new[2];d[0]=8;d[1]=9;
  fixed_result=fixed_sum(a);open_result=open_sum(a);dynamic_result=dynamic_product(d);
  later(a,suspended);
  #1;$display("TRACE automatic %0d %0d %0d %0d",fixed_result,open_result,dynamic_result,suspended);
 end
endmodule
