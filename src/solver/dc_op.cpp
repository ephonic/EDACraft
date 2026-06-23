// dc_op.cpp - DC operating point (nonlinear Newton + gmin stepping + line search)
#include "dc_op.hpp"
#include "../assembly/klu_solver.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace rfsim {

namespace {

// 由环境变量 RFSIM_DCOP_VERBOSE 控制：0=静默 1=每外层 Newton 一行 2=每步带最差节点
int dcopVerbose() {
    static int v = []() {
        const char* s = std::getenv("RFSIM_DCOP_VERBOSE");
        return s ? std::atoi(s) : 0;
    }();
    return v;
}

void assemble(uint32_t numNodes,
              const std::vector<std::unique_ptr<DeviceModel>>& devices,
              const std::vector<double>& nodeV,
              const DcOpOptions& opts,
              SparseMatrix& G, Vector& F,
              std::vector<uint32_t>& vsOff) {
    // P4 post-A1：assemble 在 Newton 主循环里每 iter 调用 1~2 次，OSDI 器件
    // 的 jacMat / tgt / nm 内部又是 per-device 分配，O(numDevices · numIter)
    // 个 std::vector 构造。改为 thread_local scratch + .assign()，对 N=20
    // BSIM4 这种 200 个 OSDI 实例的电路单次 DC 求解可省 ~1e4 次小堆分配。
    thread_local std::vector<uint32_t> vsIdx;
    thread_local std::vector<double>   tlJacMat;
    thread_local std::vector<double*>  tlTgt;
    thread_local std::vector<uint32_t> tlNm;
    vsIdx.clear();
    for (uint32_t i = 0; i < devices.size(); ++i)
        if (dynamic_cast<VoltageSource*>(devices[i].get())) vsIdx.push_back(i);
    uint32_t numVS = static_cast<uint32_t>(vsIdx.size());
    uint32_t n = numNodes + numVS;

    G.resize(n);
    F.assign(n, 0.0);
    vsOff.clear();

    auto getV = [&](uint32_t id) { return id == 0 ? 0.0 : nodeV[id]; };

    for (uint32_t i = 0; i < numNodes; ++i) {
        G.addPattern(i, i); G.add(i, i, opts.gmin.gmin);
        F[i] += opts.gmin.gmin * nodeV[i + 1];
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
            // V2-γ source stepping：按 opts.vsScale 缩放电压源
            double V = dynamic_cast<VoltageSource*>(dev.get())->voltage() * opts.vsScale;
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
            // OSDI 残差按 OpenVAF 约定为"流出节点的总电流"（与线性器件 stamp
            // F[n]+=current_out 同向）。早期实现取负号导致线性/OSDI 器件叠加时
            // 符号相反（diode 反偏化、cascode 漂浮），故 V2-γ 修正为 += 累加，
            // 雅可比同向（见下方 G.add(...,v) 而非 -v）。
            for (uint32_t k=0;k<nNodes&&k<nds.size()&&k<dc.f.size();++k) {
                // 内部隐式节点（OSDI num_nodes > num_terminals 的部分）的残差是
                // 器件内部 KCL，不应进入外部 MNA 残差向量 F。这些节点的 NodeId
                // 可能远超 numNodes（host 在 OsdiModel::initialize 中递增分配），
                // 写入会 heap-buffer-overflow。仅 stamp 外部可见节点（NodeId 在
                // [1, numNodes] 范围）。详见 docs/ki3_internal_node_overflow.md。
                NodeId nk = nds[k];
                if (nk == 0 || nk > numNodes) continue;
                F[nk - 1] += dc.f[k];
            }
            // Jacobian stamp：fullDim 是 MNA 矩阵维度 = numNodes + numVS（电压源
            // 分支）。旧实现用 max(nds)（含内部节点），会把器件内部隐式方程错误
            // 装配进外部 MNA 矩阵，且对 G(F) 越界写。内部节点必须被 OSDI 在
            // instance_data 内部自洽求解，host 不参与。这里 clamp 到 fullMnaDim。
            uint32_t fullMnaDim = numNodes + numVS;
            uint32_t fullDim = fullMnaDim + 1;  // +1 for 1-based NodeId 偏移
            tlJacMat.assign(static_cast<size_t>(fullDim)*fullDim, 0.0);
            uint32_t nE=d->num_jacobian_entries;
            tlTgt.assign(nE, nullptr);
            for(uint32_t e=0;e<nE;++e){
                const OsdiJacobianEntry& je=d->jacobian_entries[e];
                uint32_t lr=std::min(je.nodes.node_1,nNodes-1), lc=std::min(je.nodes.node_2,nNodes-1);
                NodeId gr=(lr<nds.size())?nds[lr]:0, gc=(lc<nds.size())?nds[lc]:0;
                // 内部节点跳过（与上面 F 装配一致）：NodeId > numNodes 的不装配到外部 MNA
                bool grOk = (gr == 0) || (gr <= numNodes);
                bool gcOk = (gc == 0) || (gc <= numNodes);
                tlTgt[e] = (grOk && gcOk && gr<fullDim && gc<fullDim)
                           ? &tlJacMat[gr*fullDim+gc] : &tlJacMat[0];
            }
            tlNm.assign(nds.size(), 0);
            for(uint32_t k=0;k<nds.size();++k) tlNm[k]=nds[k];
            osdi->loadJacobianInto(tlTgt.data(),fullDim,tlNm);
            for(uint32_t rr=1;rr<fullDim;++rr) for(uint32_t cc=1;cc<fullDim;++cc){
                double v=tlJacMat[rr*fullDim+cc];
                if(v!=0.0){G.addPattern(rr-1,cc-1);G.add(rr-1,cc-1,v);}
            }
        }
    }
    G.finalize();
}

bool newtonSolve(uint32_t numNodes,
                 const std::vector<std::unique_ptr<DeviceModel>>& devices,
                 std::vector<double>& nodeV,
                 const DcOpOptions& opts, bool hasNonlinear,
                 uint32_t& totalIters,
                 uint32_t& innerFloorAccepts,
                 BenchCounters* bench = nullptr,
                 bool* floorAccepted = nullptr) {
    int vb = dcopVerbose();
    for (uint32_t iter = 0; iter < opts.maxIterations; ++iter) {
        SparseMatrix J; Vector F; std::vector<uint32_t> vsOff;
        assemble(numNodes, devices, nodeV, opts, J, F, vsOff);
        KluSolver solver;
        if (!solver.factorize(J)) {
            if (vb) std::fprintf(stderr, "  [dc] iter=%u factorize FAILED\n", iter);
            if (bench) { bench->klu_factor_ms += solver.factorMs(); bench->klu_solve_ms += solver.solveMs(); }
            return false;
        }
        Vector negF(F.size());
        for (size_t k=0;k<F.size();++k) negF[k]=-F[k];
        Vector dx; solver.solve(negF, dx);
        if (bench) { bench->klu_factor_ms += solver.factorMs(); bench->klu_solve_ms += solver.solveMs(); }

        double fOld=0; for(double fv:F) fOld+=fv*fv; fOld=std::sqrt(fOld);
        double alpha=1.0;
        std::vector<double> newNodeV(numNodes+1,0.0);
        int btUsed = 0;
        double fNewBest = fOld;
        bool descent = false;
        for(int bt=0;bt<20;++bt){
            for(uint32_t i=0;i<numNodes;++i){
                double dv=alpha*dx[i];
                if(hasNonlinear&&std::fabs(dv)>opts.dvmax) dv=opts.dvmax*(dv>0?1.0:-1.0);
                newNodeV[i+1]=nodeV[i+1]+dv;
            }
            SparseMatrix J2; Vector F2; std::vector<uint32_t> vsOff2;
            assemble(numNodes, devices, newNodeV, opts, J2, F2, vsOff2);
            double fNew=0; for(double fv:F2) fNew+=fv*fv; fNew=std::sqrt(fNew);
            fNewBest = fNew;
            if(fNew<=fOld*(1.0+1e-6)) { btUsed = bt; descent = true; break; }
            alpha*=0.5; btUsed = bt+1;
        }
        // 残差地板检测：
        //   - 当 alpha 必须重度缩水（< 1e-3）且 |F| 几乎没变（双向 < 0.1%）时，
        //     说明当前 gmin 下 Newton 步即使下降也下降不动，进入残差地板。
        //   - 此时把当前点作为该 gmin 的"已收敛解"，让外层 gmin 调度去降低 gmin
        //     继续推进——gmin 减小后残差地板会随之下降。
        const double fDelta = std::fabs(fNewBest - fOld);
        const bool stagnant = (alpha < 1e-3) && (fDelta < fOld * 1e-3) && fOld > 0.0;
        if (stagnant) {
            nodeV = newNodeV;
            ++totalIters;
            ++innerFloorAccepts;
            if (vb)
                std::fprintf(stderr,
                    "  [dc] iter=%u gmin=%.1e |F|=%.3e (residual floor; "
                    "alpha=%.1e bt=%d, accepting as gmin-step solution)\n",
                    iter, opts.gmin.gmin, fNewBest, alpha, btUsed);
            if (floorAccepted) *floorAccepted = true;  // H3: 标记 floor-accept
            return true;
        }
        // 线搜索完全失败（Newton 方向不再是下降方向 + 残差又没停滞）通常意味着
        // 雅可比已奇异 / Newton 真发散。直接返回失败让外层 gmin 调度回退。
        if (!descent) {
            if (vb)
                std::fprintf(stderr,
                    "  [dc] iter=%u gmin=%.1e |F|=%.3e->%.3e LINE SEARCH FAILED (non-descent)\n",
                    iter, opts.gmin.gmin, fOld, fNewBest);
            return false;
        }

        // P3 post-A1：|F| 提早退出 —— 如果新点 |F| 已经低于 abstol，不必再
        // 算 maxDelta / 走多余的 iter；典型场景是 source-step 末段 warm-start
        // 已经命中目标偏置，再迭代纯属空转。注意要在 nodeV 更新之后再返回。
        if (fNewBest < opts.abstol) {
            nodeV = newNodeV;
            ++totalIters;
            if (vb)
                std::fprintf(stderr,
                    "  [dc] iter=%u gmin=%.1e |F|=%.3e (abstol reached, early exit)\n",
                    iter, opts.gmin.gmin, fNewBest);
            return true;
        }

        double maxDelta=0;
        uint32_t worstIdx=0;
        for(uint32_t i=1;i<=numNodes;++i){
            double dv=std::fabs(newNodeV[i]-nodeV[i]);
            double scl=std::max(std::fabs(newNodeV[i]),std::fabs(nodeV[i]))+opts.abstol;
            double rel=dv/scl;
            if(rel>maxDelta) { maxDelta=rel; worstIdx=i; }
        }
        if (vb) {
            std::fprintf(stderr,
                "  [dc] iter=%u gmin=%.1e |F|=%.3e->%.3e alpha=%.3e bt=%d "
                "maxDelta=%.3e@n%u v=%.4g newv=%.4g\n",
                iter, opts.gmin.gmin, fOld, fNewBest, alpha, btUsed,
                maxDelta, worstIdx,
                worstIdx ? nodeV[worstIdx] : 0.0,
                worstIdx ? newNodeV[worstIdx] : 0.0);
            if (vb >= 2) {
                // 打印所有节点的快照
                for (uint32_t i=1;i<=numNodes;++i)
                    std::fprintf(stderr, "       n%u: %.6g -> %.6g\n", i, nodeV[i], newNodeV[i]);
            }
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
    SteadyTimer tWall;
    BenchCounters* bench = benchJsonEnabled() ? &r.bench : nullptr;

    bool hasNonlinear=false;
    for(const auto& d:devices)
        if(auto* o=dynamic_cast<OsdiModel*>(d.get()))
            if(!o->is_linear()&&o->ready()) hasNonlinear=true;

    // 跨 DC 求解前重置 limiting 状态，避免前一次求解的 limiting 记忆污染新工作点
    for(const auto& d:devices)
        if(auto* o=dynamic_cast<OsdiModel*>(d.get()))
            o->resetLimiting();

    std::vector<double> nodeV(numNodes+1,0.0);

    // 源步进 (source stepping) 调度：当 opts.sourceStepCount > 0 且存在
    // 非线性器件时，把所有 VS 电压乘以 ε∈(0,1] 多次求解，每步 warm-start。
    // 用于级联 MOSFET 拓扑：在 V_spec 下 OSDI 模型 limiter 在 V_DS=0 处会
    // 产生数量级巨大的负 Jacobian 项，从冷启动 Newton 无法逃离。源步进让
    // 工作点沿 ε 平滑路径迁移到目标偏置。
    std::vector<double> vsSched;
    if (hasNonlinear && opts.sourceStepCount > 0) {
        const uint32_t N = opts.sourceStepCount;
        // P3 post-A1：二次 schedule  t = 1 - (1 - u)^2 ，dense-near-1。
        // BSIM4 在 V_DS 接近目标值时 limiter 雅可比突变最剧烈，把更多 source
        // step 放在 ε 接近 1 的区间，使每步前后工作点距离更短、warm-start 更准。
        // 低 ε 端 (弱反型/截止区) Jacobian 平滑，少几步无害。
        for (uint32_t s = 1; s <= N; ++s) {
            double u = double(s) / double(N);
            double t = 1.0 - (1.0 - u) * (1.0 - u);
            vsSched.push_back(t);
        }
    } else {
        vsSched.push_back(opts.vsScale);  // 单步：直接用 opts 指定的 scale（默认 1.0）
    }

    auto initVoltagesForScale = [&](double scale) {
        // 重置 nodeV 并按 scale 重新初始化（仅在 si==0 时使用；后续 step warm-start）
        std::fill(nodeV.begin(), nodeV.end(), 0.0);
        // seeded[i] : 该节点已被 VS 锚定或经电阻 BFS 传播得到非零猜测值
        std::vector<uint8_t> seeded(numNodes + 1, 0);
        // Pass 1: 直接接地的 VS 锚定其非接地节点（保留原有逻辑）。
        for (const auto& dev : devices) {
            if (auto* vs = dynamic_cast<VoltageSource*>(dev.get())) {
                const auto& nds = vs->nodes();
                if (nds.size() < 2) continue;
                NodeId n1 = nds[0], n2 = nds[1];
                double V = vs->voltage() * scale;
                if (dcopVerbose() >= 2) {
                    std::fprintf(stderr,
                        "[dc.init] VS '%s' nodes=(%u,%u) V=%.4g numNodes=%u (scale=%.3g)\n",
                        dev->name().c_str(), (unsigned)n1, (unsigned)n2, V,
                        numNodes, scale);
                }
                if (n2 == 0 && n1 != 0 && n1 <= numNodes) {
                    nodeV[n1] = V;
                    seeded[n1] = 1;
                } else if (n1 == 0 && n2 != 0 && n2 <= numNodes) {
                    nodeV[n2] = -V;
                    seeded[n2] = 1;
                }
            }
        }
        // Pass 2: 沿电阻图做 BFS 把"半电源"猜测值传播到悬浮节点。
        // 经验上 MOSFET 漏极挂电阻到 VDD 时, V_drain 初值=0 会让 BSIM4 在
        // V_DS≈0、V_GS≈Vth+ε 的深 triode 工作点上产生极大平滑 gds 导数,
        // 击穿冷启动 Newton。给悬浮端一个 0.5*V_anchor 的中轨猜测后,
        // 工作点落在饱和区或近饱和区, 雅可比平滑很多。
        // 仅在非线性电路上启用 —— 纯线性电路无需 warm-start, 一步即解。
        if (hasNonlinear) {
            constexpr int kMaxPasses = 32;
            for (int pass = 0; pass < kMaxPasses; ++pass) {
                bool changed = false;
                for (const auto& dev : devices) {
                    auto* res = dynamic_cast<Resistor*>(dev.get());
                    if (!res) continue;
                    const auto& nds = res->nodes();
                    if (nds.size() < 2) continue;
                    NodeId n1 = nds[0], n2 = nds[1];
                    if (n1 == 0 || n2 == 0) continue;          // 接地电阻不携带电压信息
                    if (n1 > numNodes || n2 > numNodes) continue;
                    if (seeded[n1] && !seeded[n2]) {
                        nodeV[n2] = 0.5 * nodeV[n1];
                        seeded[n2] = 1;
                        changed = true;
                    } else if (seeded[n2] && !seeded[n1]) {
                        nodeV[n1] = 0.5 * nodeV[n2];
                        seeded[n1] = 1;
                        changed = true;
                    }
                }
                if (!changed) break;
            }
            // Pass 3: 通过非线性器件 (MOSFET / 二极管) 传播。差分对的
            // 尾电流源漏极、cascode 中间节点常常没有电阻直接接到锚定节点,
            // pass-2 BFS 无法到达。这里给每个含至少一个已锚定节点的非线性
            // 器件, 把它所有悬浮端口设为已锚定端口（含 GND/body）的算术
            // 均值 —— 既不强 push 到 V_DS=0 (那是冷启动 hostile 点),
            // 也不无脑选 V_max/2。
            for (int pass = 0; pass < kMaxPasses; ++pass) {
                bool changed = false;
                for (const auto& dev : devices) {
                    if (dev->is_linear()) continue;
                    const auto& nds = dev->nodes();
                    if (nds.size() < 2) continue;
                    double sum = 0.0; int cntSeeded = 0; int cntUnseeded = 0;
                    for (NodeId n : nds) {
                        if (n > numNodes) continue;
                        if (n == 0) { ++cntSeeded; /* 接地节点视为已锚定值=0 */ continue; }
                        if (seeded[n]) { sum += nodeV[n]; ++cntSeeded; }
                        else ++cntUnseeded;
                    }
                    if (cntSeeded == 0 || cntUnseeded == 0) continue;
                    double mean = sum / double(cntSeeded);
                    for (NodeId n : nds) {
                        if (n == 0 || n > numNodes) continue;
                        if (!seeded[n]) {
                            nodeV[n] = mean;
                            seeded[n] = 1;
                            changed = true;
                        }
                    }
                }
                if (!changed) break;
            }
        }
    };

    // gmin homotopy 用对数（几何）调度：gmin 跨 ~10 个数量级，线性调度会在
    // 倒数第二步到最后一步之间产生数量级跳变，导致非线性器件雅可比剧烈变化、
    // Newton 不收敛。使用 log-spaced sweep 使每步的雅可比变化平滑。
    std::vector<double> gminSched;
    if(hasNonlinear && opts.gmin.gminSteps>0){
        const double gStart = std::max(opts.gmin.gminStart, opts.gmin.gmin);
        const double gEnd   = std::max(opts.gmin.gmin, 1e-300);
        const double logStart = std::log(gStart);
        const double logEnd   = std::log(gEnd);
        const uint32_t N = opts.gmin.gminSteps;
        // 共 N+1 个点：从 gStart（含）到 gEnd（含）
        for(uint32_t s=0;s<=N;++s){
            double t = double(s)/double(N);
            gminSched.push_back(std::exp(logStart*(1.0-t) + logEnd*t));
        }
    } else {
        gminSched.push_back(opts.gmin.gmin);
    }

    bool anyConvergedEver = false;
    std::vector<double> bestNodeV = nodeV;          // 跨源步/gmin 步最近一次收敛解
    double bestGmin = opts.gmin.gmin;  // H2: 初始化为 target gmin（非收敛时 polish 用 target）
    double lastConvergedScale = 0.0;

    for (size_t si = 0; si < vsSched.size(); ++si) {
        double scale = vsSched[si];
        if (si == 0) {
            initVoltagesForScale(scale);
            bestNodeV = nodeV;
        } else {
            // warm start：保留上一源步的收敛解；不重置 nodeV
            nodeV = bestNodeV;
        }
        if (dcopVerbose() && vsSched.size() > 1)
            std::fprintf(stderr,
                "[dc] ## source step %zu/%zu  vsScale=%.4f ##\n",
                si+1, vsSched.size(), scale);

        bool stepConverged = false;
        // P3 post-A1：warm-skip gmin.
        //   - si==0 (冷启动)：用完整 gminSched，从 gminStart 一路下沉到 gmin。
        //   - si>=1：上一源步已收敛到目标 gmin (bestGmin)，warm-start nodeV
        //     已经离当前 ε 的真解很近；先尝试只在目标 gmin 上做单点 Newton，
        //     收敛则跳过整个 gmin sweep；不收敛再回退到完整 gminSched 重试。
        //   该优化把 InverterChain10 这种"每源步重复 gmin sweep"的累计 iter
        //   从 N_src × N_gmin × N_newton 降到 N_src × N_newton（fast path），
        //   失败时退化为原行为，零正确性损失。
        std::vector<double> gminSchedLocal;
        bool warmSkipPath = (si > 0 && anyConvergedEver);
        if (warmSkipPath) {
            gminSchedLocal.push_back(opts.gmin.gmin);
        } else {
            gminSchedLocal = gminSched;
        }

        auto runGminSweep = [&](const std::vector<double>& sched) -> bool {
            bool stepConv = false;
            for (size_t gi = 0; gi < sched.size(); ++gi) {
                DcOpOptions o = opts;
                o.gmin.gmin = sched[gi];
                o.vsScale = scale;
                // M1: gmin 变化时清 OSDI 器件 eval cache（避免 stale Jacobian 跨 gmin 步）
                if (gi > 0) {
                    for (const auto& d : devices)
                        if (auto* o2 = dynamic_cast<OsdiModel*>(d.get()))
                            o2->invalidateEvalCache();
                }
                if (dcopVerbose())
                    std::fprintf(stderr,
                        "[dc] === gmin step %zu/%zu  gmin=%.3e maxIter=%u vsScale=%.3g ===\n",
                        gi+1, sched.size(), o.gmin.gmin, o.maxIterations, scale);
                nodeV = bestNodeV;
                bool floorAccept = false;
                bool conv = newtonSolve(numNodes, devices, nodeV, o, hasNonlinear,
                                        r.iterations, r.floorAcceptsInner, bench, &floorAccept);
                if (dcopVerbose())
                    std::fprintf(stderr,
                        "[dc] gmin step %zu/%zu  converged=%d floor=%d totalIters=%u\n",
                        gi+1, sched.size(), conv?1:0, floorAccept?1:0, r.iterations);
                if (conv) {
                    bestNodeV = nodeV;
                    bestGmin  = o.gmin.gmin;
                    anyConvergedEver = true;
                    stepConv = true;
                    // H3: floor-accept 仍设 lastConvergedScale（保持兼容），
                    // 但记录 floorAcceptOuter 供调用方判断
                    lastConvergedScale = scale;
                } else {
                    if (dcopVerbose())
                        std::fprintf(stderr,
                            "[dc] gmin floor reached at gmin=%.3e (last converged gmin=%.3e); "
                            "accepting best-converged OP\n",
                            o.gmin.gmin, bestGmin);
                    nodeV = bestNodeV;
                    if (anyConvergedEver) r.floorAcceptOuter = true;
                    break;
                }
            }
            return stepConv;
        };

        stepConverged = runGminSweep(gminSchedLocal);
        if (!stepConverged && warmSkipPath) {
            // warm-skip 失败，退回完整 gmin sweep。
            if (dcopVerbose())
                std::fprintf(stderr,
                    "[dc] warm-skip gmin failed at vsScale=%.4f, falling back to full sweep\n",
                    scale);
            stepConverged = runGminSweep(gminSched);
        }

        if (!stepConverged) {
            // 当前源步从头就没收敛过：放弃后续源步，退回到最佳已收敛点。
            if (dcopVerbose() && vsSched.size() > 1)
                std::fprintf(stderr,
                    "[dc] source step %zu/%zu (vsScale=%.4f) did not converge; "
                    "stopping source stepping\n",
                    si+1, vsSched.size(), scale);
            nodeV = bestNodeV;
            break;
        }
    }
    // 最终收敛标志：必须在 vsScale=1.0 处真正收敛过；如果源步只收敛到中间 ε
    // 而没走到 ε=1.0，则视为未达目标偏置。
    bool reachedTarget = anyConvergedEver && std::fabs(lastConvergedScale - 1.0) < 1e-9;
    bool converged = reachedTarget || (anyConvergedEver && vsSched.size() == 1 &&
                                       std::fabs(vsSched[0] - opts.vsScale) < 1e-9);

    r.converged=converged;
    if(!converged && hasNonlinear) r.diags.warn({},"DC: did not converge");

    {
        // P2-11：DC 提取阶段把支路电流改为"在收敛点 nodeV_final 处通过 KCL 重新求和"
        // 提取，而不再依赖 augmented Newton 的 dx[br] 读数。
        //
        // 节点电压保留原"再走一步 Newton"的 polish（nodeV + dx）。这一步对强非线性
        // 器件 (BSIM4) 的下游 HB-NL warm start 有实质意义：Newton 主循环的停止
        // 准则只看 maxDelta（节点电压相对变化），并不强制 F[node] = 0；最后的 +dx
        // 半步把 KCL 残差吸收进 nodeV，让 HB warm start 拿到的工作点更准确。
        // 实测移除该 polish 会导致 HbNonlinear.Bsim4CommonSourceConverges 不收敛。
        //
        // 支路电流的"KCL 提取"则按下式做：
        //   设 V* = nodeV + dx 为最终节点电压。
        //   在 V* 处重新 assemble，得到 F*（不含 VS 支路电流贡献的 KCL 残差）。
        //   令 M (numNodes × numVS) 为 VS-节点关联矩阵：
        //     M[n1-1][k]=+1（VS_k 正端在 n1≠0 时），M[n2-1][k]=-1（n2≠0 时）。
        //   物理 KCL 闭合：F* + M·I_VS = 0 ⇒ M·I_VS = -F*。
        //   numVS ≤ numNodes 时为超定，用法方程 (M^T M)·I_VS = M^T(-F*) 解出。
        //
        // 与原 -dx[br] 在解析上等价（augmented Newton 也在做同一闭合），但显式
        // KCL 求和让数值过程不依赖于"再走一步"的 dx[node] 分配，对单 VS-节点
        // 退化情形 I_VS = -F*[n1-1] 也直观可读。
        DcOpOptions oFinal = opts; oFinal.gmin.gmin = bestGmin;
        oFinal.vsScale = opts.vsScale;  // polish 在 target vsScale (默认 1.0) 处
        nodeV = bestNodeV;              // 保证 polish 输入是最佳已收敛点
        SparseMatrix J; Vector F; std::vector<uint32_t> vsOff;
        assemble(numNodes,devices,nodeV,oFinal,J,F,vsOff);
        KluSolver solver;
        std::vector<double> nodeVFinal = nodeV;
        if(solver.factorize(J)){
            if (bench) bench->klu_factor_ms += solver.factorMs();
            Vector negF(F.size()); for(size_t k=0;k<F.size();++k) negF[k]=-F[k];
            Vector dx; solver.solve(negF,dx);
            if (bench) bench->klu_solve_ms += solver.solveMs();

            // V2-γ C3-bis 修复：polish step 原来是裸一步 Newton (nodeV+dx)，
            // 既无 dvmax 限幅也无下降检查。在 Newton 多解陷阱拓扑
            // (高对称 N≥3 BSIM4 阵列) 下，homotopy 末段残差地板接受的 V[n4]~0.8V
            // 经裸 polish 半步被推到 1.25V (drain>VDD 非物理)。这里复用 Newton
            // 主循环同款 dvmax clamp + 简化 backtracking（只接受 |F| 不变差的步）。
            // 对已收敛良好的工作点，alpha=1.0 一步到位，行为不变；
            // 对发散方向，回退到原 bestNodeV，避免污染 HB warm start。
            double fOld=0; for(double fv:F) fOld+=fv*fv; fOld=std::sqrt(fOld);
            double alpha = 1.0;
            std::vector<double> newNodeV(numNodes+1, 0.0);
            double fBest = fOld;
            std::vector<double> vBest = nodeV;   // 退路：原 bestNodeV
            bool accept = false;
            for (int bt = 0; bt < 12; ++bt) {
                for (uint32_t i = 0; i < numNodes; ++i) {
                    double dv = alpha * dx[i];
                    if (hasNonlinear && std::fabs(dv) > opts.dvmax)
                        dv = opts.dvmax * (dv > 0 ? 1.0 : -1.0);
                    newNodeV[i+1] = nodeV[i+1] + dv;
                }
                SparseMatrix J2; Vector F2; std::vector<uint32_t> vsOff2;
                assemble(numNodes, devices, newNodeV, oFinal, J2, F2, vsOff2);
                double fNew = 0; for (double fv : F2) fNew += fv*fv;
                fNew = std::sqrt(fNew);
                if (fNew <= fOld * (1.0 + 1e-12)) {  // H1: 近严格下降（仅允许浮点噪声）
                    // 接受此步（含等价 residual：fNew≈fOld 也接受，保留 polish 半步语义）
                    vBest = newNodeV;
                    fBest = fNew;
                    accept = true;
                    break;
                }
                alpha *= 0.5;
            }
            if (accept) {
                nodeVFinal = vBest;
            } else {
                // line search 完全失败：方向非下降，保留原 bestNodeV 作为 polish 输出，
                // 不强行推进（避免非物理跳变）。下游 HB warm start 拿到的是
                // homotopy 末段收敛点，仍然合法。
                // fBest 仍 == fOld，无需更新。
            }
            (void)fBest;  // 调试占位，未来可用 dcopVerbose() 打印
        }
        r.nodeVoltages = nodeVFinal;

        const uint32_t numVS = static_cast<uint32_t>(vsOff.size());
        r.branchCurrents.assign(numVS,0.0);
        if(numVS>0 && numNodes>0){
            // 在 polish 后的 V* 上重新 assemble，得到 F*（此处不再求 dx，仅用 F）。
            SparseMatrix Jstar; Vector Fstar; std::vector<uint32_t> vsOffStar;
            assemble(numNodes,devices,nodeVFinal,oFinal,Jstar,Fstar,vsOffStar);
            // 收集 VS 设备索引（按出现顺序与 vsOff 对齐）
            std::vector<uint32_t> vsIdx;
            vsIdx.reserve(numVS);
            for(uint32_t i=0;i<devices.size();++i)
                if(dynamic_cast<VoltageSource*>(devices[i].get())) vsIdx.push_back(i);
            // 节点 → 该节点上 VS 列贡献 (k, ±1) 列表（M 的稀疏行视图）
            std::vector<std::vector<std::pair<uint32_t,double>>> nodeToVS(numNodes);
            for(uint32_t k=0;k<numVS && k<vsIdx.size();++k){
                const auto& nds = devices[vsIdx[k]]->nodes();
                uint32_t n1 = nds.size()>0?nds[0]:0;
                uint32_t n2 = nds.size()>1?nds[1]:0;
                if(n1!=0) nodeToVS[n1-1].push_back({k, +1.0});
                if(n2!=0) nodeToVS[n2-1].push_back({k, -1.0});
            }
            // 直接累加 A = M^T M (numVS × numVS), rhs = M^T (-F*)
            std::vector<double> A(static_cast<size_t>(numVS)*numVS, 0.0);
            std::vector<double> rhs(numVS, 0.0);
            for(uint32_t i=0;i<numNodes;++i){
                const auto& cols = nodeToVS[i];
                if(cols.empty()) continue;
                double bi = -Fstar[i];
                for(auto& [k,mik] : cols){
                    rhs[k] += mik * bi;
                    for(auto& [l,mil] : cols)
                        A[static_cast<size_t>(k)*numVS + l] += mik * mil;
                }
            }
            // 小规模稠密 Gauss 消元（部分主元）求解 A·x = rhs（numVS 通常 < 10）
            std::vector<double> aug(static_cast<size_t>(numVS)*(numVS+1), 0.0);
            for(uint32_t i=0;i<numVS;++i){
                for(uint32_t j=0;j<numVS;++j) aug[static_cast<size_t>(i)*(numVS+1)+j] = A[static_cast<size_t>(i)*numVS+j];
                aug[static_cast<size_t>(i)*(numVS+1)+numVS] = rhs[i];
            }
            bool ok = true;
            for(uint32_t i=0;i<numVS && ok;++i){
                uint32_t piv = i;
                double pivAbs = std::fabs(aug[static_cast<size_t>(i)*(numVS+1)+i]);
                for(uint32_t rr=i+1;rr<numVS;++rr){
                    double v = std::fabs(aug[static_cast<size_t>(rr)*(numVS+1)+i]);
                    if(v>pivAbs){pivAbs=v; piv=rr;}
                }
                if(pivAbs < 1e-300){ ok=false; break; }
                if(piv!=i){
                    for(uint32_t j=i;j<=numVS;++j)
                        std::swap(aug[static_cast<size_t>(i)*(numVS+1)+j],
                                  aug[static_cast<size_t>(piv)*(numVS+1)+j]);
                }
                double diag = aug[static_cast<size_t>(i)*(numVS+1)+i];
                for(uint32_t rr=i+1;rr<numVS;++rr){
                    double f = aug[static_cast<size_t>(rr)*(numVS+1)+i] / diag;
                    if(f==0.0) continue;
                    for(uint32_t j=i;j<=numVS;++j)
                        aug[static_cast<size_t>(rr)*(numVS+1)+j] -= f * aug[static_cast<size_t>(i)*(numVS+1)+j];
                }
            }
            if(ok){
                std::vector<double> x(numVS,0.0);
                for(int i=static_cast<int>(numVS)-1;i>=0;--i){
                    double s = aug[static_cast<size_t>(i)*(numVS+1)+numVS];
                    for(uint32_t j=i+1;j<numVS;++j)
                        s -= aug[static_cast<size_t>(i)*(numVS+1)+j] * x[j];
                    x[i] = s / aug[static_cast<size_t>(i)*(numVS+1)+i];
                }
                // 符号约定：原代码 r.branchCurrents[k] = -dx[br]（VS+ 端流出的电流为正）。
                // LSQ 解 x[k] 是"流入 n1 的支路电流"，与 dx[br] 同号，故仍取负输出。
                for(uint32_t k=0;k<numVS;++k) r.branchCurrents[k] = -x[k];
            }
        }
    }
    if (bench) {
        bench->wall_ms       = tWall.elapsedMs();
        bench->newton_iter   = r.iterations;
        bench->peak_rss_mb   = currentRssMb();
    }
    return r;
}

} // namespace rfsim
