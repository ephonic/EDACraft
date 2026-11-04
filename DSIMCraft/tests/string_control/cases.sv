`timescale 1ns/1ps
module top;
 string s="abc", label="abc";integer q=0,calls=0;reg done=0;
 function automatic string choose();calls=calls+1;return s;endfunction
 initial begin
  case(choose()) "":q=1;"short",label:q=7;default:q=99;endcase
  if(q!=7||calls!=1)$fatal(1,"selector or comma labels");
  $display("TRACE case %0d %0d",q,calls);
  s="longer than one byte";
  unique case(s) "longer":q=1;"longer than one byte":q=8;default:q=9;endcase
  priority case(s) "longer than one byte":q=q+1;"longer than one byte":q=99;default:q=0;endcase
  $display("TRACE qualified %0d",q);
  s="";case(s) "abc":q=1;default:q=2;endcase
  $display("TRACE default %0d",q);done=1;#1;$finish;
 end
endmodule
