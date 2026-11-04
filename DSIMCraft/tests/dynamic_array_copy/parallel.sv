`timescale 1ns/1ps
module lane #(parameter STEP=3,PERIOD=2)(output logic[7:0]q[5:6],output logic error);
logic[7:0]a[1:0][0:1];integer i,k;
initial begin error=0;a[1][0]=STEP;a[1][1]=STEP+1;a[0][0]=2*STEP;a[0][1]=2*STEP+1;
for(k=0;k<8;k=k+1)begin i=k%2;#1;q=a[i];if(q[5]!==a[i][0]||q[6]!==a[i][1])error=1;#(PERIOD-1);a[i][0]=a[i][0]+STEP;a[i][1]=a[i][1]+STEP;end
end
wire [31:0] observe_a={a[0][1],a[0][0],a[1][1],a[1][0]};
wire [15:0] observe_q={q[6],q[5]};
endmodule
module top;
logic[7:0]a[0:1],b[3:2];logic ea,eb;
lane #(3,2)left(a,ea);lane #(7,3)right(b,eb);
wire [15:0] observe_a={a[1],a[0]};
wire [15:0] observe_b={b[2],b[3]};
endmodule
