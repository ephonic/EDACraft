`timescale 1ns/1ps
module top;
typedef struct packed {bit[3:0] b;logic signed[3:0] l;} mixed_t;
typedef mixed_t alias_t;
typedef union packed {bit[7:0] b;logic[7:0] l;mixed_t parts;} view_t;
typedef struct packed {bit[64:0] upper;bit[64:0] lower;} wide_t;
typedef enum logic[1:0]{IDLE,RUN,DONE} state_t;
typedef struct packed {state_t state;logic[5:0] data;} packet_t;
typedef struct packed {mixed_t inner;packet_t packet;logic[1:0] tag;} nested_t;
typedef struct packed signed {logic signed[3:0] hi;logic[3:0] lo;} signed_t;
alias_t s;view_t u;wide_t w;packet_t packet;nested_t n;signed_t signed_s;
logic signed[63:0] extended;
initial begin
 if(s!==8'hxx||s.b!==4'b0||s.l!==4'bxxxx||w!==130'b0)$fatal(1,"defaults");
 s='x;u='x;
 if(s.b!==4'b0||u.b!==8'b0||u!==8'hxx)$fatal(1,"bit view");
 s.b=4'bx1z0;u.b=8'bxz0011zx;
 if(s!==8'bx1z0xxxx||s.b!==4'b0100||u!==8'bxz0011zx)$fatal(1,"raw bit writes");
 s=8'haf;signed_s=8'hf0;extended=s.l;
 if(extended!==-1||signed_s!==-16||s.l>=0||signed_s.hi!==-1)$fatal(1,"signed member");
 s.l>>>=1;s.l-=2;if(s.l!==-3)$fatal(1,"signed update");
 packet=0;packet.state=RUN;packet.state++;packet.data=6'h3f;
 if(packet!==8'hbf||packet.state!==DONE)$fatal(1,"enum member");
 n=0;n.inner=s;n.packet=packet;n.tag=3;
 if(n.inner.l!==-3||n.packet.state!==DONE||n.tag!==3)$fatal(1,"nested member");
 u=8'hab;u.parts.l=3;
 if(u!==8'ha3||u.parts.b!==4'ha)$fatal(1,"union alias");
 w.upper=65'h10000000000000000;w.lower='1;
 if(w[129]!==1||w.lower!==65'h1ffffffffffffffff)$fatal(1,"wide layout");
 #1 $display("TRACE values %h %h %h %h %h %0d",s,u,packet,n,w,extended);
end
endmodule
