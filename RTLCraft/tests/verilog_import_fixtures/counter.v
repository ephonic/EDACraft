module Counter (
    input wire clk,
    input wire rst,
    input wire en,
    output reg [7:0] count
);
    reg [7:0] count_reg;

    always @(*) begin
        count = count_reg;
    end

    always @(posedge clk or posedge rst) begin
        if (rst)
            count_reg <= 8'd0;
        else if (en)
            count_reg <= count_reg + 8'd1;
        else
            count_reg <= count_reg;
    end
endmodule
