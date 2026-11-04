module top;
 class Base;int v;function new(int n=0);v=n;endfunction virtual function int read();return v;endfunction endclass
 class Child extends Base;function new(int n=0);super.new(n);endfunction virtual function int read();return v+10;endfunction endclass
 Base q[$],aa[int],d[],fixed[2],b;Child c;
 int observed;
 initial begin
 c=new(7);q.push_back(c);b=q.pop_front();aa[-3]=b;d=new[2];d[0]=aa[-3];fixed[0]=d[0];
 observed=fixed[0].read();$display("TRACE objects %0d %0d %0d",observed,q.size(),d[1]==null);
 q.push_back(c);observed=q.pop_front().read();$display("TRACE chained %0d",observed);
 end
endmodule
