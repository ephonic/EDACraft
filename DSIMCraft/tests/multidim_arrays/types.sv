`timescale 1ns/1ps
module top;
typedef struct packed {logic[3:0] tag;logic[7:0] payload;} Word;
typedef enum logic[1:0] {IDLE=1,BUSY=2} State;
Word words[1:2][3:4];State state[1:2][3:4];
bit[7:0] bits[1:2][3:4];integer signed_data[1:2][3:4];logic[64:0] wide[1:2][3:4];
integer x,y,total=0;logic[7:0] q;State chosen;
wire[47:0] image={words[1][3],words[1][4],words[2][3],words[2][4]};
wire[7:0] image_state={state[1][3],state[1][4],state[2][3],state[2][4]};
wire[31:0] image_bits={bits[1][3],bits[1][4],bits[2][3],bits[2][4]};
wire[127:0] image_signed_data={signed_data[1][3],signed_data[1][4],signed_data[2][3],signed_data[2][4]};
wire[259:0] image_wide={wide[1][3],wide[1][4],wide[2][3],wide[2][4]};
initial begin
 for(x=1;x<=2;x++)for(y=3;y<=4;y++)begin
  words[x][y].tag=x;words[x][y].payload=x*16+y;state[x][y]=IDLE;
  bits[x][y]=8'b10xz0110;signed_data[x][y]=-x-y;wide[x][y]=65'h10000000000000001;
 end
 x=2;y=4;words[x][y].payload[3:0]=4'ha;state[x][y]=BUSY;chosen=state[x][y];
 if(chosen!==BUSY || words[x][y].payload!==8'h2a || words[x][y].tag!==2)$fatal(1,"typed word");
 foreach(signed_data[i,j])total+=signed_data[i][j];
 if(total!==-20 || bits[x][y]!==8'h86 || wide[x][y]!==65'h10000000000000001)$fatal(1,"signed two-state wide");
 x=0;q=bits[x][y];if(q!==0)$fatal(1,"two-state invalid read");
 #1;$display("TRACE types %0d %h %0d",total,image,chosen);
end
endmodule
