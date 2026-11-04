module top;
reg a,b; reg [3:0] ext; wire [3:0] bus,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf; wire [5:0] wide; wire tied; assign bus=ext;
dut u(a,b,bus,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied);
initial begin
a=1'b0; b=1'b0; ext=4'b0000; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'b0; b=1'b1; ext=4'b0101; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'b0; b=1'bx; ext=4'b0x0x; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'b0; b=1'bz; ext=4'b0z0z; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'b1; b=1'b0; ext=4'b1010; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'b1; b=1'b1; ext=4'b1111; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'b1; b=1'bx; ext=4'b1x1x; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'b1; b=1'bz; ext=4'b1z1z; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bx; b=1'b0; ext=4'bx0x0; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bx; b=1'b1; ext=4'bx1x1; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bx; b=1'bx; ext=4'bxxxx; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bx; b=1'bz; ext=4'bxzxz; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bz; b=1'b0; ext=4'bz0z0; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bz; b=1'b1; ext=4'bz1z1; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bz; b=1'bx; ext=4'bzxzx; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);
a=1'bz; b=1'bz; ext=4'bzzzz; #1;
$display("TRACE a=%b b=%b direct=%b cat=%b rd=%b rc=%b rw=%b trunc=%b fill=%b narrow=%b opened=%b ri=%b leaf=%b wide=%b tied=%b bus=%b",a,b,direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,wide,tied,bus);

$finish; end endmodule
