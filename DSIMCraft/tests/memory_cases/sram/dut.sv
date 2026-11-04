// Generated from owned AST/IR; functional qualification is separate.
module batch_sram_root_0 (
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
  output logic [0:0] bank_ready,
  output logic [0:0] bank_lane,
  output logic [0:0] bank_write,
  output logic [0:0] bank_address,
  output logic [0:0] bank_data,
  output logic [0:0] bank_mask,
  output logic [0:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [0:0] out_data,
  output logic [0:0] out_tag,
  input logic [0:0] enable,
  output logic [0:0] sram_ce,
  output logic [0:0] sram_we,
  output logic [0:0] sram_address,
  output logic [0:0] sram_wdata,
  output logic [0:0] sram_wmask,
  input logic [0:0] sram_rdata
);
  agent_memory_batch_0 scheduler(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_write(in_write), .in_address(in_address), .in_data(in_data), .in_mask(in_mask), .in_tag(in_tag), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_lane(bank_lane), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_tag(out_tag));
  agent_sram_bridge_0 adapter(.clk(clk), .rst_n(rst_n), .enable(enable), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .sram_ce(sram_ce), .sram_we(sram_we), .sram_address(sram_address), .sram_wdata(sram_wdata), .sram_wmask(sram_wmask), .sram_rdata(sram_rdata));
endmodule

module agent_memory_batch_0 (
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

module agent_sram_bridge_0 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] enable,
  input logic [0:0] bank_valid,
  output logic [0:0] bank_ready,
  input logic [0:0] bank_write,
  input logic [0:0] bank_address,
  input logic [0:0] bank_data,
  input logic [0:0] bank_mask,
  output logic [0:0] bank_rdata,
  output logic [0:0] sram_ce,
  output logic [0:0] sram_we,
  output logic [0:0] sram_address,
  output logic [0:0] sram_wdata,
  output logic [0:0] sram_wmask,
  input logic [0:0] sram_rdata
);
  logic [0:0] read_pending;
  logic [0:0] response_valid;
  logic [0:0] response_data;
  assign bank_ready = {((rst_n && enable[0:0]) && ((response_valid[0:0] && (!bank_write[0:0])) || (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_write[0:0] && (bank_address[0:0] < 2'd2)))))};
  assign sram_ce = {((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2))))};
  assign sram_we = {(((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0])};
  assign sram_address = {(((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) ? bank_address[0:0] : 1'd0)};
  assign sram_wdata = {((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0]) ? bank_data[0:0] : 1'd0)};
  assign sram_wmask = {((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0]) ? bank_mask[0:0] : 1'd0)};
  assign bank_rdata = response_data;
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          read_pending <= 1'd0;
          response_valid <= 1'd0;
          response_data <= 1'd0;
        end
      else
        begin
          if (read_pending[0:0])
            begin
              response_data[0:0] <= sram_rdata[0:0];
              read_pending[0:0] <= 1'd0;
              response_valid[0:0] <= 1'd1;
            end
          if ((response_valid[0:0] && ((!bank_write[0:0]) && (bank_valid[0:0] && enable[0:0]))))
            response_valid[0:0] <= 1'd0;
          if ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && (!bank_write[0:0])))
            read_pending[0:0] <= 1'd1;
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_sram_root_1 (
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
  output logic [1:0] bank_ready,
  output logic [3:0] bank_lane,
  output logic [1:0] bank_write,
  output logic [5:0] bank_address,
  output logic [15:0] bank_data,
  output logic [15:0] bank_mask,
  output logic [15:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [31:0] out_data,
  output logic [2:0] out_tag,
  input logic [1:0] enable,
  output logic [1:0] sram_ce,
  output logic [1:0] sram_we,
  output logic [5:0] sram_address,
  output logic [15:0] sram_wdata,
  output logic [15:0] sram_wmask,
  input logic [15:0] sram_rdata
);
  agent_memory_batch_1 scheduler(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_write(in_write), .in_address(in_address), .in_data(in_data), .in_mask(in_mask), .in_tag(in_tag), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_lane(bank_lane), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_tag(out_tag));
  agent_sram_bridge_1 adapter(.clk(clk), .rst_n(rst_n), .enable(enable), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .sram_ce(sram_ce), .sram_we(sram_we), .sram_address(sram_address), .sram_wdata(sram_wdata), .sram_wmask(sram_wmask), .sram_rdata(sram_rdata));
endmodule

module agent_memory_batch_1 (
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

module agent_sram_bridge_1 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [1:0] enable,
  input logic [1:0] bank_valid,
  output logic [1:0] bank_ready,
  input logic [1:0] bank_write,
  input logic [5:0] bank_address,
  input logic [15:0] bank_data,
  input logic [15:0] bank_mask,
  output logic [15:0] bank_rdata,
  output logic [1:0] sram_ce,
  output logic [1:0] sram_we,
  output logic [5:0] sram_address,
  output logic [15:0] sram_wdata,
  output logic [15:0] sram_wmask,
  input logic [15:0] sram_rdata
);
  logic [1:0] read_pending;
  logic [1:0] response_valid;
  logic [15:0] response_data;
  assign bank_ready = {((rst_n && enable[1:1]) && ((response_valid[1:1] && (!bank_write[1:1])) || (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_write[1:1] && (bank_address[5:3] < 4'd8))))), ((rst_n && enable[0:0]) && ((response_valid[0:0] && (!bank_write[0:0])) || (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_write[0:0] && (bank_address[2:0] < 4'd8)))))};
  assign sram_ce = {((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[5:3] < 4'd8)))), ((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[2:0] < 4'd8))))};
  assign sram_we = {(((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[5:3] < 4'd8)))) && bank_write[1:1]), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[2:0] < 4'd8)))) && bank_write[0:0])};
  assign sram_address = {(((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[5:3] < 4'd8)))) ? bank_address[5:3] : 3'd0), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[2:0] < 4'd8)))) ? bank_address[2:0] : 3'd0)};
  assign sram_wdata = {((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[5:3] < 4'd8)))) && bank_write[1:1]) ? bank_data[15:8] : 8'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[2:0] < 4'd8)))) && bank_write[0:0]) ? bank_data[7:0] : 8'd0)};
  assign sram_wmask = {((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[5:3] < 4'd8)))) && bank_write[1:1]) ? bank_mask[15:8] : 8'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[2:0] < 4'd8)))) && bank_write[0:0]) ? bank_mask[7:0] : 8'd0)};
  assign bank_rdata = response_data;
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          read_pending <= 2'd0;
          response_valid <= 2'd0;
          response_data <= 16'd0;
        end
      else
        begin
          if (read_pending[0:0])
            begin
              response_data[7:0] <= sram_rdata[7:0];
              read_pending[0:0] <= 1'd0;
              response_valid[0:0] <= 1'd1;
            end
          if ((response_valid[0:0] && ((!bank_write[0:0]) && (bank_valid[0:0] && enable[0:0]))))
            response_valid[0:0] <= 1'd0;
          if ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[2:0] < 4'd8)))) && (!bank_write[0:0])))
            read_pending[0:0] <= 1'd1;
          if (read_pending[1:1])
            begin
              response_data[15:8] <= sram_rdata[15:8];
              read_pending[1:1] <= 1'd0;
              response_valid[1:1] <= 1'd1;
            end
          if ((response_valid[1:1] && ((!bank_write[1:1]) && (bank_valid[1:1] && enable[1:1]))))
            response_valid[1:1] <= 1'd0;
          if ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[5:3] < 4'd8)))) && (!bank_write[1:1])))
            read_pending[1:1] <= 1'd1;
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_sram_root_2 (
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
  output logic [3:0] bank_ready,
  output logic [7:0] bank_lane,
  output logic [3:0] bank_write,
  output logic [3:0] bank_address,
  output logic [19:0] bank_data,
  output logic [19:0] bank_mask,
  output logic [19:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [14:0] out_data,
  output logic [1:0] out_tag,
  input logic [3:0] enable,
  output logic [3:0] sram_ce,
  output logic [3:0] sram_we,
  output logic [3:0] sram_address,
  output logic [19:0] sram_wdata,
  output logic [19:0] sram_wmask,
  input logic [19:0] sram_rdata
);
  agent_memory_batch_2 scheduler(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_write(in_write), .in_address(in_address), .in_data(in_data), .in_mask(in_mask), .in_tag(in_tag), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_lane(bank_lane), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_tag(out_tag));
  agent_sram_bridge_2 adapter(.clk(clk), .rst_n(rst_n), .enable(enable), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .sram_ce(sram_ce), .sram_we(sram_we), .sram_address(sram_address), .sram_wdata(sram_wdata), .sram_wmask(sram_wmask), .sram_rdata(sram_rdata));
endmodule

module agent_memory_batch_2 (
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

module agent_sram_bridge_2 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [3:0] enable,
  input logic [3:0] bank_valid,
  output logic [3:0] bank_ready,
  input logic [3:0] bank_write,
  input logic [3:0] bank_address,
  input logic [19:0] bank_data,
  input logic [19:0] bank_mask,
  output logic [19:0] bank_rdata,
  output logic [3:0] sram_ce,
  output logic [3:0] sram_we,
  output logic [3:0] sram_address,
  output logic [19:0] sram_wdata,
  output logic [19:0] sram_wmask,
  input logic [19:0] sram_rdata
);
  logic [3:0] read_pending;
  logic [3:0] response_valid;
  logic [19:0] response_data;
  assign bank_ready = {((rst_n && enable[3:3]) && ((response_valid[3:3] && (!bank_write[3:3])) || (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_write[3:3] && (bank_address[3:3] < 2'd2))))), ((rst_n && enable[2:2]) && ((response_valid[2:2] && (!bank_write[2:2])) || (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_write[2:2] && (bank_address[2:2] < 2'd2))))), ((rst_n && enable[1:1]) && ((response_valid[1:1] && (!bank_write[1:1])) || (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_write[1:1] && (bank_address[1:1] < 2'd2))))), ((rst_n && enable[0:0]) && ((response_valid[0:0] && (!bank_write[0:0])) || (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_write[0:0] && (bank_address[0:0] < 2'd2)))))};
  assign sram_ce = {((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd2)))), ((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd2)))), ((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd2)))), ((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2))))};
  assign sram_we = {(((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd2)))) && bank_write[3:3]), (((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd2)))) && bank_write[2:2]), (((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd2)))) && bank_write[1:1]), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0])};
  assign sram_address = {(((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd2)))) ? bank_address[3:3] : 1'd0), (((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd2)))) ? bank_address[2:2] : 1'd0), (((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd2)))) ? bank_address[1:1] : 1'd0), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) ? bank_address[0:0] : 1'd0)};
  assign sram_wdata = {((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd2)))) && bank_write[3:3]) ? bank_data[19:15] : 5'd0), ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd2)))) && bank_write[2:2]) ? bank_data[14:10] : 5'd0), ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd2)))) && bank_write[1:1]) ? bank_data[9:5] : 5'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0]) ? bank_data[4:0] : 5'd0)};
  assign sram_wmask = {((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd2)))) && bank_write[3:3]) ? bank_mask[19:15] : 5'd0), ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd2)))) && bank_write[2:2]) ? bank_mask[14:10] : 5'd0), ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd2)))) && bank_write[1:1]) ? bank_mask[9:5] : 5'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0]) ? bank_mask[4:0] : 5'd0)};
  assign bank_rdata = response_data;
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          read_pending <= 4'd0;
          response_valid <= 4'd0;
          response_data <= 20'd0;
        end
      else
        begin
          if (read_pending[0:0])
            begin
              response_data[4:0] <= sram_rdata[4:0];
              read_pending[0:0] <= 1'd0;
              response_valid[0:0] <= 1'd1;
            end
          if ((response_valid[0:0] && ((!bank_write[0:0]) && (bank_valid[0:0] && enable[0:0]))))
            response_valid[0:0] <= 1'd0;
          if ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && (!bank_write[0:0])))
            read_pending[0:0] <= 1'd1;
          if (read_pending[1:1])
            begin
              response_data[9:5] <= sram_rdata[9:5];
              read_pending[1:1] <= 1'd0;
              response_valid[1:1] <= 1'd1;
            end
          if ((response_valid[1:1] && ((!bank_write[1:1]) && (bank_valid[1:1] && enable[1:1]))))
            response_valid[1:1] <= 1'd0;
          if ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd2)))) && (!bank_write[1:1])))
            read_pending[1:1] <= 1'd1;
          if (read_pending[2:2])
            begin
              response_data[14:10] <= sram_rdata[14:10];
              read_pending[2:2] <= 1'd0;
              response_valid[2:2] <= 1'd1;
            end
          if ((response_valid[2:2] && ((!bank_write[2:2]) && (bank_valid[2:2] && enable[2:2]))))
            response_valid[2:2] <= 1'd0;
          if ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd2)))) && (!bank_write[2:2])))
            read_pending[2:2] <= 1'd1;
          if (read_pending[3:3])
            begin
              response_data[19:15] <= sram_rdata[19:15];
              read_pending[3:3] <= 1'd0;
              response_valid[3:3] <= 1'd1;
            end
          if ((response_valid[3:3] && ((!bank_write[3:3]) && (bank_valid[3:3] && enable[3:3]))))
            response_valid[3:3] <= 1'd0;
          if ((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd2)))) && (!bank_write[3:3])))
            read_pending[3:3] <= 1'd1;
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_sram_root_3 (
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
  output logic [7:0] bank_ready,
  output logic [23:0] bank_lane,
  output logic [7:0] bank_write,
  output logic [39:0] bank_address,
  output logic [255:0] bank_data,
  output logic [255:0] bank_mask,
  output logic [255:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [255:0] out_data,
  output logic [15:0] out_tag,
  input logic [7:0] enable,
  output logic [7:0] sram_ce,
  output logic [7:0] sram_we,
  output logic [39:0] sram_address,
  output logic [255:0] sram_wdata,
  output logic [255:0] sram_wmask,
  input logic [255:0] sram_rdata
);
  agent_memory_batch_3 scheduler(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_write(in_write), .in_address(in_address), .in_data(in_data), .in_mask(in_mask), .in_tag(in_tag), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_lane(bank_lane), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_tag(out_tag));
  agent_sram_bridge_3 adapter(.clk(clk), .rst_n(rst_n), .enable(enable), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .sram_ce(sram_ce), .sram_we(sram_we), .sram_address(sram_address), .sram_wdata(sram_wdata), .sram_wmask(sram_wmask), .sram_rdata(sram_rdata));
endmodule

module agent_memory_batch_3 (
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

module agent_sram_bridge_3 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [7:0] enable,
  input logic [7:0] bank_valid,
  output logic [7:0] bank_ready,
  input logic [7:0] bank_write,
  input logic [39:0] bank_address,
  input logic [255:0] bank_data,
  input logic [255:0] bank_mask,
  output logic [255:0] bank_rdata,
  output logic [7:0] sram_ce,
  output logic [7:0] sram_we,
  output logic [39:0] sram_address,
  output logic [255:0] sram_wdata,
  output logic [255:0] sram_wmask,
  input logic [255:0] sram_rdata
);
  logic [7:0] read_pending;
  logic [7:0] response_valid;
  logic [255:0] response_data;
  assign bank_ready = {((rst_n && enable[7:7]) && ((response_valid[7:7] && (!bank_write[7:7])) || (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_write[7:7] && (bank_address[39:35] < 6'd32))))), ((rst_n && enable[6:6]) && ((response_valid[6:6] && (!bank_write[6:6])) || (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_write[6:6] && (bank_address[34:30] < 6'd32))))), ((rst_n && enable[5:5]) && ((response_valid[5:5] && (!bank_write[5:5])) || (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_write[5:5] && (bank_address[29:25] < 6'd32))))), ((rst_n && enable[4:4]) && ((response_valid[4:4] && (!bank_write[4:4])) || (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_write[4:4] && (bank_address[24:20] < 6'd32))))), ((rst_n && enable[3:3]) && ((response_valid[3:3] && (!bank_write[3:3])) || (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_write[3:3] && (bank_address[19:15] < 6'd32))))), ((rst_n && enable[2:2]) && ((response_valid[2:2] && (!bank_write[2:2])) || (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_write[2:2] && (bank_address[14:10] < 6'd32))))), ((rst_n && enable[1:1]) && ((response_valid[1:1] && (!bank_write[1:1])) || (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_write[1:1] && (bank_address[9:5] < 6'd32))))), ((rst_n && enable[0:0]) && ((response_valid[0:0] && (!bank_write[0:0])) || (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_write[0:0] && (bank_address[4:0] < 6'd32)))))};
  assign sram_ce = {((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[39:35] < 6'd32)))), ((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[34:30] < 6'd32)))), ((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[29:25] < 6'd32)))), ((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[24:20] < 6'd32)))), ((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[19:15] < 6'd32)))), ((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[14:10] < 6'd32)))), ((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[9:5] < 6'd32)))), ((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[4:0] < 6'd32))))};
  assign sram_we = {(((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[39:35] < 6'd32)))) && bank_write[7:7]), (((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[34:30] < 6'd32)))) && bank_write[6:6]), (((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[29:25] < 6'd32)))) && bank_write[5:5]), (((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[24:20] < 6'd32)))) && bank_write[4:4]), (((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[19:15] < 6'd32)))) && bank_write[3:3]), (((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[14:10] < 6'd32)))) && bank_write[2:2]), (((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[9:5] < 6'd32)))) && bank_write[1:1]), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[4:0] < 6'd32)))) && bank_write[0:0])};
  assign sram_address = {(((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[39:35] < 6'd32)))) ? bank_address[39:35] : 5'd0), (((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[34:30] < 6'd32)))) ? bank_address[34:30] : 5'd0), (((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[29:25] < 6'd32)))) ? bank_address[29:25] : 5'd0), (((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[24:20] < 6'd32)))) ? bank_address[24:20] : 5'd0), (((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[19:15] < 6'd32)))) ? bank_address[19:15] : 5'd0), (((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[14:10] < 6'd32)))) ? bank_address[14:10] : 5'd0), (((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[9:5] < 6'd32)))) ? bank_address[9:5] : 5'd0), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[4:0] < 6'd32)))) ? bank_address[4:0] : 5'd0)};
  assign sram_wdata = {((((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[39:35] < 6'd32)))) && bank_write[7:7]) ? bank_data[255:224] : 32'd0), ((((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[34:30] < 6'd32)))) && bank_write[6:6]) ? bank_data[223:192] : 32'd0), ((((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[29:25] < 6'd32)))) && bank_write[5:5]) ? bank_data[191:160] : 32'd0), ((((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[24:20] < 6'd32)))) && bank_write[4:4]) ? bank_data[159:128] : 32'd0), ((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[19:15] < 6'd32)))) && bank_write[3:3]) ? bank_data[127:96] : 32'd0), ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[14:10] < 6'd32)))) && bank_write[2:2]) ? bank_data[95:64] : 32'd0), ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[9:5] < 6'd32)))) && bank_write[1:1]) ? bank_data[63:32] : 32'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[4:0] < 6'd32)))) && bank_write[0:0]) ? bank_data[31:0] : 32'd0)};
  assign sram_wmask = {((((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[39:35] < 6'd32)))) && bank_write[7:7]) ? bank_mask[255:224] : 32'd0), ((((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[34:30] < 6'd32)))) && bank_write[6:6]) ? bank_mask[223:192] : 32'd0), ((((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[29:25] < 6'd32)))) && bank_write[5:5]) ? bank_mask[191:160] : 32'd0), ((((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[24:20] < 6'd32)))) && bank_write[4:4]) ? bank_mask[159:128] : 32'd0), ((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[19:15] < 6'd32)))) && bank_write[3:3]) ? bank_mask[127:96] : 32'd0), ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[14:10] < 6'd32)))) && bank_write[2:2]) ? bank_mask[95:64] : 32'd0), ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[9:5] < 6'd32)))) && bank_write[1:1]) ? bank_mask[63:32] : 32'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[4:0] < 6'd32)))) && bank_write[0:0]) ? bank_mask[31:0] : 32'd0)};
  assign bank_rdata = response_data;
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          read_pending <= 8'd0;
          response_valid <= 8'd0;
          response_data <= 256'd0;
        end
      else
        begin
          if (read_pending[0:0])
            begin
              response_data[31:0] <= sram_rdata[31:0];
              read_pending[0:0] <= 1'd0;
              response_valid[0:0] <= 1'd1;
            end
          if ((response_valid[0:0] && ((!bank_write[0:0]) && (bank_valid[0:0] && enable[0:0]))))
            response_valid[0:0] <= 1'd0;
          if ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[4:0] < 6'd32)))) && (!bank_write[0:0])))
            read_pending[0:0] <= 1'd1;
          if (read_pending[1:1])
            begin
              response_data[63:32] <= sram_rdata[63:32];
              read_pending[1:1] <= 1'd0;
              response_valid[1:1] <= 1'd1;
            end
          if ((response_valid[1:1] && ((!bank_write[1:1]) && (bank_valid[1:1] && enable[1:1]))))
            response_valid[1:1] <= 1'd0;
          if ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[9:5] < 6'd32)))) && (!bank_write[1:1])))
            read_pending[1:1] <= 1'd1;
          if (read_pending[2:2])
            begin
              response_data[95:64] <= sram_rdata[95:64];
              read_pending[2:2] <= 1'd0;
              response_valid[2:2] <= 1'd1;
            end
          if ((response_valid[2:2] && ((!bank_write[2:2]) && (bank_valid[2:2] && enable[2:2]))))
            response_valid[2:2] <= 1'd0;
          if ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[14:10] < 6'd32)))) && (!bank_write[2:2])))
            read_pending[2:2] <= 1'd1;
          if (read_pending[3:3])
            begin
              response_data[127:96] <= sram_rdata[127:96];
              read_pending[3:3] <= 1'd0;
              response_valid[3:3] <= 1'd1;
            end
          if ((response_valid[3:3] && ((!bank_write[3:3]) && (bank_valid[3:3] && enable[3:3]))))
            response_valid[3:3] <= 1'd0;
          if ((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[19:15] < 6'd32)))) && (!bank_write[3:3])))
            read_pending[3:3] <= 1'd1;
          if (read_pending[4:4])
            begin
              response_data[159:128] <= sram_rdata[159:128];
              read_pending[4:4] <= 1'd0;
              response_valid[4:4] <= 1'd1;
            end
          if ((response_valid[4:4] && ((!bank_write[4:4]) && (bank_valid[4:4] && enable[4:4]))))
            response_valid[4:4] <= 1'd0;
          if ((((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[24:20] < 6'd32)))) && (!bank_write[4:4])))
            read_pending[4:4] <= 1'd1;
          if (read_pending[5:5])
            begin
              response_data[191:160] <= sram_rdata[191:160];
              read_pending[5:5] <= 1'd0;
              response_valid[5:5] <= 1'd1;
            end
          if ((response_valid[5:5] && ((!bank_write[5:5]) && (bank_valid[5:5] && enable[5:5]))))
            response_valid[5:5] <= 1'd0;
          if ((((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[29:25] < 6'd32)))) && (!bank_write[5:5])))
            read_pending[5:5] <= 1'd1;
          if (read_pending[6:6])
            begin
              response_data[223:192] <= sram_rdata[223:192];
              read_pending[6:6] <= 1'd0;
              response_valid[6:6] <= 1'd1;
            end
          if ((response_valid[6:6] && ((!bank_write[6:6]) && (bank_valid[6:6] && enable[6:6]))))
            response_valid[6:6] <= 1'd0;
          if ((((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[34:30] < 6'd32)))) && (!bank_write[6:6])))
            read_pending[6:6] <= 1'd1;
          if (read_pending[7:7])
            begin
              response_data[255:224] <= sram_rdata[255:224];
              read_pending[7:7] <= 1'd0;
              response_valid[7:7] <= 1'd1;
            end
          if ((response_valid[7:7] && ((!bank_write[7:7]) && (bank_valid[7:7] && enable[7:7]))))
            response_valid[7:7] <= 1'd0;
          if ((((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[39:35] < 6'd32)))) && (!bank_write[7:7])))
            read_pending[7:7] <= 1'd1;
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_sram_root_4 (
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
  output logic [7:0] bank_ready,
  output logic [15:0] bank_lane,
  output logic [7:0] bank_write,
  output logic [7:0] bank_address,
  output logic [23:0] bank_data,
  output logic [23:0] bank_mask,
  output logic [23:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [8:0] out_data,
  output logic [1:0] out_tag,
  input logic [7:0] enable,
  output logic [7:0] sram_ce,
  output logic [7:0] sram_we,
  output logic [7:0] sram_address,
  output logic [23:0] sram_wdata,
  output logic [23:0] sram_wmask,
  input logic [23:0] sram_rdata
);
  agent_memory_batch_4 scheduler(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_write(in_write), .in_address(in_address), .in_data(in_data), .in_mask(in_mask), .in_tag(in_tag), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_lane(bank_lane), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_tag(out_tag));
  agent_sram_bridge_4 adapter(.clk(clk), .rst_n(rst_n), .enable(enable), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .sram_ce(sram_ce), .sram_we(sram_we), .sram_address(sram_address), .sram_wdata(sram_wdata), .sram_wmask(sram_wmask), .sram_rdata(sram_rdata));
endmodule

module agent_memory_batch_4 (
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

module agent_sram_bridge_4 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [7:0] enable,
  input logic [7:0] bank_valid,
  output logic [7:0] bank_ready,
  input logic [7:0] bank_write,
  input logic [7:0] bank_address,
  input logic [23:0] bank_data,
  input logic [23:0] bank_mask,
  output logic [23:0] bank_rdata,
  output logic [7:0] sram_ce,
  output logic [7:0] sram_we,
  output logic [7:0] sram_address,
  output logic [23:0] sram_wdata,
  output logic [23:0] sram_wmask,
  input logic [23:0] sram_rdata
);
  logic [7:0] read_pending;
  logic [7:0] response_valid;
  logic [23:0] response_data;
  assign bank_ready = {((rst_n && enable[7:7]) && ((response_valid[7:7] && (!bank_write[7:7])) || (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_write[7:7] && (bank_address[7:7] < 2'd1))))), ((rst_n && enable[6:6]) && ((response_valid[6:6] && (!bank_write[6:6])) || (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_write[6:6] && (bank_address[6:6] < 2'd1))))), ((rst_n && enable[5:5]) && ((response_valid[5:5] && (!bank_write[5:5])) || (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_write[5:5] && (bank_address[5:5] < 2'd1))))), ((rst_n && enable[4:4]) && ((response_valid[4:4] && (!bank_write[4:4])) || (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_write[4:4] && (bank_address[4:4] < 2'd1))))), ((rst_n && enable[3:3]) && ((response_valid[3:3] && (!bank_write[3:3])) || (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_write[3:3] && (bank_address[3:3] < 2'd1))))), ((rst_n && enable[2:2]) && ((response_valid[2:2] && (!bank_write[2:2])) || (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_write[2:2] && (bank_address[2:2] < 2'd1))))), ((rst_n && enable[1:1]) && ((response_valid[1:1] && (!bank_write[1:1])) || (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_write[1:1] && (bank_address[1:1] < 2'd1))))), ((rst_n && enable[0:0]) && ((response_valid[0:0] && (!bank_write[0:0])) || (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_write[0:0] && (bank_address[0:0] < 2'd1)))))};
  assign sram_ce = {((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[7:7] < 2'd1)))), ((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[6:6] < 2'd1)))), ((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[5:5] < 2'd1)))), ((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[4:4] < 2'd1)))), ((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd1)))), ((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd1)))), ((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd1)))), ((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd1))))};
  assign sram_we = {(((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[7:7] < 2'd1)))) && bank_write[7:7]), (((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[6:6] < 2'd1)))) && bank_write[6:6]), (((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[5:5] < 2'd1)))) && bank_write[5:5]), (((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[4:4] < 2'd1)))) && bank_write[4:4]), (((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd1)))) && bank_write[3:3]), (((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd1)))) && bank_write[2:2]), (((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd1)))) && bank_write[1:1]), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd1)))) && bank_write[0:0])};
  assign sram_address = {(((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[7:7] < 2'd1)))) ? bank_address[7:7] : 1'd0), (((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[6:6] < 2'd1)))) ? bank_address[6:6] : 1'd0), (((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[5:5] < 2'd1)))) ? bank_address[5:5] : 1'd0), (((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[4:4] < 2'd1)))) ? bank_address[4:4] : 1'd0), (((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd1)))) ? bank_address[3:3] : 1'd0), (((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd1)))) ? bank_address[2:2] : 1'd0), (((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd1)))) ? bank_address[1:1] : 1'd0), (((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd1)))) ? bank_address[0:0] : 1'd0)};
  assign sram_wdata = {((((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[7:7] < 2'd1)))) && bank_write[7:7]) ? bank_data[23:21] : 3'd0), ((((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[6:6] < 2'd1)))) && bank_write[6:6]) ? bank_data[20:18] : 3'd0), ((((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[5:5] < 2'd1)))) && bank_write[5:5]) ? bank_data[17:15] : 3'd0), ((((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[4:4] < 2'd1)))) && bank_write[4:4]) ? bank_data[14:12] : 3'd0), ((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd1)))) && bank_write[3:3]) ? bank_data[11:9] : 3'd0), ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd1)))) && bank_write[2:2]) ? bank_data[8:6] : 3'd0), ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd1)))) && bank_write[1:1]) ? bank_data[5:3] : 3'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd1)))) && bank_write[0:0]) ? bank_data[2:0] : 3'd0)};
  assign sram_wmask = {((((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[7:7] < 2'd1)))) && bank_write[7:7]) ? bank_mask[23:21] : 3'd0), ((((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[6:6] < 2'd1)))) && bank_write[6:6]) ? bank_mask[20:18] : 3'd0), ((((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[5:5] < 2'd1)))) && bank_write[5:5]) ? bank_mask[17:15] : 3'd0), ((((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[4:4] < 2'd1)))) && bank_write[4:4]) ? bank_mask[14:12] : 3'd0), ((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd1)))) && bank_write[3:3]) ? bank_mask[11:9] : 3'd0), ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd1)))) && bank_write[2:2]) ? bank_mask[8:6] : 3'd0), ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd1)))) && bank_write[1:1]) ? bank_mask[5:3] : 3'd0), ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd1)))) && bank_write[0:0]) ? bank_mask[2:0] : 3'd0)};
  assign bank_rdata = response_data;
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          read_pending <= 8'd0;
          response_valid <= 8'd0;
          response_data <= 24'd0;
        end
      else
        begin
          if (read_pending[0:0])
            begin
              response_data[2:0] <= sram_rdata[2:0];
              read_pending[0:0] <= 1'd0;
              response_valid[0:0] <= 1'd1;
            end
          if ((response_valid[0:0] && ((!bank_write[0:0]) && (bank_valid[0:0] && enable[0:0]))))
            response_valid[0:0] <= 1'd0;
          if ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd1)))) && (!bank_write[0:0])))
            read_pending[0:0] <= 1'd1;
          if (read_pending[1:1])
            begin
              response_data[5:3] <= sram_rdata[5:3];
              read_pending[1:1] <= 1'd0;
              response_valid[1:1] <= 1'd1;
            end
          if ((response_valid[1:1] && ((!bank_write[1:1]) && (bank_valid[1:1] && enable[1:1]))))
            response_valid[1:1] <= 1'd0;
          if ((((rst_n && enable[1:1]) && (((!read_pending[1:1]) && (!response_valid[1:1])) && (bank_valid[1:1] && (bank_address[1:1] < 2'd1)))) && (!bank_write[1:1])))
            read_pending[1:1] <= 1'd1;
          if (read_pending[2:2])
            begin
              response_data[8:6] <= sram_rdata[8:6];
              read_pending[2:2] <= 1'd0;
              response_valid[2:2] <= 1'd1;
            end
          if ((response_valid[2:2] && ((!bank_write[2:2]) && (bank_valid[2:2] && enable[2:2]))))
            response_valid[2:2] <= 1'd0;
          if ((((rst_n && enable[2:2]) && (((!read_pending[2:2]) && (!response_valid[2:2])) && (bank_valid[2:2] && (bank_address[2:2] < 2'd1)))) && (!bank_write[2:2])))
            read_pending[2:2] <= 1'd1;
          if (read_pending[3:3])
            begin
              response_data[11:9] <= sram_rdata[11:9];
              read_pending[3:3] <= 1'd0;
              response_valid[3:3] <= 1'd1;
            end
          if ((response_valid[3:3] && ((!bank_write[3:3]) && (bank_valid[3:3] && enable[3:3]))))
            response_valid[3:3] <= 1'd0;
          if ((((rst_n && enable[3:3]) && (((!read_pending[3:3]) && (!response_valid[3:3])) && (bank_valid[3:3] && (bank_address[3:3] < 2'd1)))) && (!bank_write[3:3])))
            read_pending[3:3] <= 1'd1;
          if (read_pending[4:4])
            begin
              response_data[14:12] <= sram_rdata[14:12];
              read_pending[4:4] <= 1'd0;
              response_valid[4:4] <= 1'd1;
            end
          if ((response_valid[4:4] && ((!bank_write[4:4]) && (bank_valid[4:4] && enable[4:4]))))
            response_valid[4:4] <= 1'd0;
          if ((((rst_n && enable[4:4]) && (((!read_pending[4:4]) && (!response_valid[4:4])) && (bank_valid[4:4] && (bank_address[4:4] < 2'd1)))) && (!bank_write[4:4])))
            read_pending[4:4] <= 1'd1;
          if (read_pending[5:5])
            begin
              response_data[17:15] <= sram_rdata[17:15];
              read_pending[5:5] <= 1'd0;
              response_valid[5:5] <= 1'd1;
            end
          if ((response_valid[5:5] && ((!bank_write[5:5]) && (bank_valid[5:5] && enable[5:5]))))
            response_valid[5:5] <= 1'd0;
          if ((((rst_n && enable[5:5]) && (((!read_pending[5:5]) && (!response_valid[5:5])) && (bank_valid[5:5] && (bank_address[5:5] < 2'd1)))) && (!bank_write[5:5])))
            read_pending[5:5] <= 1'd1;
          if (read_pending[6:6])
            begin
              response_data[20:18] <= sram_rdata[20:18];
              read_pending[6:6] <= 1'd0;
              response_valid[6:6] <= 1'd1;
            end
          if ((response_valid[6:6] && ((!bank_write[6:6]) && (bank_valid[6:6] && enable[6:6]))))
            response_valid[6:6] <= 1'd0;
          if ((((rst_n && enable[6:6]) && (((!read_pending[6:6]) && (!response_valid[6:6])) && (bank_valid[6:6] && (bank_address[6:6] < 2'd1)))) && (!bank_write[6:6])))
            read_pending[6:6] <= 1'd1;
          if (read_pending[7:7])
            begin
              response_data[23:21] <= sram_rdata[23:21];
              read_pending[7:7] <= 1'd0;
              response_valid[7:7] <= 1'd1;
            end
          if ((response_valid[7:7] && ((!bank_write[7:7]) && (bank_valid[7:7] && enable[7:7]))))
            response_valid[7:7] <= 1'd0;
          if ((((rst_n && enable[7:7]) && (((!read_pending[7:7]) && (!response_valid[7:7])) && (bank_valid[7:7] && (bank_address[7:7] < 2'd1)))) && (!bank_write[7:7])))
            read_pending[7:7] <= 1'd1;
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_sram_root_5 (
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
  output logic [0:0] bank_ready,
  output logic [0:0] bank_lane,
  output logic [0:0] bank_write,
  output logic [0:0] bank_address,
  output logic [1:0] bank_data,
  output logic [1:0] bank_mask,
  output logic [1:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [3:0] out_data,
  output logic [0:0] out_tag,
  input logic [0:0] enable,
  output logic [0:0] sram_ce,
  output logic [0:0] sram_we,
  output logic [0:0] sram_address,
  output logic [1:0] sram_wdata,
  output logic [1:0] sram_wmask,
  input logic [1:0] sram_rdata
);
  agent_memory_batch_5 scheduler(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_write(in_write), .in_address(in_address), .in_data(in_data), .in_mask(in_mask), .in_tag(in_tag), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_lane(bank_lane), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_tag(out_tag));
  agent_sram_bridge_5 adapter(.clk(clk), .rst_n(rst_n), .enable(enable), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .sram_ce(sram_ce), .sram_we(sram_we), .sram_address(sram_address), .sram_wdata(sram_wdata), .sram_wmask(sram_wmask), .sram_rdata(sram_rdata));
endmodule

module agent_memory_batch_5 (
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

module agent_sram_bridge_5 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] enable,
  input logic [0:0] bank_valid,
  output logic [0:0] bank_ready,
  input logic [0:0] bank_write,
  input logic [0:0] bank_address,
  input logic [1:0] bank_data,
  input logic [1:0] bank_mask,
  output logic [1:0] bank_rdata,
  output logic [0:0] sram_ce,
  output logic [0:0] sram_we,
  output logic [0:0] sram_address,
  output logic [1:0] sram_wdata,
  output logic [1:0] sram_wmask,
  input logic [1:0] sram_rdata
);
  logic [0:0] read_pending;
  logic [0:0] response_valid;
  logic [1:0] response_data;
  assign bank_ready = {((rst_n && enable[0:0]) && ((response_valid[0:0] && (!bank_write[0:0])) || (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_write[0:0] && (bank_address[0:0] < 2'd2)))))};
  assign sram_ce = {((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2))))};
  assign sram_we = {(((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0])};
  assign sram_address = {(((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) ? bank_address[0:0] : 1'd0)};
  assign sram_wdata = {((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0]) ? bank_data[1:0] : 2'd0)};
  assign sram_wmask = {((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && bank_write[0:0]) ? bank_mask[1:0] : 2'd0)};
  assign bank_rdata = response_data;
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          read_pending <= 1'd0;
          response_valid <= 1'd0;
          response_data <= 2'd0;
        end
      else
        begin
          if (read_pending[0:0])
            begin
              response_data[1:0] <= sram_rdata[1:0];
              read_pending[0:0] <= 1'd0;
              response_valid[0:0] <= 1'd1;
            end
          if ((response_valid[0:0] && ((!bank_write[0:0]) && (bank_valid[0:0] && enable[0:0]))))
            response_valid[0:0] <= 1'd0;
          if ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[0:0] < 2'd2)))) && (!bank_write[0:0])))
            read_pending[0:0] <= 1'd1;
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module batch_sram_root_6 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [2:0] in_write,
  input logic [23:0] in_address,
  input logic [95:0] in_data,
  input logic [95:0] in_mask,
  input logic [15:0] in_tag,
  output logic [0:0] bank_valid,
  output logic [0:0] bank_ready,
  output logic [1:0] bank_lane,
  output logic [0:0] bank_write,
  output logic [7:0] bank_address,
  output logic [31:0] bank_data,
  output logic [31:0] bank_mask,
  output logic [31:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [95:0] out_data,
  output logic [15:0] out_tag,
  input logic [0:0] enable,
  output logic [0:0] sram_ce,
  output logic [0:0] sram_we,
  output logic [7:0] sram_address,
  output logic [31:0] sram_wdata,
  output logic [31:0] sram_wmask,
  input logic [31:0] sram_rdata
);
  agent_memory_batch_6 scheduler(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_write(in_write), .in_address(in_address), .in_data(in_data), .in_mask(in_mask), .in_tag(in_tag), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_lane(bank_lane), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_tag(out_tag));
  agent_sram_bridge_6 adapter(.clk(clk), .rst_n(rst_n), .enable(enable), .bank_valid(bank_valid), .bank_ready(bank_ready), .bank_write(bank_write), .bank_address(bank_address), .bank_data(bank_data), .bank_mask(bank_mask), .bank_rdata(bank_rdata), .sram_ce(sram_ce), .sram_we(sram_we), .sram_address(sram_address), .sram_wdata(sram_wdata), .sram_wmask(sram_wmask), .sram_rdata(sram_rdata));
endmodule

module agent_memory_batch_6 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] in_valid,
  output logic [0:0] in_ready,
  input logic [2:0] in_write,
  input logic [23:0] in_address,
  input logic [95:0] in_data,
  input logic [95:0] in_mask,
  input logic [15:0] in_tag,
  output logic [0:0] bank_valid,
  input logic [0:0] bank_ready,
  output logic [1:0] bank_lane,
  output logic [0:0] bank_write,
  output logic [7:0] bank_address,
  output logic [31:0] bank_data,
  output logic [31:0] bank_mask,
  input logic [31:0] bank_rdata,
  output logic [0:0] out_valid,
  input logic [0:0] out_ready,
  output logic [95:0] out_data,
  output logic [15:0] out_tag
);
  logic [0:0] busy;
  logic [2:0] pending;
  logic [0:0] response_valid;
  logic [2:0] saved_write;
  logic [23:0] saved_address;
  logic [95:0] saved_data;
  logic [95:0] saved_mask;
  logic [15:0] saved_tag;
  logic [95:0] result_data;
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
  wire [0:0] grant_0_2;
  assign grant_0_2 = (active && ((pending[2:2] && (1'd0 == 1'd0)) && (!((1'd0 || (pending[0:0] && (1'd0 == 1'd0))) || (pending[1:1] && (1'd0 == 1'd0))))));
  assign bank_valid = {(((1'd0 || grant_0_0) || grant_0_1) || grant_0_2)};
  assign bank_lane = {(grant_0_0 ? 2'd0 : (grant_0_1 ? 2'd1 : (grant_0_2 ? 2'd2 : 2'd0)))};
  assign bank_write = {(grant_0_0 ? saved_write[0:0] : (grant_0_1 ? saved_write[1:1] : (grant_0_2 ? saved_write[2:2] : 1'd0)))};
  assign bank_address = {(grant_0_0 ? saved_address[7:0] : (grant_0_1 ? saved_address[15:8] : (grant_0_2 ? saved_address[23:16] : 8'd0)))};
  assign bank_data = {(grant_0_0 ? saved_data[31:0] : (grant_0_1 ? saved_data[63:32] : (grant_0_2 ? saved_data[95:64] : 32'd0)))};
  assign bank_mask = {(grant_0_0 ? saved_mask[31:0] : (grant_0_1 ? saved_mask[63:32] : (grant_0_2 ? saved_mask[95:64] : 32'd0)))};
  wire [0:0] fire_0;
  assign fire_0 = (1'd0 || (grant_0_0 && bank_ready[0:0]));
  wire [0:0] fire_1;
  assign fire_1 = (1'd0 || (grant_0_1 && bank_ready[0:0]));
  wire [0:0] fire_2;
  assign fire_2 = (1'd0 || (grant_0_2 && bank_ready[0:0]));
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
          saved_address <= 24'd0;
          saved_data <= 96'd0;
          saved_mask <= 96'd0;
          saved_tag <= 16'd0;
          result_data <= 96'd0;
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
                result_data[31:0] <= (saved_write[0:0] ? 32'd0 : (grant_0_0 ? bank_rdata[31:0] : 32'd0));
              if (fire_1)
                result_data[63:32] <= (saved_write[1:1] ? 32'd0 : (grant_0_1 ? bank_rdata[31:0] : 32'd0));
              if (fire_2)
                result_data[95:64] <= (saved_write[2:2] ? 32'd0 : (grant_0_2 ? bank_rdata[31:0] : 32'd0));
            end
          if ((in_valid && in_ready))
            begin
              busy <= 1'd1;
              pending <= 3'd7;
              response_valid <= 1'd0;
              result_data <= 96'd0;
              saved_write <= in_write;
              saved_address <= in_address;
              saved_data <= in_data;
              saved_mask <= in_mask;
              saved_tag <= in_tag;
            end
        end
    end
endmodule

module agent_sram_bridge_6 (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] enable,
  input logic [0:0] bank_valid,
  output logic [0:0] bank_ready,
  input logic [0:0] bank_write,
  input logic [7:0] bank_address,
  input logic [31:0] bank_data,
  input logic [31:0] bank_mask,
  output logic [31:0] bank_rdata,
  output logic [0:0] sram_ce,
  output logic [0:0] sram_we,
  output logic [7:0] sram_address,
  output logic [31:0] sram_wdata,
  output logic [31:0] sram_wmask,
  input logic [31:0] sram_rdata
);
  logic [0:0] read_pending;
  logic [0:0] response_valid;
  logic [31:0] response_data;
  assign bank_ready = {((rst_n && enable[0:0]) && ((response_valid[0:0] && (!bank_write[0:0])) || (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_write[0:0] && (bank_address[7:0] < 9'd256)))))};
  assign sram_ce = {((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[7:0] < 9'd256))))};
  assign sram_we = {(((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[7:0] < 9'd256)))) && bank_write[0:0])};
  assign sram_address = {(((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[7:0] < 9'd256)))) ? bank_address[7:0] : 8'd0)};
  assign sram_wdata = {((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[7:0] < 9'd256)))) && bank_write[0:0]) ? bank_data[31:0] : 32'd0)};
  assign sram_wmask = {((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[7:0] < 9'd256)))) && bank_write[0:0]) ? bank_mask[31:0] : 32'd0)};
  assign bank_rdata = response_data;
  always_ff @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          read_pending <= 1'd0;
          response_valid <= 1'd0;
          response_data <= 32'd0;
        end
      else
        begin
          if (read_pending[0:0])
            begin
              response_data[31:0] <= sram_rdata[31:0];
              read_pending[0:0] <= 1'd0;
              response_valid[0:0] <= 1'd1;
            end
          if ((response_valid[0:0] && ((!bank_write[0:0]) && (bank_valid[0:0] && enable[0:0]))))
            response_valid[0:0] <= 1'd0;
          if ((((rst_n && enable[0:0]) && (((!read_pending[0:0]) && (!response_valid[0:0])) && (bank_valid[0:0] && (bank_address[7:0] < 9'd256)))) && (!bank_write[0:0])))
            read_pending[0:0] <= 1'd1;
        end
    end
endmodule

