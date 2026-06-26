`timescale 1ns/1ps
module Logic_Element (
    // input network_datain,
    // input [8:0]pc_addr,
    // input [79:0]instr,
    input [15:0]LUT,
    input sel1,sel2,sel3,sel4,
    output reg LUT_out
);

always @(LUT or sel1 or sel2 or sel3 or sel4) 
begin
    LUT_out = LUT[{sel4,sel3,sel2,sel1}];
    // if(instr[8:0]==pc_addr && instr[36]==1'b1)
    //     LUT_out = LUT[{sel4,sel3,sel2,network_datain}];
    // else if(instr[17:9]==pc_addr && instr[37]==1'b1)
    //     LUT_out = LUT[{sel4,sel3,network_datain,sel1}];
    // else if(instr[26:18]==pc_addr && instr[38]==1'b1)
    //     LUT_out = LUT[{sel4,network_datain,sel2,sel1}];
    // else if(instr[35:27]==pc_addr && instr[39]==1'b1)
    //     LUT_out = LUT[{network_datain,sel3,sel2,sel1}];
    // else
    //     LUT_out = LUT[{sel4,sel3,sel2,sel1}];
end

endmodule //Logic_Element
