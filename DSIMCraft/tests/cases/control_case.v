module top;
  reg [3:0] selector,label;
  reg [7:0] result;
  initial begin
    selector=4'b10xz; result=0;
    case(selector)
      default: result=9;
      4'b10xx: result=1;
      4'b10xz: result=2;
      4'b10xz: result=3;
    endcase
    $display("TRACE exact=%0d",result);
    casez(selector)
      4'b1000: result=4;
      4'b10x0: result=5;
      default: result=6;
    endcase
    $display("TRACE casez=%0d",result);
    casex(selector)
      4'b1011: result=7;
      4'b10xx: result=8;
      default: result=9;
    endcase
    $display("TRACE casex=%0d",result);
    selector=4'b0110; label=4'b0110;
    case(selector)
      4'h0,4'h1: result=10;
      {2'b01,2'b10}: result=11;
      label: result=12;
      default: result=13;
    endcase
    $display("TRACE concat=%0d",result);
    selector=4'b1111;
    case(selector)
      8'hff: result=14;
      4'hf: result=15;
      default: result=16;
    endcase
    $display("TRACE width=%0d",result);
    case(4'hf+4'h1)
      8'h10: result=24;
      8'h00: result=25;
      default: result=26;
    endcase
    $display("TRACE context=%0d",result);
    case('1)
      4'hf: result=27;
      default: result=28;
    endcase
    $display("TRACE fill=%0d",result);
    result=17;
    case(selector) 4'h0: result=18; endcase
    $display("TRACE hold=%0d",result);
    selector=4'bz001;
    casez(selector)
      4'b0001: result=19;
      default: result=20;
    endcase
    $display("TRACE selector_wild=%0d",result);
    selector=4'h6;
    case(selector)
      label,4'h7: begin
        selector=0;
        #0;
        case(selector) 0: result<=21; default: result<=22; endcase
      end
      default: result=23;
    endcase
    #1 $display("TRACE nested=%0d selector=%h",result,selector);
    $finish;
  end
endmodule
