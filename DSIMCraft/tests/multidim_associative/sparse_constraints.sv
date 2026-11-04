module top;
 typedef enum bit[7:0] {A=1,B=3} key_t;
 class Store;rand int answer;int data[int][key_t];
 constraint match {answer inside {[0:100]};foreach(data[i,j]) answer>data[i][j]+i+int'(j);}
 endclass
 Store s;int observed;
 initial begin s=new;s.data[2][A]=7;s.data[-1][B]=8;
 if(!s.randomize()||s.answer<=10)$fatal(1,"nested constraint");
 observed=1;$display("TRACE sparse constraints PASS");end
endmodule
