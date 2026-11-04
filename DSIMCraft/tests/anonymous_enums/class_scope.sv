module top;
 class setting #(parameter int N=3);
  enum {STANDARD,NON_STANDARD=N,ILLEGAL} src=NON_STANDARD,other=STANDARD;
  function string label();return src.name();endfunction
  function void step();src=src.next();endfunction
 endclass
 setting #(3) a;setting #(7) b;
 int observed;
 initial begin
  a=new();b=new();
  if(a.src!=3||b.src!=7||a.label()!="NON_STANDARD"||b.other!=0)$fatal(1,"class binding");
  a.step();b.step();observed=a.src+b.src;
  if(observed!=12||a.label()!="ILLEGAL"||b.label()!="ILLEGAL")$fatal(1,"class enum methods");
  #1;$display("TRACE class %0d %0d %s",a.src,b.src,a.label());$finish;
 end
endmodule
