//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/06/14 12:33:36
// Design Name: 
// Module Name: mdc_ntt_modadd_level1
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module js_vm_modadd
(
    clk,
    rstn,
    data,
    q,
    res,
    i_vm_id,
    o_vm_id,
    i_valid,
    o_valid,
    i_ready,
    o_ready
);

`include "js_vm.vh"
localparam  PART   = 4;
localparam  SEG_WIDTH= (DATA_WIDTH+PART-1)/PART; //ceil
input wire clk;
input wire rstn;
input wire [ISA_BITS+2*REG_WIDTH+1-1:0] data;
input wire [DATA_WIDTH-1:0] q;
input wire [3:0]           i_vm_id;
input wire                 i_valid;
input wire                 o_ready;
output wire [3:0]          o_vm_id;
output wire                o_valid;
output wire                i_ready;
output wire [ISA_BITS+REG_WIDTH+1-1:0] res;

wire [ISA_BITS-1 :0] isa;
wire                 cc_val;
wire [REG_WIDTH-DATA_WIDTH-1:0] flag_bits;
reg  [ISA_BITS-1 :0]            s0_isa;
reg                             s0_cc_val;
reg  [REG_WIDTH-DATA_WIDTH-1:0] s0_flag_bits;
reg  [3:0]                      s0_vm_id;
reg  [ISA_BITS-1 :0]            s1_isa;
reg                             s1_cc_val;
reg  [REG_WIDTH-DATA_WIDTH-1:0] s1_flag_bits;
reg  [3:0]                      s1_vm_id;
wire [REG_WIDTH-1:0] a;
wire [REG_WIDTH-1:0] b;
wire [PART*SEG_WIDTH-1:0] a_ext;
wire [PART*SEG_WIDTH-1:0] b_ext;
wire [PART*SEG_WIDTH-1:0] q_ext;
reg  [PART*SEG_WIDTH-1:0] q_ext_r;
wire [SEG_WIDTH-1:0] a_segment [PART-1:0];
wire [SEG_WIDTH-1:0] b_segment [PART-1:0];
wire [SEG_WIDTH-1:0] q_segment [PART-1:0];
wire [SEG_WIDTH-1:0] s0_sum_0;
wire [SEG_WIDTH-1:0] s0_sum_segment_0 [PART-2:0];
wire [SEG_WIDTH-1:0] s0_sum_segment_1 [PART-2:0];
wire [PART-1:0]      s0_carry_segment;
wire [PART-2:0]      s0_carry_segment_0;
wire [PART-2:0]      s0_carry_segment_1;
reg  [SEG_WIDTH-1:0] s0_sum_segment_r[PART-1:0];
reg                  s0_carry_r;
wire [SEG_WIDTH-1:0] s1_sum_1;
wire [SEG_WIDTH-1:0] s1_sum_segment_0 [PART-2:0];
wire [SEG_WIDTH-1:0] s1_sum_segment_1 [PART-2:0];
wire [PART-1:0]      s1_carry_segment;
wire [PART-2:0]      s1_carry_segment_0;
wire [PART-2:0]      s1_carry_segment_1;
reg  [SEG_WIDTH-1:0] s1_sum_segment_r[PART-1:0];
wire [PART*SEG_WIDTH-1:0] res_tmp;
wire                 pipe_en0;
wire                 pipe_en1;
wire                 pipe_i_valid0;
wire                 pipe_i_ready0;
reg                  pipe_o_valid0;
wire                 pipe_o_ready0;
wire                 pipe_i_valid1;
wire                 pipe_i_ready1;
reg                  pipe_o_valid1;
wire                 pipe_o_ready1;

assign {isa, cc_val, b, a} = data;
assign flag_bits           = a[REG_WIDTH-1:DATA_WIDTH]; 
assign a_ext = {{(PART*SEG_WIDTH-DATA_WIDTH){1'b0}} ,a};
assign b_ext = {{(PART*SEG_WIDTH-DATA_WIDTH){1'b0}} ,b};
assign q_ext = ~{{(PART*SEG_WIDTH-DATA_WIDTH){1'b0}} ,q};
/////pipeline Stage 0///
genvar part;
generate
    for (part=0; part<PART; part=part+1) begin: stage0
        assign a_segment[part][SEG_WIDTH-1:0] = a_ext[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH]; 
        assign b_segment[part][SEG_WIDTH-1:0] = b_ext[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH];
        if (part==0) begin
            assign {s0_carry_segment[part], s0_sum_0} = a_segment[part] + b_segment[part];
            always @ (posedge clk) begin
                if (pipe_en0) begin
                    s0_sum_segment_r[part] <= s0_sum_0; 
                end
                else begin
                    s0_sum_segment_r[part] <= s0_sum_segment_r[part]; 
                end
            end
        end
        else begin
            assign {s0_carry_segment_0[part-1], s0_sum_segment_0[part-1]} = a_segment[part] + b_segment[part];
            assign {s0_carry_segment_1[part-1], s0_sum_segment_1[part-1]} = a_segment[part] + b_segment[part] + 1'b1;
            assign s0_carry_segment[part]                                 = s0_carry_segment[part-1] ? s0_carry_segment_1[part-1] : s0_carry_segment_0[part-1];
            if (part==PART-1) begin
                always @ (posedge clk) begin
                    if (pipe_en0) begin
                        s0_carry_r <= s0_carry_segment[part];
                    end
                    else begin
                        s0_carry_r <= s0_carry_r;
                    end                
                end
            end
            always @ (posedge clk) begin
                if (pipe_en0) begin
                    s0_sum_segment_r[part] <= s0_carry_segment[part-1] ? s0_sum_segment_1[part-1] : s0_sum_segment_0[part-1];
                end
                else begin
                    s0_sum_segment_r[part] <= s0_sum_segment_r[part];
                end
            end
            
        end
    end
endgenerate

always @ (posedge clk) begin
    if (pipe_en0) begin
        q_ext_r      <= q_ext;
        s0_isa       <= isa;
        s0_cc_val    <= cc_val;
        s0_flag_bits <= flag_bits;
        s0_vm_id     <= i_vm_id;
    end
    else begin
        q_ext_r      <= q_ext_r;
        s0_isa       <= s0_isa;
        s0_cc_val    <= s0_cc_val;
        s0_flag_bits <= s0_flag_bits;
        s0_vm_id     <= s0_vm_id;
    end
end
///pipeline stage 1////
generate
    for (part=0; part<PART; part=part+1) begin: stage1
        assign q_segment[part][SEG_WIDTH-1:0] = q_ext_r[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH]; 
        if (part == 0) begin
            assign {s1_carry_segment[part], s1_sum_1} = s0_sum_segment_r[part] + q_segment[part] + 1'b1;
            always @ (posedge clk) begin
                if (pipe_en1) begin
                    s1_sum_segment_r[part] <= (s0_carry_r|s1_carry_segment[PART-1]) ? s1_sum_1 : s0_sum_segment_r[part]; //////1
                end
                else begin
                    s1_sum_segment_r[part] <= s1_sum_segment_r[part]; 
                end
            end
        end
        else begin
            assign {s1_carry_segment_0[part-1], s1_sum_segment_0[part-1]} = s0_sum_segment_r[part] + q_segment[part];
            assign {s1_carry_segment_1[part-1], s1_sum_segment_1[part-1]} = s0_sum_segment_r[part] + q_segment[part] + 1'b1;
            assign s1_carry_segment[part]                                 = s1_carry_segment[part-1] ? s1_carry_segment_1[part-1] : s1_carry_segment_0[part-1];
            always @ (posedge clk) begin
                if (pipe_en1) begin
                    s1_sum_segment_r[part] <= (s0_carry_r|s1_carry_segment[PART-1]) ? (s1_carry_segment[part-1] ? s1_sum_segment_1[part-1] : s1_sum_segment_0[part-1]) : s0_sum_segment_r[part];
                end
                else begin
                    s1_sum_segment_r[part] <= s1_sum_segment_r[part];
                end
            end            
        end
        assign res_tmp[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH] = s1_sum_segment_r[part];
    end
endgenerate

always @ (posedge clk) begin
    if (pipe_en1) begin
        s1_isa       <= s0_isa;
        s1_cc_val    <= s0_cc_val;
        s1_flag_bits <= s0_flag_bits;
        s1_vm_id     <= s0_vm_id;
    end
    else begin
        s1_isa       <= s1_isa;
        s1_cc_val    <= s1_cc_val;
        s1_flag_bits <= s1_flag_bits;
        s1_vm_id     <= s1_vm_id;
    end
end
//output
assign res = {s1_isa, s1_cc_val, s1_flag_bits, res_tmp[DATA_WIDTH-1:0]};
assign o_vm_id = s1_vm_id;
//handshake
assign pipe_en0      = pipe_i_valid0 & pipe_i_ready0;
assign pipe_en1      = pipe_i_valid1 & pipe_i_ready1;
assign pipe_i_valid0 = i_valid;
assign pipe_o_ready0 = pipe_i_ready1;
assign pipe_i_valid1 = pipe_o_valid0;
assign pipe_o_ready1 = o_ready;
assign pipe_i_ready0 = !pipe_o_valid0 | pipe_o_ready0;
assign pipe_i_ready1 = !pipe_o_valid1 | pipe_o_ready1;
assign i_ready       = pipe_i_ready0;
assign o_valid       = pipe_o_valid1;
always @ (posedge clk or negedge rstn) begin
    if (!rstn) begin
        pipe_o_valid0 <= 0;
    end
    else if (pipe_i_ready0) begin
        pipe_o_valid0 <= pipe_i_valid0;
    end
    else begin
        pipe_o_valid0 <= pipe_o_valid0;
    end
end
always @ (posedge clk or negedge rstn) begin
    if (!rstn) begin
        pipe_o_valid1 <= 0;
    end
    else if (pipe_i_ready1) begin
        pipe_o_valid1 <= pipe_i_valid1;
    end
    else begin
        pipe_o_valid1 <= pipe_o_valid1;
    end
end



endmodule
