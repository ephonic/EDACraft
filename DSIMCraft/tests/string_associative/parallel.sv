module worker #(parameter TAG=1)(output int observed);
 int values[string];
 initial begin values["a"]=TAG;#1;values["b"]=TAG+2;observed=values["a"]+values["b"];#2;values.delete("a");observed=values.size();end
endmodule
module top;
 wire[31:0] one,two;worker #(3)a(one);worker #(9)b(two);
endmodule
