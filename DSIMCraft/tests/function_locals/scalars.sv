`timescale 1ns/1ps
module top;
  reg [31:0] state = 32'h1a2b3c4d;
  reg signed [63:0] wide_result;
  reg [7:0] tiny;
  integer i;
  function automatic [31:0] scramble(input [31:0] value);
    reg [31:0] t;
    begin
      t = value ^ (value << 13);
      t = t ^ (t >> 17);
      t = t ^ (t << 5);
      scramble = t;
    end
  endfunction
  function automatic signed [63:0] mix(input signed [63:0] value, input [7:0] shift);
    reg signed [63:0] t;
    begin
      t = value >>> shift;
      if (value[0]) t = -(t + 64'sh7fffffffffffffff);
      else t = (t << 1) ^ value;
      mix = t;
    end
  endfunction
  function automatic bit [7:0] clean(input logic [7:0] value);
    bit [7:0] t;
    begin t = value; clean = t + 8'd1; end
  endfunction
  // Static storage and nonlocal writes must keep the original path.
  integer calls = 0;
  function integer persistent(input integer value);
    integer n = 5;
    begin n = n + value; persistent = n; end
  endfunction
  function automatic [31:0] effect(input [31:0] value);
    begin calls = calls + 1; effect = value + calls; end
  endfunction
  initial begin
    for(i=0;i<24;i=i+1) begin
      if(i==8) state = 32'hx0z01234;
      if(i==9) state = 32'h89abcdef;
      state = scramble(state);
      wide_result = mix({state, ~state}, i * 7);
      tiny = clean(i==8 ? 8'bx10z0011 : state[7:0]);
      $display("TRACE i=%0d state=%h wide_result=%h tiny=%h persistent=%0d effect=%h calls=%0d",
               i,state,wide_result,tiny,persistent(2),effect(state),calls);
      #1;
    end
    $finish;
  end
endmodule
