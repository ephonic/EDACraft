module ALU #(
    parameter WIDTH = 8
)(
    input wire [WIDTH-1:0] a,
    input wire [WIDTH-1:0] b,
    input wire [2:0] op,
    output reg [WIDTH-1:0] result
);
    always @(*) begin
        case (op)
            3'b000: result = a + b;
            3'b001: result = a - b;
            3'b010: result = a & b;
            3'b011: result = a | b;
            3'b100: result = a ^ b;
            default: result = 0;
        endcase
    end
endmodule
