// +FHDR----------------------------------------------------------------------------
// Project Name  : IC_Design
// Device        : Xilinx
// Author        : HonkW
// Email         : contact@honk.wang
// Website       : honk.wang
// Created On    : 2022/12/16 17:24
// Last Modified : 2023/06/29 20:02
// File Name     : approx_msb_mul_level2.v
// Description   :
//         
// Copyright (c) 2022 NB Co.,Ltd..
// ALL RIGHTS RESERVED
// 
// ---------------------------------------------------------------------------------
// Modification History:
// Date         By              Version                 Change Description
// ---------------------------------------------------------------------------------
// 2022/12/16   HonkW           1.0                     Original
// -FHDR----------------------------------------------------------------------------

module lsb_half_mul_level2 #(parameter A_WIDTH=96, B_WIDTH=96)
    (
        clk,
        rst_n,
        a,
        b,
        en0,
        en1,
        en2,
        res
    );
    localparam	WIDTH 		= A_WIDTH > B_WIDTH ? A_WIDTH : B_WIDTH;
    localparam	WIDTH_ODD	= WIDTH % 2;
    localparam	WIDTH_HALF	= (WIDTH - WIDTH_ODD) / 2;
    localparam	H_WIDTH		= WIDTH_HALF;
    localparam	L_WIDTH		= WIDTH_HALF + WIDTH_ODD;
    
    localparam	F_WIDTH		= H_WIDTH + L_WIDTH;

    input	clk;
    input	rst_n;
    input	[A_WIDTH-1:0]	a;
    input	[B_WIDTH-1:0]	b;
    input	en0;
    input	en1;
    input	en2;
    output	[A_WIDTH+B_WIDTH-1:0]	res;
    
    
    
    
    
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
    
    wire	[F_WIDTH-1 :0]	a0b1_r2;
    wire	[F_WIDTH-1 :0]	a1b0_r2;
    lsb_half_mul_level1 #(L_WIDTH, H_WIDTH) u0_mul (
    	.clk	(clk),
    	.en0	(en0),
    	.en1	(en1),
    	.a		(a0),
    	.b		(b1),
    	.res	(a0b1_r2));
    	
    lsb_half_mul_level1 #(H_WIDTH, L_WIDTH) u1_mul (
    	.clk	(clk),
    	.en0	(en0),
    	.en1	(en1),
    	.a		(a1),
    	.b		(b0),
    	.res	(a1b0_r2));
    
    
    wire	[L_WIDTH*2-1:0]	a0b0_r2;
    
    lsb_full_mul_level1 #(L_WIDTH, L_WIDTH) u2_mul (
    	.clk	(clk),
    	.en0	(en0),
    	.en1	(en1),
    	.a		(a0),
    	.b		(b0),
    	.res	(a0b0_r2));
    
    reg		[F_WIDTH-1:0]	a0b1_r3;
    reg		[F_WIDTH-1:0]	a1b0_r3;
    reg		[L_WIDTH*2-1:0]	a0b0_r3;
    always @(posedge clk)
    if(en2) begin
    	a0b1_r3	<= a0b1_r2;
    	a1b0_r3	<= a1b0_r2;
    	a0b0_r3	<= a0b0_r2;
    end
    
    wire	[WIDTH*2-1:0]	r;
    
    assign r = a0b0_r3 + {a0b1_r3, {(L_WIDTH){1'b0}}} + {a1b0_r3, {(L_WIDTH){1'b0}}};
    
    assign	res = r;

endmodule

