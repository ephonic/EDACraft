module lane #(parameter W=65)(output logic[W-1:0] observed);
 typedef logic[W-1:0] Word;typedef Word Alias;
 typedef enum logic[W-1:0] {LOW=1,HIGH={W{1'b1}}} State;
 Alias q[$:1],a[int],d[];State states[$],state;
 initial begin
  q.push_back('1);q.push_front(Word'(3));q.push_back(Word'(7));
  a[-4]=q.pop_back();d=new[1];d[0]=a[-4];states.push_back(HIGH);state=states.pop_front();
  observed=d[0]&state;$display("TRACE clone %0d %h %0d",W,observed,q.size());
 end
endmodule
module top;
 logic[64:0] a;logic[128:0] b;
 lane #(65) u(a);lane #(129) v(b);
endmodule
