`timescale 1ns/1ps
module top;
 logic a,y;
 bit b;
 logic [7:0] d,q;
 logic [3:0] v;
 wire [3:0] netpart;
 assign #2 y=a;
 assign #2 b=a;
 assign #2 q=d;
 assign #2 {netpart,v}=d;
 initial begin
  a=0;d=8'h12;
  #1 $display("TRACE pending %b %b %h",y,b,q);
  if(y!==1'bx||b!==0||q!==8'hxx)$fatal(1,"delay startup");
  a=1;d=8'h34;
  #1 a=0;d=8'h56;
  #3 $display("TRACE stable %b %b %h %h %h",y,b,q,netpart,v);
  if(y!==0||b!==0||q!==8'h56||netpart!==5||v!==6)$fatal(1,"inertial cancel");
  a=1'bx;d=8'hxz;
  #3 $display("TRACE unknown %b %b %h %h %h",y,b,q,netpart,v);
  if(y!==1'bx||b!==0||q!==8'hxz||netpart!==4'hx||v!==4'hz)$fatal(1,"delayed unknown");
  a=1'bz;d=8'hab;
  #3 $display("TRACE final %b %b %h %h %h",y,b,q,netpart,v);
  if(y!==1'bz||b!==0||q!==8'hab||netpart!==10||v!==11)$fatal(1,"delayed final");
  $finish;
 end
endmodule
