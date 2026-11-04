#include "sdf.hpp"
#include <cassert>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
using namespace dsim;
static SdfStats parse(const std::string& s,const SdfCallbacks& cb={}) {std::istringstream in(s);return parse_sdf(in,"test.sdf",cb);}
static std::string wrap(const std::string& body) {return "(DELAYFILE (SDFVERSION \"3.0\") (TIMESCALE 1ns) (CELL (CELLTYPE \"BUF\") (INSTANCE u) "+body+"))";}
int main() {
    std::vector<SdfEntry> entries;
    auto stats=parse(R"sdf(// file comment
(DELAYFILE (SDFVERSION "3.0") (DESIGN "top") (DIVIDER /)
 (TIMESCALE 10 ps) (VOLTAGE :1.0:) (TEMPERATURE -40:25:125)
 (CELL (CELLTYPE "DFF") (INSTANCE u\(0\))
  (DELAY
   (ABSOLUTE
    (IOPATH (posedge CP) Q (1:2:3) (4) ())
    (COND "enable path" (TE == 0 && RB == 1)
     (IOPATH A Q ((.1:.2:.3) (.01) (.02)) (2e-3)))
    (CONDELSE (IOPATH A Q (5)))
    (IOPATH D Q (RETAIN (0.1) (0.2)) (1) (2))
    (INTERCONNECT u0/Q u1/D (1::3))
    (PORT D (1)) (DEVICE Q (3)) (DEVICE (4)))
   (INCREMENT (IOPATH D Q (-.1) (+.2))))
  (TIMINGCHECK
   (SETUP D (posedge CP) (1:2:3))
   (HOLD (COND "on" EN == 1 (posedge CP)) D (-.1))
   (SETUPHOLD D (posedge CP) (1) (2))
   (WIDTH (negedge CP) (2)) (PERIOD CP (4))
   (RECOVERY RB CP (1)) (REMOVAL RB CP (1))
   (RECREM RB CP (1) (2)) (SKEW A B (1))
   (BIDIRECTSKEW A B (1) (2)) (NOCHANGE A B (-1) (2)))))
)sdf",{{},[&](const SdfCell& c){assert(c.instance=="u\\(0\\)");},[&](const SdfCell&,const SdfEntry& e){entries.push_back(e);}});
    assert(stats.cells==1&&stats.entries==20&&stats.incremental==1&&stats.conditional==3&&stats.retains==1);
    assert(stats.header.timescale_fs==10000&&stats.header.divider=='/');
    assert(entries[0].ports[0].edge=="posedge"&&entries[0].values.size()==3);
    assert(entries[0].values[0].delay.corner[1]=="2"&&!entries[0].values[2].delay.corner[0]);
    assert(entries[1].label=="enable path"&&entries[1].condition=="(TE == 0 && RB == 1)");
    assert(entries[1].values[0].reject->corner[1]==".01"&&entries[1].values[0].xlimit->corner[2]==".02");
    assert(entries[2].conditional_else&&entries[3].retain[0].size()==2);
    assert(!entries[4].values[0].delay.corner[1]&&entries[4].values[0].delay.corner[2]=="3");
    assert(entries[8].mode==SdfEntry::Mode::Increment&&entries[10].ports[0].condition=="EN == 1");
    auto empty=parse("(DELAYFILE(SDFVERSION \"OVI 2.1\")(CELL(CELLTYPE \"X\")(INSTANCE *)))");
    assert(empty.cells==1&&!empty.header.timescale_fs&&empty.entries==0);
    for(auto s:std::vector<std::string>{"", "(DELAYFILE)","(DELAYFILE(SDFVERSION \"3.0\"))",wrap("(BOGUS)"),
        wrap("(DELAY(ABSOLUTE(IOPATH A Y)))"),wrap("(DELAY(ABSOLUTE(IOPATH A Y (1)(2)(3)(4))))"),
        wrap("(DELAY(ABSOLUTE(IOPATH A Y (nan))))"),wrap("(DELAY(ABSOLUTE(IOPATH A Y (1:2))))"),
        wrap("(DELAY(ABSOLUTE(IOPATH A Y (::))))"),wrap("(DELAY(ABSOLUTE(IOPATH A Y (1 2))))"),
        wrap("(DELAY(ABSOLUTE(IOPATH (bad A) Y (1))))"),wrap("(TIMINGCHECK(SETUP A B))"),
        wrap("(DELAY(INCREMENTAL(IOPATH A Y (1))))"),wrap("(TIMINGCHECK(UNKNOWN A (1)))"),
        wrap("(DELAY(ABSOLUTE(COND (IOPATH A Y (1)))))"),
        wrap("(DELAY(ABSOLUTE(CONDELSE 1 (IOPATH A Y (1)))))"),
        wrap("(DELAY(ABSOLUTE(PORT A (RETAIN (1)) (1))))"),
        wrap("(DELAY(ABSOLUTE(IOPATH A Y ((1)(2)(3)(4)))))"),
        wrap("(DELAY(ABSOLUTE(IOPATH A Y (1))))")+"garbage",
        std::string("(DELAYFILE(SDFVERSION \"3.0\")(TIMESCALE 2ns)(CELL(CELLTYPE \"X\")(INSTANCE)))"),
        std::string("(DELAYFILE(SDFVERSION \"3.0\")(SDFVERSION \"3.0\")(CELL(CELLTYPE \"X\")(INSTANCE)))"),
        std::string("(DELAYFILE(SDFVERSION \"3.0\")(CELL(CELLTYPE \"X\")(INSTANCE))(DESIGN \"X\"))"),
        std::string("/* unterminated"),std::string("(DELAYFILE(SDFVERSION \"unterminated)"),
        wrap("(DELAY(ABSOLUTE(IOPATH A Y ("+std::string(140,'(')+"1"+std::string(140,')')+"))))")}) {
        bool rejected=false;try{parse(s);}catch(const std::runtime_error& e){rejected=std::string(e.what()).find("test.sdf:")==0;}assert(rejected);
    }
    assert(sdf_ticks(".0005",1000000,1000)==1);
    assert(sdf_ticks(".00049999",1000000,1000)==0);
    assert(sdf_ticks("1.234e+2",1000,1)==123400);
    assert(sdf_ticks("18446744073709551615",1,1)==UINT64_MAX);
    assert(sdf_ticks("18446744073709551614.5",1,1)==UINT64_MAX);
    assert(sdf_ticks("-0.0",1,1)==0);
    for(auto s:{"-1","NaN","1e","18446744073709551615.5","18446744073709551616","1e1000000"}) {
        bool rejected=false;try{sdf_ticks(s,1,1);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
    }
    // A single CELL may contain millions of entries. The callback sees each
    // before the next is read, rather than collecting that CELL's entire tree.
    std::ostringstream large;large<<"(DELAYFILE(SDFVERSION \"3.0\")(CELL(CELLTYPE \"TOP\")(INSTANCE)(DELAY(ABSOLUTE";
    for(int i=0;i<100000;++i)large<<"(INTERCONNECT a/Q b/D (1:2:3))";
    large<<"))))";size_t seen=0;
    auto big=parse(large.str(),{{},{},[&](const SdfCell&,const SdfEntry& e){assert(e.kind=="INTERCONNECT");++seen;}});
    assert(seen==100000&&big.entries==seen);
    std::cout<<"PASS SDF callbacks, preserved timing data, strict syntax, 100000 streamed entries, exact ticks\n";
}
