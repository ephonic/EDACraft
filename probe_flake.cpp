// probe_flake.cpp — diagnose KI-2 residual flake root cause
// After S2 MSVC switch, cross-CRT is fixed (EightFinger/Stack5 always PASS).
// But A3 / S1_InverterChainGrid still flake SEH 0xc0000005 when run
// back-to-back in same process. Goal: bisect
//   (a) N (instances per setup)              — proven: N up to 50 OK
//   (b) K (setup+teardown cycles)            — proven: K=20 x N=10 OK, K=8 x N=20 OK
//   (c) solveDcOp / solveHbNonlinear eval    — suspect; this mode E tests it
//
// Build: see src/CMakeLists.txt RFSIM_BUILD_PROBES; reuse probe_hb pattern.
// Run:   build\bin\probe_flake.exe [mode]
//   mode=N : ramp N 5..50 in one setup                (verified PASS)
//   mode=K : 20 cycles of N=10 setup+teardown         (verified PASS)
//   mode=K20: 8 cycles of N=20 setup+teardown         (verified PASS)
//   mode=E : build inverter-chain-like circuit N=20, run DC, tear down; repeat K=8

#include "rfsim.hpp"
#include "model/osdi/osdi_library.hpp"
#include "model/osdi/osdi_client.hpp"
#include "model/osdi_model.hpp"
#include "model/builtin_devices.hpp"
#include "solver/dc_op.hpp"
#include "solver/hb_nonlinear.hpp"
#include <cstdio>
#include <string>
#include <vector>
#include <crtdbg.h>

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#include <dbghelp.h>
#pragma comment(lib, "dbghelp.lib")
#pragma comment(lib, "psapi.lib")

// Vectored exception handler: dump faulting address + module on first-chance
// AV so we can see whether the crash is inside bsim4.dll or in host code.
static LONG WINAPI vehDump(PEXCEPTION_POINTERS ep) {
    if (ep->ExceptionRecord->ExceptionCode == 0xc0000005) {
        void* addr = ep->ExceptionRecord->ExceptionAddress;
        HMODULE mod = nullptr;
        char modPath[MAX_PATH] = {0};
        DWORD64 modBase = 0;
        if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCSTR)addr, &mod) && mod) {
            GetModuleFileNameA(mod, modPath, sizeof(modPath));
            MODULEINFO mi{};
            GetModuleInformation(GetCurrentProcess(), mod, &mi, sizeof(mi));
            modBase = (DWORD64)mi.lpBaseOfDll;
        }
        DWORD64 offset = (DWORD64)addr - modBase;
        fprintf(stderr, "[VEH] AV at addr=%p mod=%s  modBase=%llx  offset=0x%llx\n",
                addr, modPath[0] ? modPath : "(unknown)",
                (unsigned long long)modBase, (unsigned long long)offset);
        fprintf(stderr, "[VEH] access=%s target=%p\n",
                ep->ExceptionRecord->ExceptionInformation[0] ? "WRITE" : "READ",
                (void*)ep->ExceptionRecord->ExceptionInformation[1]);
        // Dump call stack via StackWalk (best-effort, no symbols needed)
        CONTEXT ctx = *ep->ContextRecord;
        STACKFRAME64 sf{}; sf.AddrPC.Offset = ctx.Rip; sf.AddrPC.Mode = AddrModeFlat;
        sf.AddrStack.Offset = ctx.Rsp; sf.AddrStack.Mode = AddrModeFlat;
        sf.AddrFrame.Offset = ctx.Rbp; sf.AddrFrame.Mode = AddrModeFlat;
        HANDLE h = GetCurrentThread();
        int frame = 0;
        while (frame < 12 && StackWalk64(IMAGE_FILE_MACHINE_AMD64, GetCurrentProcess(),
                                          h, &sf, &ctx, nullptr,
                                          SymFunctionTableAccess64, SymGetModuleBase64,
                                          nullptr)) {
            HMODULE m2 = nullptr;
            char mp2[MAX_PATH] = {0};
            DWORD64 mb2 = 0;
            if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                    (LPCSTR)sf.AddrPC.Offset, &m2) && m2) {
                GetModuleFileNameA(m2, mp2, sizeof(mp2));
                MODULEINFO mi2{};
                GetModuleInformation(GetCurrentProcess(), m2, &mi2, sizeof(mi2));
                mb2 = (DWORD64)mi2.lpBaseOfDll;
            }
            const char* slash = strrchr(mp2, '\\');
            // Resolve symbol name for this PC via SymFromAddr (PDB-backed)
            char symBuf[sizeof(SYMBOL_INFO) + 256] = {0};
            SYMBOL_INFO* si = reinterpret_cast<SYMBOL_INFO*>(symBuf);
            si->SizeOfStruct = sizeof(SYMBOL_INFO);
            si->MaxNameLen = 256;
            DWORD64 symDisp = 0;
            const char* symName = "";
            if (SymFromAddr(GetCurrentProcess(), sf.AddrPC.Offset, &symDisp, si)) {
                symName = si->Name;
            }
            // Image line info if available
            IMAGEHLP_LINE64 line{}; line.SizeOfStruct = sizeof(line);
            DWORD lineDisp = 0;
            const char* lineStr = "";
            char lineBuf[128] = {0};
            if (SymGetLineFromAddr64(GetCurrentProcess(), sf.AddrPC.Offset,
                                      &lineDisp, &line)) {
                const char* fileSlash = strrchr(line.FileName, '\\');
                snprintf(lineBuf, sizeof(lineBuf), " [%s:%u+%u]",
                         fileSlash ? fileSlash+1 : line.FileName,
                         line.LineNumber, lineDisp);
                lineStr = lineBuf;
            }
            fprintf(stderr, "[VEH] frame %d: pc=%p mod=%s offset=0x%llx sym=%s+0x%llx%s\n",
                    frame, (void*)sf.AddrPC.Offset, slash ? slash+1 : (mp2[0]?mp2:"?"),
                    (unsigned long long)(sf.AddrPC.Offset - mb2),
                    symName, (unsigned long long)symDisp, lineStr);
            ++frame;
        }
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
#endif

using namespace rfsim;

static std::shared_ptr<OsdiLibrary> loadBsim4() {
    const char* path = "models/bsim4.dll";
    auto lib = std::make_shared<OsdiLibrary>();
    std::string err;
    if (!lib->load(path, err)) {
        std::fprintf(stderr, "loadBsim4 failed: %s\n", err.c_str());
        return nullptr;
    }
    return lib;
}

int main(int argc, char** argv) {
    std::string mode = (argc > 1) ? argv[1] : "K20";
#ifdef _WIN32
    SymSetOptions(SYMOPT_DEFERRED_LOADS | SYMOPT_INCLUDE_32BIT_MODULES);
    SymInitialize(GetCurrentProcess(), nullptr, TRUE);
    AddVectoredExceptionHandler(0 /*last*/, &vehDump);
#endif
#ifdef _MSC_VER
    // Enable CRT debug heap; _CrtCheckMemory walks the heap each call and
    // aborts at the FIRST corruption with the offending allocation site.
    _CrtSetDbgFlag(_CRTDBG_ALLOC_MEM_DF | _CRTDBG_LEAK_CHECK_DF);
#endif
    auto lib = loadBsim4();
    if (!lib) return 2;
    if (lib->numDescriptors() < 1) { std::fprintf(stderr, "no desc\n"); return 2; }
    const OsdiDescriptor* desc = lib->descriptors();
    std::fprintf(stderr, "[probe] bsim4.dll loaded, mode=%s\n", mode.c_str());

    Diagnostics diags;

    // Shared model block (C3 pattern)
    auto modelBlock = std::make_shared<OsdiModelBlock>();
    modelBlock->descriptor = desc;

    if (mode == "N") {
        // Single setup, ramp N up
        for (int N = 5; N <= 50; N += 5) {
            std::vector<std::unique_ptr<OsdiClient>> clients;
            clients.reserve(N);
            bool ok = true;
            for (int i = 0; i < N; ++i) {
                auto c = std::make_unique<OsdiClient>();
                std::vector<NodeId> nodes{static_cast<NodeId>(2+i), 100, 0, 0};
                if (!c->init(lib, modelBlock, nodes, diags, {}, 300.15)) {
                    std::fprintf(stderr, "[probe.N] inst %d init failed at N=%d\n", i, N);
                    ok = false; break;
                }
                clients.push_back(std::move(c));
            }
            std::fprintf(stderr, "[probe.N] N=%d setup %s (clients alive=%zu)\n",
                         N, ok?"OK":"FAIL", clients.size());
            // clients destroyed here — free(instData_) K=N times
        }
        std::fprintf(stderr, "[probe.N] DONE\n");
        return 0;
    }

    if (mode == "K" || mode == "K20") {
        int N = (mode == "K20") ? 20 : 10;
        int K = (mode == "K20") ? 8 : 20;
        for (int k = 0; k < K; ++k) {
            std::vector<std::unique_ptr<OsdiClient>> clients;
            clients.reserve(N);
            bool ok = true;
            for (int i = 0; i < N; ++i) {
                auto c = std::make_unique<OsdiClient>();
                std::vector<NodeId> nodes{static_cast<NodeId>(2+i), 100, 0, 0};
                if (!c->init(lib, modelBlock, nodes, diags, {}, 300.15)) {
                    std::fprintf(stderr, "[probe.%s] cycle %d inst %d init failed\n",
                                 mode.c_str(), k, i);
                    ok = false; break;
                }
                clients.push_back(std::move(c));
            }
            std::fprintf(stderr, "[probe.%s] cycle %d/%d  N=%d setup %s (free'ing %zu instData...)\n",
                         mode.c_str(), k+1, K, N, ok?"OK":"FAIL", clients.size());
            // clients destroyed here
        }
        std::fprintf(stderr, "[probe.%s] DONE\n", mode.c_str());
        return 0;
    }

    if (mode == "E" || mode == "E20") {
        // mode E: full runInverterChainCheck replica — DC + HB then destroy, K cycles.
        // vdd=1.5, vin sine (DC 0.4 + AC 0.01 + 1MHz), Rd=5k per drain,
        // diode-connected chain N stages. Mirrors S1_InverterChainGrid exactly.
        int N = (mode == "E20") ? 20 : 15;
        int K = 4;
        auto sharedBlock = std::make_shared<OsdiModelBlock>();
        sharedBlock->descriptor = desc;

        for (int k = 0; k < K; ++k) {
            std::vector<std::unique_ptr<DeviceModel>> devs;
            devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.5));
            // vin: sine VS (matches buildInverterChain sineVS)
            auto vin = std::make_unique<VoltageSource>("vin", 2, 0, 0.4);
            Waveform wf; wf.type = Waveform::SIN;
            wf.vo = 0.4; wf.va = 0.01; wf.freq = 1e6;
            vin->setWaveform(wf);
            vin->setAcMag(Complex(0.01, 0.0));
            devs.push_back(std::move(vin));

            NodeId base = static_cast<NodeId>(3 + N);
            bool okInit = true;
            for (int i = 1; i <= N; ++i) {
                NodeId drain = static_cast<NodeId>(2 + i);
                devs.push_back(std::make_unique<Resistor>(
                    "rp" + std::to_string(i), 1, drain, 5e3));
                NodeId gate = (i == 1) ? static_cast<NodeId>(2)
                                        : static_cast<NodeId>(2 + (i - 1));
                auto m = std::make_unique<OsdiModel>(
                    "m" + std::to_string(i),
                    std::vector<NodeId>{drain, gate, 0, 0},
                    lib, desc,
                    std::vector<std::pair<std::string, ParamValue>>{
                        {"w", {ParamValue::Kind::Number, 1e-6, "", {}}},
                        {"l", {ParamValue::Kind::Number, 130e-9, "", {}}}
                    });
                m->useSharedModelBlock(sharedBlock);
                Diagnostics diags2;
                if (!m->initialize(diags2, base)) {
                    std::fprintf(stderr, "[probe.E] cycle %d inst %d init failed\n", k+1, i);
                    okInit = false; break;
                }
                devs.push_back(std::move(m));
#ifdef _MSC_VER
                if (!_CrtCheckMemory()) {
                    std::fprintf(stderr, "[probe.E] cycle %d inst %d HEAP CORRUPT after OsdiModel init\n", k+1, i);
                    std::abort();
                }
#endif
            }
            if (!okInit) continue;

            uint32_t numNodes = static_cast<uint32_t>(2 + N);
            DcOpOptions opt;
            opt.gmin.gmin = 1e-9;
            opt.gmin.gminStart = 1e-3;
            opt.gmin.gminSteps = 15;
            opt.maxIterations = 150;
            opt.dvmax = 0.2;
            opt.sourceStepCount = 6;
#ifdef _MSC_VER
            if (!_CrtCheckMemory()) {
                std::fprintf(stderr, "[probe.E] cycle %d  HEAP CORRUPT just before solveDcOp\n", k+1);
                std::abort();
            }
#endif
            auto dc = solveDcOp(numNodes, devs, opt);
#ifdef _MSC_VER
            if (!_CrtCheckMemory()) {
                std::fprintf(stderr, "[probe.E] cycle %d  HEAP CORRUPT right after solveDcOp\n", k+1);
                std::abort();
            }
#endif
            std::fprintf(stderr,
                "[probe.E] cycle %d/%d  N=%d  DC %s  iters=%u\n",
                k+1, K, N, dc.converged ? "CONV" : "FAIL", dc.iterations);
            if (!dc.converged) continue;

            // HB-NL phase (1 harmonic; matches runInverterChainCheck)
            HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
            HbNlOptions hopts;
            hopts.gmin.gmin = 1e-9;
            hopts.dvmax = 0.5;
            hopts.maxIter = 50;
            // Diagnostic toggles (via env): RFSIM_PROBE_NO_WARM=1 disables
            // AC warm-start (added in S1) to isolate whether warm-start path
            // triggers the AV.
            const char* noWarm = std::getenv("RFSIM_PROBE_NO_WARM");
            if (noWarm && std::string(noWarm) == "1") {
                hopts.acWarmStart = false;
                std::fprintf(stderr, "[probe.E] cycle %d  AC warm-start DISABLED\n", k+1);
            }
            std::vector<double> initV = dc.nodeVoltages;
            auto hb = solveHbNonlinear(numNodes, devs, cfg, &initV, hopts);
            std::fprintf(stderr,
                "[probe.E] cycle %d/%d  N=%d  HB %s\n",
                k+1, K, N, hb.converged ? "CONV" : "FAIL");
            // devs destroyed here
        }
        std::fprintf(stderr, "[probe.E] DONE\n");
        return 0;
    }

    std::fprintf(stderr, "unknown mode: %s (use N | K | K20 | E | E20)\n", mode.c_str());
    return 1;
}
