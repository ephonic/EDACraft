// A boundary abstraction is applicable to storage feedback, whose next
// state can hold or overwrite its current state, but never complements it.
// Arithmetic recurrences such as Q^increment retain the joint estimator.
std::vector<bool> storage_feedback(sizes.size(),false);
std::vector<std::vector<size_t>> members(sizes.size()),comb_members(sizes.size());
for(size_t i=0;i<gates.size();++i)members[component[i]].push_back(i);
for(auto i:order)comb_members[component[i]].push_back(i);
std::vector<uint8_t> storage_bits(activity.size());
auto scalar_value=[&](const Function& f) {
    bool value=false;
    for(auto term:f.terms) {
        bool product=true;
        for(size_t k=0;k<f.nets.size();++k)
            if(term&(uint32_t(1)<<k))product=product && storage_bits[f.nets[k]];
        value^=product;
    }
    return value;
};
for(size_t c=0;c<sizes.size();++c) {
    if(members[c].size()>4096)continue;
    size_t state_gate=size_t(-1),state_count=0;
    std::vector<uint32_t> external;
    bool bounded=true;
    for(auto i:members[c]) {
        if(is_sequential[i]) {state_gate=i;++state_count;}
        if(!gates[i].data.valid) {bounded=false;break;}
        for(auto n:gates[i].data.nets) if(driver[n]<0 || component[size_t(driver[n])]!=c) {
            if(activity[n].rate==0 && (activity[n].probability==0 || activity[n].probability==1))
                storage_bits[n]=uint8_t(activity[n].probability);
            else if(std::find(external.begin(),external.end(),n)==external.end())external.push_back(n);
            if(external.size()>12) {bounded=false;break;}
        }
    }
    if(!bounded || state_count!=1)continue;
    bool monotone=true,hold=false,overwrite_zero=false,overwrite_one=false;
    for(size_t mask=0;mask<(size_t(1)<<external.size()) && monotone;++mask) {
        for(size_t k=0;k<external.size();++k)storage_bits[external[k]]=uint8_t((mask>>k)&1);
        bool next[2];
        for(unsigned q=0;q<2;++q) {
            storage_bits[gates[state_gate].net]=uint8_t(q);
            for(auto i:comb_members[c])storage_bits[gates[i].net]=scalar_value(gates[i].data);
            next[q]=scalar_value(gates[state_gate].data);
        }
        monotone=!(next[0] && !next[1]);
        hold|=!next[0] && next[1];
        overwrite_zero|=!next[0] && !next[1];
        overwrite_one|=next[0] && next[1];
    }
    storage_feedback[c]=monotone && hold && overwrite_zero && overwrite_one;
}
