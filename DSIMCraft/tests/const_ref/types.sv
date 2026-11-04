`timescale 1ns/1ps
module top;
typedef enum logic[2:0] {IDLE=0,BUSY=3} state_t;
typedef struct packed {logic[7:0] a;bit[3:0] b;} pair_t;
state_t state=IDLE;pair_t pair_value;
logic[127:0] wide=128'hx123;bit[7:0] bits=0;
integer words[0:1],index=0,result=0;
task automatic inspect(const ref state_t s,const ref pair_t p,const ref logic[127:0] w,const ref bit[7:0] b,const ref integer word);
 #2;
 if(s!=BUSY||p.a!=8'h5a||p.b!=4'hf||w!==128'hz987||b!=8'hff||word!=11)$fatal(1,"const ref live type identity");
 result=word;
endtask
initial begin
 pair_value=0;words[0]=1;words[1]=99;
 fork
  inspect(state,pair_value,wide,bits,words[index]);
  begin #1;state=BUSY;pair_value=12'h5af;wide=128'hz987;bits=8'hff;words[0]=11;index=1;end
 join
 $display("TRACE types %0d %h %h %h %0d",state,pair_value,wide,bits,result);
end
endmodule
