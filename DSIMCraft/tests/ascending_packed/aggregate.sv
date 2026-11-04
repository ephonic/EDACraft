`timescale 1ns/1ps
module child(input logic[0:7] a,output wire[8:15] y);
assign y={a[4:7],a[0:3]};
endmodule
module top;
typedef logic [0:7] byte_t;
typedef struct packed {logic[2:5] hi;logic[-2:1] lo;} pair_t;
byte_t q,mem[2];pair_t pair;logic[0:1][0:3] multi;wire[7:0] result;integer i;
child u(q,result);
function automatic byte_t flip(input byte_t a);
 byte_t temp;temp[0:3]=a[4:7];temp[4:7]=a[0:3];return temp;
endfunction
function automatic logic[0:7] pick(input logic[0:7] a,input integer idx);
 return {4'b0,a[idx+:4]};
endfunction
task automatic alter(ref byte_t a,input integer idx);
 a[idx+:3]=3'b101;
endtask
initial begin
 q=8'h96;mem[0]=8'ha5;mem[1]=8'h3c;pair=8'h69;multi=8'hb4;i=1;
 #1;$display("TRACE AGG %h %h %h %h %h %b %b %h",result,flip(q),pick(q,i),mem[i][0:3],pair.hi[2:3],pair.lo[-2:0],multi[0],multi[i][0:1]);
 alter(q,2);pair.lo[i-:3]=3'b110;mem[i][2+:3]=3'b010;multi[i][i+:2]=2'b11;
 #1;$display("TRACE WRITE %h %h %h %h %h",q,result,pair,mem[1],multi);
 $display("TRACE HIER %h %h %b",u.a[0:3],u.y[8:11],u.a[i]);
 $finish;
end
endmodule
