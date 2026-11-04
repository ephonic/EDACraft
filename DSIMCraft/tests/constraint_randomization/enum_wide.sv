module top;
 typedef enum logic [95:0] {LOW=96'h1,HIGH=96'hfedcba987654321000000005} wide_t;
 typedef enum logic signed [7:0] {NEG=-100,POS=100} signed_t;
 class C;
  rand wide_t wide;
  rand signed_t signed_code;
  constraint legal {wide==HIGH;signed_code<0;}
 endclass
 C c;wide_t wide;signed_t signed_code;int observed;
 initial begin
  c=new;
  if(!c.randomize()||c.wide!==HIGH||c.signed_code!==NEG)$fatal(1,"wide signed enum");
  if(!std::randomize(wide,signed_code) with {wide==HIGH;signed_code<0;}||wide!==HIGH||signed_code!==NEG)$fatal(1,"wide scope enum");
  observed=int'(signed_code);
  $display("TRACE constraints enum wide signed pass");$finish;
 end
endmodule
