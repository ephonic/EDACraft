`timescale 1ns/1ps
module top;
event a,b,c,d,e,f,g,h,j,k;
integer duplicate=0,single=0,success=0,failure=0,dangling=0,qualified=0;
initial wait_order(a,a,b) duplicate=1;else duplicate=-1;
initial begin wait_order(c);single=1;end
initial begin wait_order(d,e) success=1;end
initial wait_order(f,g) else failure=1;
initial if(1) wait_order(h) if(0)dangling=1;else dangling=2;
initial unique if(0)qualified=-1;else wait_order(j,k)qualified=1;else qualified=-2;
initial begin
 #1;->a;->a;->b;->c;->d;->e;->g;->h;->j;->k;
 #1;$display("TRACE actions %0d %0d %0d %0d %0d %0d",duplicate,single,success,failure,dangling,qualified);
 if(duplicate!=1||single!=1||success!=1||failure!=1||dangling!=2||qualified!=1)$fatal(1,"ordered action grammar");
end
endmodule
