// Next full-UVM blocker: output is a private map until task copyout.
module top;
  class Node; endclass
  typedef bit edges_t[Node];
  Node a,b;
  edges_t edges;int observed;
  task automatic collect(output edges_t values);
    values[a]=1;
    #2;
  endtask
  initial begin
    a=new();b=new();edges[b]=1;
    fork
      collect(edges);
      begin #1;$display("TRACE pending %0d %0d",edges.exists(a),edges.exists(b));end
    join
    observed=edges.num();
    $display("TRACE output %0d %0d %0d",edges.num(),edges.exists(a),edges.exists(b));
  end
endmodule
