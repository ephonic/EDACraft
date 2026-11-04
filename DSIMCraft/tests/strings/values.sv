`timescale 1ns/1ps
module top;
typedef enum logic[3:0] {ZERO=0, LONG_ENUM_MEMBER_NAME=5, EX=4'bx101, EZ=4'bz101} e_t;
e_t e; string s="AbC001", t; integer i;reg z=1'bx;
initial begin

#1;e=LONG_ENUM_MEMBER_NAME;t=e.name; $display("TRACE name [%s] [%s]",t,e.name());
e=e_t'(9);$display("TRACE bad [%s]",e.name());e=EX;$display("TRACE x [%s]",e.name());e=EZ;$display("TRACE z [%s]",e.name());
$display("TRACE methods %0d %0d [%s] [%s] [%s] %0d %0d",s.len(),s.getc(0),s.substr(1,3),s.tolower(),s.toupper(),s.compare("AbC000"),s.icompare("aBc001"));
$display("TRACE bounds %0d %0d [%s] [%s] [%s]",s.getc(-1),s.getc(9),s.substr(-1,2),s.substr(2,99),s.substr(4,2));
t=z ? "one" : "two";if(t!="dfe") $fatal(1,"unknown condition");$display("TRACE mux [%s]",t);
$display("TRACE concat [%s]",{s,"ZZ"});#1;$finish;
end endmodule
