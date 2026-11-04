"""Generate expected values by walking declared labels in MSB-to-LSB order."""
from pathlib import Path
import json
p=Path(__file__).resolve().parent
bits=f'{0x96a5:016b}'
def select(value,left,index,width=1,down=False):
 start=index-width+1 if down else index
 return ''.join(value[label-left] if left<=label<left+len(value) else 'x' for label in range(start,start+width))
def store(value,left,index,rhs,down=False):
 start=index-len(rhs)+1 if down else index;out=list(value)
 for label,bit in zip(range(start,start+len(rhs)),rhs):
  if left<=label<left+len(value):out[label-left]=bit
 return ''.join(out)
wide=int('5abcdef0123456789abcdef0123456789',16)
s=[f'TRACE CONST 9 5 1 1 1001 {wide>>(131-67):017x}']
for tag,left,start,end in [('READ',4,-2,23),('NEG',-8,-11,10)]:
 for i in range(start,end+1):s.append(f'TRACE {tag} {i} {select(bits,left,i)} {select(bits,left,i,5)} {select(bits,left,i,5,True)}')
for i in range(1,23):
 s += [f'TRACE ADD {i} {store(bits,4,i,"10xz1")}',f'TRACE SUB {i} {store(bits,4,i,"10xz1",True)}']
q=store(bits,4,7,'110');s += [f'TRACE SIDE 8 {int(q,2):04x}','TRACE NBA 8e 5','TRACE EXTREME xxxxx xxxxx','TRACE EXTREME xxxxx xxxxx',f'TRACE UNKNOWN xxxxx {q}']
params=[]
for i in range(-2,10):params.append(f'TRACE PARAM {i} {select("10010110",0,i)} {select("10010110",0,i,4)} {select("10010110",0,i,4,True)} {select("10100101",-4,i-4,4)}')
params+=['TRACE FOLDED 9 a 9']
expected=dict(selects=s,aggregate=['TRACE AGG 69 69 02 3 1 100 1011 1','TRACE WRITE ae ea 6e 14 b6','TRACE HIER a e 0'],comb=['TRACE COMB 66 60','TRACE COMB 66 90','TRACE COMB aa a0'],parameter=params,parallel=[])
(p/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
