`timescale 1ns/1ps
module top;
typedef enum logic[2:0]{IDLE=0,BUSY=3} state_t;
typedef struct packed{logic[7:0]a;bit[3:0]b;} pair_t;
state_t state[0:1];pair_t pair_value[0:1];logic[129:0]wide[2];bit[7:0]bits[2];integer count=0;
task automatic change(ref state_t a[2],ref pair_t b[2],output logic[129:0] c[2],output bit[7:0] d[2]);
 a[0]=BUSY;b[1].a=8'h5a;b[1].b=4'hf;c[0]=130'h200000000000000000000000000000001;d[0]=8'hff;
endtask
// Classic array formals use the same binding path as ANSI declarations.
task automatic classic;input bit[7:0]a[2];output integer n;begin n=a[0]+a[1]+$size(a);end endtask
initial begin
 state[0]=IDLE;state[1]=IDLE;pair_value[0]='0;pair_value[1]='0;
 change(state,pair_value,wide,bits);classic(bits,count);
 $display("TRACE types %0d %h %h %h %0d",state[0],pair_value[1],bits[0],bits[1],count);
 if(state[0]!=BUSY||state[1]!=IDLE||pair_value[1]!=12'h5af||wide[0]!==130'h200000000000000000000000000000001||wide[1]!==130'bx||bits[0]!=255||bits[1]!=0||count!=257)$fatal(1,"typed array formals");
end
endmodule
