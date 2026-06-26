`timescale 1ns/1ps
module mux6_to_1 (
    input IN0,IN1,IN2,IN3,IN4,IN5,
    input [2:0]Sel,
    output reg Dataout
);

always @(*) begin
    case(Sel) 
        3'b000:     Dataout = IN0;
        3'b001:     Dataout = IN1;
        3'b010:     Dataout = IN2;
        3'b011:     Dataout = IN3;
        3'b100:     Dataout = IN4;  
        3'b101:     Dataout = IN5;   
        3'b110:     Dataout = 1'b0;
        3'b111:     Dataout = 1'b1;   
        default:    Dataout = 1'b0;
    endcase
end

endmodule //mux6_to_1

//    if(pc_addr == 9'b0 && Sel == 4'b0011)
//        begin
//            Dataout = 1'b0;        //must be 0 instead of 1
//        end 
//    else
//        begin
//        end