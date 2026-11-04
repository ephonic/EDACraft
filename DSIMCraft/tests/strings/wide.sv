`timescale 1ns/1ps
module top;
 typedef enum logic[129:0] {VERY_LONG_ENUMERATION_LABEL_EXCEEDING_SIXTY_FOUR_CHARACTERS_AND_ANY_PACKED_REGISTER=130'h200000000000000001,ALL_UNKNOWN=130'bx,ALL_HIGH_IMPEDANCE=130'bz} state_t;
 state_t state;string name;integer length=0;reg good=0;
 initial begin
  #0.25;state=VERY_LONG_ENUMERATION_LABEL_EXCEEDING_SIXTY_FOUR_CHARACTERS_AND_ANY_PACKED_REGISTER;name=state.name();length=name.len();
  if(name!="VERY_LONG_ENUMERATION_LABEL_EXCEEDING_SIXTY_FOUR_CHARACTERS_AND_ANY_PACKED_REGISTER")$fatal(1,"long name");
  state=ALL_UNKNOWN;if(state.name!="ALL_UNKNOWN")$fatal(1,"wide X");
  state=ALL_HIGH_IMPEDANCE;if(state.name()!="ALL_HIGH_IMPEDANCE")$fatal(1,"wide Z");
  state=state_t'(9);if(state.name()!="")$fatal(1,"invalid enum");
  good=1;$display("TRACE wide %0d [%s] %0d",length,name,good);#0.25;$finish;
 end
endmodule
