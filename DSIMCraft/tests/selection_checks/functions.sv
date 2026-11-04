`timescale 1ns/1ps
module lane #(parameter V=1)(output integer q);
 function automatic integer classify(input logic[2:0] x);
  unique case(x) 1:return 10;2:return 20;default:return 30;endcase
 endfunction
 task automatic walk(input logic[2:0] x,output integer result);
  unique if(x<3)begin #2;result=classify(x);end
  else result=40;
 endtask
 initial begin walk(V,q);end
endmodule
module top;
wire[31:0] a,b;integer q=0,r=0,c=0,d=0;logic x=0;
lane #(1) u(a);lane #(2) v(b);
function automatic integer choose(input logic bitval);
 unique if(bitval)return 1;else return 2;
endfunction
function automatic integer checked(input logic flag);
 unique if(flag)return 1; // report no-match 2000
 return 0;
endfunction
initial begin #2;c=checked(0);@(x);c=checked(1);end
initial begin #2;d=checked(0);end
initial begin #2;#0;x=0;end
initial begin
 q=choose(x);#1;x=1;r=choose(x);
 #3;if(a!==10||b!==20||q!==2||r!==1||c!==1||d!==0)$fatal(1,"subroutine and module cloning");
 $display("TRACE functions %0d %0d %0d %0d",a,b,q,r);
end
endmodule
