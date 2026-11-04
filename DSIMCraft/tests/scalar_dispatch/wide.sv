`timescale 1ns/1ps
module top;
  logic [128:0] value=129'h100000000000000000000000000000001;
  integer q=0;
  string text="hello";
  initial begin
    case(value)
      129'h100000000000000000000000000000001:q=1;
      default:q=2;
    endcase
    if(q!=1)$fatal(1,"wide scalar case fallback");
    case(text) "hello":q=3;default:q=4;endcase
    if(q!=3)$fatal(1,"string case fallback");
    #1;value=129'bx;
    case(value) 129'bx:q=5;default:q=6;endcase
    if(q!=5)$fatal(1,"wide X fallback");
    $display("TRACE wide %0d",q);#1;$finish;
  end
endmodule
