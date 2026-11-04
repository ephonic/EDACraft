`timescale 1ns/1ps
interface views #(parameter BIAS=4);
 integer state=3;
 modport a(import function integer read(input integer renamed=BIAS));
 modport b(import function integer read(input integer original=BIAS+3));
 modport c(import function integer read(input integer original=state+BIAS));
 function automatic integer read(input integer original=1);return state+original;endfunction
endinterface
module client(views.a a,views.b b,views.c c);
 integer one,two,three,four,named_value,empty_value;
 initial begin one=a.read();two=b.read();three=c.read();named_value=a.read(.original(5));empty_value=a.read(.original());
  #2;four=c.read();
  if(one!=7||two!=10||three!=10||four!=22||named_value!=8||empty_value!=7)$fatal(1,"FAIL prototype defaults");
  $display("TRACE defaults %0d %0d %0d %0d %0d %0d",one,two,three,four,named_value,empty_value);end
endmodule
module top;
 views v();client c(v.a,v.b,v.c);integer direct;
 initial begin direct=v.read();#1;v.state=9;#2;if(direct!=4)$fatal(1,"FAIL direct default");
  $display("TRACE defaults direct %0d",direct);#1;$finish;end
endmodule
