// 5-stage pipelined RV32I: EX forwarding (EX/MEM + MEM/WB), load-use stall,
// branch/jump resolve in EX with 2-cycle flush, RF write-first bypass in ID
`timescale 1ns/1ps
module rv32i5 (
    input  wire        clk,
    input  wire        rst_n,
    output reg  [31:0] dbg0, dbg1, dbg2, dbg3, dbg4, dbg5, dbg6, dbg7,
    output reg         halted,
    output reg  [31:0] retire
);
    localparam IMEM_WORDS = 64;   // 0x000-0x0FF
    localparam DMEM_WORDS = 64;   // 0x100-0x1FF

    reg [31:0] imem [0:IMEM_WORDS-1];
    reg [31:0] dmem [0:DMEM_WORDS-1];
    reg [31:0] rf   [0:31];
    initial begin
`include "imem.sv"
    end

    // ---------------- IF ----------------
    reg [31:0] pc;
    wire [31:0] if_instr = imem[pc[7:2]];
    wire halt_insn = (if_instr == 32'h0000006F);

    // pipeline control
    wire stall;      // load-use hazard: freeze IF/ID + PC, bubble ID/EX
    wire redirect;   // taken branch/jump in EX: flush IF/ID + ID/EX
    wire [31:0] redirect_target;

    // IF/ID
    reg        id_valid;
    reg [31:0] id_instr, id_pc;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            id_valid <= 1'b0; id_instr <= 32'd0; id_pc <= 32'd0; halted <= 1'b0;
        end else begin
            if (redirect) begin
                id_valid <= 1'b0;
            end else if (!stall && !halted) begin
                id_valid <= 1'b1;
                id_instr <= if_instr;
                id_pc    <= pc;
            end
            // halt when self-loop instruction reaches ID (after any EX redirect this cycle)
            if (id_valid && (id_instr == 32'h0000006F) && !redirect) halted <= 1'b1;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) pc <= 32'd0;
        else if (redirect)          pc <= redirect_target;
        else if (!stall && !halted) pc <= pc + 32'd4;
    end

    // ---------------- ID ----------------
    wire [6:0] id_op  = id_instr[6:0];
    wire [4:0] id_rs1 = id_instr[19:15];
    wire [4:0] id_rs2 = id_instr[24:20];
    wire [4:0] id_rd  = id_instr[11:7];

    // which sources are read (for hazard)
    wire id_uses_rs1 = (id_op == 7'b0110011) || (id_op == 7'b0010011) ||
                       (id_op == 7'b0000011) || (id_op == 7'b1100011) ||
                       (id_op == 7'b1100111);
    wire id_uses_rs2 = (id_op == 7'b0110011) || (id_op == 7'b1100011) ||
                       (id_op == 7'b0100011);

    // ID/EX (pipeline reg)
    reg        ex_valid;
    reg [31:0] ex_instr, ex_pc;
    reg [31:0] ex_rs1v, ex_rs2v;
    wire       ex_is_load = (ex_instr[6:0] == 7'b0000011);

    // load-use hazard detect (ID vs EX)
    assign stall = id_valid && ex_valid && ex_is_load && (ex_instr[11:7] != 5'd0) &&
                   ((id_uses_rs1 && (ex_instr[11:7] == id_rs1)) ||
                    (id_uses_rs2 && (ex_instr[11:7] == id_rs2)));

    // RF read with WB write-first bypass
    wire        wb_we;
    wire [4:0]  wb_rd;
    wire [31:0] wb_wdata;
    wire [31:0] id_rs1v = (wb_we && wb_rd != 5'd0 && wb_rd == id_rs1) ? wb_wdata :
                          (id_rs1 == 5'd0) ? 32'd0 : rf[id_rs1];
    wire [31:0] id_rs2v = (wb_we && wb_rd != 5'd0 && wb_rd == id_rs2) ? wb_wdata :
                          (id_rs2 == 5'd0) ? 32'd0 : rf[id_rs2];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ex_valid <= 1'b0; ex_instr <= 32'd0; ex_pc <= 32'd0;
            ex_rs1v <= 32'd0; ex_rs2v <= 32'd0;
        end else if (stall || redirect) begin
            ex_valid <= 1'b0;                    // bubble
        end else begin
            ex_valid <= id_valid;
            ex_instr <= id_instr; ex_pc <= id_pc;
            ex_rs1v  <= id_rs1v;  ex_rs2v <= id_rs2v;
        end
    end

    // ---------------- EX ----------------
    wire [6:0] ex_op = ex_instr[6:0];
    wire [2:0] ex_f3 = ex_instr[14:12];
    wire [6:0] ex_f7 = ex_instr[31:25];
    wire [4:0] ex_rs1 = ex_instr[19:15];
    wire [4:0] ex_rs2 = ex_instr[24:20];
    wire [4:0] ex_rd  = ex_instr[11:7];

    // EX/MEM pipeline reg (for forwarding)
    reg        mem_valid;
    reg [31:0] mem_instr, mem_result, mem_store;
    wire [4:0] mem_rd  = mem_instr[11:7];
    wire       mem_rf_we = (mem_instr[6:0] == 7'b0110011) || (mem_instr[6:0] == 7'b0010011) ||
                           (mem_instr[6:0] == 7'b0110111) || (mem_instr[6:0] == 7'b0010111) ||
                           (mem_instr[6:0] == 7'b1101111) || (mem_instr[6:0] == 7'b1100111) ||
                           (mem_instr[6:0] == 7'b0000011);
    wire       mem_is_load = (mem_instr[6:0] == 7'b0000011);
    wire       mem_is_store= (mem_instr[6:0] == 7'b0100011);

    // MEM/WB pipeline reg
    reg        wbb_valid;
    reg [31:0] wbb_instr, wbb_result;
    assign wb_rd    = wbb_instr[11:7];
    assign wb_we    = wbb_valid && ((wbb_instr[6:0] == 7'b0110011) || (wbb_instr[6:0] == 7'b0010011) ||
                       (wbb_instr[6:0] == 7'b0110111) || (wbb_instr[6:0] == 7'b0010111) ||
                       (wbb_instr[6:0] == 7'b1101111) || (wbb_instr[6:0] == 7'b1100111) ||
                       (wbb_instr[6:0] == 7'b0000011));
    assign wb_wdata = wbb_result;

    // ---------------- MEM ----------------
    wire [31:0] m_addr = mem_result;
    wire [31:0] m_dw   = dmem[m_addr[7:2]];
    wire        m_in_dmem = (m_addr[31:8] == 24'h01);
    wire        m_in_dbg  = (m_addr[31:8] == 24'h02);

    // load extension (hoisted: referenced by EX/MEM forwarding)
    wire [7:0]  lb0 = m_dw[7:0],  lb1 = m_dw[15:8],  lb2 = m_dw[23:16], lb3 = m_dw[31:24];
    wire [15:0] lh0 = m_dw[15:0], lh1 = m_dw[31:16];
    reg [31:0] m_ldata;
    always_comb begin
        m_ldata = 32'd0;
        if (m_in_dmem) begin
            unique case (mem_instr[14:12])
                3'b010: m_ldata = m_dw;
                3'b000: begin
                    unique case (m_addr[1:0])
                        2'd0: m_ldata = {{24{lb0[7]}}, lb0};
                        2'd1: m_ldata = {{24{lb1[7]}}, lb1};
                        2'd2: m_ldata = {{24{lb2[7]}}, lb2};
                        2'd3: m_ldata = {{24{lb3[7]}}, lb3};
                    endcase
                end
                3'b100: begin
                    unique case (m_addr[1:0])
                        2'd0: m_ldata = {24'd0, lb0};
                        2'd1: m_ldata = {24'd0, lb1};
                        2'd2: m_ldata = {24'd0, lb2};
                        2'd3: m_ldata = {24'd0, lb3};
                    endcase
                end
                3'b001: m_ldata = m_addr[1] ? {{16{lh1[15]}}, lh1} : {{16{lh0[15]}}, lh0};
                3'b101: m_ldata = m_addr[1] ? {16'd0, lh1} : {16'd0, lh0};
                default: ;
            endcase
        end
    end

    // forwarding: EX/MEM carries loads' memory data combinationally (m_ldata)
    wire exm_fwd_ok = mem_valid && mem_rf_we && (mem_rd != 5'd0);
    wire mwb_fwd_ok = wb_we && (wb_rd != 5'd0);
    wire [31:0] mem_fwd_val = mem_is_load ? m_ldata : mem_result;

    wire [31:0] fw1 = exm_fwd_ok && (mem_rd == ex_rs1) ? mem_fwd_val :
                      mwb_fwd_ok && (wb_rd  == ex_rs1) ? wb_wdata : ex_rs1v;
    wire [31:0] fw2 = exm_fwd_ok && (mem_rd == ex_rs2) ? mem_fwd_val :
                      mwb_fwd_ok && (wb_rd  == ex_rs2) ? wb_wdata : ex_rs2v;

    wire [31:0] imm_i = {{20{ex_instr[31]}}, ex_instr[31:20]};
    wire [31:0] imm_s = {{20{ex_instr[31]}}, ex_instr[31:25], ex_instr[11:7]};
    wire [31:0] imm_b = {{19{ex_instr[31]}}, ex_instr[31], ex_instr[7], ex_instr[30:25], ex_instr[11:8], 1'b0};
    wire [31:0] imm_u = {ex_instr[31:12], 12'd0};
    wire [31:0] imm_j = {{11{ex_instr[31]}}, ex_instr[31], ex_instr[19:12], ex_instr[20], ex_instr[30:21], 1'b0};

    reg [31:0] alu_r;
    always_comb begin
        unique case (ex_op)
            7'b0110011: begin
                unique case (ex_f3)
                    3'b000: alu_r = ex_f7[5] ? (fw1 - fw2) : (fw1 + fw2);
                    3'b001: alu_r = fw1 << fw2[4:0];
                    3'b010: alu_r = {31'd0, $signed(fw1) < $signed(fw2)};
                    3'b011: alu_r = {31'd0, fw1 < fw2};
                    3'b100: alu_r = fw1 ^ fw2;
                    3'b101: begin
                        if (ex_f7[5]) alu_r = $signed(fw1) >>> fw2[4:0];  // ternary form hits dsim >>> bug
                        else          alu_r = fw1 >> fw2[4:0];
                    end
                    3'b110: alu_r = fw1 | fw2;
                    3'b111: alu_r = fw1 & fw2;
                endcase
            end
            7'b0010011: begin
                unique case (ex_f3)
                    3'b000: alu_r = fw1 + imm_i;
                    3'b010: alu_r = {31'd0, $signed(fw1) < $signed(imm_i)};
                    3'b011: alu_r = {31'd0, fw1 < imm_i};
                    3'b100: alu_r = fw1 ^ imm_i;
                    3'b110: alu_r = fw1 | imm_i;
                    3'b111: alu_r = fw1 & imm_i;
                    3'b001: alu_r = fw1 << ex_instr[24:20];
                    3'b101: begin
                        if (ex_instr[30]) alu_r = $signed(fw1) >>> ex_instr[24:20]; // dsim >>> ternary bug workaround
                        else             alu_r = fw1 >> ex_instr[24:20];
                    end
                endcase
            end
            7'b0110111: alu_r = imm_u;
            7'b0010111: alu_r = ex_pc + imm_u;
            7'b0000011: alu_r = fw1 + imm_i;       // load address
            7'b0100011: alu_r = fw1 + imm_s;       // store address
            default:    alu_r = fw1 + imm_i;
        endcase
    end

    // branch resolve
    reg branch_t;
    always_comb begin
        case (ex_f3)
            3'b000: branch_t = (fw1 == fw2);
            3'b001: branch_t = (fw1 != fw2);
            3'b100: branch_t = ($signed(fw1) <  $signed(fw2));
            3'b101: branch_t = ($signed(fw1) >= $signed(fw2));
            3'b110: branch_t = (fw1 <  fw2);
            3'b111: branch_t = (fw1 >= fw2);
            default: branch_t = 1'b0;
        endcase
    end

    wire ex_is_br  = (ex_op == 7'b1100011);
    wire ex_is_jal = (ex_op == 7'b1101111);
    wire ex_is_jr  = (ex_op == 7'b1100111);

    assign redirect = ex_valid && (ex_is_jal || ex_is_jr || (ex_is_br && branch_t));
    assign redirect_target = ex_is_jr ? ((fw1 + imm_i) & 32'hFFFFFFFE) :
                             ex_is_jal ? (ex_pc + imm_j) : (ex_pc + imm_b);

    // EX/MEM register
    reg [31:0] ex_c_result;   // value to carry for rf writeback (not load)
    always_comb begin
        unique case (ex_op)
            7'b1101111, 7'b1100111: ex_c_result = ex_pc + 32'd4;   // link
            7'b0000011, 7'b0100011: ex_c_result = alu_r;           // address
            default:               ex_c_result = alu_r;
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mem_valid <= 1'b0; mem_instr <= 32'd0; mem_result <= 32'd0; mem_store <= 32'd0;
        end else begin
            mem_valid  <= ex_valid;
            mem_instr  <= ex_instr;
            mem_result <= ex_c_result;
            mem_store  <= fw2;                     // store data (forwarded)
        end
    end

    // store lane merge
    reg [31:0] m_wdata;
    always_comb begin
        unique case (mem_instr[14:12])
            3'b010: m_wdata = mem_store;
            3'b001: m_wdata = (m_addr[1]) ? {mem_store[15:0], m_dw[15:0]}
                                          : {m_dw[31:16], mem_store[15:0]};
            3'b000: begin
                unique case (m_addr[1:0])
                    2'd0: m_wdata = {m_dw[31:8],  mem_store[7:0]};
                    2'd1: m_wdata = {m_dw[31:16], mem_store[7:0], m_dw[7:0]};
                    2'd2: m_wdata = {m_dw[31:24], mem_store[7:0], m_dw[15:8]};
                    2'd3: m_wdata = {mem_store[7:0], m_dw[23:0]};
                endcase
            end
            default: m_wdata = mem_store;
        endcase
    end

    // load extension
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dbg0 <= 0; dbg1 <= 0; dbg2 <= 0; dbg3 <= 0;
            dbg4 <= 0; dbg5 <= 0; dbg6 <= 0; dbg7 <= 0;
        end else if (mem_valid && mem_is_store) begin
            if (m_in_dmem) dmem[m_addr[7:2]] <= m_wdata;
            else if (m_in_dbg) begin
                unique case (m_addr[4:2])
                    3'd0: dbg0 <= mem_store;
                    3'd1: dbg1 <= mem_store;
                    3'd2: dbg2 <= mem_store;
                    3'd3: dbg3 <= mem_store;
                    3'd4: dbg4 <= mem_store;
                    3'd5: dbg5 <= mem_store;
                    3'd6: dbg6 <= mem_store;
                    3'd7: dbg7 <= mem_store;
                endcase
            end
        end
    end

    // MEM/WB register: loads substitute memory data
    wire [31:0] wb_val = mem_is_load ? m_ldata : mem_result;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wbb_valid <= 1'b0; wbb_instr <= 32'd0; wbb_result <= 32'd0;
        end else begin
            wbb_valid  <= mem_valid;
            wbb_instr  <= mem_instr;
            wbb_result <= wb_val;
        end
    end

    // ---------------- WB ----------------
    always_ff @(posedge clk) begin
        if (rst_n && wb_we && wb_rd != 5'd0)
            rf[wb_rd] <= wb_wdata;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) retire <= 32'd0;
        else if (wbb_valid && wbb_instr != 32'h0000006F) retire <= retire + 32'd1;
    end
endmodule
