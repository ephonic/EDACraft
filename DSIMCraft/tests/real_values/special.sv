`timescale 1ps/1ps
module top;
  real observed;
  initial begin
    observed=$bitstoreal(64'h7ff8000000000042);
    if($realtobits(observed)!=64'h7ff8000000000042 || observed==observed)$fatal(1,"NaN payload");
    #1;observed=$bitstoreal(64'h7ff0000000000000);
    if($realtobits(observed)!=64'h7ff0000000000000)$fatal(1,"infinity");
    #1;observed=$bitstoreal(64'h8000000000000000);
    if(observed || $realtobits(observed)!=64'h8000000000000000)$fatal(1,"signed zero");
    #1;$display("TRACE special preserved");$finish;
  end
endmodule
