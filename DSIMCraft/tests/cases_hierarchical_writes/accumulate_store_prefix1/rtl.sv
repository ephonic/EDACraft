// Generated from owned AST/IR; functional qualification is separate.
module agent_generic_module (
  input wire [0:0] clk,
  input wire [0:0] rst_n,
  input wire [0:0] in_en,
  input wire [1:0] in_mode,
  input wire [3:0] in_a,
  input wire [3:0] in_b,
  input wire [63:0] in_d0,
  input wire [63:0] in_d1,
  input wire [12:0] in_tag,
  output wire [63:0] out_value,
  output wire [63:0] out_other,
  output reg [63:0] out_captured,
  output reg [12:0] out_held_tag
);
  reg [63:0] words[0:15];
  reg valid[0:15];
  wire [63:0] read_a;
  wire [63:0] read_b;
  assign read_a = (valid[in_a] ? words[in_a] : 64'd0);
  assign read_b = (valid[in_b] ? words[in_b] : 64'd0);
  assign out_value = read_a;
  assign out_other = read_b;
  always @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          valid[0] <= 1'b0;
          valid[1] <= 1'b0;
          valid[2] <= 1'b0;
          valid[3] <= 1'b0;
          valid[4] <= 1'b0;
          valid[5] <= 1'b0;
          valid[6] <= 1'b0;
          valid[7] <= 1'b0;
          valid[8] <= 1'b0;
          valid[9] <= 1'b0;
          valid[10] <= 1'b0;
          valid[11] <= 1'b0;
          valid[12] <= 1'b0;
          valid[13] <= 1'b0;
          valid[14] <= 1'b0;
          valid[15] <= 1'b0;
          out_captured <= 64'd0;
          out_held_tag <= 13'd7;
        end
      else
        begin
          out_captured <= read_a;
          if (in_en)
            begin
              valid[in_a] <= 1'b1;
              if (in_mode[0])
                valid[in_a] <= 1'b1;
              if ((in_mode[1] && (in_a == in_b)))
                valid[in_b] <= 1'b1;
              out_held_tag <= in_tag;
            end
        end
    end
  always @(posedge clk)
    begin
      if ((rst_n && in_en))
        begin
          ;
          if (in_mode[0])
            ;
          if ((in_mode[1] && (in_a == in_b)))
            ;
        end
      if ((((1'b1 && (rst_n && in_en)) || ((1'b1 && (rst_n && in_en)) && in_mode[0])) || ((1'b1 && (rst_n && in_en)) && (in_mode[1] && (in_a == in_b)))))
        words[(((1'b1 && (rst_n && in_en)) && (in_mode[1] && (in_a == in_b))) ? in_b : (((1'b1 && (rst_n && in_en)) && in_mode[0]) ? in_a : in_a))] <= (((1'b1 && (rst_n && in_en)) && (in_mode[1] && (in_a == in_b))) ? (read_a + in_d1) : (((1'b1 && (rst_n && in_en)) && in_mode[0]) ? in_d1 : in_d0));
    end
endmodule

