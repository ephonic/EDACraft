`timescale 1ns/1ps
module top;
integer short_values[4:3],big[7:9],q=0,r=0;
function automatic integer sum(input integer a[]);
 integer acc=0;foreach(a[i])acc+=a[i];return acc;
endfunction
function automatic integer collect(input integer a[]=short_values);
 integer count=$size(a),width=$bits(a)+1;
 return sum(a)+count+(width-1)/32;
endfunction
function automatic integer classic;
 input integer a[];
 begin return a[$right(a)];end
endfunction
initial begin
 short_values[4]=1;short_values[3]=2;big[7]=4;big[8]=5;big[9]=6;
 q=collect(short_values)+collect(.a(big))+collect(.a());r=classic(big);
 $display("TRACE functions %0d %0d",q,r);
 if(q!=35||r!=6)$fatal(1,"unsized specialization/default/query");
end
endmodule
