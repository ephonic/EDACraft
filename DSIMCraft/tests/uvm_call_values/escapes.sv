module top;
string s;
reg [63:0] p;
initial begin
 s="\%m.\%s|\q\h\z\8\9";
 $display("TRACE literal %s",s);
 s="\x41|\101|\12|\1|\\|\"";
 $display("TRACE bytes %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",s.len(),s.getc(0),s.getc(1),s.getc(2),s.getc(3),s.getc(4),s.getc(5),s.getc(6),s.getc(7),s.getc(8),s.getc(9),s.getc(10));
 p="\%q\z";
 $display("TRACE packed %h",p);
end
endmodule
