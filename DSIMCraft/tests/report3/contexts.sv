`timescale 1ns/1ps
module top;
  localparam [23:0] TAG={"A","BC"};
  localparam integer WIDTH=$bits("ABCDEFGHIJKLMNOPQ");
  localparam [31:0] SUM="AB"+1;
  logic [135:0] wide;
  logic [31:0] word;
  logic [15:0] xview;
  logic unknown=1'bx;
  string text;
  int calls=0;
  function automatic int choose();begin calls++;choose=1;end endfunction
  function automatic logic[31:0] bump(input logic[31:0] x);begin bump=x+1;end endfunction
  initial begin
    #1;
    if(TAG!==24'h414243||WIDTH!=136||SUM!==32'h4143)$fatal(1,"literal constant evaluation");
    wide="ABCDEFGHIJKLMNOPQ";
    if(wide!==136'h4142434445464748494a4b4c4d4e4f5051)$fatal(1,"wide literal byte order");
    word=bump("AB");if(word!==32'h4143)$fatal(1,"packed function argument");
    word=choose()?"AB":32'h4321;
    if(word!==32'h4142||calls!=1)$fatal(1,"conditional integral context");
    xview=unknown?"AB":"AC";
    if(xview!==16'b010000010100001x)$fatal(1,"literal unknown conditional merge");
    text=unknown?"AB":"AC";if(text!="AB")$fatal(1,"string unknown conditional");
    text={"AB","CD"};if(text!="ABCD")$fatal(1,"string concat context");
    word={2{"AB"}};if(word!==32'h41424142)$fatal(1,"literal replication");
    word=int'("AB");if(word!==32'h4142)$fatal(1,"integral literal cast");
    word=~"A";if(word!==32'hffffffbe)$fatal(1,"unary contextual width");
    if("A")word=TAG;else $fatal(1,"packed literal condition");
    case(word)"ABC":word++;default:$fatal(1,"packed literal case");endcase
    text=word; if(text!="ABD")$fatal(1,"packed-to-string conversion");
    $display("TRACE contexts %h %h %0d %b %0d [%s]",TAG,wide,WIDTH,xview,calls,text);
    #1;$finish;
  end
endmodule
