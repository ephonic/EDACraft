module top;
class C #(int W=8);
 parameter string NAME="packet";
 localparam string LABEL={NAME,":item"};
 localparam int LEN=11;
 function string get();return LABEL;endfunction
endclass
C c;int observed;string label;
initial begin c=new;label=C#()::LABEL;observed=label.len();if(c.get()!="packet:item" || observed!=11)$fatal(1,"text constants");$display("TRACE body text %s %0d",C#(16)::LABEL,observed);end
endmodule
