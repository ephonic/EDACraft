`timescale 1ns/1ps
module top;
  logic[2:0] grid[3:2];
  integer n=0,stamp=0,hits=0,outer=88;
  initial begin
    grid[3]=0;grid[2]=0;
    foreach(grid[i,j]) begin
      if(i!=3-n/3 || j!=2-n%3)$fatal(1,"dimension order");
      grid[i][j]=1;n++;
    end
    if(n!=6 || grid[3]!=7 || grid[2]!=7)$fatal(1,"grid fill");
    foreach(grid[i,j]) begin
      if(j==1)continue;
      stamp=stamp*10+j;
      if(i==2 && j==2)break;
      hits++;
    end
    if(stamp!=202 || hits!=2)$fatal(1,"break whole foreach");
    n=0;foreach(grid[,j]) begin n++; if(j!=3-n)$fatal(1,"skip");end
    if(n!=3)$fatal(1,"skip count");
    n=0;foreach(grid[i,]) begin n++; if(i!=4-n)$fatal(1,"trailing skip");end
    if(n!=2)$fatal(1,"trailing count");
    n=0;foreach(grid[outer]) foreach(grid[inner]) begin n++;if(outer<2 || inner>3)$fatal(1,"nested");end
    if(n!=4 || outer!=88)$fatal(1,"nested scope");
    #1;$display("TRACE multi %0d %0d",stamp,n);
  end
endmodule
