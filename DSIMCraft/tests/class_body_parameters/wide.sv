module top;
class C #(int W=129);
 parameter logic signed[W-1:0] NEG=-2;
 localparam logic signed[W-1:0] NEXT=NEG-1;
 localparam bit[3:0] CLEAN='x;
 localparam int N=7;
 bit[N-1:0] data;
 function int get();return NEXT+CLEAN+$bits(data);endfunction
endclass
C c;int observed;
initial begin c=new;observed=c.get();if(observed!=4 || C::NEXT!==-129'sd3 || C::CLEAN!==4'b0)$fatal(1,"wide constants");$display("TRACE body wide %0d %0d",observed,C#(65)::NEXT);end
endmodule
