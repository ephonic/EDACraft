module top;
 typedef enum bit [3:0] {A=2,B=9,C=14} code_t;
 class Base;
  rand code_t code;
  code_t ordinary;
  constraint legal {code!=A;}
 endclass
 class Child extends Base;
  rand int extra;
  constraint child_legal {extra==int'(code)+1;}
 endclass
 Base p;Child child;code_t code,saved;int observed;
 initial begin
  repeat(12)begin
   if(!std::randomize(code) with {code!=B;})$fatal(1,"scope solver");
   if(code!=A&&code!=C)$fatal(1,"scope enum domain");
  end
  saved=code;
  if(std::randomize(code) with {int'(code)==7;}||code!==saved)$fatal(1,"scope atomicity");
  child=new;p=child;
  if(!p.randomize()||child.extra!=int'(p.code)+1)$fatal(1,"dynamic inherited constraints");
  p.code=code_t'(7);p.legal.constraint_mode(0);child.child_legal.constraint_mode(0);
  if(!p.randomize(ordinary) with {ordinary==A;}||p.ordinary!=A||int'(p.code)!=7)$fatal(1,"named enum field");
  if(p.randomize(ordinary) with {int'(ordinary)==7;})$fatal(1,"ordinary enum domain");
  observed=int'(code);
  $display("TRACE constraints enum scope named inherited dynamic pass");$finish;
 end
endmodule
