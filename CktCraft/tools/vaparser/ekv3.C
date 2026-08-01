#include <Xyce_config.h>
#include <N_DEV_DeviceOptions.h>
#include <N_DEV_ExternData.h>
#include <N_DEV_MatrixLoadData.h>
#include <N_DEV_SolverState.h>
#include <N_DEV_Message.h>
#include <N_ERH_ErrorMgr.h>
#include <N_LAS_Matrix.h>
#include <N_LAS_Vector.h>
#include <N_UTL_FeatureTest.h>
#include <N_UTL_Math.h>
#include <N_ANP_NoiseData.h>
#include "ekv3.h"

using std::max;
namespace Xyce {
namespace Device {
namespace ADMS_Device {
void Traits::loadInstanceParameters(ParametricData<ADMS_Device::Instance> &p)
{
p.addPar("L", 1.00000000e-05, &ADMS_Device::Instance::L)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("W", 1.00000000e-05, &ADMS_Device::Instance::W)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NF", 1.00000000e+00, &ADMS_Device::Instance::NF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("M", 1.00000000e+00, &ADMS_Device::Instance::M)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AD", 0.00000000e+00, &ADMS_Device::Instance::AD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AS", 0.00000000e+00, &ADMS_Device::Instance::AS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PD", 0.00000000e+00, &ADMS_Device::Instance::PD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PS", 0.00000000e+00, &ADMS_Device::Instance::PS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("SA", 0.00000000e+00, &ADMS_Device::Instance::SA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("SB", 0.00000000e+00, &ADMS_Device::Instance::SB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("SD", 0.00000000e+00, &ADMS_Device::Instance::SD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
}
void Traits::loadModelParameters(ParametricData<ADMS_Device::Model> &p)
{

p.addPar("SIGN", 1.00000000e+00, &ADMS_Device::Model::SIGN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TG", -1.00000000e+00, &ADMS_Device::Model::TG)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TNOM", 2.70000000e+01, &ADMS_Device::Model::TNOM)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("SCALE", 1.00000000e+00, &ADMS_Device::Model::SCALE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("QOFF", 0.00000000e+00, &ADMS_Device::Model::QOFF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XL", 0.00000000e+00, &ADMS_Device::Model::XL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XW", 0.00000000e+00, &ADMS_Device::Model::XW)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NQS_NOI", 1.00000000e+00, &ADMS_Device::Model::NQS_NOI)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TH_NOI", 0.00000000e+00, &ADMS_Device::Model::TH_NOI)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("INFO_LEVEL", 0.00000000e+00, &ADMS_Device::Model::INFO_LEVEL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AVTO", 0.00000000e+00, &ADMS_Device::Model::AVTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AGAMMA", 0.00000000e+00, &ADMS_Device::Model::AGAMMA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AKP", 0.00000000e+00, &ADMS_Device::Model::AKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("COX", 1.20000000e-02, &ADMS_Device::Model::COX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XJ", 2.00000000e-08, &ADMS_Device::Model::XJ)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VTO", 3.00000000e-01, &ADMS_Device::Model::VTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PHIF", 4.50000000e-01, &ADMS_Device::Model::PHIF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("GAMMA", 3.00000000e-01, &ADMS_Device::Model::GAMMA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("GAMMAG", 4.10000000e+00, &ADMS_Device::Model::GAMMAG)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("N0", 1.00000000e+00, &ADMS_Device::Model::N0)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VBI", 0.00000000e+00, &ADMS_Device::Model::VBI)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AQMA", 5.00000000e-01, &ADMS_Device::Model::AQMA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AQMI", 4.00000000e-01, &ADMS_Device::Model::AQMI)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("ETAQM", 7.50000000e-01, &ADMS_Device::Model::ETAQM)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KP", 5.00000000e-04, &ADMS_Device::Model::KP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("E0", 1.00000000e+10, &ADMS_Device::Model::E0)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("E1", 3.10000000e+08, &ADMS_Device::Model::E1)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("ETA", 5.00000000e-01, &ADMS_Device::Model::ETA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("ZC", 1.00000000e-06, &ADMS_Device::Model::ZC)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("THC", 0.00000000e+00, &ADMS_Device::Model::THC)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LA", 1.00000000e+00, &ADMS_Device::Model::LA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LB", 1.00000000e+00, &ADMS_Device::Model::LB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KA", 0.00000000e+00, &ADMS_Device::Model::KA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KB", 0.00000000e+00, &ADMS_Device::Model::KB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WKP1", 1.00000000e-06, &ADMS_Device::Model::WKP1)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WKP2", 0.00000000e+00, &ADMS_Device::Model::WKP2)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WKP3", 1.00000000e+00, &ADMS_Device::Model::WKP3)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DL", -1.00000000e-08, &ADMS_Device::Model::DL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DLC", 0.00000000e+00, &ADMS_Device::Model::DLC)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DW", -1.00000000e-08, &ADMS_Device::Model::DW)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DWC", 0.00000000e+00, &ADMS_Device::Model::DWC)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LDW", 0.00000000e+00, &ADMS_Device::Model::LDW)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WDL", 0.00000000e+00, &ADMS_Device::Model::WDL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LL", 0.00000000e+00, &ADMS_Device::Model::LL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LLN", 1.00000000e+00, &ADMS_Device::Model::LLN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AVT", 0.00000000e+00, &ADMS_Device::Model::AVT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LVT", 1.00000000e+00, &ADMS_Device::Model::LVT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WVT", 1.00000000e+00, &ADMS_Device::Model::WVT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AGAM", 0.00000000e+00, &ADMS_Device::Model::AGAM)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LGAM", 1.00000000e+00, &ADMS_Device::Model::LGAM)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WGAM", 1.00000000e+00, &ADMS_Device::Model::WGAM)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NFVTA", 0.00000000e+00, &ADMS_Device::Model::NFVTA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NFVTB", 1.00000000e+04, &ADMS_Device::Model::NFVTB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("UCRIT", 5.00000000e+06, &ADMS_Device::Model::UCRIT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LAMBDA", 5.00000000e-01, &ADMS_Device::Model::LAMBDA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DELTA", 2.00000000e+00, &ADMS_Device::Model::DELTA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("ACLM", 8.30000000e-01, &ADMS_Device::Model::ACLM)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LR", 5.00000000e-08, &ADMS_Device::Model::LR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("QLR", 5.00000000e-04, &ADMS_Device::Model::QLR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NLR", 1.00000000e-02, &ADMS_Device::Model::NLR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("FLR", 0.00000000e+00, &ADMS_Device::Model::FLR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LETA0", 0.00000000e+00, &ADMS_Device::Model::LETA0)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LETA", 5.00000000e-01, &ADMS_Device::Model::LETA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LETA2", 0.00000000e+00, &ADMS_Device::Model::LETA2)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WETA", 2.00000000e-01, &ADMS_Device::Model::WETA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NCS", 1.00000000e+00, &ADMS_Device::Model::NCS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("ETAD", 1.00000000e+00, &ADMS_Device::Model::ETAD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("SIGMAD", 1.00000000e+00, &ADMS_Device::Model::SIGMAD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WR", 9.00000000e-08, &ADMS_Device::Model::WR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("QWR", 3.00000000e-04, &ADMS_Device::Model::QWR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NWR", 5.00000000e-03, &ADMS_Device::Model::NWR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("FPROUT", 1.00000000e+06, &ADMS_Device::Model::FPROUT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PDITS", 0.00000000e+00, &ADMS_Device::Model::PDITS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PDITSL", 0.00000000e+00, &ADMS_Device::Model::PDITSL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PDITSD", 1.00000000e+00, &ADMS_Device::Model::PDITSD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DDITS", 3.00000000e-01, &ADMS_Device::Model::DDITS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("IBA", 0.00000000e+00, &ADMS_Device::Model::IBA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("IBB", 3.00000000e+08, &ADMS_Device::Model::IBB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("IBN", 1.00000000e+00, &ADMS_Device::Model::IBN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XB", 3.10000000e+00, &ADMS_Device::Model::XB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("EB", 2.90000000e+10, &ADMS_Device::Model::EB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KG", 0.00000000e+00, &ADMS_Device::Model::KG)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LOVIG", 2.00000000e-08, &ADMS_Device::Model::LOVIG)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AGIDL", 0.00000000e+00, &ADMS_Device::Model::AGIDL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("BGIDL", 2.30000000e+09, &ADMS_Device::Model::BGIDL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CGIDL", 5.00000000e-01, &ADMS_Device::Model::CGIDL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("EGIDL", 8.00000000e-01, &ADMS_Device::Model::EGIDL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KF", 0.00000000e+00, &ADMS_Device::Model::KF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("AF", 1.00000000e+00, &ADMS_Device::Model::AF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("EF", 2.00000000e+00, &ADMS_Device::Model::EF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KGFN", 0.00000000e+00, &ADMS_Device::Model::KGFN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LQWR", 0.00000000e+00, &ADMS_Device::Model::LQWR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LNWR", 0.00000000e+00, &ADMS_Device::Model::LNWR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LWR", 0.00000000e+00, &ADMS_Device::Model::LWR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LDPHIEDGE", 0.00000000e+00, &ADMS_Device::Model::LDPHIEDGE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WQLR", 0.00000000e+00, &ADMS_Device::Model::WQLR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WNLR", 0.00000000e+00, &ADMS_Device::Model::WNLR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WLR", 0.00000000e+00, &ADMS_Device::Model::WLR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WUCRIT", 0.00000000e+00, &ADMS_Device::Model::WUCRIT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WLAMBDA", 0.00000000e+00, &ADMS_Device::Model::WLAMBDA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WETAD", 0.00000000e+00, &ADMS_Device::Model::WETAD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WE0", 0.00000000e+00, &ADMS_Device::Model::WE0)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WE1", 0.00000000e+00, &ADMS_Device::Model::WE1)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WRLX", 0.00000000e+00, &ADMS_Device::Model::WRLX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WUCEX", 0.00000000e+00, &ADMS_Device::Model::WUCEX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WDPHIEDGE", 0.00000000e+00, &ADMS_Device::Model::WDPHIEDGE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WLDPHIEDGE", 0.00000000e+00, &ADMS_Device::Model::WLDPHIEDGE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WLDGAMMAEDGE", 0.00000000e+00, &ADMS_Device::Model::WLDGAMMAEDGE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WEDGE", 0.00000000e+00, &ADMS_Device::Model::WEDGE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DGAMMAEDGE", 0.00000000e+00, &ADMS_Device::Model::DGAMMAEDGE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DPHIEDGE", 0.00000000e+00, &ADMS_Device::Model::DPHIEDGE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("SAREF", 0.00000000e+00, &ADMS_Device::Model::SAREF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("SBREF", 0.00000000e+00, &ADMS_Device::Model::SBREF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WLOD", 0.00000000e+00, &ADMS_Device::Model::WLOD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KKP", 0.00000000e+00, &ADMS_Device::Model::KKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LKKP", 0.00000000e+00, &ADMS_Device::Model::LKKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WKKP", 0.00000000e+00, &ADMS_Device::Model::WKKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PKKP", 0.00000000e+00, &ADMS_Device::Model::PKKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TKKP", 0.00000000e+00, &ADMS_Device::Model::TKKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LLODKKP", 1.00000000e+00, &ADMS_Device::Model::LLODKKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WLODKKP", 1.00000000e+00, &ADMS_Device::Model::WLODKKP)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KVTO", 0.00000000e+00, &ADMS_Device::Model::KVTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LKVTO", 0.00000000e+00, &ADMS_Device::Model::LKVTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WKVTO", 0.00000000e+00, &ADMS_Device::Model::WKVTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PKVTO", 0.00000000e+00, &ADMS_Device::Model::PKVTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LLODKVTO", 1.00000000e+00, &ADMS_Device::Model::LLODKVTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("WLODKVTO", 1.00000000e+00, &ADMS_Device::Model::WLODKVTO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KGAMMA", 0.00000000e+00, &ADMS_Device::Model::KGAMMA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LODKGAMMA", 1.00000000e+00, &ADMS_Device::Model::LODKGAMMA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KETAD", 0.00000000e+00, &ADMS_Device::Model::KETAD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LODKETAD", 1.00000000e+00, &ADMS_Device::Model::LODKETAD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KUCRIT", 0.00000000e+00, &ADMS_Device::Model::KUCRIT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TETA", -9.00000000e-04, &ADMS_Device::Model::TETA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TLAMBDA", 0.00000000e+00, &ADMS_Device::Model::TLAMBDA)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TCV", 6.00000000e-04, &ADMS_Device::Model::TCV)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("BEX", -1.50000000e+00, &ADMS_Device::Model::BEX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("UCEX", 1.50000000e+00, &ADMS_Device::Model::UCEX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TE0EX", 5.00000000e-01, &ADMS_Device::Model::TE0EX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TE1EX", 5.00000000e-01, &ADMS_Device::Model::TE1EX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("IBBT", 8.00000000e-04, &ADMS_Device::Model::IBBT)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TCVL", 0.00000000e+00, &ADMS_Device::Model::TCVL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TCVW", 0.00000000e+00, &ADMS_Device::Model::TCVW)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TCVWL", 0.00000000e+00, &ADMS_Device::Model::TCVWL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("GAMMAOV", 1.60000000e+00, &ADMS_Device::Model::GAMMAOV)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("GAMMAGOV", 1.00000000e+01, &ADMS_Device::Model::GAMMAGOV)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VFBOV", 0.00000000e+00, &ADMS_Device::Model::VFBOV)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LOV", 2.00000000e-08, &ADMS_Device::Model::LOV)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VOV", 1.00000000e+00, &ADMS_Device::Model::VOV)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CGSO", 0.00000000e+00, &ADMS_Device::Model::CGSO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CGDO", 0.00000000e+00, &ADMS_Device::Model::CGDO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CGBO", 0.00000000e+00, &ADMS_Device::Model::CGBO)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KJF", 0.00000000e+00, &ADMS_Device::Model::KJF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CJF", 0.00000000e+00, &ADMS_Device::Model::CJF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VFR", 0.00000000e+00, &ADMS_Device::Model::VFR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("DFR", 1.00000000e-03, &ADMS_Device::Model::DFR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("HDIF", 0.00000000e+00, &ADMS_Device::Model::HDIF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RSH", 0.00000000e+00, &ADMS_Device::Model::RSH)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("LDIF", 0.00000000e+00, &ADMS_Device::Model::LDIF)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RS", 0.00000000e+00, &ADMS_Device::Model::RS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RD", 0.00000000e+00, &ADMS_Device::Model::RD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RLX", -1.00000000e+00, &ADMS_Device::Model::RLX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RSX", -1.00000000e+00, &ADMS_Device::Model::RSX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RDX", -1.00000000e+00, &ADMS_Device::Model::RDX)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TR", 0.00000000e+00, &ADMS_Device::Model::TR)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TR2", 0.00000000e+00, &ADMS_Device::Model::TR2)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("GMIN", 0.00000000e+00, &ADMS_Device::Model::GMIN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJS", 1.00000000e+00, &ADMS_Device::Model::NJS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XJBVS", 0.00000000e+00, &ADMS_Device::Model::XJBVS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("BVS", 1.00000000e+01, &ADMS_Device::Model::BVS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JSS", 0.00000000e+00, &ADMS_Device::Model::JSS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JSSWS", 0.00000000e+00, &ADMS_Device::Model::JSSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JSSWGS", 0.00000000e+00, &ADMS_Device::Model::JSSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JTSS", 0.00000000e+00, &ADMS_Device::Model::JTSS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JTSSWS", 0.00000000e+00, &ADMS_Device::Model::JTSSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JTSSWGS", 0.00000000e+00, &ADMS_Device::Model::JTSSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJTSS", 1.00000000e+00, &ADMS_Device::Model::NJTSS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJTSSWS", 1.00000000e+00, &ADMS_Device::Model::NJTSSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJTSSWGS", 1.00000000e+00, &ADMS_Device::Model::NJTSSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VTSS", 0.00000000e+00, &ADMS_Device::Model::VTSS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VTSSWS", 0.00000000e+00, &ADMS_Device::Model::VTSSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VTSSWGS", 0.00000000e+00, &ADMS_Device::Model::VTSSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CJS", 0.00000000e+00, &ADMS_Device::Model::CJS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CJSWS", 0.00000000e+00, &ADMS_Device::Model::CJSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CJSWGS", 0.00000000e+00, &ADMS_Device::Model::CJSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PBS", 8.00000000e-01, &ADMS_Device::Model::PBS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PBSWS", 6.00000000e-01, &ADMS_Device::Model::PBSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PBSWGS", 6.00000000e-01, &ADMS_Device::Model::PBSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("MJS", 9.00000000e-01, &ADMS_Device::Model::MJS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("MJSWS", 7.00000000e-01, &ADMS_Device::Model::MJSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("MJSWGS", 7.00000000e-01, &ADMS_Device::Model::MJSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTIS", 3.00000000e+00, &ADMS_Device::Model::XTIS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTSS", 0.00000000e+00, &ADMS_Device::Model::XTSS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTSSWS", 0.00000000e+00, &ADMS_Device::Model::XTSSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTSSWGS", 0.00000000e+00, &ADMS_Device::Model::XTSSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TNJTSS", 0.00000000e+00, &ADMS_Device::Model::TNJTSS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TNJTSSWS", 0.00000000e+00, &ADMS_Device::Model::TNJTSSWS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TNJTSSWGS", 0.00000000e+00, &ADMS_Device::Model::TNJTSSWGS)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TCJ", 0.00000000e+00, &ADMS_Device::Model::TCJ)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TCJSW", 0.00000000e+00, &ADMS_Device::Model::TCJSW)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TCJSWG", 0.00000000e+00, &ADMS_Device::Model::TCJSWG)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TPB", 0.00000000e+00, &ADMS_Device::Model::TPB)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TPBSW", 0.00000000e+00, &ADMS_Device::Model::TPBSW)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TPBSWG", 0.00000000e+00, &ADMS_Device::Model::TPBSWG)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJD", 1.00000000e+00, &ADMS_Device::Model::NJD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XJBVD", 0.00000000e+00, &ADMS_Device::Model::XJBVD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("BVD", 1.00000000e+01, &ADMS_Device::Model::BVD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JSD", 0.00000000e+00, &ADMS_Device::Model::JSD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JSSWD", 0.00000000e+00, &ADMS_Device::Model::JSSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JSSWGD", 0.00000000e+00, &ADMS_Device::Model::JSSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JTSD", 0.00000000e+00, &ADMS_Device::Model::JTSD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JTSSWD", 0.00000000e+00, &ADMS_Device::Model::JTSSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("JTSSWGD", 0.00000000e+00, &ADMS_Device::Model::JTSSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJTSD", 1.00000000e+00, &ADMS_Device::Model::NJTSD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJTSSWD", 1.00000000e+00, &ADMS_Device::Model::NJTSSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("NJTSSWGD", 1.00000000e+00, &ADMS_Device::Model::NJTSSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VTSD", 0.00000000e+00, &ADMS_Device::Model::VTSD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VTSSWD", 0.00000000e+00, &ADMS_Device::Model::VTSSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("VTSSWGD", 0.00000000e+00, &ADMS_Device::Model::VTSSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CJD", 0.00000000e+00, &ADMS_Device::Model::CJD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CJSWD", 0.00000000e+00, &ADMS_Device::Model::CJSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("CJSWGD", 0.00000000e+00, &ADMS_Device::Model::CJSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PBD", 8.00000000e-01, &ADMS_Device::Model::PBD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PBSWD", 6.00000000e-01, &ADMS_Device::Model::PBSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("PBSWGD", 6.00000000e-01, &ADMS_Device::Model::PBSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("MJD", 9.00000000e-01, &ADMS_Device::Model::MJD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("MJSWD", 7.00000000e-01, &ADMS_Device::Model::MJSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("MJSWGD", 7.00000000e-01, &ADMS_Device::Model::MJSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTID", 3.00000000e+00, &ADMS_Device::Model::XTID)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTSD", 0.00000000e+00, &ADMS_Device::Model::XTSD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTSSWD", 0.00000000e+00, &ADMS_Device::Model::XTSSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("XTSSWGD", 0.00000000e+00, &ADMS_Device::Model::XTSSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TNJTSD", 0.00000000e+00, &ADMS_Device::Model::TNJTSD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TNJTSSWD", 0.00000000e+00, &ADMS_Device::Model::TNJTSSWD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TNJTSSWGD", 0.00000000e+00, &ADMS_Device::Model::TNJTSSWGD)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RGSH", 3.00000000e+00, &ADMS_Device::Model::RGSH)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("GC", 1.00000000e+00, &ADMS_Device::Model::GC)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("KRGL1", 0.00000000e+00, &ADMS_Device::Model::KRGL1)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RDSBSH", 1.00000000e+03, &ADMS_Device::Model::RDSBSH)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RBWSH", 3.00000000e-03, &ADMS_Device::Model::RBWSH)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RBN", 0.00000000e+00, &ADMS_Device::Model::RBN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RSBWSH", 1.00000000e-03, &ADMS_Device::Model::RSBWSH)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RSBN", 0.00000000e+00, &ADMS_Device::Model::RSBN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RDBWSH", 1.00000000e-03, &ADMS_Device::Model::RDBWSH)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RDBN", 0.00000000e+00, &ADMS_Device::Model::RDBN)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("RINGTYPE", 1.00000000e+00, &ADMS_Device::Model::RINGTYPE)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
}

std::vector< std::vector<int> > Instance::jacStamp;
bool Instance::processParams ()
{
temp = getDeviceOptions().temp.getImmutableValue<double>();
updateTemperature(temp);
return true;
}

Instance::Instance(
const Configuration & configuration,
const InstanceBlock & IB,
Model &model,
const FactoryBlock &  factory_block)
: DeviceInstance(IB, configuration.getInstanceParameters(), factory_block),
 model_(model),
d(0),
g(0),
s(0),
b(0),
di(0),
si(0),
noi(0),
L(0.0),
W(0.0),
NF(0.0),
M(0.0),
AD(0.0),
AS(0.0),
PD(0.0),
PS(0.0),
SA(0.0),
SB(0.0),
SD(0.0),
AMatOffset_r0c0(0),
AMatOffset_r0c4(0),
AMatOffset_r1c1(0),
AMatOffset_r1c3(0),
AMatOffset_r1c4(0),
AMatOffset_r1c5(0),
AMatOffset_r1c6(0),
AMatOffset_r2c2(0),
AMatOffset_r2c5(0),
AMatOffset_r3c1(0),
AMatOffset_r3c3(0),
AMatOffset_r3c4(0),
AMatOffset_r3c5(0),
AMatOffset_r4c0(0),
AMatOffset_r4c1(0),
AMatOffset_r4c3(0),
AMatOffset_r4c4(0),
AMatOffset_r4c5(0),
AMatOffset_r4c6(0),
AMatOffset_r5c1(0),
AMatOffset_r5c2(0),
AMatOffset_r5c3(0),
AMatOffset_r5c4(0),
AMatOffset_r5c5(0),
AMatOffset_r5c6(0),
AMatOffset_r6c6(0),
li_state_0(0),
li_state_1(0),
li_state_2(0),
li_state_3(0),
li_state_4(0),
li_state_5(0),
li_state_6(0),
li_state_7(0),
li_state_8(0),
li_state_9(0),
li_state_10(0),
li_state_11(0),
li_state_12(0),
li_state_13(0),
li_state_14(0),
li_state_15(0),
li_state_16(0),
li_state_17(0),
li_state_18(0),
li_state_19(0),
li_state_20(0),
li_state_21(0),
li_state_22(0),
li_state_23(0),
f_matPosition_r0c0(0),
f_matPosition_r0c4(0),
f_matPosition_r1c1(0),
f_matPosition_r1c3(0),
f_matPosition_r1c4(0),
f_matPosition_r1c5(0),
f_matPosition_r1c6(0),
f_matPosition_r2c2(0),
f_matPosition_r2c5(0),
f_matPosition_r3c1(0),
f_matPosition_r3c3(0),
f_matPosition_r3c4(0),
f_matPosition_r3c5(0),
f_matPosition_r4c0(0),
f_matPosition_r4c1(0),
f_matPosition_r4c3(0),
f_matPosition_r4c4(0),
f_matPosition_r4c5(0),
f_matPosition_r4c6(0),
f_matPosition_r5c1(0),
f_matPosition_r5c2(0),
f_matPosition_r5c3(0),
f_matPosition_r5c4(0),
f_matPosition_r5c5(0),
f_matPosition_r5c6(0),
f_matPosition_r6c6(0),
q_matPosition_r0c0(0),
q_matPosition_r0c4(0),
q_matPosition_r1c1(0),
q_matPosition_r1c3(0),
q_matPosition_r1c4(0),
q_matPosition_r1c5(0),
q_matPosition_r1c6(0),
q_matPosition_r2c2(0),
q_matPosition_r2c5(0),
q_matPosition_r3c1(0),
q_matPosition_r3c3(0),
q_matPosition_r3c4(0),
q_matPosition_r3c5(0),
q_matPosition_r4c0(0),
q_matPosition_r4c1(0),
q_matPosition_r4c3(0),
q_matPosition_r4c4(0),
q_matPosition_r4c5(0),
q_matPosition_r4c6(0),
q_matPosition_r5c1(0),
q_matPosition_r5c2(0),
q_matPosition_r5c3(0),
q_matPosition_r5c4(0),
q_matPosition_r5c5(0),
q_matPosition_r5c6(0),
q_matPosition_r6c6(0)
{
numIntVars = 3;
numExtVars = 4;
numStateVars = 24;
setNumStoreVars(0);
setNumBranchDataVars(0);
numBranchDataVarsIfAllocated = 0;
if(jacStamp.empty()) {
jacStamp.resize(7);
jacStamp[0].resize(2);
jacStamp[0][0] = 0;
jacStamp[0][1] = 4;
jacStamp[1].resize(5);
jacStamp[1][0] = 1;
jacStamp[1][1] = 3;
jacStamp[1][2] = 4;
jacStamp[1][3] = 5;
jacStamp[1][4] = 6;
jacStamp[2].resize(2);
jacStamp[2][0] = 2;
jacStamp[2][1] = 5;
jacStamp[3].resize(4);
jacStamp[3][0] = 1;
jacStamp[3][1] = 3;
jacStamp[3][2] = 4;
jacStamp[3][3] = 5;
jacStamp[4].resize(6);
jacStamp[4][0] = 0;
jacStamp[4][1] = 1;
jacStamp[4][2] = 3;
jacStamp[4][3] = 4;
jacStamp[4][4] = 5;
jacStamp[4][5] = 6;
jacStamp[5].resize(6);
jacStamp[5][0] = 1;
jacStamp[5][1] = 2;
jacStamp[5][2] = 3;
jacStamp[5][3] = 4;
jacStamp[5][4] = 5;
jacStamp[5][5] = 6;
jacStamp[6].resize(1);
jacStamp[6][0] = 6;
} // end of if(jacStamp.empty()) 
setDefaultParams();
setParams(IB.params);
processParams();
}

Instance::~Instance()
{
}

void Instance::registerLIDs( const std::vector<int> & intLIDVecRef,
 const std::vector<int> & extLIDVecRef )
{
intLIDVec = intLIDVecRef;
extLIDVec = extLIDVecRef;
d =  extLIDVec[0];
g =  extLIDVec[1];
s =  extLIDVec[2];
b =  extLIDVec[3];
di =  intLIDVec[0];
si =  intLIDVec[1];
noi =  intLIDVec[2];
}

void Instance::loadNodeSymbols(Util::SymbolTable &symbol_table) const
{
        addInternalNode(symbol_table, di, getName(), "di");
        addInternalNode(symbol_table, si, getName(), "si");
        addInternalNode(symbol_table, noi, getName(), "noi");
}

void Instance::registerStoreLIDs( const std::vector<int> & stoLIDVecRef )
{
}

void Instance::registerStateLIDs( const std::vector<int> & staLIDVecRef )
{
}

void Instance::registerBranchDataLIDs(const std::vector<int> & branchLIDVecRef)
{
}

const std::vector< std::vector<int> > & Instance::jacobianStamp() const
{
return jacStamp;
}

void Instance::registerJacLIDs( const std::vector< std::vector<int> > & jacLIDVec )
{
DeviceInstance::registerJacLIDs( jacLIDVec );
AMatOffset_r0c0 = jacLIDVec[0][0];
AMatOffset_r0c4 = jacLIDVec[0][1];
AMatOffset_r1c1 = jacLIDVec[1][0];
AMatOffset_r1c3 = jacLIDVec[1][1];
AMatOffset_r1c4 = jacLIDVec[1][2];
AMatOffset_r1c5 = jacLIDVec[1][3];
AMatOffset_r1c6 = jacLIDVec[1][4];
AMatOffset_r2c2 = jacLIDVec[2][0];
AMatOffset_r2c5 = jacLIDVec[2][1];
AMatOffset_r3c1 = jacLIDVec[3][0];
AMatOffset_r3c3 = jacLIDVec[3][1];
AMatOffset_r3c4 = jacLIDVec[3][2];
AMatOffset_r3c5 = jacLIDVec[3][3];
AMatOffset_r4c0 = jacLIDVec[4][0];
AMatOffset_r4c1 = jacLIDVec[4][1];
AMatOffset_r4c3 = jacLIDVec[4][2];
AMatOffset_r4c4 = jacLIDVec[4][3];
AMatOffset_r4c5 = jacLIDVec[4][4];
AMatOffset_r4c6 = jacLIDVec[4][5];
AMatOffset_r5c1 = jacLIDVec[5][0];
AMatOffset_r5c2 = jacLIDVec[5][1];
AMatOffset_r5c3 = jacLIDVec[5][2];
AMatOffset_r5c4 = jacLIDVec[5][3];
AMatOffset_r5c5 = jacLIDVec[5][4];
AMatOffset_r5c6 = jacLIDVec[5][5];
AMatOffset_r6c6 = jacLIDVec[6][0];
}

void Instance::setupPointers () 
{
#ifndef Xyce_NONPOINTER_MATRIX_LOAD
Linear::Matrix & dFdx = *(extData.dFdxMatrixPtr);
Linear::Matrix & dQdx = *(extData.dQdxMatrixPtr);
f_matPosition_r0c0 = &(dFdx[d][AMatOffset_r0c0]);
f_matPosition_r0c4 = &(dFdx[d][AMatOffset_r0c4]);
f_matPosition_r1c1 = &(dFdx[g][AMatOffset_r1c1]);
f_matPosition_r1c3 = &(dFdx[g][AMatOffset_r1c3]);
f_matPosition_r1c4 = &(dFdx[g][AMatOffset_r1c4]);
f_matPosition_r1c5 = &(dFdx[g][AMatOffset_r1c5]);
f_matPosition_r1c6 = &(dFdx[g][AMatOffset_r1c6]);
f_matPosition_r2c2 = &(dFdx[s][AMatOffset_r2c2]);
f_matPosition_r2c5 = &(dFdx[s][AMatOffset_r2c5]);
f_matPosition_r3c1 = &(dFdx[b][AMatOffset_r3c1]);
f_matPosition_r3c3 = &(dFdx[b][AMatOffset_r3c3]);
f_matPosition_r3c4 = &(dFdx[b][AMatOffset_r3c4]);
f_matPosition_r3c5 = &(dFdx[b][AMatOffset_r3c5]);
f_matPosition_r4c0 = &(dFdx[di][AMatOffset_r4c0]);
f_matPosition_r4c1 = &(dFdx[di][AMatOffset_r4c1]);
f_matPosition_r4c3 = &(dFdx[di][AMatOffset_r4c3]);
f_matPosition_r4c4 = &(dFdx[di][AMatOffset_r4c4]);
f_matPosition_r4c5 = &(dFdx[di][AMatOffset_r4c5]);
f_matPosition_r4c6 = &(dFdx[di][AMatOffset_r4c6]);
f_matPosition_r5c1 = &(dFdx[si][AMatOffset_r5c1]);
f_matPosition_r5c2 = &(dFdx[si][AMatOffset_r5c2]);
f_matPosition_r5c3 = &(dFdx[si][AMatOffset_r5c3]);
f_matPosition_r5c4 = &(dFdx[si][AMatOffset_r5c4]);
f_matPosition_r5c5 = &(dFdx[si][AMatOffset_r5c5]);
f_matPosition_r5c6 = &(dFdx[si][AMatOffset_r5c6]);
f_matPosition_r6c6 = &(dFdx[noi][AMatOffset_r6c6]);
q_matPosition_r0c0 = &(dQdx[d][AMatOffset_r0c0]);
q_matPosition_r0c4 = &(dQdx[d][AMatOffset_r0c4]);
q_matPosition_r1c1 = &(dQdx[g][AMatOffset_r1c1]);
q_matPosition_r1c3 = &(dQdx[g][AMatOffset_r1c3]);
q_matPosition_r1c4 = &(dQdx[g][AMatOffset_r1c4]);
q_matPosition_r1c5 = &(dQdx[g][AMatOffset_r1c5]);
q_matPosition_r1c6 = &(dQdx[g][AMatOffset_r1c6]);
q_matPosition_r2c2 = &(dQdx[s][AMatOffset_r2c2]);
q_matPosition_r2c5 = &(dQdx[s][AMatOffset_r2c5]);
q_matPosition_r3c1 = &(dQdx[b][AMatOffset_r3c1]);
q_matPosition_r3c3 = &(dQdx[b][AMatOffset_r3c3]);
q_matPosition_r3c4 = &(dQdx[b][AMatOffset_r3c4]);
q_matPosition_r3c5 = &(dQdx[b][AMatOffset_r3c5]);
q_matPosition_r4c0 = &(dQdx[di][AMatOffset_r4c0]);
q_matPosition_r4c1 = &(dQdx[di][AMatOffset_r4c1]);
q_matPosition_r4c3 = &(dQdx[di][AMatOffset_r4c3]);
q_matPosition_r4c4 = &(dQdx[di][AMatOffset_r4c4]);
q_matPosition_r4c5 = &(dQdx[di][AMatOffset_r4c5]);
q_matPosition_r4c6 = &(dQdx[di][AMatOffset_r4c6]);
q_matPosition_r5c1 = &(dQdx[si][AMatOffset_r5c1]);
q_matPosition_r5c2 = &(dQdx[si][AMatOffset_r5c2]);
q_matPosition_r5c3 = &(dQdx[si][AMatOffset_r5c3]);
q_matPosition_r5c4 = &(dQdx[si][AMatOffset_r5c4]);
q_matPosition_r5c5 = &(dQdx[si][AMatOffset_r5c5]);
q_matPosition_r5c6 = &(dQdx[si][AMatOffset_r5c6]);
q_matPosition_r6c6 = &(dQdx[noi][AMatOffset_r6c6]);
#endif
}

bool Instance::updateTemperature (const double & temp_tmp)
{
}

bool Instance::updateIntermediateVars ()
{
updateIntermediateVars_RHS();
updateIntermediateVars_Jac();
return true;
}

bool Instance::updateIntermediateVars_RHS()
{
    double DdtExp0, DdtExp1, DdtExp2, DdtExp3, DdtExp4, DdtExp5, DdtExp6, DdtExp7, DdtExp8, DdtExp9, DdtExp10, DdtExp11, DdtExp12, DdtExp13, DdtExp14, DdtExp15, DdtExp16, DdtExp17, DdtExp18, DdtExp19, DdtExp20, DdtExp21, DdtExp22, DdtExp23;
    double DdtAns0, DdtAns1, DdtAns2, DdtAns3, DdtAns4, DdtAns5, DdtAns6, DdtAns7, DdtAns8, DdtAns9, DdtAns10, DdtAns11, DdtAns12, DdtAns13, DdtAns14, DdtAns15, DdtAns16, DdtAns17, DdtAns18, DdtAns19, DdtAns20, DdtAns21, DdtAns22, DdtAns23;
    double myadms_t1, myadms_t2;
    double NF_M;
    double SIGN_NF;
    double SIGN_M;
    double SIGN_NF_M;
    double TSI;
    double TOX;
    double TOX2;
    double LC;
    double QON;
    double hdif;
    double ldif;
    double l;
    double WF;
    double w;
    double Leff;
    double Weff;
    double Leffc;
    double Weffc;
    double WeffNF;
    double WLeff;
    double awl;
    double VTO_a;
    double GAMMA_a;
    double KP_a;
    double DVTLONG;
    double DVTWIDE;
    double DVTNF;
    double DGAMMALONG;
    double DGAMMAWIDE;
    double LR_g;
    double QLR_g;
    double NLR_g;
    double E0_g;
    double E1_g;
    double UCRIT_g;
    double LAMBDA_g;
    double ETAD_g;
    double TCV_g;
    double UCEX_g;
    double WR_g;
    double QWR_g;
    double NWR_g;
    double DVTRSCE;
    double GAMMA_RSCE;
    double DPHIF_RSCE;
    double DVTINWE;
    double GAMMA_INWE;
    double kpl;
    double kpw;
    double VTO_DEV;
    double GAMMA_DEV;
    double PHIF_DEV;
    double KP_DEV;
    double UCRIT_DEV;
    double ETAD_DEV;
    double CHSHL;
    double CHSHW;
    double NUV;
    double UT;
    double UT2;
    double UT3;
    double sqrtUT;
    double thermocrasia;
    double tnom;
    double dT;
    double dT2;
    double rT;
    double lnrT;
    double VTO_DEV_t;
    double KP_DEV_t;
    double ETA_t;
    double E0_gt;
    double E1_gt;
    double UCRIT_DEV_t;
    double LAMBDA_gt;
    double IBB_t;
    double eg_nom;
    double eg_thermo;
    double temp_arg_S;
    double temp_arg_D;
    double temp_arg2;
    double PHIF_DEV_t;
    double phif;
    double sqrtphif;
    double vto;
    double gamma_b_dev;
    double gamma_b_dev2;
    double gamma_g;
    double gamma_g2;
    double dpd;
    double gamma_ov;
    double gamma_g_ov;
    double vfb_ov;
    double gamma_ov2;
    double ucrit_o_UT;
    double xb;
    double ub;
    double ev;
    double tmp;
    double ev1;
    double nq0;
    double aqma;
    double axetaqm2_3;
    double inv_dqmip1;
    double dpsi0;
    double DPSI0;
    double phi;
    double sqrtphi;
    double nul;
    double vbi;
    double sqrtvbi;
    double chsh_l;
    double chsh_w;
    double one_w;
    double vfb;
    double Q0;
    double Q0OV;
    double VS;
    double VD;
    double VG;
    double d_gt_s_flag;
    double vd;
    double vs;
    double vg;
    double chsh_a1;
    double chsh_a2;
    double chsh_a3;
    double gamma_b_chsh;
    double gamma_b_chsh2;
    double gamma_b_eff;
    double gamma_b_eff2;
    double vg_p;
    double vg_p_chsh;
    double vg_p_chsh_pd;
    double psi_po;
    double psi_p;
    double sqrt_psi_p;
    double vp;
    double nv;
    double deltapsis;
    double qs;
    double qs2;
    double if_;
    double sif2;
    double sif;
    double g_clm;
    double e_clm;
    double e_clm2;
    double mdm2;
    double e_clmxmdm2_2;
    double vdsat;
    double vdssat;
    double vdp;
    double deltal;
    double qdp;
    double qdp2;
    double irp;
    double sirp2;
    double sirp;
    double qsqdp;
    double qs_qdp;
    double powqs_qdp2;
    double qsqdpp1;
    double powqsqdpp1_2;
    double i;
    double nq;
    double v_o;
    double qr1;
    double qbo;
    double dpsiv;
    double qS;
    double qD;
    double qG;
    double qI;
    double qB;
    double beta_coul;
    double nu;
    double gpnu;
    double eq;
    double eq1;
    double beta_nom;
    double beta_denom;
    double beta;
    double beta_clm_denom;
    double i0;
    double Ispec;
    double dits_factor;
    double QS;
    double QD;
    double QG;
    double QB;
    double IDS;
    double IDB;
    double Leff_o_LR;
    double one_lr;
    double Weff_o_WR;
    double one_wr;
    double tmp_vfb;
    double epsilon;
    double psi_p_tmp;
    double l0;
    double v_o_dibl;
    double v_o_dibl2;
    double dv_dibl;
    double exp_tmp;
    double vv;
    double z1;
    double z2;
    double ln_z1_;
    double e_clmx2;
    double e_clmp2;
    double e_clmx2xqs;
    double qsat;
    double qs_qsat;
    double qs_qsat2;
    double vdsat_tmp1;
    double vdsat_tmp11;
    double vdsat_tmp2;
    double dv_clm;
    double vdp_tmp1;
    double vdp_tmp2;
    double vdp_tmp3;
    double u_clm;
    double alpha_clm;
    double f_dits;
    double va_dits;
    double vdseff;
    double psi_p0;
    double psi_po0;
    double sqrt_psi_p0;
    double chsh_a10;
    double chsh_a20;
    double chsh_a30;
    double gamma_b_chsh0;
    double gamma_b_chsh02;
    double vg_p_chsh_pd0;
    double psi_sa_tmp;
    double sqrt_psi_sa;
    double z0;
    double zk;
    double v1_qg;
    double v2_qg;
    double k1;
    double k2;
    double k12;
    double k12_2;
    double k12_3;
    double i_sti;
    double inv_sa05l;
    double inv_sb05l;
    double inv_saref05l;
    double inv_sbref05l;
    double tmpl;
    double tmpw;
    double KKP_sti;
    double a_sti;
    double aref_sti;
    double kp_sti;
    double ucrit_sti;
    double KVTO_sti;
    double b_sti;
    double KKP_sti_t;
    double a_sti_t;
    double aref_sti_t;
    double kp_sti_t;
    double DVTSTI;
    double DGAMMASTI;
    double DETADSTI;
    double Ispec_edge;
    double Q0_edge;
    double dgamma_edge;
    double dphi_edge;
    double dvp_edge;
    double qs_edge;
    double qdp_edge;
    double ids_edge;
    double IDS_edge;
    double psi_p_edge;
    double sqrt_psi_p_edge;
    double nq_edge;
    double qsqdp_edge;
    double qs_qdp_edge;
    double powqs_qdp2_edge;
    double qsqdpp1_edge;
    double powqsqdpp1_2_edge;
    double qS_edge;
    double qD_edge;
    double qG_edge;
    double qI_edge;
    double qB_edge;
    double QS_edge;
    double QD_edge;
    double QG_edge;
    double QB_edge;
    double gamma_b_chsh_edge;
    double QSOV;
    double QDOV;
    double vgsov_p;
    double gamma_dep_sov;
    double gamma_acc_sov;
    double v0_sov;
    double a0_sov;
    double a1_sov;
    double a2_sov;
    double a3_sov;
    double v1_sov;
    double dpsigs0;
    double gamma_dep2_sov;
    double a4_sov;
    double v2_sov;
    double dpsigs;
    double v2b_sov;
    double v3_sov;
    double dpsiox_s;
    double vgdov_p;
    double gamma_dep_dov;
    double gamma_acc_dov;
    double v0_dov;
    double a0_dov;
    double a1_dov;
    double a2_dov;
    double a3_dov;
    double v1_dov;
    double dpsigd0;
    double gamma_dep2_dov;
    double a4_dov;
    double v2_dov;
    double dpsigd;
    double v2b_dov;
    double v3_dov;
    double dpsiox_d;
    double QSFR;
    double QDFR;
    double vgse;
    double vgde;
    double tmp1;
    double tmp2;
    double IGIDL;
    double IGISL;
    double v1_ig;
    double v2_ig;
    double psi_ox;
    double d_psi_dq;
    double psi_x;
    double s1_px;
    double p_tun;
    double igo;
    double nigc;
    double nigs;
    double nigd;
    double dq_dksi;
    double a_gc;
    double b_gc;
    double psi_oxr_ov_s;
    double psi_xr_ov_s;
    double p_tun_sov;
    double psi_oxr_ov_d;
    double psi_xr_ov_d;
    double p_tun_dov;
    double IGB;
    double IG;
    double IGD;
    double IGS;
    double IGDOV;
    double IGSOV;
    double xf;
    double xr;
    double OMEGA;
    double j;
    double omegaspec;
    double snidid;
    double snigig;
    double snibib;
    double snigid;
    double c_igid;
    double gn;
    double thermal;
    double gmg;
    double flicker;
    double snspec;
    double noise_ds1;
    double noise_ds2;
    double noise_g;
    double noise_b;
    double sig_shot;
    double sig_flicker;
    double as;
    double ad;
    double ps;
    double pd;
    double v_di_b;
    double is_d;
    double arg_d;
    double f_breakdown_d;
    double idb_tun;
    double v_si_b;
    double is_s;
    double arg_s;
    double f_breakdown_s;
    double isb_tun;
    double csb_d;
    double cssw_d;
    double csswg_d;
    double csb_s;
    double cssw_s;
    double csswg_s;
    double jss_t;
    double jssws_t;
    double jsswgs_t;
    double pbs_t;
    double pbsws_t;
    double pbswgs_t;
    double cjs_t;
    double cjsws_t;
    double cjswgs_t;
    double njtss_t;
    double njtssws_t;
    double njtsswgs_t;
    double jtss_t;
    double jtssws_t;
    double jtsswgs_t;
    double jsd_t;
    double jsswd_t;
    double jsswgd_t;
    double pbd_t;
    double pbswd_t;
    double pbswgd_t;
    double cjd_t;
    double cjswd_t;
    double cjswgd_t;
    double jtsd_t;
    double jtsswd_t;
    double jtsswgd_t;
    double njtsd_t;
    double njtsswd_t;
    double njtsswgd_t;
    double IDBJ;
    double ISBJ;
    double CSBJ;
    double CDBJ;
    double QDBJ;
    double QSBJ;
    double qsb_s;
    double qssw_s;
    double qsswg_s;
    double qsb_d;
    double qssw_d;
    double qsswg_d;
    double rs;
    double rd;
    double rg;
    double rb;
    double rdsb;
    double rsb;
    double rdb;
    double v_ib;
    double file;
    double file_info;
    double Vb = (extData.nextSolVectorRawPtr)[b];
    double Vd = (extData.nextSolVectorRawPtr)[d];
    double Vdi = (extData.nextSolVectorRawPtr)[di];
    double Vg = (extData.nextSolVectorRawPtr)[g];
    double Vnoi = (extData.nextSolVectorRawPtr)[noi];
    double Vs = (extData.nextSolVectorRawPtr)[s];
    double Vsi = (extData.nextSolVectorRawPtr)[si];
    fRHS[0] = 0.;
    fRHS[1] = 0.;
    fRHS[2] = 0.;
    fRHS[3] = 0.;
    fRHS[4] = 0.;
    fRHS[5] = 0.;
    fRHS[6] = 0.;
    qRHS[0] = 0.;
    qRHS[1] = 0.;
    qRHS[2] = 0.;
    qRHS[3] = 0.;
    qRHS[4] = 0.;
    qRHS[5] = 0.;
    qRHS[6] = 0.;
    QON = (1.0-model_.QOFF);
    TSI = (1.03594314E-10)/model_.COX;
    TOX = (34.53144E-12)/model_.COX;
    TOX2 = TOX*TOX;
    LC = sqrt(TSI*model_.XJ);
    hdif = model_.HDIF*model_.SCALE;
    ldif = model_.LDIF*model_.SCALE;
    NF_M = NF*M;
    SIGN_NF = model_.SIGN*NF;
    SIGN_M = model_.SIGN*M;
    SIGN_NF_M = model_.SIGN*NF_M;
    l = L*model_.SCALE+model_.XL;
    WF = W/NF;
    w = WF*model_.SCALE+model_.XW;
    Leff = (model_.LL==0.0)?l+model_.DL+model_.WDL/w : l+model_.DL+model_.WDL/w-model_.LL*exp(model_.LLN*log(1.0/l));
    Weff = w+model_.DW+model_.LDW/l;
    Leffc = Leff+model_.DLC;
    Weffc = Weff+model_.DWC;
    Leff = ((Leff)>(1.0e-9)?(Leff) : (1.0e-9));
    Weff = ((Weff)>(1.0e-9)?(Weff) : (1.0e-9));
    Leffc = ((Leffc)>(1.0e-9)?(Leffc) : (1.0e-9));
    Weffc = ((Weffc)>(1.0e-9)?(Weffc) : (1.0e-9));
    WeffNF = Weff*NF;
    WLeff = Weff*Leff;
    awl = 1.0E6/sqrt(WLeff);
    VTO_a = model_.VTO+model_.AVTO*awl;
    GAMMA_a = model_.GAMMA+model_.AGAMMA*awl;
    KP_a = model_.KP*(1.0+model_.AKP*awl);
    DVTLONG = (-model_.AVT)*(0.5*((log(Leff/model_.LVT))+(0.0)+sqrt(((log(Leff/model_.LVT))-(0.0))*((log(Leff/model_.LVT))-(0.0))+(1.0e-2))));
    DVTWIDE = (-model_.AVT)*(0.5*((log(Weff/model_.WVT))+(0.0)+sqrt(((log(Weff/model_.WVT))-(0.0))*((log(Weff/model_.WVT))-(0.0))+(1.0e-2))));
    DGAMMALONG = (-model_.AGAM)*(0.5*((log(Leff/model_.LGAM))+(0.0)+sqrt(((log(Leff/model_.LGAM))-(0.0))*((log(Leff/model_.LGAM))-(0.0))+(1.0e-2))));
    DGAMMAWIDE = (-model_.AGAM)*(0.5*((log(Weff/model_.WGAM))+(0.0)+sqrt(((log(Weff/model_.WGAM))-(0.0))*((log(Weff/model_.WGAM))-(0.0))+(1.0e-2))));
    DVTNF = model_.NFVTA*log10(((NF)-1)*model_.NFVTB+1);
    LR_g = model_.LR+model_.WLR/Weff;
    QLR_g = model_.QLR*(1.0+model_.WQLR/Weff);
    NLR_g = model_.NLR*(1.0+model_.WNLR/Weff);
    E0_g = model_.E0*(1.0+model_.WE0/Weff);
    E1_g = model_.E1*(1.0+model_.WE1/Weff);
    UCRIT_g = model_.UCRIT*(1.0+model_.WUCRIT/Weff);
    LAMBDA_g = model_.LAMBDA*(1.0+model_.WLAMBDA/Weff);
    ETAD_g = model_.ETAD*(1.0+model_.WETAD/Weff);
    TCV_g = model_.TCV+model_.TCVL/Leff+model_.TCVW/Weff+model_.TCVWL/WLeff;
    UCEX_g = model_.UCEX*(1.0+model_.WUCEX/Weff);
    WR_g = model_.WR+model_.LWR/Leff;
    QWR_g = model_.QWR*(1.0+model_.LQWR/Leff);
    NWR_g = model_.NWR*(1.0+model_.LNWR/Leff);
    Leff_o_LR = Leff/LR_g;
    if(Leff_o_LR>6.0){
    one_lr = 1.0;
    } else {
    one_lr = 1.0-exp((-Leff_o_LR)*Leff_o_LR);
    }
    DVTRSCE = 2.0*QLR_g*one_lr/(model_.COX*Leff_o_LR);
    GAMMA_RSCE = sqrt(1.0+2.0*NLR_g*one_lr/(model_.COX*Leff_o_LR));
    DPHIF_RSCE = (((1.3807E-23)*(model_.TNOM+273.15))/(1.602E-19))*model_.FLR*log(1.0+2.0*NLR_g*one_lr/(model_.COX*Leff_o_LR));
    Weff_o_WR = Weff/WR_g;
    if(Weff_o_WR>6.0){
    one_wr = 1.0;
    } else {
    one_wr = 1.0-exp((-Weff_o_WR)*Weff_o_WR);
    }
    DVTINWE = (-2.0)*QWR_g*one_wr/(model_.COX*Weff_o_WR);
    GAMMA_INWE = 1.0/sqrt(1.0+2.0*NWR_g*one_wr/(model_.COX*Weff_o_WR));
    if((model_.KA==0.0)&&(model_.KB==0.0)){
    kpl = 1.0;
    } else {
    kpl = 1.0/(1.0+(model_.KA*model_.LA/Leff)*(1.0-exp((-Leff)/model_.LA))+(model_.KB*model_.LB/Leff)*(1.0-exp((-Leff)/model_.LB)));
    }
    if(model_.WKP2==0.0){
    kpw = 1.0;
    } else {
    kpw = (log(Weff/model_.WKP1))/model_.WKP3;
    kpw = 1.0+model_.WKP2*exp((-kpw)*kpw);
    }
    if((SA>0)&&(SB>0)){
    i_sti = 0;
    if(NF==1){
    inv_sa05l = 1.0/(SA+0.5*l);
    inv_sb05l = 1.0/(SB+0.5*l);
    } else {
    if(NF>1){
    inv_sa05l = 0.0;
    inv_sb05l = 0.0;
    for(i_sti = 0; i_sti<NF; i_sti = i_sti+1){
    inv_sa05l = inv_sa05l+1.0/(SA+0.5*l+i_sti*(SD+l));
    inv_sb05l = inv_sb05l+1.0/(SB+0.5*l+i_sti*(SD+l));
    }
    inv_sa05l = inv_sa05l/NF;
    inv_sb05l = inv_sb05l/NF;
    } else {
    inv_sa05l = 1.0;
    inv_sb05l = 1.0;
    }
    }
    inv_saref05l = 1.0/(model_.SAREF+0.5*l);
    inv_sbref05l = 1.0/(model_.SBREF+0.5*l);
    tmpl = exp((-model_.LLODKKP)*log(l));
    tmpw = exp((-model_.WLODKKP)*log(w+model_.WLOD));
    KKP_sti = (1.0+model_.LKKP*tmpl+model_.WKKP*tmpw+model_.PKKP*tmpl*tmpw);
    a_sti = model_.KKP/KKP_sti*(inv_sa05l+inv_sb05l);
    aref_sti = model_.KKP/KKP_sti*(inv_saref05l+inv_sbref05l);
    kp_sti = (1.0+a_sti)/(1.0+aref_sti);
    ucrit_sti = (1.0+model_.KUCRIT*a_sti)/(1.0+model_.KUCRIT*aref_sti);
    tmpl = exp((-model_.LLODKVTO)*log(l));
    tmpw = exp((-model_.WLODKVTO)*log(w+model_.WLOD));
    KVTO_sti = 1.0+model_.LKVTO*tmpl+model_.WKVTO*tmpw+model_.PKVTO*tmpl*tmpw;
    b_sti = inv_sa05l+inv_sb05l-inv_saref05l-inv_sbref05l;
    DVTSTI = model_.KVTO/KVTO_sti*b_sti;
    DGAMMASTI = model_.KGAMMA/exp(model_.LODKGAMMA*log(KVTO_sti))*b_sti;
    DETADSTI = model_.KETAD/exp(model_.LODKETAD*log(KVTO_sti))*b_sti;
    } else {
    kp_sti = 1.0;
    ucrit_sti = 1.0;
    DVTSTI = 0.0;
    KKP_sti = 1.0;
    DGAMMASTI = 0.0;
    DETADSTI = 0.0;
    inv_sa05l = 1.0;
    inv_sb05l = 1.0;
    inv_saref05l = 1.0;
    inv_sbref05l = 1.0;
    }
    VTO_DEV = VTO_a+model_.SIGN*(DVTLONG+DVTWIDE+DVTRSCE+DVTINWE+DVTNF+DVTSTI);
    GAMMA_DEV = (GAMMA_a*GAMMA_RSCE*GAMMA_INWE)+DGAMMASTI+DGAMMALONG+DGAMMAWIDE;
    PHIF_DEV = model_.PHIF+DPHIF_RSCE;
    KP_DEV = KP_a*kpl*kpw*kp_sti;
    ETAD_DEV = ETAD_g+DETADSTI;
    UCRIT_DEV = UCRIT_g*ucrit_sti;
    CHSHL = model_.LETA0+(model_.LETA/Leff)+(model_.LETA2/(Leff*Leff));
    CHSHW = model_.WETA/Weff;
    NUV = model_.N0+model_.NCS*3.0*TOX*CHSHL;
    UT = 1.3807E-23 *  getDeviceOptions().temp.getImmutableValue<double>() / 1.602E-19;
    UT2 = UT*UT;
    UT3 = UT*UT2;
    sqrtUT = sqrt(UT);
    thermocrasia =  getDeviceOptions().temp.getImmutableValue<double>();
    tnom = model_.TNOM+273.15;
    dT = thermocrasia-tnom;
    dT2 = dT*dT;
    rT = thermocrasia/tnom;
    lnrT = log(rT);
    if((SA>0)&&(SB>0)){
    KKP_sti_t = KKP_sti*(1.0+model_.TKKP*(rT-1.0));
    a_sti_t = model_.KKP/KKP_sti_t*(inv_sa05l+inv_sb05l);
    aref_sti_t = model_.KKP/KKP_sti_t*(inv_saref05l+inv_sbref05l);
    kp_sti_t = (1.0+a_sti_t)/(1.0+aref_sti_t)/kp_sti;
    } else {
    kp_sti_t = 1.0;
    }
    VTO_DEV_t = model_.SIGN*(VTO_DEV-TCV_g*dT);
    KP_DEV_t = KP_DEV*exp(model_.BEX*lnrT)*kp_sti_t;
    ETA_t = model_.ETA+(model_.TETA*dT);
    E0_gt = E0_g*exp(model_.TE0EX*lnrT);
    E1_gt = E1_g*exp(model_.TE1EX*lnrT);
    UCRIT_DEV_t = UCRIT_DEV*exp(UCEX_g*lnrT);
    LAMBDA_gt = LAMBDA_g+model_.TLAMBDA*(rT-1.0);
    IBB_t = model_.IBB*(1.0+model_.IBBT*dT);
    eg_nom = 1.16-(7.02E-4*tnom*tnom)/(tnom+1108.0);
    eg_thermo = 1.16-(7.02E-4*thermocrasia*thermocrasia)/(thermocrasia+1108);
    temp_arg_S = exp((eg_nom/(((1.3807E-23)*(tnom))/(1.602E-19))-eg_thermo/UT+model_.XTIS*lnrT)/model_.NJS);
    temp_arg_D = exp((eg_nom/(((1.3807E-23)*(tnom))/(1.602E-19))-eg_thermo/UT+model_.XTID*lnrT)/model_.NJD);
    temp_arg2 = (-UT)*3.0*lnrT+(eg_thermo-eg_nom*rT);
    PHIF_DEV_t = (PHIF_DEV*rT)+(temp_arg2/2.0);
    phif = PHIF_DEV_t/UT;
    sqrtphif = sqrt(phif);
    vto = VTO_DEV_t/UT;
    gamma_b_dev = GAMMA_DEV/sqrtUT;
    gamma_b_dev2 = gamma_b_dev*gamma_b_dev;
    gamma_g = model_.GAMMAG/sqrtUT;
    gamma_g2 = gamma_g*gamma_g;
    dpd = (model_.TG!=0)?gamma_b_dev2/gamma_g2 : 0.0;
    gamma_ov = model_.GAMMAOV/sqrtUT;
    gamma_g_ov = model_.GAMMAGOV/sqrtUT;
    vfb_ov = model_.VFBOV/UT;
    gamma_ov2 = gamma_ov*gamma_ov;
    ucrit_o_UT = UCRIT_DEV_t/UT;
    xb = model_.XB/UT;
    ub = model_.EB*TOX/model_.XB;
    ev = UT/(E0_gt*TSI);
    tmp = E1_gt*TSI;
    ev1 = UT2/(tmp*tmp);
    nq0 = (model_.TG<0)?(1.0/(1.0+(dpd*2.0*(1.4142135623730950488016887242097)*sqrtphif/gamma_b_dev))+gamma_b_dev/(2.0*(1.4142135623730950488016887242097)*sqrtphif)) : 1.0+(gamma_b_dev/(2.0*(1.4142135623730950488016887242097)*sqrtphif));
    aqma = model_.AQMA*exp((0.33333333333333333333333333333333)*(log(model_.COX*model_.COX/UT)));
    axetaqm2_3 = aqma*exp((0.66666666666666666666666666666667)*log(model_.ETAQM));
    inv_dqmip1 = (0.33333333333333333333333333333333)*model_.AQMI*exp((0.66666666666666666666666666666667)*log(gamma_b_dev*model_.COX*0.5/(sqrtUT*phif)))*(2.0*model_.ETAQM*nq0*(1.4142135623730950488016887242097)*sqrtphif/gamma_b_dev-1.0);
    inv_dqmip1 = 1.0/(1.0+inv_dqmip1);
    dpsi0 = model_.AQMI*exp((0.66666666666666666666666666666667)*log(gamma_b_dev*model_.COX*(1.4142135623730950488016887242097)*sqrtphif));
    DPSI0 = dpsi0*UT;
    phi = phif*2.0+log(4.0*nq0*sqrtphif*(1.4142135623730950488016887242097)/gamma_b_dev)+dpsi0;
    sqrtphi = sqrt(phi);
    if(model_.VBI==0.0){
    nul = 3.0;
    vbi = phi+nul;
    } else {
    vbi = model_.VBI/UT;
    nul = vbi-phi;
    }
    sqrtvbi = sqrt(vbi);
    Q0 = (-Weffc)*NF*Leffc*model_.COX*UT*inv_dqmip1*(Weff-model_.WEDGE)/Weff;
    Q0OV = Weffc*NF*model_.LOV*model_.COX*UT*inv_dqmip1;
    VS = (Vsi - Vb);
    VD = (Vdi - Vb);
    VG = (Vg - Vb);
    if(model_.SIGN*VS>model_.SIGN*VD){
    d_gt_s_flag = (-1);
    } else {
    d_gt_s_flag = 1;
    }
    vd = model_.SIGN*0.5*((d_gt_s_flag+1)*VD+(1-d_gt_s_flag)*VS)/UT;
    vs = model_.SIGN*0.5*((d_gt_s_flag+1)*VS+(1-d_gt_s_flag)*VD)/UT;
    vg = model_.SIGN*VG/UT;
    chsh_l = CHSHL*TSI;
    chsh_w = CHSHW*TSI;
    one_w = 1.0+chsh_w;
    chsh_a1 = 1.0-chsh_l*(sqrt((0.5*((vbi+vs)+(0.0)+sqrt(((vbi+vs)-(0.0))*((vbi+vs)-(0.0))+(UT2)))))+sqrt((0.5*((vbi+vd)+(0.0)+sqrt(((vbi+vd)-(0.0))*((vbi+vd)-(0.0))+(UT2))))))/gamma_b_dev;
    chsh_a2 = chsh_a1+chsh_a1-1.0+(chsh_w+chsh_w)*sqrtphi/gamma_b_dev;
    chsh_a3 = one_w+dpd*chsh_a2;
    gamma_b_chsh = gamma_b_dev*chsh_a1/one_w;
    gamma_b_chsh2 = gamma_b_chsh*gamma_b_chsh;
    gamma_b_eff = gamma_b_dev*chsh_a1/chsh_a3;
    gamma_b_eff2 = gamma_b_eff*gamma_b_eff;
    chsh_a10 = 1.0-chsh_l*2.0*sqrt(vbi)/gamma_b_dev;
    chsh_a20 = chsh_a10+chsh_a10-1.0+(chsh_w+chsh_w)*sqrtphi/gamma_b_dev;
    chsh_a30 = one_w+dpd*chsh_a20;
    gamma_b_chsh0 = gamma_b_dev*chsh_a10/one_w;
    gamma_b_chsh02 = gamma_b_chsh0*gamma_b_chsh0;
    tmp_vfb = 1.0-(chsh_l+chsh_l)*sqrtvbi/gamma_b_dev+chsh_w*sqrtphi/gamma_b_dev;
    vfb = vto-phi*(one_w+dpd*tmp_vfb*tmp_vfb)-gamma_b_dev*(1.0-(chsh_l+chsh_l)*sqrtvbi/gamma_b_dev)*sqrtphi;
    vg_p = vg-vfb;
    vg_p_chsh = vg_p/one_w;
    vg_p_chsh_pd = vg_p/chsh_a3;
    vg_p_chsh_pd0 = vg_p/chsh_a30;
    tmp = vg_p_chsh*0.5-3.0*(1.0+gamma_b_chsh*(0.70710678118654752440084436210485));
    psi_po = tmp+sqrt(tmp*tmp+6.0*vg_p_chsh);
    tmp = vg_p_chsh*0.5-3.0*(1.0+gamma_b_chsh0*(0.70710678118654752440084436210485));
    psi_po0 = tmp+sqrt(tmp*tmp+6.0*vg_p_chsh);
    if(vg_p<0.0){
    tmp = (psi_po-vg_p_chsh)/gamma_b_chsh;
    psi_p = (-log(1.0-psi_po+tmp*tmp));
    tmp = (psi_po0-vg_p_chsh)/gamma_b_chsh0;
    psi_p0 = (-log(1.0-psi_po0+tmp*tmp));
    } else {
    epsilon = exp((-psi_po));
    psi_p_tmp = sqrt(vg_p_chsh_pd-1.0+epsilon+gamma_b_eff2*0.25)-gamma_b_eff*0.5;
    psi_p = psi_p_tmp*psi_p_tmp+1.0-epsilon;
    epsilon = exp((-psi_po0));
    psi_p_tmp = sqrt(vg_p_chsh_pd0-1.0+epsilon+gamma_b_chsh02*0.25)-gamma_b_chsh0*0.5;
    psi_p0 = psi_p_tmp*psi_p_tmp+1.0-epsilon;
    }
    sqrt_psi_p = sqrt((0.5*((psi_p)+(1.0E-4)+sqrt(((psi_p)-(1.0E-4))*((psi_p)-(1.0E-4))+(1.0E-2)))));
    sqrt_psi_p0 = sqrt((0.5*((psi_p0)+(1.0E-4)+sqrt(((psi_p0)-(1.0E-4))*((psi_p0)-(1.0E-4))+(1.0E-2)))));
    vp = psi_p-phi;
    nv = chsh_a3+gamma_b_dev*chsh_a1/(2.0*sqrt_psi_p);
    if(model_.ETAD==0.0){
    deltapsis = 0.0;
    } else {
    l0 = ETAD_DEV*TSI*sqrt(2.0*sqrtphi/gamma_b_dev);
    v_o_dibl = 4.0+40.0*l0/Leff;
    v_o_dibl2 = v_o_dibl*v_o_dibl;
    tmp = (0.5*((vs)+(vd)-sqrt(((vs)-(vd))*((vs)-(vd))+(v_o_dibl2))));
    dv_dibl = (0.5*((vp)+(tmp)-sqrt(((vp)-(tmp))*((vp)-(tmp))+(v_o_dibl2))));
    tmp = Leff/(l0+l0);
    if(tmp>70.0){
    deltapsis = 0.0;
    } else {
    exp_tmp = exp((-tmp));
    deltapsis = exp_tmp*(2.0+model_.SIGMAD*tmp*dv_dibl/(2.0*phi))*sqrt((nul+vs-dv_dibl)*(nul+vd-dv_dibl));
    }
    }
    vv = (vp+deltapsis-vs)/NUV;
    if(vv>(-0.6)){
    z1 = 0.25*(vv-1.4+sqrt(vv*(vv-0.394036)+9.662671));
    z2 = (vv-(2.0*z1+log(z1)))/(2.0*z1+1.0);
    qs = z1*(1.0+z2*(1.0+0.070*z2))*NUV;
    } else {
    ln_z1_ = 0.5*(vv-0.201491-sqrt(vv*(vv-0.402982)+2.446562));
    z1 = exp(ln_z1_);
    z2 = (vv-(2.0*z1+ln_z1_))/(2.0*z1+1.0);
    qs = z1*(1.0+z2*(1.0+0.483*z2))*NUV;
    }
    qs2 = qs*qs;
    if_ = qs2+qs;
    sif2 = 0.25+if_;
    sif = sqrt(sif2);
    g_clm = 0.1;
    e_clm = 2.0/(ucrit_o_UT*Leff);
    e_clm2 = e_clm*e_clm;
    e_clmx2 = 2.0*e_clm;
    e_clmp2 = 2.0+e_clm;
    e_clmx2xqs = e_clmx2*qs;
    qsat = e_clmx2*if_/(e_clmp2+e_clmx2xqs+sqrt(e_clmp2*e_clmp2+4.0*e_clmx2xqs));
    qs_qsat = qs-qsat;
    qs_qsat2 = qs_qsat*qs_qsat;
    mdm2 = 2.0-model_.DELTA;
    e_clmxmdm2_2 = e_clm2*mdm2*mdm2;
    vdsat_tmp1 = (2.0*qsat+log(qsat))*(1.0+e_clm*qs_qsat);
    vdsat_tmp11 = g_clm+e_clm*mdm2*qs_qsat;
    vdsat_tmp2 = sqrt(1.0+(2.0*e_clmxmdm2_2*qs_qsat2)/vdsat_tmp11+e_clm2*qs_qsat2);
    vdsat = vp-vdsat_tmp1/vdsat_tmp2;
    dv_clm = (model_.ACLM/model_.DELTA)*(4.0*qsat+model_.DELTA)/(qs+1.0);
    vdssat = (0.5*((vdsat-vs)+(3.0)+sqrt(((vdsat-vs)-(3.0))*((vdsat-vs)-(3.0))+(4.0))));
    vdp_tmp1 = (vd-vs)*sqrt(1.0+4.0*dv_clm/vdssat);
    vdp_tmp2 = sqrt((vdp_tmp1+vdssat)*(vdp_tmp1+vdssat)+4.0*dv_clm*vdssat);
    vdp_tmp3 = sqrt((vdp_tmp1-vdssat)*(vdp_tmp1-vdssat)+4.0*dv_clm*vdssat);
    vdp = 0.5*(vdp_tmp2-vdp_tmp3)+vs;
    u_clm = 0.5*e_clm*Leff/LC*(vd-vdp);
    alpha_clm = LC/(Leff-2.0*LC);
    deltal = LAMBDA_gt*LC*log((alpha_clm+u_clm+sqrt(u_clm*u_clm+2.0*alpha_clm*u_clm+1.0))/(alpha_clm+1.0));
    vv = (vp+deltapsis-vdp)/NUV;
    if(vv>(-0.6)){
    z1 = 0.25*(vv-1.4+sqrt(vv*(vv-0.394036)+9.662671));
    z2 = (vv-(2.0*z1+log(z1)))/(2.0*z1+1.0);
    qdp = z1*(1.0+z2*(1.0+0.070*z2))*NUV;
    } else {
    ln_z1_ = 0.5*(vv-0.201491-sqrt(vv*(vv-0.402982)+2.446562));
    z1 = exp(ln_z1_);
    z2 = (vv-(2.0*z1+ln_z1_))/(2.0*z1+1.0);
    qdp = z1*(1.0+z2*(1.0+0.483*z2))*NUV;
    }
    qdp2 = qdp*qdp;
    irp = qdp2+qdp;
    sirp2 = 0.25+irp;
    sirp = sqrt(sirp2);
    qsqdp = qs+qdp;
    qs_qdp = qs-qdp;
    powqs_qdp2 = qs_qdp*qs_qdp;
    qsqdpp1 = qsqdp+1.0;
    powqsqdpp1_2 = 1.0/(qsqdpp1*qsqdpp1);
    i = if_-irp;
    psi_sa_tmp = psi_p-qs-qdp;
    sqrt_psi_sa = sqrt((0.5*((psi_sa_tmp)+(1.0e-4)+sqrt(((psi_sa_tmp)-(1.0e-4))*((psi_sa_tmp)-(1.0e-4))+(1.0E-2)))));
    if(model_.TG<0){
    z0 = 1.0+dpd+gamma_b_eff/(sqrt_psi_p+sqrt_psi_sa);
    zk = 0.5+dpd*sqrt_psi_sa/gamma_b_eff;
    nq = z0/(zk+sqrt(zk*zk+z0*(qs+qdp)/gamma_g2));
    } else {
    nq = 1.0+gamma_b_eff/(sqrt_psi_p+sqrt_psi_sa);
    }
    v_o = vg_p_chsh-psi_p0;
    if(model_.AQMA!=0.0){
    qr1 = 3.0*(0.70710678118654752440084436210485)*gamma_b_chsh;
    if(vg_p<0.0){
    qbo = vg_p_chsh-psi_p;
    } else {
    qbo = vg_p_chsh/(1.0+dpd)-psi_po;
    }
    dpsiv = axetaqm2_3*(exp((0.66666666666666666666666666666667)*log(sqrt(0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2)-0.5*qbo))-exp((0.66666666666666666666666666666667)*log(sqrt(qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2)-qr1)));
    v_o = v_o+dpsiv;
    } else {
    dpsiv = 0.0;
    }
    if(psi_p>2.0){
    qS = inv_dqmip1*nq*(0.33333333333333333333333333333333)*(qs+qdp+qs+0.5*(1.0+0.8*qs+1.2*qdp)*powqs_qdp2*powqsqdpp1_2);
    } else {
    qS = 0.0;
    }
    if(psi_p>2.0){
    qD = inv_dqmip1*nq*(0.33333333333333333333333333333333)*(qdp+qs+qdp+0.5*(1.0+0.8*qdp+1.2*qs)*powqs_qdp2*powqsqdpp1_2);
    } else {
    qD = 0.0;
    }
    if(psi_p>2.0){
    if(model_.TG<0){
    v1_qg = v_o+2.0*qs*inv_dqmip1;
    v2_qg = v_o+2.0*qdp*inv_dqmip1;
    k1 = sqrt(0.25+v1_qg/gamma_g2);
    k2 = sqrt(0.25+v2_qg/gamma_g2);
    k12 = k1+k2;
    k12_2 = k12*k12;
    k12_3 = k12_2*k12;
    qG = (v1_qg/(1.0+2.0*k1)+v2_qg/(1.0+2.0*k2)+inv_dqmip1*(0.33333333333333333333333333333333)*(powqs_qdp2/k12_3)*(0.8*(k12_2+k1*k2)/qsqdpp1+2.0/gamma_g2));
    } else {
    qG = v_o+qs+qdp+inv_dqmip1*(0.33333333333333333333333333333333)*powqs_qdp2/qsqdpp1;
    }
    } else {
    if(psi_p>0.0){
    qG = (model_.TG<0)?v_o/(0.5+sqrt(0.25+v_o/gamma_g2)) : v_o;
    } else {
    qG = (model_.TG>0)?v_o/(0.5+sqrt(0.25-v_o/gamma_g2)) : v_o;
    }
    }
    qI = qS+qD;
    qB = qG-qI;
    beta_coul = model_.THC/((1.0+(nv*model_.ZC*qs))*(1.0+(nv*model_.ZC*qdp)));
    nu = (nv*(1.0-ETA_t))-1.0;
    gpnu = (gamma_b_eff*sqrt_psi_p)+nu;
    eq = qB+(ETA_t*nv*qI);
    eq1 = gpnu*gpnu+nu*nu*(1.0+if_+if_+irp+irp)-8.0*(0.33333333333333333333333333333333)*nu*gpnu*(sif2+sif*sirp+sirp2)/(sif+sirp);
    beta_nom = 1.0+(ev*gamma_b_eff*sqrtphi)+(ev1*gamma_b_eff2*phi);
    beta_denom = 1.0+(ev*eq)+(ev1*eq1)+beta_coul;
    beta = KP_DEV_t*beta_nom/beta_denom;
    beta_clm_denom = sqrt(1.0+2.0*e_clmxmdm2_2*powqs_qdp2/(g_clm+e_clm*mdm2*(qs_qdp))+e_clm2*powqs_qdp2);
    beta = beta/beta_clm_denom;