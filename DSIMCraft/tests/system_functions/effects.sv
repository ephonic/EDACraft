`timescale 1ns/1ps
module top;
typedef struct packed{bit[3:0] b;logic[125:0] data;} packet_t;
packet_t packet;logic[129:0] wide;bit[129:0] two;
int index=0,count=0,saved=0;int mem[0:1];
logic[63:0] extended;
function int count_input(input logic[129:0] value);
 count_input=$countones(value);
endfunction
initial begin
 if($bits(packet)!=130||$bits(packet.data)!=126||$bits(wide[5+:65])!=65)$fatal(1,"width");
 if($isunknown(two)||!$isunknown(wide)||$countones(wide)!=0||$onehot(wide)||!$onehot0(wide))$fatal(1,"initial states");
 wide=0;wide[129]=1;wide[64]=1;wide[63]=1;
 if($countones(wide)!=3||$onehot(wide)||$isunknown(wide))$fatal(1,"word boundaries");
 wide[128]=1'bx;wide[0]=1'bz;
 if($countones(wide)!=3||!$isunknown(wide)||count_input(wide)!=3)$fatal(1,"wide XZ");
 two=wide;if($countones(two)!=3||$isunknown(two))$fatal(1,"two state");
 packet='x;if($isunknown(packet.b)||!$isunknown(packet.data))$fatal(1,"member conversion");
 if($countones(4'b1111)!=4||$countones(4'b1111)+64'b0!=64'd4)$fatal(1,"self width");
 count=$countones(index++);saved=$clog2(++index);
 if(index!=2||count!=0||saved!=1)$fatal(1,"single evaluation");
 mem[0]=130;mem[1]=129;index=0;
 count=$countones(mem[index++]);if(index!=1||count!=2)$fatal(1,"array address");
 extended=$countones(-1);if(extended!=32)$fatal(1,"signed argument");
 if($clog2(0)!=0||$clog2(1)!=0||$clog2(2)!=1||$clog2(3)!=2||$clog2(-1)!=32)$fatal(1,"clog2");
 if($clog2(4'bz001)!==32'bx||$clog2(4'bx)!==32'bx)$fatal(1,"clog2 XZ");
 count<=$countones(wide);wide=0;#1;
 if(count!=3)$fatal(1,"NBA capture");
 #($clog2(9)) saved=$countones(130'b1<<129);
 assert(saved==1)else $fatal(1,"delayed functions");
 $display("TRACE effects %0d %0d %0d %0t",index,count,saved,$time);
end
endmodule
