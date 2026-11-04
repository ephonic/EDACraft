module top;
 class Singleton;
  static local Singleton m_inst;
  int value;
  function new();value=37;endfunction
  static function Singleton get_inst();
   if(m_inst==null)m_inst=new();
   return m_inst;
  endfunction
 endclass
 Singleton a=Singleton::get_inst();
 int observed=0;
 initial begin observed=a.value;#1;if(a.value!=37)$fatal(1,"singleton");$display("TRACE singleton %0d",a.value);$finish;end
endmodule
