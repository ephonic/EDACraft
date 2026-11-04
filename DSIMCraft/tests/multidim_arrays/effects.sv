`timescale 1ns/1ps
module top;
logic[7:0] a[1:2][3:4];wire[31:0] image={a[1][3],a[1][4],a[2][3],a[2][4]};
integer calls=0,x=1,y=3;logic[7:0] q;
function integer f(input integer v);calls++;return v;endfunction
function void put(output logic[7:0] v);v=8'ha5;endfunction
initial begin
 foreach(a[i,j])a[i][j]=i*16+j;
 q=a[f(0)][f(3)];if(q!==8'hxx || calls!==2)$fatal(1,"invalid calls");
 a[f(1)][f(3)]+=1;if(a[1][3]!==20 || calls!==4)$fatal(1,"compound calls");
 q=a[f(1)][f(3)]++;if(q!==20 || a[1][3]!==21 || calls!==6)$fatal(1,"update calls");
 a[f(0)][f(4)]=8'hff;if(calls!==8)$fatal(1,"invalid write calls");
 a[f(1)][f(4)]<=#2 8'h66;
 #1;x=2;y=4;
 #2;if(a[1][4]!==8'h66 || a[2][4]!==8'h24 || calls!==10)$fatal(1,"NBA address");
 put(a[f(2)][f(3)]);if(a[2][3]!==8'ha5 || calls!==12)$fatal(1,"output address");
 a[x][y]=#2 8'h77;
 #1;if(a[2][4]!==8'h77)$fatal(1,"blocking delay");
 $display("TRACE effects %0d %h",calls,image);
end
endmodule
