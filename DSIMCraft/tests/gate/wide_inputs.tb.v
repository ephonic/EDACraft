module top;
reg a,b; wire [3:0] plain,cat,sp,sc,sw,open; wire [1:0] short_bus,ascending; wire one;
dut u(a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
initial begin
a=1'b0; b=1'b0; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'b0; b=1'b1; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'b0; b=1'bx; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'b0; b=1'bz; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'b1; b=1'b0; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'b1; b=1'b1; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'b1; b=1'bx; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'b1; b=1'bz; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bx; b=1'b0; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bx; b=1'b1; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bx; b=1'bx; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bx; b=1'bz; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bz; b=1'b0; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bz; b=1'b1; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bz; b=1'bx; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);
a=1'bz; b=1'bz; #1;
$display("TRACE a=%b b=%b plain=%b cat=%b sp=%b sc=%b sw=%b short_bus=%b ascending=%b one=%b open=%b",a,b,plain,cat,sp,sc,sw,short_bus,ascending,one,open);

$finish; end endmodule
