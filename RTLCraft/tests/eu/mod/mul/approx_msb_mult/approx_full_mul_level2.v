module approx_full_mul_level2(	//96x96 or similar bits
clk,
rstn,
a,
b,
en0,
en1,
en2,
res
);


parameter	A_WIDTH = 96;
parameter	B_WIDTH = 96;

input	clk;
input	rstn;
input	[A_WIDTH-1:0]	a;
input	[B_WIDTH-1:0]	b;
input	en0;
input	en1;
input	en2;
output	[A_WIDTH+B_WIDTH-1:0]	res;


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

wire	[L_WIDTH*2-1:0]	a0b0_r2;
wire	[H_WIDTH*2-1:0]	a1b1_r2;
approx_full_mul_level1 #(L_WIDTH, L_WIDTH) u0_mul (
	.clk	(clk),
	.en0	(en0),
	.en1	(en1),
	.a		(a0),
	.b		(b0),
	.res	(a0b0_r2));
	
approx_full_mul_level1 #(H_WIDTH, H_WIDTH) u1_mul (
	.clk	(clk),
	.en0	(en0),
	.en1	(en1),
	.a		(a1),
	.b		(b1),
	.res	(a1b1_r2));

wire	[F_WIDTH-1:0]	a_fold = a0 + a1;
wire	[F_WIDTH-1:0]	b_fold = b0 + b1;

wire	[F_WIDTH*2-1:0]	temp0_r2;

approx_full_mul_level1 #(F_WIDTH, F_WIDTH) u2_mul (
	.clk	(clk),
	.en0	(en0),
	.en1	(en1),
	.a		(a_fold),
	.b		(b_fold),
	.res	(temp0_r2));

reg		[L_WIDTH*2-1:0]	a0b0_r3;
reg		[H_WIDTH*2-1:0]	a1b1_r3;
reg		[F_WIDTH*2-1:0]	temp0_r3;
always @(posedge clk)
if(en2) begin
	a0b0_r3	<= a0b0_r2;
	a1b1_r3	<= a1b1_r2;
	temp0_r3	<= temp0_r2;

end

wire	[WIDTH*2-1:0]	r;

assign r = {a1b1_r3, {(2*L_WIDTH){1'b0}}} + {temp0_r3, {(L_WIDTH){1'b0}}} - {a0b0_r3, {(L_WIDTH){1'b0}}} - {a1b1_r3, {(L_WIDTH){1'b0}}} + a0b0_r3;

assign	res = r;


endmodule
