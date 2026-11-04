`timescale 1ns/1ps
module top;
logic[129:0] value;
integer result;
initial begin
 value=130'b1<<100;
 $display("TRACE before wide clog2");
 result=$clog2(value);
 if(result!=100)$fatal(1,"wide power");
 value=value|1;result=$clog2(value);
 if(result!=101)$fatal(1,"wide tail");
 value=130'b1<<129;result=$clog2(value);
 if(result!=129)$fatal(1,"top bit");
 value='1;result=$clog2(value);
 if(result!=130)$fatal(1,"all ones");
 value[127]=1'bx;result=$clog2(value);
 $display("TRACE wide unknown %h",result);
 if(result!==32'bx)$fatal(1,"unknown");
 $display("TRACE wide clog2 pass");
end
endmodule
