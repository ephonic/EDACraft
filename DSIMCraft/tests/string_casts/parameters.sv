package labels;
 typedef string text_t;
 localparam text_t BASE=string'(32'h410042);
 localparam string JOINED={BASE,":suffix"};
 localparam string EMPTY=string'(0);
 localparam bit ORDERED=string'(16'h4142)<string'(24'h414243);
 localparam CHOSEN=0 ? BASE : "literal";
 localparam AMBIGUOUS=1'bx ? BASE : BASE;
 localparam DIFFERENT=1'bx ? BASE : "different";
endpackage
module lane #(parameter string LABEL="default");
 function automatic string read_label();return LABEL;endfunction
 initial if(read_label()!=LABEL)$fatal(1,"local string parameter return");
endmodule
module top;
 import labels::*;
 int observed;
 localparam INFERRED=string'(32'h4344);
 lane #(.LABEL(JOINED)) u();
 lane #(.LABEL(string'(32'h4546))) v();
 initial begin
  if(BASE!="AB" || JOINED!="AB:suffix" || EMPTY!="" || $bits(EMPTY)!=0 || !ORDERED)$fatal(1,"constant string values");
  if(INFERRED!="CD" || $bits(INFERRED)!=16)$fatal(1,"inferred string parameter");
  if(CHOSEN!="literal" || $bits(CHOSEN)!=56 || AMBIGUOUS!=BASE || DIFFERENT!="")$fatal(1,"constant string conditional");
  observed=$bits(CHOSEN);if(observed!=56)$fatal(1,"constant string observation");
  if(u.LABEL!="AB:suffix" || v.LABEL!="EF")$fatal(1,"string parameter override/clone");
  #1;$display("TRACE string parameters u=%s v=%s",u.LABEL,v.LABEL);$finish;
 end
endmodule
