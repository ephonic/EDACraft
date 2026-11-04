module top;
 typedef enum bit[7:0] {BYTE_MAX=-8'sd1,BYTE_PREV=-8'sd2} byte_e;
 typedef enum bit[31:0] {WORD_MAX=-1,WORD_PREV=-2,WORD_ZERO=0} word_e;
 typedef enum logic[32:0] {EXT_MAX=-1,EXT_PREV=-2} extended_e;
 typedef enum bit[64:0] {WIDE_MAX=-1,WIDE_PREV=-2} wide_e;
 typedef enum bit[128:0] {HUGE_MAX=-1,HUGE_PREV=-2} huge_e;
 typedef enum logic signed[7:0] {SIGNED_MIN=-128,SIGNED_MAX=127} signed_e;
 localparam int NEGATIVE=-1;
 typedef enum bit[31:0] {PARAM_MAX=NEGATIVE,PARAM_ZERO=0} parameter_e;
 byte_e b;word_e w;extended_e e;wide_e d;huge_e h;parameter_e p;signed_e s;
 initial begin
  b=BYTE_MAX;w=WORD_MAX;e=EXT_MAX;d=WIDE_MAX;h=HUGE_MAX;p=PARAM_MAX;s=SIGNED_MIN;
  if(b!==8'hff||w!==32'hffffffff||e!=={33{1'b1}}||d!=={65{1'b1}}||h!=={129{1'b1}}||p!==w||s!=-128)
   $fatal(1,"enum signed conversion");
  if($bits(w)!=32||$bits(e)!=33||$bits(d)!=65||$bits(h)!=129||w<1||s>=0)
   $fatal(1,"enum width and signedness");
  if(w.name()!="WORD_MAX"||w.first()!=WORD_MAX||w.last()!=WORD_ZERO||w.num()!=3)
   $fatal(1,"enum methods");
  #1;w=w.next();d=WIDE_PREV;h=HUGE_PREV;
  if(w!==32'hfffffffe||d!==({65{1'b1}}-1'b1)||h!==({129{1'b1}}-1'b1))$fatal(1,"enum negative values");
  #1;w=w.next();if(w!=WORD_ZERO)$fatal(1,"enum next order");
  $display("TRACE unsigned %h %h %h %h %h %0d",b,p,e,d,h,s);$finish;
 end
endmodule
