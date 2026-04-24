module divider_core (
    input wire clk,
    input wire rst_n,
    input wire valid_i,
    output reg ready_o,
    output reg valid_o,
    input wire ready_i,
    input wire [2:0] flags_src0,
    input wire [2:0] flags_src1,
    input wire signed_mode_src0,
    input wire signed_mode_src1,
    input wire [127:0] src0,
    input wire [127:0] src1,
    input wire [3:0] vm_id_in,
    input [ISA_BITS+2*REG_WIDTH+1-1:0] div_full_in,
    output [ISA_BITS+REG_WIDTH+1-1:0] div_full_out,
    output logic [3:0] vm_id_out
);
	reg	[127:0] res;
    // State encoding
    localparam IDLE = 2'd0;
    localparam PRE_PROCESSING = 2'd1;
    localparam PROCESSING = 2'd2;
    localparam OUTPUT = 2'd3;

   reg [1:0] state, state_nxt;

    // Internal registers
    reg [127:0] dividend, divisor;
    reg [127:0] abs_dividend, abs_divisor;
    reg [255:0] partial_remainder, partial_remainder_nxt;
    reg [255:0] shifted_divisor;
    reg [127:0] temp_quotient, temp_quotient_nxt;
    reg [8:0] 	total_count, count, count_nxt;
   
    reg sign_src0, sign_src1;

    // Output register
    reg [127:0] res_tmp;
    reg output_sign;
    reg 	src0_sign_ext, src1_sign_ext;
   reg [7:0] 	data_8;
   reg [15:0] 	data_16;
   reg [31:0] 	data_32;
   reg [63:0] 	data_64;
   
   

    // Sequential logic for state transitions and register updates
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            partial_remainder <= 0;
            temp_quotient <= 0;
            count <= 0;
        end else begin
            state <= state_nxt;
            partial_remainder <= partial_remainder_nxt;
            temp_quotient <= temp_quotient_nxt;
            count <= count_nxt;
        end
    end // always @ (posedge clk or negedge rst_n)


   always @(*) begin
      sign_src0 = 0;
      sign_src1 = 0;
      dividend = 0;
      abs_dividend = 0;
      total_count = 0;
      divisor = 0;
      abs_divisor = 0;
      src0_sign_ext = 0;
      src1_sign_ext = 0;
      data_8 = 0;
      data_16 = 0;
      data_32 = 0;
      data_64 = 0;
     
      
      case (flags_src0)
        3'd0: begin
	   sign_src0 = src0[7];
	   src0_sign_ext = signed_mode_src0 ? sign_src0:1'b0;
	   dividend = {{120{src0_sign_ext}}, src0[7:0]};
	   data_8 = !signed_mode_src0 ? (sign_src0 ? (~src0[7:0] + 1'b1) : src0[7:0]) : src0[7:0];
	   abs_dividend = {120'b0, data_8};
           total_count = 8'd4;
        end
        3'd1: begin
	   sign_src0 = src0[15];
	   src0_sign_ext = signed_mode_src0 ? sign_src0:1'b0;
           dividend = {{112{src0_sign_ext}}, src0[15:0]};
	   data_16 = !signed_mode_src0 ? (sign_src0 ? (~src0[15:0] + 1'b1) : src0[15:0]) : src0[15:0];
	   abs_dividend = {112'b0, data_16};
           total_count = 8'd8;
	end
        3'd2: begin
	   sign_src0 = src0[31];
	   src0_sign_ext = signed_mode_src0 ? sign_src0:1'b0;
           dividend = {{96{src0_sign_ext}}, src0[31:0]};
	   data_32 = !signed_mode_src0 ? (sign_src0 ? (~src0[31:0] + 1'b1) : src0[31:0]) : src0[31:0];
	   
	   abs_dividend = {96'b0, data_32};
           total_count = 8'd16;
        end
        3'd3: begin
	   sign_src0 = src0[63];
	   src0_sign_ext = signed_mode_src0 ? sign_src0:1'b0;
           dividend = {{64{src0_sign_ext}}, src0[63:0]};
	   data_64 = !signed_mode_src0 ? (sign_src0 ? (~src0[63:0] + 1'b1) : src0[63:0]) : src0[63:0];
	   
	   abs_dividend = {64'b0, data_64};
           total_count = 8'd32;	   
        end
        3'd4: begin
	   sign_src0 = src0[127];
           dividend = src0;
	   abs_dividend = !signed_mode_src0 ? (sign_src0?(~src0 + 1'b1) : src0) : src0;
           total_count = 8'd64;	   	   
        end
      endcase

      case (flags_src1)
        3'd0: begin
	   sign_src1 = src1[7];
	   src1_sign_ext = signed_mode_src1 ? sign_src1:1'b0;
           divisor = {{120{src1_sign_ext}}, src1[7:0]};
	   data_8 = !signed_mode_src1 ? (sign_src1 ? (~src1[7:0] + 1'b1) : src1[7:0]) : src1[7:0];
	   
	   abs_divisor = {120'b0, data_8};
	  end
        3'd1: begin
	   sign_src1 = src1[15];
	   src1_sign_ext = signed_mode_src1 ? sign_src1:1'b0;
           divisor = {{112{src1_sign_ext}}, src1[15:0]};
	   data_16 = !signed_mode_src1 ? (sign_src1 ? (~src1[15:0] + 1'b1) : src1[15:0]) : src1[15:0];
	   abs_divisor = {112'b0, data_16};   
	  end
        3'd2: begin
	   sign_src1 = src1[31];
	   src1_sign_ext = signed_mode_src1 ? sign_src1:1'b0;
           divisor = {{96{src1_sign_ext}}, src1[31:0]};
	   data_32 = !signed_mode_src1 ? (sign_src1 ? (~src1[31:0] + 1'b1) : src1[31:0]) : src1[31:0];
	   abs_divisor = {96'b0, data_32};  
	  end 
        3'd3: begin
	   sign_src1 = src1[63];
	   src1_sign_ext = signed_mode_src1 ? sign_src1:1'b0;
           divisor = {{64{src1_sign_ext}}, src1[63:0]};
	   data_64 = !signed_mode_src1 ? (sign_src1 ? (~src1[63:0] + 1'b1) : src1[63:0]) : src1[63:0];
	   abs_divisor = {64'b0, data_64};  
	  end
        3'd4: begin
	   sign_src1 = src1[127];
           divisor = src1;
	   abs_divisor = !signed_mode_src1 ? (sign_src1?(~src1 + 1) : src1) : src1; 
	   end
      endcase
   end


    // Combinational logic for state transitions and operations
    always @(*) begin
        // Default values
        state_nxt = state;
        partial_remainder_nxt = partial_remainder;
        temp_quotient_nxt = temp_quotient;
        count_nxt = count;
        vm_id_out = vm_id_in;
        valid_o = 0;
        ready_o = 0;
        shifted_divisor = 0;
        res = 0;
       
       
        case (state)
            IDLE: begin
	        // clear temp_quotient
	       temp_quotient_nxt = 0;
                if (valid_i) begin
                    state_nxt = PRE_PROCESSING;
                end
            end

            PRE_PROCESSING: begin
                // Calculate absolute values if signed mode is enabled
	        partial_remainder_nxt = {128'b0, abs_dividend};

                if(abs_divisor == 0) begin
                    res = 0;
                    valid_o = 1'b1;
                    if(ready_i) begin
                        state_nxt = IDLE;
                        ready_o = 1'b1;
                    end
                    vm_id_out = vm_id_in;
                end
                else begin
                // Transition to PROCESSING state
                    state_nxt = PROCESSING;
                    count_nxt = 0;
                end
            end

            PROCESSING: begin
                // Initialize partial remainder and shifted divisor
                if (count < total_count) begin
		   shifted_divisor = abs_divisor << (total_count*2 - 2 * (count+1));
		   if(partial_remainder >= (shifted_divisor * 3)) begin
                        partial_remainder_nxt = partial_remainder - (shifted_divisor * 3);
                        temp_quotient_nxt = (temp_quotient << 2) | 3;
                    end else if(partial_remainder >= (shifted_divisor * 2)) begin
                        partial_remainder_nxt = partial_remainder - (shifted_divisor * 2);
                        temp_quotient_nxt = (temp_quotient << 2) | 2;
                    end else if(partial_remainder >= (shifted_divisor * 1)) begin
                        partial_remainder_nxt = partial_remainder - (shifted_divisor * 1);
                        temp_quotient_nxt = (temp_quotient << 2) | 1;
                    end else begin
                        partial_remainder_nxt = partial_remainder;
                        temp_quotient_nxt = (temp_quotient << 2);
                    end

                    count_nxt = count + 1;
                    state_nxt = PROCESSING;
                end else begin
                    state_nxt = OUTPUT;
                end
            end

            OUTPUT: begin
                output_sign = (!signed_mode_src0 ? sign_src0 : 1'b0) ^ (!signed_mode_src1 ? sign_src1 : 1'b0);
                res_tmp = output_sign ? (~temp_quotient + 1) : temp_quotient;

                // Select result size based on flags
                case (flags_src0)
                    3'd0: res = {120'b0, res_tmp[7:0]};
                    3'd1: res = {112'b0, res_tmp[15:0]};
                    3'd2: res = {96'b0, res_tmp[31:0]};
                    3'd3: res = {64'b0, res_tmp[63:0]};
                    3'd4: res = res_tmp;
                endcase
                valid_o = 1'b1;
                if(ready_i) begin
                    state_nxt = IDLE;
                    ready_o = 1'b1;
                end
                vm_id_out = vm_id_in;
	        //div_full_out = {div_full_in[ISA_BITS+2*REG_WIDTH+1-1-:ISA_BITS+1] ,{(REG_WIDTH-128){1'b0}},res};
            end
        endcase
    end

assign	div_full_out = {div_full_in[ISA_BITS+2*REG_WIDTH+1-1-:ISA_BITS+1] ,{(REG_WIDTH-128){1'b0}},res};

endmodule
