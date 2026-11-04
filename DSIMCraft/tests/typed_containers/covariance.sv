module top;
 class B;int v;endclass class D extends B;endclass
 B b[$],fixed[2],dyn[],aa[int],copied[int];D d[$],ds[2],x;
 int observed;
 initial begin
  x=new;x.v=11;d.push_back(x);b=d;ds[0]=x;fixed=ds;dyn=new[2](ds);
  aa[-7]=x;copied=aa;copied[-7].v=19;
  observed=b[0].v+fixed[0].v+dyn[0].v;
  $display("TRACE covariance %0d %0d %0d",observed,aa[-7].v,dyn[1]==null);
 end
endmodule
