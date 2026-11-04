`timescale 1ns/1ps
module top;
integer value=0,low=2,high=5,i=0;
logic[3:0] pattern=4'b1?01,unknown_value=4'bx101;
logic[7:0] result=0;
logic signed[7:0] neg=-1;
integer set_values[2:4];
logic array_hit;
always_comb array_hit=value inside {set_values};
logic[129:0] wide=130'h200000000000000000000000000000001;
logic[129:0] wide_pattern=130'h2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1;
initial begin
 set_values[2]=3;set_values[3]=9;set_values[4]=12;
 for(i=0;i<15;i++)begin
  #1 if(i>0&&array_hit!==((i-1==3)||(i-1==9)||(i-1==12)))$fatal(1,"array sensitivity");
  value=i;
  result[0]=value inside {[low:high],9};
  result[1]=value inside {set_values};
  result[2]=value inside {[high:low]};
  if(result[0]!==((i>=2&&i<=5)||i==9)||result[1]!==((i==3)||(i==9)||(i==12))||result[2]!==0)$fatal(1,"range/array membership");
 end
 result[3]=unknown_value inside {4'b0101,pattern};if(result[3]!==1'bx)$fatal(1,"set unknown");
 result[4]=unknown_value inside {4'b????};if(result[4]!==1'b1)$fatal(1,"all wild");
 result[5]=neg inside {16'shffff,32'h0};if(result[5]!==0)$fatal(1,"global unsigned set context");
 result[6]=neg inside {16'shffff};if(result[6]!==1)$fatal(1,"signed set context");
 result[7]=wide inside {wide_pattern};if(result[7]!==1||!(wide==?wide_pattern))$fatal(1,"multiword wildcard");
 #1 set_values[3]=14;wide[128]=1'bx;wide_pattern[128]=1'b0;
 if((wide==?wide_pattern)!==1'bx)$fatal(1,"multiword lhs unknown");
 wide[129]=0;if((wide==?wide_pattern)!==0)$fatal(1,"multiword mismatch dominates unknown");
 #1 if(array_hit!==1)$fatal(1,"changed array member dependency");
 $display("TRACE membership complete");
end
endmodule
