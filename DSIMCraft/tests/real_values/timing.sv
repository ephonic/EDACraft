`timescale 1ns/1ps
module top;
  realtime delay_value, seen;
  real observed;
  initial begin
    delay_value=1.25;observed=0.5;
    #delay_value;seen=$realtime;observed=1.25;
    if(seen!=1.25)$fatal(1,"realtime fractional delay");
    #(0.25+0.5);observed+=0.5;
    if($realtime!=2.0)$fatal(1,"real delay arithmetic");
    #0.5;observed<=2.5;
    #0.5;if(observed!=2.5)$fatal(1,"real NBA");
    $display("TRACE timing t=%0.3f value=%0.2f",$realtime,observed);
    $finish;
  end
endmodule
