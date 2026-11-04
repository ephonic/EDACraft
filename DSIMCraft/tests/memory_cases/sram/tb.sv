module tb;reg clk=0;integer checked=0;integer cycle;
reg u0_rst_n=0;
reg u0_in_valid=0;
wire u0_in_ready;
reg u0_in_write=0;
reg u0_in_address=0;
reg u0_in_data=0;
reg u0_in_mask=0;
reg u0_in_tag=0;
wire u0_bank_valid;
wire u0_bank_ready;
wire u0_bank_lane;
wire u0_bank_write;
wire u0_bank_address;
wire u0_bank_data;
wire u0_bank_mask;
wire u0_bank_rdata;
wire u0_out_valid;
reg u0_out_ready=0;
wire u0_out_data;
wire u0_out_tag;
reg u0_enable=0;
wire u0_sram_ce;
wire u0_sram_we;
wire u0_sram_address;
wire u0_sram_wdata;
wire u0_sram_wmask;
wire u0_sram_rdata;
reg [0:0] memory_0[0:1];
reg [0:0] macro_q_0=0;
integer init_0;
reg u1_rst_n=0;
reg u1_in_valid=0;
wire u1_in_ready;
reg [3:0] u1_in_write=0;
reg [15:0] u1_in_address=0;
reg [31:0] u1_in_data=0;
reg [31:0] u1_in_mask=0;
reg [2:0] u1_in_tag=0;
wire [1:0] u1_bank_valid;
wire [1:0] u1_bank_ready;
wire [3:0] u1_bank_lane;
wire [1:0] u1_bank_write;
wire [5:0] u1_bank_address;
wire [15:0] u1_bank_data;
wire [15:0] u1_bank_mask;
wire [15:0] u1_bank_rdata;
wire u1_out_valid;
reg u1_out_ready=0;
wire [31:0] u1_out_data;
wire [2:0] u1_out_tag;
reg [1:0] u1_enable=0;
wire [1:0] u1_sram_ce;
wire [1:0] u1_sram_we;
wire [5:0] u1_sram_address;
wire [15:0] u1_sram_wdata;
wire [15:0] u1_sram_wmask;
wire [15:0] u1_sram_rdata;
reg [7:0] memory_1[0:15];
reg [15:0] macro_q_1=0;
integer init_1;
reg u2_rst_n=0;
reg u2_in_valid=0;
wire u2_in_ready;
reg [2:0] u2_in_write=0;
reg [8:0] u2_in_address=0;
reg [14:0] u2_in_data=0;
reg [14:0] u2_in_mask=0;
reg [1:0] u2_in_tag=0;
wire [3:0] u2_bank_valid;
wire [3:0] u2_bank_ready;
wire [7:0] u2_bank_lane;
wire [3:0] u2_bank_write;
wire [3:0] u2_bank_address;
wire [19:0] u2_bank_data;
wire [19:0] u2_bank_mask;
wire [19:0] u2_bank_rdata;
wire u2_out_valid;
reg u2_out_ready=0;
wire [14:0] u2_out_data;
wire [1:0] u2_out_tag;
reg [3:0] u2_enable=0;
wire [3:0] u2_sram_ce;
wire [3:0] u2_sram_we;
wire [3:0] u2_sram_address;
wire [19:0] u2_sram_wdata;
wire [19:0] u2_sram_wmask;
wire [19:0] u2_sram_rdata;
reg [4:0] memory_2[0:7];
reg [19:0] macro_q_2=0;
integer init_2;
reg u3_rst_n=0;
reg u3_in_valid=0;
wire u3_in_ready;
reg [7:0] u3_in_write=0;
reg [63:0] u3_in_address=0;
reg [255:0] u3_in_data=0;
reg [255:0] u3_in_mask=0;
reg [15:0] u3_in_tag=0;
wire [7:0] u3_bank_valid;
wire [7:0] u3_bank_ready;
wire [23:0] u3_bank_lane;
wire [7:0] u3_bank_write;
wire [39:0] u3_bank_address;
wire [255:0] u3_bank_data;
wire [255:0] u3_bank_mask;
wire [255:0] u3_bank_rdata;
wire u3_out_valid;
reg u3_out_ready=0;
wire [255:0] u3_out_data;
wire [15:0] u3_out_tag;
reg [7:0] u3_enable=0;
wire [7:0] u3_sram_ce;
wire [7:0] u3_sram_we;
wire [39:0] u3_sram_address;
wire [255:0] u3_sram_wdata;
wire [255:0] u3_sram_wmask;
wire [255:0] u3_sram_rdata;
reg [31:0] memory_3[0:255];
reg [255:0] macro_q_3=0;
integer init_3;
reg u4_rst_n=0;
reg u4_in_valid=0;
wire u4_in_ready;
reg [2:0] u4_in_write=0;
reg [8:0] u4_in_address=0;
reg [8:0] u4_in_data=0;
reg [8:0] u4_in_mask=0;
reg [1:0] u4_in_tag=0;
wire [7:0] u4_bank_valid;
wire [7:0] u4_bank_ready;
wire [15:0] u4_bank_lane;
wire [7:0] u4_bank_write;
wire [7:0] u4_bank_address;
wire [23:0] u4_bank_data;
wire [23:0] u4_bank_mask;
wire [23:0] u4_bank_rdata;
wire u4_out_valid;
reg u4_out_ready=0;
wire [8:0] u4_out_data;
wire [1:0] u4_out_tag;
reg [7:0] u4_enable=0;
wire [7:0] u4_sram_ce;
wire [7:0] u4_sram_we;
wire [7:0] u4_sram_address;
wire [23:0] u4_sram_wdata;
wire [23:0] u4_sram_wmask;
wire [23:0] u4_sram_rdata;
reg [2:0] memory_4[0:7];
reg [23:0] macro_q_4=0;
integer init_4;
reg u5_rst_n=0;
reg u5_in_valid=0;
wire u5_in_ready;
reg [1:0] u5_in_write=0;
reg [1:0] u5_in_address=0;
reg [3:0] u5_in_data=0;
reg [3:0] u5_in_mask=0;
reg u5_in_tag=0;
wire u5_bank_valid;
wire u5_bank_ready;
wire u5_bank_lane;
wire u5_bank_write;
wire u5_bank_address;
wire [1:0] u5_bank_data;
wire [1:0] u5_bank_mask;
wire [1:0] u5_bank_rdata;
wire u5_out_valid;
reg u5_out_ready=0;
wire [3:0] u5_out_data;
wire u5_out_tag;
reg u5_enable=0;
wire u5_sram_ce;
wire u5_sram_we;
wire u5_sram_address;
wire [1:0] u5_sram_wdata;
wire [1:0] u5_sram_wmask;
wire [1:0] u5_sram_rdata;
reg [1:0] memory_5[0:1];
reg [1:0] macro_q_5=0;
integer init_5;
reg u6_rst_n=0;
reg u6_in_valid=0;
wire u6_in_ready;
reg [2:0] u6_in_write=0;
reg [23:0] u6_in_address=0;
reg [95:0] u6_in_data=0;
reg [95:0] u6_in_mask=0;
reg [15:0] u6_in_tag=0;
wire u6_bank_valid;
wire u6_bank_ready;
wire [1:0] u6_bank_lane;
wire u6_bank_write;
wire [7:0] u6_bank_address;
wire [31:0] u6_bank_data;
wire [31:0] u6_bank_mask;
wire [31:0] u6_bank_rdata;
wire u6_out_valid;
reg u6_out_ready=0;
wire [95:0] u6_out_data;
wire [15:0] u6_out_tag;
reg u6_enable=0;
wire u6_sram_ce;
wire u6_sram_we;
wire [7:0] u6_sram_address;
wire [31:0] u6_sram_wdata;
wire [31:0] u6_sram_wmask;
wire [31:0] u6_sram_rdata;
reg [31:0] memory_6[0:255];
reg [31:0] macro_q_6=0;
integer init_6;
reg [44:0] vectors_0[0:319];
reg [409:0] vectors_1[0:319];
reg [400:0] vectors_2[0:319];
reg [4518:0] vectors_3[0:319];
reg [500:0] vectors_4[0:319];
reg [70:0] vectors_5[0:319];
reg [896:0] vectors_6[0:319];
batch_sram_root_0 u0(.clk(clk),.rst_n(u0_rst_n),.in_valid(u0_in_valid),.in_ready(u0_in_ready),.in_write(u0_in_write),.in_address(u0_in_address),.in_data(u0_in_data),.in_mask(u0_in_mask),.in_tag(u0_in_tag),.bank_valid(u0_bank_valid),.bank_ready(u0_bank_ready),.bank_lane(u0_bank_lane),.bank_write(u0_bank_write),.bank_address(u0_bank_address),.bank_data(u0_bank_data),.bank_mask(u0_bank_mask),.bank_rdata(u0_bank_rdata),.out_valid(u0_out_valid),.out_ready(u0_out_ready),.out_data(u0_out_data),.out_tag(u0_out_tag),.enable(u0_enable),.sram_ce(u0_sram_ce),.sram_we(u0_sram_we),.sram_address(u0_sram_address),.sram_wdata(u0_sram_wdata),.sram_wmask(u0_sram_wmask),.sram_rdata(u0_sram_rdata));
batch_sram_root_1 u1(.clk(clk),.rst_n(u1_rst_n),.in_valid(u1_in_valid),.in_ready(u1_in_ready),.in_write(u1_in_write),.in_address(u1_in_address),.in_data(u1_in_data),.in_mask(u1_in_mask),.in_tag(u1_in_tag),.bank_valid(u1_bank_valid),.bank_ready(u1_bank_ready),.bank_lane(u1_bank_lane),.bank_write(u1_bank_write),.bank_address(u1_bank_address),.bank_data(u1_bank_data),.bank_mask(u1_bank_mask),.bank_rdata(u1_bank_rdata),.out_valid(u1_out_valid),.out_ready(u1_out_ready),.out_data(u1_out_data),.out_tag(u1_out_tag),.enable(u1_enable),.sram_ce(u1_sram_ce),.sram_we(u1_sram_we),.sram_address(u1_sram_address),.sram_wdata(u1_sram_wdata),.sram_wmask(u1_sram_wmask),.sram_rdata(u1_sram_rdata));
batch_sram_root_2 u2(.clk(clk),.rst_n(u2_rst_n),.in_valid(u2_in_valid),.in_ready(u2_in_ready),.in_write(u2_in_write),.in_address(u2_in_address),.in_data(u2_in_data),.in_mask(u2_in_mask),.in_tag(u2_in_tag),.bank_valid(u2_bank_valid),.bank_ready(u2_bank_ready),.bank_lane(u2_bank_lane),.bank_write(u2_bank_write),.bank_address(u2_bank_address),.bank_data(u2_bank_data),.bank_mask(u2_bank_mask),.bank_rdata(u2_bank_rdata),.out_valid(u2_out_valid),.out_ready(u2_out_ready),.out_data(u2_out_data),.out_tag(u2_out_tag),.enable(u2_enable),.sram_ce(u2_sram_ce),.sram_we(u2_sram_we),.sram_address(u2_sram_address),.sram_wdata(u2_sram_wdata),.sram_wmask(u2_sram_wmask),.sram_rdata(u2_sram_rdata));
batch_sram_root_3 u3(.clk(clk),.rst_n(u3_rst_n),.in_valid(u3_in_valid),.in_ready(u3_in_ready),.in_write(u3_in_write),.in_address(u3_in_address),.in_data(u3_in_data),.in_mask(u3_in_mask),.in_tag(u3_in_tag),.bank_valid(u3_bank_valid),.bank_ready(u3_bank_ready),.bank_lane(u3_bank_lane),.bank_write(u3_bank_write),.bank_address(u3_bank_address),.bank_data(u3_bank_data),.bank_mask(u3_bank_mask),.bank_rdata(u3_bank_rdata),.out_valid(u3_out_valid),.out_ready(u3_out_ready),.out_data(u3_out_data),.out_tag(u3_out_tag),.enable(u3_enable),.sram_ce(u3_sram_ce),.sram_we(u3_sram_we),.sram_address(u3_sram_address),.sram_wdata(u3_sram_wdata),.sram_wmask(u3_sram_wmask),.sram_rdata(u3_sram_rdata));
batch_sram_root_4 u4(.clk(clk),.rst_n(u4_rst_n),.in_valid(u4_in_valid),.in_ready(u4_in_ready),.in_write(u4_in_write),.in_address(u4_in_address),.in_data(u4_in_data),.in_mask(u4_in_mask),.in_tag(u4_in_tag),.bank_valid(u4_bank_valid),.bank_ready(u4_bank_ready),.bank_lane(u4_bank_lane),.bank_write(u4_bank_write),.bank_address(u4_bank_address),.bank_data(u4_bank_data),.bank_mask(u4_bank_mask),.bank_rdata(u4_bank_rdata),.out_valid(u4_out_valid),.out_ready(u4_out_ready),.out_data(u4_out_data),.out_tag(u4_out_tag),.enable(u4_enable),.sram_ce(u4_sram_ce),.sram_we(u4_sram_we),.sram_address(u4_sram_address),.sram_wdata(u4_sram_wdata),.sram_wmask(u4_sram_wmask),.sram_rdata(u4_sram_rdata));
batch_sram_root_5 u5(.clk(clk),.rst_n(u5_rst_n),.in_valid(u5_in_valid),.in_ready(u5_in_ready),.in_write(u5_in_write),.in_address(u5_in_address),.in_data(u5_in_data),.in_mask(u5_in_mask),.in_tag(u5_in_tag),.bank_valid(u5_bank_valid),.bank_ready(u5_bank_ready),.bank_lane(u5_bank_lane),.bank_write(u5_bank_write),.bank_address(u5_bank_address),.bank_data(u5_bank_data),.bank_mask(u5_bank_mask),.bank_rdata(u5_bank_rdata),.out_valid(u5_out_valid),.out_ready(u5_out_ready),.out_data(u5_out_data),.out_tag(u5_out_tag),.enable(u5_enable),.sram_ce(u5_sram_ce),.sram_we(u5_sram_we),.sram_address(u5_sram_address),.sram_wdata(u5_sram_wdata),.sram_wmask(u5_sram_wmask),.sram_rdata(u5_sram_rdata));
batch_sram_root_6 u6(.clk(clk),.rst_n(u6_rst_n),.in_valid(u6_in_valid),.in_ready(u6_in_ready),.in_write(u6_in_write),.in_address(u6_in_address),.in_data(u6_in_data),.in_mask(u6_in_mask),.in_tag(u6_in_tag),.bank_valid(u6_bank_valid),.bank_ready(u6_bank_ready),.bank_lane(u6_bank_lane),.bank_write(u6_bank_write),.bank_address(u6_bank_address),.bank_data(u6_bank_data),.bank_mask(u6_bank_mask),.bank_rdata(u6_bank_rdata),.out_valid(u6_out_valid),.out_ready(u6_out_ready),.out_data(u6_out_data),.out_tag(u6_out_tag),.enable(u6_enable),.sram_ce(u6_sram_ce),.sram_we(u6_sram_we),.sram_address(u6_sram_address),.sram_wdata(u6_sram_wdata),.sram_wmask(u6_sram_wmask),.sram_rdata(u6_sram_rdata));
assign u0_sram_rdata=macro_q_0;
always @(posedge clk) if(u0_sram_ce[0]) begin if(u0_sram_we[0]) memory_0[(u0_sram_address[0:0]*1+0)]<=(memory_0[(u0_sram_address[0:0]*1+0)]&~u0_sram_wmask[0:0])|(u0_sram_wdata[0:0]&u0_sram_wmask[0:0]);else macro_q_0[0:0]<=memory_0[(u0_sram_address[0:0]*1+0)];end
assign u1_sram_rdata=macro_q_1;
always @(posedge clk) if(u1_sram_ce[0]) begin if(u1_sram_we[0]) memory_1[(u1_sram_address[2:0]*2+0)]<=(memory_1[(u1_sram_address[2:0]*2+0)]&~u1_sram_wmask[7:0])|(u1_sram_wdata[7:0]&u1_sram_wmask[7:0]);else macro_q_1[7:0]<=memory_1[(u1_sram_address[2:0]*2+0)];end
always @(posedge clk) if(u1_sram_ce[1]) begin if(u1_sram_we[1]) memory_1[(u1_sram_address[5:3]*2+1)]<=(memory_1[(u1_sram_address[5:3]*2+1)]&~u1_sram_wmask[15:8])|(u1_sram_wdata[15:8]&u1_sram_wmask[15:8]);else macro_q_1[15:8]<=memory_1[(u1_sram_address[5:3]*2+1)];end
assign u2_sram_rdata=macro_q_2;
always @(posedge clk) if(u2_sram_ce[0]) begin if(u2_sram_we[0]) memory_2[(u2_sram_address[0:0]+0)]<=(memory_2[(u2_sram_address[0:0]+0)]&~u2_sram_wmask[4:0])|(u2_sram_wdata[4:0]&u2_sram_wmask[4:0]);else macro_q_2[4:0]<=memory_2[(u2_sram_address[0:0]+0)];end
always @(posedge clk) if(u2_sram_ce[1]) begin if(u2_sram_we[1]) memory_2[(u2_sram_address[1:1]+2)]<=(memory_2[(u2_sram_address[1:1]+2)]&~u2_sram_wmask[9:5])|(u2_sram_wdata[9:5]&u2_sram_wmask[9:5]);else macro_q_2[9:5]<=memory_2[(u2_sram_address[1:1]+2)];end
always @(posedge clk) if(u2_sram_ce[2]) begin if(u2_sram_we[2]) memory_2[(u2_sram_address[2:2]+4)]<=(memory_2[(u2_sram_address[2:2]+4)]&~u2_sram_wmask[14:10])|(u2_sram_wdata[14:10]&u2_sram_wmask[14:10]);else macro_q_2[14:10]<=memory_2[(u2_sram_address[2:2]+4)];end
always @(posedge clk) if(u2_sram_ce[3]) begin if(u2_sram_we[3]) memory_2[(u2_sram_address[3:3]+6)]<=(memory_2[(u2_sram_address[3:3]+6)]&~u2_sram_wmask[19:15])|(u2_sram_wdata[19:15]&u2_sram_wmask[19:15]);else macro_q_2[19:15]<=memory_2[(u2_sram_address[3:3]+6)];end
assign u3_sram_rdata=macro_q_3;
always @(posedge clk) if(u3_sram_ce[0]) begin if(u3_sram_we[0]) memory_3[(u3_sram_address[4:0]+0)]<=(memory_3[(u3_sram_address[4:0]+0)]&~u3_sram_wmask[31:0])|(u3_sram_wdata[31:0]&u3_sram_wmask[31:0]);else macro_q_3[31:0]<=memory_3[(u3_sram_address[4:0]+0)];end
always @(posedge clk) if(u3_sram_ce[1]) begin if(u3_sram_we[1]) memory_3[(u3_sram_address[9:5]+32)]<=(memory_3[(u3_sram_address[9:5]+32)]&~u3_sram_wmask[63:32])|(u3_sram_wdata[63:32]&u3_sram_wmask[63:32]);else macro_q_3[63:32]<=memory_3[(u3_sram_address[9:5]+32)];end
always @(posedge clk) if(u3_sram_ce[2]) begin if(u3_sram_we[2]) memory_3[(u3_sram_address[14:10]+64)]<=(memory_3[(u3_sram_address[14:10]+64)]&~u3_sram_wmask[95:64])|(u3_sram_wdata[95:64]&u3_sram_wmask[95:64]);else macro_q_3[95:64]<=memory_3[(u3_sram_address[14:10]+64)];end
always @(posedge clk) if(u3_sram_ce[3]) begin if(u3_sram_we[3]) memory_3[(u3_sram_address[19:15]+96)]<=(memory_3[(u3_sram_address[19:15]+96)]&~u3_sram_wmask[127:96])|(u3_sram_wdata[127:96]&u3_sram_wmask[127:96]);else macro_q_3[127:96]<=memory_3[(u3_sram_address[19:15]+96)];end
always @(posedge clk) if(u3_sram_ce[4]) begin if(u3_sram_we[4]) memory_3[(u3_sram_address[24:20]+128)]<=(memory_3[(u3_sram_address[24:20]+128)]&~u3_sram_wmask[159:128])|(u3_sram_wdata[159:128]&u3_sram_wmask[159:128]);else macro_q_3[159:128]<=memory_3[(u3_sram_address[24:20]+128)];end
always @(posedge clk) if(u3_sram_ce[5]) begin if(u3_sram_we[5]) memory_3[(u3_sram_address[29:25]+160)]<=(memory_3[(u3_sram_address[29:25]+160)]&~u3_sram_wmask[191:160])|(u3_sram_wdata[191:160]&u3_sram_wmask[191:160]);else macro_q_3[191:160]<=memory_3[(u3_sram_address[29:25]+160)];end
always @(posedge clk) if(u3_sram_ce[6]) begin if(u3_sram_we[6]) memory_3[(u3_sram_address[34:30]+192)]<=(memory_3[(u3_sram_address[34:30]+192)]&~u3_sram_wmask[223:192])|(u3_sram_wdata[223:192]&u3_sram_wmask[223:192]);else macro_q_3[223:192]<=memory_3[(u3_sram_address[34:30]+192)];end
always @(posedge clk) if(u3_sram_ce[7]) begin if(u3_sram_we[7]) memory_3[(u3_sram_address[39:35]+224)]<=(memory_3[(u3_sram_address[39:35]+224)]&~u3_sram_wmask[255:224])|(u3_sram_wdata[255:224]&u3_sram_wmask[255:224]);else macro_q_3[255:224]<=memory_3[(u3_sram_address[39:35]+224)];end
assign u4_sram_rdata=macro_q_4;
always @(posedge clk) if(u4_sram_ce[0]) begin if(u4_sram_we[0]) memory_4[(u4_sram_address[0:0]*8+0)]<=(memory_4[(u4_sram_address[0:0]*8+0)]&~u4_sram_wmask[2:0])|(u4_sram_wdata[2:0]&u4_sram_wmask[2:0]);else macro_q_4[2:0]<=memory_4[(u4_sram_address[0:0]*8+0)];end
always @(posedge clk) if(u4_sram_ce[1]) begin if(u4_sram_we[1]) memory_4[(u4_sram_address[1:1]*8+1)]<=(memory_4[(u4_sram_address[1:1]*8+1)]&~u4_sram_wmask[5:3])|(u4_sram_wdata[5:3]&u4_sram_wmask[5:3]);else macro_q_4[5:3]<=memory_4[(u4_sram_address[1:1]*8+1)];end
always @(posedge clk) if(u4_sram_ce[2]) begin if(u4_sram_we[2]) memory_4[(u4_sram_address[2:2]*8+2)]<=(memory_4[(u4_sram_address[2:2]*8+2)]&~u4_sram_wmask[8:6])|(u4_sram_wdata[8:6]&u4_sram_wmask[8:6]);else macro_q_4[8:6]<=memory_4[(u4_sram_address[2:2]*8+2)];end
always @(posedge clk) if(u4_sram_ce[3]) begin if(u4_sram_we[3]) memory_4[(u4_sram_address[3:3]*8+3)]<=(memory_4[(u4_sram_address[3:3]*8+3)]&~u4_sram_wmask[11:9])|(u4_sram_wdata[11:9]&u4_sram_wmask[11:9]);else macro_q_4[11:9]<=memory_4[(u4_sram_address[3:3]*8+3)];end
always @(posedge clk) if(u4_sram_ce[4]) begin if(u4_sram_we[4]) memory_4[(u4_sram_address[4:4]*8+4)]<=(memory_4[(u4_sram_address[4:4]*8+4)]&~u4_sram_wmask[14:12])|(u4_sram_wdata[14:12]&u4_sram_wmask[14:12]);else macro_q_4[14:12]<=memory_4[(u4_sram_address[4:4]*8+4)];end
always @(posedge clk) if(u4_sram_ce[5]) begin if(u4_sram_we[5]) memory_4[(u4_sram_address[5:5]*8+5)]<=(memory_4[(u4_sram_address[5:5]*8+5)]&~u4_sram_wmask[17:15])|(u4_sram_wdata[17:15]&u4_sram_wmask[17:15]);else macro_q_4[17:15]<=memory_4[(u4_sram_address[5:5]*8+5)];end
always @(posedge clk) if(u4_sram_ce[6]) begin if(u4_sram_we[6]) memory_4[(u4_sram_address[6:6]*8+6)]<=(memory_4[(u4_sram_address[6:6]*8+6)]&~u4_sram_wmask[20:18])|(u4_sram_wdata[20:18]&u4_sram_wmask[20:18]);else macro_q_4[20:18]<=memory_4[(u4_sram_address[6:6]*8+6)];end
always @(posedge clk) if(u4_sram_ce[7]) begin if(u4_sram_we[7]) memory_4[(u4_sram_address[7:7]*8+7)]<=(memory_4[(u4_sram_address[7:7]*8+7)]&~u4_sram_wmask[23:21])|(u4_sram_wdata[23:21]&u4_sram_wmask[23:21]);else macro_q_4[23:21]<=memory_4[(u4_sram_address[7:7]*8+7)];end
assign u5_sram_rdata=macro_q_5;
always @(posedge clk) if(u5_sram_ce[0]) begin if(u5_sram_we[0]) memory_5[(u5_sram_address[0:0]+0)]<=(memory_5[(u5_sram_address[0:0]+0)]&~u5_sram_wmask[1:0])|(u5_sram_wdata[1:0]&u5_sram_wmask[1:0]);else macro_q_5[1:0]<=memory_5[(u5_sram_address[0:0]+0)];end
assign u6_sram_rdata=macro_q_6;
always @(posedge clk) if(u6_sram_ce[0]) begin if(u6_sram_we[0]) memory_6[(u6_sram_address[7:0]*1+0)]<=(memory_6[(u6_sram_address[7:0]*1+0)]&~u6_sram_wmask[31:0])|(u6_sram_wdata[31:0]&u6_sram_wmask[31:0]);else macro_q_6[31:0]<=memory_6[(u6_sram_address[7:0]*1+0)];end
initial begin
for(init_0=0;init_0<2;init_0=init_0+1) memory_0[init_0]=((init_0*37)^19)&1'd1;
for(init_1=0;init_1<16;init_1=init_1+1) memory_1[init_1]=((init_1*37)^19)&8'd255;
for(init_2=0;init_2<8;init_2=init_2+1) memory_2[init_2]=((init_2*37)^19)&5'd31;
for(init_3=0;init_3<256;init_3=init_3+1) memory_3[init_3]=((init_3*37)^19)&32'd4294967295;
for(init_4=0;init_4<8;init_4=init_4+1) memory_4[init_4]=((init_4*37)^19)&3'd7;
for(init_5=0;init_5<2;init_5=init_5+1) memory_5[init_5]=((init_5*37)^19)&2'd3;
for(init_6=0;init_6<256;init_6=init_6+1) memory_6[init_6]=((init_6*37)^19)&32'd4294967295;
$readmemh("vectors_0.txt",vectors_0);
$readmemh("vectors_1.txt",vectors_1);
$readmemh("vectors_2.txt",vectors_2);
$readmemh("vectors_3.txt",vectors_3);
$readmemh("vectors_4.txt",vectors_4);
$readmemh("vectors_5.txt",vectors_5);
$readmemh("vectors_6.txt",vectors_6);
for(cycle=0;cycle<320;cycle=cycle+1)begin clk=0;
{u0_rst_n,u0_in_valid,u0_in_write,u0_in_address,u0_in_data,u0_in_mask,u0_in_tag,u0_out_ready,u0_enable}=vectors_0[cycle][44:36];
{u1_rst_n,u1_in_valid,u1_in_write,u1_in_address,u1_in_data,u1_in_mask,u1_in_tag,u1_out_ready,u1_enable}=vectors_1[cycle][409:318];
{u2_rst_n,u2_in_valid,u2_in_write,u2_in_address,u2_in_data,u2_in_mask,u2_in_tag,u2_out_ready,u2_enable}=vectors_2[cycle][400:350];
{u3_rst_n,u3_in_valid,u3_in_write,u3_in_address,u3_in_data,u3_in_mask,u3_in_tag,u3_out_ready,u3_enable}=vectors_3[cycle][4518:3908];
{u4_rst_n,u4_in_valid,u4_in_write,u4_in_address,u4_in_data,u4_in_mask,u4_in_tag,u4_out_ready,u4_enable}=vectors_4[cycle][500:458];
{u5_rst_n,u5_in_valid,u5_in_write,u5_in_address,u5_in_data,u5_in_mask,u5_in_tag,u5_out_ready,u5_enable}=vectors_5[cycle][70:54];
{u6_rst_n,u6_in_valid,u6_in_write,u6_in_address,u6_in_data,u6_in_mask,u6_in_tag,u6_out_ready,u6_enable}=vectors_6[cycle][896:658];
#1;
if({u0_in_ready,u0_bank_valid,u0_bank_ready,u0_bank_lane,u0_bank_write,u0_bank_address,u0_bank_data,u0_bank_mask,u0_bank_rdata,u0_out_valid,u0_out_data,u0_out_tag,u0_sram_ce,u0_sram_we,u0_sram_address,u0_sram_wdata,u0_sram_wmask} !== vectors_0[cycle][35:19])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=0 phase=before",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_0 !== vectors_0[cycle][1:1])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=0 phase=before macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u1_in_ready,u1_bank_valid,u1_bank_ready,u1_bank_lane,u1_bank_write,u1_bank_address,u1_bank_data,u1_bank_mask,u1_bank_rdata,u1_out_valid,u1_out_data,u1_out_tag,u1_sram_ce,u1_sram_we,u1_sram_address,u1_sram_wdata,u1_sram_wmask} !== vectors_1[cycle][317:175])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=1 phase=before",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_1 !== vectors_1[cycle][31:16])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=1 phase=before macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u2_in_ready,u2_bank_valid,u2_bank_ready,u2_bank_lane,u2_bank_write,u2_bank_address,u2_bank_data,u2_bank_mask,u2_bank_rdata,u2_out_valid,u2_out_data,u2_out_tag,u2_sram_ce,u2_sram_we,u2_sram_address,u2_sram_wdata,u2_sram_wmask} !== vectors_2[cycle][349:195])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=2 phase=before",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_2 !== vectors_2[cycle][39:20])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=2 phase=before macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u3_in_ready,u3_bank_valid,u3_bank_ready,u3_bank_lane,u3_bank_write,u3_bank_address,u3_bank_data,u3_bank_mask,u3_bank_rdata,u3_out_valid,u3_out_data,u3_out_tag,u3_sram_ce,u3_sram_we,u3_sram_address,u3_sram_wdata,u3_sram_wmask} !== vectors_3[cycle][3907:2210])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=3 phase=before",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_3 !== vectors_3[cycle][511:256])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=3 phase=before macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u4_in_ready,u4_bank_valid,u4_bank_ready,u4_bank_lane,u4_bank_write,u4_bank_address,u4_bank_data,u4_bank_mask,u4_bank_rdata,u4_out_valid,u4_out_data,u4_out_tag,u4_sram_ce,u4_sram_we,u4_sram_address,u4_sram_wdata,u4_sram_wmask} !== vectors_4[cycle][457:253])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=4 phase=before",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_4 !== vectors_4[cycle][47:24])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=4 phase=before macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u5_in_ready,u5_bank_valid,u5_bank_ready,u5_bank_lane,u5_bank_write,u5_bank_address,u5_bank_data,u5_bank_mask,u5_bank_rdata,u5_out_valid,u5_out_data,u5_out_tag,u5_sram_ce,u5_sram_we,u5_sram_address,u5_sram_wdata,u5_sram_wmask} !== vectors_5[cycle][53:29])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=5 phase=before",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_5 !== vectors_5[cycle][3:2])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=5 phase=before macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u6_in_ready,u6_bank_valid,u6_bank_ready,u6_bank_lane,u6_bank_write,u6_bank_address,u6_bank_data,u6_bank_mask,u6_bank_rdata,u6_out_valid,u6_out_data,u6_out_tag,u6_sram_ce,u6_sram_we,u6_sram_address,u6_sram_wdata,u6_sram_wmask} !== vectors_6[cycle][657:361])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=6 phase=before",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_6 !== vectors_6[cycle][63:32])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=6 phase=before macro_q",cycle);$fatal(1,"independent SRAM output");end
clk=1;#1;
if({u0_in_ready,u0_bank_valid,u0_bank_ready,u0_bank_lane,u0_bank_write,u0_bank_address,u0_bank_data,u0_bank_mask,u0_bank_rdata,u0_out_valid,u0_out_data,u0_out_tag,u0_sram_ce,u0_sram_we,u0_sram_address,u0_sram_wdata,u0_sram_wmask} !== vectors_0[cycle][18:2])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=0 phase=after",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_0 !== vectors_0[cycle][0:0])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=0 phase=after macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u1_in_ready,u1_bank_valid,u1_bank_ready,u1_bank_lane,u1_bank_write,u1_bank_address,u1_bank_data,u1_bank_mask,u1_bank_rdata,u1_out_valid,u1_out_data,u1_out_tag,u1_sram_ce,u1_sram_we,u1_sram_address,u1_sram_wdata,u1_sram_wmask} !== vectors_1[cycle][174:32])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=1 phase=after",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_1 !== vectors_1[cycle][15:0])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=1 phase=after macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u2_in_ready,u2_bank_valid,u2_bank_ready,u2_bank_lane,u2_bank_write,u2_bank_address,u2_bank_data,u2_bank_mask,u2_bank_rdata,u2_out_valid,u2_out_data,u2_out_tag,u2_sram_ce,u2_sram_we,u2_sram_address,u2_sram_wdata,u2_sram_wmask} !== vectors_2[cycle][194:40])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=2 phase=after",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_2 !== vectors_2[cycle][19:0])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=2 phase=after macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u3_in_ready,u3_bank_valid,u3_bank_ready,u3_bank_lane,u3_bank_write,u3_bank_address,u3_bank_data,u3_bank_mask,u3_bank_rdata,u3_out_valid,u3_out_data,u3_out_tag,u3_sram_ce,u3_sram_we,u3_sram_address,u3_sram_wdata,u3_sram_wmask} !== vectors_3[cycle][2209:512])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=3 phase=after",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_3 !== vectors_3[cycle][255:0])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=3 phase=after macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u4_in_ready,u4_bank_valid,u4_bank_ready,u4_bank_lane,u4_bank_write,u4_bank_address,u4_bank_data,u4_bank_mask,u4_bank_rdata,u4_out_valid,u4_out_data,u4_out_tag,u4_sram_ce,u4_sram_we,u4_sram_address,u4_sram_wdata,u4_sram_wmask} !== vectors_4[cycle][252:48])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=4 phase=after",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_4 !== vectors_4[cycle][23:0])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=4 phase=after macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u5_in_ready,u5_bank_valid,u5_bank_ready,u5_bank_lane,u5_bank_write,u5_bank_address,u5_bank_data,u5_bank_mask,u5_bank_rdata,u5_out_valid,u5_out_data,u5_out_tag,u5_sram_ce,u5_sram_we,u5_sram_address,u5_sram_wdata,u5_sram_wmask} !== vectors_5[cycle][28:4])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=5 phase=after",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_5 !== vectors_5[cycle][1:0])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=5 phase=after macro_q",cycle);$fatal(1,"independent SRAM output");end
if({u6_in_ready,u6_bank_valid,u6_bank_ready,u6_bank_lane,u6_bank_write,u6_bank_address,u6_bank_data,u6_bank_mask,u6_bank_rdata,u6_out_valid,u6_out_data,u6_out_tag,u6_sram_ce,u6_sram_we,u6_sram_address,u6_sram_wdata,u6_sram_wmask} !== vectors_6[cycle][360:64])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=6 phase=after",cycle);$fatal(1,"independent synchronous SRAM system");end checked=checked+1;
if(macro_q_6 !== vectors_6[cycle][31:0])begin $display("SRAM_BRIDGE_MISMATCH cycle=%0d instance=6 phase=after macro_q",cycle);$fatal(1,"independent SRAM output");end
end
$display("SRAM_BRIDGE_PASS checked=%0d",checked);$finish;end endmodule
