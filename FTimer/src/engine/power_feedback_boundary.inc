// Optional averaged-power abstraction for controls entering a feedback SCC.
// Marginals come exclusively from this design's PI activities and Boolean
// functions. No reference-tool activity or power values enter this model.
std::vector<bool> feedback_boundary(activity.size(),false);
if (const char* option=std::getenv("FTIMER_POWER_FEEDBACK_BOUNDARY")) {
    const std::string mode(option);
    if (mode!="0" && mode!="1")
        throw std::invalid_argument("FTIMER_POWER_FEEDBACK_BOUNDARY must be 0 or 1");
    if (mode=="1") {
        std::vector<std::vector<size_t>> forward(gates.size()),reverse(gates.size());
        for (size_t i=0;i<gates.size();++i)
            for (const auto* f:{&gates[i].data,&gates[i].clock,&gates[i].clear,&gates[i].preset})
                for (auto n:f->nets) if (driver[n]>=0) {
                    forward[size_t(driver[n])].push_back(i);
                    reverse[i].push_back(size_t(driver[n]));
                }
        // Iterative Kosaraju traversal avoids stack depth proportional to a
        // large mapped cone. Register feedback is part of this graph.
        std::vector<bool> seen(gates.size(),false);
        std::vector<size_t> finish;
        for (size_t start=0;start<gates.size();++start) if (!seen[start]) {
            std::vector<std::pair<size_t,size_t>> stack{{start,0}};seen[start]=true;
            while (!stack.empty()) {
                auto& entry=stack.back();const auto u=entry.first;
                if (entry.second<forward[u].size()) {
                    const auto v=forward[u][entry.second++];
                    if (!seen[v]) {seen[v]=true;stack.push_back({v,0});}
                } else {finish.push_back(u);stack.pop_back();}
            }
        }
        std::vector<size_t> component(gates.size(),size_t(-1)),sizes;
        for (auto it=finish.rbegin();it!=finish.rend();++it) if (component[*it]==size_t(-1)) {
            const auto id=sizes.size();sizes.push_back(0);
            std::vector<size_t> stack{*it};component[*it]=id;
            while (!stack.empty()) {
                const auto u=stack.back();stack.pop_back();++sizes[id];
                for (auto v:reverse[u]) if (component[v]==size_t(-1)) {
                    component[v]=id;stack.push_back(v);
                }
            }
        }
        std::vector<bool> sequential_support(activity.size(),false);
        for (auto i:sequential) sequential_support[gates[i].net]=true;
        for (auto i:order) for (auto n:gates[i].data.nets)
            sequential_support[gates[i].net]=sequential_support[gates[i].net] || sequential_support[n];
        #include "power_feedback_storage.inc"
        std::vector<bool> candidate(activity.size(),false);
        // A PI used directly inside a feedback component must remain the
        // same random variable in its external input cones. Cutting a cone
        // sharing that PI would disconnect data/carry or reset correlations.
        std::vector<std::vector<uint32_t>> direct_roots(sizes.size());
        for (size_t i=0;i<gates.size();++i)
            for (const auto* f:{&gates[i].data,&gates[i].clock,&gates[i].clear,&gates[i].preset})
                for (auto n:f->nets) if (driver[n]<0 && activity[n].source!="clock" &&
                    (activity[n].rate>0 || (activity[n].probability>0 && activity[n].probability<1)))
                    direct_roots[component[i]].push_back(n);
        for (auto& roots:direct_roots) {
            std::sort(roots.begin(),roots.end());
            roots.erase(std::unique(roots.begin(),roots.end()),roots.end());
        }
        for (size_t i=0;i<gates.size();++i) {
            const bool cyclic=sizes[component[i]]>1 ||
                std::find(forward[i].begin(),forward[i].end(),i)!=forward[i].end();
            if (!cyclic || !storage_feedback[component[i]]) continue;
            for (const auto* f:{&gates[i].data,&gates[i].clock,&gates[i].clear,&gates[i].preset})
                for (auto n:f->nets) if (driver[n]>=0 &&
                    component[size_t(driver[n])]!=component[i] && !sequential_support[n] &&
                    activity[n].source!="clock") candidate[n]=true;
        }
        // Shared support is expressed in the averaged model's physical
        // propagation coordinates. A library unary projection can be inside
        // an external cone, not just its final gate at the SCC boundary.
        // Require one physical input pin: tied binary gates are not unary.
        std::vector<bool> primitive_projection(activity.size(),false);
        for (uint32_t n=0;n<activity.size();++n) if(driver[n]>=0 && !sequential_support[n]) {
            const auto i=size_t(driver[n]);const auto& f=gates[i].data;
            if(is_sequential[i] || f.nets.size()!=1 || (f.code!=1 && f.code!=2))continue;
            const auto pin=network.net(NetId{n}).driver;
            if(!valid(pin) || !valid(network.pin(pin).instance))continue;
            const auto& cell=network.cell(network.instance(network.pin(pin).instance).cell);
            if(!valid(cell.liberty_library) || !valid(cell.liberty_cell))continue;
            const auto& lc=impl_->liberty->library(cell.liberty_library.id).cells[cell.liberty_cell.id];
            size_t inputs=0;
            for(const auto& input:lc.pins)inputs+=input.direction==edacraft::core::PortDirection::Input;
            primitive_projection[n]=inputs==1;
        }
        auto projected_support=[&](uint32_t n) {
            std::vector<uint32_t> stack{n},roots;std::map<uint32_t,bool> visited;
            bool complete=true;
            while(!stack.empty()) {
                const auto v=stack.back();stack.pop_back();
                if(visited.count(v))continue;
                visited[v]=true;
                if(visited.size()>4096) {complete=false;break;}
                if(driver[v]<0 || primitive_projection[v]) {
                    if(activity[v].source!="clock" &&
                       (activity[v].rate>0 || (activity[v].probability>0 && activity[v].probability<1)))
                        roots.push_back(v);
                    continue;
                }
                const auto j=size_t(driver[v]);
                if(is_sequential[j] || !gates[j].data.valid) {complete=false;break;}
                for(auto dependency:gates[j].data.nets)stack.push_back(dependency);
            }
            return std::make_pair(complete,roots);
        };
        // External functions entering one storage component may share PI
        // variables even when none of those PIs enters the component directly.
        // Keep these functions joint: independently sampling an enable and a
        // data product can change a mux register into a different circuit.
        std::vector<std::map<uint32_t,unsigned>> external_root_uses(sizes.size());
        std::vector<bool> complete_external_support(sizes.size(),true);
        std::vector<std::vector<uint32_t>> external_nets(sizes.size());
        for(size_t i=0;i<gates.size();++i) if(storage_feedback[component[i]])
            for(const auto* f:{&gates[i].data,&gates[i].clock,&gates[i].clear,&gates[i].preset})
                for(auto n:f->nets) if(driver[n]<0 || component[size_t(driver[n])]!=component[i])
                    external_nets[component[i]].push_back(n);
        for(size_t c=0;c<sizes.size();++c) if(storage_feedback[c]) {
            auto& nets=external_nets[c];
            std::sort(nets.begin(),nets.end());nets.erase(std::unique(nets.begin(),nets.end()),nets.end());
            for(auto n:nets) {
                const auto support=projected_support(n);
                complete_external_support[c]=complete_external_support[c] && support.first;
                for(auto root:support.second)++external_root_uses[c][root];
            }
        }
        std::vector<uint8_t> bits(activity.size());
        std::vector<std::pair<uint32_t,Activity>> boundaries;
        for (uint32_t target=0;target<activity.size();++target) if (candidate[target]) {
            Truth truth;std::vector<size_t> cone;
            std::vector<std::pair<uint32_t,bool>> stack{{target,false}};
            std::map<uint32_t,bool> visited;bool bounded=true;
            while (!stack.empty() && bounded) {
                const auto [n,exit]=stack.back();stack.pop_back();
                if (exit) {cone.push_back(size_t(driver[n]));continue;}
                if (visited.count(n)) continue;
                visited[n]=true;
                if (driver[n]<0) {
                    truth.nets.push_back(n);bounded=truth.nets.size()<=12;continue;
                }
                const auto i=size_t(driver[n]);
                if (is_sequential[i] || !gates[i].data.valid || visited.size()>4096) {bounded=false;break;}
                stack.push_back({n,true});
                for (auto dependency:gates[i].data.nets) stack.push_back({dependency,false});
            }
            // Large primary-control functions retain the joint model rather
            // than silently replacing exact support with an independence fit.
            if (!bounded) continue;
            const auto support=projected_support(target);
            bool shared_root=!support.first;
            for (auto user:forward[size_t(driver[target])]) {
                const auto c=component[user];
                const auto& roots=direct_roots[c];
                shared_root|=!complete_external_support[c];
                for (auto n:support.second) {
                    const auto use=external_root_uses[c].find(n);
                    shared_root|=std::binary_search(roots.begin(),roots.end(),n) ||
                        (use!=external_root_uses[c].end() && use->second>1);
                }
            }
            // In the averaged model a physical unary BUF/INV entering
            // storage feedback supplies its propagated marginal. Native555/556
            // distinguish this boundary from a binary XOR tied to a constant.
            // Keep shared-root protection for complex external functions and
            // never classify hierarchy/assign pseudo-cells as library gates.
            if (shared_root && !primitive_projection[target]) continue;
            truth.valid=true;truth.values.reserve(size_t(1)<<truth.nets.size());
            for (size_t mask=0;mask<(size_t(1)<<truth.nets.size());++mask) {
                for (size_t k=0;k<truth.nets.size();++k) bits[truth.nets[k]]=uint8_t((mask>>k)&1);
                for (auto i:cone) {
                    const auto& f=gates[i].data;bool value=false;
                    for (auto term:f.terms) {
                        bool product=true;
                        for (size_t k=0;k<f.nets.size();++k)
                            if (term&(uint32_t(1)<<k)) product=product && bits[f.nets[k]];
                        value^=product;
                    }
                    bits[gates[i].net]=uint8_t(value);
                }
                truth.values.push_back(bits[target]!=0);
            }
            boundaries.push_back({target,Activity{transition_rate(truth,activity,2*sample_hz),
                probability(truth,activity),"default"}});
        }
        // Each physical boundary net is one shared stochastic root. Different
        // boundary nets retain separate identities, including complementary
        // controls implemented by distinct gates outside the SCC.
        for (const auto& entry:boundaries) {
            const auto n=entry.first;activity[n]=entry.second;driver[n]=-1;
            feedback_boundary[n]=true;state[n]=bernoulli(activity[n].probability);
        }
        result.feedback_boundary_nets=uint32_t(boundaries.size());
    }
}
