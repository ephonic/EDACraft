// 16-bit ALU: covers arithmetic, logic, shift, compare operators
`timescale 1ns/1ps
module alu #(
    parameter W = 16
)(
    input  wire [3:0]  op,
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output reg  [W-1:0] result,
    output reg          zero,
    output reg          neg,
    output reg          ovf
);
    localparam OP_ADD  = 4'd0,  OP_SUB  = 4'd1,  OP_AND = 4'd2,  OP_OR  = 4'd3,
               OP_XOR  = 4'd4,  OP_SLL  = 4'd5,  OP_SRL = 4'd6,  OP_SRA = 4'd7,
               OP_SLT  = 4'd8,  OP_SLTU = 4'd9,  OP_MUL  = 4'd10, OP_DIV = 4'd11,
               OP_MOD  = 4'd12, OP_CLZ  = 4'd13, OP_MIN  = 4'd14, OP_ROL = 4'd15;

    reg [2*W-1:0] mul_r;
    reg [W-1:0] shamt;
    localparam W2 = 2*W;
    localparam W1 = W-1;

    always @* begin
        result = {W{1'b0}};
        ovf    = 1'b0;
        mul_r  = {W2{1'b0}};
        shamt  = b[$clog2(W)-1:0];
        case (op)
            OP_ADD: begin
                {ovf, result} = {a[W-1], a} + {b[W-1], b} + cin;
                ovf = (a[W-1] == b[W-1]) && (result[W-1] != a[W-1]);
            end
            OP_SUB: begin
                result = a - b - cin;
                ovf    = (a[W-1] != b[W-1]) && (result[W-1] != a[W-1]);
            end
            OP_AND: result = a & b;
            OP_OR:  result = a | b;
            OP_XOR: result = a ^ b;
            OP_SLL: result = a << shamt;
            OP_SRL: result = a >> shamt;
            OP_SRA: result = $signed(a) >>> shamt;
            OP_SLT: result = ($signed(a) < $signed(b)) ? 16'd1 : 16'd0;
            OP_SLTU: result = (a < b) ? 16'd1 : 16'd0;
            OP_MUL: begin
                mul_r = $signed(a) * $signed(b);
                result = mul_r[W-1:0];
            end
            OP_DIV: result = (b == 0) ? {W{1'b1}} : $signed(a) / $signed(b);
            OP_MOD: result = (b == 0) ? a : $signed(a) % $signed(b);
            OP_CLZ: begin
                result = W;
                for (integer k = W-1; k >= 0; k = k - 1) begin
                    if (a[k] && result == W) result = W-1-k;
                end
                if (a == {W{1'b1}}) result = 0;
            end
            OP_MIN: result = ($signed(a) < $signed(b)) ? a : b;
            OP_ROL: result = (a << shamt) | (a >> (W - shamt));
            default: result = {W{1'bX}};
        endcase
        zero = (result == {W{1'b0}});
        neg  = result[W-1];
    end
endmodule
