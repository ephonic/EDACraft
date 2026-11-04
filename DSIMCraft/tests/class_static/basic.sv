module top;
 class Base;
  static int count=0;
  int id;
  function new(int i=0);id=i;count++;endfunction
  static function int add(int v=1);int tmp;tmp=count+v;count=tmp;return tmp;endfunction
  static task later(int v);int tmp;tmp=v;#2;count+=tmp;endtask
  virtual function int value();return id+1;endfunction
 endclass
 class Sub extends Base;
  static int own=19;
  function new(int i=0);super.new(i);endfunction
  virtual function int value();return id+2;endfunction
  function int base_value();return Base::value();endfunction
 endclass
 Base a,b,n;Sub d;int result,observed;
 initial begin
  $display("TRACE initial %0d %0d",Base::count,Sub::count);
  result=Base::add(3);a=new(7);b=new(10);d=new(11);
  $display("TRACE shared %0d %0d %0d %0d",a.count,b.count,d.count,Sub::own);
  result=n.add(4);n.count+=1;
  $display("TRACE nullstatic %0d %0d",result,Base::count);
  $display("TRACE dispatch %0d %0d",d.value(),d.base_value());
  Base::later(6);observed=Base::count;
  $display("TRACE task %0t %0d",$time,observed);
  #1;$finish;
 end
endmodule
