"""Waveform fixtures whose settled values avoid Active-region observation races."""
CASES={
'rtl_states':'''module leaf(input [7:0] a,output [7:0] y); assign y=a; endmodule
module top;
reg clk; reg [7:0] d; reg [15:8] q; wire [7:0] y;
leaf u(d,y);
initial begin
 clk=0;d=0;q=8'h12;
 #1;d=8'h3c;clk=1;
 #0;d=8'h5a;
 #0;clk=0;
 #1;d=8'b10xz01z0;
 #1;d=8'hff;
 #1;$display("TRACE q=%h y=%h",q,y);$finish;
end
always @(posedge clk) q<=d;
endmodule
''',
'ranges_escaped':r'''module top;
reg [5:5] one;reg [0:0] single;reg [63:0] wide;reg \name.with.dot ;
initial begin
one=1'bx;single=1'bz;wide=64'bx;\name.with.dot =1'b0;
#1;one=1'bz;single=1;wide=64'hfedcba9876543210;\name.with.dot =1'b1;
#1;one=0;single=0;wide=64'h0000000000000f0f;
#1;$display("TRACE wide=%h",wide);$finish;
end endmodule
''',
'quiet_finish':'''module top;
reg a;
initial begin a=0;#1;a=1;#0;a=0;#4;$display("TRACE quiet=%b",a);$finish;end
endmodule
''',
}
EXPECTED={'rtl_states':['TRACE q=3c y=ff'],'ranges_escaped':['TRACE wide=0000000000000f0f'],'quiet_finish':['TRACE quiet=0']}

CASES={name:"`timescale 10ps/10ps\n"+source for name,source in CASES.items()}
