`timescale 1ns/1ps
module top;
logic[129:0] wide;logic[7:3] mem[2:6];
logic[1:0] control;logic[129:0] dimension;
int address=2,dim=1,source=3,ctl=0,count=0;
integer q,nba_value;logic[63:0] extended;
function integer bounds(input logic[7:3] data,input integer d);
 bounds=$left(data,d);
endfunction
function int width_probe(input int data);
 width_probe=data+1;
endfunction
initial begin
 q=$size(mem[address++]);if(q!=5||address!=2)$fatal(1,"unevaluated address");
 q=$left(mem,dim++);if(q!=2||dim!=2)$fatal(1,"single dimension evaluation");
 q=$right(mem,dim++);if(q!=3||dim!=3)$fatal(1,"dimension two");
 q=$high(mem,dim++);if(q!==32'bx||dim!=4)$fatal(1,"invalid dimension");
 dimension=130'b1<<100;q=$size(mem,dimension);if(q!==32'bx)$fatal(1,"high dimension");
 dimension=2;dimension[129]=1'bx;q=$size(mem,dimension);if(q!==32'bx)$fatal(1,"unknown high dimension");
 dimension=2;q=$size(mem,dimension);if(q!=5)$fatal(1,"wide valid dimension");
 if(width_probe(0)!=1||bounds(5'b0,1)!=7)$fatal(1,"function types");
 wide=0;wide[129]=1;wide[64]=1;wide[63]=1;wide[128]=1'bx;wide[0]=1'bz;
 if($countbits(wide,1'b1)!=3||$countbits(wide,1'bx)!=1||$countbits(wide,1'bz)!=1||$countbits(wide,1'b0)!=125)$fatal(1,"wide values");
 if($countbits(wide,1'b0,1'b1,1'bx,1'bz,1'bx)!=130)$fatal(1,"duplicate controls");
 control=2'b11;count=$countbits(wide,control);if(count!=3)$fatal(1,"control LSB");
 control=2'bxz;count=$countbits(wide,control);if(count!=1)$fatal(1,"control XZ");
 count=$countbits(source++,1'b0);ctl++;if(count!=30||source!=4||ctl!=1)$fatal(1,"argument effects");
 count=$countbits(mem[address++],1'bx);if(count!=5||address!=3)$fatal(1,"array address once");
 extended=$increment(mem);if(extended!==64'hffffffffffffffff)$fatal(1,"signed query result");
 dimension=1;extended=$increment(mem,dimension);if(extended!==64'hffffffffffffffff)$fatal(1,"dynamic signed query result");
 extended=$countbits(4'b0000,1'b0);if(extended!=4)$fatal(1,"self sized count");
 nba_value<=$countbits(wide,1'bx,1'bz);wide=0;#1;
 if(nba_value!=2)$fatal(1,"NBA capture");
 #($size(mem,2)) q=$right(mem,1);
 assert(q==6)else $fatal(1,"delay query");
 $display("TRACE effects %0d %0d %0d %0d %0t",address,dim,count,q,$time);
end
endmodule
