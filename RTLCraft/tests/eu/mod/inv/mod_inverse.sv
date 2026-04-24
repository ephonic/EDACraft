// `define MODULU_LENGTH 32   //384 actually
// This module is for zk_poly_div
module mod_inverse #(parameter MODULU_LENGTH = 384)(
    input                          clk,
    input                          rstn,
    input                          go,
    output                         valid,
    input      [MODULU_LENGTH-1:0] prime_q,
    input      [MODULU_LENGTH-1:0] a,//the number needed to get its inverse
    output     [MODULU_LENGTH-1:0] R //a's modular inverse
);
//initial:a->u,prime_q->v
//initial:1->x,0->y
wire [MODULU_LENGTH-1:0] u;
wire [MODULU_LENGTH-1:0] v;
wire [MODULU_LENGTH:0]   u_v_minus_result;
wire [MODULU_LENGTH:0]   v_u_minus_result;
wire [MODULU_LENGTH-1:0] u_or_divide_2;
wire [MODULU_LENGTH-1:0] v_or_divide_2;
wire u_v_final_select;
wire v_u_final_select;
reg  [MODULU_LENGTH-1:0] new_u;
reg  [MODULU_LENGTH-1:0] new_v;
reg  [MODULU_LENGTH-1:0] q_reg;//keep the prime_q
wire [MODULU_LENGTH-1:0] x;
wire [MODULU_LENGTH-1:0] y;
wire [MODULU_LENGTH-1:0] result_x;
wire [MODULU_LENGTH-1:0] result_y;
reg  [MODULU_LENGTH-1:0] new_x;
reg  [MODULU_LENGTH-1:0] new_y;
wire [MODULU_LENGTH:0]   x_y_minus_result;//avoid overflow
wire [MODULU_LENGTH-1:0] x_or_minus_y;
wire [MODULU_LENGTH:0]   x_pluse_q;//avoid overflow
wire [MODULU_LENGTH:0]   x_before_divide_2;//avoid overflow
wire [MODULU_LENGTH-1:0] x_after_divide_2;

wire [MODULU_LENGTH:0]   y_x_minus_result;//avoid overflow
wire [MODULU_LENGTH-1:0] y_or_minus_x;
wire [MODULU_LENGTH:0]   y_pluse_q;//avoid overflow
wire [MODULU_LENGTH:0]   y_before_divide_2;//avoid overflow
wire [MODULU_LENGTH-1:0] y_after_divide_2;
reg state;
//submodule to fresh the u & v
assign u_v_minus_result = u-v;
assign u_or_divide_2     = u[0] ? u:(u>>1);
assign v_u_minus_result = v-u;
assign v_or_divide_2     = ((!v[0])&&u[0]) ?(v>>1):v;
assign v                = new_v;
assign u                = new_u;
assign u_v_final_select = u[0]&v[0]&(!u_v_minus_result[MODULU_LENGTH]);
assign v_u_final_select = u[0]&v[0]&(!v_u_minus_result[MODULU_LENGTH]);
always@(posedge clk or negedge rstn)begin
    if(!rstn)begin
        new_v<='0;
        new_u<='0;
    end
    else if(go)begin
        new_v<=prime_q;
        new_u<=a;
    end
    else begin
        new_v<=v_u_final_select ? v_u_minus_result: v_or_divide_2;
        new_u<=u_v_final_select ? u_v_minus_result: u_or_divide_2;
    end
end

always@(posedge clk or negedge rstn)begin
    if(!rstn)begin
        q_reg<='0;
    end
    else if(go)begin
        q_reg<=prime_q;
    end
end

//submodule to fresh the x & y
assign x = new_x;
assign y = new_y;
assign x_y_minus_result  = x-y;
assign x_or_minus_y      = u_v_final_select ? x_y_minus_result: x;
assign x_pluse_q         = x_or_minus_y+q_reg;//prime_q;//q_reg;
//assign x_before_divide_2 = (u_v_final_select||(u[0]==0)) ? x_pluse_q: x_or_minus_y;
assign x_before_divide_2 = (((x[0]==1)&&(u[0]==0))||(x_y_minus_result[MODULU_LENGTH]&&u_v_final_select)) ? x_pluse_q: x_or_minus_y;
assign x_after_divide_2  = x_before_divide_2[MODULU_LENGTH:1];

assign y_x_minus_result  = y-x;
assign y_or_minus_x      = v_u_final_select ? y_x_minus_result: y;
assign y_pluse_q         = y_or_minus_x+q_reg;//prime_q;//q_reg;
//assign y_before_divide_2 = (v_u_final_select||((v[0]==0)&&(u[0]==1))) ? y_pluse_q: y_or_minus_x;
assign y_before_divide_2 = (((y[0]==1)&&((v[0]==0)&&(u[0]==1)))||(y_x_minus_result[MODULU_LENGTH]&&v_u_final_select)) ? y_pluse_q: y_or_minus_x;
assign y_after_divide_2  = y_before_divide_2[MODULU_LENGTH:1];

always@(posedge clk or negedge rstn)begin
    if(!rstn)begin
        new_x<=1'd1;
        new_y<=1'd0;
    end
    else if(go)begin
        new_x<=1'd1;
        new_y<=1'd0;
    end
    else begin
        new_x<=(u[0]==0)              ? x_after_divide_2: x_before_divide_2;
        new_y<=((v[0]==0)&&(u[0]==1)) ? y_after_divide_2: y_before_divide_2;
    end
end

//output the result
assign result_x = (x>q_reg) ? (x-q_reg): x;
assign result_y = (y>q_reg) ? (y-q_reg): y;
assign valid = ((u==1)||(v==1))&&state;
assign R     = ((u==1)? result_x: (v==1) ? result_y: '0);
always@(posedge clk or negedge rstn)begin
    if(!rstn)begin
        state <= 1'b0;
    end
    else if(go)begin
        state <= 1'b1;
    end
    else if(valid)begin
        state <= 1'b0;
    end
end


endmodule
