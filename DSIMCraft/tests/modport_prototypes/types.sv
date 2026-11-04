`timescale 1ns/1ps
package signatures;
 typedef enum logic[1:0]{IDLE=0,RUN=2} mode_t;
 typedef struct packed {logic[3:0] upper;bit[3:0] lower;} word_t;
 typedef struct packed {logic[7:0] renamed;} word_view_t;
 typedef logic signed[79:0] wide_t;
endpackage
interface typed_bus import signatures::*; ();
 mode_t mode=RUN;word_t value=8'ha3;
 modport client(import function mode_t status(), function word_view_t word(input logic[1:0][3:0] arg), function wide_t widen(input logic signed[7:0] arg),input value);
 function automatic mode_t status();return mode;endfunction
 function automatic word_t word(input word_t arg);word_t result_value;result_value.upper=arg.upper^value.upper;result_value.lower=arg.lower+value.lower;return result_value;endfunction
 function automatic wide_t widen(input logic signed[7:0] arg);return arg;endfunction
endinterface
module client import signatures::*; (typed_bus.client p);
 mode_t mode;word_t input_value=8'h12,result_value;wide_t wide_value;
 initial begin mode=p.status();result_value=p.word(input_value);wide_value=p.widen(-3);
  if(mode!=RUN||result_value!=8'hb5||wide_value!=-80'sd3||$bits(p.widen(1))!=80)$fatal(1,"FAIL prototype types");
  $display("TRACE types %s %h %h",mode.name(),result_value,wide_value);end
endmodule
module top;typed_bus b();client c(b);initial begin #1;$finish;end endmodule
