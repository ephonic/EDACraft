// dc_op.cpp - DC operating point (nonlinear Newton + gmin stepping + line search)
#include "dc_op.hpp"
#include "../assembly/lu_solver.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"

#include <algorithm>
#include <cmath>

namespace rfsim {

namespace {

void assemble(uint32_t numNodes,
              const std::vector<std::unique_ptr<DeviceModel>>& devices,
              const std::vector<double>& nodeV,
              const DcOpOptions& opts,
              SparseMatrix& G, Vector& F,
              std::vector<uint32_t>& vsOff) {
    std::vector<uint32_t> vsIdx;
    for (uint32_t i = 0; i < devices.size(); ++i)
        if (dynamic_cast<VoltageSource*>(devices[i].get())) vsIdx.push_back(i);
    uint32_t numVS = static_cast<uint32_t>(vsIdx.size());
    uint32_t n = numNodes + numVS;

    G.resize(n);
    F.assign(n, 0.0);
    vsOff.clear();

    auto getV = [&](uint32_t id) { return id == 0 ? 0.0 : nodeV[id]; };

    for (uint32_t i = 0; i < numNodes; ++i) {
        G.addPattern(i, i); G.add(i, i, opts.gmin);
        F[i] += opts.gmin * nodeV[i + 1];
    }

    for (uint32_t di = 0; di < devices.size(); ++di) {
        const auto& dev = devices[di];
        const auto& nds = dev->nodes();

        if (auto* res = dynamic_cast<Resistor*>(dev.get())) {
            double g = res->conductance();
            uint32_t n1 = nds.size()>0?nds[0]:0, n2 = nds.size()>1?nds[1]:0;
            if (n1!=0){G.addPattern(n1-1,n1-1);G.add(n1-1,n1-1,g);}
            if (n2!=0){G.addPattern(n2-1,n2-1);G.add(n2-1,n2-1,g);}
            if (n1!=0&&n2!=0){G.addPattern(n1-1,n2-1);G.add(n1-1,n2-1,-g);
                              G.addPattern(n2-1,n1-1);G.add(n2-1,n1-1,-g);}
            double iR = g*(getV(n1)-getV(n2));
            if(n1!=0)F[n1-1]+=iR; if(n2!=0)F[n2-1]-=iR;
        } else if (dynamic_cast<CurrentSource*>(dev.get())) {
            double I = dynamic_cast<CurrentSource*>(dev.get())->current();
            uint32_t n1=nds.size()>0?nds[0]:0, n2=nds.size()>1?nds[1]:0;
            if(n1!=0)F[n1-1]-=I; if(n2!=0)F[n2-1]+=I;
        } else if (dynamic_cast<VoltageSource*>(dev.get())) {
            uint32_t br=0; for(uint32_t k=0;k<vsIdx.size();++k) if(vsIdx[k]==di){br=numNodes+k;break;}
            vsOff.push_back(br);
            uint32_t n1=nds.size()>0?nds[0]:0, n2=nds.size()>1?nds[1]:0;
            double V = dynamic_cast<VoltageSource*>(dev.get())->voltage();
            if(n1!=0){G.addPattern(n1-1,br);G.add(n1-1,br,1.0);G.addPattern(br,n1-1);G.add(br,n1-1,1.0);}
            if(n2!=0){G.addPattern(n2-1,br);G.add(n2-1,br,-1.0);G.addPattern(br,n2-1);G.add(br,n2-1,-1.0);}
            G.addPattern(br,br);
            F[br] = (getV(n1)-getV(n2)) - V;
        } else if (dynamic_cast<Capacitor*>(dev.get())) {
        } else if (dynamic_cast<Inductor*>(dev.get())) {
            double g=1e6; uint32_t n1=nds.size()>0?nds[0]:0,n2=nds.size()>1?nds[1]:0;
            if(n1!=0&&n2!=0){G.addPattern(n1-1,n1-1);G.add(n1-1,n1-1,g);
                              G.addPattern(n2-1,n2-1);G.add(n2-1,n2-1,g);
                              G.addPattern(n1-1,n2-1);G.add(n1-1,n2-1,-g);
                              G.addPattern(n2-1,n1-1);G.add(n2-1,n1-1,-g);}
            else if(n1!=0){G.addPattern(n1-1,n1-1);G.add(n1-1,n1-1,g);}
            else if(n2!=0){G.addPattern(n2-1,n2-1);G.add(n2-1,n2-1,g);}
            double iL=g*(getV(n1)-getV(n2));
            if(n1!=0)F[n1-1]+=iL; if(n2!=0)F[n2-1]-=iL;
        } else if (auto* osdi = dynamic_cast<OsdiModel*>(dev.get())) {
            if (!osdi->ready()) continue;
            const OsdiDescriptor* d = osdi->descriptor();
            uint32_t nNodes = d->num_nodes;
            OperatingPoint op{nodeV};
            DeviceContribution dc;
            osdi->eval(op, dc);
            for (uint32_t k=0;k<nNodes&&k<nds.size()&&k<dc.f.size();++k)
                if (nds[k]!=0) F[nds[k]-1] -= dc.f[k];
            NodeId maxN=0; for(NodeId nn:nds) if(nn>maxN)maxN=nn;
            uint32_t fullDim=maxN+1;
            std::vector<double> jacMat(fullDim*fullDim,0.0);
            uint32_t nE=d->num_jacobian_entries;
            std::vector<double*> tgt(nE,nullptr);
            for(uint32_t e=0;e<nE;++e){
                const OsdiJacobianEntry& je=d->jacobian_entries[e];
                uint32_t lr=std::min(je.nodes.node_1,nNodes-1), lc=std::min(je.nodes.node_2,nNodes-1);
                NodeId gr=(lr<nds.size())?nds[lr]:0, gc=(lc<nds.size())?nds[lc]:0;
                tgt[e] = (gr<fullDim&&gc<fullDim)?&jacMat[gr*fullDim+gc]:&jacMat[0];
            }
            std::vector<uint32_t> nm(nds.size(),0);
            for(uint32_t k=0;k<nds.size();++k) nm[k]=nds[k];
            osdi->loadJacobianInto(tgt.data(),fullDim,nm);
            for(uint32_t rr=1;rr<fullDim;++rr) for(uint32_t cc=1;cc<fullDim;++cc){
                double v=jacMat[rr*fullDim+cc];
                if(v!=0.0){G.addPattern(rr-1,cc-1);G.add(rr-1,cc-1,-v);}
            }
        }
    }
    G.finalize();
}

bool newtonSolve(uint32_t numNodes,
                 const std::vector<std::unique_ptr<DeviceModel>>& devices,
                 std::vector<double>& nodeV,
                 const DcOpOptions& opts, bool hasNonlinear,
                 uint32_t& totalIters) {
    for (uint32_t iter = 0; iter < opts.maxIterations; ++iter) {
        SparseMatrix J; Vector F; std::vector<uint32_t> vsOff;
        assemble(numNodes, devices, nodeV, opts, J, F, vsOff);
        LuSolver solver;
        if (!solver.factorize(J)) return false;
        Vector negF(F.size());
        for (size_t k=0;k<F.size();++k) negF[k]=-F[k];
        Vector dx; solver.solve(negF, dx);

        double fOld=0; for(double fv:F) fOld+=fv*fv; fOld=std::sqrt(fOld);
        double alpha=1.0;
        std::vector<double> newNodeV(numNodes+1,0.0);
        for(int bt=0;bt<20;++bt){
            for(uint32_t i=0;i<numNodes;++i){
                double dv=alpha*dx[i];
                if(hasNonlinear&&std::fabs(dv)>opts.dvmax) dv=opts.dvmax*(dv>0?1.0:-1.0);
                newNodeV[i+1]=nodeV[i+1]+dv;
            }
            SparseMatrix J2; Vector F2; std::vector<uint32_t> vsOff2;
            assemble(numNodes, devices, newNodeV, opts, J2, F2, vsOff2);
            double fNew=0; for(double fv:F2) fNew+=fv*fv; fNew=std::sqrt(fNew);
            if(fNew<=fOld*(1.0+1e-10)||alpha<1e-6) break;
            alpha*=0.5;
        }
        double maxDelta=0;
        for(uint32_t i=1;i<=numNodes;++i){
            double dv=std::fabs(newNodeV[i]-nodeV[i]);
            double scl=std::max(std::fabs(newNodeV[i]),std::fabs(nodeV[i]))+opts.abstol;
            if(dv/scl>maxDelta) maxDelta=dv/scl;
        }
        nodeV=newNodeV;
        ++totalIters;
        if(!hasNonlinear) return true;
        if(maxDelta<opts.reltol) return true;
    }
    return false;
}

} // namespace

DcOpResult solveDcOp(uint32_t numNodes,
                     const std::vector<std::unique_ptr<DeviceModel>>& devices,
                     const DcOpOptions& opts) {
    DcOpResult r;

    bool hasNonlinear=false;
    for(const auto& d:devices)
        if(auto* o=dynamic_cast<OsdiModel*>(d.get()))
            if(!o->is_linear()&&o->ready()) hasNonlinear=true;

    // 跨 DC 求解前重置 limiting 状态，避免前一次求解的 limiting 记忆污染新工作点
    for(const auto& d:devices)
        if(auto* o=dynamic_cast<OsdiModel*>(d.get()))
            o->resetLimiting();

    std::vector<double> nodeV(numNodes+1,0.0);

    std::vector<double> gminSched;
    if(hasNonlinear && opts.gminSteps>0){
        for(uint32_t s=0;s<opts.gminSteps;++s){
            double frac=double(opts.gminSteps-s)/double(opts.gminSteps);
            gminSched.push_back(opts.gminStart*frac+opts.gmin*(1.0-frac));
        }
        gminSched.push_back(opts.gmin);
    } else {
        gminSched.push_back(opts.gmin);
    }

    bool converged=false;
    for(size_t gi=0;gi<gminSched.size();++gi){
        DcOpOptions o=opts; o.gmin=gminSched[gi];
        if(gi+1<gminSched.size()) o.maxIterations=std::min(opts.maxIterations,uint32_t(50));
        converged = newtonSolve(numNodes,devices,nodeV,o,hasNonlinear,r.iterations);
    }

    r.converged=converged;
    if(!converged && hasNonlinear) r.diags.warn({},"DC: did not converge");

    {
        SparseMatrix J; Vector F; std::vector<uint32_t> vsOff;
        assemble(numNodes,devices,nodeV,opts,J,F,vsOff);
        LuSolver solver;
        if(solver.factorize(J)){
            Vector negF(F.size()); for(size_t k=0;k<F.size();++k) negF[k]=-F[k];
            Vector dx; solver.solve(negF,dx);
            r.nodeVoltages.assign(numNodes+1,0.0);
            for(uint32_t i=0;i<numNodes;++i) r.nodeVoltages[i+1]=nodeV[i+1]+dx[i];
            r.branchCurrents.assign(vsOff.size(),0.0);
            for(uint32_t k=0;k<vsOff.size();++k)
                r.branchCurrents[k]=-(vsOff[k]<dx.size()?dx[vsOff[k]]:0.0);
        }
    }
    return r;
}

} // namespace rfsim
