module top;
reg c,d,e,a,oe,seed,td,te,ta,toe; reg [31:0] is,id,ie,ia,io,i; wire [5:0] y;
dut u(c,d,e,a,oe,y);
initial begin
i=0;
for(is=0; is<32'd3; is=is+32'd1) begin
case(is)
32'd0: seed=1'b0;
32'd1: seed=1'b1;
32'd2: seed=1'bx;
endcase
for(id=0; id<32'd4; id=id+32'd1) begin
case(id)
32'd0: td=1'b0;
32'd1: td=1'b1;
32'd2: td=1'bx;
32'd3: td=1'bz;
endcase
for(ie=0; ie<32'd4; ie=ie+32'd1) begin
case(ie)
32'd0: te=1'b0;
32'd1: te=1'b1;
32'd2: te=1'bx;
32'd3: te=1'bz;
endcase
for(ia=0; ia<32'd4; ia=ia+32'd1) begin
case(ia)
32'd0: ta=1'b0;
32'd1: ta=1'b1;
32'd2: ta=1'bx;
32'd3: ta=1'bz;
endcase
for(io=0; io<32'd4; io=io+32'd1) begin
case(io)
32'd0: toe=1'b0;
32'd1: toe=1'b1;
32'd2: toe=1'bx;
32'd3: toe=1'bz;
endcase
c=0; d=seed; e=1; a=0; oe=0; #1;
c=1; #1;
c=0; #1;
d=td; e=te; a=ta; oe=toe; #1;
c=1; #0;
$display("TRACE i=%0d phase=0 d=%b e=%b a=%b oe=%b y=%b",i,d,e,a,oe,y);
#1;
$display("TRACE i=%0d phase=1 d=%b e=%b a=%b oe=%b y=%b",i,d,e,a,oe,y);
i=i+32'd1;
end end end end end
$finish;
end endmodule
