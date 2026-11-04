"""Binary reads: VCS fixtures, full streams, target effects and cursor rollback."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations

def run(command,work,label):
 p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

def file_bytes(work,wanted,label):
 observed={name:(work/name).read_bytes().hex() for name in wanted}
 assert observed==wanted,(label,observed,wanted)
 (work/(label+'.files.json')).write_text(json.dumps(observed,indent=2)+'\n')
expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0,'accepted_predictions':0}
try:
 # Kernel test inspects real files *during* speculation, not only after replay.
 unit=out/'runtime';run(['c++','-std=c++17','-O2','-UNDEBUG','-I'+str(ROOT/'include'),fixtures/'runtime.cpp','-o',unit],out,'runtime-compile')
 run([unit,out/'runtime-files'],out,'runtime-run');report['runtime_transactions']='PASS'
 for name,row in expected.items():
  wanted=row['output'];work=out/name;work.mkdir(exist_ok=True);reference={}
  for file,hex_bytes in row['files'].items():(work/file).write_bytes(bytes.fromhex(hex_bytes))
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   for mode in ['ordered','settled']:
    wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode',mode],work,backend+'-'+mode)
    assert text.splitlines()==wanted,(name,backend,mode,text,wanted)
    file_bytes(work,row['files'],backend+'-'+mode)
    current=stream(wave)
    if backend=='serial':reference[mode]=current
    else:assert current==reference[mode],(name,backend,mode,'complete stream')
    report['captures']+=1
  run([compiler,fixtures/(name+'.sv'),'--emit-cpp',work/'plain.cpp','-o',work/'plain'],work,'plain-compile')
  assert run([work/'plain'],work,'plain-run').splitlines()==wanted,(name,'plain')
  file_bytes(work,row['files'],'plain-run')
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1 and code.count('Sim s;')==1
  names=list(row['files'])+(['export.txt'] if name=='memory' else [])
  seed='std::vector<std::string> io_paths='+json.dumps(names).replace('[','{').replace(']','}')+';\n'
  check='''
auto disk_bytes=[](const std::string& path){std::ifstream in(path,std::ios::binary);return std::string(std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>());};
std::vector<std::pair<bool,std::string>> original_files;
for(const auto& path:io_paths)original_files.push_back({std::filesystem::exists(path),disk_bytes(path)});
auto unchanged_files=[&]{for(size_t i=0;i<io_paths.size();++i)if(original_files[i]!=std::make_pair(std::filesystem::exists(io_paths[i]),disk_bytes(io_paths[i])))throw std::runtime_error("speculation changed an external file");};
'''
  for mode in ['replay','accepted']:
   patch=check+'\nbool accepted=s.predict_until(10000,[&](Sim& predicted){predicted.run();unchanged_files();},[](const Sim&){return '+('true' if mode=='accepted' else 'false')+';},[&](Sim& corrected){unchanged_files();corrected.run();});\n'
   patch+='if(accepted!='+('true' if mode=='accepted' else 'false')+'||s.prediction_stats.'+('commits' if mode=='accepted' else 'rollbacks')+'!=1)throw std::runtime_error("prediction result mismatch");\ns.run();\n'
   (work/(mode+'.cpp')).write_text(code.replace('Sim s;',seed+'Sim s;',1).replace('\ns.run();\n',patch))
   run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],work/(mode+'.cpp'),config['DSIM_ZSTD_LIBRARY'],'-o',work/mode],work,mode+'-compile')
   wave=work/(mode+'.vcd');wave.unlink(missing_ok=True)
   assert run([work/mode,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,mode+'-run').splitlines()==wanted,(name,mode,'output')
   file_bytes(work,row['files'],mode+'-run')
   assert stream(wave)==reference['ordered'],(name,mode,'complete stream')
   report['captures']+=1
  report['rollbacks']+=1;report['accepted_predictions']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'output':wanted,'files':row['files']}
  print('PASS binary_io',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 report['real_parallel_partitions']=2
 negatives={
  'arity':('int r;initial r=$fread(r);','argument count'),
  'too_many':('int a[2],r;initial r=$fread(a,1,0,1,2);','argument count'),
  'packed_range':('int r;initial r=$fread(r,1,0);','start/count require'),
  'net':('wire[15:0]v;int r;initial r=$fread(v,1);','variable target'),
  'enum':('typedef enum int{A=0,B=1}e;e v;int r;initial r=$fread(v,1);','non-enum'),
  'text':('string v;int r;initial r=$fread(v,1);','integral non-enum'),
  'const_ref':('task automatic t(const ref int v);int r;r=$fread(v,1);endtask int v;initial t(v);','const ref'),
  'const_array':('task automatic t(const ref int v[2]);int r;r=$fread(v,1);endtask int v[2];initial t(v);','const ref'),
  'string_fd':('string fd;int r;initial r=$fread(r,fd);','integral value'),
  'dynamic':('int a[],r;initial r=$fread(a,1);','dynamic arrays'),
  'multidim':('int a[2][2],r;initial r=$fread(a,1);','one-dimensional'),
  'concat':('reg[7:0]a,b;int r;initial r=$fread({a,b},1);','concatenation'),
 }
 for name,(body,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+body+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  p=subprocess.run([str(compiler),str(source),'--emit-only','--emit-cpp',str(dest)],capture_output=True,text=True)
  (out/(name+'.stderr')).write_text(p.stderr)
  assert p.returncode==1 and diagnostic in p.stderr and not dest.exists(),(name,p.returncode,p.stdout,p.stderr)
 errors={
  'bad_fd':('int r;initial r=$fread(r,1);','invalid file descriptor'),
  'unknown_fd':('int r;initial r=$fread(r,32\'hx);','contains X/Z'),
  'bad_start':('int a[2],r,fd;initial begin fd=$fopen("input.bin","rb");r=$fread(a,fd,2);end','array range out of bounds'),
  'bad_count':('int a[2],r,fd;initial begin fd=$fopen("input.bin","rb");r=$fread(a,fd,0,-1);end','array range out of bounds'),
 }
 (out/'input.bin').write_bytes(bytes.fromhex('123456789abcdef001'))
 for name,(body,diagnostic) in errors.items():
  source=out/(name+'.sv');source.write_text('module top;'+body+' endmodule\n')
  run([compiler,source,'-o',out/name],out,name+'-compile')
  p=subprocess.run([out/name],cwd=out,capture_output=True,text=True)
  (out/(name+'.stderr')).write_text(p.stderr)
  assert p.returncode==1 and diagnostic in p.stderr,(name,p.returncode,p.stderr)
 report.update(status='PASS',negative_cases=len(negatives),runtime_rejections=len(errors))
except Exception as error:report.update(status='FAIL',error=str(error));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS binary_io:',len(report['models']),'models,',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['accepted_predictions'],'commits')
