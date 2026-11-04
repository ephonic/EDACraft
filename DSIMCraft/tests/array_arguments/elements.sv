`timescale 1ns/1ps
module top;
integer grid[0:1][2:1],index=0,calls=0,sum=0;
function automatic integer pick();calls++;return index;endfunction
task automatic take(input integer a[0:1],output integer b[0:1]);#2;b[0]=a[0]+10;b[1]=a[1]+20;endtask
task automatic change(ref integer a[7:8]);a[7]++;#2;a[8]+=2;endtask
task automatic forward(ref integer a[9:8]);change(a);endtask
initial begin
 grid[0][2]=3;grid[0][1]=4;grid[1][2]=5;grid[1][1]=6;
 fork take(grid[pick()],grid[index]);begin #1;index=1;grid[0][2]=99;end join
 index=0;
 fork forward(grid[pick()]);begin #1;index=1;end join
 sum=grid[0][2]+grid[0][1]+grid[1][2]+grid[1][1];
 $display("TRACE elements %0d %0d %0d %0d %0d %0d",grid[0][2],grid[0][1],grid[1][2],grid[1][1],calls,sum);
 if(grid[0][2]!=100||grid[0][1]!=6||grid[1][2]!=13||grid[1][1]!=24||calls!=2||sum!=143)$fatal(1,"subarray address timing");
end
endmodule
