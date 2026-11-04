`timescale 1ns/1ps
module top;
typedef struct packed {logic[7:0] a;bit[3:0] b;} pair_t;
integer grid[1:0][7:8],result=0,mixed_result=0;
pair_t pairs[4:3];bit[129:0] wide[9:8];integer types=0;
function automatic integer matrix(input integer a[][]);
 integer acc=0;foreach(a[i,j])acc+=a[i][j];
 if($left(a)!=0||$right(a)!=1||$left(a[0])!=0||$right(a[0])!=1||$bits(a)!=128)return -999;
 return acc;
endfunction
function automatic integer mixed(input integer a[][2:1]);return a[0][2]+a[1][1];endfunction
function automatic integer typed(input pair_t p[],input bit[129:0] w[]);
 if($bits(p)!=24||$bits(w)!=260||w[0]!==130'h1||w[1]!==130'h3)return -999;
 return p[0].a+p[1].b;
endfunction
initial begin
 grid[1][7]=1;grid[1][8]=2;grid[0][7]=3;grid[0][8]=4;
 pairs[4]=12'h127;pairs[3]=12'h345;wide[9]=1;wide[8]=3;
 result=matrix(grid);mixed_result=mixed(grid);types=typed(pairs,wide);
 $display("TRACE multidim %0d %0d %0d",result,mixed_result,types);
 if(result!=10||mixed_result!=5||types!=23)$fatal(1,"multidim/typed unsized arguments");
end
endmodule
