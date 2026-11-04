module top; reg a; wire y,c,f; dut u(a,y,c,f); initial begin
a=1'b0; #1; $display("TRACE a=%b y=%b constant=%b floating=%b",a,y,c,f);
a=1'b1; #1; $display("TRACE a=%b y=%b constant=%b floating=%b",a,y,c,f);
a=1'bx; #1; $display("TRACE a=%b y=%b constant=%b floating=%b",a,y,c,f);
a=1'bz; #1; $display("TRACE a=%b y=%b constant=%b floating=%b",a,y,c,f);
$finish; end endmodule
