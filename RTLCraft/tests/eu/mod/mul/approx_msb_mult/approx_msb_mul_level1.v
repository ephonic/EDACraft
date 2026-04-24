// +FHDR----------------------------------------------------------------------------
// Project Name  : IC_Design
// Device        : Xilinx
// Author        : HonkW
// Email         : contact@honk.wang
// Website       : honk.wang
// Created On    : 2022/12/16 16:55
// Last Modified : 2023/06/29 20:31
// File Name     : approx_msb_mul_level4.v
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

module approx_msb_mul_level1 #(parameter A_WIDTH=48, B_WIDTH=48, R_WIDTH = 48)
    (
        clk,
        a,
        b,
        en0,
        en1,
        res
    );

    input  clk;
    input  [A_WIDTH-1:0] a;
    input  [B_WIDTH-1:0] b;
    input  en0;
    input  en1;
    output [A_WIDTH+B_WIDTH-1:0] res;

    //localparam	WIDTH 		= A_WIDTH > B_WIDTH ? A_WIDTH : B_WIDTH;
    localparam	WIDTH_ODD	= R_WIDTH % 2;
    localparam	WIDTH_HALF	= (R_WIDTH - WIDTH_ODD) / 2;
    //localparam	H_WIDTH		= WIDTH_HALF + WIDTH_ODD;
    localparam	L_WIDTH		= WIDTH_HALF;
    localparam  A_H_WIDTH   = A_WIDTH-L_WIDTH;
    localparam  B_H_WIDTH   = B_WIDTH-L_WIDTH;
    //localparam	F_WIDTH		= H_WIDTH + L_WIDTH;
    
    wire	[L_WIDTH-1  :0]	a0;
    wire	[A_H_WIDTH-1:0]	a1;
    wire	[L_WIDTH-1  :0]	b0;
    wire	[B_H_WIDTH-1:0]	b1;
    
    
    //				a1		a0
    //x				b1		b0
    //-------------------------
    //	a1b1	a1b0+a0b1	a0b0
    //	a1b0 + a0b1 = (a0+a1)(b0+b1) - a1b1 - a0b0
    assign	{a1, a0} = a;
    assign	{b1, b0} = b;
    
    reg		[L_WIDTH-1  :0]	a0_r1;
    reg		[A_H_WIDTH-1:0]	a1_r1;
    reg		[L_WIDTH-1  :0]	b0_r1;
    reg		[B_H_WIDTH-1:0]	b1_r1;
    
    always @(posedge clk)
    if(en0) begin
    	a0_r1 <= a0;
    	a1_r1 <= a1;
    	b0_r1 <= b0;
    	b1_r1 <= b1;
    end
    
    
    
    
    wire	[A_H_WIDTH+B_H_WIDTH-1:0] a1b1_r1 = a1_r1*b1_r1; //mul24x24(a1,b1);
    wire    [L_WIDTH+B_H_WIDTH  -1:0] a0b1_r1 = a0_r1*b1_r1; //mul24x24(a0,b1);
    wire    [L_WIDTH+A_H_WIDTH  -1:0] a1b0_r1 = a1_r1*b0_r1; //mul24x24(a1,b0);

    reg	[A_H_WIDTH+B_H_WIDTH-1:0] a1b1_r2;
    reg	[L_WIDTH+B_H_WIDTH  -1:0] a0b1_r2;
    reg	[L_WIDTH+A_H_WIDTH  -1:0] a1b0_r2;
    
    always @(posedge clk)
    if(en1) begin
    	a1b1_r2 	<= a1b1_r1;
    	a0b1_r2 	<= a0b1_r1;
    	a1b0_r2 	<= a1b0_r1;
    end
    
    wire	[A_WIDTH+B_WIDTH*2-1:0]	r;
    
    assign r = {a1b1_r2, {(2*L_WIDTH){1'b0}}} + {{a0b1_r2, {(L_WIDTH){1'b0}}}} + {a1b0_r2, {(L_WIDTH){1'b0}}};
    
    assign	res = r;
    
endmodule

