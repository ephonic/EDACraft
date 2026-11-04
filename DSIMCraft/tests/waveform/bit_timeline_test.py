from reader import bit_timeline

def meta(decls):
 return {'signals':[{'code':d[3],'width':int(d[2])} for d in decls],
         'header':[['$scope','module','top','$end'],*decls,['$upscope','$end']]}
vector=meta([['$var','wire','4','v','y','[5:2]','$end']])
events=[(0,'value',(0,(9,10))),(1,'value',(0,(0,0))),(1,'value',(0,(3,4)))]
expected={('top','y',2):[(0,(1,0))],('top','y',3):[(0,(0,1)),(1,(1,0))],
          ('top','y',4):[(0,(0,0)),(1,(0,1))],('top','y',5):[(0,(1,1)),(1,(0,0))]}
assert bit_timeline(vector,events)==expected
split=meta([['$var','wire','1',str(i),'y',f'[{i+2}]','$end'] for i in range(4)])
scalar=[(0,'value',(i,v)) for i,v in enumerate([(1,0),(0,1),(0,0),(1,1)])]
scalar += [(1,'value',(1,(0,0))),(1,'value',(1,(1,0))),(1,'value',(2,(0,1))),(1,'value',(3,(0,0)))]
assert bit_timeline(split,scalar)==expected
ascending=meta([['$var','wire','4','v','y','[2:5]','$end']])
assert bit_timeline(ascending,events)=={('top','y',7-key[-1]):value for key,value in expected.items()}
plain=meta([['$var','wire','1','s','a','$end']])
assert bit_timeline(plain,[(0,'value',(0,(1,1)))])=={('top','a',None):[(0,(1,1))]}
for decls in [
 [['$var','wire','4','v','y','[5:3]','$end']],
 [['$var','wire','1','a','y','[2]','$end'],['$var','wire','1','b','y','[2]','$end']],
]:
 try:bit_timeline(meta(decls),[])
 except AssertionError:pass
 else:raise AssertionError('invalid range/duplicate bit was accepted')
print('PASS vector/indexed-scalar equivalence, four states, ascending ranges, settled changes and strict duplicate/range failures')
