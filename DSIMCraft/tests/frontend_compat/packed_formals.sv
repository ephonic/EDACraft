`timescale 1ns/1ps
module top;
  typedef logic [1:0][7:0] pair_t;
  pair_t typed;
  logic [1:0][7:0] value;
  integer calls=0;
  function automatic [1:0][7:0] swap(input logic [1:0][7:0] x);
    logic [1:0][7:0] local_value;
    local_value=x;swap[0]=local_value[1];swap[1]=local_value[0];
  endfunction
  task automatic change(input logic [1:0][7:0] x, output logic [1:0][7:0] y);
    logic [1:0][7:0] saved;
    integer i;
    saved=x;i=0;saved[i]+=8'd1;#1;y=saved;calls++;
  endtask
  initial begin
    typed=16'h12a5;value=swap(typed);
    if(value!==16'ha512||$size(typed,2)!==8) $fatal(1,"function/type");
    change(value,typed);
    if(typed!==16'ha513||calls!==1) $fatal(1,"task");
    $display("TRACE formals %h %h %0d",value,typed,calls);
    $finish;
  end
endmodule
