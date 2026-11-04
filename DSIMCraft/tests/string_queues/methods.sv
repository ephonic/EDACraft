module top;
 string q[$],copy[$],s; int observed,total;
 initial begin
  if(q.pop_front()!=""||q.pop_back()!=""||q[0]!=""||q[-1]!="")$fatal(1,"empty defaults");
  q.push_back("alpha");q.push_front("beta");q.insert(1,"0123456789abcdef");
  if(q.size()!=3||q[0]!="beta"||q[1].len()!=16||q[2]!="alpha")$fatal(1,"insert");
  q[1]="changed";q[q.size()]="tail";q[-1]="ignored";q[9]="ignored";
  copy=q;q.delete(1);s=q.pop_front();
  if(s!="beta"||q.size()!=2||copy[1]!="changed")$fatal(1,"copy");
  s=q.pop_back();if(s!="tail"||q.pop_front()!="alpha")$fatal(1,"pop");
  q.delete();if(q.size()!=0||q.pop_front()!="")$fatal(1,"delete");
  q='{"one","two"};q={q,"three"};
  q[0].putc(0,8'h4f);if(q[0]!="One")$fatal(1,"element putc");q[0]="one";
  foreach(q[i])total+=q[i].len();if(total!=11)$fatal(1,"foreach strings");observed=q[2].len()+copy.size();
  $display("TRACE methods %s %s %0d",q[0],q[2],observed);$finish;
 end
endmodule
