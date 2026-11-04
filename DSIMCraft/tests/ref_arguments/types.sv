`timescale 1ns/1ps
module top;
typedef enum logic[2:0] {IDLE=0,BUSY=3} state_t;
typedef struct packed {logic[7:0] a;bit[3:0] b;} pair_t;
state_t state=IDLE;pair_t pair_value;
logic[7:0] data=8'hx5;
bit[7:0] bits=0;
integer x=1,q=0;
function automatic integer use_default(ref integer a=x);a+=2;return a;endfunction
task automatic change(ref state_t a,ref pair_t b,ref logic[7:0] c,ref bit[7:0] d);
 a=BUSY;b.a=8'h5a;b.b=4'hf;c=8'hz7;d=8'hff;
endtask
initial begin
 pair_value=0;
 change(state,pair_value,data,bits);
 q=use_default();q+=use_default(.a());
 $display("TRACE types %0d %h %h %h %0d %0d",state,pair_value,data,bits,x,q);
 if(state!=BUSY||pair_value!=12'h5af||data!==8'hz7||bits!=8'hff||x!=5||q!=8)$fatal(1,"ref type identity/default binding");
end
endmodule
