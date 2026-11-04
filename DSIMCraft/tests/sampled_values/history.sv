`timescale 1ns/1ps
module top;
reg clk=0;logic [7:0] q=8'h39,prev=8'h39,older=8'h39,g1=8'h39,g2=8'h39;
logic gate=0;integer checks=0,errors=0;
logic [129:0] wide=130'h3123456789abcdef0123456789abcdef01,wp=130'h3123456789abcdef0123456789abcdef01;
logic signed[7:0] neg=-7,np=-7;bit [4:0] two=17,tp=17;
initial begin
 #1;q=3;wide='x;neg=-3;two=2;
 repeat(8)begin #3;clk=1;#1;clk=0;q=q+7;wide={wide[128:0],1'bz};neg=neg-1;two=two+1;gate=~gate;end
 #2;$display("TRACE history %0d %0d",checks,errors);if(checks!=8||errors) $fatal(1,"FAIL history");$finish;
end
always @(posedge clk) begin prev<=q;older<=prev;wp<=wide;np<=neg;tp<=two;if(gate)begin g1<=q;g2<=g1;end end
check: assert property(@(posedge clk)
 ($past(q)===prev)&&($past(q,2)===older)&&($past(q,1,gate)===g1)&&($past(q,2,gate)===g2)&&
 ($past(wide)===wp)&&($past(neg)===np)&&($past(neg)<0)&&($past(two)===tp)&&($bits($past(wide))==130)) checks=checks+1;else errors=errors+1;
endmodule
