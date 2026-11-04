`timescale 1ps/1ps
module top;
 int matrix[2][3:1];
 int values[$];
 int dynamic_values[];
 int x,y;
 class C;
  rand int n;
  int state[int];
  int i=77;
  constraint c {n inside {[0:15]};foreach(state[i]) n>state[i];}
 endclass
 C c;
 initial begin
  matrix[0][1]=4;matrix[0][2]=5;matrix[0][3]=6;
  matrix[1][1]=7;matrix[1][2]=8;matrix[1][3]=9;
  if(!std::randomize(x) with {
    x inside {[0:30]};
    foreach(matrix[i,j]) {x>matrix[i][j];}
    foreach(matrix[,j]) {x<j+10;}
   }||x!=10)$fatal(1,"fixed dimensions/directions/omission");
  values={1,4,7};
  if(!std::randomize(y) with {y==8;foreach(values[k]) {y>values[k];}})$fatal(1,"queue iteration");
  dynamic_values=new[2];dynamic_values[0]=3;dynamic_values[1]=9;
  if(!std::randomize(y) with {y==10;foreach(dynamic_values[k])y>dynamic_values[k];})$fatal(1,"dynamic iteration");
  c=new;c.state[-3]=1;c.state[8]=14;
  if(!c.randomize()||c.n!=15||c.i!=77)$fatal(1,"associative indices shadow fields");
  c.state.delete(8);c.state[4]=15;
  if(c.randomize())$fatal(1,"new associative content");
  c.state.delete();
  if(!c.randomize() with {n==0;})$fatal(1,"empty associative vacuity");
  $display("TRACE constraint foreach fixed dynamic associative lexical indices pass");$finish;
 end
endmodule
