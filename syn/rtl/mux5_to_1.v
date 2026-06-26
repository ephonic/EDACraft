`timescale 1ns/1ps
module mux5_to_1 (
    input IN0,IN1,IN2,IN3,IN4,
    input [3:0]Sel,
    output reg Dataout
);

//Change the Opcode for LUT Configuration Instruction and IDLE Instruction
always @(*) begin
    case(Sel) 
        4'b0011:    Dataout = IN0;
        4'b0001:    Dataout = IN1;
        4'b0010:    Dataout = IN2;
        4'b0000:    Dataout = IN3;
        4'b0100:    Dataout = IN4;  
        default:    Dataout = IN4;
    endcase
end

endmodule //mux5_to_1

//    if(pc_addr == 9'b0 && Sel == 4'b0011)
//        begin
//            Dataout = 1'b0;        //must be 0 instead of 1
//        end 
//    else
//        begin
//        end