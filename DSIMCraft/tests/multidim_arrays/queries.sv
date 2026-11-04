`timescale 1ns/1ps
module child #(parameter L=2)(input logic[7:0] value,output logic hit);
 logic[7:0] table_data[L:L+1][4:3];
 wire[31:0] image_table={table_data[L][3],table_data[L][4],table_data[L+1][3],table_data[L+1][4]};
 initial foreach(table_data[i,j])table_data[i][j]=i*16+j;
 always_comb hit=value inside {table_data};
endmodule
module top;
logic[7:0] value=0;wire hit;
logic[3:0] data[2:1][4:6];integer sum=0,count=0;
wire[23:0] image_data={data[1][4],data[1][5],data[1][6],data[2][4],data[2][5],data[2][6]};
child #(2) u(value,hit);
initial begin
 if($dimensions(data)!==3 || $unpacked_dimensions(data)!==2 || $size(data,1)!==2 || $size(data,2)!==3 || $size(data,3)!==4 || $bits(data)!==24)$fatal(1,"shape");
 foreach(data[i,j])data[i][j]=i+j;
 foreach(data[,j])begin count++;sum+=j;end
 if(count!==3 || sum!==15)$fatal(1,"omitted dimension");
 #1;value=8'h23;#1;if(!hit)$fatal(1,"inside array hit");
 value=8'h77;#1;if(hit)$fatal(1,"inside array miss");
 $display("TRACE queries %0d %0d %b",count,sum,hit);
end
endmodule
