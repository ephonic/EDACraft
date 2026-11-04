module top;
 typedef struct {string name;int count;logic flag;} item_t;
 item_t x,y,items[2];
 typedef struct {string value;} single_t;
 single_t only,copy;
 int index,observed;
 function automatic item_t edit(input item_t src);
   item_t tmp;
   tmp=src;tmp.name={src.name,"!"};tmp.count++;return tmp;
 endfunction
 task automatic update(ref item_t dst,input string name);
   dst.name=name;dst.count+=10;
 endtask
 initial begin
   x='{name:"one",count:1,flag:1'bx};y=edit(x);
   if(x.name!="one"||y.name!="one!"||y.count!=2||y.flag!==1'bx)$fatal(1,"function copy");
   update(y,"two");items[0]=x;items[1]=y;
   index=1;items[index].name="array";
   if(items[0].name!="one"||items[1].name!="array"||y.name!="two")$fatal(1,"array copy");
   only.value="single";copy=only;copy.value="changed";
   if(only.value!="single"||copy.value!="changed")$fatal(1,"single field");
   only=(index?copy:only);if(only.value!="changed")$fatal(1,"conditional");
   observed=items[index].count;
   $display("TRACE calls %s %s %s %0d",x.name,y.name,items[index].name,observed);
   #1;$finish;
 end
endmodule
