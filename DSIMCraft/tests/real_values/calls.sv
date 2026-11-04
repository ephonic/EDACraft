package fp;
  typedef real value_t;
  class Base;
    real total;
    virtual function real add(real a);total+=a;return total;endfunction
  endclass
  class Acc extends Base;
    extern virtual function value_t add(real a);
    function automatic real twice(real a, shortreal b=0.5);return (a+b)*2.0;endfunction
  endclass
  function fp::value_t Acc::add(real a);total+=a*2.0;return total;endfunction
endpackage
module top;
  import fp::*;
  Acc obj;
  Base base;
  real r;
  function automatic real scale(real a, real b=1.25);return a*b;endfunction
  task automatic bump(ref real value, input real delta);value+=delta;endtask
  initial begin
    obj=new;base=obj;
    if(obj.total!=0.0)$fatal(1,"real member default");
    r=scale(2.0);bump(r,0.25);
    if(r!=2.75 || base.add(1.5)!=3.0 || obj.twice(1.0)!=3.0)$fatal(1,"real call");
    r++;if(r!=3.75)$fatal(1,"real increment");
    if((r++)!=3.75 || r!=4.75)$fatal(1,"real postfix");
    if($sformatf("%0.2f",r)!="4.75")$fatal(1,"real format");
    $display("TRACE calls value=%0.2f total=%0.2f",r,obj.total);
    $finish;
  end
endmodule
