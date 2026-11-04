module top;
reg[127:0] index;
reg[127:0] q;
initial begin
 index=128'h10000000000000004;q=128'h123456789abcdef0123456789abcdef0;
 $display("TRACE large=%b %b",q[index],q[index+:8]);
 q[index]=0;q[index+:16]<=#1 0;
 #2;$display("TRACE unchanged=%h",q);
 index=128'hx0000000000000004;
 $display("TRACE unknown-high=%b",q[index+:8]);
 $finish;
end
endmodule
