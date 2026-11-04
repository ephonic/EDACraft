`timescale 1ns/1ps
module tb_compare;
reg clk,rst_n,in_valid,out_ready;reg [12:0] in_data;
reg [6:0] in_tag;reg in_last;wire out_valid,in_ready;
wire [12:0] out_data;wire [6:0] out_tag;wire out_last;
dut u(.clk(clk),.rst_n(rst_n),.in_valid(in_valid),.out_ready(out_ready),.in_data(in_data),.in_tag(in_tag),.in_last(in_last),
.out_valid(out_valid),.in_ready(in_ready),.out_data(out_data),.out_tag(out_tag),.out_last(out_last));
reg [24:0] vectors[0:519];integer i;
initial begin $readmemh("stimulus.hex",vectors);clk=0;rst_n=1;in_valid=0;out_ready=0;in_data=0;in_tag=0;in_last=0;#1;
for(i=0;i<520;i=i+1)begin
clk=0;{in_last,in_tag,in_data,out_ready,in_valid,rst_n}=vectors[i][23:0];#2;
$display("RTL_DUAL_TRACE %0d ready=%b valid=%b data=%b tag=%b last=%b",2*i,in_ready,out_valid,out_data,out_tag,out_last);
clk=vectors[i][24];#2;
$display("RTL_DUAL_TRACE %0d ready=%b valid=%b data=%b tag=%b last=%b",2*i+1,in_ready,out_valid,out_data,out_tag,out_last);
end
$display("RTL_DUAL_DONE events=1040 outputs=5");$finish;end endmodule
module rtl_transport_79785cf07781297a4385bb7a(input wire clk,rst_n,iv,ir,ov,orr,
 input wire [20:0] incoming,outgoing);
integer serial=0;
always @(posedge clk or negedge rst_n) begin
 if(serial==0) $display("RTL_TRANSPORT_V1 id=79785cf07781297a4385bb7a0a7da8a7c54884ffd2f61b53e0da344d19c362b7 scope=%m n=0 event=S");
 serial=serial+1;
 if(serial>100000) $fatal(1,"Transport history event budget exceeded");
 if(rst_n===1'b0) $display("RTL_TRANSPORT_V1 id=79785cf07781297a4385bb7a0a7da8a7c54884ffd2f61b53e0da344d19c362b7 scope=%m n=%0d event=R",serial);
 else $display("RTL_TRANSPORT_V1 id=79785cf07781297a4385bb7a0a7da8a7c54884ffd2f61b53e0da344d19c362b7 scope=%m n=%0d event=C rst=%b iv=%b ir=%b ov=%b orr=%b i=%b o=%b",serial,rst_n,iv,ir,ov,orr,incoming,outgoing);
end
final begin
 if(serial==0) $display("RTL_TRANSPORT_V1 id=79785cf07781297a4385bb7a0a7da8a7c54884ffd2f61b53e0da344d19c362b7 scope=%m n=0 event=S");
 $display("RTL_TRANSPORT_V1 id=79785cf07781297a4385bb7a0a7da8a7c54884ffd2f61b53e0da344d19c362b7 scope=%m n=%0d event=E",serial+1);
end
endmodule
bind dut rtl_transport_79785cf07781297a4385bb7a observer_79785cf07781297a4385bb7a(.clk(clk),.rst_n(rst_n),
 .iv(p.valid_o),.ir(p.ready),
 .ov(c.valid),.orr(c.ready_o),
 .incoming({p.data_o,p.tag_o,p.last_o}),.outgoing({c.data,c.tag,c.last}));
