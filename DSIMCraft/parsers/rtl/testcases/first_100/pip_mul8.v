// Full-pipelined 8x8 unsigned multiplier
// Uses 2x2 multiplier as the conceptual building block
// 3 pipeline stages: PP generation -> Wallace compression -> Final CPA

module pip_mul8 (clk, rst, a, b, p, valid_out);
  input        clk;
  input        rst;
  input  [7:0] a;
  input  [7:0] b;
  output [15:0] p;
  output       valid_out;

  wire clk, rst;
  wire [7:0] a, b;
  wire [15:0] p;
  wire valid_out;

  reg  [15:0] p;
  reg         valid_out;

  // ──────────────────────────────────────────────
  // Stage 1: Partial Product Generation via 2x2 multipliers
  // ──────────────────────────────────────────────

  // 2x2 multiplier results (bit-level expansion of 2x2 MUL)
  // 2x2 MUL: p[0]=a[0]&b[0], p[1]=a[0]&b[1]^a[1]&b[0],
  //          p[2]=(a[0]&b[1]&a[1]&b[0])^a[1]&b[1]
  //          p[3]=a[0]&a[1]&b[0]&b[1]

  // pp00 = a[1:0] * b[1:0]
  wire pp00_0 = a[0] & b[0];
  wire pp00_1 = (a[0] & b[1]) ^ (a[1] & b[0]);
  wire pp00_2 = ((a[0] & b[1]) & (a[1] & b[0])) ^ (a[1] & b[1]);
  wire pp00_3 = (a[0] & a[1]) & (b[0] & b[1]);

  // pp01 = a[1:0] * b[3:2]  (shift 2)
  wire pp01_0 = a[0] & b[2];
  wire pp01_1 = (a[0] & b[3]) ^ (a[1] & b[2]);
  wire pp01_2 = ((a[0] & b[3]) & (a[1] & b[2])) ^ (a[1] & b[3]);
  wire pp01_3 = (a[0] & a[1]) & (b[2] & b[3]);

  // pp02 = a[1:0] * b[5:4]  (shift 4)
  wire pp02_0 = a[0] & b[4];
  wire pp02_1 = (a[0] & b[5]) ^ (a[1] & b[4]);
  wire pp02_2 = ((a[0] & b[5]) & (a[1] & b[4])) ^ (a[1] & b[5]);
  wire pp02_3 = (a[0] & a[1]) & (b[4] & b[5]);

  // pp03 = a[1:0] * b[7:6]  (shift 6)
  wire pp03_0 = a[0] & b[6];
  wire pp03_1 = (a[0] & b[7]) ^ (a[1] & b[6]);
  wire pp03_2 = ((a[0] & b[7]) & (a[1] & b[6])) ^ (a[1] & b[7]);
  wire pp03_3 = (a[0] & a[1]) & (b[6] & b[7]);

  // pp10 = a[3:2] * b[1:0]  (shift 2)
  wire pp10_0 = a[2] & b[0];
  wire pp10_1 = (a[2] & b[1]) ^ (a[3] & b[0]);
  wire pp10_2 = ((a[2] & b[1]) & (a[3] & b[0])) ^ (a[3] & b[1]);
  wire pp10_3 = (a[2] & a[3]) & (b[0] & b[1]);

  // pp11 = a[3:2] * b[3:2]  (shift 4)
  wire pp11_0 = a[2] & b[2];
  wire pp11_1 = (a[2] & b[3]) ^ (a[3] & b[2]);
  wire pp11_2 = ((a[2] & b[3]) & (a[3] & b[2])) ^ (a[3] & b[3]);
  wire pp11_3 = (a[2] & a[3]) & (b[2] & b[3]);

  // pp12 = a[3:2] * b[5:4]  (shift 6)
  wire pp12_0 = a[2] & b[4];
  wire pp12_1 = (a[2] & b[5]) ^ (a[3] & b[4]);
  wire pp12_2 = ((a[2] & b[5]) & (a[3] & b[4])) ^ (a[3] & b[5]);
  wire pp12_3 = (a[2] & a[3]) & (b[4] & b[5]);

  // pp13 = a[3:2] * b[7:6]  (shift 8)
  wire pp13_0 = a[2] & b[6];
  wire pp13_1 = (a[2] & b[7]) ^ (a[3] & b[6]);
  wire pp13_2 = ((a[2] & b[7]) & (a[3] & b[6])) ^ (a[3] & b[7]);
  wire pp13_3 = (a[2] & a[3]) & (b[6] & b[7]);

  // pp20 = a[5:4] * b[1:0]  (shift 4)
  wire pp20_0 = a[4] & b[0];
  wire pp20_1 = (a[4] & b[1]) ^ (a[5] & b[0]);
  wire pp20_2 = ((a[4] & b[1]) & (a[5] & b[0])) ^ (a[5] & b[1]);
  wire pp20_3 = (a[4] & a[5]) & (b[0] & b[1]);

  // pp21 = a[5:4] * b[3:2]  (shift 6)
  wire pp21_0 = a[4] & b[2];
  wire pp21_1 = (a[4] & b[3]) ^ (a[5] & b[2]);
  wire pp21_2 = ((a[4] & b[3]) & (a[5] & b[2])) ^ (a[5] & b[3]);
  wire pp21_3 = (a[4] & a[5]) & (b[2] & b[3]);

  // pp22 = a[5:4] * b[5:4]  (shift 8)
  wire pp22_0 = a[4] & b[4];
  wire pp22_1 = (a[4] & b[5]) ^ (a[5] & b[4]);
  wire pp22_2 = ((a[4] & b[5]) & (a[5] & b[4])) ^ (a[5] & b[5]);
  wire pp22_3 = (a[4] & a[5]) & (b[4] & b[5]);

  // pp23 = a[5:4] * b[7:6]  (shift 10)
  wire pp23_0 = a[4] & b[6];
  wire pp23_1 = (a[4] & b[7]) ^ (a[5] & b[6]);
  wire pp23_2 = ((a[4] & b[7]) & (a[5] & b[6])) ^ (a[5] & b[7]);
  wire pp23_3 = (a[4] & a[5]) & (b[6] & b[7]);

  // pp30 = a[7:6] * b[1:0]  (shift 6)
  wire pp30_0 = a[6] & b[0];
  wire pp30_1 = (a[6] & b[1]) ^ (a[7] & b[0]);
  wire pp30_2 = ((a[6] & b[1]) & (a[7] & b[0])) ^ (a[7] & b[1]);
  wire pp30_3 = (a[6] & a[7]) & (b[0] & b[1]);

  // pp31 = a[7:6] * b[3:2]  (shift 8)
  wire pp31_0 = a[6] & b[2];
  wire pp31_1 = (a[6] & b[3]) ^ (a[7] & b[2]);
  wire pp31_2 = ((a[6] & b[3]) & (a[7] & b[2])) ^ (a[7] & b[3]);
  wire pp31_3 = (a[6] & a[7]) & (b[2] & b[3]);

  // pp32 = a[7:6] * b[5:4]  (shift 10)
  wire pp32_0 = a[6] & b[4];
  wire pp32_1 = (a[6] & b[5]) ^ (a[7] & b[4]);
  wire pp32_2 = ((a[6] & b[5]) & (a[7] & b[4])) ^ (a[7] & b[5]);
  wire pp32_3 = (a[6] & a[7]) & (b[4] & b[5]);

  // pp33 = a[7:6] * b[7:6]  (shift 12)
  wire pp33_0 = a[6] & b[6];
  wire pp33_1 = (a[6] & b[7]) ^ (a[7] & b[6]);
  wire pp33_2 = ((a[6] & b[7]) & (a[7] & b[6])) ^ (a[7] & b[7]);
  wire pp33_3 = (a[6] & a[7]) & (b[6] & b[7]);

  // Aligned 16-bit partial products
  wire [15:0] pp00_w = {12'b0, pp00_3, pp00_2, pp00_1, pp00_0};
  wire [15:0] pp01_w = {8'b0,  pp01_3, pp01_2, pp01_1, pp01_0, 4'b0};
  wire [15:0] pp02_w = {4'b0,  pp02_3, pp02_2, pp02_1, pp02_0, 8'b0};
  wire [15:0] pp03_w = {      pp03_3, pp03_2, pp03_1, pp03_0, 12'b0};
  wire [15:0] pp10_w = {8'b0,  pp10_3, pp10_2, pp10_1, pp10_0, 4'b0};
  wire [15:0] pp11_w = {4'b0,  pp11_3, pp11_2, pp11_1, pp11_0, 8'b0};
  wire [15:0] pp12_w = {      pp12_3, pp12_2, pp12_1, pp12_0, 12'b0};
  wire [15:0] pp13_w = {pp13_3, pp13_2, pp13_1, pp13_0, 8'b0};
  wire [15:0] pp20_w = {4'b0,  pp20_3, pp20_2, pp20_1, pp20_0, 8'b0};
  wire [15:0] pp21_w = {      pp21_3, pp21_2, pp21_1, pp21_0, 12'b0};
  wire [15:0] pp22_w = {pp22_3, pp22_2, pp22_1, pp22_0, 8'b0};
  wire [15:0] pp23_w = {pp23_3, pp23_2, pp23_1, pp23_0, 4'b0};
  wire [15:0] pp30_w = {      pp30_3, pp30_2, pp30_1, pp30_0, 12'b0};
  wire [15:0] pp31_w = {pp31_3, pp31_2, pp31_1, pp31_0, 8'b0};
  wire [15:0] pp32_w = {pp32_3, pp32_2, pp32_1, pp32_0, 4'b0};
  wire [15:0] pp33_w = {pp33_3, pp33_2, pp33_1, pp33_0, 0};

  // Stage 1 pipeline registers
  reg [15:0] pp00_r, pp01_r, pp02_r, pp03_r;
  reg [15:0] pp10_r, pp11_r, pp12_r, pp13_r;
  reg [15:0] pp20_r, pp21_r, pp22_r, pp23_r;
  reg [15:0] pp30_r, pp31_r, pp32_r, pp33_r;
  reg        valid_s1;

  always @(posedge clk) begin
    if (rst) begin
      pp00_r <= 16'b0; pp01_r <= 16'b0; pp02_r <= 16'b0; pp03_r <= 16'b0;
      pp10_r <= 16'b0; pp11_r <= 16'b0; pp12_r <= 16'b0; pp13_r <= 16'b0;
      pp20_r <= 16'b0; pp21_r <= 16'b0; pp22_r <= 16'b0; pp23_r <= 16'b0;
      pp30_r <= 16'b0; pp31_r <= 16'b0; pp32_r <= 16'b0; pp33_r <= 16'b0;
      valid_s1 <= 1'b0;
    end else begin
      pp00_r <= pp00_w; pp01_r <= pp01_w; pp02_r <= pp02_w; pp03_r <= pp03_w;
      pp10_r <= pp10_w; pp11_r <= pp11_w; pp12_r <= pp12_w; pp13_r <= pp13_w;
      pp20_r <= pp20_w; pp21_r <= pp21_w; pp22_r <= pp22_w; pp23_r <= pp23_w;
      pp30_r <= pp30_w; pp31_r <= pp31_w; pp32_r <= pp32_w; pp33_r <= pp33_w;
      valid_s1 <= 1'b1;
    end
  end

  // ──────────────────────────────────────────────
  // Stage 2: Wallace Tree Compression (16 -> 2)
  // ──────────────────────────────────────────────

  // CSA: s = x^y^z, c = maj(x,y,z) shifted left
  // sum_a, sum_b are the two operands for final adder
  wire [15:0] sum_a, sum_b;

  // Level 1: 16 -> 11 (5 CSAs: 15 inputs -> 10, + 1 leftover)
  wire [15:0] w1_s0 = pp00_r ^ pp01_r ^ pp02_r;
  wire [15:0] w1_c0 = ((pp00_r & pp01_r) | (pp00_r & pp02_r) | (pp01_r & pp02_r)) << 1;
  wire [15:0] w1_s1 = pp03_r ^ pp10_r ^ pp11_r;
  wire [15:0] w1_c1 = ((pp03_r & pp10_r) | (pp03_r & pp11_r) | (pp10_r & pp11_r)) << 1;
  wire [15:0] w1_s2 = pp12_r ^ pp13_r ^ pp20_r;
  wire [15:0] w1_c2 = ((pp12_r & pp13_r) | (pp12_r & pp20_r) | (pp13_r & pp20_r)) << 1;
  wire [15:0] w1_s3 = pp21_r ^ pp22_r ^ pp23_r;
  wire [15:0] w1_c3 = ((pp21_r & pp22_r) | (pp21_r & pp23_r) | (pp22_r & pp23_r)) << 1;
  wire [15:0] w1_s4 = pp30_r ^ pp31_r ^ pp32_r;
  wire [15:0] w1_c4 = ((pp30_r & pp31_r) | (pp30_r & pp32_r) | (pp31_r & pp32_r)) << 1;
  wire [15:0] w1_r0 = pp33_r;

  // Level 2: 11 -> 8 (3 CSAs: 9 -> 6, + 2 leftover)
  wire [15:0] w2_s0 = w1_s0 ^ w1_c0 ^ w1_s1;
  wire [15:0] w2_c0 = ((w1_s0 & w1_c0) | (w1_s0 & w1_s1) | (w1_c0 & w1_s1)) << 1;
  wire [15:0] w2_s1 = w1_c1 ^ w1_s2 ^ w1_c2;
  wire [15:0] w2_c1 = ((w1_c1 & w1_s2) | (w1_c1 & w1_c2) | (w1_s2 & w1_c2)) << 1;
  wire [15:0] w2_s2 = w1_s3 ^ w1_c3 ^ w1_s4;
  wire [15:0] w2_c2 = ((w1_s3 & w1_c3) | (w1_s3 & w1_s4) | (w1_c3 & w1_s4)) << 1;
  wire [15:0] w2_r0 = w1_c4;
  wire [15:0] w2_r1 = w1_r0;

  // Level 3: 8 -> 5 (2 CSAs: 6 -> 4, + 2 leftover)
  wire [15:0] w3_s0 = w2_s0 ^ w2_c0 ^ w2_s1;
  wire [15:0] w3_c0 = ((w2_s0 & w2_c0) | (w2_s0 & w2_s1) | (w2_c0 & w2_s1)) << 1;
  wire [15:0] w3_s1 = w2_c1 ^ w2_s2 ^ w2_c2;
  wire [15:0] w3_c1 = ((w2_c1 & w2_s2) | (w2_c1 & w2_c2) | (w2_s2 & w2_c2)) << 1;
  wire [15:0] w3_r0 = w2_r0;
  wire [15:0] w3_r1 = w2_r1;

  // Level 4: 5 -> 3 (1 CSA: 3 -> 2, + 2 leftover)
  wire [15:0] w4_s0 = w3_s0 ^ w3_c0 ^ w3_s1;
  wire [15:0] w4_c0 = ((w3_s0 & w3_c0) | (w3_s0 & w3_s1) | (w3_c0 & w3_s1)) << 1;
  wire [15:0] w4_r0 = w3_c1;
  wire [15:0] w4_r1 = w3_r0;
  wire [15:0] w4_r2 = w3_r1;

  // Level 5: 3 -> 2
  wire [15:0] w5_s0 = w4_s0 ^ w4_c0 ^ w4_r0;
  wire [15:0] w5_c0 = ((w4_s0 & w4_c0) | (w4_s0 & w4_r0) | (w4_c0 & w4_r0)) << 1;

  // Combine remaining into two operands
  assign sum_a = w5_s0 + w4_r1;
  assign sum_b = w5_c0 + w4_r2;

  // Stage 2 pipeline registers
  reg [15:0] sum_a_r, sum_b_r;
  reg        valid_s2;

  always @(posedge clk) begin
    if (rst) begin
      sum_a_r <= 16'b0;
      sum_b_r <= 16'b0;
      valid_s2 <= 1'b0;
    end else begin
      sum_a_r <= sum_a;
      sum_b_r <= sum_b;
      valid_s2 <= valid_s1;
    end
  end

  // ──────────────────────────────────────────────
  // Stage 3: Final Carry-Propagate Adder
  // ──────────────────────────────────────────────
  wire [15:0] result = sum_a_r + sum_b_r;

  // Output pipeline register
  always @(posedge clk) begin
    if (rst) begin
      p         <= 16'b0;
      valid_out <= 1'b0;
    end else begin
      p         <= result;
      valid_out <= valid_s2;
    end
  end

endmodule
