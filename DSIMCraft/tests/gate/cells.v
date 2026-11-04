// Independent VCS/Icarus reference for the functional Liberty library.
module AND2(input A,B,output Y); assign Y=A&B; endmodule
module INV(input A,output Y); assign Y=~A; endmodule
module XOR2(input A,B,output Y); assign Y=A^B; endmodule
// Liberty XOR precedes AND; make the intended grouping explicit in Verilog.
module COMPLEX(input A,B,C,output RESULT); assign RESULT=A&(B^C); endmodule
module HALF(input A,B,output SUM,CARRY); assign SUM=A^B; assign CARRY=A&B; endmodule
module TBUF(input A,E,output Y); assign Y=E?A:1'bz; endmodule
