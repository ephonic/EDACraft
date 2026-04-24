module lsb_full_mul_level1(	// 48x48 or similar bits
clk,
a,
b,
en0,
en1,
res
);
parameter	A_WIDTH = 48;
parameter	B_WIDTH = 48;

input	clk;
input	[A_WIDTH-1:0]	a;
input	[B_WIDTH-1:0]	b;
input	en0;
input	en1;
output	[A_WIDTH+B_WIDTH-1:0]	res;

//`include js_zk_func.vh


localparam	WIDTH 		= A_WIDTH > B_WIDTH ? A_WIDTH : B_WIDTH;
localparam	WIDTH_ODD	= WIDTH % 2;
localparam	WIDTH_HALF	= (WIDTH - WIDTH_ODD) / 2;
localparam	H_WIDTH		= WIDTH_HALF + WIDTH_ODD;
localparam	L_WIDTH		= WIDTH_HALF;

localparam	F_WIDTH		= H_WIDTH + 1;

wire	[L_WIDTH-1:0]	a0;
wire	[H_WIDTH-1:0]	a1;
wire	[L_WIDTH-1:0]	b0;
wire	[H_WIDTH-1:0]	b1;


//				a1		a0
//x				b1		b0
//-------------------------
//	a1b1	a1b0+a0b1	a0b0
//	a1b0 + a0b1 = (a0+a1)(b0+b1) - a1b1 - a0b0


assign	{a1, a0} = a;
assign	{b1, b0} = b;
wire	[F_WIDTH-1:0]	a_fold = a0 + a1;
wire	[F_WIDTH-1:0]	b_fold = b0 + b1;

reg		[L_WIDTH-1:0]	a0_r1;
reg		[H_WIDTH-1:0]	a1_r1;
reg		[L_WIDTH-1:0]	b0_r1;
reg		[H_WIDTH-1:0]	b1_r1;
reg		[F_WIDTH-1:0]	a_fold_r1;
reg		[F_WIDTH-1:0]	b_fold_r1;

always @(posedge clk)
if(en0) begin
	a0_r1 <= a0;
	a1_r1 <= a1;
	b0_r1 <= b0;
	b1_r1 <= b1;
	a_fold_r1 <= a_fold;
	b_fold_r1 <= b_fold;
end




wire	[L_WIDTH*2-1:0]	a0b0_r1 = a0_r1*b0_r1; //mul24x24(a0,b0);
wire	[H_WIDTH*2-1:0]	a1b1_r1 = a1_r1*b1_r1; //mul24x24(a1,b1);

wire	[F_WIDTH*2-1:0]	temp0_r1 = a_fold_r1 * b_fold_r1; //mul25x25(a0_a1, b0_b1);

reg	[L_WIDTH*2-1:0]	a0b0_r2;
reg	[H_WIDTH*2-1:0]	a1b1_r2;
reg	[F_WIDTH*2-1:0]	temp0_r2;

always @(posedge clk)
if(en1) begin
	a0b0_r2		<= a0b0_r1;
	a1b1_r2 	<= a1b1_r1;
	temp0_r2	<= temp0_r1;
end

wire	[WIDTH*2-1:0]	r;

assign r = {a1b1_r2, {(2*L_WIDTH){1'b0}}} + {temp0_r2, {(L_WIDTH){1'b0}}} - {a0b0_r2, {(L_WIDTH){1'b0}}} - {a1b1_r2, {(L_WIDTH){1'b0}}} + a0b0_r2;

assign	res = r;

	
	
endmodule
