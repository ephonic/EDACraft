`timescale 1ns/1ps
module top;
logic[7:0]a[3:2][7:6][1:2],b[0:1][5:4],row[0:1];integer i,j,calls,result;
wire[7:0]nets[3:2][0:1];
assign nets[3][0]=a[3][7][1];assign nets[3][1]=a[3][7][2];assign nets[2][0]=a[2][7][1];assign nets[2][1]=a[2][7][2];
function automatic integer pick(input integer v);
logic[7:0]local_words[0:1];begin local_words[0]=v;calls=calls+1;pick=local_words[0];end
endfunction
function automatic integer sum(input integer v);
logic[7:0]x[1:0][0:1],y[3:2];integer k;
begin x[1][0]=v;x[1][1]=v+1;k=1;y=x[k];return y[3]+y[2];end
endfunction
always_comb b=a[i];
initial begin
calls=0;foreach(a[u,v,w])a[u][v][w]=(u-2)*40+(v-6)*10+w;
i=3;j=7;row=a[pick(i)][j];result=sum(9);
#1;if(row[0]!==51||row[1]!==52||b[0][5]!==51||b[1][4]!==42||calls!==1||result!==19)$fatal(1,"indexed initial");
i=2;#1;if(b[0][5]!==11||b[1][4]!==2)$fatal(1,"index sensitivity");
a[2][7][1]=99;#1;if(b[0][5]!==99)$fatal(1,"word sensitivity");
a[i][j]=row;#1;if(b[0][5]!==51||b[0][4]!==52)$fatal(1,"dynamic target");
row=nets[i];#1;if(row[0]!==51||row[1]!==52)$fatal(1,"net source");
$display("TRACE indexed %h %h %h %0d %0d",row[0],row[1],b[0][5],calls,result);$finish;
end
wire [63:0] observe_a={a[2][6][2],a[2][6][1],a[2][7][2],a[2][7][1],a[3][6][2],a[3][6][1],a[3][7][2],a[3][7][1]};
wire [31:0] observe_b={b[1][4],b[1][5],b[0][4],b[0][5]};
wire [15:0] observe_row={row[1],row[0]};
wire[31:0]observe_nets={nets[2][1],nets[2][0],nets[3][1],nets[3][0]};
endmodule
