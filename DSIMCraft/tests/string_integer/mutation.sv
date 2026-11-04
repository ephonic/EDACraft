`timescale 1ns/1ps
module top;
  string text="abcd";integer index=0;
  function automatic int replace(ref string target);
    target="xyz";return 8'h51;
  endfunction
  function automatic string format_value(input int n);
    string local_text;
    local_text.hextoa(n);local_text.putc(0,8'h41);return local_text;
  endfunction
  initial begin
    #1;
    text.putc(index++,8'h41+index);
    if(text!="Bbcd"||index!=1)$fatal(1,"left to right actual evaluation");
    text.putc(1,0);text.putc(1,8'hx);text.putc(1,8'hz);
    text.putc(-1,65);text.putc(20,65);text.putc(32'hx,65);
    if(text!="Bbcd")$fatal(1,"invalid putc changes receiver");
    text.putc(1,8'h41);
    if(text!="BAcd")$fatal(1,"byte replacement");
    #1;
    text.putc(1,replace(text));
    if(text!="xQz")$fatal(1,"actual modifies receiver");
    #1;
    text.itoa(index++);if(text!="1"||index!=2)$fatal(1,"conversion actual evaluated once");
    #1;
    text=format_value(255);if(text!="Af")$fatal(1,"automatic function methods");
    // Return values may be explicitly discarded as method statements.
    text.atoi();void'(text.atohex());
    #1;
    $display("TRACE mutation %s %0d",text,index);
    $finish;
  end
endmodule
