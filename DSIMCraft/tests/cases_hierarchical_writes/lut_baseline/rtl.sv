module dut(input wire clk,rst_n,in_valid,in_ready,in_wen,in_mode,
 input wire [3:0] in_a,in_b,in_c,in_d,in_addr,
 input wire [31:0] in_data,input wire [12:0] in_tag,
 output wire out_ready,output reg out_valid,
 output reg [31:0] out_value,output reg [12:0] out_tag);
 reg [31:0] words[0:15];reg [31:0] history;
 wire [31:0] read_a,read_b;
 assign read_a=words[in_a];assign read_b=words[in_b];
 assign out_ready=rst_n && (!out_valid || in_ready);
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin out_valid<=1'b0;out_value<=32'd0;out_tag<=13'd7;history<=32'd3;end
 else if(out_ready) begin out_valid<=in_valid;
 if(in_valid) begin if(in_mode) out_value <= read_a ^ read_b;
       else out_value <= read_a - read_b;
       history <= words[in_c] + history;
       if(in_wen) out_value <= out_value + words[in_d]; out_tag<=in_tag;end end end
 always @(posedge clk) if(rst_n && out_ready && in_valid && in_wen) words[in_addr]<=in_data;
 endmodule