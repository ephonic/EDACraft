module top;
reg c,d,a,oe,r; wire [7:0] y;
dut u(c,d,a,oe,r,y);
initial begin
c=0;d=0;a=1;oe=1;r=1;#1;r=0;#1;d=1;#1;
c=1;#0;
$display("TRACE clock_inactive c=%b y=%b",c,y);
#1;
$display("TRACE clock_settled c=%b y=%b",c,y);
c=0;#1;a=0;oe=0;#0;
$display("TRACE outputs_active c=%b y=%b",c,y);
#1;r=1;#0;
$display("TRACE reset_inactive c=%b y=%b",c,y);
#1;
$display("TRACE reset_settled c=%b y=%b",c,y);
r=0;#1;d=0;a=1;oe=1;#1;c=1;#0;
$display("TRACE pulse_rise c=%b y=%b",c,y);
c=0;#0;
$display("TRACE pulse_fall c=%b y=%b",c,y);
#1;
$display("TRACE pulse_settled c=%b y=%b",c,y);
d=1;#1;c<=1;#0;
$display("TRACE nba_clock c=%b y=%b",c,y);
#1;
$display("TRACE nba_settled c=%b y=%b",c,y);
$finish;
end endmodule
