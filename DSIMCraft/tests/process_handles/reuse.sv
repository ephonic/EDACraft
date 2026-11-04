`timescale 1ps/1ps
module top;
 process parent,child,previous,handles[$];string archived,before_child;int count;
 initial begin
  parent=process::self();
  for(int i=0;i<4;i++)begin
   fork begin
    child=process::self();
    if(child==parent||child==previous)$fatal(1,"reused process identity");
    handles.push_back(child);before_child=child.get_randstate();
    if(previous!=null)begin
     if(previous.get_randstate()!=archived)$fatal(1,"archived state changed");
     previous.srandom(99);
     if(child.get_randstate()!=before_child)$fatal(1,"old handle targets new activation");
    end
    child.srandom(42);#1;
    if(process::self()!=child)$fatal(1,"identity across delay");
    count++;
   end join
   previous=child;archived=previous.get_randstate();
  end
  if(handles.size()!=4||handles[0]==handles[2])$fatal(1,"container identity");
  $display("TRACE reuse %0d",count);$finish;
 end
endmodule
