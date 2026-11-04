#include "sdf_models.hpp"
#include "liberty/liberty_parser.hh"
#include "liberty/db_api.h"
#include <fstream>
#include <iterator>
#include <set>
#include <stdexcept>

namespace dsim {
// Reuse the provided Liberty tokenizer. Only timing-group sdf_cond/when pairs
// are retained, without building CCS table objects for this preparation step.
SdfConditionAliases liberty_sdf_conditions(const std::vector<std::string>& files,const TimingLibrary& library) {
    using te::parser::Token;using T=te::parser::TokenType;
    std::set<std::string> wanted;for(const auto& m:library.models)wanted.insert(m.name);
    SdfConditionAliases result;
    for(const auto& file:files) {
        if(edacraft::core::dbio::detect_library_file(file)==edacraft::core::dbio::LibraryFileFormat::SynopsysDb)
            throw std::runtime_error(file+": native Synopsys DB SDF condition ownership is unresolved; binary data cannot be treated as text Liberty");
        std::ifstream in(file,std::ios::binary);if(!in)throw std::runtime_error("cannot read Liberty "+file);
        std::string data{std::istreambuf_iterator<char>(in),{}};
        te::parser::LibertyTokenizer lexer(data);Token token=lexer.next();
        auto next=[&](){token=lexer.next();};
        auto fail=[&](){throw std::runtime_error(file+":"+std::to_string(token.line)+": malformed Liberty condition metadata");};
        std::function<void(std::string,std::string,int)> group;
        group=[&](std::string kind,std::string cell,int depth) {
            if(depth>128)fail();
            std::map<std::string,std::string> attrs;
            while(token.type!=T::RBrace) {
                if(token.type==T::Eof)fail();
                if(token.type!=T::Ident){next();continue;}
                auto name=token.text;next();
                if(token.type==T::Colon) {
                    next();std::string value;
                    while(token.type!=T::Semi) {
                        if(token.type==T::Eof||token.type==T::LBrace||token.type==T::RBrace)fail();
                        if(!value.empty())value+=' ';value+=token.text;next();
                    }
                    next();if(kind=="timing"&&(name=="sdf_cond"||name=="when"))attrs[name]=value;
                } else if(token.type==T::LParen) {
                    next();int parens=1;std::string argument;
                    while(parens) {
                        if(token.type==T::Eof)fail();
                        if(token.type==T::LParen)++parens;else if(token.type==T::RParen)--parens;
                        if(parens){if(!argument.empty())argument+=' ';argument+=token.text;}next();
                    }
                    if(token.type==T::LBrace) {
                        next();auto child=name=="cell"?argument:cell;
                        if(name=="cell"&&!wanted.count(argument)) {
                            int braces=1;while(braces){if(token.type==T::Eof)fail();if(token.type==T::LBrace)++braces;else if(token.type==T::RBrace)--braces;next();}
                        } else group(name,child,depth+1);
                    } else if(token.type==T::Semi)next();
                } else if(token.type==T::LBrace){next();group(name,cell,depth+1);}
            }
            next();
            if(kind=="timing"&&!cell.empty()&&attrs.count("sdf_cond")&&attrs.count("when")) {
                auto alias=attrs.at("sdf_cond");
                if(alias.empty()||alias.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")!=std::string::npos)return;
                const auto& value=attrs.at("when");auto [it,inserted]=result[cell].emplace(alias,value);
                if(!inserted&&timing_expression_key(it->second)!=timing_expression_key(value))throw std::runtime_error(file+": conflicting Liberty sdf_cond definitions for "+cell+"."+alias);
            }
        };
        while(token.type!=T::Eof) {
            if(token.type!=T::Ident)fail();auto name=token.text;next();
            if(token.type!=T::LParen)fail();int parens=1;next();
            while(parens){if(token.type==T::Eof)fail();if(token.type==T::LParen)++parens;else if(token.type==T::RParen)--parens;next();}
            if(token.type!=T::LBrace)fail();next();group(name,{},0);
        }
    }
    return result;
}
}
