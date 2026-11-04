`timescale 1ns/1ps
module top;
typedef enum logic signed[129:0] {NEG=-2,BIG=130'h1000000000000000001,SMALL=7} Wide;
typedef enum logic[2:0] {A=1,B=4,C=6} E;
typedef struct packed {logic[1:0] tag;E state;} Packed;
Wide w;E words[1:2][3:4],chosen;Packed item;
integer x=1,y=3;
wire[11:0] image={words[1][3],words[1][4],words[2][3],words[2][4]};
initial begin
w=NEG;if(w.next()!==BIG||w.prev()!==SMALL||w.first()!==NEG)$fatal(1,"wide values");
w=w.next(2).prev();if(w!==BIG||w.num()!==3||$bits(w.next())!==130)$fatal(1,"wide chain");
words[1][3]=A;words[1][4]=B;words[2][3]=C;words[2][4]=A;
chosen=words[x++][y++].next();if(chosen!==B||x!==2||y!==4)$fatal(1,"array once");
words[x][y]=words[x][y].prev();item.tag=2;item.state=chosen;
item.state=item.state.next();if(item.state!==C)$fatal(1,"packed receiver");
#1;w<=#1 w.prev();chosen=item.state.prev(2);
if(chosen!==A)$fatal(1,"member identity");
#2;if(w!==NEG)$fatal(1,"wide nba");
$display("TRACE types %h %h %0d %0d %0d",w,image,item,chosen,x+y);
end
endmodule
