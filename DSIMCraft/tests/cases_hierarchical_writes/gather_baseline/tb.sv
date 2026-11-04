module tb_compare;
reg clk,rst_n;
reg frame_clock;
integer i;
reg [0:0] in_valid;
reg [0:0] in_ready;
reg [0:0] in_wen;
reg [0:0] in_mode;
reg [2:0] in_a;
reg [2:0] in_b;
reg [2:0] in_c;
reg [2:0] in_d;
reg [2:0] in_addr;
reg [15:0] in_data;
reg [12:0] in_tag;
wire out_ready,out_valid;
wire [15:0] out_value;
wire [12:0] out_tag;
reg [49:0] frames[0:3071];
dut dut(.clk(clk),.rst_n(rst_n),.in_valid(in_valid),.in_ready(in_ready),.in_wen(in_wen),.in_mode(in_mode),.in_a(in_a),.in_b(in_b),.in_c(in_c),.in_d(in_d),.in_addr(in_addr),.in_data(in_data),.in_tag(in_tag),.out_ready(out_ready),.out_valid(out_valid),.out_value(out_value),.out_tag(out_tag));
initial begin clk=0;rst_n=1;
dut.words[0]=16'd9029;
dut.words[1]=16'd18058;
dut.words[2]=16'd27087;
dut.words[3]=16'd36116;
dut.words[4]=16'd45145;
dut.words[5]=16'd54174;
dut.words[6]=16'd63203;
dut.words[7]=16'd6696;
$readmemh("stimulus.hex",frames);
for(i=0;i<3072;i=i+1) begin
{rst_n,frame_clock,in_valid,in_ready,in_wen,in_mode,in_a,in_b,in_c,in_d,in_addr,in_data,in_tag}=frames[i];
#2;
$display("RTL_DUAL_TRACE %0d ready=%b valid=%b value=%b tag=%b history=%b mem0=%b mem1=%b mem2=%b mem3=%b mem4=%b mem5=%b mem6=%b mem7=%b",2*i,out_ready,out_valid,out_value,out_tag,dut.history,dut.words[0],dut.words[1],dut.words[2],dut.words[3],dut.words[4],dut.words[5],dut.words[6],dut.words[7]);
#1;if(frame_clock) clk=1;#2;
$display("RTL_DUAL_TRACE %0d ready=%b valid=%b value=%b tag=%b history=%b mem0=%b mem1=%b mem2=%b mem3=%b mem4=%b mem5=%b mem6=%b mem7=%b",2*i+1,out_ready,out_valid,out_value,out_tag,dut.history,dut.words[0],dut.words[1],dut.words[2],dut.words[3],dut.words[4],dut.words[5],dut.words[6],dut.words[7]);
clk=0;#1;end
$display("RTL_DUAL_DONE events=6144 outputs=13");$finish;end endmodule
