`timescale 1ns/1ps
module top;
logic scalar;logic[0:0] singleton;logic[7:3] mem[2:6];int address=2,source=3,ctl=0,count;
integer value;logic[63:0] extended;
typedef logic scalar_t;
function int width_probe(input int data);width_probe=data+1;endfunction
initial begin
 if($dimensions(width_probe(source++))!=1||$size(width_probe(source++))!=32||source!=3)$fatal(1,"unevaluated function");
 if(width_probe(0)!=1)$fatal(1,"function result");
 count=$countbits(source++,ctl++);if(count!=30||source!=4||ctl!=1)$fatal(1,"postincrement control result");
 if($dimensions(scalar)!=0||$dimensions(scalar_t)!=0||$unpacked_dimensions(scalar)!=0||$dimensions(singleton)!=1)$fatal(1,"scalar metadata");
 if($size(scalar)!==32'bx||$left(singleton[0])!==32'bx)$fatal(1,"zero dimensions");
 if($dimensions(mem[address++])!=1||address!=2)$fatal(1,"unused index");
 value=$increment(bit[0:4]);extended=value;
 if(value!=-1||extended!==64'hffffffffffffffff)$fatal(1,"negative sign");
 if($size(mem,64'h100000002)!==32'bx||$left(mem,64'hx00000002)!==32'bx)$fatal(1,"wide constant selector");
 if($countbits(4'b01xz,64'hx00000001)!=1||$countbits(4'b01xz,64'hz00000000)!=1)$fatal(1,"constant control LSB");
 $display("TRACE native scalar and wide boundary pass");
end
endmodule
