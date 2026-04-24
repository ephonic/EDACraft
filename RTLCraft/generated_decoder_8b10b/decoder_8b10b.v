module Decoder8b10b (
    input clk_in,
    input reset_in,
    input control_in,
    input [9:0] decoder_in,
    input decoder_valid_in,
    output [7:0] decoder_out,
    output decoder_valid_out,
    output control_out
);

    logic [7:0] control_dec;
    logic [7:0] data_dec;
    logic [4:0] data5;
    logic [2:0] data3;
    reg [9:0] r_data;
    reg r_ctrl;
    reg r_valid;
    reg [7:0] decoder_out_reg;
    reg decoder_valid_out_reg;
    reg control_out_reg;

    assign decoder_out = decoder_out_reg;
    assign decoder_valid_out = decoder_valid_out_reg;
    assign control_out = control_out_reg;

    always @(*) begin
        case (r_data)
            8'd244: begin
                control_dec = 5'd28;
            end
            10'd779: begin
                control_dec = 5'd28;
            end
            8'd249: begin
                control_dec = 6'd60;
            end
            10'd774: begin
                control_dec = 6'd60;
            end
            8'd245: begin
                control_dec = 7'd92;
            end
            10'd778: begin
                control_dec = 7'd92;
            end
            8'd243: begin
                control_dec = 7'd124;
            end
            10'd780: begin
                control_dec = 7'd124;
            end
            8'd242: begin
                control_dec = 8'd156;
            end
            10'd781: begin
                control_dec = 8'd156;
            end
            8'd250: begin
                control_dec = 8'd188;
            end
            10'd773: begin
                control_dec = 8'd188;
            end
            8'd246: begin
                control_dec = 8'd220;
            end
            10'd777: begin
                control_dec = 8'd220;
            end
            8'd248: begin
                control_dec = 8'd252;
            end
            10'd775: begin
                control_dec = 8'd252;
            end
            10'd936: begin
                control_dec = 8'd247;
            end
            7'd87: begin
                control_dec = 8'd247;
            end
            10'd872: begin
                control_dec = 8'd251;
            end
            8'd151: begin
                control_dec = 8'd251;
            end
            10'd744: begin
                control_dec = 8'd253;
            end
            9'd279: begin
                control_dec = 8'd253;
            end
            9'd488: begin
                control_dec = 8'd254;
            end
            10'd535: begin
                control_dec = 8'd254;
            end
            default: begin
                control_dec = 1'd0;
            end
        endcase
    end

    always @(*) begin
        case (r_data[9:4])
            6'd39: begin
                data5 = 1'd0;
            end
            5'd24: begin
                data5 = 1'd0;
            end
            5'd29: begin
                data5 = 1'd1;
            end
            6'd34: begin
                data5 = 1'd1;
            end
            6'd45: begin
                data5 = 2'd2;
            end
            5'd18: begin
                data5 = 2'd2;
            end
            6'd49: begin
                data5 = 2'd3;
            end
            6'd53: begin
                data5 = 3'd4;
            end
            4'd10: begin
                data5 = 3'd4;
            end
            6'd41: begin
                data5 = 3'd5;
            end
            5'd25: begin
                data5 = 3'd6;
            end
            6'd56: begin
                data5 = 3'd7;
            end
            3'd7: begin
                data5 = 3'd7;
            end
            6'd57: begin
                data5 = 4'd8;
            end
            3'd6: begin
                data5 = 4'd8;
            end
            6'd37: begin
                data5 = 4'd9;
            end
            5'd21: begin
                data5 = 4'd10;
            end
            6'd52: begin
                data5 = 4'd11;
            end
            4'd13: begin
                data5 = 4'd12;
            end
            6'd44: begin
                data5 = 4'd13;
            end
            5'd28: begin
                data5 = 4'd14;
            end
            5'd23: begin
                data5 = 4'd15;
            end
            6'd40: begin
                data5 = 4'd15;
            end
            5'd27: begin
                data5 = 5'd16;
            end
            6'd36: begin
                data5 = 5'd16;
            end
            6'd35: begin
                data5 = 5'd17;
            end
            5'd19: begin
                data5 = 5'd18;
            end
            6'd50: begin
                data5 = 5'd19;
            end
            4'd11: begin
                data5 = 5'd20;
            end
            6'd42: begin
                data5 = 5'd21;
            end
            5'd26: begin
                data5 = 5'd22;
            end
            6'd58: begin
                data5 = 5'd23;
            end
            3'd5: begin
                data5 = 5'd23;
            end
            6'd51: begin
                data5 = 5'd24;
            end
            4'd12: begin
                data5 = 5'd24;
            end
            6'd38: begin
                data5 = 5'd25;
            end
            5'd22: begin
                data5 = 5'd26;
            end
            6'd54: begin
                data5 = 5'd27;
            end
            4'd9: begin
                data5 = 5'd27;
            end
            4'd14: begin
                data5 = 5'd28;
            end
            6'd46: begin
                data5 = 5'd29;
            end
            5'd17: begin
                data5 = 5'd29;
            end
            5'd30: begin
                data5 = 5'd30;
            end
            6'd33: begin
                data5 = 5'd30;
            end
            6'd43: begin
                data5 = 5'd31;
            end
            5'd20: begin
                data5 = 5'd31;
            end
            default: begin
                data5 = 1'd0;
            end
        endcase
        case (r_data[3:0])
            3'd4: begin
                data3 = 1'd0;
            end
            4'd11: begin
                data3 = 1'd0;
            end
            4'd9: begin
                data3 = 1'd1;
            end
            3'd5: begin
                data3 = 2'd2;
            end
            2'd3: begin
                data3 = 2'd3;
            end
            4'd12: begin
                data3 = 2'd3;
            end
            2'd2: begin
                data3 = 3'd4;
            end
            4'd13: begin
                data3 = 3'd4;
            end
            4'd10: begin
                data3 = 3'd5;
            end
            3'd6: begin
                data3 = 3'd6;
            end
            4'd14: begin
                data3 = 3'd7;
            end
            1'd1: begin
                data3 = 3'd7;
            end
            default: begin
                data3 = 1'd0;
            end
        endcase
        data_dec = {data3, data5};
    end

    always @(posedge clk_in or posedge reset_in) begin
        if ((reset_in == 1'd1)) begin
            r_data <= 1'd0;
            r_ctrl <= 1'd0;
            r_valid <= 1'd0;
            decoder_out_reg <= 1'd0;
            decoder_valid_out_reg <= 1'd0;
            control_out_reg <= 1'd0;
        end else begin
            r_data <= decoder_in;
            r_ctrl <= control_in;
            r_valid <= decoder_valid_in;
            decoder_valid_out_reg <= r_valid;
            control_out_reg <= r_ctrl;
            if ((r_ctrl == 1'd1)) begin
                decoder_out_reg <= control_dec;
            end else begin
                decoder_out_reg <= data_dec;
            end
        end
    end

endmodule