module js_zk_mul_level3(	//384x384 or similar bits
clk,
rstn,
a,
b,
en0,
en1,
en2,
en3,
en4,
res
);
parameter A_WIDTH = 384;
parameter B_WIDTH = 384;
parameter R_WIDTH = 768;


input	clk;
input	rstn;
input	[A_WIDTH-1:0]	a;
input	[B_WIDTH-1:0]	b;
input	en0;
input	en1;
input	en2;
input	en3;
input	en4;
output	[R_WIDTH-1:0]	res;


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
wire	[F_WIDTH-1:0]	a_fold = a0 + a1;
wire	[F_WIDTH-1:0]	b_fold = b0 + b1;
//				a1		a0
//x				b1		b0
//-------------------------
//	a1b1	a1b0+a0b1	a0b0
//	a1b0 + a0b1 = (a0+a1)(b0+b1) - a1b1 - a0b0

reg	[L_WIDTH-1:0]	a0_r0, b0_r0;
reg	[H_WIDTH-1:0]	a1_r0, b1_r0;
reg	[F_WIDTH-1:0]	a_fold_r0;
reg	[F_WIDTH-1:0]	b_fold_r0;
always @(posedge clk)
if(en0) begin
	{a1_r0, a0_r0} <= a;
	{b1_r0, b0_r0} <= b;
	a_fold_r0 <= a_fold;
	b_fold_r0 <= b_fold;
end

assign	{a1, a0} = a;
assign	{b1, b0} = b;




wire	[L_WIDTH*2-1:0]	a0b0_r3;
wire	[H_WIDTH*2-1:0]	a1b1_r3;
js_zk_mul_level2 #(L_WIDTH, L_WIDTH) u0_mul (
	.clk	(clk), 
	.rstn	(rstn),
	.en0	(en1),
	.en1	(en2),
	.en2	(en3),
	.a		(a0_r0),
	.b		(b0_r0),
	.res	(a0b0_r3));
	
js_zk_mul_level2 #(H_WIDTH, H_WIDTH) u1_mul (
	.clk	(clk), 
	.rstn	(rstn),
	.en0	(en0),
	.en1	(en1),
	.en2	(en2),
	.a		(a1_r0),
	.b		(b1_r0),
	.res	(a1b1_r3));


wire	[F_WIDTH*2-1:0]	temp0_r3;


js_zk_mul_level2 #(F_WIDTH, F_WIDTH) u2_mul (
	.clk	(clk), 
	.rstn	(rstn),
	.en0	(en0),
	.en1	(en1),
	.en2	(en2),
	.a		(a_fold_r0),
	.b		(b_fold_r0),
	.res	(temp0_r3));


reg		[L_WIDTH*2-1:0]	a0b0_r4;
reg		[H_WIDTH*2-1:0]	a1b1_r4;
reg		[F_WIDTH*2-1:0]	temp0_r4;

always @(posedge clk)
if(en3) begin
	a0b0_r4  <= a0b0_r3;
	a1b1_r4  <= a1b1_r3;
	temp0_r4 <= temp0_r3;
end

wire	[WIDTH*2-1:0]	r;

assign r = {({a1b1_r4, {(L_WIDTH){1'b0}}} + temp0_r4-a0b0_r4-a1b1_r4), {(L_WIDTH){1'b0}}} + a0b0_r4;

reg		[R_WIDTH-1:0]	res;
always @(posedge clk)
if(en4)
	res <= r[R_WIDTH-1:0];

endmodule
