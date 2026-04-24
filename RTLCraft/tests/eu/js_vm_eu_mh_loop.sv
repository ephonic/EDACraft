module js_vm_eu_mh_loop (/*AUTOARG*/
   // Outputs
   mov_merkel_ready, mov_mh_valid, mov_mh_data, mov_mh_type,
   mov_mh_index, mov_mh_last,
   // Inputs
   clk, rstn, mov_merkel_valid, mov_merkel_eop, mov_merkel_res,
   mov_mh_ready
   );
`include "js_vm.vh"
input           clk;
input           rstn;

input           mov_merkel_valid;
input           mov_merkel_eop;
input   [1+8+256-1:0]   mov_merkel_res;
output          mov_merkel_ready;

output          mov_mh_valid;
output  [255:0] mov_mh_data;
output  [3:0]   mov_mh_type;
output  [17:0]  mov_mh_index;
output          mov_mh_last;
input           mov_mh_ready;


localparam  MERKEL_MAX    = 1<<(3*MERKEL_LEVEL); // 2^18
//-------------------------------------
/*AUTOWIRE*/
reg         mh_valid;
wire        mh_ready = mov_mh_ready;

localparam  MH_IDLE = 2'b00;
localparam  MH_LOOP = 2'b01;
localparam  MH_EOP  = 2'b10;

reg     [1:0]   mh_st, mh_st_nxt;

wire    [253-1:0]   mov_merkel_data;
wire    [2:0]       mov_rsv;
wire                mov_merkel_bit;
wire    [7:0]       mov_merkel_mcnt;
assign {mov_merkel_bit, mov_merkel_mcnt, mov_rsv, mov_merkel_data} = mov_merkel_res;
wire            mov_merkel_is_fr  = (mov_merkel_bit == 1'b0);
wire            mov_merkel_is_bit = (mov_merkel_bit == 1'b1);
wire    [7:0]   mov_merkel_mnum = mov_merkel_is_fr ? 8'd1 :
                                  mov_merkel_is_bit ? mov_merkel_mcnt : 8'd0;

// the index from mov
reg [17:0]  mov_merkel_index;
wire [18:0]  mov_merkel_index_nxt = mov_mh_last ? 18'b0 : (mov_merkel_index + mov_merkel_mnum);
wire    [18:0]  mov_merkel_sending = mov_merkel_index + mov_merkel_mnum;
always @(posedge clk or negedge rstn)
if(!rstn)
    mov_merkel_index    <= 18'b0;
else if(mov_merkel_valid && mov_merkel_ready)
    mov_merkel_index    <= mov_merkel_index_nxt[17:0];

reg	[31:0]	mh_cnt;
always @(posedge clk or negedge rstn)
if(!rstn)
	mh_cnt	<= 'h0;
else if(mov_merkel_valid && mov_merkel_ready)
	mh_cnt	<= mh_cnt + 1;
wire    [18:0]  pre_max_merkel =    !mov_merkel_eop ? 19'd262144 : 
                                |mov_merkel_sending[18:15] ? 19'd262144 :
                                |mov_merkel_sending[14:12] ? 19'd32768 :
                                |mov_merkel_sending[11:9]  ? 19'd4096 :
                                |mov_merkel_sending[8:6]   ? 19'd512 :
                                |mov_merkel_sending[5:3]   ? 19'd64 : 19'd8;
reg [18:0]  max_merkel;
reg     mh_padding_start;
always @(posedge clk or negedge rstn)
if(!rstn)
    max_merkel  <= 19'b0;
else if(mh_padding_start)
    max_merkel  <= pre_max_merkel;


// the bit data of this mov transaction; pad zeros at lsb
wire    [264-1:0] mov_bit_data = {11'b0, mov_merkel_data} << mov_merkel_index[2:0];
wire    [7:0]   mov_bit_array   [0:32];
genvar i;
generate
    for(i=0; i<33; i=i+1) begin
        assign mov_bit_array[i] = mov_bit_data[i*8+:8];
    end
endgenerate

//----------
// loop & eop control
wire    [17:0]      mov_eop_padding_bit_num = MERKEL_MAX - mov_merkel_index[17:0];
wire                mov_eop_padding_1st_bad = |mov_eop_padding_bit_num[2:0];
wire    [3:0]       mov_eop_padding_1st_num = ~|mov_eop_padding_bit_num[2:0] ? 4'd8 : {1'b0, mov_eop_padding_bit_num[2:0]};
wire    [5:0]       mov_eop_padding_cycle   = mov_eop_padding_bit_num[17:15] + 
                                              mov_eop_padding_bit_num[14:12] + 
                                              mov_eop_padding_bit_num[11:9] + 
                                              mov_eop_padding_bit_num[8:6] + 
                                              mov_eop_padding_bit_num[5:3] + |mov_eop_padding_bit_num[2:0];

wire    [8:0]       mov_bit_num     = mov_merkel_mcnt + mov_merkel_index[2:0];
wire                mov_bit_need_split = (mov_merkel_index[2:0] + mov_merkel_mcnt) > 8;

wire                mov_bit_1st_bad = |mov_merkel_index[2:0];
wire    [3:0]       mov_bit_1st_num = 8-mov_merkel_index[2:0];
wire	[8:0]	    mov_bit_num_adj = mov_bit_num - (|mov_merkel_index[2:0] ? 8 : 0);
wire    [5:0]       mov_bit_cycle   = mov_bit_need_split ? (mov_bit_num_adj[8:3] + mov_bit_1st_bad + |mov_bit_num_adj[2:0]) : 5'h1;

//wire    [17:0]      mov_trans_bits = mh_st == MH_EOP ? (MERKEL_MAX - {mov_merkel_index[17:3], 3'b0}) : ({10'b0, mov_merkel_mnum} + mov_merkel_index[2:0]);
//wire    [15:0]      mov_trans_num  = mh_st == MH_EOP ? (mov_trans_bits[17:3]+|mov_trans_bits[2:0]) :
//                                     mov_merkel_is_fr ? 16'b1 : (mov_trans_bits[17:3] + |mov_trans_bits[2:0]);
wire    [17:0]      mov_trans_bits = mh_st == MH_EOP ? mov_eop_padding_bit_num : {9'b0, mov_bit_num};
wire    [5:0]       mov_trans_num  = mh_st == MH_EOP ? mov_eop_padding_cycle : mov_merkel_is_bit ? mov_bit_cycle : 6'd1;
reg [5:0]  mov_trans_cnt;
wire    mov_trans_last = mov_trans_cnt == (mov_trans_num - 1);
wire    [5:0]   mov_trans_cnt_nxt = mov_trans_last ? 6'd0 : (mov_trans_cnt + 1);
always @(posedge clk or negedge rstn)
if(!rstn)
    mov_trans_cnt <= 6'd0;
else if(mov_mh_valid && mov_mh_ready)
    mov_trans_cnt <= mov_trans_cnt_nxt;
wire    mov_trans_first = ~|mov_trans_cnt;
//--------------

//--------
// generate output
// assume the total number of merkel from the VM is multiple of 8
// after the EOP, zeros are padded, else
// pad to multiple-of-8 for the first trans of the mov-bits transactions
wire    [7:0]   mov_mh_bits      = mh_st==MH_EOP ? 8'b0 : 
                                   mov_merkel_is_bit ? (mov_trans_first ? (mov_bit_array[0]>>mov_merkel_index[2:0]) : mov_bit_array[mov_trans_cnt]) : 8'b0;

assign          mov_mh_valid = mh_valid;
reg     [17:0]  mov_mh_index;
wire    [18:0]  mov_mh_index_nxt;
wire            mov_mh_last;
reg     [3:0]   mh_bit_num;


wire    [3:0]   mov_loop_bit_num = mov_trans_first ? (8-{~|mov_merkel_index[2:0], mov_merkel_index[2:0]}) :
                                   mov_trans_last  ? ({~|mov_trans_bits[2:0], mov_trans_bits[2:0]}) : 4'd8;
wire    [3:0]   mov_mh_type;
assign  mov_mh_type[2:0]    = (mh_st!=MH_EOP && mov_merkel_is_fr) ? 3'h0 :
                              (mh_st!=MH_EOP && mov_merkel_is_bit) ? (mh_bit_num==4'h8 ? 3'h2 : 3'h1) :
                              (|mov_mh_index[2:0])  ? 3'h1 :
                              (|mov_mh_index[5:3])  ? 3'h2 :
                              (|mov_mh_index[8:6])  ? 3'h3 :
                              (|mov_mh_index[11:9]) ? 3'h4 :
                              (|mov_mh_index[14:12])? 3'h5 :
                              (|mov_mh_index[17:15])? 3'h6 : 3'h7;
assign  mov_mh_type[3]      = mh_st==MH_EOP ? ({1'b0, mov_mh_index}>=max_merkel) : ({1'b0, mov_mh_index}>pre_max_merkel);
wire    [255:0] mov_mh_data = mov_mh_type[2:0] == 3'h0 ? {3'b0, mov_merkel_data} :
                              mov_mh_type[2:0] == 3'h1 ? {244'b0, mh_bit_num, mov_mh_bits} :
                              mov_mh_type[2:0] == 3'h2 ? {244'b0, 4'h8,       mov_mh_bits} : 256'b0; 
                              
wire    [17:0]  mh_inc_num  = mov_mh_type[2:0] == 3'h0 ? 18'd1 : 
                              mov_mh_type[2:0] == 3'h1 ? {14'b0, mh_bit_num} :
                              mov_mh_type[2:0] == 3'h2 ? 18'b1<<3 :
                              mov_mh_type[2:0] == 3'h3 ? 18'b1<<6 :
                              mov_mh_type[2:0] == 3'h4 ? 18'b1<<9 :
                              mov_mh_type[2:0] == 3'h5 ? 18'b1<<12 :
                              mov_mh_type[2:0] == 3'h6 ? 18'b1<<15 : 18'b1<<18 ;

assign  mov_mh_index_nxt = {1'b0, mov_mh_index} + mh_inc_num;
assign  mov_mh_last = mov_mh_index_nxt == MERKEL_MAX;


always @(posedge clk or negedge rstn)
if(!rstn)
    mov_mh_index <= 'b0;
else if(mov_mh_valid && mov_mh_ready)
     mov_mh_index <= mov_mh_last ? 18'h0 : mov_mh_index_nxt[17:0];



always @(posedge clk or negedge rstn)
if(!rstn) begin
    mh_st   <= MH_IDLE;
end
else begin
    mh_st   <= mh_st_nxt;
end
reg     mov_merkel_ready;
reg     mh_is_bit;

always @(*) begin
    mh_st_nxt = mh_st;
    mh_valid = 1'b0;
    mov_merkel_ready = 1'b0;
    mh_bit_num = 4'h0;
    mh_padding_start = 1'b0;
    case(mh_st)
        MH_IDLE : begin
            if(mov_merkel_valid) begin
                mh_valid = mov_merkel_bit ? mov_merkel_mcnt!=8'b0 : 1'b1;
                if(mov_merkel_bit) begin
                    if((mov_merkel_index[2:0] + mov_merkel_mcnt)>8)
                        mh_bit_num = 8 - mov_mh_index[2:0];
                    else
                        mh_bit_num = mov_merkel_mcnt[3:0];
                end else begin
                    mh_bit_num = 1'b1;
                end
		        if(mov_merkel_bit && mov_merkel_mcnt==8'b0) begin
		            if(mov_merkel_eop) begin
			            mov_merkel_ready = mov_mh_last;
			            mh_st_nxt = mov_mh_last ? MH_IDLE : MH_EOP;
                        mh_padding_start = !mov_mh_last;
		            end else begin
			            mov_merkel_ready = 1'b1;
			            mh_st_nxt = MH_IDLE;
		            end
		        end
                else if(mov_mh_ready) begin
                    if(mov_trans_last) begin
                        if(mov_merkel_eop) begin
                            mov_merkel_ready = mov_mh_last;
                            mh_st_nxt = mov_mh_last ? MH_IDLE : MH_EOP;
                            mh_padding_start = !mov_mh_last;
                        end else begin
                            mov_merkel_ready = 1'b1;
                        end
                    end
                    else
                        mh_st_nxt = MH_LOOP;
                end
            end
        end
        MH_LOOP : begin
            mh_valid = 1'b1;
            mh_bit_num = mov_trans_last ? {~|mov_merkel_sending[2:0], mov_merkel_sending[2:0]} : 4'h8;
            if(mov_mh_ready) begin
                if(mov_trans_last) begin
//                    mh_bit_num = {~|mov_merkel_sending[2:0], mov_merkel_sending[2:0]};
                    if(mov_merkel_eop) begin
                        mov_merkel_ready = mov_mh_last;
                        mh_st_nxt = mov_mh_last ? MH_IDLE : MH_EOP;
                        mh_padding_start = !mov_mh_last;
                    end else begin
                        mov_merkel_ready = 1'b1;
                        mh_st_nxt = MH_IDLE;
                    end
                end
//                else begin
//                    mh_bit_num = 4'h8;
//                end
            end
        end
        MH_EOP  : begin
            mh_valid = 1'b1;
	        if(mov_trans_first)
		        mh_bit_num = 4'h8 - mov_mh_index[2:0];
	        else
		        mh_bit_num = 4'hf;
            if(mov_mh_ready) begin
                if(mov_mh_last) begin
                    mh_st_nxt = MH_IDLE;
                    mov_merkel_ready = 1'b1;
                end
            end
        end
        default: mh_st_nxt = MH_IDLE;
    endcase
end






endmodule

