"""Exercise worker overlap and reject unsupported CLI combinations."""
import json

def probe(compiler,work,run):
    work.mkdir();source=work/'top.v'
    source.write_text('module top;reg a,b;initial begin a=0;#2 a=1;end '
                      'initial begin b=0;#3 b=1;end endmodule\n')
    cpp=work/'original.cpp'
    run([compiler,source,'--threads','2','--emit-only','--emit-cpp',cpp],work,'emit')
    code=cpp.read_text()
    marker='s.process([&,pc=0]() mutable {for(;;){s.step();switch(pc){'
    assert code.count(marker)==2
    helper='''
#include <mutex>
#include <condition_variable>
#include <set>
#include <thread>
#include <chrono>
static std::atomic<unsigned> state_copies{0};
struct CopyProbe {
  CopyProbe()=default;
  CopyProbe(const CopyProbe&){++state_copies;}
  CopyProbe& operator=(const CopyProbe&){++state_copies;return *this;}
};
static std::mutex worker_mutex;
static std::condition_variable worker_cv;
static std::set<std::thread::id> worker_ids;
static void prove_overlap() {
  std::unique_lock<std::mutex> lock(worker_mutex);
  worker_ids.insert(std::this_thread::get_id());worker_cv.notify_all();
  if(!worker_cv.wait_for(lock,std::chrono::seconds(5),[]{return worker_ids.size()==2;}))
    throw std::runtime_error("generated partitions did not overlap on two worker threads");
}
'''
    marker_main='using namespace dsim;\nint main('
    assert code.count(marker_main)==1
    code=code.replace(marker_main,helper+marker_main)
    code=code.replace(marker,marker.replace('{for(;;)', '{if(pc==0)prove_overlap();for(;;)'))
    assert code.count('\nengine.run();\n')==1
    code=code.replace('\nengine.run();\n',
        '\nfor(size_t i=0;i<engine.partition_count();++i)engine.kernel(i).register_state(std::make_shared<CopyProbe>());\n'
        'engine.run();std::cerr<<"WORKERS "<<worker_ids.size()<<"\\nCOPIES "<<state_copies.load()<<"\\n";\n')
    instrumented=work/'instrumented.cpp';instrumented.write_text(code);exe=work/'instrumented'
    run(['c++','-std=c++17','-O2','-pthread',instrumented,'-o',exe],work,'build')
    observed=run([exe],work,'overlap');assert observed.stderr=='WORKERS 2\nCOPIES 0\n'
    assert 'engine.enable_global_finish();' not in code[code.index(marker_main):]
    reference=work/'forced-transactions.cpp'
    reference.write_text(code.replace('\nengine.run();','\nengine.enable_global_finish();engine.run();'))
    forced=work/'forced-transactions'
    run(['c++','-std=c++17','-O2','-pthread',reference,'-o',forced],work,'build-forced')
    observed=run([forced],work,'forced')
    assert observed.stderr.startswith('WORKERS 2\nCOPIES ')
    copies=int(observed.stderr.splitlines()[1].split()[1]);assert copies>0
    rejected=0
    protected=work/'protected.cpp';protected.write_text('keep-this-output')
    for number,args in enumerate([
        ['--threads'],['--threads','0'],['--threads','-1'],['--threads','129'],
        ['--threads','bad'],['--threads','1.2'],['--threads','18446744073709551616'],
        ['--threads','1','--threads','2'],['--threads','1','-E'],
        ['--threads','1','--timing-model-check'],['--threads','1','--sdf-check',source],
    ]):
        result=run([compiler,source,'--emit-only','--emit-cpp',protected,*args],work,'reject-'+str(number),False)
        assert result.stderr.strip()
        assert protected.read_text()=='keep-this-output';rejected+=1
    dump=work/'dump.v';dump.write_text('module top;reg a;initial begin $dumpvars;a=0;end endmodule\n')
    result=run([compiler,dump,'--threads','2','--emit-only','--emit-cpp',protected],work,'reject-dump',False)
    assert 'dump tasks are not yet supported with --threads' in result.stderr
    assert protected.read_text()=='keep-this-output';rejected+=1
    return dict(status='PASS',overlapping_worker_threads=2,cli_rejections=rejected,
                state_copies_without_finish=0,state_copies_with_forced_transactions=copies)
