`timescale 1ns/1ps
module child #(parameter W=8)(input wire clk);
 typedef enum logic[2:0]{A=1,B=3,C=7} state_t;
 typedef struct packed{logic[7:0] data;logic valid;} item_t;
 reg[7:0] mem[2:3][4:5];
 bit[7:0] binary_mem[0:1];
 logic[1:0][3:0] packed_mem[0:1];
 state_t state=B,states[0:1];
 item_t packet;
 integer signed_mem[0:1];
 initial begin
  mem[2][4]=8'h12;mem[2][5]=8'h34;mem[3][4]=8'h56;mem[3][5]=8'h78;
  binary_mem[0]=8'hff;binary_mem[1]=8'h12;packed_mem[0]=8'h5a;packed_mem[1]=8'hc3;
  states[0]=A;states[1]=C;packet.data=8'hab;packet.valid=1;signed_mem[0]=-7;signed_mem[1]=9;
 end
 always @(posedge clk)begin mem[3][5]<=mem[3][5]+1;state<=state.next();end
endmodule
module top;
 reg clk=0;integer i=2,j=4,k=0;reg[7:0] value=0;reg[3:0] nibble=0;
 reg[1:0] unknown_index=2'bxx;
 child a(clk);child #(.W(16)) b(clk);
 always #5 clk=~clk;
 always @* value=a.mem[i][j];
 wire[7:0] observe_24=a.mem[2][4],observe_25=a.mem[2][5],observe_34=a.mem[3][4],observe_35=a.mem[3][5];
 wire[7:0] observe_state0=a.states[0],observe_state1=a.states[1];
 initial begin
  #1;
  if(value!==8'h12||a.mem[3][5]!==8'h78||a.mem[2][5][7:4]!==4'h3)$fatal(1,"FAIL matrix");
  if(a.mem[1][4]!==8'hxx||a.mem[unknown_index][4]!==8'hxx||a.binary_mem[3]!==0)$fatal(1,"FAIL bounds");
  if(a.signed_mem[0]!==-7||a.signed_mem[k]>=0)$fatal(1,"FAIL signed");
  if(a.state.name!="B"||b.state.next().name()!="C"||a.states[k].name()!="A"||a.states[1].prev().name!="B")$fatal(1,"FAIL enum");
  if(a.state.first()!==3'd1||a.state.last()!==3'd7||a.state.num()!==3)$fatal(1,"FAIL enum metadata");
  if(a.packet.data!==8'hab||a.packet.valid!==1)$fatal(1,"FAIL struct");
  if(a.packed_mem[1][0]!==4'h3||a.packed_mem[0][1][2:1]!==2'b10)$fatal(1,"FAIL packed");
  $display("TRACE hierarchy initial %h %s %h",value,a.state.name,a.packet.data);
  i=3;j=5;#1;if(value!==8'h78)$fatal(1,"FAIL implicit index");
  #4;if(value!==8'h79||a.state.name!="C")$fatal(1,"FAIL update");
  $display("TRACE hierarchy update %h %s",value,a.state.name);
  #1;$finish;
 end
endmodule
