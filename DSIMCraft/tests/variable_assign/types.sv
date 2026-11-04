`timescale 1ns/1ps
module top;
 typedef enum logic[2:0] {IDLE=1,RUN=3,DONE=7} State;
 typedef struct packed {logic[3:0] hi;bit[3:0] lo;} Pair;
 State state,next_state;
 Pair pair;
 logic signed[129:0] d;
 logic signed[135:0] q;
 bit [129:0] two;
 logic [3:0] n;
 logic [3:0] words[0:1][2:3];
 wire [15:0] image;
 assign q=d;
 assign #1 two=d;
 assign pair.hi=n,pair.lo=n;
 assign words[0][2]=n,words[0][3]=n,words[1][2]=n,words[1][3]=n;
 assign image={words[0][2],words[0][3],words[1][2],words[1][3]};
 assign next_state=state.next();
 initial begin
  d=-130'sd3;n=9;state=IDLE;
  #2 $display("TRACE types %h %h %h %h %h",q,two,pair,image,next_state);
  if(q!==-136'sd3||two!==-130'sd3||pair!==8'h99||image!==16'h9999||next_state!==RUN)$fatal(1,"types first");
  d=130'h200000000000000000000000000000005;n=4'bxz01;state=DONE;
  #2 $display("TRACE types %h %h %b %b %h",q,two,pair,image,next_state);
  if(q!==136'hfe00000000000000000000000000000005||pair!==8'bxz01xz01||pair.lo!==1||image!==16'bxz01xz01xz01xz01||next_state!==IDLE)$fatal(1,"types second");
  d=130'h123456789abcdef0123456789abcdef01;n=6;state=RUN;
  #2 $display("TRACE types %h %h %h %h %h",q,two,pair,image,next_state);
  if(q!==136'h123456789abcdef0123456789abcdef01||pair!==8'h66||image!==16'h6666||next_state!==DONE)$fatal(1,"types final");
  $finish;
 end
endmodule
