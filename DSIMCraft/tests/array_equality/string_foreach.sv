class C;
 string value="AX";
 function string walk();
  string joined="";
  foreach(value[i])joined={joined,$sformatf("%c",value[i])};
  return joined;
 endfunction
endclass
module top;
 string s="ab",result="";int count=0;C c;
 function automatic string walk(input string value);
  string collected="";
  foreach(value[index])collected={collected,$sformatf("%c",value[index])};
  return collected;
 endfunction
 initial begin
  $display("TRACE walk %s empty=%0d",walk("Az09"),walk("")=="");
  foreach(s[i])begin
   result={result,$sformatf("%c",s[i])};count++;
   if(i==0)s={s,"C"};
  end
  $display("TRACE grow %s count=%0d",result,count);
  result="";count=0;s="WXYZ";
  foreach(s[i])begin
   if(i==1)continue;
   result={result,$sformatf("%c",s[i])};count++;
   if(i==2)break;
  end
  $display("TRACE control %s count=%0d",result,count);
  c=new;$display("TRACE class %s",c.walk());
 end
endmodule
