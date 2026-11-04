// Generated from owned AST/IR; functional qualification is separate.
module case_0_0 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words[0:15];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = words[a];
  assign y = words[b];
  always @(posedge clk)
    if (we)
      words[a] <= data;
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_0_1 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = ((a[1:0] == 2'd0) ? words_bank_0[a[3:2]] : ((a[1:0] == 2'd1) ? words_bank_1[a[3:2]] : ((a[1:0] == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign y = ((b[1:0] == 2'd0) ? words_bank_0[b[3:2]] : ((b[1:0] == 2'd1) ? words_bank_1[b[3:2]] : ((b[1:0] == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]])));
  always @(posedge clk)
    if (we)
      begin
        if ((a[1:0] == 2'd0))
          words_bank_0[a[3:2]] <= data;
        if ((a[1:0] == 2'd1))
          words_bank_1[a[3:2]] <= data;
        if ((a[1:0] == 2'd2))
          words_bank_2[a[3:2]] <= data;
        if ((a[1:0] == 2'd3))
          words_bank_3[a[3:2]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_0_2 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = ((a[3:2] == 2'd0) ? words_bank_0[a[1:0]] : ((a[3:2] == 2'd1) ? words_bank_1[a[1:0]] : ((a[3:2] == 2'd2) ? words_bank_2[a[1:0]] : words_bank_3[a[1:0]])));
  assign y = ((b[3:2] == 2'd0) ? words_bank_0[b[1:0]] : ((b[3:2] == 2'd1) ? words_bank_1[b[1:0]] : ((b[3:2] == 2'd2) ? words_bank_2[b[1:0]] : words_bank_3[b[1:0]])));
  always @(posedge clk)
    if (we)
      begin
        if ((a[3:2] == 2'd0))
          words_bank_0[a[1:0]] <= data;
        if ((a[3:2] == 2'd1))
          words_bank_1[a[1:0]] <= data;
        if ((a[3:2] == 2'd2))
          words_bank_2[a[1:0]] <= data;
        if ((a[3:2] == 2'd3))
          words_bank_3[a[1:0]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_0_3 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = (((a[1:0] ^ a[3:2]) == 2'd0) ? words_bank_0[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd1) ? words_bank_1[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign y = (((b[1:0] ^ b[3:2]) == 2'd0) ? words_bank_0[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd1) ? words_bank_1[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]])));
  always @(posedge clk)
    if (we)
      begin
        if (((a[1:0] ^ a[3:2]) == 2'd0))
          words_bank_0[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd1))
          words_bank_1[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd2))
          words_bank_2[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd3))
          words_bank_3[a[3:2]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_1_0 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words[0:15];
  wire [3:0] other;
  assign other = (a ^ 4'd4);
  assign x = words[a];
  assign y = words[other];
  always @(posedge clk)
    if (we)
      words[a] <= data;
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_1_1 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd4);
  assign x = ((a[1:0] == 2'd0) ? words_bank_0[a[3:2]] : ((a[1:0] == 2'd1) ? words_bank_1[a[3:2]] : ((a[1:0] == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign y = ((other[1:0] == 2'd0) ? words_bank_0[other[3:2]] : ((other[1:0] == 2'd1) ? words_bank_1[other[3:2]] : ((other[1:0] == 2'd2) ? words_bank_2[other[3:2]] : words_bank_3[other[3:2]])));
  always @(posedge clk)
    if (we)
      begin
        if ((a[1:0] == 2'd0))
          words_bank_0[a[3:2]] <= data;
        if ((a[1:0] == 2'd1))
          words_bank_1[a[3:2]] <= data;
        if ((a[1:0] == 2'd2))
          words_bank_2[a[3:2]] <= data;
        if ((a[1:0] == 2'd3))
          words_bank_3[a[3:2]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_1_2 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd4);
  assign x = ((a[3:2] == 2'd0) ? words_bank_0[a[1:0]] : ((a[3:2] == 2'd1) ? words_bank_1[a[1:0]] : ((a[3:2] == 2'd2) ? words_bank_2[a[1:0]] : words_bank_3[a[1:0]])));
  assign y = ((other[3:2] == 2'd0) ? words_bank_0[other[1:0]] : ((other[3:2] == 2'd1) ? words_bank_1[other[1:0]] : ((other[3:2] == 2'd2) ? words_bank_2[other[1:0]] : words_bank_3[other[1:0]])));
  always @(posedge clk)
    if (we)
      begin
        if ((a[3:2] == 2'd0))
          words_bank_0[a[1:0]] <= data;
        if ((a[3:2] == 2'd1))
          words_bank_1[a[1:0]] <= data;
        if ((a[3:2] == 2'd2))
          words_bank_2[a[1:0]] <= data;
        if ((a[3:2] == 2'd3))
          words_bank_3[a[1:0]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_1_3 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd4);
  assign x = (((a[1:0] ^ a[3:2]) == 2'd0) ? words_bank_0[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd1) ? words_bank_1[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign y = (((other[1:0] ^ other[3:2]) == 2'd0) ? words_bank_0[other[3:2]] : (((other[1:0] ^ other[3:2]) == 2'd1) ? words_bank_1[other[3:2]] : (((other[1:0] ^ other[3:2]) == 2'd2) ? words_bank_2[other[3:2]] : words_bank_3[other[3:2]])));
  always @(posedge clk)
    if (we)
      begin
        if (((a[1:0] ^ a[3:2]) == 2'd0))
          words_bank_0[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd1))
          words_bank_1[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd2))
          words_bank_2[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd3))
          words_bank_3[a[3:2]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_2_0 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words[0:15];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = words[a];
  assign y = words[other];
  always @(posedge clk)
    if (we)
      words[a] <= data;
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_2_1 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = ((a[1:0] == 2'd0) ? words_bank_0[a[3:2]] : ((a[1:0] == 2'd1) ? words_bank_1[a[3:2]] : ((a[1:0] == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign y = ((other[1:0] == 2'd0) ? words_bank_0[other[3:2]] : ((other[1:0] == 2'd1) ? words_bank_1[other[3:2]] : ((other[1:0] == 2'd2) ? words_bank_2[other[3:2]] : words_bank_3[other[3:2]])));
  always @(posedge clk)
    if (we)
      begin
        if ((a[1:0] == 2'd0))
          words_bank_0[a[3:2]] <= data;
        if ((a[1:0] == 2'd1))
          words_bank_1[a[3:2]] <= data;
        if ((a[1:0] == 2'd2))
          words_bank_2[a[3:2]] <= data;
        if ((a[1:0] == 2'd3))
          words_bank_3[a[3:2]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_2_2 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = ((a[3:2] == 2'd0) ? words_bank_0[a[1:0]] : ((a[3:2] == 2'd1) ? words_bank_1[a[1:0]] : ((a[3:2] == 2'd2) ? words_bank_2[a[1:0]] : words_bank_3[a[1:0]])));
  assign y = ((other[3:2] == 2'd0) ? words_bank_0[other[1:0]] : ((other[3:2] == 2'd1) ? words_bank_1[other[1:0]] : ((other[3:2] == 2'd2) ? words_bank_2[other[1:0]] : words_bank_3[other[1:0]])));
  always @(posedge clk)
    if (we)
      begin
        if ((a[3:2] == 2'd0))
          words_bank_0[a[1:0]] <= data;
        if ((a[3:2] == 2'd1))
          words_bank_1[a[1:0]] <= data;
        if ((a[3:2] == 2'd2))
          words_bank_2[a[1:0]] <= data;
        if ((a[3:2] == 2'd3))
          words_bank_3[a[1:0]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_2_3 (
  input wire clk,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] x,
  output wire [7:0] y
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  wire [3:0] other;
  assign other = (a ^ 4'd5);
  assign x = (((a[1:0] ^ a[3:2]) == 2'd0) ? words_bank_0[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd1) ? words_bank_1[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign y = (((other[1:0] ^ other[3:2]) == 2'd0) ? words_bank_0[other[3:2]] : (((other[1:0] ^ other[3:2]) == 2'd1) ? words_bank_1[other[3:2]] : (((other[1:0] ^ other[3:2]) == 2'd2) ? words_bank_2[other[3:2]] : words_bank_3[other[3:2]])));
  always @(posedge clk)
    if (we)
      begin
        if (((a[1:0] ^ a[3:2]) == 2'd0))
          words_bank_0[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd1))
          words_bank_1[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd2))
          words_bank_2[a[3:2]] <= data;
        if (((a[1:0] ^ a[3:2]) == 2'd3))
          words_bank_3[a[3:2]] <= data;
      end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_3_0 (
  input wire clk,
  input wire rst_n,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] out_live,
  output wire [3:0] out_lane,
  output reg [7:0] out_q
);
  reg [7:0] words[0:15];
  assign out_live = words[a];
  assign out_lane = words[b][3:0];
  always @(posedge clk)
    begin
      if ((!rst_n))
        out_q <= 8'd0;
      else
        begin
          out_q <= words[b];
          if (we)
            begin
              words[a] <= data;
              words[b][3:0] <= data[3:0];
              if (sel)
                words[a] <= (words[b] ^ data);
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_3_1 (
  input wire clk,
  input wire rst_n,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] out_live,
  output wire [3:0] out_lane,
  output reg [7:0] out_q
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  assign out_live = ((a[1:0] == 2'd0) ? words_bank_0[a[3:2]] : ((a[1:0] == 2'd1) ? words_bank_1[a[3:2]] : ((a[1:0] == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign out_lane = ((b[1:0] == 2'd0) ? words_bank_0[b[3:2]][3:0] : ((b[1:0] == 2'd1) ? words_bank_1[b[3:2]][3:0] : ((b[1:0] == 2'd2) ? words_bank_2[b[3:2]][3:0] : words_bank_3[b[3:2]][3:0])));
  always @(posedge clk)
    begin
      if ((!rst_n))
        out_q <= 8'd0;
      else
        begin
          out_q <= ((b[1:0] == 2'd0) ? words_bank_0[b[3:2]] : ((b[1:0] == 2'd1) ? words_bank_1[b[3:2]] : ((b[1:0] == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]])));
          if (we)
            begin
              begin
                if ((a[1:0] == 2'd0))
                  words_bank_0[a[3:2]] <= data;
                if ((a[1:0] == 2'd1))
                  words_bank_1[a[3:2]] <= data;
                if ((a[1:0] == 2'd2))
                  words_bank_2[a[3:2]] <= data;
                if ((a[1:0] == 2'd3))
                  words_bank_3[a[3:2]] <= data;
              end
              begin
                if ((b[1:0] == 2'd0))
                  words_bank_0[b[3:2]][3:0] <= data[3:0];
                if ((b[1:0] == 2'd1))
                  words_bank_1[b[3:2]][3:0] <= data[3:0];
                if ((b[1:0] == 2'd2))
                  words_bank_2[b[3:2]][3:0] <= data[3:0];
                if ((b[1:0] == 2'd3))
                  words_bank_3[b[3:2]][3:0] <= data[3:0];
              end
              if (sel)
                begin
                  if ((a[1:0] == 2'd0))
                    words_bank_0[a[3:2]] <= (((b[1:0] == 2'd0) ? words_bank_0[b[3:2]] : ((b[1:0] == 2'd1) ? words_bank_1[b[3:2]] : ((b[1:0] == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                  if ((a[1:0] == 2'd1))
                    words_bank_1[a[3:2]] <= (((b[1:0] == 2'd0) ? words_bank_0[b[3:2]] : ((b[1:0] == 2'd1) ? words_bank_1[b[3:2]] : ((b[1:0] == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                  if ((a[1:0] == 2'd2))
                    words_bank_2[a[3:2]] <= (((b[1:0] == 2'd0) ? words_bank_0[b[3:2]] : ((b[1:0] == 2'd1) ? words_bank_1[b[3:2]] : ((b[1:0] == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                  if ((a[1:0] == 2'd3))
                    words_bank_3[a[3:2]] <= (((b[1:0] == 2'd0) ? words_bank_0[b[3:2]] : ((b[1:0] == 2'd1) ? words_bank_1[b[3:2]] : ((b[1:0] == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                end
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_3_2 (
  input wire clk,
  input wire rst_n,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] out_live,
  output wire [3:0] out_lane,
  output reg [7:0] out_q
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  assign out_live = ((a[3:2] == 2'd0) ? words_bank_0[a[1:0]] : ((a[3:2] == 2'd1) ? words_bank_1[a[1:0]] : ((a[3:2] == 2'd2) ? words_bank_2[a[1:0]] : words_bank_3[a[1:0]])));
  assign out_lane = ((b[3:2] == 2'd0) ? words_bank_0[b[1:0]][3:0] : ((b[3:2] == 2'd1) ? words_bank_1[b[1:0]][3:0] : ((b[3:2] == 2'd2) ? words_bank_2[b[1:0]][3:0] : words_bank_3[b[1:0]][3:0])));
  always @(posedge clk)
    begin
      if ((!rst_n))
        out_q <= 8'd0;
      else
        begin
          out_q <= ((b[3:2] == 2'd0) ? words_bank_0[b[1:0]] : ((b[3:2] == 2'd1) ? words_bank_1[b[1:0]] : ((b[3:2] == 2'd2) ? words_bank_2[b[1:0]] : words_bank_3[b[1:0]])));
          if (we)
            begin
              begin
                if ((a[3:2] == 2'd0))
                  words_bank_0[a[1:0]] <= data;
                if ((a[3:2] == 2'd1))
                  words_bank_1[a[1:0]] <= data;
                if ((a[3:2] == 2'd2))
                  words_bank_2[a[1:0]] <= data;
                if ((a[3:2] == 2'd3))
                  words_bank_3[a[1:0]] <= data;
              end
              begin
                if ((b[3:2] == 2'd0))
                  words_bank_0[b[1:0]][3:0] <= data[3:0];
                if ((b[3:2] == 2'd1))
                  words_bank_1[b[1:0]][3:0] <= data[3:0];
                if ((b[3:2] == 2'd2))
                  words_bank_2[b[1:0]][3:0] <= data[3:0];
                if ((b[3:2] == 2'd3))
                  words_bank_3[b[1:0]][3:0] <= data[3:0];
              end
              if (sel)
                begin
                  if ((a[3:2] == 2'd0))
                    words_bank_0[a[1:0]] <= (((b[3:2] == 2'd0) ? words_bank_0[b[1:0]] : ((b[3:2] == 2'd1) ? words_bank_1[b[1:0]] : ((b[3:2] == 2'd2) ? words_bank_2[b[1:0]] : words_bank_3[b[1:0]]))) ^ data);
                  if ((a[3:2] == 2'd1))
                    words_bank_1[a[1:0]] <= (((b[3:2] == 2'd0) ? words_bank_0[b[1:0]] : ((b[3:2] == 2'd1) ? words_bank_1[b[1:0]] : ((b[3:2] == 2'd2) ? words_bank_2[b[1:0]] : words_bank_3[b[1:0]]))) ^ data);
                  if ((a[3:2] == 2'd2))
                    words_bank_2[a[1:0]] <= (((b[3:2] == 2'd0) ? words_bank_0[b[1:0]] : ((b[3:2] == 2'd1) ? words_bank_1[b[1:0]] : ((b[3:2] == 2'd2) ? words_bank_2[b[1:0]] : words_bank_3[b[1:0]]))) ^ data);
                  if ((a[3:2] == 2'd3))
                    words_bank_3[a[1:0]] <= (((b[3:2] == 2'd0) ? words_bank_0[b[1:0]] : ((b[3:2] == 2'd1) ? words_bank_1[b[1:0]] : ((b[3:2] == 2'd2) ? words_bank_2[b[1:0]] : words_bank_3[b[1:0]]))) ^ data);
                end
            end
        end
    end
endmodule


// Generated from owned AST/IR; functional qualification is separate.
module case_3_3 (
  input wire clk,
  input wire rst_n,
  input wire we,
  input wire sel,
  input wire [3:0] a,
  input wire [3:0] b,
  input wire [7:0] data,
  output wire [7:0] out_live,
  output wire [3:0] out_lane,
  output reg [7:0] out_q
);
  reg [7:0] words_bank_0[0:3];
  reg [7:0] words_bank_1[0:3];
  reg [7:0] words_bank_2[0:3];
  reg [7:0] words_bank_3[0:3];
  assign out_live = (((a[1:0] ^ a[3:2]) == 2'd0) ? words_bank_0[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd1) ? words_bank_1[a[3:2]] : (((a[1:0] ^ a[3:2]) == 2'd2) ? words_bank_2[a[3:2]] : words_bank_3[a[3:2]])));
  assign out_lane = (((b[1:0] ^ b[3:2]) == 2'd0) ? words_bank_0[b[3:2]][3:0] : (((b[1:0] ^ b[3:2]) == 2'd1) ? words_bank_1[b[3:2]][3:0] : (((b[1:0] ^ b[3:2]) == 2'd2) ? words_bank_2[b[3:2]][3:0] : words_bank_3[b[3:2]][3:0])));
  always @(posedge clk)
    begin
      if ((!rst_n))
        out_q <= 8'd0;
      else
        begin
          out_q <= (((b[1:0] ^ b[3:2]) == 2'd0) ? words_bank_0[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd1) ? words_bank_1[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]])));
          if (we)
            begin
              begin
                if (((a[1:0] ^ a[3:2]) == 2'd0))
                  words_bank_0[a[3:2]] <= data;
                if (((a[1:0] ^ a[3:2]) == 2'd1))
                  words_bank_1[a[3:2]] <= data;
                if (((a[1:0] ^ a[3:2]) == 2'd2))
                  words_bank_2[a[3:2]] <= data;
                if (((a[1:0] ^ a[3:2]) == 2'd3))
                  words_bank_3[a[3:2]] <= data;
              end
              begin
                if (((b[1:0] ^ b[3:2]) == 2'd0))
                  words_bank_0[b[3:2]][3:0] <= data[3:0];
                if (((b[1:0] ^ b[3:2]) == 2'd1))
                  words_bank_1[b[3:2]][3:0] <= data[3:0];
                if (((b[1:0] ^ b[3:2]) == 2'd2))
                  words_bank_2[b[3:2]][3:0] <= data[3:0];
                if (((b[1:0] ^ b[3:2]) == 2'd3))
                  words_bank_3[b[3:2]][3:0] <= data[3:0];
              end
              if (sel)
                begin
                  if (((a[1:0] ^ a[3:2]) == 2'd0))
                    words_bank_0[a[3:2]] <= ((((b[1:0] ^ b[3:2]) == 2'd0) ? words_bank_0[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd1) ? words_bank_1[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                  if (((a[1:0] ^ a[3:2]) == 2'd1))
                    words_bank_1[a[3:2]] <= ((((b[1:0] ^ b[3:2]) == 2'd0) ? words_bank_0[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd1) ? words_bank_1[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                  if (((a[1:0] ^ a[3:2]) == 2'd2))
                    words_bank_2[a[3:2]] <= ((((b[1:0] ^ b[3:2]) == 2'd0) ? words_bank_0[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd1) ? words_bank_1[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                  if (((a[1:0] ^ a[3:2]) == 2'd3))
                    words_bank_3[a[3:2]] <= ((((b[1:0] ^ b[3:2]) == 2'd0) ? words_bank_0[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd1) ? words_bank_1[b[3:2]] : (((b[1:0] ^ b[3:2]) == 2'd2) ? words_bank_2[b[3:2]] : words_bank_3[b[3:2]]))) ^ data);
                end
            end
        end
    end
endmodule

