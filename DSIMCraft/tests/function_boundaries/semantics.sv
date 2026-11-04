`timescale 1ps/1ps
module top;
  integer calls=0,pos=0;
  logic [63:0] data[0:1];
  logic [127:0] a,b;
  function automatic logic[127:0] encode(input logic[63:0] value);
    integer k;
    for(k=0;k<64;k=k+1)case(value[k])
      1'b0:encode[k*2+:2]=2'b00;
      1'b1:encode[k*2+:2]=2'b01;
      1'bx:encode[k*2+:2]=2'b10;
      1'bz:encode[k*2+:2]=2'b11;
    endcase
    calls++;
  endfunction
  initial begin
    data[0]=64'h0123456789abcdef;data[1]={32'hxz01xz01,32'hfedcba98};
    a=encode(data[pos++]);b=encode(data[pos++]);
    if(calls!=2||pos!=2)$fatal(1,"argument or body side effects repeated");
    #1;$display("TRACE boundaries %h %h %0d %0d",a,b,calls,pos);
    $finish;
  end
endmodule
