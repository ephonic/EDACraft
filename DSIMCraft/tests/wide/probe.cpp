#define DSIM_WIDE_VALUES 1
#include "dsim/runtime.hpp"
#include <iomanip>
using namespace dsim;
static V value(std::string a,std::string b,int width){
    std::vector<V::Word> words(size_t((width+63)/64));
    auto plane=[&](std::string text,bool unknown){size_t i=0;while(!text.empty()){size_t start=text.size()>16?text.size()-16:0;auto n=std::stoull(text.substr(start),nullptr,16);if(i>=words.size())throw std::runtime_error("probe plane exceeds width");if(unknown)words[i].b=n;else words[i].a=n;++i;text.resize(start);}};
    plane(a,false);plane(b,true);return V::from_words(std::move(words),width);
}
int main(){try{std::string op,aa,ax,ba,bx;int aw,bw,width,offset;size_t count=0;
    while(std::cin>>op>>aw>>bw>>width>>offset>>aa>>ax>>ba>>bx){auto a=value(aa,ax,aw),b=value(ba,bx,bw);V out;
        if(op=="slice")out=slice(a,offset,width);
        else if(op=="replace")out=replace(a,offset,width,b);
        else if(op=="concat")out=concat(a,b);
        else if(op=="size")out=a.size(width);
        else if(op=="resolve")out=resolve(a,b);
        else if(op=="mux")out=mux(V::x(1),a,b,width);
        else if(op=="case")out=V(case_match(a,b,offset));
        else if(op=="not")out=inv(a);
        else if(op=="redand")out=unary("&",a,aw);
        else if(op=="redor")out=unary("|",a,aw);
        else if(op=="redxor")out=unary("^",a,aw);
        else if(op=="neg")out=unary("-",a,aw);
        else out=binary(op,a,b,width);
        std::cout<<format(out,'b')<<' '<<format(out,'d')<<'\n';++count;
    }
    if(!std::cin.eof())throw std::runtime_error("invalid probe input");std::cerr<<"checked "<<count<<" operations\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
