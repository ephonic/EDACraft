`timescale 1ns/1ps
module top;
  logic [3:0] sel=0;
  logic signed [3:0] small_signed=-1;
  logic signed [63:0] long_signed=-1;
  logic [63:0] key64=64'hffffffffffffffff;
  integer q=0, calls=0, i;
  function automatic integer label_effect(input integer value);
    calls=calls+1;label_effect=value;
  endfunction
  function automatic integer decode(input logic [3:0] value);
    case(value)
      4'd0,4'd0:decode=10;
      4'd1:decode=11;
      4'd15:decode=25;
      default:decode=-1;
    endcase
  endfunction
  initial begin
    for(i=0;i<20;i=i+1) begin
      if(i==16)sel=4'bx001;
      else if(i==17)sel=4'bz001;
      else sel=i;
      unique case(sel)
        4'd0,4'd0:q=10;
        4'd1,4'd2:q=11;
        4'd2:q=12;
        4'd15:q=25;
        default:q=-1;
      endcase
      $display("TRACE select %b %0d %0d",sel,q,decode(sel));
      #1;
    end
    case(long_signed)
      4'shf:q=30;
      64'sh8000000000000000:q=31;
      default:q=32;
    endcase
    if(q!=30)$fatal(1,"signed case extension");
    case(small_signed)
      64'shffffffffffffffff:q=33;
      default:q=34;
    endcase
    if(q!=33)$fatal(1,"signed selector extension");
    // An unsigned label prevents sign extension of all operands.
    case(small_signed)
      64'hffffffffffffffff:q=35;
      4'shf:q=36;
      default:q=37;
    endcase
    if(q!=36)$fatal(1,"mixed signed case");
    case(key64)
      64'h8000000000000000:q=38;
      64'hffffffffffffffff:q=39;
      default:q=40;
    endcase
    if(q!=39)$fatal(1,"64-bit case key");
    sel=0;
    // First-match priority and duplicate branches are distinct from unique.
    priority case(sel) 0:q=41;0:q=42;endcase
    if(q!=41)$fatal(1,"priority first match");
    case(sel) 0,0:q=43;0:q=44;endcase
    if(q!=43)$fatal(1,"ordinary first match");
    sel=9;
    unique0 case(sel) 0:q=45;1:q=46;endcase
    priority case(sel) 0:q=45;1:q=46;endcase
    unique case(sel) 0:q=45;1:q=46;endcase
    #1;
    // Side-effect labels and X/Z labels must retain ordered matching.
    sel=2;
    case(sel)
      label_effect(2),label_effect(3):q=47;
      label_effect(2):q=48;
      default:q=49;
    endcase
    if(q!=47||calls!=2)$fatal(1,"comma label evaluation");
    sel=4'bx001;
    case(sel) 4'bx001:q=50;4'bz001:q=51;default:q=52;endcase
    if(q!=50)$fatal(1,"X exact label");
    casez(sel) 4'b?001:q=53;default:q=54;endcase
    if(q!=53)$fatal(1,"casez fallback");
    casex(sel) 4'b0001:q=55;default:q=56;endcase
    if(q!=55)$fatal(1,"casex fallback");
    $display("TRACE final %0d %0d",q,calls);
    #1;$finish;
  end
endmodule
