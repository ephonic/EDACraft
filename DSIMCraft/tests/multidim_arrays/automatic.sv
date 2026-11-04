`timescale 1ns/1ps
module top;
integer a=0,b=0,sum=0;
function automatic integer calc(input integer seed);
 integer grid[2:1][3:4][0:1];integer total;
 total=0;foreach(grid[i,j,k])begin grid[i][j][k]=seed+i+j+k;total+=grid[i][j][k];end
 return total;
endfunction
task automatic walk(input integer seed,input integer step,output integer result);
 logic[7:0] grid[2:1][3:4];integer total;
 total=0;foreach(grid[i,j])begin grid[i][j]=seed+i+j;end
 foreach(grid[i,j])begin # (step);total+=grid[i][j];end
 result=total;
endtask
initial begin sum=calc(1)+calc(2);if(sum!==112)$fatal(1,"function storage");end
initial begin walk(10,2,a);if(a!==60)$fatal(1,"activation a");end
initial begin walk(20,3,b);if(b!==100)$fatal(1,"activation b");#1;$display("TRACE automatic %0d %0d %0d",a,b,sum);end
endmodule
