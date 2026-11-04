package loop_types;typedef int count_t;endpackage
module top;
 typedef logic signed [68:0] wide_t;
 typedef bit [7:0] byte_t;
 typedef enum int {FIRST=2,SECOND=4,LAST=6} state_t;
 typedef struct packed {bit[3:0] key;logic[3:0] value;} pair_t;
 typedef string word_t;
 int observed,steps;
 wide_t wide;
 function int start();steps++;return -2;endfunction
 function int step(input int n);return n+1;endfunction
 initial begin
  for(wide_t i=start(),j=i+1;i<2;i++)begin
   if(j!=-1)$fatal(1,"wide sibling initializer");
   wide=i;observed+=int'(i);
  end
  for(state_t s=FIRST;s<=LAST;s=s.next())begin
   observed+=int'(s);if(s==LAST)break;
  end
  for(pair_t p=8'h12;p.key<4;p.key++)observed+=p.value;
  for(word_t word="ab";word.len()<5;word={word,"x"})observed+=word.len();
  for(byte_t k=8'hfe;k!=1;k++)observed+=k;
  // Ordinary expression initializers must retain their original parse.
  for(steps=steps+1,wide=0;wide<2;wide=step(int'(wide)))observed++;
  if(observed!=536 || steps!=2 || wide!=2)$fatal(1,"alias loop %0d",observed);
  for(steps=2;steps<3;steps++);
  for(loop_types::count_t p=0;p<2;p++)observed++;
  if(observed!=538 || steps!=3)$fatal(1,"expression/package type parsing");
  $display("TRACE aliases %0d %0d %0d",observed,steps,wide);
 end
endmodule
