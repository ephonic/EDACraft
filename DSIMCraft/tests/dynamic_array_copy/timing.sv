`timescale 1ns/1ps
module top;
logic[7:0]a[1:0][2:3],b[5:4][1:0],row[0:1],clocked[0:1];integer src,dst,delay_value;logic clk;
function automatic integer delay_ticks(input integer v);delay_ticks=v;endfunction
always_ff @(posedge clk) clocked<=a[src];
initial begin
clk=0;a[1][2]=10;a[1][3]=11;a[0][2]=20;a[0][3]=21;b[5][1]=0;b[5][0]=0;b[4][1]=0;b[4][0]=0;src=1;dst=5;delay_value=2;
b[dst]<=#(delay_ticks(delay_value)) a[src];src=0;dst=4;
#1;a[1][2]=99;b[dst]<=#2 a[src];clk=1;src=1;
#1.001;if(b[5][1]!==10||b[5][0]!==11||b[4][1]!==0)$fatal(1,"NBA address or source sampling");
#1;if(b[4][1]!==20||b[4][0]!==21||clocked[0]!==99||clocked[1]!==11)$fatal(1,"NBA delivery");
row=a[src];row<=row;#1;
$display("TRACE timing %h %h %h %h %h",b[5][1],b[5][0],b[4][1],b[4][0],clocked[0]);$finish;
end
wire [31:0] observe_a={a[0][3],a[0][2],a[1][3],a[1][2]};
wire [31:0] observe_b={b[4][0],b[4][1],b[5][0],b[5][1]};
wire [15:0] observe_row={row[1],row[0]};
wire [15:0] observe_clocked={clocked[1],clocked[0]};
endmodule
