#include "liberty/db_api.h"
#include <zlib.h>
#include <cassert>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
using namespace edacraft::core;
namespace fs=std::filesystem;
static std::string token(const std::string& s){return std::string(1,char(s.size()))+s;}
static std::string f32(float value){uint32_t b;std::memcpy(&b,&value,4);std::string r;for(int i=24;i>=0;i-=8)r+=char(b>>i);return r;}
static std::string array(const std::string& tag,std::initializer_list<float> values){std::string r=tag+char(values.size());for(auto v:values)r+=f32(v);return r;}
static std::string gzip(const std::string& text){
    z_stream z{};assert(deflateInit2(&z,6,Z_DEFLATED,31,8,Z_DEFAULT_STRATEGY)==Z_OK);
    std::string out(compressBound(text.size())+32,'\0');
    z.next_in=(Bytef*)text.data();z.avail_in=text.size();z.next_out=(Bytef*)out.data();z.avail_out=out.size();
    assert(deflate(&z,Z_FINISH)==Z_STREAM_END);out.resize(z.total_out);deflateEnd(&z);return out;
}
static void write(const fs::path& path,const std::string& text){std::ofstream f(path,std::ios::binary);f.write(text.data(),text.size());assert(f.good());}
int main(int argc,char**argv){
    assert(argc==2);fs::path dir=argv[1];fs::create_directories(dir);
    auto table=token("cell_rise")+array(std::string("\x22\x03",2),{.25f,.5f})+
        array(std::string("\x22\x03",2),{1,2})+array(std::string("\x82\x02\x03",3),{3,4,5,6});
    std::vector<native::NldmTable> tables;
    assert(native::parse_stream_tables(table,tables));assert(tables.size()==1);
    assert(tables[0].kind=="cell_rise");assert(tables[0].axis1==std::vector<float>({.25f,.5f}));
    assert(tables[0].axis2==std::vector<float>({1,2}));assert(tables[0].values==std::vector<float>({3,4,5,6}));
    // Compact CCS coordinate markers and signed current samples.
    auto wave=std::string("\x30\x09\x01",3)+f32(.125f)+std::string("\x02\x06\x03\x01",4)+f32(.25f)+
        std::string("\x03\x01\x04\x06\x03\x01",6)+f32(.5f)+
        array(std::string("\x3e\x03",2),{0,.125f,.25f,.5f})+
        array(std::string("\x3e\x03",2),{0,-.25f,.125f,0})+std::string("\x09\x04\x0a\x14\0",5);
    std::vector<native::CcsVectorDoc> ccs;
    assert(native::parse_stream_ccs(wave,256,"output_current_rise",ccs));assert(ccs.size()==1);
    assert(ccs[0].vectors.size()==1);const auto& v=ccs[0].vectors[0];
    assert(v.ref_time==.125f && v.slew==.25f && v.cap==.5f);
    assert(v.times==std::vector<float>({0,.125f,.25f,.5f}));assert(v.currents==std::vector<float>({0,-.25f,.125f,0}));
    const std::string magic=std::string("\x03\x17\x10\x63\x00\x40\xff\x03",8)+std::string(248,0);
    auto root=token("db library name")+char(0)+token("#unit_fixture");
    auto file=dir/"fixture.db";write(file,magic+gzip(table)+gzip(wave)+gzip(root));
    native::DbDocument doc;std::string error="stale";
    assert(native::read_synopsys_db(file.string(),doc,&error));assert(error.empty());
    assert(doc.info.stream_count==3 && doc.info.library_name=="unit_fixture");
    assert(doc.ccs.size()==1 && doc.tables.size()==1 && !doc.simulation_model_complete);
    LibertyDB db;StringPool pool;db.add_library(pool.intern("existing"));auto size=pool.size();
    assert(!dbio::read_library_file(file.string(),db,pool,&error));
    assert(error.find("model incomplete")!=std::string::npos);
    assert(db.library_count()==1 && pool.size()==size && pool.view(db.library(0).name)=="existing");
    auto text=dir/"text.db";write(text,"/*"+std::string(70000,'x')+"*/\n// format by content\nlibrary(example){cell(INV){area:1;pin(A){direction:input;}pin(Y){direction:output;function:\"!A\";}}}");
    assert(dbio::detect_library_file(text.string())==dbio::LibraryFileFormat::LibertyText);
    assert(dbio::read_library_file(text.string(),db,pool,&error));
    assert(db.library_count()==2 && pool.view(db.library(1).name)=="example");
    assert(pool.view(db.library(1).cells[0].pins[1].function)=="!A");
    auto bad=dir/"bad.lib";write(bad,"library broken");size=pool.size();
    assert(!dbio::read_library_file(bad.string(),db,pool,&error));assert(db.library_count()==2 && pool.size()==size);
    write(bad,magic);auto before=native::db_document_json(doc);
    assert(!native::read_synopsys_db(bad.string(),doc,&error));assert(native::db_document_json(doc)==before);
    // Cut every byte boundary of valid records and include malformed varints.
    // These are untrusted binary readers; ASan/UBSan run this same corpus.
    for(const auto& data:{table,wave,std::string(1024,char(0xff))})
        for(size_t i=0;i<=data.size();++i){
            std::vector<native::NldmTable> t;native::parse_stream_tables(data.substr(0,i),t);
            std::vector<native::CcsVectorDoc> w;native::parse_stream_ccs(data.substr(0,i),0,"",w);
        }
    std::mt19937 rng(96);
    for(size_t n=0;n<1024;++n){
        std::string data(n,'\0');for(char& c:data)c=char(rng());
        std::vector<native::NldmTable> t;native::parse_stream_tables(data,t);
        std::vector<native::CcsVectorDoc> w;native::parse_stream_ccs(data,0,"",w);
    }
    std::cout<<"PASS native exact float arrays/CCS samples, transactional loads, malformed/truncated corpus\n";
}
