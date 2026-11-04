`timescale 1ns/1ps
module top;
  reg clk=0;
  reg [31:0] words[0:0];
  reg [31:0] data=32'h12345678, result=0, mask=32'h10203040;
  integer n=0;
  initial begin $readmemh("input.mem",words); data=words[0]; end
  always #5 clk=~clk;

  function automatic [31:0] mix(input [31:0] x);
    integer i;
    reg [31:0] t;
    begin
      t=x;
      for(i=0;i<8;i=i+1) t=(t>>1)^(32'hedb88320 & {32{t[0]}});
      mix=t;
    end
  endfunction

  function automatic [31:0] global_mix(input [31:0] x);
    integer i;
    reg [31:0] t;
    begin
      t=x;
      for(i=0;i<3;i=i+1) t=(t<<1)^mask;
      global_mix=t;
    end
  endfunction

  function automatic [31:0] two_mix(input [31:0] x);
    integer i;
    bit [31:0] t;
    begin
      t=x;
      for(i=0;i<4;i=i+1) t=(t>>1)+32'h13579bdf;
      two_mix=t;
    end
  endfunction

  always @(posedge clk) begin
    result<=mix(data)^global_mix(data)^two_mix(data);
  end
  initial begin
    repeat(9) begin
      @(negedge clk);
      $display("TRACE loop %0d %h %h %h %h",n,result,mix(data),global_mix(data),two_mix(data));
      n=n+1;
      case(n)
        1:data=0;
        2:data=32'hffffffff;
        3:data=32'hx1234567;
        4:data=32'hz1234567;
        default:data=data+32'h12345;
      endcase
      mask=mask+32'h103;
    end
    $finish;
  end
endmodule
