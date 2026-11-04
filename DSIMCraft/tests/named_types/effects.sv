`timescale 1ns/1ps
module top;
typedef byte byte_t;
typedef logic signed [7:0] word_t;
typedef word_t copy_t;
typedef bit [129:0] wide_t;
word_t mem[0:1];
int count=0;
reg [63:0] a,b;
wide_t w;
reg flag;
initial begin
 a=64'(byte_t'(count++));
 b=64'(copy_t'(count++ + 127));
 flag=0 && byte_t'(count++);
 w=1 ? wide_t'(count++) : wide_t'(count++);
 if(count!==3 || a!==0 || b!==64'hffffffffffffff80 || w!==130'd2) $fatal(1,"single evaluation");
 mem[0]=copy_t'(8'hxz);mem[1]=copy_t'(0);
 mem[1]<=#2 copy_t'(count++ + 125);
 #1;mem[0]=byte_t'(mem[0]);
 if(count!==4 || mem[0]!==0) $fatal(1,"array alias conversion");
 #2;if(mem[1]!==8'h80) $fatal(1,"delayed alias NBA");
 $display("TRACE effects %0d %h %h %h %h",count,a,b,mem[0],mem[1]);$finish;
end
endmodule
