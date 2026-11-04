`timescale 1ns/1ps
module top;
 typedef enum logic[1:0] {IDLE=1, BUSY=2} state_t;
 typedef struct packed {bit[3:0] a;logic signed[7:0] b;state_t mode;} item_t;
 typedef struct packed {item_t inner;logic[2:0] tag;} nested_t;
 integer a[2:0]='{1,2,3};
 logic[7:0] bytes[1:3]='{default:'1};
 logic[1:0][3:0] p='{4'ha,4'hb};
 item_t s='{b:-2,a:4'hf,mode:BUSY};
 nested_t n;
 logic[7:0] input_value=8'h39;wire[1:0][7:0] driven;
 assign driven='{input_value,~input_value};
 initial begin
  #1;$display("TRACE init %0d %0d %0d %h %h %h %h %0d",a[2],a[1],a[0],bytes[2],p,s,s.a,s.b);
  a='{0:8,default:4};bytes='{2:8'bxz1010zx,default:8'h12};
  p='{0:4'h6,default:4'h3};
  n='{tag:3'b101,inner:'{mode:IDLE,default:'1}};
  #1;$display("TRACE keys %0d %0d %0d %h %h %h %h %h",a[2],a[1],a[0],bytes[1],bytes[2],bytes[3],p,n);
  a='{3{9}};s='{4'bxz10,-3,IDLE};input_value=8'hc7;
  #1;$display("TRACE repeat %0d %0d %0d %h %0d %h",a[2],a[1],a[0],s,s.b,driven);
 end
endmodule
