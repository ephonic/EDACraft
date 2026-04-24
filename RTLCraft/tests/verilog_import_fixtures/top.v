module Top #(
    parameter WIDTH = 8
)(
    input wire clk,
    input wire rst,
    input wire en,
    output wire [WIDTH-1:0] count_out,
    output wire sum,
    output wire cout
);
    wire fa_a;
    wire fa_b;
    wire fa_cin;

    Counter u_counter (
        .clk(clk),
        .rst(rst),
        .en(en),
        .count(count_out[WIDTH-1:0])
    );

    FullAdder u_fa (
        .a(fa_a),
        .b(fa_b),
        .cin(fa_cin),
        .sum(sum),
        .cout(cout)
    );
endmodule
