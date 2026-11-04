`timescale 1ns/1ps
module top;
integer a=0,b=0,ea=0,eb=0,i,j;
function automatic integer add(input integer x);
 integer local_value=x+1;
 begin return local_value+2;end
endfunction
task automatic tick(input integer x,output integer y);
 integer saved=x;
 begin #1;y=add(saved);end
endtask
initial for(i=0;i<5;i=i+1)begin #2;tick(i+3,a);if(a!==i+6)ea=1;end
initial for(j=0;j<5;j=j+1)begin #3;tick(j+17,b);if(b!==j+20)eb=1;end
endmodule
