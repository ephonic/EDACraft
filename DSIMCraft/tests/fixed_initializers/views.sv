`timescale 1ns/1ps
module top;
 logic signed[95:0] source[2][3:2];integer index=1,evaluations=0,observed=0;
 function automatic integer pick();evaluations++;return index;endfunction
 task automatic work();
  bit signed[95:0] row[2]=source[pick()];
  logic signed[95:0] all_values[1:0][2]=source;
  $display("TRACE view %h %h %0d %0d",row[0],row[1],all_values[0][0]===source[1][3],evaluations);
  row[0]=0;#1;observed=row[0]+all_values[1][1];
 endtask
 typedef enum logic[2:0]{ONE=1,THREE=3} kind;
 kind enums[2];
 typedef struct packed {logic[3:0] high;logic[3:0] low;} record;
 record records[2];
 task automatic typed();
  kind enum_copy[2]=enums;record record_copy[2]=records;
  $display("TRACE types %0d %0d %h %h",enum_copy[0],enum_copy[1],record_copy[0],record_copy[1]);
 endtask
 initial begin
  source[0][3]=1;source[0][2]=2;source[1][3]=96'hx0123456789abcdef0012345;source[1][2]=-2;
  work();index=0;work();enums[0]=ONE;enums[1]=THREE;records[0]=8'ha5;records[1]=8'h3c;typed();
 end
endmodule
