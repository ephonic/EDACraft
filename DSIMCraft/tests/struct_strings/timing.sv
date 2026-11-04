module top;
 typedef struct {string text;bit [3:0] bits;logic [79:0] wide;} item_t;
 item_t a,b;
 int phase,observed;
 initial begin
  a='{text:"first",bits:4'bxz10,wide:80'h123456789abcdef01234};b=a;
  a = #2 b;
  phase=1;
  if(a.text!="first"||a.bits!==4'b0010||a.wide!==80'h123456789abcdef01234)$fatal(1,"delayed snapshot");
  a.text="third";a.bits=4'bx101;
  #1;if(a.text!="third"||a.bits!==4'b0101)$fatal(1,"integral field conversion");phase=2;
  a.text.putc(0,"T");a.bits=4'bx101;
  if(a.text!="Third"||a.bits!==4'b0101||a.wide!==80'h123456789abcdef01234)$fatal(1,"field normalization");
  b = #1 a;
  if(b.text!="Third"||b.wide!==a.wide)$fatal(1,"blocking delay");
  a.text = #1 "last";
  if(a.text!="last")$fatal(1,"string blocking delay");
  observed=a.bits;phase=3;
  $display("TRACE timing %s %s %0d",a.text,b.text,observed);
  #1;$finish;
 end
 initial begin #1;b.text="second";b.wide=80'hffffffffffffffffffff;end
endmodule
