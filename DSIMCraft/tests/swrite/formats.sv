`timescale 1ns/1ps
module top;
 string s,fmt="[%0d]",text="a%0db";int n=-7;byte unsigned u=253;int stage=0;
 initial begin
  $swrite(s,"A",n,"B%0d",5,"C",u);$display("TRACE mixed <%s>",s);
  $swrite(s,fmt,5);$display("TRACE dynamic <%s>",s);
  $swrite(s,text,5);$display("TRACE text <%s>",s);
  $swrite(s,"hello %%");$display("TRACE escape <%s>",s);
  $swrite(s,"[%.2f]",3);$display("TRACE realfmt <%s>",s);
  $swrite(s,"%0d",4,"%s","%0d",8);$display("TRACE consumed <%s>",s);
  $swrite(s,"[%h/%c/%s]","AB","CD","");$display("TRACE literals <%s>",s);
  stage++;#1;$timeformat(-9,1,"ns",0);$swrite(s,"%m/%t",$time);$display("TRACE time <%s>",s);$finish;
 end
endmodule
