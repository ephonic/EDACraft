`timescale 1ns/1ps
module lane #(parameter MODE=0)(output integer result=0);
event a,b,c,other;
initial wait_order(a,b,c) result=1; else result=-1;
initial begin
 #1;
 case(MODE)
  0: begin ->a;->b;->c;end
  1: ->b;
  2: begin ->a;->a;->b;->c;end
  3: begin ->a;->c;end
  4: begin ->other;->a;->other;->b;->c;end
  5: begin ->a;#1;->b;#1;->a;#1;->c;end
 endcase
end
endmodule
module top;
wire signed[31:0] a,b,c,d,e,f;
lane #(0)u0(a);lane #(1)u1(b);lane #(2)u2(c);
lane #(3)u3(d);lane #(4)u4(e);lane #(5)u5(f);
initial begin #6;$display("TRACE sequences %0d %0d %0d %0d %0d %0d",a,b,c,d,e,f);
 if(a!=1||b!=-1||c!=1||d!=-1||e!=1||f!=1)$fatal(1,"ordered event semantics");end
endmodule
