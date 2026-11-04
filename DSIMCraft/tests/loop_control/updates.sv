`timescale 1ns/1ps
module top;
reg signed [129:0] wide;
reg [79:0] mem[0:2];
reg [7:0] packed_value;
integer idx=0,i;
reg [239:0] observe;
initial begin : work
 wide=-130'sd2;
 packed_value=8'hff;
 mem[0]=80'hffffffffffffffffffff;mem[1]=80'h0123456789abcdef0123;mem[2]=0;
 ++wide;wide++;wide--;--wide;
 packed_value++;--packed_value;
 mem[idx]++;
 idx=1;++mem[idx][15:8];mem[idx][7:0]--;
 #1 $display("TRACE updates %h %h %h %h",wide,packed_value,mem[0],mem[1]);
 wide=130'sbx01;wide++;
 mem[2]=80'bz;--mem[2];
 idx=-1;mem[idx]++;
 for(i=0;i<3;i++)begin
  if(i==1)continue;
  mem[i]<=#2 80'h55+i;
 end
 #3 observe={mem[2],mem[1],mem[0]};
 $display("TRACE delayed %h %h",wide,observe);
 $finish;
end
endmodule
