`timescale 1ns/1ps
module top;
 string s="AbC001",a,b,joined,zeroes="000word";
 longint wide_comparison;
 byte signed neg=-1;byte unsigned byte_index=255;
 integer n=0,character=0,comparison=0;reg equal=0;
 initial begin
  #0.25;
  if($bits(s.len())!=32||$bits(s.getc(0))!=8||s.len()!=6||s.getc(0)!=65||s.getc(-1)!=0||s.getc(99)!=0) $fatal(1,"length or character");
  if(s.getc(32'bx)!=65||s.getc(32'bx1)!=98||s.substr(32'bx,1)!=""||s.substr(0,32'bx)!="")$fatal(1,"unknown index");
  if(s.substr(1,3)!="bC0"||s.substr(-1,2)!=""||s.substr(2,99)!=""||s.substr(4,2)!="") $fatal(1,"substring bounds");
  if(s.tolower()!="abc001"||s.toupper()!="ABC001"||s.icompare("aBc001")!=0||s.compare("AbC000")!=1||s.compare("ZZZ")!=-25||s.compare("A")!=1||s.compare("AbC001a")!=-1||s.compare("AbC004")!=-3) $fatal(1,"case or comparison");
  wide_comparison=s.compare("ZZZ");if(wide_comparison!=-25)$fatal(1,"signed wide method result");
  a="0123456789abcdef";b=a;
  repeat(7) a={a,a};
  if(a.getc(neg)!=0||a.getc(byte_index)!=102||a.substr(neg,1)!="")$fatal(1,"signed method arguments");
  if(a.len()!=2048||b.len()!=16||a.substr(2032,2047)!=b) $fatal(1,"dynamic length and copy independence");
  joined={s,"/",b};n=a.len();character=a.getc(2047);equal=joined=="AbC001/0123456789abcdef";comparison=s<"foobar";if(("z"<"aa")!=1)$fatal(1,"packed literal comparison");
  $display("TRACE methods %0d %0d %0d %0d [%s] [%10s] [%0s]",n,character,equal,comparison,joined,"ok",zeroes);
  #0.25;$finish;
 end
endmodule
