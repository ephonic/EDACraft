`timescale 1ns/1ps
interface data_if #(parameter W=3);
 logic[W-1:0] value=0;
 modport out(output value);
endinterface
module drive(data_if.out b);
 initial begin #1;b.value='1;#1;b.value=b.value-1;end
endmodule
interface unused_if;logic hidden;endinterface
module top;
 data_if #(.W(7)) a();data_if #(13) b();drive d1(a);drive d2(b);
 initial begin #0.5;if($bits(a.value)!=7||$bits(b.value)!=13)$fatal(1,"FAIL parameter widths");
 #1;if(a.value!==7'h7f||b.value!==13'h1fff)$fatal(1,"FAIL parameter ones");
 #1;if(a.value!==7'h7e||b.value!==13'h1ffe)$fatal(1,"FAIL parameter alias");
 $display("TRACE parameterized %h %h",a.value,b.value);#1;$finish;end
endmodule
