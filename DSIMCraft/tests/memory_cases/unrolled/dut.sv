// Generated from owned AST/IR; functional qualification is separate.
module batch_0 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [0:0] in_write,
  input logic [0:0] in_address,
  input logic [0:0] in_data,
  input logic [0:0] in_mask,
  input logic [0:0] in_tag,
  output logic [0:0] bank_valid,
  input logic [0:0] bank_ready,
  output logic [0:0] bank_lane,
  output logic [0:0] bank_write,
  output logic [0:0] bank_address,
  output logic [0:0] bank_data,
  output logic [0:0] bank_mask,
  input logic [0:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [0:0] out_data,
  output logic [0:0] out_tag
);
  logic [0:0] busy;
  logic [0:0] pending;
  logic [0:0] response_valid;
  logic [0:0] saved_write;
  logic [0:0] saved_address;
  logic [0:0] saved_data;
  logic [0:0] saved_mask;
  logic [0:0] saved_tag;
  logic [0:0] result_data;
  wire [0:0] active;
  assign active = (rst_n && (busy && (!response_valid)));
  assign in_ready = (rst_n && (!busy));
  assign out_valid = (rst_n && response_valid);
  assign out_tag = saved_tag;
  assign out_data = result_data;
  wire [0:0] grant_0_0;
  assign grant_0_0 = (active && ((pending[0:0] && (1'd0 == 1'd0)) && (!1'd0)));
  assign bank_valid = {(1'd0 || grant_0_0)};
  assign bank_lane = {(grant_0_0 ? 1'd0 : 1'd0)};
  assign bank_write = {(grant_0_0 ? saved_write[0:0] : 1'd0)};
  assign bank_address = {(grant_0_0 ? saved_address[0:0] : 1'd0)};
  assign bank_data = {(grant_0_0 ? saved_data[0:0] : 1'd0)};
  assign bank_mask = {(grant_0_0 ? saved_mask[0:0] : 1'd0)};
  wire [0:0] fire_0;
  assign fire_0 = (1'd0 || (grant_0_0 && bank_ready[0:0]));
  wire [0:0] fired;
  assign fired = {fire_0};
  wire [0:0] remaining;
  assign remaining = (pending & (~fired));
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          busy <= 1'd0;
          pending <= 1'd0;
          response_valid <= 1'd0;
          saved_write <= 1'd0;
          saved_address <= 1'd0;
          saved_data <= 1'd0;
          saved_mask <= 1'd0;
          saved_tag <= 1'd0;
          result_data <= 1'd0;
        end
      else
        begin
          if ((out_valid && out_ready))
            begin
              busy <= 1'd0;
              response_valid <= 1'd0;
            end
          if (active)
            begin
              pending <= remaining;
              if ((remaining == 1'd0))
                response_valid <= 1'd1;
              if (fire_0)
                result_data[0:0] <= (saved_write[0:0] ? 1'd0 : (grant_0_0 ? bank_rdata[0:0] : 1'd0));
            end
          if ((in_valid && in_ready))
            begin
              busy <= 1'd1;
              pending <= 1'd1;
              response_valid <= 1'd0;
              result_data <= 1'd0;
              saved_write <= in_write;
              saved_address <= in_address;
              saved_data <= in_data;
              saved_mask <= in_mask;
              saved_tag <= in_tag;
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_1 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [3:0] in_write,
  input logic [15:0] in_address,
  input logic [31:0] in_data,
  input logic [31:0] in_mask,
  input logic [2:0] in_tag,
  output logic [1:0] bank_valid,
  input logic [1:0] bank_ready,
  output logic [3:0] bank_lane,
  output logic [1:0] bank_write,
  output logic [5:0] bank_address,
  output logic [15:0] bank_data,
  output logic [15:0] bank_mask,
  input logic [15:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [31:0] out_data,
  output logic [2:0] out_tag
);
  logic [0:0] busy;
  logic [3:0] pending;
  logic [0:0] response_valid;
  logic [3:0] saved_write;
  logic [15:0] saved_address;
  logic [31:0] saved_data;
  logic [31:0] saved_mask;
  logic [2:0] saved_tag;
  logic [31:0] result_data;
  wire [0:0] active;
  assign active = (rst_n && (busy && (!response_valid)));
  assign in_ready = (rst_n && (!busy));
  assign out_valid = (rst_n && response_valid);
  assign out_tag = saved_tag;
  assign out_data = result_data;
  wire [0:0] grant_0_0;
  assign grant_0_0 = (active && ((pending[0:0] && (saved_address[0:0] == 1'd0)) && (!1'd0)));
  wire [0:0] grant_0_1;
  assign grant_0_1 = (active && ((pending[1:1] && (saved_address[4:4] == 1'd0)) && (!(1'd0 || (pending[0:0] && (saved_address[0:0] == 1'd0))))));
  wire [0:0] grant_0_2;
  assign grant_0_2 = (active && ((pending[2:2] && (saved_address[8:8] == 1'd0)) && (!((1'd0 || (pending[0:0] && (saved_address[0:0] == 1'd0))) || (pending[1:1] && (saved_address[4:4] == 1'd0))))));
  wire [0:0] grant_0_3;
  assign grant_0_3 = (active && ((pending[3:3] && (saved_address[12:12] == 1'd0)) && (!(((1'd0 || (pending[0:0] && (saved_address[0:0] == 1'd0))) || (pending[1:1] && (saved_address[4:4] == 1'd0))) || (pending[2:2] && (saved_address[8:8] == 1'd0))))));
  wire [0:0] grant_1_0;
  assign grant_1_0 = (active && ((pending[0:0] && (saved_address[0:0] == 1'd1)) && (!1'd0)));
  wire [0:0] grant_1_1;
  assign grant_1_1 = (active && ((pending[1:1] && (saved_address[4:4] == 1'd1)) && (!(1'd0 || (pending[0:0] && (saved_address[0:0] == 1'd1))))));
  wire [0:0] grant_1_2;
  assign grant_1_2 = (active && ((pending[2:2] && (saved_address[8:8] == 1'd1)) && (!((1'd0 || (pending[0:0] && (saved_address[0:0] == 1'd1))) || (pending[1:1] && (saved_address[4:4] == 1'd1))))));
  wire [0:0] grant_1_3;
  assign grant_1_3 = (active && ((pending[3:3] && (saved_address[12:12] == 1'd1)) && (!(((1'd0 || (pending[0:0] && (saved_address[0:0] == 1'd1))) || (pending[1:1] && (saved_address[4:4] == 1'd1))) || (pending[2:2] && (saved_address[8:8] == 1'd1))))));
  assign bank_valid = {((((1'd0 || grant_1_0) || grant_1_1) || grant_1_2) || grant_1_3), ((((1'd0 || grant_0_0) || grant_0_1) || grant_0_2) || grant_0_3)};
  assign bank_lane = {(grant_1_0 ? 2'd0 : (grant_1_1 ? 2'd1 : (grant_1_2 ? 2'd2 : (grant_1_3 ? 2'd3 : 2'd0)))), (grant_0_0 ? 2'd0 : (grant_0_1 ? 2'd1 : (grant_0_2 ? 2'd2 : (grant_0_3 ? 2'd3 : 2'd0))))};
  assign bank_write = {(grant_1_0 ? saved_write[0:0] : (grant_1_1 ? saved_write[1:1] : (grant_1_2 ? saved_write[2:2] : (grant_1_3 ? saved_write[3:3] : 1'd0)))), (grant_0_0 ? saved_write[0:0] : (grant_0_1 ? saved_write[1:1] : (grant_0_2 ? saved_write[2:2] : (grant_0_3 ? saved_write[3:3] : 1'd0))))};
  assign bank_address = {(grant_1_0 ? saved_address[3:1] : (grant_1_1 ? saved_address[7:5] : (grant_1_2 ? saved_address[11:9] : (grant_1_3 ? saved_address[15:13] : 3'd0)))), (grant_0_0 ? saved_address[3:1] : (grant_0_1 ? saved_address[7:5] : (grant_0_2 ? saved_address[11:9] : (grant_0_3 ? saved_address[15:13] : 3'd0))))};
  assign bank_data = {(grant_1_0 ? saved_data[7:0] : (grant_1_1 ? saved_data[15:8] : (grant_1_2 ? saved_data[23:16] : (grant_1_3 ? saved_data[31:24] : 8'd0)))), (grant_0_0 ? saved_data[7:0] : (grant_0_1 ? saved_data[15:8] : (grant_0_2 ? saved_data[23:16] : (grant_0_3 ? saved_data[31:24] : 8'd0))))};
  assign bank_mask = {(grant_1_0 ? saved_mask[7:0] : (grant_1_1 ? saved_mask[15:8] : (grant_1_2 ? saved_mask[23:16] : (grant_1_3 ? saved_mask[31:24] : 8'd0)))), (grant_0_0 ? saved_mask[7:0] : (grant_0_1 ? saved_mask[15:8] : (grant_0_2 ? saved_mask[23:16] : (grant_0_3 ? saved_mask[31:24] : 8'd0))))};
  wire [0:0] fire_0;
  assign fire_0 = ((1'd0 || (grant_0_0 && bank_ready[0:0])) || (grant_1_0 && bank_ready[1:1]));
  wire [0:0] fire_1;
  assign fire_1 = ((1'd0 || (grant_0_1 && bank_ready[0:0])) || (grant_1_1 && bank_ready[1:1]));
  wire [0:0] fire_2;
  assign fire_2 = ((1'd0 || (grant_0_2 && bank_ready[0:0])) || (grant_1_2 && bank_ready[1:1]));
  wire [0:0] fire_3;
  assign fire_3 = ((1'd0 || (grant_0_3 && bank_ready[0:0])) || (grant_1_3 && bank_ready[1:1]));
  wire [3:0] fired;
  assign fired = {fire_3, fire_2, fire_1, fire_0};
  wire [3:0] remaining;
  assign remaining = (pending & (~fired));
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          busy <= 1'd0;
          pending <= 4'd0;
          response_valid <= 1'd0;
          saved_write <= 4'd0;
          saved_address <= 16'd0;
          saved_data <= 32'd0;
          saved_mask <= 32'd0;
          saved_tag <= 3'd0;
          result_data <= 32'd0;
        end
      else
        begin
          if ((out_valid && out_ready))
            begin
              busy <= 1'd0;
              response_valid <= 1'd0;
            end
          if (active)
            begin
              pending <= remaining;
              if ((remaining == 4'd0))
                response_valid <= 1'd1;
              if (fire_0)
                result_data[7:0] <= (saved_write[0:0] ? 8'd0 : (grant_0_0 ? bank_rdata[7:0] : (grant_1_0 ? bank_rdata[15:8] : 8'd0)));
              if (fire_1)
                result_data[15:8] <= (saved_write[1:1] ? 8'd0 : (grant_0_1 ? bank_rdata[7:0] : (grant_1_1 ? bank_rdata[15:8] : 8'd0)));
              if (fire_2)
                result_data[23:16] <= (saved_write[2:2] ? 8'd0 : (grant_0_2 ? bank_rdata[7:0] : (grant_1_2 ? bank_rdata[15:8] : 8'd0)));
              if (fire_3)
                result_data[31:24] <= (saved_write[3:3] ? 8'd0 : (grant_0_3 ? bank_rdata[7:0] : (grant_1_3 ? bank_rdata[15:8] : 8'd0)));
            end
          if ((in_valid && in_ready))
            begin
              busy <= 1'd1;
              pending <= 4'd15;
              response_valid <= 1'd0;
              result_data <= 32'd0;
              saved_write <= in_write;
              saved_address <= in_address;
              saved_data <= in_data;
              saved_mask <= in_mask;
              saved_tag <= in_tag;
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_2 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [2:0] in_write,
  input logic [8:0] in_address,
  input logic [14:0] in_data,
  input logic [14:0] in_mask,
  input logic [1:0] in_tag,
  output logic [3:0] bank_valid,
  input logic [3:0] bank_ready,
  output logic [7:0] bank_lane,
  output logic [3:0] bank_write,
  output logic [3:0] bank_address,
  output logic [19:0] bank_data,
  output logic [19:0] bank_mask,
  input logic [19:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [14:0] out_data,
  output logic [1:0] out_tag
);
  logic [0:0] busy;
  logic [2:0] pending;
  logic [0:0] response_valid;
  logic [2:0] saved_write;
  logic [8:0] saved_address;
  logic [14:0] saved_data;
  logic [14:0] saved_mask;
  logic [1:0] saved_tag;
  logic [14:0] result_data;
  wire [0:0] active;
  assign active = (rst_n && (busy && (!response_valid)));
  assign in_ready = (rst_n && (!busy));
  assign out_valid = (rst_n && response_valid);
  assign out_tag = saved_tag;
  assign out_data = result_data;
  wire [0:0] grant_0_0;
  assign grant_0_0 = (active && ((pending[0:0] && (saved_address[2:1] == 2'd0)) && (!1'd0)));
  wire [0:0] grant_0_1;
  assign grant_0_1 = (active && ((pending[1:1] && (saved_address[5:4] == 2'd0)) && (!(1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd0))))));
  wire [0:0] grant_0_2;
  assign grant_0_2 = (active && ((pending[2:2] && (saved_address[8:7] == 2'd0)) && (!((1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd0))) || (pending[1:1] && (saved_address[5:4] == 2'd0))))));
  wire [0:0] grant_1_0;
  assign grant_1_0 = (active && ((pending[0:0] && (saved_address[2:1] == 2'd1)) && (!1'd0)));
  wire [0:0] grant_1_1;
  assign grant_1_1 = (active && ((pending[1:1] && (saved_address[5:4] == 2'd1)) && (!(1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd1))))));
  wire [0:0] grant_1_2;
  assign grant_1_2 = (active && ((pending[2:2] && (saved_address[8:7] == 2'd1)) && (!((1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd1))) || (pending[1:1] && (saved_address[5:4] == 2'd1))))));
  wire [0:0] grant_2_0;
  assign grant_2_0 = (active && ((pending[0:0] && (saved_address[2:1] == 2'd2)) && (!1'd0)));
  wire [0:0] grant_2_1;
  assign grant_2_1 = (active && ((pending[1:1] && (saved_address[5:4] == 2'd2)) && (!(1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd2))))));
  wire [0:0] grant_2_2;
  assign grant_2_2 = (active && ((pending[2:2] && (saved_address[8:7] == 2'd2)) && (!((1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd2))) || (pending[1:1] && (saved_address[5:4] == 2'd2))))));
  wire [0:0] grant_3_0;
  assign grant_3_0 = (active && ((pending[0:0] && (saved_address[2:1] == 2'd3)) && (!1'd0)));
  wire [0:0] grant_3_1;
  assign grant_3_1 = (active && ((pending[1:1] && (saved_address[5:4] == 2'd3)) && (!(1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd3))))));
  wire [0:0] grant_3_2;
  assign grant_3_2 = (active && ((pending[2:2] && (saved_address[8:7] == 2'd3)) && (!((1'd0 || (pending[0:0] && (saved_address[2:1] == 2'd3))) || (pending[1:1] && (saved_address[5:4] == 2'd3))))));
  assign bank_valid = {(((1'd0 || grant_3_0) || grant_3_1) || grant_3_2), (((1'd0 || grant_2_0) || grant_2_1) || grant_2_2), (((1'd0 || grant_1_0) || grant_1_1) || grant_1_2), (((1'd0 || grant_0_0) || grant_0_1) || grant_0_2)};
  assign bank_lane = {(grant_3_0 ? 2'd0 : (grant_3_1 ? 2'd1 : (grant_3_2 ? 2'd2 : 2'd0))), (grant_2_0 ? 2'd0 : (grant_2_1 ? 2'd1 : (grant_2_2 ? 2'd2 : 2'd0))), (grant_1_0 ? 2'd0 : (grant_1_1 ? 2'd1 : (grant_1_2 ? 2'd2 : 2'd0))), (grant_0_0 ? 2'd0 : (grant_0_1 ? 2'd1 : (grant_0_2 ? 2'd2 : 2'd0)))};
  assign bank_write = {(grant_3_0 ? saved_write[0:0] : (grant_3_1 ? saved_write[1:1] : (grant_3_2 ? saved_write[2:2] : 1'd0))), (grant_2_0 ? saved_write[0:0] : (grant_2_1 ? saved_write[1:1] : (grant_2_2 ? saved_write[2:2] : 1'd0))), (grant_1_0 ? saved_write[0:0] : (grant_1_1 ? saved_write[1:1] : (grant_1_2 ? saved_write[2:2] : 1'd0))), (grant_0_0 ? saved_write[0:0] : (grant_0_1 ? saved_write[1:1] : (grant_0_2 ? saved_write[2:2] : 1'd0)))};
  assign bank_address = {(grant_3_0 ? saved_address[0:0] : (grant_3_1 ? saved_address[3:3] : (grant_3_2 ? saved_address[6:6] : 1'd0))), (grant_2_0 ? saved_address[0:0] : (grant_2_1 ? saved_address[3:3] : (grant_2_2 ? saved_address[6:6] : 1'd0))), (grant_1_0 ? saved_address[0:0] : (grant_1_1 ? saved_address[3:3] : (grant_1_2 ? saved_address[6:6] : 1'd0))), (grant_0_0 ? saved_address[0:0] : (grant_0_1 ? saved_address[3:3] : (grant_0_2 ? saved_address[6:6] : 1'd0)))};
  assign bank_data = {(grant_3_0 ? saved_data[4:0] : (grant_3_1 ? saved_data[9:5] : (grant_3_2 ? saved_data[14:10] : 5'd0))), (grant_2_0 ? saved_data[4:0] : (grant_2_1 ? saved_data[9:5] : (grant_2_2 ? saved_data[14:10] : 5'd0))), (grant_1_0 ? saved_data[4:0] : (grant_1_1 ? saved_data[9:5] : (grant_1_2 ? saved_data[14:10] : 5'd0))), (grant_0_0 ? saved_data[4:0] : (grant_0_1 ? saved_data[9:5] : (grant_0_2 ? saved_data[14:10] : 5'd0)))};
  assign bank_mask = {(grant_3_0 ? saved_mask[4:0] : (grant_3_1 ? saved_mask[9:5] : (grant_3_2 ? saved_mask[14:10] : 5'd0))), (grant_2_0 ? saved_mask[4:0] : (grant_2_1 ? saved_mask[9:5] : (grant_2_2 ? saved_mask[14:10] : 5'd0))), (grant_1_0 ? saved_mask[4:0] : (grant_1_1 ? saved_mask[9:5] : (grant_1_2 ? saved_mask[14:10] : 5'd0))), (grant_0_0 ? saved_mask[4:0] : (grant_0_1 ? saved_mask[9:5] : (grant_0_2 ? saved_mask[14:10] : 5'd0)))};
  wire [0:0] fire_0;
  assign fire_0 = ((((1'd0 || (grant_0_0 && bank_ready[0:0])) || (grant_1_0 && bank_ready[1:1])) || (grant_2_0 && bank_ready[2:2])) || (grant_3_0 && bank_ready[3:3]));
  wire [0:0] fire_1;
  assign fire_1 = ((((1'd0 || (grant_0_1 && bank_ready[0:0])) || (grant_1_1 && bank_ready[1:1])) || (grant_2_1 && bank_ready[2:2])) || (grant_3_1 && bank_ready[3:3]));
  wire [0:0] fire_2;
  assign fire_2 = ((((1'd0 || (grant_0_2 && bank_ready[0:0])) || (grant_1_2 && bank_ready[1:1])) || (grant_2_2 && bank_ready[2:2])) || (grant_3_2 && bank_ready[3:3]));
  wire [2:0] fired;
  assign fired = {fire_2, fire_1, fire_0};
  wire [2:0] remaining;
  assign remaining = (pending & (~fired));
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          busy <= 1'd0;
          pending <= 3'd0;
          response_valid <= 1'd0;
          saved_write <= 3'd0;
          saved_address <= 9'd0;
          saved_data <= 15'd0;
          saved_mask <= 15'd0;
          saved_tag <= 2'd0;
          result_data <= 15'd0;
        end
      else
        begin
          if ((out_valid && out_ready))
            begin
              busy <= 1'd0;
              response_valid <= 1'd0;
            end
          if (active)
            begin
              pending <= remaining;
              if ((remaining == 3'd0))
                response_valid <= 1'd1;
              if (fire_0)
                result_data[4:0] <= (saved_write[0:0] ? 5'd0 : (grant_0_0 ? bank_rdata[4:0] : (grant_1_0 ? bank_rdata[9:5] : (grant_2_0 ? bank_rdata[14:10] : (grant_3_0 ? bank_rdata[19:15] : 5'd0)))));
              if (fire_1)
                result_data[9:5] <= (saved_write[1:1] ? 5'd0 : (grant_0_1 ? bank_rdata[4:0] : (grant_1_1 ? bank_rdata[9:5] : (grant_2_1 ? bank_rdata[14:10] : (grant_3_1 ? bank_rdata[19:15] : 5'd0)))));
              if (fire_2)
                result_data[14:10] <= (saved_write[2:2] ? 5'd0 : (grant_0_2 ? bank_rdata[4:0] : (grant_1_2 ? bank_rdata[9:5] : (grant_2_2 ? bank_rdata[14:10] : (grant_3_2 ? bank_rdata[19:15] : 5'd0)))));
            end
          if ((in_valid && in_ready))
            begin
              busy <= 1'd1;
              pending <= 3'd7;
              response_valid <= 1'd0;
              result_data <= 15'd0;
              saved_write <= in_write;
              saved_address <= in_address;
              saved_data <= in_data;
              saved_mask <= in_mask;
              saved_tag <= in_tag;
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_3 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [7:0] in_write,
  input logic [63:0] in_address,
  input logic [255:0] in_data,
  input logic [255:0] in_mask,
  input logic [15:0] in_tag,
  output logic [7:0] bank_valid,
  input logic [7:0] bank_ready,
  output logic [23:0] bank_lane,
  output logic [7:0] bank_write,
  output logic [39:0] bank_address,
  output logic [255:0] bank_data,
  output logic [255:0] bank_mask,
  input logic [255:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [255:0] out_data,
  output logic [15:0] out_tag
);
  logic [0:0] busy;
  logic [7:0] pending;
  logic [0:0] response_valid;
  logic [7:0] saved_write;
  logic [63:0] saved_address;
  logic [255:0] saved_data;
  logic [255:0] saved_mask;
  logic [15:0] saved_tag;
  logic [255:0] result_data;
  wire [0:0] active;
  assign active = (rst_n && (busy && (!response_valid)));
  assign in_ready = (rst_n && (!busy));
  assign out_valid = (rst_n && response_valid);
  assign out_tag = saved_tag;
  assign out_data = result_data;
  wire [0:0] grant_0_0;
  assign grant_0_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd0)) && (!1'd0)));
  wire [0:0] grant_0_1;
  assign grant_0_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd0)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd0))))));
  wire [0:0] grant_0_2;
  assign grant_0_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd0)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd0))) || (pending[1:1] && (saved_address[15:13] == 3'd0))))));
  wire [0:0] grant_0_3;
  assign grant_0_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd0)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd0))) || (pending[1:1] && (saved_address[15:13] == 3'd0))) || (pending[2:2] && (saved_address[23:21] == 3'd0))))));
  wire [0:0] grant_0_4;
  assign grant_0_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd0)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd0))) || (pending[1:1] && (saved_address[15:13] == 3'd0))) || (pending[2:2] && (saved_address[23:21] == 3'd0))) || (pending[3:3] && (saved_address[31:29] == 3'd0))))));
  wire [0:0] grant_0_5;
  assign grant_0_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd0)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd0))) || (pending[1:1] && (saved_address[15:13] == 3'd0))) || (pending[2:2] && (saved_address[23:21] == 3'd0))) || (pending[3:3] && (saved_address[31:29] == 3'd0))) || (pending[4:4] && (saved_address[39:37] == 3'd0))))));
  wire [0:0] grant_0_6;
  assign grant_0_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd0)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd0))) || (pending[1:1] && (saved_address[15:13] == 3'd0))) || (pending[2:2] && (saved_address[23:21] == 3'd0))) || (pending[3:3] && (saved_address[31:29] == 3'd0))) || (pending[4:4] && (saved_address[39:37] == 3'd0))) || (pending[5:5] && (saved_address[47:45] == 3'd0))))));
  wire [0:0] grant_0_7;
  assign grant_0_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd0)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd0))) || (pending[1:1] && (saved_address[15:13] == 3'd0))) || (pending[2:2] && (saved_address[23:21] == 3'd0))) || (pending[3:3] && (saved_address[31:29] == 3'd0))) || (pending[4:4] && (saved_address[39:37] == 3'd0))) || (pending[5:5] && (saved_address[47:45] == 3'd0))) || (pending[6:6] && (saved_address[55:53] == 3'd0))))));
  wire [0:0] grant_1_0;
  assign grant_1_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd1)) && (!1'd0)));
  wire [0:0] grant_1_1;
  assign grant_1_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd1)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd1))))));
  wire [0:0] grant_1_2;
  assign grant_1_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd1)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd1))) || (pending[1:1] && (saved_address[15:13] == 3'd1))))));
  wire [0:0] grant_1_3;
  assign grant_1_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd1)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd1))) || (pending[1:1] && (saved_address[15:13] == 3'd1))) || (pending[2:2] && (saved_address[23:21] == 3'd1))))));
  wire [0:0] grant_1_4;
  assign grant_1_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd1)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd1))) || (pending[1:1] && (saved_address[15:13] == 3'd1))) || (pending[2:2] && (saved_address[23:21] == 3'd1))) || (pending[3:3] && (saved_address[31:29] == 3'd1))))));
  wire [0:0] grant_1_5;
  assign grant_1_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd1)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd1))) || (pending[1:1] && (saved_address[15:13] == 3'd1))) || (pending[2:2] && (saved_address[23:21] == 3'd1))) || (pending[3:3] && (saved_address[31:29] == 3'd1))) || (pending[4:4] && (saved_address[39:37] == 3'd1))))));
  wire [0:0] grant_1_6;
  assign grant_1_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd1)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd1))) || (pending[1:1] && (saved_address[15:13] == 3'd1))) || (pending[2:2] && (saved_address[23:21] == 3'd1))) || (pending[3:3] && (saved_address[31:29] == 3'd1))) || (pending[4:4] && (saved_address[39:37] == 3'd1))) || (pending[5:5] && (saved_address[47:45] == 3'd1))))));
  wire [0:0] grant_1_7;
  assign grant_1_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd1)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd1))) || (pending[1:1] && (saved_address[15:13] == 3'd1))) || (pending[2:2] && (saved_address[23:21] == 3'd1))) || (pending[3:3] && (saved_address[31:29] == 3'd1))) || (pending[4:4] && (saved_address[39:37] == 3'd1))) || (pending[5:5] && (saved_address[47:45] == 3'd1))) || (pending[6:6] && (saved_address[55:53] == 3'd1))))));
  wire [0:0] grant_2_0;
  assign grant_2_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd2)) && (!1'd0)));
  wire [0:0] grant_2_1;
  assign grant_2_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd2)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd2))))));
  wire [0:0] grant_2_2;
  assign grant_2_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd2)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd2))) || (pending[1:1] && (saved_address[15:13] == 3'd2))))));
  wire [0:0] grant_2_3;
  assign grant_2_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd2)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd2))) || (pending[1:1] && (saved_address[15:13] == 3'd2))) || (pending[2:2] && (saved_address[23:21] == 3'd2))))));
  wire [0:0] grant_2_4;
  assign grant_2_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd2)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd2))) || (pending[1:1] && (saved_address[15:13] == 3'd2))) || (pending[2:2] && (saved_address[23:21] == 3'd2))) || (pending[3:3] && (saved_address[31:29] == 3'd2))))));
  wire [0:0] grant_2_5;
  assign grant_2_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd2)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd2))) || (pending[1:1] && (saved_address[15:13] == 3'd2))) || (pending[2:2] && (saved_address[23:21] == 3'd2))) || (pending[3:3] && (saved_address[31:29] == 3'd2))) || (pending[4:4] && (saved_address[39:37] == 3'd2))))));
  wire [0:0] grant_2_6;
  assign grant_2_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd2)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd2))) || (pending[1:1] && (saved_address[15:13] == 3'd2))) || (pending[2:2] && (saved_address[23:21] == 3'd2))) || (pending[3:3] && (saved_address[31:29] == 3'd2))) || (pending[4:4] && (saved_address[39:37] == 3'd2))) || (pending[5:5] && (saved_address[47:45] == 3'd2))))));
  wire [0:0] grant_2_7;
  assign grant_2_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd2)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd2))) || (pending[1:1] && (saved_address[15:13] == 3'd2))) || (pending[2:2] && (saved_address[23:21] == 3'd2))) || (pending[3:3] && (saved_address[31:29] == 3'd2))) || (pending[4:4] && (saved_address[39:37] == 3'd2))) || (pending[5:5] && (saved_address[47:45] == 3'd2))) || (pending[6:6] && (saved_address[55:53] == 3'd2))))));
  wire [0:0] grant_3_0;
  assign grant_3_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd3)) && (!1'd0)));
  wire [0:0] grant_3_1;
  assign grant_3_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd3)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd3))))));
  wire [0:0] grant_3_2;
  assign grant_3_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd3)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd3))) || (pending[1:1] && (saved_address[15:13] == 3'd3))))));
  wire [0:0] grant_3_3;
  assign grant_3_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd3)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd3))) || (pending[1:1] && (saved_address[15:13] == 3'd3))) || (pending[2:2] && (saved_address[23:21] == 3'd3))))));
  wire [0:0] grant_3_4;
  assign grant_3_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd3)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd3))) || (pending[1:1] && (saved_address[15:13] == 3'd3))) || (pending[2:2] && (saved_address[23:21] == 3'd3))) || (pending[3:3] && (saved_address[31:29] == 3'd3))))));
  wire [0:0] grant_3_5;
  assign grant_3_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd3)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd3))) || (pending[1:1] && (saved_address[15:13] == 3'd3))) || (pending[2:2] && (saved_address[23:21] == 3'd3))) || (pending[3:3] && (saved_address[31:29] == 3'd3))) || (pending[4:4] && (saved_address[39:37] == 3'd3))))));
  wire [0:0] grant_3_6;
  assign grant_3_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd3)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd3))) || (pending[1:1] && (saved_address[15:13] == 3'd3))) || (pending[2:2] && (saved_address[23:21] == 3'd3))) || (pending[3:3] && (saved_address[31:29] == 3'd3))) || (pending[4:4] && (saved_address[39:37] == 3'd3))) || (pending[5:5] && (saved_address[47:45] == 3'd3))))));
  wire [0:0] grant_3_7;
  assign grant_3_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd3)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd3))) || (pending[1:1] && (saved_address[15:13] == 3'd3))) || (pending[2:2] && (saved_address[23:21] == 3'd3))) || (pending[3:3] && (saved_address[31:29] == 3'd3))) || (pending[4:4] && (saved_address[39:37] == 3'd3))) || (pending[5:5] && (saved_address[47:45] == 3'd3))) || (pending[6:6] && (saved_address[55:53] == 3'd3))))));
  wire [0:0] grant_4_0;
  assign grant_4_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd4)) && (!1'd0)));
  wire [0:0] grant_4_1;
  assign grant_4_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd4)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd4))))));
  wire [0:0] grant_4_2;
  assign grant_4_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd4)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd4))) || (pending[1:1] && (saved_address[15:13] == 3'd4))))));
  wire [0:0] grant_4_3;
  assign grant_4_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd4)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd4))) || (pending[1:1] && (saved_address[15:13] == 3'd4))) || (pending[2:2] && (saved_address[23:21] == 3'd4))))));
  wire [0:0] grant_4_4;
  assign grant_4_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd4)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd4))) || (pending[1:1] && (saved_address[15:13] == 3'd4))) || (pending[2:2] && (saved_address[23:21] == 3'd4))) || (pending[3:3] && (saved_address[31:29] == 3'd4))))));
  wire [0:0] grant_4_5;
  assign grant_4_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd4)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd4))) || (pending[1:1] && (saved_address[15:13] == 3'd4))) || (pending[2:2] && (saved_address[23:21] == 3'd4))) || (pending[3:3] && (saved_address[31:29] == 3'd4))) || (pending[4:4] && (saved_address[39:37] == 3'd4))))));
  wire [0:0] grant_4_6;
  assign grant_4_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd4)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd4))) || (pending[1:1] && (saved_address[15:13] == 3'd4))) || (pending[2:2] && (saved_address[23:21] == 3'd4))) || (pending[3:3] && (saved_address[31:29] == 3'd4))) || (pending[4:4] && (saved_address[39:37] == 3'd4))) || (pending[5:5] && (saved_address[47:45] == 3'd4))))));
  wire [0:0] grant_4_7;
  assign grant_4_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd4)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd4))) || (pending[1:1] && (saved_address[15:13] == 3'd4))) || (pending[2:2] && (saved_address[23:21] == 3'd4))) || (pending[3:3] && (saved_address[31:29] == 3'd4))) || (pending[4:4] && (saved_address[39:37] == 3'd4))) || (pending[5:5] && (saved_address[47:45] == 3'd4))) || (pending[6:6] && (saved_address[55:53] == 3'd4))))));
  wire [0:0] grant_5_0;
  assign grant_5_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd5)) && (!1'd0)));
  wire [0:0] grant_5_1;
  assign grant_5_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd5)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd5))))));
  wire [0:0] grant_5_2;
  assign grant_5_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd5)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd5))) || (pending[1:1] && (saved_address[15:13] == 3'd5))))));
  wire [0:0] grant_5_3;
  assign grant_5_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd5)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd5))) || (pending[1:1] && (saved_address[15:13] == 3'd5))) || (pending[2:2] && (saved_address[23:21] == 3'd5))))));
  wire [0:0] grant_5_4;
  assign grant_5_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd5)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd5))) || (pending[1:1] && (saved_address[15:13] == 3'd5))) || (pending[2:2] && (saved_address[23:21] == 3'd5))) || (pending[3:3] && (saved_address[31:29] == 3'd5))))));
  wire [0:0] grant_5_5;
  assign grant_5_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd5)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd5))) || (pending[1:1] && (saved_address[15:13] == 3'd5))) || (pending[2:2] && (saved_address[23:21] == 3'd5))) || (pending[3:3] && (saved_address[31:29] == 3'd5))) || (pending[4:4] && (saved_address[39:37] == 3'd5))))));
  wire [0:0] grant_5_6;
  assign grant_5_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd5)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd5))) || (pending[1:1] && (saved_address[15:13] == 3'd5))) || (pending[2:2] && (saved_address[23:21] == 3'd5))) || (pending[3:3] && (saved_address[31:29] == 3'd5))) || (pending[4:4] && (saved_address[39:37] == 3'd5))) || (pending[5:5] && (saved_address[47:45] == 3'd5))))));
  wire [0:0] grant_5_7;
  assign grant_5_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd5)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd5))) || (pending[1:1] && (saved_address[15:13] == 3'd5))) || (pending[2:2] && (saved_address[23:21] == 3'd5))) || (pending[3:3] && (saved_address[31:29] == 3'd5))) || (pending[4:4] && (saved_address[39:37] == 3'd5))) || (pending[5:5] && (saved_address[47:45] == 3'd5))) || (pending[6:6] && (saved_address[55:53] == 3'd5))))));
  wire [0:0] grant_6_0;
  assign grant_6_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd6)) && (!1'd0)));
  wire [0:0] grant_6_1;
  assign grant_6_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd6)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd6))))));
  wire [0:0] grant_6_2;
  assign grant_6_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd6)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd6))) || (pending[1:1] && (saved_address[15:13] == 3'd6))))));
  wire [0:0] grant_6_3;
  assign grant_6_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd6)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd6))) || (pending[1:1] && (saved_address[15:13] == 3'd6))) || (pending[2:2] && (saved_address[23:21] == 3'd6))))));
  wire [0:0] grant_6_4;
  assign grant_6_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd6)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd6))) || (pending[1:1] && (saved_address[15:13] == 3'd6))) || (pending[2:2] && (saved_address[23:21] == 3'd6))) || (pending[3:3] && (saved_address[31:29] == 3'd6))))));
  wire [0:0] grant_6_5;
  assign grant_6_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd6)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd6))) || (pending[1:1] && (saved_address[15:13] == 3'd6))) || (pending[2:2] && (saved_address[23:21] == 3'd6))) || (pending[3:3] && (saved_address[31:29] == 3'd6))) || (pending[4:4] && (saved_address[39:37] == 3'd6))))));
  wire [0:0] grant_6_6;
  assign grant_6_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd6)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd6))) || (pending[1:1] && (saved_address[15:13] == 3'd6))) || (pending[2:2] && (saved_address[23:21] == 3'd6))) || (pending[3:3] && (saved_address[31:29] == 3'd6))) || (pending[4:4] && (saved_address[39:37] == 3'd6))) || (pending[5:5] && (saved_address[47:45] == 3'd6))))));
  wire [0:0] grant_6_7;
  assign grant_6_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd6)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd6))) || (pending[1:1] && (saved_address[15:13] == 3'd6))) || (pending[2:2] && (saved_address[23:21] == 3'd6))) || (pending[3:3] && (saved_address[31:29] == 3'd6))) || (pending[4:4] && (saved_address[39:37] == 3'd6))) || (pending[5:5] && (saved_address[47:45] == 3'd6))) || (pending[6:6] && (saved_address[55:53] == 3'd6))))));
  wire [0:0] grant_7_0;
  assign grant_7_0 = (active && ((pending[0:0] && (saved_address[7:5] == 3'd7)) && (!1'd0)));
  wire [0:0] grant_7_1;
  assign grant_7_1 = (active && ((pending[1:1] && (saved_address[15:13] == 3'd7)) && (!(1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd7))))));
  wire [0:0] grant_7_2;
  assign grant_7_2 = (active && ((pending[2:2] && (saved_address[23:21] == 3'd7)) && (!((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd7))) || (pending[1:1] && (saved_address[15:13] == 3'd7))))));
  wire [0:0] grant_7_3;
  assign grant_7_3 = (active && ((pending[3:3] && (saved_address[31:29] == 3'd7)) && (!(((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd7))) || (pending[1:1] && (saved_address[15:13] == 3'd7))) || (pending[2:2] && (saved_address[23:21] == 3'd7))))));
  wire [0:0] grant_7_4;
  assign grant_7_4 = (active && ((pending[4:4] && (saved_address[39:37] == 3'd7)) && (!((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd7))) || (pending[1:1] && (saved_address[15:13] == 3'd7))) || (pending[2:2] && (saved_address[23:21] == 3'd7))) || (pending[3:3] && (saved_address[31:29] == 3'd7))))));
  wire [0:0] grant_7_5;
  assign grant_7_5 = (active && ((pending[5:5] && (saved_address[47:45] == 3'd7)) && (!(((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd7))) || (pending[1:1] && (saved_address[15:13] == 3'd7))) || (pending[2:2] && (saved_address[23:21] == 3'd7))) || (pending[3:3] && (saved_address[31:29] == 3'd7))) || (pending[4:4] && (saved_address[39:37] == 3'd7))))));
  wire [0:0] grant_7_6;
  assign grant_7_6 = (active && ((pending[6:6] && (saved_address[55:53] == 3'd7)) && (!((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd7))) || (pending[1:1] && (saved_address[15:13] == 3'd7))) || (pending[2:2] && (saved_address[23:21] == 3'd7))) || (pending[3:3] && (saved_address[31:29] == 3'd7))) || (pending[4:4] && (saved_address[39:37] == 3'd7))) || (pending[5:5] && (saved_address[47:45] == 3'd7))))));
  wire [0:0] grant_7_7;
  assign grant_7_7 = (active && ((pending[7:7] && (saved_address[63:61] == 3'd7)) && (!(((((((1'd0 || (pending[0:0] && (saved_address[7:5] == 3'd7))) || (pending[1:1] && (saved_address[15:13] == 3'd7))) || (pending[2:2] && (saved_address[23:21] == 3'd7))) || (pending[3:3] && (saved_address[31:29] == 3'd7))) || (pending[4:4] && (saved_address[39:37] == 3'd7))) || (pending[5:5] && (saved_address[47:45] == 3'd7))) || (pending[6:6] && (saved_address[55:53] == 3'd7))))));
  assign bank_valid = {((((((((1'd0 || grant_7_0) || grant_7_1) || grant_7_2) || grant_7_3) || grant_7_4) || grant_7_5) || grant_7_6) || grant_7_7), ((((((((1'd0 || grant_6_0) || grant_6_1) || grant_6_2) || grant_6_3) || grant_6_4) || grant_6_5) || grant_6_6) || grant_6_7), ((((((((1'd0 || grant_5_0) || grant_5_1) || grant_5_2) || grant_5_3) || grant_5_4) || grant_5_5) || grant_5_6) || grant_5_7), ((((((((1'd0 || grant_4_0) || grant_4_1) || grant_4_2) || grant_4_3) || grant_4_4) || grant_4_5) || grant_4_6) || grant_4_7), ((((((((1'd0 || grant_3_0) || grant_3_1) || grant_3_2) || grant_3_3) || grant_3_4) || grant_3_5) || grant_3_6) || grant_3_7), ((((((((1'd0 || grant_2_0) || grant_2_1) || grant_2_2) || grant_2_3) || grant_2_4) || grant_2_5) || grant_2_6) || grant_2_7), ((((((((1'd0 || grant_1_0) || grant_1_1) || grant_1_2) || grant_1_3) || grant_1_4) || grant_1_5) || grant_1_6) || grant_1_7), ((((((((1'd0 || grant_0_0) || grant_0_1) || grant_0_2) || grant_0_3) || grant_0_4) || grant_0_5) || grant_0_6) || grant_0_7)};
  assign bank_lane = {(grant_7_0 ? 3'd0 : (grant_7_1 ? 3'd1 : (grant_7_2 ? 3'd2 : (grant_7_3 ? 3'd3 : (grant_7_4 ? 3'd4 : (grant_7_5 ? 3'd5 : (grant_7_6 ? 3'd6 : (grant_7_7 ? 3'd7 : 3'd0)))))))), (grant_6_0 ? 3'd0 : (grant_6_1 ? 3'd1 : (grant_6_2 ? 3'd2 : (grant_6_3 ? 3'd3 : (grant_6_4 ? 3'd4 : (grant_6_5 ? 3'd5 : (grant_6_6 ? 3'd6 : (grant_6_7 ? 3'd7 : 3'd0)))))))), (grant_5_0 ? 3'd0 : (grant_5_1 ? 3'd1 : (grant_5_2 ? 3'd2 : (grant_5_3 ? 3'd3 : (grant_5_4 ? 3'd4 : (grant_5_5 ? 3'd5 : (grant_5_6 ? 3'd6 : (grant_5_7 ? 3'd7 : 3'd0)))))))), (grant_4_0 ? 3'd0 : (grant_4_1 ? 3'd1 : (grant_4_2 ? 3'd2 : (grant_4_3 ? 3'd3 : (grant_4_4 ? 3'd4 : (grant_4_5 ? 3'd5 : (grant_4_6 ? 3'd6 : (grant_4_7 ? 3'd7 : 3'd0)))))))), (grant_3_0 ? 3'd0 : (grant_3_1 ? 3'd1 : (grant_3_2 ? 3'd2 : (grant_3_3 ? 3'd3 : (grant_3_4 ? 3'd4 : (grant_3_5 ? 3'd5 : (grant_3_6 ? 3'd6 : (grant_3_7 ? 3'd7 : 3'd0)))))))), (grant_2_0 ? 3'd0 : (grant_2_1 ? 3'd1 : (grant_2_2 ? 3'd2 : (grant_2_3 ? 3'd3 : (grant_2_4 ? 3'd4 : (grant_2_5 ? 3'd5 : (grant_2_6 ? 3'd6 : (grant_2_7 ? 3'd7 : 3'd0)))))))), (grant_1_0 ? 3'd0 : (grant_1_1 ? 3'd1 : (grant_1_2 ? 3'd2 : (grant_1_3 ? 3'd3 : (grant_1_4 ? 3'd4 : (grant_1_5 ? 3'd5 : (grant_1_6 ? 3'd6 : (grant_1_7 ? 3'd7 : 3'd0)))))))), (grant_0_0 ? 3'd0 : (grant_0_1 ? 3'd1 : (grant_0_2 ? 3'd2 : (grant_0_3 ? 3'd3 : (grant_0_4 ? 3'd4 : (grant_0_5 ? 3'd5 : (grant_0_6 ? 3'd6 : (grant_0_7 ? 3'd7 : 3'd0))))))))};
  assign bank_write = {(grant_7_0 ? saved_write[0:0] : (grant_7_1 ? saved_write[1:1] : (grant_7_2 ? saved_write[2:2] : (grant_7_3 ? saved_write[3:3] : (grant_7_4 ? saved_write[4:4] : (grant_7_5 ? saved_write[5:5] : (grant_7_6 ? saved_write[6:6] : (grant_7_7 ? saved_write[7:7] : 1'd0)))))))), (grant_6_0 ? saved_write[0:0] : (grant_6_1 ? saved_write[1:1] : (grant_6_2 ? saved_write[2:2] : (grant_6_3 ? saved_write[3:3] : (grant_6_4 ? saved_write[4:4] : (grant_6_5 ? saved_write[5:5] : (grant_6_6 ? saved_write[6:6] : (grant_6_7 ? saved_write[7:7] : 1'd0)))))))), (grant_5_0 ? saved_write[0:0] : (grant_5_1 ? saved_write[1:1] : (grant_5_2 ? saved_write[2:2] : (grant_5_3 ? saved_write[3:3] : (grant_5_4 ? saved_write[4:4] : (grant_5_5 ? saved_write[5:5] : (grant_5_6 ? saved_write[6:6] : (grant_5_7 ? saved_write[7:7] : 1'd0)))))))), (grant_4_0 ? saved_write[0:0] : (grant_4_1 ? saved_write[1:1] : (grant_4_2 ? saved_write[2:2] : (grant_4_3 ? saved_write[3:3] : (grant_4_4 ? saved_write[4:4] : (grant_4_5 ? saved_write[5:5] : (grant_4_6 ? saved_write[6:6] : (grant_4_7 ? saved_write[7:7] : 1'd0)))))))), (grant_3_0 ? saved_write[0:0] : (grant_3_1 ? saved_write[1:1] : (grant_3_2 ? saved_write[2:2] : (grant_3_3 ? saved_write[3:3] : (grant_3_4 ? saved_write[4:4] : (grant_3_5 ? saved_write[5:5] : (grant_3_6 ? saved_write[6:6] : (grant_3_7 ? saved_write[7:7] : 1'd0)))))))), (grant_2_0 ? saved_write[0:0] : (grant_2_1 ? saved_write[1:1] : (grant_2_2 ? saved_write[2:2] : (grant_2_3 ? saved_write[3:3] : (grant_2_4 ? saved_write[4:4] : (grant_2_5 ? saved_write[5:5] : (grant_2_6 ? saved_write[6:6] : (grant_2_7 ? saved_write[7:7] : 1'd0)))))))), (grant_1_0 ? saved_write[0:0] : (grant_1_1 ? saved_write[1:1] : (grant_1_2 ? saved_write[2:2] : (grant_1_3 ? saved_write[3:3] : (grant_1_4 ? saved_write[4:4] : (grant_1_5 ? saved_write[5:5] : (grant_1_6 ? saved_write[6:6] : (grant_1_7 ? saved_write[7:7] : 1'd0)))))))), (grant_0_0 ? saved_write[0:0] : (grant_0_1 ? saved_write[1:1] : (grant_0_2 ? saved_write[2:2] : (grant_0_3 ? saved_write[3:3] : (grant_0_4 ? saved_write[4:4] : (grant_0_5 ? saved_write[5:5] : (grant_0_6 ? saved_write[6:6] : (grant_0_7 ? saved_write[7:7] : 1'd0))))))))};
  assign bank_address = {(grant_7_0 ? saved_address[4:0] : (grant_7_1 ? saved_address[12:8] : (grant_7_2 ? saved_address[20:16] : (grant_7_3 ? saved_address[28:24] : (grant_7_4 ? saved_address[36:32] : (grant_7_5 ? saved_address[44:40] : (grant_7_6 ? saved_address[52:48] : (grant_7_7 ? saved_address[60:56] : 5'd0)))))))), (grant_6_0 ? saved_address[4:0] : (grant_6_1 ? saved_address[12:8] : (grant_6_2 ? saved_address[20:16] : (grant_6_3 ? saved_address[28:24] : (grant_6_4 ? saved_address[36:32] : (grant_6_5 ? saved_address[44:40] : (grant_6_6 ? saved_address[52:48] : (grant_6_7 ? saved_address[60:56] : 5'd0)))))))), (grant_5_0 ? saved_address[4:0] : (grant_5_1 ? saved_address[12:8] : (grant_5_2 ? saved_address[20:16] : (grant_5_3 ? saved_address[28:24] : (grant_5_4 ? saved_address[36:32] : (grant_5_5 ? saved_address[44:40] : (grant_5_6 ? saved_address[52:48] : (grant_5_7 ? saved_address[60:56] : 5'd0)))))))), (grant_4_0 ? saved_address[4:0] : (grant_4_1 ? saved_address[12:8] : (grant_4_2 ? saved_address[20:16] : (grant_4_3 ? saved_address[28:24] : (grant_4_4 ? saved_address[36:32] : (grant_4_5 ? saved_address[44:40] : (grant_4_6 ? saved_address[52:48] : (grant_4_7 ? saved_address[60:56] : 5'd0)))))))), (grant_3_0 ? saved_address[4:0] : (grant_3_1 ? saved_address[12:8] : (grant_3_2 ? saved_address[20:16] : (grant_3_3 ? saved_address[28:24] : (grant_3_4 ? saved_address[36:32] : (grant_3_5 ? saved_address[44:40] : (grant_3_6 ? saved_address[52:48] : (grant_3_7 ? saved_address[60:56] : 5'd0)))))))), (grant_2_0 ? saved_address[4:0] : (grant_2_1 ? saved_address[12:8] : (grant_2_2 ? saved_address[20:16] : (grant_2_3 ? saved_address[28:24] : (grant_2_4 ? saved_address[36:32] : (grant_2_5 ? saved_address[44:40] : (grant_2_6 ? saved_address[52:48] : (grant_2_7 ? saved_address[60:56] : 5'd0)))))))), (grant_1_0 ? saved_address[4:0] : (grant_1_1 ? saved_address[12:8] : (grant_1_2 ? saved_address[20:16] : (grant_1_3 ? saved_address[28:24] : (grant_1_4 ? saved_address[36:32] : (grant_1_5 ? saved_address[44:40] : (grant_1_6 ? saved_address[52:48] : (grant_1_7 ? saved_address[60:56] : 5'd0)))))))), (grant_0_0 ? saved_address[4:0] : (grant_0_1 ? saved_address[12:8] : (grant_0_2 ? saved_address[20:16] : (grant_0_3 ? saved_address[28:24] : (grant_0_4 ? saved_address[36:32] : (grant_0_5 ? saved_address[44:40] : (grant_0_6 ? saved_address[52:48] : (grant_0_7 ? saved_address[60:56] : 5'd0))))))))};
  assign bank_data = {(grant_7_0 ? saved_data[31:0] : (grant_7_1 ? saved_data[63:32] : (grant_7_2 ? saved_data[95:64] : (grant_7_3 ? saved_data[127:96] : (grant_7_4 ? saved_data[159:128] : (grant_7_5 ? saved_data[191:160] : (grant_7_6 ? saved_data[223:192] : (grant_7_7 ? saved_data[255:224] : 32'd0)))))))), (grant_6_0 ? saved_data[31:0] : (grant_6_1 ? saved_data[63:32] : (grant_6_2 ? saved_data[95:64] : (grant_6_3 ? saved_data[127:96] : (grant_6_4 ? saved_data[159:128] : (grant_6_5 ? saved_data[191:160] : (grant_6_6 ? saved_data[223:192] : (grant_6_7 ? saved_data[255:224] : 32'd0)))))))), (grant_5_0 ? saved_data[31:0] : (grant_5_1 ? saved_data[63:32] : (grant_5_2 ? saved_data[95:64] : (grant_5_3 ? saved_data[127:96] : (grant_5_4 ? saved_data[159:128] : (grant_5_5 ? saved_data[191:160] : (grant_5_6 ? saved_data[223:192] : (grant_5_7 ? saved_data[255:224] : 32'd0)))))))), (grant_4_0 ? saved_data[31:0] : (grant_4_1 ? saved_data[63:32] : (grant_4_2 ? saved_data[95:64] : (grant_4_3 ? saved_data[127:96] : (grant_4_4 ? saved_data[159:128] : (grant_4_5 ? saved_data[191:160] : (grant_4_6 ? saved_data[223:192] : (grant_4_7 ? saved_data[255:224] : 32'd0)))))))), (grant_3_0 ? saved_data[31:0] : (grant_3_1 ? saved_data[63:32] : (grant_3_2 ? saved_data[95:64] : (grant_3_3 ? saved_data[127:96] : (grant_3_4 ? saved_data[159:128] : (grant_3_5 ? saved_data[191:160] : (grant_3_6 ? saved_data[223:192] : (grant_3_7 ? saved_data[255:224] : 32'd0)))))))), (grant_2_0 ? saved_data[31:0] : (grant_2_1 ? saved_data[63:32] : (grant_2_2 ? saved_data[95:64] : (grant_2_3 ? saved_data[127:96] : (grant_2_4 ? saved_data[159:128] : (grant_2_5 ? saved_data[191:160] : (grant_2_6 ? saved_data[223:192] : (grant_2_7 ? saved_data[255:224] : 32'd0)))))))), (grant_1_0 ? saved_data[31:0] : (grant_1_1 ? saved_data[63:32] : (grant_1_2 ? saved_data[95:64] : (grant_1_3 ? saved_data[127:96] : (grant_1_4 ? saved_data[159:128] : (grant_1_5 ? saved_data[191:160] : (grant_1_6 ? saved_data[223:192] : (grant_1_7 ? saved_data[255:224] : 32'd0)))))))), (grant_0_0 ? saved_data[31:0] : (grant_0_1 ? saved_data[63:32] : (grant_0_2 ? saved_data[95:64] : (grant_0_3 ? saved_data[127:96] : (grant_0_4 ? saved_data[159:128] : (grant_0_5 ? saved_data[191:160] : (grant_0_6 ? saved_data[223:192] : (grant_0_7 ? saved_data[255:224] : 32'd0))))))))};
  assign bank_mask = {(grant_7_0 ? saved_mask[31:0] : (grant_7_1 ? saved_mask[63:32] : (grant_7_2 ? saved_mask[95:64] : (grant_7_3 ? saved_mask[127:96] : (grant_7_4 ? saved_mask[159:128] : (grant_7_5 ? saved_mask[191:160] : (grant_7_6 ? saved_mask[223:192] : (grant_7_7 ? saved_mask[255:224] : 32'd0)))))))), (grant_6_0 ? saved_mask[31:0] : (grant_6_1 ? saved_mask[63:32] : (grant_6_2 ? saved_mask[95:64] : (grant_6_3 ? saved_mask[127:96] : (grant_6_4 ? saved_mask[159:128] : (grant_6_5 ? saved_mask[191:160] : (grant_6_6 ? saved_mask[223:192] : (grant_6_7 ? saved_mask[255:224] : 32'd0)))))))), (grant_5_0 ? saved_mask[31:0] : (grant_5_1 ? saved_mask[63:32] : (grant_5_2 ? saved_mask[95:64] : (grant_5_3 ? saved_mask[127:96] : (grant_5_4 ? saved_mask[159:128] : (grant_5_5 ? saved_mask[191:160] : (grant_5_6 ? saved_mask[223:192] : (grant_5_7 ? saved_mask[255:224] : 32'd0)))))))), (grant_4_0 ? saved_mask[31:0] : (grant_4_1 ? saved_mask[63:32] : (grant_4_2 ? saved_mask[95:64] : (grant_4_3 ? saved_mask[127:96] : (grant_4_4 ? saved_mask[159:128] : (grant_4_5 ? saved_mask[191:160] : (grant_4_6 ? saved_mask[223:192] : (grant_4_7 ? saved_mask[255:224] : 32'd0)))))))), (grant_3_0 ? saved_mask[31:0] : (grant_3_1 ? saved_mask[63:32] : (grant_3_2 ? saved_mask[95:64] : (grant_3_3 ? saved_mask[127:96] : (grant_3_4 ? saved_mask[159:128] : (grant_3_5 ? saved_mask[191:160] : (grant_3_6 ? saved_mask[223:192] : (grant_3_7 ? saved_mask[255:224] : 32'd0)))))))), (grant_2_0 ? saved_mask[31:0] : (grant_2_1 ? saved_mask[63:32] : (grant_2_2 ? saved_mask[95:64] : (grant_2_3 ? saved_mask[127:96] : (grant_2_4 ? saved_mask[159:128] : (grant_2_5 ? saved_mask[191:160] : (grant_2_6 ? saved_mask[223:192] : (grant_2_7 ? saved_mask[255:224] : 32'd0)))))))), (grant_1_0 ? saved_mask[31:0] : (grant_1_1 ? saved_mask[63:32] : (grant_1_2 ? saved_mask[95:64] : (grant_1_3 ? saved_mask[127:96] : (grant_1_4 ? saved_mask[159:128] : (grant_1_5 ? saved_mask[191:160] : (grant_1_6 ? saved_mask[223:192] : (grant_1_7 ? saved_mask[255:224] : 32'd0)))))))), (grant_0_0 ? saved_mask[31:0] : (grant_0_1 ? saved_mask[63:32] : (grant_0_2 ? saved_mask[95:64] : (grant_0_3 ? saved_mask[127:96] : (grant_0_4 ? saved_mask[159:128] : (grant_0_5 ? saved_mask[191:160] : (grant_0_6 ? saved_mask[223:192] : (grant_0_7 ? saved_mask[255:224] : 32'd0))))))))};
  wire [0:0] fire_0;
  assign fire_0 = ((((((((1'd0 || (grant_0_0 && bank_ready[0:0])) || (grant_1_0 && bank_ready[1:1])) || (grant_2_0 && bank_ready[2:2])) || (grant_3_0 && bank_ready[3:3])) || (grant_4_0 && bank_ready[4:4])) || (grant_5_0 && bank_ready[5:5])) || (grant_6_0 && bank_ready[6:6])) || (grant_7_0 && bank_ready[7:7]));
  wire [0:0] fire_1;
  assign fire_1 = ((((((((1'd0 || (grant_0_1 && bank_ready[0:0])) || (grant_1_1 && bank_ready[1:1])) || (grant_2_1 && bank_ready[2:2])) || (grant_3_1 && bank_ready[3:3])) || (grant_4_1 && bank_ready[4:4])) || (grant_5_1 && bank_ready[5:5])) || (grant_6_1 && bank_ready[6:6])) || (grant_7_1 && bank_ready[7:7]));
  wire [0:0] fire_2;
  assign fire_2 = ((((((((1'd0 || (grant_0_2 && bank_ready[0:0])) || (grant_1_2 && bank_ready[1:1])) || (grant_2_2 && bank_ready[2:2])) || (grant_3_2 && bank_ready[3:3])) || (grant_4_2 && bank_ready[4:4])) || (grant_5_2 && bank_ready[5:5])) || (grant_6_2 && bank_ready[6:6])) || (grant_7_2 && bank_ready[7:7]));
  wire [0:0] fire_3;
  assign fire_3 = ((((((((1'd0 || (grant_0_3 && bank_ready[0:0])) || (grant_1_3 && bank_ready[1:1])) || (grant_2_3 && bank_ready[2:2])) || (grant_3_3 && bank_ready[3:3])) || (grant_4_3 && bank_ready[4:4])) || (grant_5_3 && bank_ready[5:5])) || (grant_6_3 && bank_ready[6:6])) || (grant_7_3 && bank_ready[7:7]));
  wire [0:0] fire_4;
  assign fire_4 = ((((((((1'd0 || (grant_0_4 && bank_ready[0:0])) || (grant_1_4 && bank_ready[1:1])) || (grant_2_4 && bank_ready[2:2])) || (grant_3_4 && bank_ready[3:3])) || (grant_4_4 && bank_ready[4:4])) || (grant_5_4 && bank_ready[5:5])) || (grant_6_4 && bank_ready[6:6])) || (grant_7_4 && bank_ready[7:7]));
  wire [0:0] fire_5;
  assign fire_5 = ((((((((1'd0 || (grant_0_5 && bank_ready[0:0])) || (grant_1_5 && bank_ready[1:1])) || (grant_2_5 && bank_ready[2:2])) || (grant_3_5 && bank_ready[3:3])) || (grant_4_5 && bank_ready[4:4])) || (grant_5_5 && bank_ready[5:5])) || (grant_6_5 && bank_ready[6:6])) || (grant_7_5 && bank_ready[7:7]));
  wire [0:0] fire_6;
  assign fire_6 = ((((((((1'd0 || (grant_0_6 && bank_ready[0:0])) || (grant_1_6 && bank_ready[1:1])) || (grant_2_6 && bank_ready[2:2])) || (grant_3_6 && bank_ready[3:3])) || (grant_4_6 && bank_ready[4:4])) || (grant_5_6 && bank_ready[5:5])) || (grant_6_6 && bank_ready[6:6])) || (grant_7_6 && bank_ready[7:7]));
  wire [0:0] fire_7;
  assign fire_7 = ((((((((1'd0 || (grant_0_7 && bank_ready[0:0])) || (grant_1_7 && bank_ready[1:1])) || (grant_2_7 && bank_ready[2:2])) || (grant_3_7 && bank_ready[3:3])) || (grant_4_7 && bank_ready[4:4])) || (grant_5_7 && bank_ready[5:5])) || (grant_6_7 && bank_ready[6:6])) || (grant_7_7 && bank_ready[7:7]));
  wire [7:0] fired;
  assign fired = {fire_7, fire_6, fire_5, fire_4, fire_3, fire_2, fire_1, fire_0};
  wire [7:0] remaining;
  assign remaining = (pending & (~fired));
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          busy <= 1'd0;
          pending <= 8'd0;
          response_valid <= 1'd0;
          saved_write <= 8'd0;
          saved_address <= 64'd0;
          saved_data <= 256'd0;
          saved_mask <= 256'd0;
          saved_tag <= 16'd0;
          result_data <= 256'd0;
        end
      else
        begin
          if ((out_valid && out_ready))
            begin
              busy <= 1'd0;
              response_valid <= 1'd0;
            end
          if (active)
            begin
              pending <= remaining;
              if ((remaining == 8'd0))
                response_valid <= 1'd1;
              if (fire_0)
                result_data[31:0] <= (saved_write[0:0] ? 32'd0 : (grant_0_0 ? bank_rdata[31:0] : (grant_1_0 ? bank_rdata[63:32] : (grant_2_0 ? bank_rdata[95:64] : (grant_3_0 ? bank_rdata[127:96] : (grant_4_0 ? bank_rdata[159:128] : (grant_5_0 ? bank_rdata[191:160] : (grant_6_0 ? bank_rdata[223:192] : (grant_7_0 ? bank_rdata[255:224] : 32'd0)))))))));
              if (fire_1)
                result_data[63:32] <= (saved_write[1:1] ? 32'd0 : (grant_0_1 ? bank_rdata[31:0] : (grant_1_1 ? bank_rdata[63:32] : (grant_2_1 ? bank_rdata[95:64] : (grant_3_1 ? bank_rdata[127:96] : (grant_4_1 ? bank_rdata[159:128] : (grant_5_1 ? bank_rdata[191:160] : (grant_6_1 ? bank_rdata[223:192] : (grant_7_1 ? bank_rdata[255:224] : 32'd0)))))))));
              if (fire_2)
                result_data[95:64] <= (saved_write[2:2] ? 32'd0 : (grant_0_2 ? bank_rdata[31:0] : (grant_1_2 ? bank_rdata[63:32] : (grant_2_2 ? bank_rdata[95:64] : (grant_3_2 ? bank_rdata[127:96] : (grant_4_2 ? bank_rdata[159:128] : (grant_5_2 ? bank_rdata[191:160] : (grant_6_2 ? bank_rdata[223:192] : (grant_7_2 ? bank_rdata[255:224] : 32'd0)))))))));
              if (fire_3)
                result_data[127:96] <= (saved_write[3:3] ? 32'd0 : (grant_0_3 ? bank_rdata[31:0] : (grant_1_3 ? bank_rdata[63:32] : (grant_2_3 ? bank_rdata[95:64] : (grant_3_3 ? bank_rdata[127:96] : (grant_4_3 ? bank_rdata[159:128] : (grant_5_3 ? bank_rdata[191:160] : (grant_6_3 ? bank_rdata[223:192] : (grant_7_3 ? bank_rdata[255:224] : 32'd0)))))))));
              if (fire_4)
                result_data[159:128] <= (saved_write[4:4] ? 32'd0 : (grant_0_4 ? bank_rdata[31:0] : (grant_1_4 ? bank_rdata[63:32] : (grant_2_4 ? bank_rdata[95:64] : (grant_3_4 ? bank_rdata[127:96] : (grant_4_4 ? bank_rdata[159:128] : (grant_5_4 ? bank_rdata[191:160] : (grant_6_4 ? bank_rdata[223:192] : (grant_7_4 ? bank_rdata[255:224] : 32'd0)))))))));
              if (fire_5)
                result_data[191:160] <= (saved_write[5:5] ? 32'd0 : (grant_0_5 ? bank_rdata[31:0] : (grant_1_5 ? bank_rdata[63:32] : (grant_2_5 ? bank_rdata[95:64] : (grant_3_5 ? bank_rdata[127:96] : (grant_4_5 ? bank_rdata[159:128] : (grant_5_5 ? bank_rdata[191:160] : (grant_6_5 ? bank_rdata[223:192] : (grant_7_5 ? bank_rdata[255:224] : 32'd0)))))))));
              if (fire_6)
                result_data[223:192] <= (saved_write[6:6] ? 32'd0 : (grant_0_6 ? bank_rdata[31:0] : (grant_1_6 ? bank_rdata[63:32] : (grant_2_6 ? bank_rdata[95:64] : (grant_3_6 ? bank_rdata[127:96] : (grant_4_6 ? bank_rdata[159:128] : (grant_5_6 ? bank_rdata[191:160] : (grant_6_6 ? bank_rdata[223:192] : (grant_7_6 ? bank_rdata[255:224] : 32'd0)))))))));
              if (fire_7)
                result_data[255:224] <= (saved_write[7:7] ? 32'd0 : (grant_0_7 ? bank_rdata[31:0] : (grant_1_7 ? bank_rdata[63:32] : (grant_2_7 ? bank_rdata[95:64] : (grant_3_7 ? bank_rdata[127:96] : (grant_4_7 ? bank_rdata[159:128] : (grant_5_7 ? bank_rdata[191:160] : (grant_6_7 ? bank_rdata[223:192] : (grant_7_7 ? bank_rdata[255:224] : 32'd0)))))))));
            end
          if ((in_valid && in_ready))
            begin
              busy <= 1'd1;
              pending <= 8'd255;
              response_valid <= 1'd0;
              result_data <= 256'd0;
              saved_write <= in_write;
              saved_address <= in_address;
              saved_data <= in_data;
              saved_mask <= in_mask;
              saved_tag <= in_tag;
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_4 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [2:0] in_write,
  input logic [8:0] in_address,
  input logic [8:0] in_data,
  input logic [8:0] in_mask,
  input logic [1:0] in_tag,
  output logic [7:0] bank_valid,
  input logic [7:0] bank_ready,
  output logic [15:0] bank_lane,
  output logic [7:0] bank_write,
  output logic [7:0] bank_address,
  output logic [23:0] bank_data,
  output logic [23:0] bank_mask,
  input logic [23:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [8:0] out_data,
  output logic [1:0] out_tag
);
  logic [0:0] busy;
  logic [2:0] pending;
  logic [0:0] response_valid;
  logic [2:0] saved_write;
  logic [8:0] saved_address;
  logic [8:0] saved_data;
  logic [8:0] saved_mask;
  logic [1:0] saved_tag;
  logic [8:0] result_data;
  wire [0:0] active;
  assign active = (rst_n && (busy && (!response_valid)));
  assign in_ready = (rst_n && (!busy));
  assign out_valid = (rst_n && response_valid);
  assign out_tag = saved_tag;
  assign out_data = result_data;
  wire [0:0] grant_0_0;
  assign grant_0_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd0)) && (!1'd0)));
  wire [0:0] grant_0_1;
  assign grant_0_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd0)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd0))))));
  wire [0:0] grant_0_2;
  assign grant_0_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd0)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd0))) || (pending[1:1] && (saved_address[5:3] == 3'd0))))));
  wire [0:0] grant_1_0;
  assign grant_1_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd1)) && (!1'd0)));
  wire [0:0] grant_1_1;
  assign grant_1_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd1)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd1))))));
  wire [0:0] grant_1_2;
  assign grant_1_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd1)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd1))) || (pending[1:1] && (saved_address[5:3] == 3'd1))))));
  wire [0:0] grant_2_0;
  assign grant_2_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd2)) && (!1'd0)));
  wire [0:0] grant_2_1;
  assign grant_2_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd2)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd2))))));
  wire [0:0] grant_2_2;
  assign grant_2_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd2)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd2))) || (pending[1:1] && (saved_address[5:3] == 3'd2))))));
  wire [0:0] grant_3_0;
  assign grant_3_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd3)) && (!1'd0)));
  wire [0:0] grant_3_1;
  assign grant_3_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd3)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd3))))));
  wire [0:0] grant_3_2;
  assign grant_3_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd3)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd3))) || (pending[1:1] && (saved_address[5:3] == 3'd3))))));
  wire [0:0] grant_4_0;
  assign grant_4_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd4)) && (!1'd0)));
  wire [0:0] grant_4_1;
  assign grant_4_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd4)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd4))))));
  wire [0:0] grant_4_2;
  assign grant_4_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd4)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd4))) || (pending[1:1] && (saved_address[5:3] == 3'd4))))));
  wire [0:0] grant_5_0;
  assign grant_5_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd5)) && (!1'd0)));
  wire [0:0] grant_5_1;
  assign grant_5_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd5)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd5))))));
  wire [0:0] grant_5_2;
  assign grant_5_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd5)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd5))) || (pending[1:1] && (saved_address[5:3] == 3'd5))))));
  wire [0:0] grant_6_0;
  assign grant_6_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd6)) && (!1'd0)));
  wire [0:0] grant_6_1;
  assign grant_6_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd6)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd6))))));
  wire [0:0] grant_6_2;
  assign grant_6_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd6)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd6))) || (pending[1:1] && (saved_address[5:3] == 3'd6))))));
  wire [0:0] grant_7_0;
  assign grant_7_0 = (active && ((pending[0:0] && (saved_address[2:0] == 3'd7)) && (!1'd0)));
  wire [0:0] grant_7_1;
  assign grant_7_1 = (active && ((pending[1:1] && (saved_address[5:3] == 3'd7)) && (!(1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd7))))));
  wire [0:0] grant_7_2;
  assign grant_7_2 = (active && ((pending[2:2] && (saved_address[8:6] == 3'd7)) && (!((1'd0 || (pending[0:0] && (saved_address[2:0] == 3'd7))) || (pending[1:1] && (saved_address[5:3] == 3'd7))))));
  assign bank_valid = {(((1'd0 || grant_7_0) || grant_7_1) || grant_7_2), (((1'd0 || grant_6_0) || grant_6_1) || grant_6_2), (((1'd0 || grant_5_0) || grant_5_1) || grant_5_2), (((1'd0 || grant_4_0) || grant_4_1) || grant_4_2), (((1'd0 || grant_3_0) || grant_3_1) || grant_3_2), (((1'd0 || grant_2_0) || grant_2_1) || grant_2_2), (((1'd0 || grant_1_0) || grant_1_1) || grant_1_2), (((1'd0 || grant_0_0) || grant_0_1) || grant_0_2)};
  assign bank_lane = {(grant_7_0 ? 2'd0 : (grant_7_1 ? 2'd1 : (grant_7_2 ? 2'd2 : 2'd0))), (grant_6_0 ? 2'd0 : (grant_6_1 ? 2'd1 : (grant_6_2 ? 2'd2 : 2'd0))), (grant_5_0 ? 2'd0 : (grant_5_1 ? 2'd1 : (grant_5_2 ? 2'd2 : 2'd0))), (grant_4_0 ? 2'd0 : (grant_4_1 ? 2'd1 : (grant_4_2 ? 2'd2 : 2'd0))), (grant_3_0 ? 2'd0 : (grant_3_1 ? 2'd1 : (grant_3_2 ? 2'd2 : 2'd0))), (grant_2_0 ? 2'd0 : (grant_2_1 ? 2'd1 : (grant_2_2 ? 2'd2 : 2'd0))), (grant_1_0 ? 2'd0 : (grant_1_1 ? 2'd1 : (grant_1_2 ? 2'd2 : 2'd0))), (grant_0_0 ? 2'd0 : (grant_0_1 ? 2'd1 : (grant_0_2 ? 2'd2 : 2'd0)))};
  assign bank_write = {(grant_7_0 ? saved_write[0:0] : (grant_7_1 ? saved_write[1:1] : (grant_7_2 ? saved_write[2:2] : 1'd0))), (grant_6_0 ? saved_write[0:0] : (grant_6_1 ? saved_write[1:1] : (grant_6_2 ? saved_write[2:2] : 1'd0))), (grant_5_0 ? saved_write[0:0] : (grant_5_1 ? saved_write[1:1] : (grant_5_2 ? saved_write[2:2] : 1'd0))), (grant_4_0 ? saved_write[0:0] : (grant_4_1 ? saved_write[1:1] : (grant_4_2 ? saved_write[2:2] : 1'd0))), (grant_3_0 ? saved_write[0:0] : (grant_3_1 ? saved_write[1:1] : (grant_3_2 ? saved_write[2:2] : 1'd0))), (grant_2_0 ? saved_write[0:0] : (grant_2_1 ? saved_write[1:1] : (grant_2_2 ? saved_write[2:2] : 1'd0))), (grant_1_0 ? saved_write[0:0] : (grant_1_1 ? saved_write[1:1] : (grant_1_2 ? saved_write[2:2] : 1'd0))), (grant_0_0 ? saved_write[0:0] : (grant_0_1 ? saved_write[1:1] : (grant_0_2 ? saved_write[2:2] : 1'd0)))};
  assign bank_address = {(grant_7_0 ? 1'd0 : (grant_7_1 ? 1'd0 : (grant_7_2 ? 1'd0 : 1'd0))), (grant_6_0 ? 1'd0 : (grant_6_1 ? 1'd0 : (grant_6_2 ? 1'd0 : 1'd0))), (grant_5_0 ? 1'd0 : (grant_5_1 ? 1'd0 : (grant_5_2 ? 1'd0 : 1'd0))), (grant_4_0 ? 1'd0 : (grant_4_1 ? 1'd0 : (grant_4_2 ? 1'd0 : 1'd0))), (grant_3_0 ? 1'd0 : (grant_3_1 ? 1'd0 : (grant_3_2 ? 1'd0 : 1'd0))), (grant_2_0 ? 1'd0 : (grant_2_1 ? 1'd0 : (grant_2_2 ? 1'd0 : 1'd0))), (grant_1_0 ? 1'd0 : (grant_1_1 ? 1'd0 : (grant_1_2 ? 1'd0 : 1'd0))), (grant_0_0 ? 1'd0 : (grant_0_1 ? 1'd0 : (grant_0_2 ? 1'd0 : 1'd0)))};
  assign bank_data = {(grant_7_0 ? saved_data[2:0] : (grant_7_1 ? saved_data[5:3] : (grant_7_2 ? saved_data[8:6] : 3'd0))), (grant_6_0 ? saved_data[2:0] : (grant_6_1 ? saved_data[5:3] : (grant_6_2 ? saved_data[8:6] : 3'd0))), (grant_5_0 ? saved_data[2:0] : (grant_5_1 ? saved_data[5:3] : (grant_5_2 ? saved_data[8:6] : 3'd0))), (grant_4_0 ? saved_data[2:0] : (grant_4_1 ? saved_data[5:3] : (grant_4_2 ? saved_data[8:6] : 3'd0))), (grant_3_0 ? saved_data[2:0] : (grant_3_1 ? saved_data[5:3] : (grant_3_2 ? saved_data[8:6] : 3'd0))), (grant_2_0 ? saved_data[2:0] : (grant_2_1 ? saved_data[5:3] : (grant_2_2 ? saved_data[8:6] : 3'd0))), (grant_1_0 ? saved_data[2:0] : (grant_1_1 ? saved_data[5:3] : (grant_1_2 ? saved_data[8:6] : 3'd0))), (grant_0_0 ? saved_data[2:0] : (grant_0_1 ? saved_data[5:3] : (grant_0_2 ? saved_data[8:6] : 3'd0)))};
  assign bank_mask = {(grant_7_0 ? saved_mask[2:0] : (grant_7_1 ? saved_mask[5:3] : (grant_7_2 ? saved_mask[8:6] : 3'd0))), (grant_6_0 ? saved_mask[2:0] : (grant_6_1 ? saved_mask[5:3] : (grant_6_2 ? saved_mask[8:6] : 3'd0))), (grant_5_0 ? saved_mask[2:0] : (grant_5_1 ? saved_mask[5:3] : (grant_5_2 ? saved_mask[8:6] : 3'd0))), (grant_4_0 ? saved_mask[2:0] : (grant_4_1 ? saved_mask[5:3] : (grant_4_2 ? saved_mask[8:6] : 3'd0))), (grant_3_0 ? saved_mask[2:0] : (grant_3_1 ? saved_mask[5:3] : (grant_3_2 ? saved_mask[8:6] : 3'd0))), (grant_2_0 ? saved_mask[2:0] : (grant_2_1 ? saved_mask[5:3] : (grant_2_2 ? saved_mask[8:6] : 3'd0))), (grant_1_0 ? saved_mask[2:0] : (grant_1_1 ? saved_mask[5:3] : (grant_1_2 ? saved_mask[8:6] : 3'd0))), (grant_0_0 ? saved_mask[2:0] : (grant_0_1 ? saved_mask[5:3] : (grant_0_2 ? saved_mask[8:6] : 3'd0)))};
  wire [0:0] fire_0;
  assign fire_0 = ((((((((1'd0 || (grant_0_0 && bank_ready[0:0])) || (grant_1_0 && bank_ready[1:1])) || (grant_2_0 && bank_ready[2:2])) || (grant_3_0 && bank_ready[3:3])) || (grant_4_0 && bank_ready[4:4])) || (grant_5_0 && bank_ready[5:5])) || (grant_6_0 && bank_ready[6:6])) || (grant_7_0 && bank_ready[7:7]));
  wire [0:0] fire_1;
  assign fire_1 = ((((((((1'd0 || (grant_0_1 && bank_ready[0:0])) || (grant_1_1 && bank_ready[1:1])) || (grant_2_1 && bank_ready[2:2])) || (grant_3_1 && bank_ready[3:3])) || (grant_4_1 && bank_ready[4:4])) || (grant_5_1 && bank_ready[5:5])) || (grant_6_1 && bank_ready[6:6])) || (grant_7_1 && bank_ready[7:7]));
  wire [0:0] fire_2;
  assign fire_2 = ((((((((1'd0 || (grant_0_2 && bank_ready[0:0])) || (grant_1_2 && bank_ready[1:1])) || (grant_2_2 && bank_ready[2:2])) || (grant_3_2 && bank_ready[3:3])) || (grant_4_2 && bank_ready[4:4])) || (grant_5_2 && bank_ready[5:5])) || (grant_6_2 && bank_ready[6:6])) || (grant_7_2 && bank_ready[7:7]));
  wire [2:0] fired;
  assign fired = {fire_2, fire_1, fire_0};
  wire [2:0] remaining;
  assign remaining = (pending & (~fired));
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          busy <= 1'd0;
          pending <= 3'd0;
          response_valid <= 1'd0;
          saved_write <= 3'd0;
          saved_address <= 9'd0;
          saved_data <= 9'd0;
          saved_mask <= 9'd0;
          saved_tag <= 2'd0;
          result_data <= 9'd0;
        end
      else
        begin
          if ((out_valid && out_ready))
            begin
              busy <= 1'd0;
              response_valid <= 1'd0;
            end
          if (active)
            begin
              pending <= remaining;
              if ((remaining == 3'd0))
                response_valid <= 1'd1;
              if (fire_0)
                result_data[2:0] <= (saved_write[0:0] ? 3'd0 : (grant_0_0 ? bank_rdata[2:0] : (grant_1_0 ? bank_rdata[5:3] : (grant_2_0 ? bank_rdata[8:6] : (grant_3_0 ? bank_rdata[11:9] : (grant_4_0 ? bank_rdata[14:12] : (grant_5_0 ? bank_rdata[17:15] : (grant_6_0 ? bank_rdata[20:18] : (grant_7_0 ? bank_rdata[23:21] : 3'd0)))))))));
              if (fire_1)
                result_data[5:3] <= (saved_write[1:1] ? 3'd0 : (grant_0_1 ? bank_rdata[2:0] : (grant_1_1 ? bank_rdata[5:3] : (grant_2_1 ? bank_rdata[8:6] : (grant_3_1 ? bank_rdata[11:9] : (grant_4_1 ? bank_rdata[14:12] : (grant_5_1 ? bank_rdata[17:15] : (grant_6_1 ? bank_rdata[20:18] : (grant_7_1 ? bank_rdata[23:21] : 3'd0)))))))));
              if (fire_2)
                result_data[8:6] <= (saved_write[2:2] ? 3'd0 : (grant_0_2 ? bank_rdata[2:0] : (grant_1_2 ? bank_rdata[5:3] : (grant_2_2 ? bank_rdata[8:6] : (grant_3_2 ? bank_rdata[11:9] : (grant_4_2 ? bank_rdata[14:12] : (grant_5_2 ? bank_rdata[17:15] : (grant_6_2 ? bank_rdata[20:18] : (grant_7_2 ? bank_rdata[23:21] : 3'd0)))))))));
            end
          if ((in_valid && in_ready))
            begin
              busy <= 1'd1;
              pending <= 3'd7;
              response_valid <= 1'd0;
              result_data <= 9'd0;
              saved_write <= in_write;
              saved_address <= in_address;
              saved_data <= in_data;
              saved_mask <= in_mask;
              saved_tag <= in_tag;
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_5 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [1:0] in_write,
  input logic [1:0] in_address,
  input logic [3:0] in_data,
  input logic [3:0] in_mask,
  input logic [0:0] in_tag,
  output logic [0:0] bank_valid,
  input logic [0:0] bank_ready,
  output logic [0:0] bank_lane,
  output logic [0:0] bank_write,
  output logic [0:0] bank_address,
  output logic [1:0] bank_data,
  output logic [1:0] bank_mask,
  input logic [1:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [3:0] out_data,
  output logic [0:0] out_tag
);
  logic [0:0] busy;
  logic [1:0] pending;
  logic [0:0] response_valid;
  logic [1:0] saved_write;
  logic [1:0] saved_address;
  logic [3:0] saved_data;
  logic [3:0] saved_mask;
  logic [0:0] saved_tag;
  logic [3:0] result_data;
  wire [0:0] active;
  assign active = (rst_n && (busy && (!response_valid)));
  assign in_ready = (rst_n && (!busy));
  assign out_valid = (rst_n && response_valid);
  assign out_tag = saved_tag;
  assign out_data = result_data;
  wire [0:0] grant_0_0;
  assign grant_0_0 = (active && ((pending[0:0] && (1'd0 == 1'd0)) && (!1'd0)));
  wire [0:0] grant_0_1;
  assign grant_0_1 = (active && ((pending[1:1] && (1'd0 == 1'd0)) && (!(1'd0 || (pending[0:0] && (1'd0 == 1'd0))))));
  assign bank_valid = {((1'd0 || grant_0_0) || grant_0_1)};
  assign bank_lane = {(grant_0_0 ? 1'd0 : (grant_0_1 ? 1'd1 : 1'd0))};
  assign bank_write = {(grant_0_0 ? saved_write[0:0] : (grant_0_1 ? saved_write[1:1] : 1'd0))};
  assign bank_address = {(grant_0_0 ? saved_address[0:0] : (grant_0_1 ? saved_address[1:1] : 1'd0))};
  assign bank_data = {(grant_0_0 ? saved_data[1:0] : (grant_0_1 ? saved_data[3:2] : 2'd0))};
  assign bank_mask = {(grant_0_0 ? saved_mask[1:0] : (grant_0_1 ? saved_mask[3:2] : 2'd0))};
  wire [0:0] fire_0;
  assign fire_0 = (1'd0 || (grant_0_0 && bank_ready[0:0]));
  wire [0:0] fire_1;
  assign fire_1 = (1'd0 || (grant_0_1 && bank_ready[0:0]));
  wire [1:0] fired;
  assign fired = {fire_1, fire_0};
  wire [1:0] remaining;
  assign remaining = (pending & (~fired));
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          busy <= 1'd0;
          pending <= 2'd0;
          response_valid <= 1'd0;
          saved_write <= 2'd0;
          saved_address <= 2'd0;
          saved_data <= 4'd0;
          saved_mask <= 4'd0;
          saved_tag <= 1'd0;
          result_data <= 4'd0;
        end
      else
        begin
          if ((out_valid && out_ready))
            begin
              busy <= 1'd0;
              response_valid <= 1'd0;
            end
          if (active)
            begin
              pending <= remaining;
              if ((remaining == 2'd0))
                response_valid <= 1'd1;
              if (fire_0)
                result_data[1:0] <= (saved_write[0:0] ? 2'd0 : (grant_0_0 ? bank_rdata[1:0] : 2'd0));
              if (fire_1)
                result_data[3:2] <= (saved_write[1:1] ? 2'd0 : (grant_0_1 ? bank_rdata[1:0] : 2'd0));
            end
          if ((in_valid && in_ready))
            begin
              busy <= 1'd1;
              pending <= 2'd3;
              response_valid <= 1'd0;
              result_data <= 4'd0;
              saved_write <= in_write;
              saved_address <= in_address;
              saved_data <= in_data;
              saved_mask <= in_mask;
              saved_tag <= in_tag;
            end
        end
    end
endmodule

