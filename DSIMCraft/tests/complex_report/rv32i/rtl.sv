// single-cycle RV32I core (integer subset) -- dsim complexity stress
`timescale 1ns/1ps
module rv32i_core (
    input  wire        clk,
    input  wire        rst_n,
    output wire [31:0] dbg_pc,
    output reg  [31:0] dbg0, dbg1, dbg2, dbg3, dbg4, dbg5, dbg6, dbg7,
    output reg         halted,
    output reg  [31:0] retire     // retired instruction count
);
    localparam IMEM_WORDS = 64;   // 0x000-0x0FF
    localparam DMEM_WORDS = 64;   // 0x100-0x1FF

    reg [31:0] imem [0:IMEM_WORDS-1];
    reg [31:0] dmem [0:DMEM_WORDS-1];
    reg [31:0] rf   [0:31];

    initial begin
`include "imem.sv"
    end

    reg [31:0] pc;
    assign dbg_pc = pc;

    // fetch
    wire [31:0] instr = imem[pc[7:2]];

    // decode fields
    wire [6:0] op  = instr[6:0];
    wire [4:0] rd  = instr[11:7];
    wire [2:0] f3  = instr[14:12];
    wire [4:0] rs1 = instr[19:15];
    wire [4:0] rs2 = instr[24:20];
    wire [6:0] f7  = instr[31:25];

    // register file read (x0 = 0), combinational
    wire [31:0] rs1v = (rs1 == 5'd0) ? 32'd0 : rf[rs1];
    wire [31:0] rs2v = (rs2 == 5'd0) ? 32'd0 : rf[rs2];

    // immediates
    wire [31:0] imm_i = {{20{instr[31]}}, instr[31:20]};
    wire [31:0] imm_s = {{20{instr[31]}}, instr[31:25], instr[11:7]};
    wire [31:0] imm_b = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};
    wire [31:0] imm_u = {instr[31:12], 12'd0};
    wire [31:0] imm_j = {{11{instr[31]}}, instr[31], instr[19:12], instr[20], instr[30:21], 1'b0};

    // ALU
    reg [31:0] alu_r;
    always_comb begin
        unique case (op)
            7'b0110011: begin // OP
                unique case (f3)
                    3'b000: alu_r = f7[5] ? (rs1v - rs2v) : (rs1v + rs2v);
                    3'b001: alu_r = rs1v << rs2v[4:0];
                    3'b010: alu_r = {31'd0, $signed(rs1v) < $signed(rs2v)};
                    3'b011: alu_r = {31'd0, rs1v < rs2v};
                    3'b100: alu_r = rs1v ^ rs2v;
                    3'b101: alu_r = f7[5] ? ($signed(rs1v) >>> rs2v[4:0]) : (rs1v >> rs2v[4:0]);
                    3'b110: alu_r = rs1v | rs2v;
                    3'b111: alu_r = rs1v & rs2v;
                endcase
            end
            7'b0010011: begin // OP-IMM
                unique case (f3)
                    3'b000: alu_r = rs1v + imm_i;
                    3'b010: alu_r = {31'd0, $signed(rs1v) < $signed(imm_i)};
                    3'b011: alu_r = {31'd0, rs1v < imm_i};
                    3'b100: alu_r = rs1v ^ imm_i;
                    3'b110: alu_r = rs1v | imm_i;
                    3'b111: alu_r = rs1v & imm_i;
                    3'b001: alu_r = rs1v << instr[24:20];
                    3'b101: alu_r = instr[30] ? ($signed(rs1v) >>> instr[24:20]) : (rs1v >> instr[24:20]);
                endcase
            end
            7'b0110111: alu_r = imm_u;                    // LUI
            7'b0010111: alu_r = pc + imm_u;               // AUIPC
            default:    alu_r = 32'd0;
        endcase
    end

    // branch resolve
    reg branch_t;
    always_comb begin
        branch_t = 1'b0;
        case (f3)
            3'b000: branch_t = (rs1v == rs2v);
            3'b001: branch_t = (rs1v != rs2v);
            3'b100: branch_t = ($signed(rs1v) <  $signed(rs2v));
            3'b101: branch_t = ($signed(rs1v) >= $signed(rs2v));
            3'b110: branch_t = (rs1v <  rs2v);
            3'b111: branch_t = (rs1v >= rs2v);
            default: branch_t = 1'b0;
        endcase
    end

    // load path
    wire [31:0] laddr = rs1v + imm_i;
    wire [31:0] dw    = dmem[laddr[7:2]];
    // byte/half extraction for sub-word loads
    wire [7:0]  lb0 = dw[7:0],  lb1 = dw[15:8],  lb2 = dw[23:16], lb3 = dw[31:24];
    wire [15:0] lh0 = dw[15:0], lh1 = dw[31:16];
    reg [31:0] ldata2;
    always_comb begin
        ldata2 = 32'd0;
        if (laddr[31:8] == 24'h01) begin
            if (f3 == 3'b010) ldata2 = dw;                                   // LW
            else if (f3 == 3'b000) begin                                      // LB
                case (laddr[1:0])
                    2'd0: ldata2 = {{24{lb0[7]}}, lb0};
                    2'd1: ldata2 = {{24{lb1[7]}}, lb1};
                    2'd2: ldata2 = {{24{lb2[7]}}, lb2};
                    2'd3: ldata2 = {{24{lb3[7]}}, lb3};
                endcase
            end else if (f3 == 3'b100) begin                                  // LBU
                case (laddr[1:0])
                    2'd0: ldata2 = {24'd0, lb0};
                    2'd1: ldata2 = {24'd0, lb1};
                    2'd2: ldata2 = {24'd0, lb2};
                    2'd3: ldata2 = {24'd0, lb3};
                endcase
            end else if (f3 == 3'b001) begin                                  // LH
                case (laddr[1:0])
                    2'd0: ldata2 = {{16{lh0[15]}}, lh0};
                    2'd2: ldata2 = {{16{lh1[15]}}, lh1};
                    default: ldata2 = 32'd0;
                endcase
            end else if (f3 == 3'b101) begin                                  // LHU
                case (laddr[1:0])
                    2'd0: ldata2 = {16'd0, lh0};
                    2'd2: ldata2 = {16'd0, lh1};
                    default: ldata2 = 32'd0;
                endcase
            end
        end
    end

    // writeback select
    reg [31:0] wdata;
    always_comb begin
        unique case (op)
            7'b0000011: wdata = ldata2;                       // LOAD
            7'b1101111,
            7'b1100111: wdata = pc + 32'd4;                   // JAL/JALR
            default:    wdata = alu_r;
        endcase
    end

    // register write
    always_ff @(posedge clk) begin
        if (rst_n && rd != 5'd0) begin
            if (op == 7'b0110011 || op == 7'b0010011 || op == 7'b0110111 ||
                op == 7'b0010111 || op == 7'b1101111 || op == 7'b1100111 ||
                op == 7'b0000011)
                rf[rd] <= wdata;
        end
    end

    // store path
    wire [31:0] saddr = rs1v + imm_s;
    reg  [31:0] oldw;
    always_comb begin
        oldw = (saddr[31:8] == 24'h01) ? dmem[saddr[7:2]] : 32'd0;
    end
    always_ff @(posedge clk) begin
        if (rst_n && op == 7'b0100011) begin
            if (saddr[31:8] == 24'h01) begin
                case (f3)
                    3'b010: dmem[saddr[7:2]] <= rs2v;                       // SW
                    3'b001: begin                                           // SH
                        case (saddr[1])
                            1'b0: dmem[saddr[7:2]] <= {oldw[31:16], rs2v[15:0]};
                            1'b1: dmem[saddr[7:2]] <= {rs2v[15:0], oldw[15:0]};
                        endcase
                    end
                    3'b000: begin                                           // SB
                        case (saddr[1:0])
                            2'd0: dmem[saddr[7:2]] <= {oldw[31:8], rs2v[7:0]};
                            2'd1: dmem[saddr[7:2]] <= {oldw[31:16], rs2v[7:0], oldw[7:0]};
                            2'd2: dmem[saddr[7:2]] <= {oldw[31:24], rs2v[7:0], oldw[15:8]};
                            2'd3: dmem[saddr[7:2]] <= {rs2v[7:0], oldw[23:0]};
                        endcase
                    end
                    default: ;
                endcase
            end else if (saddr[31:8] == 24'h02) begin                       // dbg latches
                case (saddr[4:2])
                    3'd0: dbg0 <= rs2v;
                    3'd1: dbg1 <= rs2v;
                    3'd2: dbg2 <= rs2v;
                    3'd3: dbg3 <= rs2v;
                    3'd4: dbg4 <= rs2v;
                    3'd5: dbg5 <= rs2v;
                    3'd6: dbg6 <= rs2v;
                    3'd7: dbg7 <= rs2v;
                endcase
            end
        end
    end

    // next pc + halt on self-loop (jal r0, 0 = 0x0000006F)
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pc      <= 32'd0;
            halted  <= 1'b0;
            retire  <= 32'd0;
        end else begin
            retire <= retire + 32'd1;
            if (instr == 32'h0000006F) begin
                halted <= 1'b1;
            end else begin
                unique case (op)
                    7'b1101111: pc <= pc + imm_j;                        // JAL
                    7'b1100111: pc <= (rs1v + imm_i) & 32'hFFFFFFFE;     // JALR
                    7'b1100011: pc <= branch_t ? (pc + imm_b) : (pc + 32'd4);
                    default:    pc <= pc + 32'd4;
                endcase
            end
        end
    end
endmodule
