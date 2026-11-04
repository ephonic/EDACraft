`timescale 1ps/1ps
module S(input A,output Z);assign Z=A;specify(A=>Z)=0;endspecify endmodule
`timescale 1ps/1ps
module D(input A,output Z);assign Z=A;specify(A=>Z)=5;endspecify endmodule
