`timescale 1ns/1ps
module lane #(parameter STEP=3,PERIOD=2)(output logic[7:0]q[5:6],output logic error);
 logic[7:0]a[0:1];integer i;
wire [15:0] observe_a={a[1],a[0]};
wire [15:0] observe_q={q[6],q[5]};
 initial begin error=0;a[0]=STEP;a[1]=STEP+1;
 for(i=0;i<8;i=i+1)begin
 q=#1 a;
 if(q[5]!==a[0]||q[6]!==a[1])error=1;
 #(PERIOD-1);a[0]=a[0]+STEP;a[1]=a[1]+STEP;
 end
 end
endmodule
module top;
 logic[7:0]a[0:1],b[3:2];logic ea,eb;
 lane #(3,2)left(a,ea);lane #(7,3)right(b,eb);
wire [15:0] observe_a={a[1],a[0]};
wire [15:0] observe_b={b[3],b[2]};
endmodule
