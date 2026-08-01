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
    i0 = 2.0*nq*UT2*beta*inv_dqmip1;
    Ispec = i0*WeffNF/(Leff-deltal)*(Weff-model_.WEDGE)/Weff;
    if(model_.PDITS==0.0){
    dits_factor = 1.0;
    } else {
    f_dits = 1.0/(1.0+model_.FPROUT*sqrt(Leff)/(qI+2.0));
    va_dits = (f_dits/model_.PDITS)*(1.0+(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT));
    vdseff = vdssat-(0.5*((vdssat-(vd-vs)-model_.DDITS)+(0.0)+sqrt(((vdssat-(vd-vs)-model_.DDITS)-(0.0))*((vdssat-(vd-vs)-model_.DDITS)-(0.0))+(4.0*model_.DDITS*vdssat))));
    dits_factor = (1.0+(vd-vs-vdseff)/va_dits);
    }
    QS = qS*Q0;
    QD = qD*Q0;
    QG = (-qG)*Q0;
    QB = (-QS)-QD-QG;
    IDS = Ispec*i*dits_factor;
    printf("Begin of output.");
    jss_t = model_.JSS*temp_arg_S;
    jssws_t = model_.JSSWS*temp_arg_S;
    jsswgs_t = model_.JSSWGS*temp_arg_S;
    pbs_t = model_.PBS-(model_.TPB*dT);
    pbsws_t = model_.PBSWS-(model_.TPBSW*dT);
    pbswgs_t = model_.PBSWGS-(model_.TPBSWG*dT);
    cjs_t = model_.CJS*(1.0+model_.TCJ*dT);
    cjsws_t = model_.CJSWS*(1.0+model_.TCJSW*dT);
    cjswgs_t = model_.CJSWGS*(1.0+model_.TCJSWG*dT);
    jtss_t = model_.JTSS*exp((-eg_nom)/UT*model_.XTSS*(1.0-rT));
    jtssws_t = model_.JTSSWS*exp((-eg_nom)/UT*model_.XTSSWS*(1.0-rT));
    jtsswgs_t = model_.JTSSWGS*exp((-eg_nom)/UT*model_.XTSSWGS*(1.0-rT));
    njtss_t = model_.NJTSS*(1.0+(rT-1.0)*model_.TNJTSS);
    njtssws_t = model_.NJTSSWS*(1.0+(rT-1.0)*model_.TNJTSSWS);
    njtsswgs_t = model_.NJTSSWGS*(1.0+(rT-1.0)*model_.TNJTSSWGS);
    jsd_t = model_.JSD*temp_arg_D;
    jsswd_t = model_.JSSWD*temp_arg_D;
    jsswgd_t = model_.JSSWGD*temp_arg_D;
    pbd_t = model_.PBD-(model_.TPB*dT);
    pbswd_t = model_.PBSWD-(model_.TPBSW*dT);
    pbswgd_t = model_.PBSWGD-(model_.TPBSWG*dT);
    cjd_t = model_.CJD*(1.0+model_.TCJ*dT);
    cjswd_t = model_.CJSWD*(1.0+model_.TCJSW*dT);
    cjswgd_t = model_.CJSWGD*(1.0+model_.TCJSWG*dT);
    jtsd_t = model_.JTSD*exp((-eg_nom)/UT*model_.XTSD*(1.0-rT));
    jtsswd_t = model_.JTSSWD*exp((-eg_nom)/UT*model_.XTSSWD*(1.0-rT));
    jtsswgd_t = model_.JTSSWGD*exp((-eg_nom)/UT*model_.XTSSWGD*(1.0-rT));
    njtsd_t = model_.NJTSD*(1.0+(rT-1.0)*model_.TNJTSD);
    njtsswd_t = model_.NJTSSWD*(1.0+(rT-1.0)*model_.TNJTSSWD);
    njtsswgd_t = model_.NJTSSWGD*(1.0+(rT-1.0)*model_.TNJTSSWGD);
    if((AS==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    as = hdif*Weff*(NF+2);
    } else {
    as = hdif*Weff*(NF+1);
    }
    } else {
    as = AS*model_.SCALE*model_.SCALE;
    }
    if((PS==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    ps = 2.0*(hdif*(NF+2)+Weff);
    } else {
    ps = 2.0*hdif*(NF+1)+Weff;
    }
    } else {
    ps = PS*model_.SCALE;
    }
    if((AD==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    ad = hdif*Weff*(NF);
    } else {
    ad = hdif*Weff*(NF+1);
    }
    } else {
    ad = AD*model_.SCALE*model_.SCALE;
    }
    if((PD==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    pd = 2.0*hdif*NF;
    } else {
    pd = 2.0*hdif*(NF+1)+Weff;
    }
    } else {
    pd = PD*model_.SCALE;
    }
    v_si_b = model_.SIGN*(Vsi - Vb);
    v_di_b = model_.SIGN*(Vdi - Vb);
    is_s = jss_t*as+jssws_t*ps+jsswgs_t*WeffNF;
    arg_s = (-v_si_b)*rT/(UT*model_.NJS);
    if(arg_s<(-40.0)){
    arg_s = (-40.0);
    }
    f_breakdown_s = 1.0+model_.XJBVS*exp((-((-v_si_b)+model_.BVS))*rT/(UT*model_.NJS));
    isb_tun = WeffNF*jtsswgs_t*(exp(v_si_b*rT/(UT*njtsswgs_t)*model_.VTSSWGS/max(model_.VTSSWGS+v_si_b, 1.0E-3))-1.0);
    isb_tun = isb_tun+ps*jtssws_t*(exp(v_si_b*rT/(UT*njtssws_t)*model_.VTSSWS/max(model_.VTSSWS+v_si_b, 1.0E-3))-1.0);
    isb_tun = isb_tun+as*jtss_t*(exp(v_si_b*rT/(UT*njtss_t)*model_.VTSS/max(model_.VTSS+v_si_b, 1.0E-3))-1.0);
    ISBJ = (is_s*(1.0-exp(arg_s))*f_breakdown_s+v_si_b*model_.GMIN+isb_tun);
    is_d = jsd_t*ad+jsswd_t*pd+jsswgd_t*WeffNF;
    arg_d = (-v_di_b)*rT/(UT*model_.NJD);
    if(arg_d<(-40.0)){
    arg_d = (-40.0);
    }
    f_breakdown_d = 1.0+model_.XJBVD*exp((-((-v_di_b)+model_.BVD))*rT/(UT*model_.NJD));
    idb_tun = WeffNF*jtsswgd_t*(exp(v_di_b*rT/(UT*njtsswgd_t)*model_.VTSSWGD/max(model_.VTSSWGD+v_di_b, 1.0E-3))-1.0);
    idb_tun = idb_tun+pd*jtsswd_t*(exp(v_di_b*rT/(UT*njtsswd_t)*model_.VTSSWD/max(model_.VTSSWD+v_di_b, 1.0E-3))-1.0);
    idb_tun = idb_tun+ad*jtsd_t*(exp(v_di_b*rT/(UT*njtsd_t)*model_.VTSD/max(model_.VTSD+v_di_b, 1.0E-3))-1.0);
    IDBJ = (is_d*(1.0-exp(arg_d))*f_breakdown_d+v_di_b*model_.GMIN+idb_tun);
    if(v_si_b>0.0){
    csb_s = cjs_t*as*exp((-model_.MJS)*log(1.0+v_si_b/pbs_t));
    cssw_s = cjsws_t*ps*exp((-model_.MJSWS)*log(1.0+v_si_b/pbsws_t));
    csswg_s = cjswgs_t*WeffNF*exp((-model_.MJSWGS)*log(1.0+v_si_b/pbswgs_t));
    qsb_s = cjs_t*as*pbs_t*(1.0-exp((1.0-model_.MJS)*log(1.0+v_si_b/pbs_t)))/(1.0-model_.MJS);
    qssw_s = cjsws_t*ps*pbsws_t*(1.0-exp((1.0-model_.MJSWS)*log(1.0+v_si_b/pbsws_t)))/(1.0-model_.MJSWS);
    qsswg_s = cjswgs_t*WeffNF*pbswgs_t*(1.0-exp((1.0-model_.MJSWGS)*log(1.0+v_si_b/pbswgs_t)))/(1.0-model_.MJSWGS);
    } else {
    csb_s = cjs_t*as*(1.0-model_.MJS*v_si_b/pbs_t);
    cssw_s = cjsws_t*ps*(1.0-model_.MJSWS*v_si_b/pbsws_t);
    csswg_s = cjswgs_t*WeffNF*(1.0-model_.MJSWGS*v_si_b/pbswgs_t);
    qsb_s = cjs_t*as*((-v_si_b)+model_.MJS*0.5/pbs_t*(v_si_b*v_si_b));
    qssw_s = cjsws_t*ps*((-v_si_b)+model_.MJSWS*0.5/pbsws_t*(v_si_b*v_si_b));
    qsswg_s = cjswgs_t*WeffNF*((-v_si_b)+model_.MJSWGS*0.5/pbswgs_t*(v_si_b*v_si_b));
    }
    CSBJ = csb_s+cssw_s+csswg_s;
    QSBJ = (-(qsb_s+qssw_s+qsswg_s));
    if(v_di_b>0.0){
    csb_d = cjd_t*ad*exp((-model_.MJD)*log(1.0+v_di_b/pbd_t));
    cssw_d = cjswd_t*pd*exp((-model_.MJSWD)*log(1.0+v_di_b/pbswd_t));
    csswg_d = cjswgd_t*WeffNF*exp((-model_.MJSWGD)*log(1.0+v_di_b/pbswgd_t));
    qsb_d = cjd_t*ad*pbd_t*(1.0-exp((1.0-model_.MJD)*log(1.0+v_di_b/pbd_t)))/(1.0-model_.MJD);
    qssw_d = cjswd_t*pd*pbswd_t*(1.0-exp((1.0-model_.MJSWD)*log(1.0+v_di_b/pbswd_t)))/(1.0-model_.MJSWD);
    qsswg_d = cjswgd_t*WeffNF*pbswgd_t*(1.0-exp((1.0-model_.MJSWGD)*log(1.0+v_di_b/pbswgd_t)))/(1.0-model_.MJSWGD);
    } else {
    csb_d = cjd_t*ad*(1.0-model_.MJD*v_di_b/pbd_t);
    cssw_d = cjswd_t*pd*(1.0-model_.MJSWD*v_di_b/pbswd_t);
    csswg_d = cjswgd_t*WeffNF*(1.0-model_.MJSWGD*v_di_b/pbswgd_t);
    qsb_d = cjd_t*ad*((-v_di_b)+model_.MJD*0.5/pbd_t*(v_di_b*v_di_b));
    qssw_d = cjswd_t*pd*((-v_di_b)+model_.MJSWD*0.5/pbswd_t*(v_di_b*v_di_b));
    qsswg_d = cjswgd_t*WeffNF*((-v_di_b)+model_.MJSWGD*0.5/pbswgd_t*(v_di_b*v_di_b));
    }
    CDBJ = csb_d+cssw_d+csswg_d;
    QDBJ = (-(qsb_d+qssw_d+qsswg_d));
    printf("IDB = ", SIGN_M*IDBJ);
    printf("IDBDvd = ", SIGN_M*IDBJ);
    printf("IDBDvs = ", SIGN_M*IDBJ);
    printf("IDBDvg = ", SIGN_M*IDBJ);
    printf("ISB = ", SIGN_M*ISBJ);
    printf("ISBDvd = ", SIGN_M*ISBJ);
    printf("ISBDvs = ", SIGN_M*ISBJ);
    printf("ISBDvg = ", SIGN_M*ISBJ);
    myadms_t1 = SIGN_M*IDBJ;
    fRHS[4] += myadms_t1;
    fRHS[3] -= myadms_t1;
    myadms_t1 = SIGN_M*ISBJ;
    fRHS[5] += myadms_t1;
    fRHS[3] -= myadms_t1;
    DdtExp0 = QDBJ;
    DdtAns0 = DdtExp0;
    myadms_t1 = SIGN_M*0.0;
    fRHS[4] += myadms_t1;
    fRHS[3] -= myadms_t1;
    myadms_t2 = SIGN_M*DdtAns0;
    qRHS[4] += myadms_t2 - myadms_t1;
    qRHS[3] -= (myadms_t2 - myadms_t1);
    DdtExp1 = QSBJ;
    DdtAns1 = DdtExp1;
    myadms_t1 = SIGN_M*0.0;
    fRHS[5] += myadms_t1;
    fRHS[3] -= myadms_t1;
    myadms_t2 = SIGN_M*DdtAns1;
    qRHS[5] += myadms_t2 - myadms_t1;
    qRHS[3] -= (myadms_t2 - myadms_t1);
    if(model_.RLX<0.0){
    if(model_.RSX<0.0){
    rs = (hdif*model_.RSH+(ldif-model_.DL/2.0)*model_.RS)/WeffNF;
    } else {
    rs = model_.RSX/WeffNF;
    }
    if(model_.RDX<0.0){
    rd = (hdif*model_.RSH+(ldif-model_.DL/2.0)*model_.RD)/WeffNF;
    } else {
    rd = model_.RDX/WeffNF;
    }
    } else {
    rs = model_.RLX/WeffNF;
    rd = rs;
    }
    tmp = (1.0+model_.WRLX/Weff);
    rs = rs*tmp;
    rd = rd*tmp;
    rg = model_.RGSH*Weff/(3.0*model_.GC*model_.GC*NF*Leff)*(1.0+model_.KRGL1*Leff*Leff);
    if(model_.RINGTYPE==1.0){
    rb = (model_.RBN==0.0)?model_.RBWSH*0.5/Weff : 1.0/((Weff*2.0/model_.RBWSH)+(NF/model_.RBN));
    if(int(NF)%2==0){
    rsb = (model_.RSBN==0.0)?model_.RSBWSH*0.5/Weff : 1.0/((Weff*2.0/model_.RSBWSH)+(NF/model_.RSBN));
    rdb = (model_.RDBN==0.0)?model_.RDBWSH*0.5/Weff : 1.0/((Weff*2.0/model_.RDBWSH)+(NF/model_.RDBN));
    } else {
    rsb = (model_.RSBN==0.0)?model_.RSBWSH/Weff : 1.0/((Weff/model_.RSBWSH)+(NF/model_.RSBN));
    rdb = rsb;
    }
    } else {
    rb = model_.RBWSH*0.5/Weff;
    if(int(NF)%2==0){
    rsb = model_.RSBWSH*0.5/Weff;
    rdb = model_.RDBWSH*0.5/Weff;
    } else {
    rsb = model_.RSBWSH/Weff;
    rdb = rsb;
    }
    }
    rdsb = model_.RDSBSH*Leff/WeffNF;
    tmp = (1.0+model_.TR*dT+model_.TR2*dT2);
    rs = rs*tmp;
    rd = rd*tmp;
    rg = rg*tmp;
    rb = rb*tmp;
    rsb = rsb*tmp;
    rdb = rdb*tmp;
    rdsb = rdsb*tmp;
    rs = ((rs)>((1.0E-3))?(rs) : ((1.0E-3)));
    rd = ((rd)>((1.0E-3))?(rd) : ((1.0E-3)));
    rg = ((rg)>((1.0E-3))?(rg) : ((1.0E-3)));
    rb = ((rb)>((1.0E-3))?(rb) : ((1.0E-3)));
    rsb = ((rsb)>((1.0E-3))?(rsb) : ((1.0E-3)));
    rdb = ((rdb)>((1.0E-3))?(rdb) : ((1.0E-3)));
    rdsb = ((rdsb)>((1.0E-3))?(rdsb) : ((1.0E-3)));
    DdtExp2 = model_.CGSO*M*WeffNF*(Vg - Vsi);
    DdtAns2 = DdtExp2;
    myadms_t1 = 0.0;
    fRHS[1] += myadms_t1;
    fRHS[5] -= myadms_t1;
    myadms_t2 = DdtAns2;
    qRHS[1] += myadms_t2 - myadms_t1;
    qRHS[5] -= (myadms_t2 - myadms_t1);
    DdtExp3 = model_.CGDO*M*WeffNF*(Vg - Vdi);
    DdtAns3 = DdtExp3;
    myadms_t1 = 0.0;
    fRHS[1] += myadms_t1;
    fRHS[4] -= myadms_t1;
    myadms_t2 = DdtAns3;
    qRHS[1] += myadms_t2 - myadms_t1;
    qRHS[4] -= (myadms_t2 - myadms_t1);
    DdtExp4 = model_.CGBO*M*2.0*Leff*NF*(Vg - Vb);
    DdtAns4 = DdtExp4;
    myadms_t1 = 0.0;
    fRHS[1] += myadms_t1;
    fRHS[3] -= myadms_t1;
    myadms_t2 = DdtAns4;
    qRHS[1] += myadms_t2 - myadms_t1;
    qRHS[3] -= (myadms_t2 - myadms_t1);
    myadms_t1 = M*(Vs - Vsi)/rs;
    fRHS[2] += myadms_t1;
    fRHS[5] -= myadms_t1;
    myadms_t1 = 0;
    fRHS[2] += myadms_t1;
    fRHS[5] -= myadms_t1;
    myadms_t1 = M*(Vd - Vdi)/rd;
    fRHS[0] += myadms_t1;
    fRHS[4] -= myadms_t1;
    myadms_t1 = 0;
    fRHS[0] += myadms_t1;
    fRHS[4] -= myadms_t1;
    Ispec_edge = Ispec*model_.WEDGE/(Weff-model_.WEDGE);
    Q0_edge = Q0*model_.WEDGE/(Weff-model_.WEDGE);
    dgamma_edge = (model_.DGAMMAEDGE*(1.0+model_.WLDGAMMAEDGE/WLeff)/sqrtUT);
    dphi_edge = model_.DPHIEDGE*(1.0+model_.LDPHIEDGE/Leff)*(1.0+model_.WDPHIEDGE/Weff)*(1.0+model_.WLDPHIEDGE/WLeff)/UT;
    dvp_edge = (-dgamma_edge)*psi_p/(sqrt_psi_p+0.5*gamma_b_eff)-dphi_edge;
    vv = (vp+dvp_edge+deltapsis-vs)/NUV;
    if(vv>(-0.6)){
    z1 = 0.25*(vv-1.4+sqrt(vv*(vv-0.394036)+9.662671));
    z2 = (vv-(2.0*z1+log(z1)))/(2.0*z1+1.0);
    qs_edge = z1*(1.0+z2*(1.0+0.070*z2))*NUV;
    } else {
    ln_z1_ = 0.5*(vv-0.201491-sqrt(vv*(vv-0.402982)+2.446562));
    z1 = exp(ln_z1_);
    z2 = (vv-(2.0*z1+ln_z1_))/(2.0*z1+1.0);
    qs_edge = z1*(1.0+z2*(1.0+0.483*z2))*NUV;
    }
    vv = (vp+dvp_edge+deltapsis-vdp)/NUV;
    if(vv>(-0.6)){
    z1 = 0.25*(vv-1.4+sqrt(vv*(vv-0.394036)+9.662671));
    z2 = (vv-(2.0*z1+log(z1)))/(2.0*z1+1.0);
    qdp_edge = z1*(1.0+z2*(1.0+0.070*z2))*NUV;
    } else {
    ln_z1_ = 0.5*(vv-0.201491-sqrt(vv*(vv-0.402982)+2.446562));
    z1 = exp(ln_z1_);
    z2 = (vv-(2.0*z1+ln_z1_))/(2.0*z1+1.0);
    qdp_edge = z1*(1.0+z2*(1.0+0.483*z2))*NUV;
    }
    ids_edge = (qs_edge*(qs_edge+1.0)-qdp_edge*(qdp_edge+1.0));
    IDS_edge = Ispec_edge*ids_edge*dits_factor;
    psi_p_edge = psi_p-dgamma_edge*psi_p/(sqrt_psi_p+0.5*gamma_b_eff);
    sqrt_psi_p_edge = sqrt((0.5*((psi_p_edge)+(1.0E-4)+sqrt(((psi_p_edge)-(1.0E-4))*((psi_p_edge)-(1.0E-4))+(1.0E-2)))));
    gamma_b_chsh_edge = gamma_b_chsh+dgamma_edge;
    psi_sa_tmp = psi_p_edge-qs_edge-qdp_edge;
    sqrt_psi_sa = sqrt((0.5*((psi_sa_tmp)+(1.0e-4)+sqrt(((psi_sa_tmp)-(1.0e-4))*((psi_sa_tmp)-(1.0e-4))+(1.0E-2)))));
    if(model_.TG<0){
    z0 = 1.0+dpd+gamma_b_chsh_edge/(sqrt_psi_p_edge+sqrt_psi_sa);
    zk = 0.5+dpd*sqrt_psi_sa/gamma_b_chsh_edge;
    nq_edge = z0/(zk+sqrt(zk*zk+z0*(qs_edge+qdp_edge)/gamma_g2));
    } else {
    nq_edge = 1.0+gamma_b_chsh_edge/(sqrt_psi_p_edge+sqrt_psi_sa);
    }
    qsqdp_edge = qs_edge+qdp_edge;
    qs_qdp_edge = qs_edge-qdp_edge;
    powqs_qdp2_edge = qs_qdp_edge*qs_qdp_edge;
    qsqdpp1_edge = qsqdp_edge+1.0;
    powqsqdpp1_2_edge = 1.0/(qsqdpp1_edge*qsqdpp1_edge);
    if(psi_p_edge>2.0){
    qS_edge = inv_dqmip1*nq_edge*(0.33333333333333333333333333333333)*(qs_edge+qdp_edge+qs_edge+0.5*(1.0+0.8*qs_edge+1.2*qdp_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge);
    } else {
    qS_edge = 0.0;
    }
    if(psi_p_edge>2.0){
    qD_edge = inv_dqmip1*nq_edge*(0.33333333333333333333333333333333)*(qdp_edge+qs_edge+qdp_edge+0.5*(1.0+0.8*qdp_edge+1.2*qs_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge);
    } else {
    qD_edge = 0.0;
    }
    if(psi_p_edge>2.0){
    if(model_.TG<0){
    v1_qg = v_o+2.0*qs_edge*inv_dqmip1;
    v2_qg = v_o+2.0*qdp_edge*inv_dqmip1;
    k1 = sqrt(0.25+v1_qg/gamma_g2);
    k2 = sqrt(0.25+v2_qg/gamma_g2);
    k12 = k1+k2;
    k12_2 = k12*k12;
    k12_3 = k12_2*k12;
    qG_edge = (v1_qg/(1.0+2.0*k1)+v2_qg/(1.0+2.0*k2)+inv_dqmip1*(0.33333333333333333333333333333333)*(powqs_qdp2_edge/k12_3)*(0.8*(k12_2+k1*k2)/qsqdpp1_edge+2.0/gamma_g2));
    } else {
    qG_edge = v_o+qs_edge+qdp_edge+inv_dqmip1*(0.33333333333333333333333333333333)*powqs_qdp2_edge/qsqdpp1_edge;
    }
    } else {
    if(psi_p_edge>0.0){
    qG_edge = (model_.TG<0)?v_o/(0.5+sqrt(0.25+v_o/gamma_g2)) : v_o;
    } else {
    qG_edge = (model_.TG>0)?v_o/(0.5+sqrt(0.25-v_o/gamma_g2)) : v_o;
    }
    }
    qI_edge = qS_edge+qD_edge;
    qB_edge = qG_edge-qI_edge;
    QS_edge = qS_edge*Q0_edge;
    QD_edge = qD_edge*Q0_edge;
    QG_edge = (-qG_edge)*Q0_edge;
    QB_edge = (-QS_edge)-QD_edge-QG_edge;
    myadms_t1 = SIGN_M*d_gt_s_flag*IDS_edge;
    fRHS[4] += myadms_t1;
    fRHS[5] -= myadms_t1;
    DdtExp5 = QB_edge;
    DdtAns5 = DdtExp5;
    myadms_t1 = SIGN_M*0.0*QON;
    fRHS[3] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*DdtAns5*QON;
    qRHS[3] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    DdtExp6 = QD_edge;
    DdtAns6 = DdtExp6;
    DdtExp7 = QS_edge;
    DdtAns7 = DdtExp7;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    fRHS[4] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns6+(1-d_gt_s_flag)*DdtAns7)*QON;
    qRHS[4] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    DdtExp8 = QS_edge;
    DdtAns8 = DdtExp8;
    DdtExp9 = QD_edge;
    DdtAns9 = DdtExp9;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    fRHS[5] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns8+(1-d_gt_s_flag)*DdtAns9)*QON;
    qRHS[5] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    if(model_.LOV>0.0){
    if(model_.TG<0){
    vgsov_p = vg-model_.VOV*vs-vfb_ov;
    if(vgsov_p>0.0){
    gamma_dep_sov = gamma_g_ov;
    gamma_acc_sov = gamma_ov;
    v0_sov = vgsov_p;
    } else {
    gamma_dep_sov = gamma_ov;
    gamma_acc_sov = gamma_g_ov;
    v0_sov = (-vgsov_p);
    }
    a0_sov = 1.0+gamma_acc_sov*(0.70710678118654752440084436210485);
    a1_sov = gamma_dep_sov/gamma_acc_sov;
    a2_sov = a0_sov/(a0_sov+a1_sov);
    a3_sov = 1.0+gamma_dep_sov*(0.70710678118654752440084436210485)+a1_sov;
    v1_sov = v0_sov*0.5-3.0*a2_sov*a3_sov;
    dpsigs0 = v1_sov+sqrt(v1_sov*v1_sov+6.0*a2_sov*v0_sov);
    gamma_dep2_sov = gamma_dep_sov*(0.5+3.0/(3.0*(1.4142135623730950488016887242097)*gamma_acc_sov+v0_sov-dpsigs0));
    a4_sov = 1.0-exp((-dpsigs0));
    v2_sov = v0_sov-a4_sov;
    tmp = v2_sov/(gamma_dep2_sov+sqrt(gamma_dep2_sov*gamma_dep2_sov+v2_sov));
    dpsigs = tmp*tmp+a4_sov;
    v2b_sov = v0_sov-dpsigs;
    v3_sov = v2b_sov*0.5;
    tmp = v3_sov+3.0*a0_sov;
    if(vgsov_p>0.0){
    dpsiox_s = v3_sov-3.0*a0_sov+sqrt(tmp*tmp-6.0*v2b_sov);
    } else {
    dpsiox_s = (-(v3_sov-3.0*a0_sov+sqrt(tmp*tmp-6.0*v2b_sov)));
    }
    } else {
    vgsov_p = vg-model_.VOV*vs-vfb_ov;
    if(vgsov_p>0.0){
    gamma_acc_sov = gamma_ov;
    v0_sov = vgsov_p;
    a0_sov = 1.0+gamma_acc_sov*(0.70710678118654752440084436210485);
    v1_sov = v0_sov*0.5-3.0*a0_sov*a0_sov;
    dpsigs0 = v1_sov+sqrt(v1_sov*v1_sov);
    dpsigs = 1.0-exp((-dpsigs0));
    v2b_sov = v0_sov-dpsigs;
    v3_sov = v2b_sov*0.5;
    tmp = v3_sov+3.0*a0_sov;
    dpsiox_s = v3_sov-3.0*a0_sov+sqrt(tmp*tmp-6.0*v2b_sov);
    } else {
    gamma_dep_sov = gamma_ov;
    v0_sov = (-vgsov_p);
    a3_sov = 1.0+gamma_dep_sov*(0.70710678118654752440084436210485);
    v1_sov = v0_sov*0.5-3.0*a3_sov;
    dpsigs0 = v1_sov+sqrt(v1_sov*v1_sov+6.0*v0_sov);
    gamma_dep2_sov = gamma_dep_sov*0.5;
    a4_sov = 1.0-exp((-dpsigs0));
    v2_sov = v0_sov-a4_sov;
    tmp = v2_sov/(gamma_dep2_sov+sqrt(gamma_dep2_sov*gamma_dep2_sov+v2_sov));
    dpsigs = tmp*tmp+a4_sov;
    v2b_sov = v0_sov-dpsigs;
    dpsiox_s = (-v2b_sov);
    }
    }
    if(model_.TG<0){
    vgdov_p = vg-model_.VOV*vd-vfb_ov;
    if(vgdov_p>0.0){
    gamma_dep_dov = gamma_g_ov;
    gamma_acc_dov = gamma_ov;
    v0_dov = vgdov_p;
    } else {
    gamma_dep_dov = gamma_ov;
    gamma_acc_dov = gamma_g_ov;
    v0_dov = (-vgdov_p);
    }
    a0_dov = 1.0+gamma_acc_dov*(0.70710678118654752440084436210485);
    a1_dov = gamma_dep_dov/gamma_acc_dov;
    a2_dov = a0_dov/(a0_dov+a1_dov);
    a3_dov = 1.0+gamma_dep_dov*(0.70710678118654752440084436210485)+a1_dov;
    v1_dov = v0_dov*0.5-3.0*a2_dov*a3_dov;
    dpsigd0 = v1_dov+sqrt(v1_dov*v1_dov+6.0*a2_dov*v0_dov);
    gamma_dep2_dov = gamma_dep_dov*(0.5+3.0/(3.0*(1.4142135623730950488016887242097)*gamma_acc_dov+v0_dov-dpsigd0));
    a4_dov = 1.0-exp((-dpsigd0));
    v2_dov = v0_dov-a4_dov;
    tmp = v2_dov/(gamma_dep2_dov+sqrt(gamma_dep2_dov*gamma_dep2_dov+v2_dov));
    dpsigd = tmp*tmp+a4_dov;
    v2b_dov = v0_dov-dpsigd;
    v3_dov = v2b_dov*0.5;
    tmp = v3_dov+3.0*a0_dov;
    if(vgdov_p>0.0){
    dpsiox_d = v3_dov-3.0*a0_dov+sqrt(tmp*tmp-6.0*v2b_dov);
    } else {
    dpsiox_d = (-(v3_dov-3.0*a0_dov+sqrt(tmp*tmp-6.0*v2b_dov)));
    }
    } else {
    vgdov_p = vg-model_.VOV*vd-vfb_ov;
    if(vgdov_p>0.0){
    gamma_acc_dov = gamma_ov;
    v0_dov = vgdov_p;
    a0_dov = 1.0+gamma_acc_dov*(0.70710678118654752440084436210485);
    v1_dov = v0_dov*0.5-3.0*a0_dov*a0_dov;
    dpsigd0 = v1_dov+sqrt(v1_dov*v1_dov);
    dpsigd = 1.0-exp((-dpsigd0));
    v2b_dov = v0_dov-dpsigd;
    v3_dov = v2b_dov*0.5;
    tmp = v3_dov+3.0*a0_dov;
    dpsiox_d = v3_dov-3.0*a0_dov+sqrt(tmp*tmp-6.0*v2b_dov);
    } else {
    gamma_dep_dov = gamma_ov;
    v0_dov = (-vgdov_p);
    a3_dov = 1.0+gamma_dep_dov*(0.70710678118654752440084436210485);
    v1_dov = v0_dov*0.5-3.0*a3_dov;
    dpsigd0 = v1_dov+sqrt(v1_dov*v1_dov+6.0*v0_dov);
    gamma_dep2_dov = gamma_dep_dov*0.5;
    a4_dov = 1.0-exp((-dpsigd0));
    v2_dov = v0_dov-a4_dov;
    tmp = v2_dov/(gamma_dep2_dov+sqrt(gamma_dep2_dov*gamma_dep2_dov+v2_dov));
    dpsigd = tmp*tmp+a4_dov;
    v2b_dov = v0_dov-dpsigd;
    dpsiox_d = (-v2b_dov);
    }
    }
    QSOV = (-Q0OV)*dpsiox_s;
    QDOV = (-Q0OV)*dpsiox_d;
    } else {
    dpsiox_s = 0.0;
    QSOV = 0.0;
    dpsiox_d = 0.0;
    QDOV = 0.0;
    }
    DdtExp10 = QDOV;
    DdtAns10 = DdtExp10;
    DdtExp11 = QSOV;
    DdtAns11 = DdtExp11;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    fRHS[4] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns10+(1-d_gt_s_flag)*DdtAns11);
    qRHS[4] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    DdtExp12 = QSOV;
    DdtAns12 = DdtExp12;
    DdtExp13 = QDOV;
    DdtAns13 = DdtExp13;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    fRHS[5] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns12+(1-d_gt_s_flag)*DdtAns13);
    qRHS[5] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    if(model_.KJF!=0.0){
    tmp = vbi+model_.VFR/UT+vs-(psi_p-2.0*qs);
    QSFR = Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vs)*sqrt(UT*(0.5*((tmp)+(0.0)+sqrt(((tmp)-(0.0))*((tmp)-(0.0))+(model_.DFR)))));
    tmp = vbi+model_.VFR/UT+vdp-(psi_p-2.0*qdp);
    QDFR = Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vdp)*sqrt(UT*(0.5*((tmp)+(0.0)+sqrt(((tmp)-(0.0))*((tmp)-(0.0))+(model_.DFR)))));
    } else {
    QSFR = 0.0;
    QDFR = 0.0;
    }
    DdtExp14 = QDFR;
    DdtAns14 = DdtExp14;
    DdtExp15 = QSFR;
    DdtAns15 = DdtExp15;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    fRHS[4] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns14+(1-d_gt_s_flag)*DdtAns15);
    qRHS[4] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    DdtExp16 = QSFR;
    DdtAns16 = DdtExp16;
    DdtExp17 = QDFR;
    DdtAns17 = DdtExp17;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    fRHS[5] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns16+(1-d_gt_s_flag)*DdtAns17);
    qRHS[5] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    vgse = vfb+psi_p-2.0*qs;
    tmp1 = (vdp-vs-vgse)*UT-model_.EGIDL;
    if(tmp1<1.0e-10){
    IGIDL = 0.0;
    } else {
    tmp2 = vdp*vdp*vdp*UT3;
    IGIDL = model_.AGIDL*WeffNF*(tmp1/(3.0*TOX))*exp((-(3.0*TOX*model_.BGIDL))/tmp1)*tmp2/(model_.CGIDL+tmp2);
    }
    vgde = vfb+psi_p-2.0*qdp;
    tmp1 = (vs-vdp-vgde)*UT-model_.EGIDL;
    if(tmp1<1.0e-10){
    IGISL = 0.0;
    } else {
    tmp2 = vs*vs*vs*UT3;
    IGISL = model_.AGIDL*WeffNF*(tmp1/(3.0*TOX))*exp((-(3.0*TOX*model_.BGIDL))/tmp1)*tmp2/(model_.CGIDL+tmp2);
    }
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*IGIDL+(1-d_gt_s_flag)*IGISL);
    fRHS[4] += myadms_t1;
    fRHS[3] -= myadms_t1;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*IGISL+(1-d_gt_s_flag)*IGIDL);
    fRHS[5] += myadms_t1;
    fRHS[3] -= myadms_t1;
    if(model_.KG>0.0){
    if(((psi_p>0)&&(model_.TG<0))||((psi_p<0)&&(model_.TG>0))){
    v1_ig = sqrt(0.25+(v_o+2.0*qs)/gamma_g2);
    v2_ig = 0.5+v1_ig;
    psi_ox = (v_o+2.0*qs)/v2_ig;
    d_psi_dq = (2.0/v2_ig)*(1.0-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2));
    } else {
    psi_ox = v_o+2.0*qs;
    d_psi_dq = 2.0;
    }
    psi_x = fabs(psi_ox)/xb;
    if(psi_x<1.0){
    s1_px = sqrt(1.0-psi_x);
    p_tun = exp((-ub)*(1.0/(1.0+s1_px)+s1_px));
    } else {
    p_tun = exp((-ub)/psi_x);
    }
    igo = qs*psi_ox*p_tun;
    if((vs==vd)||(psi_ox==0.0)){
    nigc = igo*nq;
    nigs = nigc*0.5;
    nigd = nigs;
    } else {
    dq_dksi = (irp-if_)/(2.0*qs+1.0);
    a_gc = dq_dksi*(1.0/qs+d_psi_dq/psi_ox);
    if(psi_x<1.0){
    s1_px = sqrt(1.0-psi_x);
    if(psi_ox>0.0){
    b_gc = dq_dksi*d_psi_dq*(ub/xb)*(3.0+psi_x)/(4.0+2.0*s1_px*(2.0+psi_x));
    } else {
    b_gc = (-dq_dksi)*d_psi_dq*(ub/xb)*(3.0+psi_x)/(4.0+2.0*s1_px*(2.0+psi_x));
    }
    } else {
    b_gc = dq_dksi*d_psi_dq*ub/(psi_x*psi_ox);
    }
    nigc = nq*igo*(2.0+a_gc)/(2.0-b_gc);
    nigs = 0.5*nq*igo*(3.0+a_gc)/(3.0-b_gc);
    nigd = nigc-nigs;
    }
    if(vg>vfb){
    IGB = 0.0;
    IG = 2.0*model_.KG*WeffNF*Leff*UT2*nigc/TOX2;
    IGD = 2.0*model_.KG*WeffNF*Leff*UT2*nigd/TOX2;
    IGS = IG-IGD;
    } else {
    IGB = model_.KG*WeffNF*Leff*psi_ox*fabs(psi_ox)*UT2*p_tun/TOX2;
    IG = 0.0;
    IGD = 0.0;
    IGS = 0.0;
    }
    if(model_.LOVIG!=0){
    psi_oxr_ov_s = (vg-vs>vfb_ov)?vg-vs-pow(sqrt(vg-vs-vfb_ov+gamma_g2*0.25)-gamma_g*0.5, 2.0) : vg-vs+pow(sqrt((-vg)+vs+vfb_ov+gamma_ov2*0.25)-gamma_ov*0.5, 2.0);
    psi_xr_ov_s = fabs(psi_oxr_ov_s)/xb;
    if(psi_xr_ov_s<1.0){
    s1_px = sqrt(1.0-psi_xr_ov_s);
    p_tun_sov = exp((-ub)*(1.0/(1.0+s1_px)+s1_px));
    } else {
    p_tun_sov = exp((-ub)/psi_xr_ov_s);
    }
    IGSOV = model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*fabs(psi_oxr_ov_s)*UT2*p_tun_sov/TOX2;
    psi_oxr_ov_d = (vg-vd>vfb_ov)?vg-vd-pow(sqrt(vg-vd-vfb_ov+gamma_g2*0.25)-gamma_g*0.5, 2.0) : vg-vd+pow(sqrt((-vg)+vd+vfb_ov+gamma_ov2*0.25)-gamma_ov*0.5, 2.0);
    psi_xr_ov_d = fabs(psi_oxr_ov_d)/xb;
    if(psi_xr_ov_d<1.0){
    s1_px = sqrt(1.0-psi_xr_ov_d);
    p_tun_dov = exp((-ub)*(1.0/(1.0+s1_px)+s1_px));
    } else {
    p_tun_dov = exp((-ub)/psi_xr_ov_d);
    }
    IGDOV = model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*fabs(psi_oxr_ov_d)*UT2*p_tun_dov/TOX2;
    } else {
    IGSOV = 0.0;
    IGDOV = 0.0;
    }
    } else {
    IG = 0.0;
    IGS = 0.0;
    IGD = 0.0;
    IGB = 0.0;
    IGSOV = 0.0;
    IGDOV = 0.0;
    }
    myadms_t1 = (-SIGN_M)*IGB;
    fRHS[3] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t1 = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD);
    fRHS[5] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t1 = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS);
    fRHS[4] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t1 = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV);
    fRHS[5] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t1 = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV);
    fRHS[4] += myadms_t1;
    fRHS[1] -= myadms_t1;
    v_ib = (vd-vs)-model_.IBN*2.0*vdssat;
    if((v_ib>0.0)&&(model_.IBA>0.0)){
    tmp = IBB_t*LC/(v_ib*UT);
    if(tmp>70.0){
    IDB = 0.0;
    } else {
    IDB = IDS*v_ib*UT*exp((-tmp))*model_.IBA/IBB_t;
    }
    } else {
    IDB = 0.0;
    }
    myadms_t1 = SIGN_M*0.5*(d_gt_s_flag+1)*IDB;
    fRHS[4] += myadms_t1;
    fRHS[3] -= myadms_t1;
    myadms_t1 = SIGN_M*0.5*(1-d_gt_s_flag)*IDB;
    fRHS[5] += myadms_t1;
    fRHS[3] -= myadms_t1;
    tmp = 1+e_clm*qs_qdp;
    gn = (2/(tmp*tmp*qsqdpp1))*((0.33333333333333333333333333333333)*(qs2+qs*qdp+qdp2)+e_clm2*i*i*0.25+0.25*(e_clm*i+1)*qsqdp+(e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*log(max(1.0E-24, fabs((qs+0.5-0.5*e_clm*i)/(qdp+0.5-0.5*e_clm*i)))));
    thermal = 4.0*(1.3807E-23)*thermocrasia*Ispec*gn/UT*model_.TH_NOI;
    gmg = (Ispec/UT)*(qs_qdp)/nv;
    flicker = model_.KF*exp(model_.EF*log(max(1.0E-24, fabs(gmg))))/(WeffNF*Leff*model_.COX*inv_dqmip1);
    omegaspec = (beta/model_.COX)*UT/(Leff*Leff);
    if(omegaspec!=0.0){
    OMEGA = 1.0/omegaspec;
    } else {
    OMEGA = 0.0;
    }
    j = 1.0;
    xf = qs+0.5;
    xr = qdp+0.5;
    snidid = (4.0*xf*xf-3.0*xf+4.0*xf*xr-3.0*xr+4.0*xr*xr)/(6.0*(xf+xr));
    snigig = OMEGA*OMEGA*(16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr+80.0*xf*xr*xr*xr+80.0*xf*xf*xf*xr+168.0*xf*xf*xr*xr-15.0*xf*xf*xf-15.0*xr*xr*xr-75.0*xf*xf*xr-75.0*xf*xr*xr)/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr));
    snibib = snigig*(nq0-1.0)*(nq0-1.0);
    snigid = (j*OMEGA/(18.0*nq0))*((xf-xr)*(xf*xf+4.0*xf*xr+xr*xr))/((xf+xr)*(xf+xr)*(xf+xr));
    if((snidid==0.0)||(snigig==0.0)){
    c_igid = 0.0;
    } else {
    c_igid = j*snigid/sqrt(snidid*snigig);
    }
    snspec = 4.0*(1.3807E-23)*thermocrasia*Ispec/UT;
    snidid = snidid*model_.NQS_NOI;
    snigig = snigig*model_.NQS_NOI;
    snigid = snigid*model_.NQS_NOI;
    noise_ds1 = snidid*(1.0-c_igid*c_igid)*model_.NQS_NOI;
    noise_ds2 = c_igid*snidid*model_.NQS_NOI;
    noise_g = snigig*model_.NQS_NOI;
    noise_b = snibib*model_.NQS_NOI;
    if(noise_ds1<=0.0){
    noise_ds1 = 0.0;
    }
    if(noise_ds2<=0.0){
    noise_ds2 = 0.0;
    }
    if(noise_g<=0.0){
    noise_g = 0.0;
    }
    if(noise_b<=0.0){
    noise_b = 0.0;
    }
    if(IG>0.0){
    sig_shot = 2.0*(1.602E-19)*IG;
    sig_flicker = model_.KGFN*IG*IG;
    } else {
    sig_shot = 0.0;
    sig_flicker = 0.0;
    }
    myadms_t1 = 0;
    fRHS[4] += myadms_t1;
    fRHS[5] -= myadms_t1;
    myadms_t1 = 0;
    fRHS[4] += myadms_t1;
    fRHS[5] -= myadms_t1;
    myadms_t1 = Vnoi;
    fRHS[6] += myadms_t1;
    myadms_t1 = 0;
    fRHS[6] += myadms_t1;
    myadms_t1 = 0;
    fRHS[4] += myadms_t1;
    fRHS[5] -= myadms_t1;
    myadms_t1 = Vnoi*noise_ds2;
    fRHS[4] += myadms_t1;
    fRHS[5] -= myadms_t1;
    DdtExp18 = Vnoi*noise_g;
    DdtAns18 = DdtExp18;
    myadms_t1 = 0.0;
    fRHS[1] += myadms_t1;
   myadms_t2 = DdtAns18;
   qRHS[1] += myadms_t2 - myadms_t1;
    myadms_t1 = 0;
    fRHS[3] += myadms_t1;
    myadms_t1 = 0;
    fRHS[1] += myadms_t1;
    myadms_t1 = 0;
    fRHS[1] += myadms_t1;
    printf("IDS = ", SIGN_M*IDS*d_gt_s_flag);
    printf("IDSDvd = ", SIGN_M*IDS*d_gt_s_flag);
    printf("IDSDvs = ", SIGN_M*IDS*d_gt_s_flag);
    printf("IDSDvg = ", SIGN_M*IDS*d_gt_s_flag);
    printf("**End of Time point.");
    myadms_t1 = SIGN_M*d_gt_s_flag*IDS;
    fRHS[4] += myadms_t1;
    fRHS[5] -= myadms_t1;
    DdtExp19 = QB;
    DdtAns19 = DdtExp19;
    myadms_t1 = SIGN_M*0.0*QON;
    fRHS[3] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*DdtAns19*QON;
    qRHS[3] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    DdtExp20 = QD;
    DdtAns20 = DdtExp20;
    DdtExp21 = QS;
    DdtAns21 = DdtExp21;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    fRHS[4] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns20+(1-d_gt_s_flag)*DdtAns21)*QON;
    qRHS[4] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    DdtExp22 = QS;
    DdtAns22 = DdtExp22;
    DdtExp23 = QD;
    DdtAns23 = DdtExp23;
    myadms_t1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    fRHS[5] += myadms_t1;
    fRHS[1] -= myadms_t1;
    myadms_t2 = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns22+(1-d_gt_s_flag)*DdtAns23)*QON;
    qRHS[5] += myadms_t2 - myadms_t1;
    qRHS[1] -= (myadms_t2 - myadms_t1);
    if(model_.INFO_LEVEL>0.0){
    if(model_.INFO_LEVEL==1.0){
    printf("");
    printf("########################################");
    printf("#                                      #");
    printf("# EKV3 model, Verilog-A code           #");
    printf("# (Model version: 301.02)              #");
    printf("# Information level = %g                #", model_.INFO_LEVEL);
    printf("#   (INFO_LEVEL)                       #");
    printf("#                                      #");
    printf("########################################");
    printf("");
    printf("  On device: %m");
    printf("  Model case: low frequency (DC: two intrinsic nodes) ");
    printf("  Temperature: %g C \t UT = %g V \t model_.TNOM = %g C", (thermocrasia-273.15), UT, model_.TNOM);
    printf("");
    printf("+ GENERAL CHARACTERISTICS ");
    printf("|");
    printf(">- TOX = %g m ", TOX);
    printf(">- model_.COX = %g F*m^(-2)", model_.COX);
    printf(">- VSB = %g V ", (Vs - Vb));
    printf("");
    printf("+ EXTERNAL BIAS ");
    printf("|");
    printf(">- VGB = %g V \t VGS = %g V", (Vg - Vb), ((Vg - Vb)-(Vs - Vb)));
    printf(">- VDB = %g V \t VDS = %g V", (Vd - Vb), ((Vd - Vb)-(Vs - Vb)));
    printf(">- VSB = %g V ", (Vs - Vb));
    printf("");
    printf("+ DEVICE GEOMETRY ");
    printf("|");
    printf(">- Leff = %g m \t Leffc = %g m ", Leff, Leffc);
    printf(">- Weff = %g m \t Weffc = %g m \t (finger)", Weff, Weffc);
    printf(">- Wtot = %g m \t NF    = %g m ", WeffNF, NF);
    printf(">");
    printf(">- Leff - deltaL = %g m \t (CHANNEL LENGTH MODULATION)", (Leff-deltal));
    printf(">- Weff - model_.WEDGE  = %g m \t (EDGE CONDUCTANCE)", (Weff-model_.WEDGE));
    printf(">- model_.WEDGE         = %g m ", model_.WEDGE);
    printf(">");
    printf(">- W/L           = %g ", ((Weff-model_.WEDGE)*NF/(Leff-deltal)));
    printf("");
    printf("+ THRESHOLD VOLTAGE ");
    printf("|");
    printf(">- VTO(dev,T) = %g V \t VTO(dev,TNOM) = %g V", VTO_DEV_t, VTO_DEV);
    printf(">");
    printf(">- model_.VTO        = %g V ", model_.VTO);
    printf(">- DVTO(RSCE) = %g V \t\t (REVERSE SHORT CHANNEL EFFECT)", DVTRSCE);
    printf(">- DVTO(INCE) = %g V \t\t (INVERSE NARROW CHANNEL EFFECT)", DVTINWE);
    printf(">- DVTO(STI)  = %g V \t\t (STI STRESS EFFECT)", DVTSTI);
    printf(">- DVTO(LONG) = %g V \t\t (LONG CHANNEL CORRECTION)", DVTLONG);
    printf(">- DVTO(WIDE) = %g V \t\t (WIDE CHANNEL CORRECTION)", DVTWIDE);
    printf(">- DVTO(NF)   = %g V \t\t (NF CORRECTION)", DVTNF);
    printf(">- DVTO(T)    = %g V \t\t (TEMPERATURE)", (VTO_DEV_t-VTO_DEV));
    printf(">");
    printf(">- VFB        = %g V ", (vfb*UT));
    printf("");
    printf("+ BODY EFFECT FACTOR ");
    printf("|");
    printf(">- GAMMA(dev)  = %g V^(1/2)", GAMMA_DEV);
    printf(">");
    printf(">- model_.GAMMA       = %g V^(1/2)", model_.GAMMA);
    printf(">- AGAMMA(RSCE)= %g   \t\t (REVERSE SHORT CHANNEL EFFECT)", GAMMA_RSCE);
    printf(">- AGAMMA(INCE)= %g   \t\t (INVERSE NARROW CHANNEL EFFECT)", GAMMA_INWE);
    printf(">- DGAMMA(STI) = %g V^(1/2) \t\t (STI STRESS EFFECT)", DGAMMASTI);
    printf(">- DGAMMA(LONG)= %g V^(1/2) \t\t (LONG CHANNEL CORRECTION)", DGAMMALONG);
    printf(">- DGAMMA(WIDE)= %g V^(1/2) \t\t (WIDE CHANNEL CORRECTION)", DGAMMAWIDE);
    printf(">");
    printf(">- GAMMAeff(CHSH) = %g V^(1/2) \t\t (CHARGE SHARING))", (gamma_b_chsh*UT));
    printf(">- GAMMAeff0(CHSH)= %g V^(1/2) \t\t (CHARGE SHARING, NO BIAS)", (gamma_b_chsh0*UT));
    printf(">- GAMMAeff       = %g V^(1/2) \t\t (ALL PHENOMENA, POLYSILICON DEPLETION)", (gamma_b_eff*UT));
    printf("");
    printf("+ FERMI POTENTIAL ");
    printf("|");
    printf(">- PHIF(dev,T)  = %g V \t PHIF(dev,TNOM) = %g V", PHIF_DEV_t, PHIF_DEV);
    printf(">");
    printf(">- model_.PHIF        = %g V", model_.PHIF);
    printf(">- DPHIF(RSCE) = %g V \t\t (REVERSE SHORT CHANNEL EFFECT)", DPHIF_RSCE);
    printf(">- DPHIF(T)    = %g V \t\t (TEMPERATURE)", (PHIF_DEV_t-PHIF_DEV));
    printf(">");
    printf(">- PHIF(dev,T)^(1/2) = %g V^(1/2)", (sqrt(PHIF_DEV_t)));
    printf(">- PHI(dev,T)  = %g V", (phi*UT));
    printf(">- DPSI(QM)    = %g V \t\t (QUANTUM MECHANICAL EFFECTS)", DPSI0);
    printf(">- VBI(dev,T)  = %g V", (vbi*UT));
    printf("");
    printf("+ MOBILITY RELATED EFFECTS ");
    printf("|");
    printf(">- MOB(dev,T)    = %g m^2/(V*s)", (beta/model_.COX));
    printf(">");
    printf(">- MOB(TNOM)     = %g m^2/(V*s)", (model_.KP/model_.COX));
    printf(">- AMOB(STI,TNOM)= %g ", kp_sti);
    printf(">- AMOB(STI,T)   = %g ", kp_sti_t);
    printf(">- AMOB(LENGTH_SCALING) = %g ", kpl);
    printf(">- AMOB(WIDTH_SCALING)  = %g ", kpw);
    printf(">- AMOB(T)       = %g ", (exp(model_.BEX*lnrT)));
    printf(">- AMOB(MRVF)    = %g \t\t (MOBILITY REDUCTION DUE TO VERTICAL FIELD)", (beta_nom/beta_denom));
    printf(">- AMOB(MRLF)    = %g \t\t (MOBILITY REDUCTION DUE TO LONGITUDINAL FIELD)", (1.0/beta_clm_denom));
    printf("");
    printf("+ QUANTUM MECHANICAL EFFECTS ");
    printf("|");
    printf(">- model_.AQMA = %g \t model_.AQMI = %g \t model_.ETAQM = %g", model_.AQMA, model_.AQMI, model_.ETAQM);
    printf(">");
    printf(">- 1/(1+delta_QMI) = %g ", inv_dqmip1);
    printf(">- DPSI            = %g V \t\t (FERMI POTENTIAL)", DPSI0);
    printf(">- DPSIV           = %g V \t\t (DVO ON CHARGE MODEL OF QB)", (dpsiv*UT));
    printf("");
    printf("+ SLOPE FACTOR ");
    printf("|");
    printf(">- nv  = %g ", nv);
    printf(">- nq  = %g ", nq);
    printf(">- nq0 = %g ", nq0);
    printf("");
    printf("+ PINCH-OFF SURFACE POTENTIAL AND VOLTAGE ");
    printf("|");
    printf(">- PSI_P   = %g V ", (psi_p*UT));
    printf(">- PSI_P0  = %g V ", (psi_p0*UT));
    printf(">");
    printf(">- PSI_PO  = %g V \t\t (APPROXIMATION AROUND PSI_P=0)", (psi_po*UT));
    printf(">- PSI_PO0 = %g V \t\t (APPROXIMATION AROUND PSI_P=0)", (psi_po0*UT));
    printf("|");
    printf(">- V_P         = %g V ", (vp*UT));
    printf(">- DPSI_S(DIBL)= %g V \t\t (DRAIN INDUCED BARRIER LOWERING)", (deltapsis*UT));
    printf(">- V_P(DIBL)   = %g V ", ((vp+deltapsis)*UT));
    printf("");
    printf("+ VELOCITY SATURATION ");
    printf("|");
    printf(">- model_.UCRIT  = %g V/m \t\t model_.LAMBDA = %g   \t\t model_.DELTA  = %g \t\t model_.ACLM = %g ", model_.UCRIT, model_.LAMBDA, model_.DELTA, model_.ACLM);
    printf(">- model_.UCEX   = %g     \t\t model_.WUCRIT = %g m \t\t model_.KUCRIT = %g ", model_.UCEX, model_.WUCRIT, model_.KUCRIT);
    printf(">- model_.TLAMBDA= %g     \t\t model_.WLAMBDA= %g m ", model_.TLAMBDA, model_.WLAMBDA);
    printf(">");
    printf(">- UCRIT(dev,T)  = %g V/m ", UCRIT_DEV_t);
    printf(">- LAMBDA(dev,T) = %g ", LAMBDA_gt);
    printf("|");
    printf(">- VDS_SAT       = %g V \t\t VDS    = %g V ", (vdssat*UT), ((vd-vs)*UT));
    printf(">- VD_PRIME      = %g V \t\t VD     = %g V ", (vdp*UT), (vd*UT));
    printf(">- DELTA_L       = %g m ", deltal);
    printf("");
    printf("+ NORMALIZED (LOCAL) INVERTED CHARGES");
    printf("|");
    printf(">- qs     = %g \t\t V_PS  = %g V ", qs, ((vp+deltapsis-vs)*UT));
    printf(">- qd     = %g \t\t V_PD  = %g V ", qdp, ((vp+deltapsis-vdp)*UT));
    printf("");
    printf("+ CHANNEL CURRENT");
    printf("|");
    printf(">- if     = %g ", if_);
    printf(">- irp    = %g ", irp);
    printf(">- i      = %g ", i);
    printf(">");
    printf(">- Ispec  = %g A [2*nq*(UT^2)*beta*(W/L)*(1/(1+delta_QMI))]", Ispec);
    printf(">");
    printf(">- nq              = %g ", nq);
    printf(">- beta            = %g A*V^(-2) ", beta);
    printf(">- W/L             = %g ", ((Weff-model_.WEDGE)*NF/(Leff-deltal)));
    printf(">- 1/(1+delta_QMI) = %g ", inv_dqmip1);
    printf(">- 2*UT^2          = %g V^2 ", UT2+UT2);
    printf(">");
    printf(">- DITS            = %g ", dits_factor);
    printf(">");
    printf(">- #### IDS ####   = %g A", IDS);
    printf("");
    printf("+ CHARGES ");
    printf("|");
    printf(">- qS = %g \t\t qD = %g \t\t qI = %g ", qS, qD, qI);
    printf(">- qG = %g \t\t qB = %g ", qG, qB);
    printf(">");
    printf(">- Qspec           = %g Cb [-UT*Wc*Lc*COX*(1/(1+delta_QMI))]", Q0);
    printf(">");
    printf(">- model_.COX             = %g F*m^(-2)", model_.COX);
    printf(">- Wc*Lc           = %g m^2", (Weffc*NF*Leffc*(Weff-model_.WEDGE)/Weff));
    printf(">- 1/(1+delta_QMI) = %g ", inv_dqmip1);
    printf(">- UT              = %g V ", UT);
    printf(">");
    printf(">- ## QS ## = %g Cb ", QS);
    printf(">- ## QD ## = %g Cb ", QD);
    printf(">- ## QG ## = %g Cb ", QG);
    printf(">- ## QB ## = %g Cb ", QB);
    printf("");
    printf("+ EDGE CONDUCTION ");
    printf("|");
    printf(">- Ispec_edge = %g A ", Ispec_edge);
    printf(">- Q0_edge    = %g Cb ", Q0_edge);
    printf(">");
    printf(">- DELTA_GAMMA_EDGE_eff = %g V^(1/2) ", (dgamma_edge*sqrtUT));
    printf(">- DELTA_PHI_EDGE_eff   = %g V  ", (dphi_edge*UT));
    printf(">");
    printf(">- DELTA_V_P_EDGE_eff   = %g V  ", (dvp_edge*UT));
    printf(">");
    printf(">- qs_edge= %g \t\t V_PS_edge  = %g V ", qs_edge, ((vp+dvp_edge+deltapsis-vs)*UT));
    printf(">- qd_edge= %g \t\t V_PD_edge  = %g V ", qdp_edge, ((vp+dvp_edge+deltapsis-vdp)*UT));
    printf(">");
    printf(">- ids_edge= %g ", ids_edge);
    printf(">");
    printf(">- DITS            = %g ", dits_factor);
    printf(">");
    printf(">- ### IDS_edge ### = A %g ", IDS_edge);
    printf(">");
    printf(">- PSI_P_edge            = %g V", (psi_p_edge*UT));
    printf(">- GAMMA_eff_edge(CHSH)  = %g V^(1/2)", (gamma_b_chsh_edge*sqrtUT));
    printf(">- nq_edge               = %g ", nq_edge);
    printf(">");
    printf(">- qS_edge= %g \t\t QS_edge  = %g Cb ", qS_edge, QS_edge);
    printf(">- qD_edge= %g \t\t QD_edge  = %g Cb ", qD_edge, QD_edge);
    printf(">- qG_edge= %g \t\t QG_edge  = %g Cb ", qG_edge, QG_edge);
    printf(">- qB_edge= %g \t\t QB_edge  = %g Cb ", qB_edge, QB_edge);
    printf("");
    printf("+ OVERLAP ");
    printf("|");
    printf(">- qSOV    = %g ", dpsiox_s);
    printf(">- qDOV    = %g ", dpsiox_d);
    printf(">");
    printf(">- Q0OV    = %g Cb ", (-Q0OV));
    printf(">");
    printf(">- Wc*L(OV)= %g m^2 ", (Weffc*NF*model_.LOV));
    printf(">");
    printf(">- QSOV    = %g Cb ", QSOV);
    printf(">- QDOV    = %g Cb ", QDOV);
    printf("");
    printf("+ FRINGING ");
    printf("|");
    printf(">- QSFR    = %g Cb", QSFR);
    printf(">- QDFR    = %g Cb", QDFR);
    printf("");
    printf("+ GIDL / GISL ");
    printf("|");
    printf(">- IGISL    = %g A", IGISL);
    printf(">- IGIDL    = %g A", IGIDL);
    printf("");
    printf("+ GATE CURRENT ");
    printf("|");
    printf(">- IG    = %g A \t\t [IG=IGS+IGD]", IG);
    printf(">- IGS   = %g A", IGS);
    printf(">- IGD   = %g A", IGD);
    printf(">- IGB   = %g A", IGB);
    printf(">");
    printf(">- IGSOV = %g A ", IGSOV);
    printf(">- IGDOV = %g A ", IGDOV);
    printf("");
    printf("+ IMPACT IONIZATION CURRENT ");
    printf("|");
    printf(">- IDB   = %g A ", IDB);
    printf("");
    printf("+ NOISE ");
    printf("|");
    printf(">- THERMAL NOISE \t\t (model_.TH_NOI = %g)", model_.TH_NOI);
    printf(">- gn      = %g \t\t (NORMALIZED EQUIVALENT CHANNEL NOISE RESISTANCE)", gn);
    printf(">- thermal = %g (PSD) \t\t (THERMAL NOISE) ", thermal);
    printf(">");
    printf(">- FLICKER NOISE");
    printf(">- gmg     = %g \t\t ", gmg);
    printf(">- flicker = %g (PSD) \t\t (FLICKER NOISE AT 1Hz) ", flicker);
    printf(">");
    printf(">- NON-QUASI-STATIC NOISE \t\t (model_.NQS_NOI = %g)", model_.NQS_NOI);
    printf(">- Sn(id,id)     = %g (PSD) ", (snspec*snidid));
    printf(">- Sn(ig,ig)     = %g * OMEGA^2   (PSD) ", (snspec*snigig));
    printf(">- Sn(ig,id)     = %g * j * OMEGA (PSD) ", (snspec*snigid));
    printf(">- C(ig,id)      = %g * j         (PSD) ", c_igid);
    printf(">- Sn(ib,ib)     = %g * OMEGA^2   (PSD) ", (snspec*snibib));
    printf(">");
    printf(">- GATE SHOT AND FLICKER NOISE ");
    printf(">- Sig(shot)        = %g (PSD) ", sig_shot);
    printf(">- Sig(flicker,1Hz) = %g (PSD) ", sig_flicker);
    printf("");
    printf("+ EXTRINSIC DIODES ");
    printf("|");
    printf(">- AREA      (SOURCE-SIDE) = %g m^2", as);
    printf(">- PERIMETER (SOURCE-SIDE) = %g m", ps);
    printf(">- GATE-SIDE (SOURCE-SIDE) = %g m", WeffNF);
    printf(">- AREA      (DRAIN-SIDE)  = %g m^2", ad);
    printf(">- PERIMETER (DRAIN-SIDE)  = %g m", pd);
    printf(">- GATE-SIDE (DRAIN-SIDE)  = %g m", WeffNF);
    printf(">");
    printf(">- IS_S   = %g A ", is_s);
    printf(">- IS_D   = %g A ", is_d);
    printf(">");
    printf(">- ISB_TUN = %g A", isb_tun);
    printf(">- IDB_TUN = %g A", idb_tun);
    printf(">");
    printf(">- ISBJ    = %g A", ISBJ);
    printf(">- IDBJ    = %g A", IDBJ);
    printf(">");
    printf(">- CSBJ    = %g F \t\t QSBJ    = %g Cb", CSBJ, QSBJ);
    printf(">- CDBJ    = %g F \t\t QDBJ    = %g Cb", CDBJ, QDBJ);
    printf("");
    printf("+ EXTRINSIC RESISTORS ");
    printf("|");
    printf(">- RS     = %g Ohm \t\t NOISE = %g (PSD)", rs, (4.0*(1.3807E-23)*thermocrasia/rs));
    printf(">- RD     = %g Ohm \t\t NOISE = %g (PSD)", rd, (4.0*(1.3807E-23)*thermocrasia/rd));
    printf("");
    printf("+ EXTRINSIC BIAS INDEPENDENT CAPACITORS ");
    printf("|");
    printf(">- CGS      = %g F ", (model_.CGSO*WeffNF));
    printf(">- CGD      = %g F ", (model_.CGDO*WeffNF));
    printf(">- CGB      = %g F ", (model_.CGBO*2.0*Leff*NF));
    printf("");
    printf("");
    printf("########################################");
    printf("#                                      #");
    printf("# END OF INFORMATION                   #");
    printf("#                                      #");
    printf("########################################");
    }
    } else {
    }
    file = 0;
    file_info = 0;
}

bool Instance::updateIntermediateVars_Jac()
{
    double _der0 = 1.0;
    double DdtExp0, DdtExp1, DdtExp2, DdtExp3, DdtExp4, DdtExp5, DdtExp6, DdtExp7, DdtExp8, DdtExp9, DdtExp10, DdtExp11, DdtExp12, DdtExp13, DdtExp14, DdtExp15, DdtExp16, DdtExp17, DdtExp18, DdtExp19, DdtExp20, DdtExp21, DdtExp22, DdtExp23;
    double DdtAns0, DdtAns1, DdtAns2, DdtAns3, DdtAns4, DdtAns5, DdtAns6, DdtAns7, DdtAns8, DdtAns9, DdtAns10, DdtAns11, DdtAns12, DdtAns13, DdtAns14, DdtAns15, DdtAns16, DdtAns17, DdtAns18, DdtAns19, DdtAns20, DdtAns21, DdtAns22, DdtAns23;
    double Vb =  (extData.nextSolVectorRawPtr)[b];
    double dVbDv3 = 1.;
    double Vd =  (extData.nextSolVectorRawPtr)[d];
    double dVdDv0 = 1.;
    double Vdi =  (extData.nextSolVectorRawPtr)[di];
    double dVdiDv4 = 1.;
    double Vg =  (extData.nextSolVectorRawPtr)[g];
    double dVgDv1 = 1.;
    double Vnoi =  (extData.nextSolVectorRawPtr)[noi];
    double dVnoiDv6 = 1.;
    double Vs =  (extData.nextSolVectorRawPtr)[s];
    double dVsDv2 = 1.;
    double Vsi =  (extData.nextSolVectorRawPtr)[si];
    double dVsiDv5 = 1.;
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
    double dCDBJDv3, dCDBJDv4, dCSBJDv3, dCSBJDv5, dDdtAns0Dv3;
    double dDdtAns0Dv4, dDdtAns10Dv1, dDdtAns10Dv3, dDdtAns10Dv4, dDdtAns10Dv5;
    double dDdtAns11Dv1, dDdtAns11Dv3, dDdtAns11Dv4, dDdtAns11Dv5, dDdtAns12Dv1;
    double dDdtAns12Dv3, dDdtAns12Dv4, dDdtAns12Dv5, dDdtAns13Dv1, dDdtAns13Dv3;
    double dDdtAns13Dv4, dDdtAns13Dv5, dDdtAns14Dv1, dDdtAns14Dv3, dDdtAns14Dv4;
    double dDdtAns14Dv5, dDdtAns15Dv1, dDdtAns15Dv3, dDdtAns15Dv4, dDdtAns15Dv5;
    double dDdtAns16Dv1, dDdtAns16Dv3, dDdtAns16Dv4, dDdtAns16Dv5, dDdtAns17Dv1;
    double dDdtAns17Dv3, dDdtAns17Dv4, dDdtAns17Dv5, dDdtAns18Dv1, dDdtAns18Dv3;
    double dDdtAns18Dv4, dDdtAns18Dv5, dDdtAns18Dv6, dDdtAns19Dv1, dDdtAns19Dv3;
    double dDdtAns19Dv4, dDdtAns19Dv5, dDdtAns1Dv3, dDdtAns1Dv5, dDdtAns20Dv1;
    double dDdtAns20Dv3, dDdtAns20Dv4, dDdtAns20Dv5, dDdtAns21Dv1, dDdtAns21Dv3;
    double dDdtAns21Dv4, dDdtAns21Dv5, dDdtAns22Dv1, dDdtAns22Dv3, dDdtAns22Dv4;
    double dDdtAns22Dv5, dDdtAns23Dv1, dDdtAns23Dv3, dDdtAns23Dv4, dDdtAns23Dv5;
    double dDdtAns2Dv1, dDdtAns2Dv5, dDdtAns3Dv1, dDdtAns3Dv4, dDdtAns4Dv1;
    double dDdtAns4Dv3, dDdtAns5Dv1, dDdtAns5Dv3, dDdtAns5Dv4, dDdtAns5Dv5;
    double dDdtAns6Dv1, dDdtAns6Dv3, dDdtAns6Dv4, dDdtAns6Dv5, dDdtAns7Dv1;
    double dDdtAns7Dv3, dDdtAns7Dv4, dDdtAns7Dv5, dDdtAns8Dv1, dDdtAns8Dv3;
    double dDdtAns8Dv4, dDdtAns8Dv5, dDdtAns9Dv1, dDdtAns9Dv3, dDdtAns9Dv4;
    double dDdtAns9Dv5, dDdtExp0Dv3, dDdtExp0Dv4, dDdtExp10Dv1, dDdtExp10Dv3;
    double dDdtExp10Dv4, dDdtExp10Dv5, dDdtExp11Dv1, dDdtExp11Dv3, dDdtExp11Dv4;
    double dDdtExp11Dv5, dDdtExp12Dv1, dDdtExp12Dv3, dDdtExp12Dv4, dDdtExp12Dv5;
    double dDdtExp13Dv1, dDdtExp13Dv3, dDdtExp13Dv4, dDdtExp13Dv5, dDdtExp14Dv1;
    double dDdtExp14Dv3, dDdtExp14Dv4, dDdtExp14Dv5, dDdtExp15Dv1, dDdtExp15Dv3;
    double dDdtExp15Dv4, dDdtExp15Dv5, dDdtExp16Dv1, dDdtExp16Dv3, dDdtExp16Dv4;
    double dDdtExp16Dv5, dDdtExp17Dv1, dDdtExp17Dv3, dDdtExp17Dv4, dDdtExp17Dv5;
    double dDdtExp18Dv1, dDdtExp18Dv3, dDdtExp18Dv4, dDdtExp18Dv5, dDdtExp18Dv6;
    double dDdtExp19Dv1, dDdtExp19Dv3, dDdtExp19Dv4, dDdtExp19Dv5, dDdtExp1Dv3;
    double dDdtExp1Dv5, dDdtExp20Dv1, dDdtExp20Dv3, dDdtExp20Dv4, dDdtExp20Dv5;
    double dDdtExp21Dv1, dDdtExp21Dv3, dDdtExp21Dv4, dDdtExp21Dv5, dDdtExp22Dv1;
    double dDdtExp22Dv3, dDdtExp22Dv4, dDdtExp22Dv5, dDdtExp23Dv1, dDdtExp23Dv3;
    double dDdtExp23Dv4, dDdtExp23Dv5, dDdtExp2Dv1, dDdtExp2Dv5, dDdtExp3Dv1;
    double dDdtExp3Dv4, dDdtExp4Dv1, dDdtExp4Dv3, dDdtExp5Dv1, dDdtExp5Dv3;
    double dDdtExp5Dv4, dDdtExp5Dv5, dDdtExp6Dv1, dDdtExp6Dv3, dDdtExp6Dv4;
    double dDdtExp6Dv5, dDdtExp7Dv1, dDdtExp7Dv3, dDdtExp7Dv4, dDdtExp7Dv5;
    double dDdtExp8Dv1, dDdtExp8Dv3, dDdtExp8Dv4, dDdtExp8Dv5, dDdtExp9Dv1;
    double dDdtExp9Dv3, dDdtExp9Dv4, dDdtExp9Dv5, dIDBDv1, dIDBDv3;
    double dIDBDv4, dIDBDv5, dIDBJDv3, dIDBJDv4, dIDSDv1;
    double dIDSDv3, dIDSDv4, dIDSDv5, dIDS_edgeDv1, dIDS_edgeDv3;
    double dIDS_edgeDv4, dIDS_edgeDv5, dIGBDv1, dIGBDv3, dIGBDv4;
    double dIGBDv5, dIGDDv1, dIGDDv3, dIGDDv4, dIGDDv5;
    double dIGDOVDv1, dIGDOVDv3, dIGDOVDv4, dIGDOVDv5, dIGDv1;
    double dIGDv3, dIGDv4, dIGDv5, dIGIDLDv1, dIGIDLDv3;
    double dIGIDLDv4, dIGIDLDv5, dIGISLDv1, dIGISLDv3, dIGISLDv4;
    double dIGISLDv5, dIGSDv1, dIGSDv3, dIGSDv4, dIGSDv5;
    double dIGSOVDv1, dIGSOVDv3, dIGSOVDv4, dIGSOVDv5, dISBJDv3;
    double dISBJDv5, dIspecDv1, dIspecDv3, dIspecDv4, dIspecDv5;
    double dIspec_edgeDv1, dIspec_edgeDv3, dIspec_edgeDv4, dIspec_edgeDv5, dOMEGADv1;
    double dOMEGADv3, dOMEGADv4, dOMEGADv5, dQBDv1, dQBDv3;
    double dQBDv4, dQBDv5, dQB_edgeDv1, dQB_edgeDv3, dQB_edgeDv4;
    double dQB_edgeDv5, dQDBJDv3, dQDBJDv4, dQDDv1, dQDDv3;
    double dQDDv4, dQDDv5, dQDFRDv1, dQDFRDv3, dQDFRDv4;
    double dQDFRDv5, dQDOVDv1, dQDOVDv3, dQDOVDv4, dQDOVDv5;
    double dQD_edgeDv1, dQD_edgeDv3, dQD_edgeDv4, dQD_edgeDv5, dQGDv1;
    double dQGDv3, dQGDv4, dQGDv5, dQG_edgeDv1, dQG_edgeDv3;
    double dQG_edgeDv4, dQG_edgeDv5, dQSBJDv3, dQSBJDv5, dQSDv1;
    double dQSDv3, dQSDv4, dQSDv5, dQSFRDv1, dQSFRDv3;
    double dQSFRDv4, dQSFRDv5, dQSOVDv1, dQSOVDv3, dQSOVDv4;
    double dQSOVDv5, dQS_edgeDv1, dQS_edgeDv3, dQS_edgeDv4, dQS_edgeDv5;
    double dVDDv3, dVDDv4, dVGDv1, dVGDv3, dVSDv3;
    double dVSDv5, da4_dovDv1, da4_dovDv3, da4_dovDv4, da4_dovDv5;
    double da4_sovDv1, da4_sovDv3, da4_sovDv4, da4_sovDv5, da_gcDv1;
    double da_gcDv3, da_gcDv4, da_gcDv5, darg_dDv3, darg_dDv4;
    double darg_sDv3, darg_sDv5, db_gcDv1, db_gcDv3, db_gcDv4;
    double db_gcDv5, dbetaDv1, dbetaDv3, dbetaDv4, dbetaDv5;
    double dbeta_clm_denomDv1, dbeta_clm_denomDv3, dbeta_clm_denomDv4, dbeta_clm_denomDv5, dbeta_coulDv1;
    double dbeta_coulDv3, dbeta_coulDv4, dbeta_coulDv5, dbeta_denomDv1, dbeta_denomDv3;
    double dbeta_denomDv4, dbeta_denomDv5, dbeta_nomDv3, dbeta_nomDv4, dbeta_nomDv5;
    double dc_igidDv1, dc_igidDv3, dc_igidDv4, dc_igidDv5, dchsh_a1Dv3;
    double dchsh_a1Dv4, dchsh_a1Dv5, dchsh_a2Dv3, dchsh_a2Dv4, dchsh_a2Dv5;
    double dchsh_a3Dv3, dchsh_a3Dv4, dchsh_a3Dv5, dcsb_dDv3, dcsb_dDv4;
    double dcsb_sDv3, dcsb_sDv5, dcssw_dDv3, dcssw_dDv4, dcssw_sDv3;
    double dcssw_sDv5, dcsswg_dDv3, dcsswg_dDv4, dcsswg_sDv3, dcsswg_sDv5;
    double dd_psi_dqDv1, dd_psi_dqDv3, dd_psi_dqDv4, dd_psi_dqDv5, ddeltalDv1;
    double ddeltalDv3, ddeltalDv4, ddeltalDv5, ddeltapsisDv1, ddeltapsisDv3;
    double ddeltapsisDv4, ddeltapsisDv5, ddits_factorDv1, ddits_factorDv3, ddits_factorDv4;
    double ddits_factorDv5, ddpsigd0Dv1, ddpsigd0Dv3, ddpsigd0Dv4, ddpsigd0Dv5;
    double ddpsigdDv1, ddpsigdDv3, ddpsigdDv4, ddpsigdDv5, ddpsigs0Dv1;
    double ddpsigs0Dv3, ddpsigs0Dv4, ddpsigs0Dv5, ddpsigsDv1, ddpsigsDv3;
    double ddpsigsDv4, ddpsigsDv5, ddpsiox_dDv1, ddpsiox_dDv3, ddpsiox_dDv4;
    double ddpsiox_dDv5, ddpsiox_sDv1, ddpsiox_sDv3, ddpsiox_sDv4, ddpsiox_sDv5;
    double ddpsivDv1, ddpsivDv3, ddpsivDv4, ddpsivDv5, ddq_dksiDv1;
    double ddq_dksiDv3, ddq_dksiDv4, ddq_dksiDv5, ddv_clmDv1, ddv_clmDv3;
    double ddv_clmDv4, ddv_clmDv5, ddv_diblDv1, ddv_diblDv3, ddv_diblDv4;
    double ddv_diblDv5, ddvp_edgeDv1, ddvp_edgeDv3, ddvp_edgeDv4, ddvp_edgeDv5;
    double de_clmx2xqsDv1, de_clmx2xqsDv3, de_clmx2xqsDv4, de_clmx2xqsDv5, depsilonDv1;
    double depsilonDv3, depsilonDv4, depsilonDv5, deq1Dv1, deq1Dv3;
    double deq1Dv4, deq1Dv5, deqDv1, deqDv3, deqDv4;
    double deqDv5, df_breakdown_dDv3, df_breakdown_dDv4, df_breakdown_sDv3, df_breakdown_sDv5;
    double df_ditsDv1, df_ditsDv3, df_ditsDv4, df_ditsDv5, dgamma_b_chsh2Dv3;
    double dgamma_b_chsh2Dv4, dgamma_b_chsh2Dv5, dgamma_b_chshDv3, dgamma_b_chshDv4, dgamma_b_chshDv5;
    double dgamma_b_chsh_edgeDv3, dgamma_b_chsh_edgeDv4, dgamma_b_chsh_edgeDv5, dgamma_b_eff2Dv3, dgamma_b_eff2Dv4;
    double dgamma_b_eff2Dv5, dgamma_b_effDv3, dgamma_b_effDv4, dgamma_b_effDv5, dgamma_dep2_dovDv1;
    double dgamma_dep2_dovDv3, dgamma_dep2_dovDv4, dgamma_dep2_dovDv5, dgamma_dep2_sovDv1, dgamma_dep2_sovDv3;
    double dgamma_dep2_sovDv4, dgamma_dep2_sovDv5, dgmgDv1, dgmgDv3, dgmgDv4;
    double dgmgDv5, dgnDv1, dgnDv3, dgnDv4, dgnDv5;
    double dgpnuDv1, dgpnuDv3, dgpnuDv4, dgpnuDv5, di0Dv1;
    double di0Dv3, di0Dv4, di0Dv5, diDv1, diDv3;
    double diDv4, diDv5, didb_tunDv3, didb_tunDv4, dids_edgeDv1;
    double dids_edgeDv3, dids_edgeDv4, dids_edgeDv5, dif_Dv1, dif_Dv3;
    double dif_Dv4, dif_Dv5, digoDv1, digoDv3, digoDv4;
    double digoDv5, dirpDv1, dirpDv3, dirpDv4, dirpDv5;
    double disb_tunDv3, disb_tunDv5, dk12Dv1, dk12Dv3, dk12Dv4;
    double dk12Dv5, dk12_2Dv1, dk12_2Dv3, dk12_2Dv4, dk12_2Dv5;
    double dk12_3Dv1, dk12_3Dv3, dk12_3Dv4, dk12_3Dv5, dk1Dv1;
    double dk1Dv3, dk1Dv4, dk1Dv5, dk2Dv1, dk2Dv3;
    double dk2Dv4, dk2Dv5, dln_z1_Dv1, dln_z1_Dv3, dln_z1_Dv4;
    double dln_z1_Dv5, dnigcDv1, dnigcDv3, dnigcDv4, dnigcDv5;
    double dnigdDv1, dnigdDv3, dnigdDv4, dnigdDv5, dnigsDv1;
    double dnigsDv3, dnigsDv4, dnigsDv5, dnoise_bDv1, dnoise_bDv3;
    double dnoise_bDv4, dnoise_bDv5, dnoise_ds1Dv1, dnoise_ds1Dv3, dnoise_ds1Dv4;
    double dnoise_ds1Dv5, dnoise_ds2Dv1, dnoise_ds2Dv3, dnoise_ds2Dv4, dnoise_ds2Dv5;
    double dnoise_gDv1, dnoise_gDv3, dnoise_gDv4, dnoise_gDv5, dnqDv1;
    double dnqDv3, dnqDv4, dnqDv5, dnq_edgeDv1, dnq_edgeDv3;
    double dnq_edgeDv4, dnq_edgeDv5, dnuDv1, dnuDv3, dnuDv4;
    double dnuDv5, dnvDv1, dnvDv3, dnvDv4, dnvDv5;
    double domegaspecDv1, domegaspecDv3, domegaspecDv4, domegaspecDv5, dp_tunDv1;
    double dp_tunDv3, dp_tunDv4, dp_tunDv5, dp_tun_dovDv1, dp_tun_dovDv3;
    double dp_tun_dovDv4, dp_tun_dovDv5, dp_tun_sovDv1, dp_tun_sovDv3, dp_tun_sovDv4;
    double dp_tun_sovDv5, dpowqs_qdp2Dv1, dpowqs_qdp2Dv3, dpowqs_qdp2Dv4, dpowqs_qdp2Dv5;
    double dpowqs_qdp2_edgeDv1, dpowqs_qdp2_edgeDv3, dpowqs_qdp2_edgeDv4, dpowqs_qdp2_edgeDv5, dpowqsqdpp1_2Dv1;
    double dpowqsqdpp1_2Dv3, dpowqsqdpp1_2Dv4, dpowqsqdpp1_2Dv5, dpowqsqdpp1_2_edgeDv1, dpowqsqdpp1_2_edgeDv3;
    double dpowqsqdpp1_2_edgeDv4, dpowqsqdpp1_2_edgeDv5, dpsi_oxDv1, dpsi_oxDv3, dpsi_oxDv4;
    double dpsi_oxDv5, dpsi_oxr_ov_dDv1, dpsi_oxr_ov_dDv3, dpsi_oxr_ov_dDv4, dpsi_oxr_ov_dDv5;
    double dpsi_oxr_ov_sDv1, dpsi_oxr_ov_sDv3, dpsi_oxr_ov_sDv4, dpsi_oxr_ov_sDv5, dpsi_p0Dv1;
    double dpsi_p0Dv3, dpsi_pDv1, dpsi_pDv3, dpsi_pDv4, dpsi_pDv5;
    double dpsi_p_edgeDv1, dpsi_p_edgeDv3, dpsi_p_edgeDv4, dpsi_p_edgeDv5, dpsi_p_tmpDv1;
    double dpsi_p_tmpDv3, dpsi_p_tmpDv4, dpsi_p_tmpDv5, dpsi_po0Dv1, dpsi_po0Dv3;
    double dpsi_poDv1, dpsi_poDv3, dpsi_poDv4, dpsi_poDv5, dpsi_sa_tmpDv1;
    double dpsi_sa_tmpDv3, dpsi_sa_tmpDv4, dpsi_sa_tmpDv5, dpsi_xDv1, dpsi_xDv3;
    double dpsi_xDv4, dpsi_xDv5, dpsi_xr_ov_dDv1, dpsi_xr_ov_dDv3, dpsi_xr_ov_dDv4;
    double dpsi_xr_ov_dDv5, dpsi_xr_ov_sDv1, dpsi_xr_ov_sDv3, dpsi_xr_ov_sDv4, dpsi_xr_ov_sDv5;
    double dqBDv1, dqBDv3, dqBDv4, dqBDv5, dqB_edgeDv1;
    double dqB_edgeDv3, dqB_edgeDv4, dqB_edgeDv5, dqDDv1, dqDDv3;
    double dqDDv4, dqDDv5, dqD_edgeDv1, dqD_edgeDv3, dqD_edgeDv4;
    double dqD_edgeDv5, dqGDv1, dqGDv3, dqGDv4, dqGDv5;
    double dqG_edgeDv1, dqG_edgeDv3, dqG_edgeDv4, dqG_edgeDv5, dqIDv1;
    double dqIDv3, dqIDv4, dqIDv5, dqI_edgeDv1, dqI_edgeDv3;
    double dqI_edgeDv4, dqI_edgeDv5, dqSDv1, dqSDv3, dqSDv4;
    double dqSDv5, dqS_edgeDv1, dqS_edgeDv3, dqS_edgeDv4, dqS_edgeDv5;
    double dqboDv1, dqboDv3, dqboDv4, dqboDv5, dqdp2Dv1;
    double dqdp2Dv3, dqdp2Dv4, dqdp2Dv5, dqdpDv1, dqdpDv3;
    double dqdpDv4, dqdpDv5, dqdp_edgeDv1, dqdp_edgeDv3, dqdp_edgeDv4;
    double dqdp_edgeDv5, dqr1Dv3, dqr1Dv4, dqr1Dv5, dqs2Dv1;
    double dqs2Dv3, dqs2Dv4, dqs2Dv5, dqsDv1, dqsDv3;
    double dqsDv4, dqsDv5, dqs_edgeDv1, dqs_edgeDv3, dqs_edgeDv4;
    double dqs_edgeDv5, dqs_qdpDv1, dqs_qdpDv3, dqs_qdpDv4, dqs_qdpDv5;
    double dqs_qdp_edgeDv1, dqs_qdp_edgeDv3, dqs_qdp_edgeDv4, dqs_qdp_edgeDv5, dqs_qsat2Dv1;
    double dqs_qsat2Dv3, dqs_qsat2Dv4, dqs_qsat2Dv5, dqs_qsatDv1, dqs_qsatDv3;
    double dqs_qsatDv4, dqs_qsatDv5, dqsatDv1, dqsatDv3, dqsatDv4;
    double dqsatDv5, dqsb_dDv3, dqsb_dDv4, dqsb_sDv3, dqsb_sDv5;
    double dqsqdpDv1, dqsqdpDv3, dqsqdpDv4, dqsqdpDv5, dqsqdp_edgeDv1;
    double dqsqdp_edgeDv3, dqsqdp_edgeDv4, dqsqdp_edgeDv5, dqsqdpp1Dv1, dqsqdpp1Dv3;
    double dqsqdpp1Dv4, dqsqdpp1Dv5, dqsqdpp1_edgeDv1, dqsqdpp1_edgeDv3, dqsqdpp1_edgeDv4;
    double dqsqdpp1_edgeDv5, dqssw_dDv3, dqssw_dDv4, dqssw_sDv3, dqssw_sDv5;
    double dqsswg_dDv3, dqsswg_dDv4, dqsswg_sDv3, dqsswg_sDv5, ds1_pxDv1;
    double ds1_pxDv3, ds1_pxDv4, ds1_pxDv5, dsif2Dv1, dsif2Dv3;
    double dsif2Dv4, dsif2Dv5, dsifDv1, dsifDv3, dsifDv4;
    double dsifDv5, dsig_flickerDv1, dsig_flickerDv3, dsig_flickerDv4, dsig_flickerDv5;
    double dsig_shotDv1, dsig_shotDv3, dsig_shotDv4, dsig_shotDv5, dsirp2Dv1;
    double dsirp2Dv3, dsirp2Dv4, dsirp2Dv5, dsirpDv1, dsirpDv3;
    double dsirpDv4, dsirpDv5, dsnibibDv1, dsnibibDv3, dsnibibDv4;
    double dsnibibDv5, dsnididDv1, dsnididDv3, dsnididDv4, dsnididDv5;
    double dsnigidDv1, dsnigidDv3, dsnigidDv4, dsnigidDv5, dsnigigDv1;
    double dsnigigDv3, dsnigigDv4, dsnigigDv5, dsnspecDv1, dsnspecDv3;
    double dsnspecDv4, dsnspecDv5, dsqrt_psi_p0Dv1, dsqrt_psi_p0Dv3, dsqrt_psi_pDv1;
    double dsqrt_psi_pDv3, dsqrt_psi_pDv4, dsqrt_psi_pDv5, dsqrt_psi_p_edgeDv1, dsqrt_psi_p_edgeDv3;
    double dsqrt_psi_p_edgeDv4, dsqrt_psi_p_edgeDv5, dsqrt_psi_saDv1, dsqrt_psi_saDv3, dsqrt_psi_saDv4;
    double dsqrt_psi_saDv5, dthermalDv1, dthermalDv3, dthermalDv4, dthermalDv5;
    double dtmp1Dv1, dtmp1Dv3, dtmp1Dv4, dtmp1Dv5, dtmp2Dv1;
    double dtmp2Dv3, dtmp2Dv4, dtmp2Dv5, dtmpDv1, dtmpDv3;
    double dtmpDv4, dtmpDv5, du_clmDv1, du_clmDv3, du_clmDv4;
    double du_clmDv5, dv0_dovDv1, dv0_dovDv3, dv0_dovDv4, dv0_dovDv5;
    double dv0_sovDv1, dv0_sovDv3, dv0_sovDv4, dv0_sovDv5, dv1_dovDv1;
    double dv1_dovDv3, dv1_dovDv4, dv1_dovDv5, dv1_igDv1, dv1_igDv3;
    double dv1_igDv4, dv1_igDv5, dv1_qgDv1, dv1_qgDv3, dv1_qgDv4;
    double dv1_qgDv5, dv1_sovDv1, dv1_sovDv3, dv1_sovDv4, dv1_sovDv5;
    double dv2_dovDv1, dv2_dovDv3, dv2_dovDv4, dv2_dovDv5, dv2_igDv1;
    double dv2_igDv3, dv2_igDv4, dv2_igDv5, dv2_qgDv1, dv2_qgDv3;
    double dv2_qgDv4, dv2_qgDv5, dv2_sovDv1, dv2_sovDv3, dv2_sovDv4;
    double dv2_sovDv5, dv2b_dovDv1, dv2b_dovDv3, dv2b_dovDv4, dv2b_dovDv5;
    double dv2b_sovDv1, dv2b_sovDv3, dv2b_sovDv4, dv2b_sovDv5, dv3_dovDv1;
    double dv3_dovDv3, dv3_dovDv4, dv3_dovDv5, dv3_sovDv1, dv3_sovDv3;
    double dv3_sovDv4, dv3_sovDv5, dv_di_bDv3, dv_di_bDv4, dv_ibDv1;
    double dv_ibDv3, dv_ibDv4, dv_ibDv5, dv_oDv1, dv_oDv3;
    double dv_oDv4, dv_oDv5, dv_si_bDv3, dv_si_bDv5, dva_ditsDv1;
    double dva_ditsDv3, dva_ditsDv4, dva_ditsDv5, dvdDv3, dvdDv4;
    double dvdDv5, dvdpDv1, dvdpDv3, dvdpDv4, dvdpDv5;
    double dvdp_tmp1Dv1, dvdp_tmp1Dv3, dvdp_tmp1Dv4, dvdp_tmp1Dv5, dvdp_tmp2Dv1;
    double dvdp_tmp2Dv3, dvdp_tmp2Dv4, dvdp_tmp2Dv5, dvdp_tmp3Dv1, dvdp_tmp3Dv3;
    double dvdp_tmp3Dv4, dvdp_tmp3Dv5, dvdsatDv1, dvdsatDv3, dvdsatDv4;
    double dvdsatDv5, dvdsat_tmp11Dv1, dvdsat_tmp11Dv3, dvdsat_tmp11Dv4, dvdsat_tmp11Dv5;
    double dvdsat_tmp1Dv1, dvdsat_tmp1Dv3, dvdsat_tmp1Dv4, dvdsat_tmp1Dv5, dvdsat_tmp2Dv1;
    double dvdsat_tmp2Dv3, dvdsat_tmp2Dv4, dvdsat_tmp2Dv5, dvdseffDv1, dvdseffDv3;
    double dvdseffDv4, dvdseffDv5, dvdssatDv1, dvdssatDv3, dvdssatDv4;
    double dvdssatDv5, dvgDv1, dvgDv3, dvg_pDv1, dvg_pDv3;
    double dvg_p_chshDv1, dvg_p_chshDv3, dvg_p_chsh_pd0Dv1, dvg_p_chsh_pd0Dv3, dvg_p_chsh_pdDv1;
    double dvg_p_chsh_pdDv3, dvg_p_chsh_pdDv4, dvg_p_chsh_pdDv5, dvgdeDv1, dvgdeDv3;
    double dvgdeDv4, dvgdeDv5, dvgdov_pDv1, dvgdov_pDv3, dvgdov_pDv4;
    double dvgdov_pDv5, dvgseDv1, dvgseDv3, dvgseDv4, dvgseDv5;
    double dvgsov_pDv1, dvgsov_pDv3, dvgsov_pDv4, dvgsov_pDv5, dvpDv1;
    double dvpDv3, dvpDv4, dvpDv5, dvsDv3, dvsDv4;
    double dvsDv5, dvvDv1, dvvDv3, dvvDv4, dvvDv5;
    double dxfDv1, dxfDv3, dxfDv4, dxfDv5, dxrDv1;
    double dxrDv3, dxrDv4, dxrDv5, dz0Dv1, dz0Dv3;
    double dz0Dv4, dz0Dv5, dz1Dv1, dz1Dv3, dz1Dv4;
    double dz1Dv5, dz2Dv1, dz2Dv3, dz2Dv4, dz2Dv5;
    double dzkDv1, dzkDv3, dzkDv4, dzkDv5;
    double contributetmp;
    double dcontributetmpDv0, dcontributetmpDv1, dcontributetmpDv2, dcontributetmpDv3;
    double dcontributetmpDv4, dcontributetmpDv5, dcontributetmpDv6;

    double contributetmporg;
    double dcontributetmporgDv0, dcontributetmporgDv1, dcontributetmporgDv2, dcontributetmporgDv3;
    double dcontributetmporgDv4, dcontributetmporgDv5, dcontributetmporgDv6;

    fMat_r0c0 = 0.;
    fMat_r0c4 = 0.;
    fMat_r1c1 = 0.;
    fMat_r1c3 = 0.;
    fMat_r1c4 = 0.;
    fMat_r1c5 = 0.;
    fMat_r1c6 = 0.;
    fMat_r2c2 = 0.;
    fMat_r2c5 = 0.;
    fMat_r3c1 = 0.;
    fMat_r3c3 = 0.;
    fMat_r3c4 = 0.;
    fMat_r3c5 = 0.;
    fMat_r4c0 = 0.;
    fMat_r4c1 = 0.;
    fMat_r4c3 = 0.;
    fMat_r4c4 = 0.;
    fMat_r4c5 = 0.;
    fMat_r4c6 = 0.;
    fMat_r5c1 = 0.;
    fMat_r5c2 = 0.;
    fMat_r5c3 = 0.;
    fMat_r5c4 = 0.;
    fMat_r5c5 = 0.;
    fMat_r5c6 = 0.;
    fMat_r6c6 = 0.;
    qMat_r0c0 = 0.;
    qMat_r0c4 = 0.;
    qMat_r1c1 = 0.;
    qMat_r1c3 = 0.;
    qMat_r1c4 = 0.;
    qMat_r1c5 = 0.;
    qMat_r1c6 = 0.;
    qMat_r2c2 = 0.;
    qMat_r2c5 = 0.;
    qMat_r3c1 = 0.;
    qMat_r3c3 = 0.;
    qMat_r3c4 = 0.;
    qMat_r3c5 = 0.;
    qMat_r4c0 = 0.;
    qMat_r4c1 = 0.;
    qMat_r4c3 = 0.;
    qMat_r4c4 = 0.;
    qMat_r4c5 = 0.;
    qMat_r4c6 = 0.;
    qMat_r5c1 = 0.;
    qMat_r5c2 = 0.;
    qMat_r5c3 = 0.;
    qMat_r5c4 = 0.;
    qMat_r5c5 = 0.;
    qMat_r5c6 = 0.;
    qMat_r6c6 = 0.;

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
    dVSDv3 = (-dVbDv3);
    dVSDv5 = dVsiDv5;
    VS = (Vsi-Vb);

    dVDDv3 = (-dVbDv3);
    dVDDv4 = dVdiDv4;
    VD = (Vdi-Vb);

    dVGDv1 = dVgDv1;
    dVGDv3 = (-dVbDv3);
    VG = (Vg-Vb);

    if(model_.SIGN*VS>model_.SIGN*VD){
    d_gt_s_flag = (-1);
    } else {
    d_gt_s_flag = 1;
    }
    dvdDv3 = model_.SIGN*0.5*((d_gt_s_flag+1)*dVDDv3+(1-d_gt_s_flag)*dVSDv3)/(UT);
    dvdDv4 = model_.SIGN*0.5*(d_gt_s_flag+1)*dVDDv4/(UT);
    dvdDv5 = model_.SIGN*0.5*(1-d_gt_s_flag)*dVSDv5/(UT);
    vd = model_.SIGN*0.5*((d_gt_s_flag+1)*VD+(1-d_gt_s_flag)*VS)/(UT);

    dvsDv3 = model_.SIGN*0.5*((d_gt_s_flag+1)*dVSDv3+(1-d_gt_s_flag)*dVDDv3)/(UT);
    dvsDv4 = model_.SIGN*0.5*(1-d_gt_s_flag)*dVDDv4/(UT);
    dvsDv5 = model_.SIGN*0.5*(d_gt_s_flag+1)*dVSDv5/(UT);
    vs = model_.SIGN*0.5*((d_gt_s_flag+1)*VS+(1-d_gt_s_flag)*VD)/(UT);

    dvgDv1 = model_.SIGN*dVGDv1/(UT);
    dvgDv3 = model_.SIGN*dVGDv3/(UT);
    vg = model_.SIGN*VG/(UT);

    chsh_l = CHSHL*TSI;
    chsh_w = CHSHW*TSI;
    one_w = 1.0+chsh_w;
    dchsh_a1Dv3 = (-chsh_l*(1/(2*sqrt(0.5*((vbi+vs)+sqrt(((vbi+vs)*(vbi+vs)+UT2)))))*(0.5*(dvsDv3+1/(2*sqrt(((vbi+vs)*(vbi+vs)+UT2)))*(((vbi+vs)*dvsDv3+dvsDv3*(vbi+vs)))))+1/(2*sqrt(0.5*((vbi+vd)+sqrt(((vbi+vd)*(vbi+vd)+UT2)))))*(0.5*(dvdDv3+1/(2*sqrt(((vbi+vd)*(vbi+vd)+UT2)))*(((vbi+vd)*dvdDv3+dvdDv3*(vbi+vd))))))/(gamma_b_dev));
    dchsh_a1Dv4 = (-chsh_l*(1/(2*sqrt(0.5*((vbi+vs)+sqrt(((vbi+vs)*(vbi+vs)+UT2)))))*(0.5*(dvsDv4+1/(2*sqrt(((vbi+vs)*(vbi+vs)+UT2)))*(((vbi+vs)*dvsDv4+dvsDv4*(vbi+vs)))))+1/(2*sqrt(0.5*((vbi+vd)+sqrt(((vbi+vd)*(vbi+vd)+UT2)))))*(0.5*(dvdDv4+1/(2*sqrt(((vbi+vd)*(vbi+vd)+UT2)))*(((vbi+vd)*dvdDv4+dvdDv4*(vbi+vd))))))/(gamma_b_dev));
    dchsh_a1Dv5 = (-chsh_l*(1/(2*sqrt(0.5*((vbi+vs)+sqrt(((vbi+vs)*(vbi+vs)+UT2)))))*(0.5*(dvsDv5+1/(2*sqrt(((vbi+vs)*(vbi+vs)+UT2)))*(((vbi+vs)*dvsDv5+dvsDv5*(vbi+vs)))))+1/(2*sqrt(0.5*((vbi+vd)+sqrt(((vbi+vd)*(vbi+vd)+UT2)))))*(0.5*(dvdDv5+1/(2*sqrt(((vbi+vd)*(vbi+vd)+UT2)))*(((vbi+vd)*dvdDv5+dvdDv5*(vbi+vd))))))/(gamma_b_dev));
    chsh_a1 = (1.0-chsh_l*(sqrt(0.5*((vbi+vs)+sqrt(((vbi+vs)*(vbi+vs)+UT2))))+sqrt(0.5*((vbi+vd)+sqrt(((vbi+vd)*(vbi+vd)+UT2)))))/(gamma_b_dev));

    dchsh_a2Dv3 = (dchsh_a1Dv3+dchsh_a1Dv3);
    dchsh_a2Dv4 = (dchsh_a1Dv4+dchsh_a1Dv4);
    dchsh_a2Dv5 = (dchsh_a1Dv5+dchsh_a1Dv5);
    chsh_a2 = (((chsh_a1+chsh_a1)-1.0)+(chsh_w+chsh_w)*sqrtphi/(gamma_b_dev));

    dchsh_a3Dv3 = dpd*dchsh_a2Dv3;
    dchsh_a3Dv4 = dpd*dchsh_a2Dv4;
    dchsh_a3Dv5 = dpd*dchsh_a2Dv5;
    chsh_a3 = (one_w+dpd*chsh_a2);

    dgamma_b_chshDv3 = gamma_b_dev*dchsh_a1Dv3/(one_w);
    dgamma_b_chshDv4 = gamma_b_dev*dchsh_a1Dv4/(one_w);
    dgamma_b_chshDv5 = gamma_b_dev*dchsh_a1Dv5/(one_w);
    gamma_b_chsh = gamma_b_dev*chsh_a1/(one_w);

    dgamma_b_chsh2Dv3 = (gamma_b_chsh*dgamma_b_chshDv3+dgamma_b_chshDv3*gamma_b_chsh);
    dgamma_b_chsh2Dv4 = (gamma_b_chsh*dgamma_b_chshDv4+dgamma_b_chshDv4*gamma_b_chsh);
    dgamma_b_chsh2Dv5 = (gamma_b_chsh*dgamma_b_chshDv5+dgamma_b_chshDv5*gamma_b_chsh);
    gamma_b_chsh2 = gamma_b_chsh*gamma_b_chsh;

    dgamma_b_effDv3 = (gamma_b_dev*dchsh_a1Dv3-gamma_b_dev*chsh_a1/(chsh_a3)*dchsh_a3Dv3)/(chsh_a3);
    dgamma_b_effDv4 = (gamma_b_dev*dchsh_a1Dv4-gamma_b_dev*chsh_a1/(chsh_a3)*dchsh_a3Dv4)/(chsh_a3);
    dgamma_b_effDv5 = (gamma_b_dev*dchsh_a1Dv5-gamma_b_dev*chsh_a1/(chsh_a3)*dchsh_a3Dv5)/(chsh_a3);
    gamma_b_eff = gamma_b_dev*chsh_a1/(chsh_a3);

    dgamma_b_eff2Dv3 = (gamma_b_eff*dgamma_b_effDv3+dgamma_b_effDv3*gamma_b_eff);
    dgamma_b_eff2Dv4 = (gamma_b_eff*dgamma_b_effDv4+dgamma_b_effDv4*gamma_b_eff);
    dgamma_b_eff2Dv5 = (gamma_b_eff*dgamma_b_effDv5+dgamma_b_effDv5*gamma_b_eff);
    gamma_b_eff2 = gamma_b_eff*gamma_b_eff;

    chsh_a10 = 1.0-chsh_l*2.0*sqrt(vbi)/gamma_b_dev;
    chsh_a20 = chsh_a10+chsh_a10-1.0+(chsh_w+chsh_w)*sqrtphi/gamma_b_dev;
    chsh_a30 = one_w+dpd*chsh_a20;
    gamma_b_chsh0 = gamma_b_dev*chsh_a10/one_w;
    gamma_b_chsh02 = gamma_b_chsh0*gamma_b_chsh0;
    tmp_vfb = 1.0-(chsh_l+chsh_l)*sqrtvbi/gamma_b_dev+chsh_w*sqrtphi/gamma_b_dev;
    vfb = vto-phi*(one_w+dpd*tmp_vfb*tmp_vfb)-gamma_b_dev*(1.0-(chsh_l+chsh_l)*sqrtvbi/gamma_b_dev)*sqrtphi;
    dvg_pDv1 = dvgDv1;
    dvg_pDv3 = dvgDv3;
    vg_p = (vg-vfb);

    dvg_p_chshDv1 = dvg_pDv1/(one_w);
    dvg_p_chshDv3 = dvg_pDv3/(one_w);
    vg_p_chsh = vg_p/(one_w);

    dvg_p_chsh_pdDv1 = dvg_pDv1/(chsh_a3);
    dvg_p_chsh_pdDv3 = (dvg_pDv3-vg_p/(chsh_a3)*dchsh_a3Dv3)/(chsh_a3);
    dvg_p_chsh_pdDv4 = (-vg_p/(chsh_a3)*dchsh_a3Dv4)/(chsh_a3);
    dvg_p_chsh_pdDv5 = (-vg_p/(chsh_a3)*dchsh_a3Dv5)/(chsh_a3);
    vg_p_chsh_pd = vg_p/(chsh_a3);

    dvg_p_chsh_pd0Dv1 = dvg_pDv1/(chsh_a30);
    dvg_p_chsh_pd0Dv3 = dvg_pDv3/(chsh_a30);
    vg_p_chsh_pd0 = vg_p/(chsh_a30);

    dtmpDv1 = dvg_p_chshDv1*0.5;
    dtmpDv3 = (dvg_p_chshDv3*0.5-3.0*dgamma_b_chshDv3*0.70710678118654752440084436210485);
    dtmpDv4 = (-3.0*dgamma_b_chshDv4*0.70710678118654752440084436210485);
    dtmpDv5 = (-3.0*dgamma_b_chshDv5*0.70710678118654752440084436210485);
    tmp = (vg_p_chsh*0.5-3.0*(1.0+gamma_b_chsh*0.70710678118654752440084436210485));

    dpsi_poDv1 = (dtmpDv1+1/(2*sqrt((tmp*tmp+6.0*vg_p_chsh)))*(((tmp*dtmpDv1+dtmpDv1*tmp)+6.0*dvg_p_chshDv1)));
    dpsi_poDv3 = (dtmpDv3+1/(2*sqrt((tmp*tmp+6.0*vg_p_chsh)))*(((tmp*dtmpDv3+dtmpDv3*tmp)+6.0*dvg_p_chshDv3)));
    dpsi_poDv4 = (dtmpDv4+1/(2*sqrt((tmp*tmp+6.0*vg_p_chsh)))*((tmp*dtmpDv4+dtmpDv4*tmp)));
    dpsi_poDv5 = (dtmpDv5+1/(2*sqrt((tmp*tmp+6.0*vg_p_chsh)))*((tmp*dtmpDv5+dtmpDv5*tmp)));
    psi_po = (tmp+sqrt((tmp*tmp+6.0*vg_p_chsh)));

    dtmpDv1 = dvg_p_chshDv1*0.5;
    dtmpDv3 = dvg_p_chshDv3*0.5;
    tmp = (vg_p_chsh*0.5-3.0*(1.0+gamma_b_chsh0*0.70710678118654752440084436210485));

    dpsi_po0Dv1 = (dtmpDv1+1/(2*sqrt((tmp*tmp+6.0*vg_p_chsh)))*(((tmp*dtmpDv1+dtmpDv1*tmp)+6.0*dvg_p_chshDv1)));
    dpsi_po0Dv3 = (dtmpDv3+1/(2*sqrt((tmp*tmp+6.0*vg_p_chsh)))*(((tmp*dtmpDv3+dtmpDv3*tmp)+6.0*dvg_p_chshDv3)));
    psi_po0 = (tmp+sqrt((tmp*tmp+6.0*vg_p_chsh)));

    dpsi_p_tmpDv1 = dpsi_p_tmpDv3 = 0.0;
    depsilonDv1 = depsilonDv3 = 0.0;
    if(vg_p<0.0){
    dtmpDv1 = (dpsi_poDv1-dvg_p_chshDv1)/(gamma_b_chsh);
    dtmpDv3 = ((dpsi_poDv3-dvg_p_chshDv3)-(psi_po-vg_p_chsh)/(gamma_b_chsh)*dgamma_b_chshDv3)/(gamma_b_chsh);
    dtmpDv4 = (dpsi_poDv4-(psi_po-vg_p_chsh)/(gamma_b_chsh)*dgamma_b_chshDv4)/(gamma_b_chsh);
    dtmpDv5 = (dpsi_poDv5-(psi_po-vg_p_chsh)/(gamma_b_chsh)*dgamma_b_chshDv5)/(gamma_b_chsh);
    tmp = (psi_po-vg_p_chsh)/(gamma_b_chsh);

    dpsi_pDv1 = (-1/(((1.0-psi_po)+tmp*tmp))*(((-dpsi_poDv1)+(tmp*dtmpDv1+dtmpDv1*tmp))));
    dpsi_pDv3 = (-1/(((1.0-psi_po)+tmp*tmp))*(((-dpsi_poDv3)+(tmp*dtmpDv3+dtmpDv3*tmp))));
    dpsi_pDv4 = (-1/(((1.0-psi_po)+tmp*tmp))*(((-dpsi_poDv4)+(tmp*dtmpDv4+dtmpDv4*tmp))));
    dpsi_pDv5 = (-1/(((1.0-psi_po)+tmp*tmp))*(((-dpsi_poDv5)+(tmp*dtmpDv5+dtmpDv5*tmp))));
    psi_p = (-log(((1.0-psi_po)+tmp*tmp)));

    dtmpDv1 = (dpsi_po0Dv1-dvg_p_chshDv1)/(gamma_b_chsh0);
    dtmpDv3 = (dpsi_po0Dv3-dvg_p_chshDv3)/(gamma_b_chsh0);
    tmp = (psi_po0-vg_p_chsh)/(gamma_b_chsh0);

    dpsi_p0Dv1 = (-1/(((1.0-psi_po0)+tmp*tmp))*(((-dpsi_po0Dv1)+(tmp*dtmpDv1+dtmpDv1*tmp))));
    dpsi_p0Dv3 = (-1/(((1.0-psi_po0)+tmp*tmp))*(((-dpsi_po0Dv3)+(tmp*dtmpDv3+dtmpDv3*tmp))));
    psi_p0 = (-log(((1.0-psi_po0)+tmp*tmp)));

    } else {
    depsilonDv1 = exp((-psi_po))*((-dpsi_poDv1));
    depsilonDv3 = exp((-psi_po))*((-dpsi_poDv3));
    depsilonDv4 = exp((-psi_po))*((-dpsi_poDv4));
    depsilonDv5 = exp((-psi_po))*((-dpsi_poDv5));
    epsilon = exp((-psi_po));

    dpsi_p_tmpDv1 = 1/(2*sqrt((((vg_p_chsh_pd-1.0)+epsilon)+gamma_b_eff2*0.25)))*((dvg_p_chsh_pdDv1+depsilonDv1));
    dpsi_p_tmpDv3 = (1/(2*sqrt((((vg_p_chsh_pd-1.0)+epsilon)+gamma_b_eff2*0.25)))*(((dvg_p_chsh_pdDv3+depsilonDv3)+dgamma_b_eff2Dv3*0.25))-dgamma_b_effDv3*0.5);
    dpsi_p_tmpDv4 = (1/(2*sqrt((((vg_p_chsh_pd-1.0)+epsilon)+gamma_b_eff2*0.25)))*(((dvg_p_chsh_pdDv4+depsilonDv4)+dgamma_b_eff2Dv4*0.25))-dgamma_b_effDv4*0.5);
    dpsi_p_tmpDv5 = (1/(2*sqrt((((vg_p_chsh_pd-1.0)+epsilon)+gamma_b_eff2*0.25)))*(((dvg_p_chsh_pdDv5+depsilonDv5)+dgamma_b_eff2Dv5*0.25))-dgamma_b_effDv5*0.5);
    psi_p_tmp = (sqrt((((vg_p_chsh_pd-1.0)+epsilon)+gamma_b_eff2*0.25))-gamma_b_eff*0.5);

    dpsi_pDv1 = ((psi_p_tmp*dpsi_p_tmpDv1+dpsi_p_tmpDv1*psi_p_tmp)-depsilonDv1);
    dpsi_pDv3 = ((psi_p_tmp*dpsi_p_tmpDv3+dpsi_p_tmpDv3*psi_p_tmp)-depsilonDv3);
    dpsi_pDv4 = ((psi_p_tmp*dpsi_p_tmpDv4+dpsi_p_tmpDv4*psi_p_tmp)-depsilonDv4);
    dpsi_pDv5 = ((psi_p_tmp*dpsi_p_tmpDv5+dpsi_p_tmpDv5*psi_p_tmp)-depsilonDv5);
    psi_p = ((psi_p_tmp*psi_p_tmp+1.0)-epsilon);

    depsilonDv1 = exp((-psi_po0))*((-dpsi_po0Dv1));
    depsilonDv3 = exp((-psi_po0))*((-dpsi_po0Dv3));
    epsilon = exp((-psi_po0));

    dpsi_p_tmpDv1 = 1/(2*sqrt((((vg_p_chsh_pd0-1.0)+epsilon)+gamma_b_chsh02*0.25)))*((dvg_p_chsh_pd0Dv1+depsilonDv1));
    dpsi_p_tmpDv3 = 1/(2*sqrt((((vg_p_chsh_pd0-1.0)+epsilon)+gamma_b_chsh02*0.25)))*((dvg_p_chsh_pd0Dv3+depsilonDv3));
    psi_p_tmp = (sqrt((((vg_p_chsh_pd0-1.0)+epsilon)+gamma_b_chsh02*0.25))-gamma_b_chsh0*0.5);

    dpsi_p0Dv1 = ((psi_p_tmp*dpsi_p_tmpDv1+dpsi_p_tmpDv1*psi_p_tmp)-depsilonDv1);
    dpsi_p0Dv3 = ((psi_p_tmp*dpsi_p_tmpDv3+dpsi_p_tmpDv3*psi_p_tmp)-depsilonDv3);
    psi_p0 = ((psi_p_tmp*psi_p_tmp+1.0)-epsilon);

    }
    dsqrt_psi_pDv1 = 1/(2*sqrt(0.5*((psi_p+1.0E-4)+sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_pDv1+1/(2*sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))*(((psi_p-1.0E-4)*dpsi_pDv1+dpsi_pDv1*(psi_p-1.0E-4)))));
    dsqrt_psi_pDv3 = 1/(2*sqrt(0.5*((psi_p+1.0E-4)+sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_pDv3+1/(2*sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))*(((psi_p-1.0E-4)*dpsi_pDv3+dpsi_pDv3*(psi_p-1.0E-4)))));
    dsqrt_psi_pDv4 = 1/(2*sqrt(0.5*((psi_p+1.0E-4)+sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_pDv4+1/(2*sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))*(((psi_p-1.0E-4)*dpsi_pDv4+dpsi_pDv4*(psi_p-1.0E-4)))));
    dsqrt_psi_pDv5 = 1/(2*sqrt(0.5*((psi_p+1.0E-4)+sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_pDv5+1/(2*sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2)))*(((psi_p-1.0E-4)*dpsi_pDv5+dpsi_pDv5*(psi_p-1.0E-4)))));
    sqrt_psi_p = sqrt(0.5*((psi_p+1.0E-4)+sqrt(((psi_p-1.0E-4)*(psi_p-1.0E-4)+1.0E-2))));

    dsqrt_psi_p0Dv1 = 1/(2*sqrt(0.5*((psi_p0+1.0E-4)+sqrt(((psi_p0-1.0E-4)*(psi_p0-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_p0Dv1+1/(2*sqrt(((psi_p0-1.0E-4)*(psi_p0-1.0E-4)+1.0E-2)))*(((psi_p0-1.0E-4)*dpsi_p0Dv1+dpsi_p0Dv1*(psi_p0-1.0E-4)))));
    dsqrt_psi_p0Dv3 = 1/(2*sqrt(0.5*((psi_p0+1.0E-4)+sqrt(((psi_p0-1.0E-4)*(psi_p0-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_p0Dv3+1/(2*sqrt(((psi_p0-1.0E-4)*(psi_p0-1.0E-4)+1.0E-2)))*(((psi_p0-1.0E-4)*dpsi_p0Dv3+dpsi_p0Dv3*(psi_p0-1.0E-4)))));
    sqrt_psi_p0 = sqrt(0.5*((psi_p0+1.0E-4)+sqrt(((psi_p0-1.0E-4)*(psi_p0-1.0E-4)+1.0E-2))));

    dvpDv1 = dpsi_pDv1;
    dvpDv3 = dpsi_pDv3;
    dvpDv4 = dpsi_pDv4;
    dvpDv5 = dpsi_pDv5;
    vp = (psi_p-phi);

    dnvDv1 = (-gamma_b_dev*chsh_a1/(2.0*sqrt_psi_p)*2.0*dsqrt_psi_pDv1)/(2.0*sqrt_psi_p);
    dnvDv3 = (dchsh_a3Dv3+(gamma_b_dev*dchsh_a1Dv3-gamma_b_dev*chsh_a1/(2.0*sqrt_psi_p)*2.0*dsqrt_psi_pDv3)/(2.0*sqrt_psi_p));
    dnvDv4 = (dchsh_a3Dv4+(gamma_b_dev*dchsh_a1Dv4-gamma_b_dev*chsh_a1/(2.0*sqrt_psi_p)*2.0*dsqrt_psi_pDv4)/(2.0*sqrt_psi_p));
    dnvDv5 = (dchsh_a3Dv5+(gamma_b_dev*dchsh_a1Dv5-gamma_b_dev*chsh_a1/(2.0*sqrt_psi_p)*2.0*dsqrt_psi_pDv5)/(2.0*sqrt_psi_p));
    nv = (chsh_a3+gamma_b_dev*chsh_a1/(2.0*sqrt_psi_p));

    ddv_diblDv1 = ddv_diblDv3 = ddv_diblDv4 = ddv_diblDv5 = 0.0;
    if(model_.ETAD==0.0){
    deltapsis = 0.0;
    ddeltapsisDv1 = ddeltapsisDv3 = ddeltapsisDv4 = ddeltapsisDv5 = 0.0;
    } else {
    l0 = ETAD_DEV*TSI*sqrt(2.0*sqrtphi/gamma_b_dev);
    v_o_dibl = 4.0+40.0*l0/Leff;
    v_o_dibl2 = v_o_dibl*v_o_dibl;
    dtmpDv3 = 0.5*((dvsDv3+dvdDv3)-1/(2*sqrt(((vs-vd)*(vs-vd)+v_o_dibl2)))*(((vs-vd)*(dvsDv3-dvdDv3)+(dvsDv3-dvdDv3)*(vs-vd))));
    dtmpDv4 = 0.5*((dvsDv4+dvdDv4)-1/(2*sqrt(((vs-vd)*(vs-vd)+v_o_dibl2)))*(((vs-vd)*(dvsDv4-dvdDv4)+(dvsDv4-dvdDv4)*(vs-vd))));
    dtmpDv5 = 0.5*((dvsDv5+dvdDv5)-1/(2*sqrt(((vs-vd)*(vs-vd)+v_o_dibl2)))*(((vs-vd)*(dvsDv5-dvdDv5)+(dvsDv5-dvdDv5)*(vs-vd))));
    tmp = 0.5*((vs+vd)-sqrt(((vs-vd)*(vs-vd)+v_o_dibl2)));

    ddv_diblDv1 = 0.5*(dvpDv1-1/(2*sqrt(((vp-tmp)*(vp-tmp)+v_o_dibl2)))*(((vp-tmp)*dvpDv1+dvpDv1*(vp-tmp))));
    ddv_diblDv3 = 0.5*((dvpDv3+dtmpDv3)-1/(2*sqrt(((vp-tmp)*(vp-tmp)+v_o_dibl2)))*(((vp-tmp)*(dvpDv3-dtmpDv3)+(dvpDv3-dtmpDv3)*(vp-tmp))));
    ddv_diblDv4 = 0.5*((dvpDv4+dtmpDv4)-1/(2*sqrt(((vp-tmp)*(vp-tmp)+v_o_dibl2)))*(((vp-tmp)*(dvpDv4-dtmpDv4)+(dvpDv4-dtmpDv4)*(vp-tmp))));
    ddv_diblDv5 = 0.5*((dvpDv5+dtmpDv5)-1/(2*sqrt(((vp-tmp)*(vp-tmp)+v_o_dibl2)))*(((vp-tmp)*(dvpDv5-dtmpDv5)+(dvpDv5-dtmpDv5)*(vp-tmp))));
    dv_dibl = 0.5*((vp+tmp)-sqrt(((vp-tmp)*(vp-tmp)+v_o_dibl2)));

    tmp = Leff/(l0+l0);
    if(tmp>70.0){
    deltapsis = 0.0;
    ddeltapsisDv1 = ddeltapsisDv3 = ddeltapsisDv4 = ddeltapsisDv5 = 0.0;
    } else {
    exp_tmp = exp((-tmp));
    ddeltapsisDv1 = (exp_tmp*(2.0+model_.SIGMAD*tmp*dv_dibl/(2.0*phi))*1/(2*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)))*((((nul+vs)-dv_dibl)*(-ddv_diblDv1)+(-ddv_diblDv1)*((nul+vd)-dv_dibl)))+exp_tmp*model_.SIGMAD*tmp*ddv_diblDv1/(2.0*phi)*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)));
    ddeltapsisDv3 = (exp_tmp*(2.0+model_.SIGMAD*tmp*dv_dibl/(2.0*phi))*1/(2*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)))*((((nul+vs)-dv_dibl)*(dvdDv3-ddv_diblDv3)+(dvsDv3-ddv_diblDv3)*((nul+vd)-dv_dibl)))+exp_tmp*model_.SIGMAD*tmp*ddv_diblDv3/(2.0*phi)*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)));
    ddeltapsisDv4 = (exp_tmp*(2.0+model_.SIGMAD*tmp*dv_dibl/(2.0*phi))*1/(2*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)))*((((nul+vs)-dv_dibl)*(dvdDv4-ddv_diblDv4)+(dvsDv4-ddv_diblDv4)*((nul+vd)-dv_dibl)))+exp_tmp*model_.SIGMAD*tmp*ddv_diblDv4/(2.0*phi)*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)));
    ddeltapsisDv5 = (exp_tmp*(2.0+model_.SIGMAD*tmp*dv_dibl/(2.0*phi))*1/(2*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)))*((((nul+vs)-dv_dibl)*(dvdDv5-ddv_diblDv5)+(dvsDv5-ddv_diblDv5)*((nul+vd)-dv_dibl)))+exp_tmp*model_.SIGMAD*tmp*ddv_diblDv5/(2.0*phi)*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl)));
    deltapsis = exp_tmp*(2.0+model_.SIGMAD*tmp*dv_dibl/(2.0*phi))*sqrt(((nul+vs)-dv_dibl)*((nul+vd)-dv_dibl));

    }
    dtmpDv1 = dtmpDv3 = 0.0;
    }
    dvvDv1 = (dvpDv1+ddeltapsisDv1)/(NUV);
    dvvDv3 = ((dvpDv3+ddeltapsisDv3)-dvsDv3)/(NUV);
    dvvDv4 = ((dvpDv4+ddeltapsisDv4)-dvsDv4)/(NUV);
    dvvDv5 = ((dvpDv5+ddeltapsisDv5)-dvsDv5)/(NUV);
    vv = ((vp+deltapsis)-vs)/(NUV);

    dln_z1_Dv1 = dln_z1_Dv3 = dln_z1_Dv4 = dln_z1_Dv5 = 0.0;
    if(vv>(-0.6)){
    dz1Dv1 = 0.25*(dvvDv1+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv1+dvvDv1*(vv-0.394036))));
    dz1Dv3 = 0.25*(dvvDv3+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv3+dvvDv3*(vv-0.394036))));
    dz1Dv4 = 0.25*(dvvDv4+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv4+dvvDv4*(vv-0.394036))));
    dz1Dv5 = 0.25*(dvvDv5+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv5+dvvDv5*(vv-0.394036))));
    z1 = 0.25*((vv-1.4)+sqrt((vv*(vv-0.394036)+9.662671)));

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+1/(z1)*(dz1Dv1)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+1/(z1)*(dz1Dv3)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+1/(z1)*(dz1Dv4)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+1/(z1)*(dz1Dv5)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+log(z1)))/((2.0*z1+1.0));

    dqsDv1 = (z1*(z2*0.070*dz2Dv1+dz2Dv1*(1.0+0.070*z2))+dz1Dv1*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqsDv3 = (z1*(z2*0.070*dz2Dv3+dz2Dv3*(1.0+0.070*z2))+dz1Dv3*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqsDv4 = (z1*(z2*0.070*dz2Dv4+dz2Dv4*(1.0+0.070*z2))+dz1Dv4*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqsDv5 = (z1*(z2*0.070*dz2Dv5+dz2Dv5*(1.0+0.070*z2))+dz1Dv5*(1.0+z2*(1.0+0.070*z2)))*NUV;
    qs = z1*(1.0+z2*(1.0+0.070*z2))*NUV;

    } else {
    dln_z1_Dv1 = 0.5*(dvvDv1-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv1+dvvDv1*(vv-0.402982))));
    dln_z1_Dv3 = 0.5*(dvvDv3-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv3+dvvDv3*(vv-0.402982))));
    dln_z1_Dv4 = 0.5*(dvvDv4-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv4+dvvDv4*(vv-0.402982))));
    dln_z1_Dv5 = 0.5*(dvvDv5-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv5+dvvDv5*(vv-0.402982))));
    ln_z1_ = 0.5*((vv-0.201491)-sqrt((vv*(vv-0.402982)+2.446562)));

    dz1Dv1 = exp(ln_z1_)*(dln_z1_Dv1);
    dz1Dv3 = exp(ln_z1_)*(dln_z1_Dv3);
    dz1Dv4 = exp(ln_z1_)*(dln_z1_Dv4);
    dz1Dv5 = exp(ln_z1_)*(dln_z1_Dv5);
    z1 = exp(ln_z1_);

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+dln_z1_Dv1))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+dln_z1_Dv3))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+dln_z1_Dv4))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+dln_z1_Dv5))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0));

    dqsDv1 = (z1*(z2*0.483*dz2Dv1+dz2Dv1*(1.0+0.483*z2))+dz1Dv1*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqsDv3 = (z1*(z2*0.483*dz2Dv3+dz2Dv3*(1.0+0.483*z2))+dz1Dv3*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqsDv4 = (z1*(z2*0.483*dz2Dv4+dz2Dv4*(1.0+0.483*z2))+dz1Dv4*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqsDv5 = (z1*(z2*0.483*dz2Dv5+dz2Dv5*(1.0+0.483*z2))+dz1Dv5*(1.0+z2*(1.0+0.483*z2)))*NUV;
    qs = z1*(1.0+z2*(1.0+0.483*z2))*NUV;

    }
    dqs2Dv1 = (qs*dqsDv1+dqsDv1*qs);
    dqs2Dv3 = (qs*dqsDv3+dqsDv3*qs);
    dqs2Dv4 = (qs*dqsDv4+dqsDv4*qs);
    dqs2Dv5 = (qs*dqsDv5+dqsDv5*qs);
    qs2 = qs*qs;

    dif_Dv1 = (dqs2Dv1+dqsDv1);
    dif_Dv3 = (dqs2Dv3+dqsDv3);
    dif_Dv4 = (dqs2Dv4+dqsDv4);
    dif_Dv5 = (dqs2Dv5+dqsDv5);
    if_ = (qs2+qs);

    dsif2Dv1 = dif_Dv1;
    dsif2Dv3 = dif_Dv3;
    dsif2Dv4 = dif_Dv4;
    dsif2Dv5 = dif_Dv5;
    sif2 = (0.25+if_);

    dsifDv1 = 1/(2*sqrt(sif2))*(dsif2Dv1);
    dsifDv3 = 1/(2*sqrt(sif2))*(dsif2Dv3);
    dsifDv4 = 1/(2*sqrt(sif2))*(dsif2Dv4);
    dsifDv5 = 1/(2*sqrt(sif2))*(dsif2Dv5);
    sif = sqrt(sif2);

    g_clm = 0.1;
    e_clm = 2.0/(ucrit_o_UT*Leff);
    e_clm2 = e_clm*e_clm;
    e_clmx2 = 2.0*e_clm;
    e_clmp2 = 2.0+e_clm;
    de_clmx2xqsDv1 = e_clmx2*dqsDv1;
    de_clmx2xqsDv3 = e_clmx2*dqsDv3;
    de_clmx2xqsDv4 = e_clmx2*dqsDv4;
    de_clmx2xqsDv5 = e_clmx2*dqsDv5;
    e_clmx2xqs = e_clmx2*qs;

    dqsatDv1 = (e_clmx2*dif_Dv1-e_clmx2*if_/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))))*(de_clmx2xqsDv1+1/(2*sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs)))*(4.0*de_clmx2xqsDv1)))/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))));
    dqsatDv3 = (e_clmx2*dif_Dv3-e_clmx2*if_/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))))*(de_clmx2xqsDv3+1/(2*sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs)))*(4.0*de_clmx2xqsDv3)))/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))));
    dqsatDv4 = (e_clmx2*dif_Dv4-e_clmx2*if_/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))))*(de_clmx2xqsDv4+1/(2*sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs)))*(4.0*de_clmx2xqsDv4)))/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))));
    dqsatDv5 = (e_clmx2*dif_Dv5-e_clmx2*if_/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))))*(de_clmx2xqsDv5+1/(2*sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs)))*(4.0*de_clmx2xqsDv5)))/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))));
    qsat = e_clmx2*if_/(((e_clmp2+e_clmx2xqs)+sqrt((e_clmp2*e_clmp2+4.0*e_clmx2xqs))));

    dqs_qsatDv1 = (dqsDv1-dqsatDv1);
    dqs_qsatDv3 = (dqsDv3-dqsatDv3);
    dqs_qsatDv4 = (dqsDv4-dqsatDv4);
    dqs_qsatDv5 = (dqsDv5-dqsatDv5);
    qs_qsat = (qs-qsat);

    dqs_qsat2Dv1 = (qs_qsat*dqs_qsatDv1+dqs_qsatDv1*qs_qsat);
    dqs_qsat2Dv3 = (qs_qsat*dqs_qsatDv3+dqs_qsatDv3*qs_qsat);
    dqs_qsat2Dv4 = (qs_qsat*dqs_qsatDv4+dqs_qsatDv4*qs_qsat);
    dqs_qsat2Dv5 = (qs_qsat*dqs_qsatDv5+dqs_qsatDv5*qs_qsat);
    qs_qsat2 = qs_qsat*qs_qsat;

    mdm2 = 2.0-model_.DELTA;
    e_clmxmdm2_2 = e_clm2*mdm2*mdm2;
    dvdsat_tmp1Dv1 = ((2.0*qsat+log(qsat))*e_clm*dqs_qsatDv1+(2.0*dqsatDv1+1/(qsat)*(dqsatDv1))*(1.0+e_clm*qs_qsat));
    dvdsat_tmp1Dv3 = ((2.0*qsat+log(qsat))*e_clm*dqs_qsatDv3+(2.0*dqsatDv3+1/(qsat)*(dqsatDv3))*(1.0+e_clm*qs_qsat));
    dvdsat_tmp1Dv4 = ((2.0*qsat+log(qsat))*e_clm*dqs_qsatDv4+(2.0*dqsatDv4+1/(qsat)*(dqsatDv4))*(1.0+e_clm*qs_qsat));
    dvdsat_tmp1Dv5 = ((2.0*qsat+log(qsat))*e_clm*dqs_qsatDv5+(2.0*dqsatDv5+1/(qsat)*(dqsatDv5))*(1.0+e_clm*qs_qsat));
    vdsat_tmp1 = (2.0*qsat+log(qsat))*(1.0+e_clm*qs_qsat);

    dvdsat_tmp11Dv1 = e_clm*mdm2*dqs_qsatDv1;
    dvdsat_tmp11Dv3 = e_clm*mdm2*dqs_qsatDv3;
    dvdsat_tmp11Dv4 = e_clm*mdm2*dqs_qsatDv4;
    dvdsat_tmp11Dv5 = e_clm*mdm2*dqs_qsatDv5;
    vdsat_tmp11 = (g_clm+e_clm*mdm2*qs_qsat);

    dvdsat_tmp2Dv1 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11))+e_clm2*qs_qsat2)))*(((2.0*e_clmxmdm2_2*dqs_qsat2Dv1-2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11)*dvdsat_tmp11Dv1)/(vdsat_tmp11)+e_clm2*dqs_qsat2Dv1));
    dvdsat_tmp2Dv3 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11))+e_clm2*qs_qsat2)))*(((2.0*e_clmxmdm2_2*dqs_qsat2Dv3-2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11)*dvdsat_tmp11Dv3)/(vdsat_tmp11)+e_clm2*dqs_qsat2Dv3));
    dvdsat_tmp2Dv4 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11))+e_clm2*qs_qsat2)))*(((2.0*e_clmxmdm2_2*dqs_qsat2Dv4-2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11)*dvdsat_tmp11Dv4)/(vdsat_tmp11)+e_clm2*dqs_qsat2Dv4));
    dvdsat_tmp2Dv5 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11))+e_clm2*qs_qsat2)))*(((2.0*e_clmxmdm2_2*dqs_qsat2Dv5-2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11)*dvdsat_tmp11Dv5)/(vdsat_tmp11)+e_clm2*dqs_qsat2Dv5));
    vdsat_tmp2 = sqrt(((1.0+2.0*e_clmxmdm2_2*qs_qsat2/(vdsat_tmp11))+e_clm2*qs_qsat2));

    dvdsatDv1 = (dvpDv1-(dvdsat_tmp1Dv1-vdsat_tmp1/(vdsat_tmp2)*dvdsat_tmp2Dv1)/(vdsat_tmp2));
    dvdsatDv3 = (dvpDv3-(dvdsat_tmp1Dv3-vdsat_tmp1/(vdsat_tmp2)*dvdsat_tmp2Dv3)/(vdsat_tmp2));
    dvdsatDv4 = (dvpDv4-(dvdsat_tmp1Dv4-vdsat_tmp1/(vdsat_tmp2)*dvdsat_tmp2Dv4)/(vdsat_tmp2));
    dvdsatDv5 = (dvpDv5-(dvdsat_tmp1Dv5-vdsat_tmp1/(vdsat_tmp2)*dvdsat_tmp2Dv5)/(vdsat_tmp2));
    vdsat = (vp-vdsat_tmp1/(vdsat_tmp2));

    ddv_clmDv1 = (model_.ACLM/(model_.DELTA)*4.0*dqsatDv1-model_.ACLM/(model_.DELTA)*(4.0*qsat+model_.DELTA)/((qs+1.0))*dqsDv1)/((qs+1.0));
    ddv_clmDv3 = (model_.ACLM/(model_.DELTA)*4.0*dqsatDv3-model_.ACLM/(model_.DELTA)*(4.0*qsat+model_.DELTA)/((qs+1.0))*dqsDv3)/((qs+1.0));
    ddv_clmDv4 = (model_.ACLM/(model_.DELTA)*4.0*dqsatDv4-model_.ACLM/(model_.DELTA)*(4.0*qsat+model_.DELTA)/((qs+1.0))*dqsDv4)/((qs+1.0));
    ddv_clmDv5 = (model_.ACLM/(model_.DELTA)*4.0*dqsatDv5-model_.ACLM/(model_.DELTA)*(4.0*qsat+model_.DELTA)/((qs+1.0))*dqsDv5)/((qs+1.0));
    dv_clm = model_.ACLM/(model_.DELTA)*(4.0*qsat+model_.DELTA)/((qs+1.0));

    dvdssatDv1 = 0.5*(dvdsatDv1+1/(2*sqrt((((vdsat-vs)-3.0)*((vdsat-vs)-3.0)+4.0)))*((((vdsat-vs)-3.0)*dvdsatDv1+dvdsatDv1*((vdsat-vs)-3.0))));
    dvdssatDv3 = 0.5*((dvdsatDv3-dvsDv3)+1/(2*sqrt((((vdsat-vs)-3.0)*((vdsat-vs)-3.0)+4.0)))*((((vdsat-vs)-3.0)*(dvdsatDv3-dvsDv3)+(dvdsatDv3-dvsDv3)*((vdsat-vs)-3.0))));
    dvdssatDv4 = 0.5*((dvdsatDv4-dvsDv4)+1/(2*sqrt((((vdsat-vs)-3.0)*((vdsat-vs)-3.0)+4.0)))*((((vdsat-vs)-3.0)*(dvdsatDv4-dvsDv4)+(dvdsatDv4-dvsDv4)*((vdsat-vs)-3.0))));
    dvdssatDv5 = 0.5*((dvdsatDv5-dvsDv5)+1/(2*sqrt((((vdsat-vs)-3.0)*((vdsat-vs)-3.0)+4.0)))*((((vdsat-vs)-3.0)*(dvdsatDv5-dvsDv5)+(dvdsatDv5-dvsDv5)*((vdsat-vs)-3.0))));
    vdssat = 0.5*(((vdsat-vs)+3.0)+sqrt((((vdsat-vs)-3.0)*((vdsat-vs)-3.0)+4.0)));

    dvdp_tmp1Dv1 = (vd-vs)*1/(2*sqrt((1.0+4.0*dv_clm/(vdssat))))*((4.0*ddv_clmDv1-4.0*dv_clm/(vdssat)*dvdssatDv1)/(vdssat));
    dvdp_tmp1Dv3 = ((vd-vs)*1/(2*sqrt((1.0+4.0*dv_clm/(vdssat))))*((4.0*ddv_clmDv3-4.0*dv_clm/(vdssat)*dvdssatDv3)/(vdssat))+(dvdDv3-dvsDv3)*sqrt((1.0+4.0*dv_clm/(vdssat))));
    dvdp_tmp1Dv4 = ((vd-vs)*1/(2*sqrt((1.0+4.0*dv_clm/(vdssat))))*((4.0*ddv_clmDv4-4.0*dv_clm/(vdssat)*dvdssatDv4)/(vdssat))+(dvdDv4-dvsDv4)*sqrt((1.0+4.0*dv_clm/(vdssat))));
    dvdp_tmp1Dv5 = ((vd-vs)*1/(2*sqrt((1.0+4.0*dv_clm/(vdssat))))*((4.0*ddv_clmDv5-4.0*dv_clm/(vdssat)*dvdssatDv5)/(vdssat))+(dvdDv5-dvsDv5)*sqrt((1.0+4.0*dv_clm/(vdssat))));
    vdp_tmp1 = (vd-vs)*sqrt((1.0+4.0*dv_clm/(vdssat)));

    dvdp_tmp2Dv1 = 1/(2*sqrt(((vdp_tmp1+vdssat)*(vdp_tmp1+vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1+vdssat)*(dvdp_tmp1Dv1+dvdssatDv1)+(dvdp_tmp1Dv1+dvdssatDv1)*(vdp_tmp1+vdssat))+(4.0*dv_clm*dvdssatDv1+4.0*ddv_clmDv1*vdssat)));
    dvdp_tmp2Dv3 = 1/(2*sqrt(((vdp_tmp1+vdssat)*(vdp_tmp1+vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1+vdssat)*(dvdp_tmp1Dv3+dvdssatDv3)+(dvdp_tmp1Dv3+dvdssatDv3)*(vdp_tmp1+vdssat))+(4.0*dv_clm*dvdssatDv3+4.0*ddv_clmDv3*vdssat)));
    dvdp_tmp2Dv4 = 1/(2*sqrt(((vdp_tmp1+vdssat)*(vdp_tmp1+vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1+vdssat)*(dvdp_tmp1Dv4+dvdssatDv4)+(dvdp_tmp1Dv4+dvdssatDv4)*(vdp_tmp1+vdssat))+(4.0*dv_clm*dvdssatDv4+4.0*ddv_clmDv4*vdssat)));
    dvdp_tmp2Dv5 = 1/(2*sqrt(((vdp_tmp1+vdssat)*(vdp_tmp1+vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1+vdssat)*(dvdp_tmp1Dv5+dvdssatDv5)+(dvdp_tmp1Dv5+dvdssatDv5)*(vdp_tmp1+vdssat))+(4.0*dv_clm*dvdssatDv5+4.0*ddv_clmDv5*vdssat)));
    vdp_tmp2 = sqrt(((vdp_tmp1+vdssat)*(vdp_tmp1+vdssat)+4.0*dv_clm*vdssat));

    dvdp_tmp3Dv1 = 1/(2*sqrt(((vdp_tmp1-vdssat)*(vdp_tmp1-vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1-vdssat)*(dvdp_tmp1Dv1-dvdssatDv1)+(dvdp_tmp1Dv1-dvdssatDv1)*(vdp_tmp1-vdssat))+(4.0*dv_clm*dvdssatDv1+4.0*ddv_clmDv1*vdssat)));
    dvdp_tmp3Dv3 = 1/(2*sqrt(((vdp_tmp1-vdssat)*(vdp_tmp1-vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1-vdssat)*(dvdp_tmp1Dv3-dvdssatDv3)+(dvdp_tmp1Dv3-dvdssatDv3)*(vdp_tmp1-vdssat))+(4.0*dv_clm*dvdssatDv3+4.0*ddv_clmDv3*vdssat)));
    dvdp_tmp3Dv4 = 1/(2*sqrt(((vdp_tmp1-vdssat)*(vdp_tmp1-vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1-vdssat)*(dvdp_tmp1Dv4-dvdssatDv4)+(dvdp_tmp1Dv4-dvdssatDv4)*(vdp_tmp1-vdssat))+(4.0*dv_clm*dvdssatDv4+4.0*ddv_clmDv4*vdssat)));
    dvdp_tmp3Dv5 = 1/(2*sqrt(((vdp_tmp1-vdssat)*(vdp_tmp1-vdssat)+4.0*dv_clm*vdssat)))*((((vdp_tmp1-vdssat)*(dvdp_tmp1Dv5-dvdssatDv5)+(dvdp_tmp1Dv5-dvdssatDv5)*(vdp_tmp1-vdssat))+(4.0*dv_clm*dvdssatDv5+4.0*ddv_clmDv5*vdssat)));
    vdp_tmp3 = sqrt(((vdp_tmp1-vdssat)*(vdp_tmp1-vdssat)+4.0*dv_clm*vdssat));

    dvdpDv1 = 0.5*(dvdp_tmp2Dv1-dvdp_tmp3Dv1);
    dvdpDv3 = (0.5*(dvdp_tmp2Dv3-dvdp_tmp3Dv3)+dvsDv3);
    dvdpDv4 = (0.5*(dvdp_tmp2Dv4-dvdp_tmp3Dv4)+dvsDv4);
    dvdpDv5 = (0.5*(dvdp_tmp2Dv5-dvdp_tmp3Dv5)+dvsDv5);
    vdp = (0.5*(vdp_tmp2-vdp_tmp3)+vs);

    du_clmDv1 = 0.5*e_clm*Leff/(LC)*(-dvdpDv1);
    du_clmDv3 = 0.5*e_clm*Leff/(LC)*(dvdDv3-dvdpDv3);
    du_clmDv4 = 0.5*e_clm*Leff/(LC)*(dvdDv4-dvdpDv4);
    du_clmDv5 = 0.5*e_clm*Leff/(LC)*(dvdDv5-dvdpDv5);
    u_clm = 0.5*e_clm*Leff/(LC)*(vd-vdp);

    alpha_clm = LC/(Leff-2.0*LC);
    ddeltalDv1 = LAMBDA_gt*LC*1/(((alpha_clm+u_clm)+sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))/((alpha_clm+1.0)))*((du_clmDv1+1/(2*sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))*(((u_clm*du_clmDv1+du_clmDv1*u_clm)+2.0*alpha_clm*du_clmDv1)))/((alpha_clm+1.0)));
    ddeltalDv3 = LAMBDA_gt*LC*1/(((alpha_clm+u_clm)+sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))/((alpha_clm+1.0)))*((du_clmDv3+1/(2*sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))*(((u_clm*du_clmDv3+du_clmDv3*u_clm)+2.0*alpha_clm*du_clmDv3)))/((alpha_clm+1.0)));
    ddeltalDv4 = LAMBDA_gt*LC*1/(((alpha_clm+u_clm)+sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))/((alpha_clm+1.0)))*((du_clmDv4+1/(2*sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))*(((u_clm*du_clmDv4+du_clmDv4*u_clm)+2.0*alpha_clm*du_clmDv4)))/((alpha_clm+1.0)));
    ddeltalDv5 = LAMBDA_gt*LC*1/(((alpha_clm+u_clm)+sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))/((alpha_clm+1.0)))*((du_clmDv5+1/(2*sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))*(((u_clm*du_clmDv5+du_clmDv5*u_clm)+2.0*alpha_clm*du_clmDv5)))/((alpha_clm+1.0)));
    deltal = LAMBDA_gt*LC*log(((alpha_clm+u_clm)+sqrt(((u_clm*u_clm+2.0*alpha_clm*u_clm)+1.0)))/((alpha_clm+1.0)));

    dvvDv1 = ((dvpDv1+ddeltapsisDv1)-dvdpDv1)/(NUV);
    dvvDv3 = ((dvpDv3+ddeltapsisDv3)-dvdpDv3)/(NUV);
    dvvDv4 = ((dvpDv4+ddeltapsisDv4)-dvdpDv4)/(NUV);
    dvvDv5 = ((dvpDv5+ddeltapsisDv5)-dvdpDv5)/(NUV);
    vv = ((vp+deltapsis)-vdp)/(NUV);

    if(vv>(-0.6)){
    dz1Dv1 = 0.25*(dvvDv1+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv1+dvvDv1*(vv-0.394036))));
    dz1Dv3 = 0.25*(dvvDv3+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv3+dvvDv3*(vv-0.394036))));
    dz1Dv4 = 0.25*(dvvDv4+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv4+dvvDv4*(vv-0.394036))));
    dz1Dv5 = 0.25*(dvvDv5+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv5+dvvDv5*(vv-0.394036))));
    z1 = 0.25*((vv-1.4)+sqrt((vv*(vv-0.394036)+9.662671)));

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+1/(z1)*(dz1Dv1)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+1/(z1)*(dz1Dv3)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+1/(z1)*(dz1Dv4)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+1/(z1)*(dz1Dv5)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+log(z1)))/((2.0*z1+1.0));

    dqdpDv1 = (z1*(z2*0.070*dz2Dv1+dz2Dv1*(1.0+0.070*z2))+dz1Dv1*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqdpDv3 = (z1*(z2*0.070*dz2Dv3+dz2Dv3*(1.0+0.070*z2))+dz1Dv3*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqdpDv4 = (z1*(z2*0.070*dz2Dv4+dz2Dv4*(1.0+0.070*z2))+dz1Dv4*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqdpDv5 = (z1*(z2*0.070*dz2Dv5+dz2Dv5*(1.0+0.070*z2))+dz1Dv5*(1.0+z2*(1.0+0.070*z2)))*NUV;
    qdp = z1*(1.0+z2*(1.0+0.070*z2))*NUV;

    } else {
    dln_z1_Dv1 = 0.5*(dvvDv1-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv1+dvvDv1*(vv-0.402982))));
    dln_z1_Dv3 = 0.5*(dvvDv3-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv3+dvvDv3*(vv-0.402982))));
    dln_z1_Dv4 = 0.5*(dvvDv4-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv4+dvvDv4*(vv-0.402982))));
    dln_z1_Dv5 = 0.5*(dvvDv5-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv5+dvvDv5*(vv-0.402982))));
    ln_z1_ = 0.5*((vv-0.201491)-sqrt((vv*(vv-0.402982)+2.446562)));

    dz1Dv1 = exp(ln_z1_)*(dln_z1_Dv1);
    dz1Dv3 = exp(ln_z1_)*(dln_z1_Dv3);
    dz1Dv4 = exp(ln_z1_)*(dln_z1_Dv4);
    dz1Dv5 = exp(ln_z1_)*(dln_z1_Dv5);
    z1 = exp(ln_z1_);

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+dln_z1_Dv1))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+dln_z1_Dv3))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+dln_z1_Dv4))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+dln_z1_Dv5))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0));

    dqdpDv1 = (z1*(z2*0.483*dz2Dv1+dz2Dv1*(1.0+0.483*z2))+dz1Dv1*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqdpDv3 = (z1*(z2*0.483*dz2Dv3+dz2Dv3*(1.0+0.483*z2))+dz1Dv3*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqdpDv4 = (z1*(z2*0.483*dz2Dv4+dz2Dv4*(1.0+0.483*z2))+dz1Dv4*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqdpDv5 = (z1*(z2*0.483*dz2Dv5+dz2Dv5*(1.0+0.483*z2))+dz1Dv5*(1.0+z2*(1.0+0.483*z2)))*NUV;
    qdp = z1*(1.0+z2*(1.0+0.483*z2))*NUV;

    }
    dqdp2Dv1 = (qdp*dqdpDv1+dqdpDv1*qdp);
    dqdp2Dv3 = (qdp*dqdpDv3+dqdpDv3*qdp);
    dqdp2Dv4 = (qdp*dqdpDv4+dqdpDv4*qdp);
    dqdp2Dv5 = (qdp*dqdpDv5+dqdpDv5*qdp);
    qdp2 = qdp*qdp;

    dirpDv1 = (dqdp2Dv1+dqdpDv1);
    dirpDv3 = (dqdp2Dv3+dqdpDv3);
    dirpDv4 = (dqdp2Dv4+dqdpDv4);
    dirpDv5 = (dqdp2Dv5+dqdpDv5);
    irp = (qdp2+qdp);

    dsirp2Dv1 = dirpDv1;
    dsirp2Dv3 = dirpDv3;
    dsirp2Dv4 = dirpDv4;
    dsirp2Dv5 = dirpDv5;
    sirp2 = (0.25+irp);

    dsirpDv1 = 1/(2*sqrt(sirp2))*(dsirp2Dv1);
    dsirpDv3 = 1/(2*sqrt(sirp2))*(dsirp2Dv3);
    dsirpDv4 = 1/(2*sqrt(sirp2))*(dsirp2Dv4);
    dsirpDv5 = 1/(2*sqrt(sirp2))*(dsirp2Dv5);
    sirp = sqrt(sirp2);

    dqsqdpDv1 = (dqsDv1+dqdpDv1);
    dqsqdpDv3 = (dqsDv3+dqdpDv3);
    dqsqdpDv4 = (dqsDv4+dqdpDv4);
    dqsqdpDv5 = (dqsDv5+dqdpDv5);
    qsqdp = (qs+qdp);

    dqs_qdpDv1 = (dqsDv1-dqdpDv1);
    dqs_qdpDv3 = (dqsDv3-dqdpDv3);
    dqs_qdpDv4 = (dqsDv4-dqdpDv4);
    dqs_qdpDv5 = (dqsDv5-dqdpDv5);
    qs_qdp = (qs-qdp);

    dpowqs_qdp2Dv1 = (qs_qdp*dqs_qdpDv1+dqs_qdpDv1*qs_qdp);
    dpowqs_qdp2Dv3 = (qs_qdp*dqs_qdpDv3+dqs_qdpDv3*qs_qdp);
    dpowqs_qdp2Dv4 = (qs_qdp*dqs_qdpDv4+dqs_qdpDv4*qs_qdp);
    dpowqs_qdp2Dv5 = (qs_qdp*dqs_qdpDv5+dqs_qdpDv5*qs_qdp);
    powqs_qdp2 = qs_qdp*qs_qdp;

    dqsqdpp1Dv1 = dqsqdpDv1;
    dqsqdpp1Dv3 = dqsqdpDv3;
    dqsqdpp1Dv4 = dqsqdpDv4;
    dqsqdpp1Dv5 = dqsqdpDv5;
    qsqdpp1 = (qsqdp+1.0);

    dpowqsqdpp1_2Dv1 = (-1.0/(qsqdpp1*qsqdpp1)*(qsqdpp1*dqsqdpp1Dv1+dqsqdpp1Dv1*qsqdpp1))/(qsqdpp1*qsqdpp1);
    dpowqsqdpp1_2Dv3 = (-1.0/(qsqdpp1*qsqdpp1)*(qsqdpp1*dqsqdpp1Dv3+dqsqdpp1Dv3*qsqdpp1))/(qsqdpp1*qsqdpp1);
    dpowqsqdpp1_2Dv4 = (-1.0/(qsqdpp1*qsqdpp1)*(qsqdpp1*dqsqdpp1Dv4+dqsqdpp1Dv4*qsqdpp1))/(qsqdpp1*qsqdpp1);
    dpowqsqdpp1_2Dv5 = (-1.0/(qsqdpp1*qsqdpp1)*(qsqdpp1*dqsqdpp1Dv5+dqsqdpp1Dv5*qsqdpp1))/(qsqdpp1*qsqdpp1);
    powqsqdpp1_2 = 1.0/(qsqdpp1*qsqdpp1);

    diDv1 = (dif_Dv1-dirpDv1);
    diDv3 = (dif_Dv3-dirpDv3);
    diDv4 = (dif_Dv4-dirpDv4);
    diDv5 = (dif_Dv5-dirpDv5);
    i = (if_-irp);

    dpsi_sa_tmpDv1 = ((dpsi_pDv1-dqsDv1)-dqdpDv1);
    dpsi_sa_tmpDv3 = ((dpsi_pDv3-dqsDv3)-dqdpDv3);
    dpsi_sa_tmpDv4 = ((dpsi_pDv4-dqsDv4)-dqdpDv4);
    dpsi_sa_tmpDv5 = ((dpsi_pDv5-dqsDv5)-dqdpDv5);
    psi_sa_tmp = ((psi_p-qs)-qdp);

    dsqrt_psi_saDv1 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv1+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv1+dpsi_sa_tmpDv1*(psi_sa_tmp-1.0e-4)))));
    dsqrt_psi_saDv3 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv3+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv3+dpsi_sa_tmpDv3*(psi_sa_tmp-1.0e-4)))));
    dsqrt_psi_saDv4 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv4+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv4+dpsi_sa_tmpDv4*(psi_sa_tmp-1.0e-4)))));
    dsqrt_psi_saDv5 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv5+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv5+dpsi_sa_tmpDv5*(psi_sa_tmp-1.0e-4)))));
    sqrt_psi_sa = sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2))));

    dzkDv1 = dzkDv3 = dzkDv4 = dzkDv5 = 0.0;
    dz0Dv1 = dz0Dv3 = dz0Dv4 = dz0Dv5 = 0.0;
    if(model_.TG<0){
    dz0Dv1 = (-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv1+dsqrt_psi_saDv1))/((sqrt_psi_p+sqrt_psi_sa));
    dz0Dv3 = (dgamma_b_effDv3-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv3+dsqrt_psi_saDv3))/((sqrt_psi_p+sqrt_psi_sa));
    dz0Dv4 = (dgamma_b_effDv4-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv4+dsqrt_psi_saDv4))/((sqrt_psi_p+sqrt_psi_sa));
    dz0Dv5 = (dgamma_b_effDv5-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv5+dsqrt_psi_saDv5))/((sqrt_psi_p+sqrt_psi_sa));
    z0 = ((1.0+dpd)+gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa)));

    dzkDv1 = dpd*dsqrt_psi_saDv1/(gamma_b_eff);
    dzkDv3 = (dpd*dsqrt_psi_saDv3-dpd*sqrt_psi_sa/(gamma_b_eff)*dgamma_b_effDv3)/(gamma_b_eff);
    dzkDv4 = (dpd*dsqrt_psi_saDv4-dpd*sqrt_psi_sa/(gamma_b_eff)*dgamma_b_effDv4)/(gamma_b_eff);
    dzkDv5 = (dpd*dsqrt_psi_saDv5-dpd*sqrt_psi_sa/(gamma_b_eff)*dgamma_b_effDv5)/(gamma_b_eff);
    zk = (0.5+dpd*sqrt_psi_sa/(gamma_b_eff));

    dnqDv1 = (dz0Dv1-z0/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))))*(dzkDv1+1/(2*sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2))))*(((zk*dzkDv1+dzkDv1*zk)+(z0*(dqsDv1+dqdpDv1)+dz0Dv1*(qs+qdp))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))));
    dnqDv3 = (dz0Dv3-z0/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))))*(dzkDv3+1/(2*sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2))))*(((zk*dzkDv3+dzkDv3*zk)+(z0*(dqsDv3+dqdpDv3)+dz0Dv3*(qs+qdp))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))));
    dnqDv4 = (dz0Dv4-z0/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))))*(dzkDv4+1/(2*sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2))))*(((zk*dzkDv4+dzkDv4*zk)+(z0*(dqsDv4+dqdpDv4)+dz0Dv4*(qs+qdp))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))));
    dnqDv5 = (dz0Dv5-z0/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))))*(dzkDv5+1/(2*sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2))))*(((zk*dzkDv5+dzkDv5*zk)+(z0*(dqsDv5+dqdpDv5)+dz0Dv5*(qs+qdp))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))));
    nq = z0/((zk+sqrt((zk*zk+z0*(qs+qdp)/(gamma_g2)))));

    } else {
    dnqDv1 = (-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv1+dsqrt_psi_saDv1))/((sqrt_psi_p+sqrt_psi_sa));
    dnqDv3 = (dgamma_b_effDv3-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv3+dsqrt_psi_saDv3))/((sqrt_psi_p+sqrt_psi_sa));
    dnqDv4 = (dgamma_b_effDv4-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv4+dsqrt_psi_saDv4))/((sqrt_psi_p+sqrt_psi_sa));
    dnqDv5 = (dgamma_b_effDv5-gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa))*(dsqrt_psi_pDv5+dsqrt_psi_saDv5))/((sqrt_psi_p+sqrt_psi_sa));
    nq = (1.0+gamma_b_eff/((sqrt_psi_p+sqrt_psi_sa)));

    }
    dv_oDv1 = (dvg_p_chshDv1-dpsi_p0Dv1);
    dv_oDv3 = (dvg_p_chshDv3-dpsi_p0Dv3);
    v_o = (vg_p_chsh-psi_p0);

    dv_oDv4 = dv_oDv5 = 0.0;
    dqr1Dv3 = dqr1Dv4 = dqr1Dv5 = 0.0;
    dqboDv1 = dqboDv3 = dqboDv4 = dqboDv5 = 0.0;
    if(model_.AQMA!=0.0){
    dqr1Dv3 = 3.0*0.70710678118654752440084436210485*dgamma_b_chshDv3;
    dqr1Dv4 = 3.0*0.70710678118654752440084436210485*dgamma_b_chshDv4;
    dqr1Dv5 = 3.0*0.70710678118654752440084436210485*dgamma_b_chshDv5;
    qr1 = 3.0*0.70710678118654752440084436210485*gamma_b_chsh;

    if(vg_p<0.0){
    dqboDv1 = (dvg_p_chshDv1-dpsi_pDv1);
    dqboDv3 = (dvg_p_chshDv3-dpsi_pDv3);
    dqboDv4 = (-dpsi_pDv4);
    dqboDv5 = (-dpsi_pDv5);
    qbo = (vg_p_chsh-psi_p);

    } else {
    dqboDv1 = (dvg_p_chshDv1/((1.0+dpd))-dpsi_poDv1);
    dqboDv3 = (dvg_p_chshDv3/((1.0+dpd))-dpsi_poDv3);
    dqboDv4 = (-dpsi_poDv4);
    dqboDv5 = (-dpsi_poDv5);
    qbo = (vg_p_chsh/((1.0+dpd))-psi_po);

    }
    ddpsivDv1 = axetaqm2_3*exp(0.66666666666666666666666666666667*log((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo)))*(0.66666666666666666666666666666667*1/((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo))*((1/(2*sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2)))*((0.25*qbo*dqboDv1+0.25*dqboDv1*qbo))-0.5*dqboDv1)));
    ddpsivDv3 = axetaqm2_3*(exp(0.66666666666666666666666666666667*log((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo)))*(0.66666666666666666666666666666667*1/((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo))*((1/(2*sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2)))*(((0.25*qbo*dqboDv3+0.25*dqboDv3*qbo)+4.0*axetaqm2_3*dgamma_b_chsh2Dv3))-0.5*dqboDv3)))-exp(0.66666666666666666666666666666667*log((sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2))-qr1)))*(0.66666666666666666666666666666667*1/((sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2))-qr1))*((1/(2*sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2)))*(((qr1*dqr1Dv3+dqr1Dv3*qr1)+4.0*axetaqm2_3*dgamma_b_chsh2Dv3))-dqr1Dv3))));
    ddpsivDv4 = axetaqm2_3*(exp(0.66666666666666666666666666666667*log((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo)))*(0.66666666666666666666666666666667*1/((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo))*((1/(2*sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2)))*(((0.25*qbo*dqboDv4+0.25*dqboDv4*qbo)+4.0*axetaqm2_3*dgamma_b_chsh2Dv4))-0.5*dqboDv4)))-exp(0.66666666666666666666666666666667*log((sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2))-qr1)))*(0.66666666666666666666666666666667*1/((sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2))-qr1))*((1/(2*sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2)))*(((qr1*dqr1Dv4+dqr1Dv4*qr1)+4.0*axetaqm2_3*dgamma_b_chsh2Dv4))-dqr1Dv4))));
    ddpsivDv5 = axetaqm2_3*(exp(0.66666666666666666666666666666667*log((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo)))*(0.66666666666666666666666666666667*1/((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo))*((1/(2*sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2)))*(((0.25*qbo*dqboDv5+0.25*dqboDv5*qbo)+4.0*axetaqm2_3*dgamma_b_chsh2Dv5))-0.5*dqboDv5)))-exp(0.66666666666666666666666666666667*log((sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2))-qr1)))*(0.66666666666666666666666666666667*1/((sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2))-qr1))*((1/(2*sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2)))*(((qr1*dqr1Dv5+dqr1Dv5*qr1)+4.0*axetaqm2_3*dgamma_b_chsh2Dv5))-dqr1Dv5))));
    dpsiv = axetaqm2_3*(exp(0.66666666666666666666666666666667*log((sqrt((0.25*qbo*qbo+4.0*axetaqm2_3*gamma_b_chsh2))-0.5*qbo)))-exp(0.66666666666666666666666666666667*log((sqrt((qr1*qr1+4.0*axetaqm2_3*gamma_b_chsh2))-qr1))));

    dv_oDv1 = (dv_oDv1+ddpsivDv1);
    dv_oDv3 = (dv_oDv3+ddpsivDv3);
    dv_oDv4 = ddpsivDv4;
    dv_oDv5 = ddpsivDv5;
    v_o = (v_o+dpsiv);

    } else {
    dpsiv = 0.0;
    ddpsivDv1 = ddpsivDv3 = ddpsivDv4 = ddpsivDv5 = 0.0;
    }
    if(psi_p>2.0){
    dqSDv1 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqsDv1+dqdpDv1)+dqsDv1)+(0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*dpowqsqdpp1_2Dv1+(0.5*((1.0+0.8*qs)+1.2*qdp)*dpowqs_qdp2Dv1+0.5*(0.8*dqsDv1+1.2*dqdpDv1)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv1*0.33333333333333333333333333333333*(((qs+qdp)+qs)+0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*powqsqdpp1_2));
    dqSDv3 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqsDv3+dqdpDv3)+dqsDv3)+(0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*dpowqsqdpp1_2Dv3+(0.5*((1.0+0.8*qs)+1.2*qdp)*dpowqs_qdp2Dv3+0.5*(0.8*dqsDv3+1.2*dqdpDv3)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv3*0.33333333333333333333333333333333*(((qs+qdp)+qs)+0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*powqsqdpp1_2));
    dqSDv4 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqsDv4+dqdpDv4)+dqsDv4)+(0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*dpowqsqdpp1_2Dv4+(0.5*((1.0+0.8*qs)+1.2*qdp)*dpowqs_qdp2Dv4+0.5*(0.8*dqsDv4+1.2*dqdpDv4)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv4*0.33333333333333333333333333333333*(((qs+qdp)+qs)+0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*powqsqdpp1_2));
    dqSDv5 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqsDv5+dqdpDv5)+dqsDv5)+(0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*dpowqsqdpp1_2Dv5+(0.5*((1.0+0.8*qs)+1.2*qdp)*dpowqs_qdp2Dv5+0.5*(0.8*dqsDv5+1.2*dqdpDv5)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv5*0.33333333333333333333333333333333*(((qs+qdp)+qs)+0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*powqsqdpp1_2));
    qS = inv_dqmip1*nq*0.33333333333333333333333333333333*(((qs+qdp)+qs)+0.5*((1.0+0.8*qs)+1.2*qdp)*powqs_qdp2*powqsqdpp1_2);

    } else {
    qS = 0.0;
    dqSDv1 = dqSDv3 = dqSDv4 = dqSDv5 = 0.0;
    }
    if(psi_p>2.0){
    dqDDv1 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqdpDv1+dqsDv1)+dqdpDv1)+(0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*dpowqsqdpp1_2Dv1+(0.5*((1.0+0.8*qdp)+1.2*qs)*dpowqs_qdp2Dv1+0.5*(0.8*dqdpDv1+1.2*dqsDv1)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv1*0.33333333333333333333333333333333*(((qdp+qs)+qdp)+0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*powqsqdpp1_2));
    dqDDv3 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqdpDv3+dqsDv3)+dqdpDv3)+(0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*dpowqsqdpp1_2Dv3+(0.5*((1.0+0.8*qdp)+1.2*qs)*dpowqs_qdp2Dv3+0.5*(0.8*dqdpDv3+1.2*dqsDv3)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv3*0.33333333333333333333333333333333*(((qdp+qs)+qdp)+0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*powqsqdpp1_2));
    dqDDv4 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqdpDv4+dqsDv4)+dqdpDv4)+(0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*dpowqsqdpp1_2Dv4+(0.5*((1.0+0.8*qdp)+1.2*qs)*dpowqs_qdp2Dv4+0.5*(0.8*dqdpDv4+1.2*dqsDv4)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv4*0.33333333333333333333333333333333*(((qdp+qs)+qdp)+0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*powqsqdpp1_2));
    dqDDv5 = (inv_dqmip1*nq*0.33333333333333333333333333333333*(((dqdpDv5+dqsDv5)+dqdpDv5)+(0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*dpowqsqdpp1_2Dv5+(0.5*((1.0+0.8*qdp)+1.2*qs)*dpowqs_qdp2Dv5+0.5*(0.8*dqdpDv5+1.2*dqsDv5)*powqs_qdp2)*powqsqdpp1_2))+inv_dqmip1*dnqDv5*0.33333333333333333333333333333333*(((qdp+qs)+qdp)+0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*powqsqdpp1_2));
    qD = inv_dqmip1*nq*0.33333333333333333333333333333333*(((qdp+qs)+qdp)+0.5*((1.0+0.8*qdp)+1.2*qs)*powqs_qdp2*powqsqdpp1_2);

    } else {
    qD = 0.0;
    dqDDv1 = dqDDv3 = dqDDv4 = dqDDv5 = 0.0;
    }
    dv2_qgDv1 = dv2_qgDv3 = dv2_qgDv4 = dv2_qgDv5 = 0.0;
    dv1_qgDv1 = dv1_qgDv3 = dv1_qgDv4 = dv1_qgDv5 = 0.0;
    dk2Dv1 = dk2Dv3 = dk2Dv4 = dk2Dv5 = 0.0;
    dk12_3Dv1 = dk12_3Dv3 = dk12_3Dv4 = dk12_3Dv5 = 0.0;
    dk12_2Dv1 = dk12_2Dv3 = dk12_2Dv4 = dk12_2Dv5 = 0.0;
    dk12Dv1 = dk12Dv3 = dk12Dv4 = dk12Dv5 = 0.0;
    dk1Dv1 = dk1Dv3 = dk1Dv4 = dk1Dv5 = 0.0;
    if(psi_p>2.0){
    dv2_qgDv1 = dv2_qgDv3 = dv2_qgDv4 = dv2_qgDv5 = 0.0;
    dv1_qgDv1 = dv1_qgDv3 = dv1_qgDv4 = dv1_qgDv5 = 0.0;
    dk2Dv1 = dk2Dv3 = dk2Dv4 = dk2Dv5 = 0.0;
    dk12_3Dv1 = dk12_3Dv3 = dk12_3Dv4 = dk12_3Dv5 = 0.0;
    dk12_2Dv1 = dk12_2Dv3 = dk12_2Dv4 = dk12_2Dv5 = 0.0;
    dk12Dv1 = dk12Dv3 = dk12Dv4 = dk12Dv5 = 0.0;
    dk1Dv1 = dk1Dv3 = dk1Dv4 = dk1Dv5 = 0.0;
    if(model_.TG<0){
    dv1_qgDv1 = (dv_oDv1+2.0*dqsDv1*inv_dqmip1);
    dv1_qgDv3 = (dv_oDv3+2.0*dqsDv3*inv_dqmip1);
    dv1_qgDv4 = (dv_oDv4+2.0*dqsDv4*inv_dqmip1);
    dv1_qgDv5 = (dv_oDv5+2.0*dqsDv5*inv_dqmip1);
    v1_qg = (v_o+2.0*qs*inv_dqmip1);

    dv2_qgDv1 = (dv_oDv1+2.0*dqdpDv1*inv_dqmip1);
    dv2_qgDv3 = (dv_oDv3+2.0*dqdpDv3*inv_dqmip1);
    dv2_qgDv4 = (dv_oDv4+2.0*dqdpDv4*inv_dqmip1);
    dv2_qgDv5 = (dv_oDv5+2.0*dqdpDv5*inv_dqmip1);
    v2_qg = (v_o+2.0*qdp*inv_dqmip1);

    dk1Dv1 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv1/(gamma_g2));
    dk1Dv3 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv3/(gamma_g2));
    dk1Dv4 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv4/(gamma_g2));
    dk1Dv5 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv5/(gamma_g2));
    k1 = sqrt((0.25+v1_qg/(gamma_g2)));

    dk2Dv1 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv1/(gamma_g2));
    dk2Dv3 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv3/(gamma_g2));
    dk2Dv4 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv4/(gamma_g2));
    dk2Dv5 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv5/(gamma_g2));
    k2 = sqrt((0.25+v2_qg/(gamma_g2)));

    dk12Dv1 = (dk1Dv1+dk2Dv1);
    dk12Dv3 = (dk1Dv3+dk2Dv3);
    dk12Dv4 = (dk1Dv4+dk2Dv4);
    dk12Dv5 = (dk1Dv5+dk2Dv5);
    k12 = (k1+k2);

    dk12_2Dv1 = (k12*dk12Dv1+dk12Dv1*k12);
    dk12_2Dv3 = (k12*dk12Dv3+dk12Dv3*k12);
    dk12_2Dv4 = (k12*dk12Dv4+dk12Dv4*k12);
    dk12_2Dv5 = (k12*dk12Dv5+dk12Dv5*k12);
    k12_2 = k12*k12;

    dk12_3Dv1 = (k12_2*dk12Dv1+dk12_2Dv1*k12);
    dk12_3Dv3 = (k12_2*dk12Dv3+dk12_2Dv3*k12);
    dk12_3Dv4 = (k12_2*dk12Dv4+dk12_2Dv4*k12);
    dk12_3Dv5 = (k12_2*dk12Dv5+dk12_2Dv5*k12);
    k12_3 = k12_2*k12;

    dqGDv1 = (((dv1_qgDv1-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv1)/((1.0+2.0*k1))+(dv2_qgDv1-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv1)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(k12_3)*(0.8*(dk12_2Dv1+(k1*dk2Dv1+dk1Dv1*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1)*dqsqdpp1Dv1)/(qsqdpp1)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2Dv1-powqs_qdp2/(k12_3)*dk12_3Dv1)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1)+2.0/(gamma_g2))));
    dqGDv3 = (((dv1_qgDv3-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv3)/((1.0+2.0*k1))+(dv2_qgDv3-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv3)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(k12_3)*(0.8*(dk12_2Dv3+(k1*dk2Dv3+dk1Dv3*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1)*dqsqdpp1Dv3)/(qsqdpp1)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2Dv3-powqs_qdp2/(k12_3)*dk12_3Dv3)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1)+2.0/(gamma_g2))));
    dqGDv4 = (((dv1_qgDv4-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv4)/((1.0+2.0*k1))+(dv2_qgDv4-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv4)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(k12_3)*(0.8*(dk12_2Dv4+(k1*dk2Dv4+dk1Dv4*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1)*dqsqdpp1Dv4)/(qsqdpp1)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2Dv4-powqs_qdp2/(k12_3)*dk12_3Dv4)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1)+2.0/(gamma_g2))));
    dqGDv5 = (((dv1_qgDv5-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv5)/((1.0+2.0*k1))+(dv2_qgDv5-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv5)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(k12_3)*(0.8*(dk12_2Dv5+(k1*dk2Dv5+dk1Dv5*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1)*dqsqdpp1Dv5)/(qsqdpp1)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2Dv5-powqs_qdp2/(k12_3)*dk12_3Dv5)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1)+2.0/(gamma_g2))));
    qG = ((v1_qg/((1.0+2.0*k1))+v2_qg/((1.0+2.0*k2)))+inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1)+2.0/(gamma_g2)));

    } else {
    dqGDv1 = (((dv_oDv1+dqsDv1)+dqdpDv1)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2Dv1-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(qsqdpp1)*dqsqdpp1Dv1)/(qsqdpp1));
    dqGDv3 = (((dv_oDv3+dqsDv3)+dqdpDv3)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2Dv3-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(qsqdpp1)*dqsqdpp1Dv3)/(qsqdpp1));
    dqGDv4 = (((dv_oDv4+dqsDv4)+dqdpDv4)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2Dv4-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(qsqdpp1)*dqsqdpp1Dv4)/(qsqdpp1));
    dqGDv5 = (((dv_oDv5+dqsDv5)+dqdpDv5)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2Dv5-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(qsqdpp1)*dqsqdpp1Dv5)/(qsqdpp1));
    qG = (((v_o+qs)+qdp)+inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2/(qsqdpp1));

    }
    } else {
    if(psi_p>0.0){
    dqGDv1 = ((model_.TG < 0) ? (dv_oDv1-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv1/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv1);
    dqGDv3 = ((model_.TG < 0) ? (dv_oDv3-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv3/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv3);
    dqGDv4 = ((model_.TG < 0) ? (dv_oDv4-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv4/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv4);
    dqGDv5 = ((model_.TG < 0) ? (dv_oDv5-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv5/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv5);
    qG = ((model_.TG < 0) ? v_o/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : v_o);

    } else {
    dqGDv1 = ((model_.TG > 0) ? (dv_oDv1-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv1/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv1);
    dqGDv3 = ((model_.TG > 0) ? (dv_oDv3-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv3/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv3);
    dqGDv4 = ((model_.TG > 0) ? (dv_oDv4-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv4/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv4);
    dqGDv5 = ((model_.TG > 0) ? (dv_oDv5-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv5/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv5);
    qG = ((model_.TG > 0) ? v_o/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : v_o);

    }
    }
    dqIDv1 = (dqSDv1+dqDDv1);
    dqIDv3 = (dqSDv3+dqDDv3);
    dqIDv4 = (dqSDv4+dqDDv4);
    dqIDv5 = (dqSDv5+dqDDv5);
    qI = (qS+qD);

    dqBDv1 = (dqGDv1-dqIDv1);
    dqBDv3 = (dqGDv3-dqIDv3);
    dqBDv4 = (dqGDv4-dqIDv4);
    dqBDv5 = (dqGDv5-dqIDv5);
    qB = (qG-qI);

    dbeta_coulDv1 = (-model_.THC/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp))*((1.0+nv*model_.ZC*qs)*(nv*model_.ZC*dqdpDv1+dnvDv1*model_.ZC*qdp)+(nv*model_.ZC*dqsDv1+dnvDv1*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp)))/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp));
    dbeta_coulDv3 = (-model_.THC/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp))*((1.0+nv*model_.ZC*qs)*(nv*model_.ZC*dqdpDv3+dnvDv3*model_.ZC*qdp)+(nv*model_.ZC*dqsDv3+dnvDv3*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp)))/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp));
    dbeta_coulDv4 = (-model_.THC/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp))*((1.0+nv*model_.ZC*qs)*(nv*model_.ZC*dqdpDv4+dnvDv4*model_.ZC*qdp)+(nv*model_.ZC*dqsDv4+dnvDv4*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp)))/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp));
    dbeta_coulDv5 = (-model_.THC/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp))*((1.0+nv*model_.ZC*qs)*(nv*model_.ZC*dqdpDv5+dnvDv5*model_.ZC*qdp)+(nv*model_.ZC*dqsDv5+dnvDv5*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp)))/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp));
    beta_coul = model_.THC/((1.0+nv*model_.ZC*qs)*(1.0+nv*model_.ZC*qdp));

    dnuDv1 = dnvDv1*(1.0-ETA_t);
    dnuDv3 = dnvDv3*(1.0-ETA_t);
    dnuDv4 = dnvDv4*(1.0-ETA_t);
    dnuDv5 = dnvDv5*(1.0-ETA_t);
    nu = (nv*(1.0-ETA_t)-1.0);

    dgpnuDv1 = (gamma_b_eff*dsqrt_psi_pDv1+dnuDv1);
    dgpnuDv3 = ((gamma_b_eff*dsqrt_psi_pDv3+dgamma_b_effDv3*sqrt_psi_p)+dnuDv3);
    dgpnuDv4 = ((gamma_b_eff*dsqrt_psi_pDv4+dgamma_b_effDv4*sqrt_psi_p)+dnuDv4);
    dgpnuDv5 = ((gamma_b_eff*dsqrt_psi_pDv5+dgamma_b_effDv5*sqrt_psi_p)+dnuDv5);
    gpnu = (gamma_b_eff*sqrt_psi_p+nu);

    deqDv1 = (dqBDv1+(ETA_t*nv*dqIDv1+ETA_t*dnvDv1*qI));
    deqDv3 = (dqBDv3+(ETA_t*nv*dqIDv3+ETA_t*dnvDv3*qI));
    deqDv4 = (dqBDv4+(ETA_t*nv*dqIDv4+ETA_t*dnvDv4*qI));
    deqDv5 = (dqBDv5+(ETA_t*nv*dqIDv5+ETA_t*dnvDv5*qI));
    eq = (qB+ETA_t*nv*qI);

    deq1Dv1 = (((gpnu*dgpnuDv1+dgpnuDv1*gpnu)+(nu*nu*(((dif_Dv1+dif_Dv1)+dirpDv1)+dirpDv1)+(nu*dnuDv1+dnuDv1*nu)*((((1.0+if_)+if_)+irp)+irp)))-((8.0*0.33333333333333333333333333333333*nu*gpnu*((dsif2Dv1+(sif*dsirpDv1+dsifDv1*sirp))+dsirp2Dv1)+(8.0*0.33333333333333333333333333333333*nu*dgpnuDv1+8.0*0.33333333333333333333333333333333*dnuDv1*gpnu)*((sif2+sif*sirp)+sirp2))-8.0*0.33333333333333333333333333333333*nu*gpnu*((sif2+sif*sirp)+sirp2)/((sif+sirp))*(dsifDv1+dsirpDv1))/((sif+sirp)));
    deq1Dv3 = (((gpnu*dgpnuDv3+dgpnuDv3*gpnu)+(nu*nu*(((dif_Dv3+dif_Dv3)+dirpDv3)+dirpDv3)+(nu*dnuDv3+dnuDv3*nu)*((((1.0+if_)+if_)+irp)+irp)))-((8.0*0.33333333333333333333333333333333*nu*gpnu*((dsif2Dv3+(sif*dsirpDv3+dsifDv3*sirp))+dsirp2Dv3)+(8.0*0.33333333333333333333333333333333*nu*dgpnuDv3+8.0*0.33333333333333333333333333333333*dnuDv3*gpnu)*((sif2+sif*sirp)+sirp2))-8.0*0.33333333333333333333333333333333*nu*gpnu*((sif2+sif*sirp)+sirp2)/((sif+sirp))*(dsifDv3+dsirpDv3))/((sif+sirp)));
    deq1Dv4 = (((gpnu*dgpnuDv4+dgpnuDv4*gpnu)+(nu*nu*(((dif_Dv4+dif_Dv4)+dirpDv4)+dirpDv4)+(nu*dnuDv4+dnuDv4*nu)*((((1.0+if_)+if_)+irp)+irp)))-((8.0*0.33333333333333333333333333333333*nu*gpnu*((dsif2Dv4+(sif*dsirpDv4+dsifDv4*sirp))+dsirp2Dv4)+(8.0*0.33333333333333333333333333333333*nu*dgpnuDv4+8.0*0.33333333333333333333333333333333*dnuDv4*gpnu)*((sif2+sif*sirp)+sirp2))-8.0*0.33333333333333333333333333333333*nu*gpnu*((sif2+sif*sirp)+sirp2)/((sif+sirp))*(dsifDv4+dsirpDv4))/((sif+sirp)));
    deq1Dv5 = (((gpnu*dgpnuDv5+dgpnuDv5*gpnu)+(nu*nu*(((dif_Dv5+dif_Dv5)+dirpDv5)+dirpDv5)+(nu*dnuDv5+dnuDv5*nu)*((((1.0+if_)+if_)+irp)+irp)))-((8.0*0.33333333333333333333333333333333*nu*gpnu*((dsif2Dv5+(sif*dsirpDv5+dsifDv5*sirp))+dsirp2Dv5)+(8.0*0.33333333333333333333333333333333*nu*dgpnuDv5+8.0*0.33333333333333333333333333333333*dnuDv5*gpnu)*((sif2+sif*sirp)+sirp2))-8.0*0.33333333333333333333333333333333*nu*gpnu*((sif2+sif*sirp)+sirp2)/((sif+sirp))*(dsifDv5+dsirpDv5))/((sif+sirp)));
    eq1 = ((gpnu*gpnu+nu*nu*((((1.0+if_)+if_)+irp)+irp))-8.0*0.33333333333333333333333333333333*nu*gpnu*((sif2+sif*sirp)+sirp2)/((sif+sirp)));

    dbeta_nomDv3 = (ev*dgamma_b_effDv3*sqrtphi+ev1*dgamma_b_eff2Dv3*phi);
    dbeta_nomDv4 = (ev*dgamma_b_effDv4*sqrtphi+ev1*dgamma_b_eff2Dv4*phi);
    dbeta_nomDv5 = (ev*dgamma_b_effDv5*sqrtphi+ev1*dgamma_b_eff2Dv5*phi);
    beta_nom = ((1.0+ev*gamma_b_eff*sqrtphi)+ev1*gamma_b_eff2*phi);

    dbeta_denomDv1 = ((ev*deqDv1+ev1*deq1Dv1)+dbeta_coulDv1);
    dbeta_denomDv3 = ((ev*deqDv3+ev1*deq1Dv3)+dbeta_coulDv3);
    dbeta_denomDv4 = ((ev*deqDv4+ev1*deq1Dv4)+dbeta_coulDv4);
    dbeta_denomDv5 = ((ev*deqDv5+ev1*deq1Dv5)+dbeta_coulDv5);
    beta_denom = (((1.0+ev*eq)+ev1*eq1)+beta_coul);

    dbetaDv1 = (-KP_DEV_t*beta_nom/(beta_denom)*dbeta_denomDv1)/(beta_denom);
    dbetaDv3 = (KP_DEV_t*dbeta_nomDv3-KP_DEV_t*beta_nom/(beta_denom)*dbeta_denomDv3)/(beta_denom);
    dbetaDv4 = (KP_DEV_t*dbeta_nomDv4-KP_DEV_t*beta_nom/(beta_denom)*dbeta_denomDv4)/(beta_denom);
    dbetaDv5 = (KP_DEV_t*dbeta_nomDv5-KP_DEV_t*beta_nom/(beta_denom)*dbeta_denomDv5)/(beta_denom);
    beta = KP_DEV_t*beta_nom/(beta_denom);

    dbeta_clm_denomDv1 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp)))+e_clm2*powqs_qdp2)))*(((2.0*e_clmxmdm2_2*dpowqs_qdp2Dv1-2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp))*e_clm*mdm2*dqs_qdpDv1)/((g_clm+e_clm*mdm2*qs_qdp))+e_clm2*dpowqs_qdp2Dv1));
    dbeta_clm_denomDv3 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp)))+e_clm2*powqs_qdp2)))*(((2.0*e_clmxmdm2_2*dpowqs_qdp2Dv3-2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp))*e_clm*mdm2*dqs_qdpDv3)/((g_clm+e_clm*mdm2*qs_qdp))+e_clm2*dpowqs_qdp2Dv3));
    dbeta_clm_denomDv4 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp)))+e_clm2*powqs_qdp2)))*(((2.0*e_clmxmdm2_2*dpowqs_qdp2Dv4-2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp))*e_clm*mdm2*dqs_qdpDv4)/((g_clm+e_clm*mdm2*qs_qdp))+e_clm2*dpowqs_qdp2Dv4));
    dbeta_clm_denomDv5 = 1/(2*sqrt(((1.0+2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp)))+e_clm2*powqs_qdp2)))*(((2.0*e_clmxmdm2_2*dpowqs_qdp2Dv5-2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp))*e_clm*mdm2*dqs_qdpDv5)/((g_clm+e_clm*mdm2*qs_qdp))+e_clm2*dpowqs_qdp2Dv5));
    beta_clm_denom = sqrt(((1.0+2.0*e_clmxmdm2_2*powqs_qdp2/((g_clm+e_clm*mdm2*qs_qdp)))+e_clm2*powqs_qdp2));

    dbetaDv1 = (dbetaDv1-beta/(beta_clm_denom)*dbeta_clm_denomDv1)/(beta_clm_denom);
    dbetaDv3 = (dbetaDv3-beta/(beta_clm_denom)*dbeta_clm_denomDv3)/(beta_clm_denom);
    dbetaDv4 = (dbetaDv4-beta/(beta_clm_denom)*dbeta_clm_denomDv4)/(beta_clm_denom);
    dbetaDv5 = (dbetaDv5-beta/(beta_clm_denom)*dbeta_clm_denomDv5)/(beta_clm_denom);
    beta = beta/(beta_clm_denom);

    di0Dv1 = (2.0*nq*UT2*dbetaDv1+2.0*dnqDv1*UT2*beta)*inv_dqmip1;
    di0Dv3 = (2.0*nq*UT2*dbetaDv3+2.0*dnqDv3*UT2*beta)*inv_dqmip1;
    di0Dv4 = (2.0*nq*UT2*dbetaDv4+2.0*dnqDv4*UT2*beta)*inv_dqmip1;
    di0Dv5 = (2.0*nq*UT2*dbetaDv5+2.0*dnqDv5*UT2*beta)*inv_dqmip1;
    i0 = 2.0*nq*UT2*beta*inv_dqmip1;

    dIspecDv1 = (di0Dv1*WeffNF-i0*WeffNF/((Leff-deltal))*(-ddeltalDv1))/((Leff-deltal))*(Weff-model_.WEDGE)/(Weff);
    dIspecDv3 = (di0Dv3*WeffNF-i0*WeffNF/((Leff-deltal))*(-ddeltalDv3))/((Leff-deltal))*(Weff-model_.WEDGE)/(Weff);
    dIspecDv4 = (di0Dv4*WeffNF-i0*WeffNF/((Leff-deltal))*(-ddeltalDv4))/((Leff-deltal))*(Weff-model_.WEDGE)/(Weff);
    dIspecDv5 = (di0Dv5*WeffNF-i0*WeffNF/((Leff-deltal))*(-ddeltalDv5))/((Leff-deltal))*(Weff-model_.WEDGE)/(Weff);
    Ispec = i0*WeffNF/((Leff-deltal))*(Weff-model_.WEDGE)/(Weff);

    dvdseffDv1 = dvdseffDv3 = dvdseffDv4 = dvdseffDv5 = 0.0;
    dva_ditsDv1 = dva_ditsDv3 = dva_ditsDv4 = dva_ditsDv5 = 0.0;
    df_ditsDv1 = df_ditsDv3 = df_ditsDv4 = df_ditsDv5 = 0.0;
    if(model_.PDITS==0.0){
    dits_factor = 1.0;
    ddits_factorDv1 = ddits_factorDv3 = ddits_factorDv4 = ddits_factorDv5 = 0.0;
    } else {
    df_ditsDv1 = (-1.0/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))))*(-model_.FPROUT*sqrt(Leff)/((qI+2.0))*dqIDv1)/((qI+2.0)))/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))));
    df_ditsDv3 = (-1.0/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))))*(-model_.FPROUT*sqrt(Leff)/((qI+2.0))*dqIDv3)/((qI+2.0)))/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))));
    df_ditsDv4 = (-1.0/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))))*(-model_.FPROUT*sqrt(Leff)/((qI+2.0))*dqIDv4)/((qI+2.0)))/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))));
    df_ditsDv5 = (-1.0/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))))*(-model_.FPROUT*sqrt(Leff)/((qI+2.0))*dqIDv5)/((qI+2.0)))/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))));
    f_dits = 1.0/((1.0+model_.FPROUT*sqrt(Leff)/((qI+2.0))));

    dva_ditsDv1 = df_ditsDv1/(model_.PDITS)*(1.0+(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT));
    dva_ditsDv3 = (f_dits/(model_.PDITS)*(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT)*(model_.PDITSD*(dvdDv3-dvsDv3)*UT)+df_ditsDv3/(model_.PDITS)*(1.0+(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT)));
    dva_ditsDv4 = (f_dits/(model_.PDITS)*(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT)*(model_.PDITSD*(dvdDv4-dvsDv4)*UT)+df_ditsDv4/(model_.PDITS)*(1.0+(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT)));
    dva_ditsDv5 = (f_dits/(model_.PDITS)*(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT)*(model_.PDITSD*(dvdDv5-dvsDv5)*UT)+df_ditsDv5/(model_.PDITS)*(1.0+(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT)));
    va_dits = f_dits/(model_.PDITS)*(1.0+(1.0+model_.PDITSL*Leff)*exp(model_.PDITSD*(vd-vs)*UT));

    dvdseffDv1 = (dvdssatDv1-0.5*(dvdssatDv1+1/(2*sqrt((((vdssat-(vd-vs))-model_.DDITS)*((vdssat-(vd-vs))-model_.DDITS)+4.0*model_.DDITS*vdssat)))*(((((vdssat-(vd-vs))-model_.DDITS)*dvdssatDv1+dvdssatDv1*((vdssat-(vd-vs))-model_.DDITS))+4.0*model_.DDITS*dvdssatDv1))));
    dvdseffDv3 = (dvdssatDv3-0.5*((dvdssatDv3-(dvdDv3-dvsDv3))+1/(2*sqrt((((vdssat-(vd-vs))-model_.DDITS)*((vdssat-(vd-vs))-model_.DDITS)+4.0*model_.DDITS*vdssat)))*(((((vdssat-(vd-vs))-model_.DDITS)*(dvdssatDv3-(dvdDv3-dvsDv3))+(dvdssatDv3-(dvdDv3-dvsDv3))*((vdssat-(vd-vs))-model_.DDITS))+4.0*model_.DDITS*dvdssatDv3))));
    dvdseffDv4 = (dvdssatDv4-0.5*((dvdssatDv4-(dvdDv4-dvsDv4))+1/(2*sqrt((((vdssat-(vd-vs))-model_.DDITS)*((vdssat-(vd-vs))-model_.DDITS)+4.0*model_.DDITS*vdssat)))*(((((vdssat-(vd-vs))-model_.DDITS)*(dvdssatDv4-(dvdDv4-dvsDv4))+(dvdssatDv4-(dvdDv4-dvsDv4))*((vdssat-(vd-vs))-model_.DDITS))+4.0*model_.DDITS*dvdssatDv4))));
    dvdseffDv5 = (dvdssatDv5-0.5*((dvdssatDv5-(dvdDv5-dvsDv5))+1/(2*sqrt((((vdssat-(vd-vs))-model_.DDITS)*((vdssat-(vd-vs))-model_.DDITS)+4.0*model_.DDITS*vdssat)))*(((((vdssat-(vd-vs))-model_.DDITS)*(dvdssatDv5-(dvdDv5-dvsDv5))+(dvdssatDv5-(dvdDv5-dvsDv5))*((vdssat-(vd-vs))-model_.DDITS))+4.0*model_.DDITS*dvdssatDv5))));
    vdseff = (vdssat-0.5*(((vdssat-(vd-vs))-model_.DDITS)+sqrt((((vdssat-(vd-vs))-model_.DDITS)*((vdssat-(vd-vs))-model_.DDITS)+4.0*model_.DDITS*vdssat))));

    ddits_factorDv1 = ((-dvdseffDv1)-((vd-vs)-vdseff)/(va_dits)*dva_ditsDv1)/(va_dits);
    ddits_factorDv3 = (((dvdDv3-dvsDv3)-dvdseffDv3)-((vd-vs)-vdseff)/(va_dits)*dva_ditsDv3)/(va_dits);
    ddits_factorDv4 = (((dvdDv4-dvsDv4)-dvdseffDv4)-((vd-vs)-vdseff)/(va_dits)*dva_ditsDv4)/(va_dits);
    ddits_factorDv5 = (((dvdDv5-dvsDv5)-dvdseffDv5)-((vd-vs)-vdseff)/(va_dits)*dva_ditsDv5)/(va_dits);
    dits_factor = (1.0+((vd-vs)-vdseff)/(va_dits));

    }
    dQSDv1 = dqSDv1*Q0;
    dQSDv3 = dqSDv3*Q0;
    dQSDv4 = dqSDv4*Q0;
    dQSDv5 = dqSDv5*Q0;
    QS = qS*Q0;

    dQDDv1 = dqDDv1*Q0;
    dQDDv3 = dqDDv3*Q0;
    dQDDv4 = dqDDv4*Q0;
    dQDDv5 = dqDDv5*Q0;
    QD = qD*Q0;

    dQGDv1 = (-dqGDv1)*Q0;
    dQGDv3 = (-dqGDv3)*Q0;
    dQGDv4 = (-dqGDv4)*Q0;
    dQGDv5 = (-dqGDv5)*Q0;
    QG = (-qG)*Q0;

    dQBDv1 = (((-dQSDv1)-dQDDv1)-dQGDv1);
    dQBDv3 = (((-dQSDv3)-dQDDv3)-dQGDv3);
    dQBDv4 = (((-dQSDv4)-dQDDv4)-dQGDv4);
    dQBDv5 = (((-dQSDv5)-dQDDv5)-dQGDv5);
    QB = (((-QS)-QD)-QG);

    dIDSDv1 = (Ispec*i*ddits_factorDv1+(Ispec*diDv1+dIspecDv1*i)*dits_factor);
    dIDSDv3 = (Ispec*i*ddits_factorDv3+(Ispec*diDv3+dIspecDv3*i)*dits_factor);
    dIDSDv4 = (Ispec*i*ddits_factorDv4+(Ispec*diDv4+dIspecDv4*i)*dits_factor);
    dIDSDv5 = (Ispec*i*ddits_factorDv5+(Ispec*diDv5+dIspecDv5*i)*dits_factor);
    IDS = Ispec*i*dits_factor;

    jss_t = model_.JSS*temp_arg_S;
    jssws_t = model_.JSSWS*temp_arg_S;
    jsswgs_t = model_.JSSWGS*temp_arg_S;
    pbs_t = model_.PBS-(model_.TPB*dT);
    pbsws_t = model_.PBSWS-(model_.TPBSW*dT);
    pbswgs_t = model_.PBSWGS-(model_.TPBSWG*dT);
    cjs_t = model_.CJS*(1.0+model_.TCJ*dT);
    cjsws_t = model_.CJSWS*(1.0+model_.TCJSW*dT);
    cjswgs_t = model_.CJSWGS*(1.0+model_.TCJSWG*dT);
    jtss_t = model_.JTSS*exp((-eg_nom)/UT*model_.XTSS*(1.0-rT));
    jtssws_t = model_.JTSSWS*exp((-eg_nom)/UT*model_.XTSSWS*(1.0-rT));
    jtsswgs_t = model_.JTSSWGS*exp((-eg_nom)/UT*model_.XTSSWGS*(1.0-rT));
    njtss_t = model_.NJTSS*(1.0+(rT-1.0)*model_.TNJTSS);
    njtssws_t = model_.NJTSSWS*(1.0+(rT-1.0)*model_.TNJTSSWS);
    njtsswgs_t = model_.NJTSSWGS*(1.0+(rT-1.0)*model_.TNJTSSWGS);
    jsd_t = model_.JSD*temp_arg_D;
    jsswd_t = model_.JSSWD*temp_arg_D;
    jsswgd_t = model_.JSSWGD*temp_arg_D;
    pbd_t = model_.PBD-(model_.TPB*dT);
    pbswd_t = model_.PBSWD-(model_.TPBSW*dT);
    pbswgd_t = model_.PBSWGD-(model_.TPBSWG*dT);
    cjd_t = model_.CJD*(1.0+model_.TCJ*dT);
    cjswd_t = model_.CJSWD*(1.0+model_.TCJSW*dT);
    cjswgd_t = model_.CJSWGD*(1.0+model_.TCJSWG*dT);
    jtsd_t = model_.JTSD*exp((-eg_nom)/UT*model_.XTSD*(1.0-rT));
    jtsswd_t = model_.JTSSWD*exp((-eg_nom)/UT*model_.XTSSWD*(1.0-rT));
    jtsswgd_t = model_.JTSSWGD*exp((-eg_nom)/UT*model_.XTSSWGD*(1.0-rT));
    njtsd_t = model_.NJTSD*(1.0+(rT-1.0)*model_.TNJTSD);
    njtsswd_t = model_.NJTSSWD*(1.0+(rT-1.0)*model_.TNJTSSWD);
    njtsswgd_t = model_.NJTSSWGD*(1.0+(rT-1.0)*model_.TNJTSSWGD);
    if((AS==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    as = hdif*Weff*(NF+2);
    } else {
    as = hdif*Weff*(NF+1);
    }
    } else {
    as = AS*model_.SCALE*model_.SCALE;
    }
    if((PS==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    ps = 2.0*(hdif*(NF+2)+Weff);
    } else {
    ps = 2.0*hdif*(NF+1)+Weff;
    }
    } else {
    ps = PS*model_.SCALE;
    }
    if((AD==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    ad = hdif*Weff*(NF);
    } else {
    ad = hdif*Weff*(NF+1);
    }
    } else {
    ad = AD*model_.SCALE*model_.SCALE;
    }
    if((PD==0.0)&&(model_.HDIF>0.0)){
    if(int(NF)%2==0){
    pd = 2.0*hdif*NF;
    } else {
    pd = 2.0*hdif*(NF+1)+Weff;
    }
    } else {
    pd = PD*model_.SCALE;
    }
    dv_si_bDv3 = model_.SIGN*(-dVbDv3);
    dv_si_bDv5 = model_.SIGN*dVsiDv5;
    v_si_b = model_.SIGN*(Vsi-Vb);

    dv_di_bDv3 = model_.SIGN*(-dVbDv3);
    dv_di_bDv4 = model_.SIGN*dVdiDv4;
    v_di_b = model_.SIGN*(Vdi-Vb);

    is_s = jss_t*as+jssws_t*ps+jsswgs_t*WeffNF;
    darg_sDv3 = (-dv_si_bDv3)*rT/(UT*model_.NJS);
    darg_sDv5 = (-dv_si_bDv5)*rT/(UT*model_.NJS);
    arg_s = (-v_si_b)*rT/(UT*model_.NJS);

    if(arg_s<(-40.0)){
    arg_s = (-40.0);
    darg_sDv3 = darg_sDv5 = 0.0;
    }
    df_breakdown_sDv3 = model_.XJBVS*exp((-((-v_si_b)+model_.BVS))*rT/(UT*model_.NJS))*((-(-dv_si_bDv3))*rT/(UT*model_.NJS));
    df_breakdown_sDv5 = model_.XJBVS*exp((-((-v_si_b)+model_.BVS))*rT/(UT*model_.NJS))*((-(-dv_si_bDv5))*rT/(UT*model_.NJS));
    f_breakdown_s = (1.0+model_.XJBVS*exp((-((-v_si_b)+model_.BVS))*rT/(UT*model_.NJS)));

    disb_tunDv3 = WeffNF*jtsswgs_t*exp(v_si_b*rT/(UT*njtsswgs_t)*model_.VTSSWGS/(max((model_.VTSSWGS+v_si_b),1.0E-3)))*((dv_si_bDv3*rT/(UT*njtsswgs_t)*model_.VTSSWGS-v_si_b*rT/(UT*njtsswgs_t)*model_.VTSSWGS/(max((model_.VTSSWGS+v_si_b),1.0E-3))*(((model_.VTSSWGS+v_si_b)>1.0E-3)?dv_si_bDv3:0))/(max((model_.VTSSWGS+v_si_b),1.0E-3)));
    disb_tunDv5 = WeffNF*jtsswgs_t*exp(v_si_b*rT/(UT*njtsswgs_t)*model_.VTSSWGS/(max((model_.VTSSWGS+v_si_b),1.0E-3)))*((dv_si_bDv5*rT/(UT*njtsswgs_t)*model_.VTSSWGS-v_si_b*rT/(UT*njtsswgs_t)*model_.VTSSWGS/(max((model_.VTSSWGS+v_si_b),1.0E-3))*(((model_.VTSSWGS+v_si_b)>1.0E-3)?dv_si_bDv5:0))/(max((model_.VTSSWGS+v_si_b),1.0E-3)));
    isb_tun = WeffNF*jtsswgs_t*(exp(v_si_b*rT/(UT*njtsswgs_t)*model_.VTSSWGS/(max((model_.VTSSWGS+v_si_b),1.0E-3)))-1.0);

    disb_tunDv3 = (disb_tunDv3+ps*jtssws_t*exp(v_si_b*rT/(UT*njtssws_t)*model_.VTSSWS/(max((model_.VTSSWS+v_si_b),1.0E-3)))*((dv_si_bDv3*rT/(UT*njtssws_t)*model_.VTSSWS-v_si_b*rT/(UT*njtssws_t)*model_.VTSSWS/(max((model_.VTSSWS+v_si_b),1.0E-3))*(((model_.VTSSWS+v_si_b)>1.0E-3)?dv_si_bDv3:0))/(max((model_.VTSSWS+v_si_b),1.0E-3))));
    disb_tunDv5 = (disb_tunDv5+ps*jtssws_t*exp(v_si_b*rT/(UT*njtssws_t)*model_.VTSSWS/(max((model_.VTSSWS+v_si_b),1.0E-3)))*((dv_si_bDv5*rT/(UT*njtssws_t)*model_.VTSSWS-v_si_b*rT/(UT*njtssws_t)*model_.VTSSWS/(max((model_.VTSSWS+v_si_b),1.0E-3))*(((model_.VTSSWS+v_si_b)>1.0E-3)?dv_si_bDv5:0))/(max((model_.VTSSWS+v_si_b),1.0E-3))));
    isb_tun = (isb_tun+ps*jtssws_t*(exp(v_si_b*rT/(UT*njtssws_t)*model_.VTSSWS/(max((model_.VTSSWS+v_si_b),1.0E-3)))-1.0));

    disb_tunDv3 = (disb_tunDv3+as*jtss_t*exp(v_si_b*rT/(UT*njtss_t)*model_.VTSS/(max((model_.VTSS+v_si_b),1.0E-3)))*((dv_si_bDv3*rT/(UT*njtss_t)*model_.VTSS-v_si_b*rT/(UT*njtss_t)*model_.VTSS/(max((model_.VTSS+v_si_b),1.0E-3))*(((model_.VTSS+v_si_b)>1.0E-3)?dv_si_bDv3:0))/(max((model_.VTSS+v_si_b),1.0E-3))));
    disb_tunDv5 = (disb_tunDv5+as*jtss_t*exp(v_si_b*rT/(UT*njtss_t)*model_.VTSS/(max((model_.VTSS+v_si_b),1.0E-3)))*((dv_si_bDv5*rT/(UT*njtss_t)*model_.VTSS-v_si_b*rT/(UT*njtss_t)*model_.VTSS/(max((model_.VTSS+v_si_b),1.0E-3))*(((model_.VTSS+v_si_b)>1.0E-3)?dv_si_bDv5:0))/(max((model_.VTSS+v_si_b),1.0E-3))));
    isb_tun = (isb_tun+as*jtss_t*(exp(v_si_b*rT/(UT*njtss_t)*model_.VTSS/(max((model_.VTSS+v_si_b),1.0E-3)))-1.0));

    dISBJDv3 = (((is_s*(1.0-exp(arg_s))*df_breakdown_sDv3+is_s*(-exp(arg_s)*(darg_sDv3))*f_breakdown_s)+dv_si_bDv3*model_.GMIN)+disb_tunDv3);
    dISBJDv5 = (((is_s*(1.0-exp(arg_s))*df_breakdown_sDv5+is_s*(-exp(arg_s)*(darg_sDv5))*f_breakdown_s)+dv_si_bDv5*model_.GMIN)+disb_tunDv5);
    ISBJ = ((is_s*(1.0-exp(arg_s))*f_breakdown_s+v_si_b*model_.GMIN)+isb_tun);

    is_d = jsd_t*ad+jsswd_t*pd+jsswgd_t*WeffNF;
    darg_dDv3 = (-dv_di_bDv3)*rT/(UT*model_.NJD);
    darg_dDv4 = (-dv_di_bDv4)*rT/(UT*model_.NJD);
    arg_d = (-v_di_b)*rT/(UT*model_.NJD);

    if(arg_d<(-40.0)){
    arg_d = (-40.0);
    darg_dDv3 = darg_dDv4 = 0.0;
    }
    df_breakdown_dDv3 = model_.XJBVD*exp((-((-v_di_b)+model_.BVD))*rT/(UT*model_.NJD))*((-(-dv_di_bDv3))*rT/(UT*model_.NJD));
    df_breakdown_dDv4 = model_.XJBVD*exp((-((-v_di_b)+model_.BVD))*rT/(UT*model_.NJD))*((-(-dv_di_bDv4))*rT/(UT*model_.NJD));
    f_breakdown_d = (1.0+model_.XJBVD*exp((-((-v_di_b)+model_.BVD))*rT/(UT*model_.NJD)));

    didb_tunDv3 = WeffNF*jtsswgd_t*exp(v_di_b*rT/(UT*njtsswgd_t)*model_.VTSSWGD/(max((model_.VTSSWGD+v_di_b),1.0E-3)))*((dv_di_bDv3*rT/(UT*njtsswgd_t)*model_.VTSSWGD-v_di_b*rT/(UT*njtsswgd_t)*model_.VTSSWGD/(max((model_.VTSSWGD+v_di_b),1.0E-3))*(((model_.VTSSWGD+v_di_b)>1.0E-3)?dv_di_bDv3:0))/(max((model_.VTSSWGD+v_di_b),1.0E-3)));
    didb_tunDv4 = WeffNF*jtsswgd_t*exp(v_di_b*rT/(UT*njtsswgd_t)*model_.VTSSWGD/(max((model_.VTSSWGD+v_di_b),1.0E-3)))*((dv_di_bDv4*rT/(UT*njtsswgd_t)*model_.VTSSWGD-v_di_b*rT/(UT*njtsswgd_t)*model_.VTSSWGD/(max((model_.VTSSWGD+v_di_b),1.0E-3))*(((model_.VTSSWGD+v_di_b)>1.0E-3)?dv_di_bDv4:0))/(max((model_.VTSSWGD+v_di_b),1.0E-3)));
    idb_tun = WeffNF*jtsswgd_t*(exp(v_di_b*rT/(UT*njtsswgd_t)*model_.VTSSWGD/(max((model_.VTSSWGD+v_di_b),1.0E-3)))-1.0);

    didb_tunDv3 = (didb_tunDv3+pd*jtsswd_t*exp(v_di_b*rT/(UT*njtsswd_t)*model_.VTSSWD/(max((model_.VTSSWD+v_di_b),1.0E-3)))*((dv_di_bDv3*rT/(UT*njtsswd_t)*model_.VTSSWD-v_di_b*rT/(UT*njtsswd_t)*model_.VTSSWD/(max((model_.VTSSWD+v_di_b),1.0E-3))*(((model_.VTSSWD+v_di_b)>1.0E-3)?dv_di_bDv3:0))/(max((model_.VTSSWD+v_di_b),1.0E-3))));
    didb_tunDv4 = (didb_tunDv4+pd*jtsswd_t*exp(v_di_b*rT/(UT*njtsswd_t)*model_.VTSSWD/(max((model_.VTSSWD+v_di_b),1.0E-3)))*((dv_di_bDv4*rT/(UT*njtsswd_t)*model_.VTSSWD-v_di_b*rT/(UT*njtsswd_t)*model_.VTSSWD/(max((model_.VTSSWD+v_di_b),1.0E-3))*(((model_.VTSSWD+v_di_b)>1.0E-3)?dv_di_bDv4:0))/(max((model_.VTSSWD+v_di_b),1.0E-3))));
    idb_tun = (idb_tun+pd*jtsswd_t*(exp(v_di_b*rT/(UT*njtsswd_t)*model_.VTSSWD/(max((model_.VTSSWD+v_di_b),1.0E-3)))-1.0));

    didb_tunDv3 = (didb_tunDv3+ad*jtsd_t*exp(v_di_b*rT/(UT*njtsd_t)*model_.VTSD/(max((model_.VTSD+v_di_b),1.0E-3)))*((dv_di_bDv3*rT/(UT*njtsd_t)*model_.VTSD-v_di_b*rT/(UT*njtsd_t)*model_.VTSD/(max((model_.VTSD+v_di_b),1.0E-3))*(((model_.VTSD+v_di_b)>1.0E-3)?dv_di_bDv3:0))/(max((model_.VTSD+v_di_b),1.0E-3))));
    didb_tunDv4 = (didb_tunDv4+ad*jtsd_t*exp(v_di_b*rT/(UT*njtsd_t)*model_.VTSD/(max((model_.VTSD+v_di_b),1.0E-3)))*((dv_di_bDv4*rT/(UT*njtsd_t)*model_.VTSD-v_di_b*rT/(UT*njtsd_t)*model_.VTSD/(max((model_.VTSD+v_di_b),1.0E-3))*(((model_.VTSD+v_di_b)>1.0E-3)?dv_di_bDv4:0))/(max((model_.VTSD+v_di_b),1.0E-3))));
    idb_tun = (idb_tun+ad*jtsd_t*(exp(v_di_b*rT/(UT*njtsd_t)*model_.VTSD/(max((model_.VTSD+v_di_b),1.0E-3)))-1.0));

    dIDBJDv3 = (((is_d*(1.0-exp(arg_d))*df_breakdown_dDv3+is_d*(-exp(arg_d)*(darg_dDv3))*f_breakdown_d)+dv_di_bDv3*model_.GMIN)+didb_tunDv3);
    dIDBJDv4 = (((is_d*(1.0-exp(arg_d))*df_breakdown_dDv4+is_d*(-exp(arg_d)*(darg_dDv4))*f_breakdown_d)+dv_di_bDv4*model_.GMIN)+didb_tunDv4);
    IDBJ = ((is_d*(1.0-exp(arg_d))*f_breakdown_d+v_di_b*model_.GMIN)+idb_tun);

    if(v_si_b>0.0){
    dcsb_sDv3 = cjs_t*as*exp((-model_.MJS)*log((1.0+v_si_b/(pbs_t))))*(((-model_.MJS)*1/((1.0+v_si_b/(pbs_t)))*(dv_si_bDv3/(pbs_t))+(-0)*log((1.0+v_si_b/(pbs_t)))));
    dcsb_sDv5 = cjs_t*as*exp((-model_.MJS)*log((1.0+v_si_b/(pbs_t))))*(((-model_.MJS)*1/((1.0+v_si_b/(pbs_t)))*(dv_si_bDv5/(pbs_t))+(-0)*log((1.0+v_si_b/(pbs_t)))));
    csb_s = cjs_t*as*exp((-model_.MJS)*log((1.0+v_si_b/(pbs_t))));

    dcssw_sDv3 = cjsws_t*ps*exp((-model_.MJSWS)*log((1.0+v_si_b/(pbsws_t))))*(((-model_.MJSWS)*1/((1.0+v_si_b/(pbsws_t)))*(dv_si_bDv3/(pbsws_t))+(-0)*log((1.0+v_si_b/(pbsws_t)))));
    dcssw_sDv5 = cjsws_t*ps*exp((-model_.MJSWS)*log((1.0+v_si_b/(pbsws_t))))*(((-model_.MJSWS)*1/((1.0+v_si_b/(pbsws_t)))*(dv_si_bDv5/(pbsws_t))+(-0)*log((1.0+v_si_b/(pbsws_t)))));
    cssw_s = cjsws_t*ps*exp((-model_.MJSWS)*log((1.0+v_si_b/(pbsws_t))));

    dcsswg_sDv3 = cjswgs_t*WeffNF*exp((-model_.MJSWGS)*log((1.0+v_si_b/(pbswgs_t))))*(((-model_.MJSWGS)*1/((1.0+v_si_b/(pbswgs_t)))*(dv_si_bDv3/(pbswgs_t))+(-0)*log((1.0+v_si_b/(pbswgs_t)))));
    dcsswg_sDv5 = cjswgs_t*WeffNF*exp((-model_.MJSWGS)*log((1.0+v_si_b/(pbswgs_t))))*(((-model_.MJSWGS)*1/((1.0+v_si_b/(pbswgs_t)))*(dv_si_bDv5/(pbswgs_t))+(-0)*log((1.0+v_si_b/(pbswgs_t)))));
    csswg_s = cjswgs_t*WeffNF*exp((-model_.MJSWGS)*log((1.0+v_si_b/(pbswgs_t))));

    dqsb_sDv3 = cjs_t*as*pbs_t*(-exp((1.0-model_.MJS)*log((1.0+v_si_b/(pbs_t))))*((1.0-model_.MJS)*1/((1.0+v_si_b/(pbs_t)))*(dv_si_bDv3/(pbs_t))))/((1.0-model_.MJS));
    dqsb_sDv5 = cjs_t*as*pbs_t*(-exp((1.0-model_.MJS)*log((1.0+v_si_b/(pbs_t))))*((1.0-model_.MJS)*1/((1.0+v_si_b/(pbs_t)))*(dv_si_bDv5/(pbs_t))))/((1.0-model_.MJS));
    qsb_s = cjs_t*as*pbs_t*(1.0-exp((1.0-model_.MJS)*log((1.0+v_si_b/(pbs_t)))))/((1.0-model_.MJS));

    dqssw_sDv3 = cjsws_t*ps*pbsws_t*(-exp((1.0-model_.MJSWS)*log((1.0+v_si_b/(pbsws_t))))*((1.0-model_.MJSWS)*1/((1.0+v_si_b/(pbsws_t)))*(dv_si_bDv3/(pbsws_t))))/((1.0-model_.MJSWS));
    dqssw_sDv5 = cjsws_t*ps*pbsws_t*(-exp((1.0-model_.MJSWS)*log((1.0+v_si_b/(pbsws_t))))*((1.0-model_.MJSWS)*1/((1.0+v_si_b/(pbsws_t)))*(dv_si_bDv5/(pbsws_t))))/((1.0-model_.MJSWS));
    qssw_s = cjsws_t*ps*pbsws_t*(1.0-exp((1.0-model_.MJSWS)*log((1.0+v_si_b/(pbsws_t)))))/((1.0-model_.MJSWS));

    dqsswg_sDv3 = cjswgs_t*WeffNF*pbswgs_t*(-exp((1.0-model_.MJSWGS)*log((1.0+v_si_b/(pbswgs_t))))*((1.0-model_.MJSWGS)*1/((1.0+v_si_b/(pbswgs_t)))*(dv_si_bDv3/(pbswgs_t))))/((1.0-model_.MJSWGS));
    dqsswg_sDv5 = cjswgs_t*WeffNF*pbswgs_t*(-exp((1.0-model_.MJSWGS)*log((1.0+v_si_b/(pbswgs_t))))*((1.0-model_.MJSWGS)*1/((1.0+v_si_b/(pbswgs_t)))*(dv_si_bDv5/(pbswgs_t))))/((1.0-model_.MJSWGS));
    qsswg_s = cjswgs_t*WeffNF*pbswgs_t*(1.0-exp((1.0-model_.MJSWGS)*log((1.0+v_si_b/(pbswgs_t)))))/((1.0-model_.MJSWGS));

    } else {
    dcsb_sDv3 = cjs_t*as*(-model_.MJS*dv_si_bDv3/(pbs_t));
    dcsb_sDv5 = cjs_t*as*(-model_.MJS*dv_si_bDv5/(pbs_t));
    csb_s = cjs_t*as*(1.0-model_.MJS*v_si_b/(pbs_t));

    dcssw_sDv3 = cjsws_t*ps*(-model_.MJSWS*dv_si_bDv3/(pbsws_t));
    dcssw_sDv5 = cjsws_t*ps*(-model_.MJSWS*dv_si_bDv5/(pbsws_t));
    cssw_s = cjsws_t*ps*(1.0-model_.MJSWS*v_si_b/(pbsws_t));

    dcsswg_sDv3 = cjswgs_t*WeffNF*(-model_.MJSWGS*dv_si_bDv3/(pbswgs_t));
    dcsswg_sDv5 = cjswgs_t*WeffNF*(-model_.MJSWGS*dv_si_bDv5/(pbswgs_t));
    csswg_s = cjswgs_t*WeffNF*(1.0-model_.MJSWGS*v_si_b/(pbswgs_t));

    dqsb_sDv3 = cjs_t*as*((-dv_si_bDv3)+model_.MJS*0.5/(pbs_t)*(v_si_b*dv_si_bDv3+dv_si_bDv3*v_si_b));
    dqsb_sDv5 = cjs_t*as*((-dv_si_bDv5)+model_.MJS*0.5/(pbs_t)*(v_si_b*dv_si_bDv5+dv_si_bDv5*v_si_b));
    qsb_s = cjs_t*as*((-v_si_b)+model_.MJS*0.5/(pbs_t)*v_si_b*v_si_b);

    dqssw_sDv3 = cjsws_t*ps*((-dv_si_bDv3)+model_.MJSWS*0.5/(pbsws_t)*(v_si_b*dv_si_bDv3+dv_si_bDv3*v_si_b));
    dqssw_sDv5 = cjsws_t*ps*((-dv_si_bDv5)+model_.MJSWS*0.5/(pbsws_t)*(v_si_b*dv_si_bDv5+dv_si_bDv5*v_si_b));
    qssw_s = cjsws_t*ps*((-v_si_b)+model_.MJSWS*0.5/(pbsws_t)*v_si_b*v_si_b);

    dqsswg_sDv3 = cjswgs_t*WeffNF*((-dv_si_bDv3)+model_.MJSWGS*0.5/(pbswgs_t)*(v_si_b*dv_si_bDv3+dv_si_bDv3*v_si_b));
    dqsswg_sDv5 = cjswgs_t*WeffNF*((-dv_si_bDv5)+model_.MJSWGS*0.5/(pbswgs_t)*(v_si_b*dv_si_bDv5+dv_si_bDv5*v_si_b));
    qsswg_s = cjswgs_t*WeffNF*((-v_si_b)+model_.MJSWGS*0.5/(pbswgs_t)*v_si_b*v_si_b);

    }
    dCSBJDv3 = ((dcsb_sDv3+dcssw_sDv3)+dcsswg_sDv3);
    dCSBJDv5 = ((dcsb_sDv5+dcssw_sDv5)+dcsswg_sDv5);
    CSBJ = ((csb_s+cssw_s)+csswg_s);

    dQSBJDv3 = (-((dqsb_sDv3+dqssw_sDv3)+dqsswg_sDv3));
    dQSBJDv5 = (-((dqsb_sDv5+dqssw_sDv5)+dqsswg_sDv5));
    QSBJ = (-((qsb_s+qssw_s)+qsswg_s));

    if(v_di_b>0.0){
    dcsb_dDv3 = cjd_t*ad*exp((-model_.MJD)*log((1.0+v_di_b/(pbd_t))))*(((-model_.MJD)*1/((1.0+v_di_b/(pbd_t)))*(dv_di_bDv3/(pbd_t))+(-0)*log((1.0+v_di_b/(pbd_t)))));
    dcsb_dDv4 = cjd_t*ad*exp((-model_.MJD)*log((1.0+v_di_b/(pbd_t))))*(((-model_.MJD)*1/((1.0+v_di_b/(pbd_t)))*(dv_di_bDv4/(pbd_t))+(-0)*log((1.0+v_di_b/(pbd_t)))));
    csb_d = cjd_t*ad*exp((-model_.MJD)*log((1.0+v_di_b/(pbd_t))));

    dcssw_dDv3 = cjswd_t*pd*exp((-model_.MJSWD)*log((1.0+v_di_b/(pbswd_t))))*(((-model_.MJSWD)*1/((1.0+v_di_b/(pbswd_t)))*(dv_di_bDv3/(pbswd_t))+(-0)*log((1.0+v_di_b/(pbswd_t)))));
    dcssw_dDv4 = cjswd_t*pd*exp((-model_.MJSWD)*log((1.0+v_di_b/(pbswd_t))))*(((-model_.MJSWD)*1/((1.0+v_di_b/(pbswd_t)))*(dv_di_bDv4/(pbswd_t))+(-0)*log((1.0+v_di_b/(pbswd_t)))));
    cssw_d = cjswd_t*pd*exp((-model_.MJSWD)*log((1.0+v_di_b/(pbswd_t))));

    dcsswg_dDv3 = cjswgd_t*WeffNF*exp((-model_.MJSWGD)*log((1.0+v_di_b/(pbswgd_t))))*(((-model_.MJSWGD)*1/((1.0+v_di_b/(pbswgd_t)))*(dv_di_bDv3/(pbswgd_t))+(-0)*log((1.0+v_di_b/(pbswgd_t)))));
    dcsswg_dDv4 = cjswgd_t*WeffNF*exp((-model_.MJSWGD)*log((1.0+v_di_b/(pbswgd_t))))*(((-model_.MJSWGD)*1/((1.0+v_di_b/(pbswgd_t)))*(dv_di_bDv4/(pbswgd_t))+(-0)*log((1.0+v_di_b/(pbswgd_t)))));
    csswg_d = cjswgd_t*WeffNF*exp((-model_.MJSWGD)*log((1.0+v_di_b/(pbswgd_t))));

    dqsb_dDv3 = cjd_t*ad*pbd_t*(-exp((1.0-model_.MJD)*log((1.0+v_di_b/(pbd_t))))*((1.0-model_.MJD)*1/((1.0+v_di_b/(pbd_t)))*(dv_di_bDv3/(pbd_t))))/((1.0-model_.MJD));
    dqsb_dDv4 = cjd_t*ad*pbd_t*(-exp((1.0-model_.MJD)*log((1.0+v_di_b/(pbd_t))))*((1.0-model_.MJD)*1/((1.0+v_di_b/(pbd_t)))*(dv_di_bDv4/(pbd_t))))/((1.0-model_.MJD));
    qsb_d = cjd_t*ad*pbd_t*(1.0-exp((1.0-model_.MJD)*log((1.0+v_di_b/(pbd_t)))))/((1.0-model_.MJD));

    dqssw_dDv3 = cjswd_t*pd*pbswd_t*(-exp((1.0-model_.MJSWD)*log((1.0+v_di_b/(pbswd_t))))*((1.0-model_.MJSWD)*1/((1.0+v_di_b/(pbswd_t)))*(dv_di_bDv3/(pbswd_t))))/((1.0-model_.MJSWD));
    dqssw_dDv4 = cjswd_t*pd*pbswd_t*(-exp((1.0-model_.MJSWD)*log((1.0+v_di_b/(pbswd_t))))*((1.0-model_.MJSWD)*1/((1.0+v_di_b/(pbswd_t)))*(dv_di_bDv4/(pbswd_t))))/((1.0-model_.MJSWD));
    qssw_d = cjswd_t*pd*pbswd_t*(1.0-exp((1.0-model_.MJSWD)*log((1.0+v_di_b/(pbswd_t)))))/((1.0-model_.MJSWD));

    dqsswg_dDv3 = cjswgd_t*WeffNF*pbswgd_t*(-exp((1.0-model_.MJSWGD)*log((1.0+v_di_b/(pbswgd_t))))*((1.0-model_.MJSWGD)*1/((1.0+v_di_b/(pbswgd_t)))*(dv_di_bDv3/(pbswgd_t))))/((1.0-model_.MJSWGD));
    dqsswg_dDv4 = cjswgd_t*WeffNF*pbswgd_t*(-exp((1.0-model_.MJSWGD)*log((1.0+v_di_b/(pbswgd_t))))*((1.0-model_.MJSWGD)*1/((1.0+v_di_b/(pbswgd_t)))*(dv_di_bDv4/(pbswgd_t))))/((1.0-model_.MJSWGD));
    qsswg_d = cjswgd_t*WeffNF*pbswgd_t*(1.0-exp((1.0-model_.MJSWGD)*log((1.0+v_di_b/(pbswgd_t)))))/((1.0-model_.MJSWGD));

    } else {
    dcsb_dDv3 = cjd_t*ad*(-model_.MJD*dv_di_bDv3/(pbd_t));
    dcsb_dDv4 = cjd_t*ad*(-model_.MJD*dv_di_bDv4/(pbd_t));
    csb_d = cjd_t*ad*(1.0-model_.MJD*v_di_b/(pbd_t));

    dcssw_dDv3 = cjswd_t*pd*(-model_.MJSWD*dv_di_bDv3/(pbswd_t));
    dcssw_dDv4 = cjswd_t*pd*(-model_.MJSWD*dv_di_bDv4/(pbswd_t));
    cssw_d = cjswd_t*pd*(1.0-model_.MJSWD*v_di_b/(pbswd_t));

    dcsswg_dDv3 = cjswgd_t*WeffNF*(-model_.MJSWGD*dv_di_bDv3/(pbswgd_t));
    dcsswg_dDv4 = cjswgd_t*WeffNF*(-model_.MJSWGD*dv_di_bDv4/(pbswgd_t));
    csswg_d = cjswgd_t*WeffNF*(1.0-model_.MJSWGD*v_di_b/(pbswgd_t));

    dqsb_dDv3 = cjd_t*ad*((-dv_di_bDv3)+model_.MJD*0.5/(pbd_t)*(v_di_b*dv_di_bDv3+dv_di_bDv3*v_di_b));
    dqsb_dDv4 = cjd_t*ad*((-dv_di_bDv4)+model_.MJD*0.5/(pbd_t)*(v_di_b*dv_di_bDv4+dv_di_bDv4*v_di_b));
    qsb_d = cjd_t*ad*((-v_di_b)+model_.MJD*0.5/(pbd_t)*v_di_b*v_di_b);

    dqssw_dDv3 = cjswd_t*pd*((-dv_di_bDv3)+model_.MJSWD*0.5/(pbswd_t)*(v_di_b*dv_di_bDv3+dv_di_bDv3*v_di_b));
    dqssw_dDv4 = cjswd_t*pd*((-dv_di_bDv4)+model_.MJSWD*0.5/(pbswd_t)*(v_di_b*dv_di_bDv4+dv_di_bDv4*v_di_b));
    qssw_d = cjswd_t*pd*((-v_di_b)+model_.MJSWD*0.5/(pbswd_t)*v_di_b*v_di_b);

    dqsswg_dDv3 = cjswgd_t*WeffNF*((-dv_di_bDv3)+model_.MJSWGD*0.5/(pbswgd_t)*(v_di_b*dv_di_bDv3+dv_di_bDv3*v_di_b));
    dqsswg_dDv4 = cjswgd_t*WeffNF*((-dv_di_bDv4)+model_.MJSWGD*0.5/(pbswgd_t)*(v_di_b*dv_di_bDv4+dv_di_bDv4*v_di_b));
    qsswg_d = cjswgd_t*WeffNF*((-v_di_b)+model_.MJSWGD*0.5/(pbswgd_t)*v_di_b*v_di_b);

    }
    dCDBJDv3 = ((dcsb_dDv3+dcssw_dDv3)+dcsswg_dDv3);
    dCDBJDv4 = ((dcsb_dDv4+dcssw_dDv4)+dcsswg_dDv4);
    CDBJ = ((csb_d+cssw_d)+csswg_d);

    dQDBJDv3 = (-((dqsb_dDv3+dqssw_dDv3)+dqsswg_dDv3));
    dQDBJDv4 = (-((dqsb_dDv4+dqssw_dDv4)+dqsswg_dDv4));
    QDBJ = (-((qsb_d+qssw_d)+qsswg_d));

    dcontributetmpDv3 = SIGN_M*dIDBJDv3;
    dcontributetmpDv4 = SIGN_M*dIDBJDv4;
    contributetmp = SIGN_M*IDBJ;

    dcontributetmporgDv3 = SIGN_M*dIDBJDv3;
    dcontributetmporgDv4 = SIGN_M*dIDBJDv4;
    contributetmporg = SIGN_M*IDBJ;

    fMat_r4c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r3c4 += -dcontributetmpDv4;
    dcontributetmpDv3 = SIGN_M*dISBJDv3;
    dcontributetmpDv5 = SIGN_M*dISBJDv5;
    contributetmp = SIGN_M*ISBJ;

    dcontributetmporgDv3 = SIGN_M*dISBJDv3;
    dcontributetmporgDv5 = SIGN_M*dISBJDv5;
    contributetmporg = SIGN_M*ISBJ;

    fMat_r5c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r3c5 += -dcontributetmpDv5;
    dDdtExp0Dv3 = dQDBJDv3;
    dDdtExp0Dv4 = dQDBJDv4;
    DdtExp0 = QDBJ;

    dDdtAns0Dv3 = 0;
    dDdtAns0Dv4 = 0;
    DdtAns0 = DdtExp0;

    dDdtAns0Dv3 = dDdtExp0Dv3 * _der0;
    dDdtAns0Dv4 = dDdtExp0Dv4 * _der0;
    dcontributetmpDv3 = SIGN_M*0.0;
    dcontributetmpDv4 = SIGN_M*0.0;
    contributetmp = SIGN_M*DdtAns0;

    dcontributetmporgDv3 = SIGN_M*dDdtAns0Dv3;
    dcontributetmporgDv4 = SIGN_M*dDdtAns0Dv4;
    contributetmporg = SIGN_M*DdtAns0;

    fMat_r4c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    qMat_r4c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r3c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r3c4 += -dcontributetmpDv4;
    qMat_r4c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r3c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    dDdtExp1Dv3 = dQSBJDv3;
    dDdtExp1Dv5 = dQSBJDv5;
    DdtExp1 = QSBJ;

    dDdtAns1Dv3 = 0;
    dDdtAns1Dv5 = 0;
    DdtAns1 = DdtExp1;

    dDdtAns1Dv3 = dDdtExp1Dv3 * _der0;
    dDdtAns1Dv5 = dDdtExp1Dv5 * _der0;
    dcontributetmpDv3 = SIGN_M*0.0;
    dcontributetmpDv5 = SIGN_M*0.0;
    contributetmp = SIGN_M*DdtAns1;

    dcontributetmporgDv3 = SIGN_M*dDdtAns1Dv3;
    dcontributetmporgDv5 = SIGN_M*dDdtAns1Dv5;
    contributetmporg = SIGN_M*DdtAns1;

    fMat_r5c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    qMat_r5c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r3c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r3c5 += -dcontributetmpDv5;
    qMat_r5c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r3c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    if(model_.RLX<0.0){
    if(model_.RSX<0.0){
    rs = (hdif*model_.RSH+(ldif-model_.DL/2.0)*model_.RS)/WeffNF;
    } else {
    rs = model_.RSX/WeffNF;
    }
    if(model_.RDX<0.0){
    rd = (hdif*model_.RSH+(ldif-model_.DL/2.0)*model_.RD)/WeffNF;
    } else {
    rd = model_.RDX/WeffNF;
    }
    } else {
    rs = model_.RLX/WeffNF;
    rd = rs;
    }
    tmp = (1.0+model_.WRLX/Weff);
    rs = rs*tmp;
    rd = rd*tmp;
    rg = model_.RGSH*Weff/(3.0*model_.GC*model_.GC*NF*Leff)*(1.0+model_.KRGL1*Leff*Leff);
    if(model_.RINGTYPE==1.0){
    rb = (model_.RBN==0.0)?model_.RBWSH*0.5/Weff : 1.0/((Weff*2.0/model_.RBWSH)+(NF/model_.RBN));
    if(int(NF)%2==0){
    rsb = (model_.RSBN==0.0)?model_.RSBWSH*0.5/Weff : 1.0/((Weff*2.0/model_.RSBWSH)+(NF/model_.RSBN));
    rdb = (model_.RDBN==0.0)?model_.RDBWSH*0.5/Weff : 1.0/((Weff*2.0/model_.RDBWSH)+(NF/model_.RDBN));
    } else {
    rsb = (model_.RSBN==0.0)?model_.RSBWSH/Weff : 1.0/((Weff/model_.RSBWSH)+(NF/model_.RSBN));
    rdb = rsb;
    }
    } else {
    rb = model_.RBWSH*0.5/Weff;
    if(int(NF)%2==0){
    rsb = model_.RSBWSH*0.5/Weff;
    rdb = model_.RDBWSH*0.5/Weff;
    } else {
    rsb = model_.RSBWSH/Weff;
    rdb = rsb;
    }
    }
    rdsb = model_.RDSBSH*Leff/WeffNF;
    tmp = (1.0+model_.TR*dT+model_.TR2*dT2);
    rs = rs*tmp;
    rd = rd*tmp;
    rg = rg*tmp;
    rb = rb*tmp;
    rsb = rsb*tmp;
    rdb = rdb*tmp;
    rdsb = rdsb*tmp;
    rs = ((rs)>((1.0E-3))?(rs) : ((1.0E-3)));
    rd = ((rd)>((1.0E-3))?(rd) : ((1.0E-3)));
    rg = ((rg)>((1.0E-3))?(rg) : ((1.0E-3)));
    rb = ((rb)>((1.0E-3))?(rb) : ((1.0E-3)));
    rsb = ((rsb)>((1.0E-3))?(rsb) : ((1.0E-3)));
    rdb = ((rdb)>((1.0E-3))?(rdb) : ((1.0E-3)));
    rdsb = ((rdsb)>((1.0E-3))?(rdsb) : ((1.0E-3)));
    dDdtExp2Dv1 = model_.CGSO*M*WeffNF*dVgDv1;
    dDdtExp2Dv5 = model_.CGSO*M*WeffNF*(-dVsiDv5);
    DdtExp2 = model_.CGSO*M*WeffNF*(Vg-Vsi);

    dDdtAns2Dv1 = 0;
    dDdtAns2Dv5 = 0;
    DdtAns2 = DdtExp2;

    dDdtAns2Dv1 = dDdtExp2Dv1 * _der0;
    dDdtAns2Dv5 = dDdtExp2Dv5 * _der0;
    dcontributetmpDv1 = 0.0;
    dcontributetmpDv5 = 0.0;
    contributetmp = DdtAns2;

    dcontributetmporgDv1 = dDdtAns2Dv1;
    dcontributetmporgDv5 = dDdtAns2Dv5;
    contributetmporg = DdtAns2;

    fMat_r1c1 += dcontributetmpDv1;
    fMat_r5c1 += -dcontributetmpDv1;
    qMat_r1c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r5c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r1c5 += dcontributetmpDv5;
    fMat_r5c5 += -dcontributetmpDv5;
    qMat_r1c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r5c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dDdtExp3Dv1 = model_.CGDO*M*WeffNF*dVgDv1;
    dDdtExp3Dv4 = model_.CGDO*M*WeffNF*(-dVdiDv4);
    DdtExp3 = model_.CGDO*M*WeffNF*(Vg-Vdi);

    dDdtAns3Dv1 = 0;
    dDdtAns3Dv4 = 0;
    DdtAns3 = DdtExp3;

    dDdtAns3Dv1 = dDdtExp3Dv1 * _der0;
    dDdtAns3Dv4 = dDdtExp3Dv4 * _der0;
    dcontributetmpDv1 = 0.0;
    dcontributetmpDv4 = 0.0;
    contributetmp = DdtAns3;

    dcontributetmporgDv1 = dDdtAns3Dv1;
    dcontributetmporgDv4 = dDdtAns3Dv4;
    contributetmporg = DdtAns3;

    fMat_r1c1 += dcontributetmpDv1;
    fMat_r4c1 += -dcontributetmpDv1;
    qMat_r1c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r4c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r1c4 += dcontributetmpDv4;
    fMat_r4c4 += -dcontributetmpDv4;
    qMat_r1c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r4c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    dDdtExp4Dv1 = model_.CGBO*M*2.0*Leff*NF*dVgDv1;
    dDdtExp4Dv3 = model_.CGBO*M*2.0*Leff*NF*(-dVbDv3);
    DdtExp4 = model_.CGBO*M*2.0*Leff*NF*(Vg-Vb);

    dDdtAns4Dv1 = 0;
    dDdtAns4Dv3 = 0;
    DdtAns4 = DdtExp4;

    dDdtAns4Dv1 = dDdtExp4Dv1 * _der0;
    dDdtAns4Dv3 = dDdtExp4Dv3 * _der0;
    dcontributetmpDv1 = 0.0;
    dcontributetmpDv3 = 0.0;
    contributetmp = DdtAns4;

    dcontributetmporgDv1 = dDdtAns4Dv1;
    dcontributetmporgDv3 = dDdtAns4Dv3;
    contributetmporg = DdtAns4;

    fMat_r1c1 += dcontributetmpDv1;
    fMat_r3c1 += -dcontributetmpDv1;
    qMat_r1c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r3c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r1c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    qMat_r1c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r3c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    dcontributetmpDv2 = M*dVsDv2/(rs);
    dcontributetmpDv5 = M*(-dVsiDv5)/(rs);
    contributetmp = M*(Vs-Vsi)/(rs);

    dcontributetmporgDv2 = M*dVsDv2/(rs);
    dcontributetmporgDv5 = M*(-dVsiDv5)/(rs);
    contributetmporg = M*(Vs-Vsi)/(rs);

    fMat_r2c2 += dcontributetmpDv2;
    fMat_r5c2 += -dcontributetmpDv2;
    fMat_r2c5 += dcontributetmpDv5;
    fMat_r5c5 += -dcontributetmpDv5;
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
    dcontributetmpDv0 = M*dVdDv0/(rd);
    dcontributetmpDv4 = M*(-dVdiDv4)/(rd);
    contributetmp = M*(Vd-Vdi)/(rd);

    dcontributetmporgDv0 = M*dVdDv0/(rd);
    dcontributetmporgDv4 = M*(-dVdiDv4)/(rd);
    contributetmporg = M*(Vd-Vdi)/(rd);

    fMat_r0c0 += dcontributetmpDv0;
    fMat_r4c0 += -dcontributetmpDv0;
    fMat_r0c4 += dcontributetmpDv4;
    fMat_r4c4 += -dcontributetmpDv4;
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
    dIspec_edgeDv1 = dIspecDv1*model_.WEDGE/((Weff-model_.WEDGE));
    dIspec_edgeDv3 = dIspecDv3*model_.WEDGE/((Weff-model_.WEDGE));
    dIspec_edgeDv4 = dIspecDv4*model_.WEDGE/((Weff-model_.WEDGE));
    dIspec_edgeDv5 = dIspecDv5*model_.WEDGE/((Weff-model_.WEDGE));
    Ispec_edge = Ispec*model_.WEDGE/((Weff-model_.WEDGE));

    Q0_edge = Q0*model_.WEDGE/(Weff-model_.WEDGE);
    dgamma_edge = (model_.DGAMMAEDGE*(1.0+model_.WLDGAMMAEDGE/WLeff)/sqrtUT);
    dphi_edge = model_.DPHIEDGE*(1.0+model_.LDPHIEDGE/Leff)*(1.0+model_.WDPHIEDGE/Weff)*(1.0+model_.WLDPHIEDGE/WLeff)/UT;
    ddvp_edgeDv1 = (((-dgamma_edge)*dpsi_pDv1+(-0)*psi_p)-(-dgamma_edge)*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*dsqrt_psi_pDv1)/((sqrt_psi_p+0.5*gamma_b_eff));
    ddvp_edgeDv3 = (((-dgamma_edge)*dpsi_pDv3+(-0)*psi_p)-(-dgamma_edge)*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*(dsqrt_psi_pDv3+0.5*dgamma_b_effDv3))/((sqrt_psi_p+0.5*gamma_b_eff));
    ddvp_edgeDv4 = (((-dgamma_edge)*dpsi_pDv4+(-0)*psi_p)-(-dgamma_edge)*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*(dsqrt_psi_pDv4+0.5*dgamma_b_effDv4))/((sqrt_psi_p+0.5*gamma_b_eff));
    ddvp_edgeDv5 = (((-dgamma_edge)*dpsi_pDv5+(-0)*psi_p)-(-dgamma_edge)*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*(dsqrt_psi_pDv5+0.5*dgamma_b_effDv5))/((sqrt_psi_p+0.5*gamma_b_eff));
    dvp_edge = ((-dgamma_edge)*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))-dphi_edge);

    dvvDv1 = ((dvpDv1+ddvp_edgeDv1)+ddeltapsisDv1)/(NUV);
    dvvDv3 = (((dvpDv3+ddvp_edgeDv3)+ddeltapsisDv3)-dvsDv3)/(NUV);
    dvvDv4 = (((dvpDv4+ddvp_edgeDv4)+ddeltapsisDv4)-dvsDv4)/(NUV);
    dvvDv5 = (((dvpDv5+ddvp_edgeDv5)+ddeltapsisDv5)-dvsDv5)/(NUV);
    vv = (((vp+dvp_edge)+deltapsis)-vs)/(NUV);

    if(vv>(-0.6)){
    dz1Dv1 = 0.25*(dvvDv1+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv1+dvvDv1*(vv-0.394036))));
    dz1Dv3 = 0.25*(dvvDv3+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv3+dvvDv3*(vv-0.394036))));
    dz1Dv4 = 0.25*(dvvDv4+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv4+dvvDv4*(vv-0.394036))));
    dz1Dv5 = 0.25*(dvvDv5+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv5+dvvDv5*(vv-0.394036))));
    z1 = 0.25*((vv-1.4)+sqrt((vv*(vv-0.394036)+9.662671)));

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+1/(z1)*(dz1Dv1)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+1/(z1)*(dz1Dv3)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+1/(z1)*(dz1Dv4)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+1/(z1)*(dz1Dv5)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+log(z1)))/((2.0*z1+1.0));

    dqs_edgeDv1 = (z1*(z2*0.070*dz2Dv1+dz2Dv1*(1.0+0.070*z2))+dz1Dv1*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqs_edgeDv3 = (z1*(z2*0.070*dz2Dv3+dz2Dv3*(1.0+0.070*z2))+dz1Dv3*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqs_edgeDv4 = (z1*(z2*0.070*dz2Dv4+dz2Dv4*(1.0+0.070*z2))+dz1Dv4*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqs_edgeDv5 = (z1*(z2*0.070*dz2Dv5+dz2Dv5*(1.0+0.070*z2))+dz1Dv5*(1.0+z2*(1.0+0.070*z2)))*NUV;
    qs_edge = z1*(1.0+z2*(1.0+0.070*z2))*NUV;

    } else {
    dln_z1_Dv1 = 0.5*(dvvDv1-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv1+dvvDv1*(vv-0.402982))));
    dln_z1_Dv3 = 0.5*(dvvDv3-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv3+dvvDv3*(vv-0.402982))));
    dln_z1_Dv4 = 0.5*(dvvDv4-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv4+dvvDv4*(vv-0.402982))));
    dln_z1_Dv5 = 0.5*(dvvDv5-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv5+dvvDv5*(vv-0.402982))));
    ln_z1_ = 0.5*((vv-0.201491)-sqrt((vv*(vv-0.402982)+2.446562)));

    dz1Dv1 = exp(ln_z1_)*(dln_z1_Dv1);
    dz1Dv3 = exp(ln_z1_)*(dln_z1_Dv3);
    dz1Dv4 = exp(ln_z1_)*(dln_z1_Dv4);
    dz1Dv5 = exp(ln_z1_)*(dln_z1_Dv5);
    z1 = exp(ln_z1_);

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+dln_z1_Dv1))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+dln_z1_Dv3))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+dln_z1_Dv4))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+dln_z1_Dv5))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0));

    dqs_edgeDv1 = (z1*(z2*0.483*dz2Dv1+dz2Dv1*(1.0+0.483*z2))+dz1Dv1*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqs_edgeDv3 = (z1*(z2*0.483*dz2Dv3+dz2Dv3*(1.0+0.483*z2))+dz1Dv3*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqs_edgeDv4 = (z1*(z2*0.483*dz2Dv4+dz2Dv4*(1.0+0.483*z2))+dz1Dv4*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqs_edgeDv5 = (z1*(z2*0.483*dz2Dv5+dz2Dv5*(1.0+0.483*z2))+dz1Dv5*(1.0+z2*(1.0+0.483*z2)))*NUV;
    qs_edge = z1*(1.0+z2*(1.0+0.483*z2))*NUV;

    }
    dvvDv1 = (((dvpDv1+ddvp_edgeDv1)+ddeltapsisDv1)-dvdpDv1)/(NUV);
    dvvDv3 = (((dvpDv3+ddvp_edgeDv3)+ddeltapsisDv3)-dvdpDv3)/(NUV);
    dvvDv4 = (((dvpDv4+ddvp_edgeDv4)+ddeltapsisDv4)-dvdpDv4)/(NUV);
    dvvDv5 = (((dvpDv5+ddvp_edgeDv5)+ddeltapsisDv5)-dvdpDv5)/(NUV);
    vv = (((vp+dvp_edge)+deltapsis)-vdp)/(NUV);

    if(vv>(-0.6)){
    dz1Dv1 = 0.25*(dvvDv1+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv1+dvvDv1*(vv-0.394036))));
    dz1Dv3 = 0.25*(dvvDv3+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv3+dvvDv3*(vv-0.394036))));
    dz1Dv4 = 0.25*(dvvDv4+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv4+dvvDv4*(vv-0.394036))));
    dz1Dv5 = 0.25*(dvvDv5+1/(2*sqrt((vv*(vv-0.394036)+9.662671)))*((vv*dvvDv5+dvvDv5*(vv-0.394036))));
    z1 = 0.25*((vv-1.4)+sqrt((vv*(vv-0.394036)+9.662671)));

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+1/(z1)*(dz1Dv1)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+1/(z1)*(dz1Dv3)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+1/(z1)*(dz1Dv4)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+1/(z1)*(dz1Dv5)))-(vv-(2.0*z1+log(z1)))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+log(z1)))/((2.0*z1+1.0));

    dqdp_edgeDv1 = (z1*(z2*0.070*dz2Dv1+dz2Dv1*(1.0+0.070*z2))+dz1Dv1*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqdp_edgeDv3 = (z1*(z2*0.070*dz2Dv3+dz2Dv3*(1.0+0.070*z2))+dz1Dv3*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqdp_edgeDv4 = (z1*(z2*0.070*dz2Dv4+dz2Dv4*(1.0+0.070*z2))+dz1Dv4*(1.0+z2*(1.0+0.070*z2)))*NUV;
    dqdp_edgeDv5 = (z1*(z2*0.070*dz2Dv5+dz2Dv5*(1.0+0.070*z2))+dz1Dv5*(1.0+z2*(1.0+0.070*z2)))*NUV;
    qdp_edge = z1*(1.0+z2*(1.0+0.070*z2))*NUV;

    } else {
    dln_z1_Dv1 = 0.5*(dvvDv1-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv1+dvvDv1*(vv-0.402982))));
    dln_z1_Dv3 = 0.5*(dvvDv3-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv3+dvvDv3*(vv-0.402982))));
    dln_z1_Dv4 = 0.5*(dvvDv4-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv4+dvvDv4*(vv-0.402982))));
    dln_z1_Dv5 = 0.5*(dvvDv5-1/(2*sqrt((vv*(vv-0.402982)+2.446562)))*((vv*dvvDv5+dvvDv5*(vv-0.402982))));
    ln_z1_ = 0.5*((vv-0.201491)-sqrt((vv*(vv-0.402982)+2.446562)));

    dz1Dv1 = exp(ln_z1_)*(dln_z1_Dv1);
    dz1Dv3 = exp(ln_z1_)*(dln_z1_Dv3);
    dz1Dv4 = exp(ln_z1_)*(dln_z1_Dv4);
    dz1Dv5 = exp(ln_z1_)*(dln_z1_Dv5);
    z1 = exp(ln_z1_);

    dz2Dv1 = ((dvvDv1-(2.0*dz1Dv1+dln_z1_Dv1))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv1)/((2.0*z1+1.0));
    dz2Dv3 = ((dvvDv3-(2.0*dz1Dv3+dln_z1_Dv3))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv3)/((2.0*z1+1.0));
    dz2Dv4 = ((dvvDv4-(2.0*dz1Dv4+dln_z1_Dv4))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv4)/((2.0*z1+1.0));
    dz2Dv5 = ((dvvDv5-(2.0*dz1Dv5+dln_z1_Dv5))-(vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0))*2.0*dz1Dv5)/((2.0*z1+1.0));
    z2 = (vv-(2.0*z1+ln_z1_))/((2.0*z1+1.0));

    dqdp_edgeDv1 = (z1*(z2*0.483*dz2Dv1+dz2Dv1*(1.0+0.483*z2))+dz1Dv1*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqdp_edgeDv3 = (z1*(z2*0.483*dz2Dv3+dz2Dv3*(1.0+0.483*z2))+dz1Dv3*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqdp_edgeDv4 = (z1*(z2*0.483*dz2Dv4+dz2Dv4*(1.0+0.483*z2))+dz1Dv4*(1.0+z2*(1.0+0.483*z2)))*NUV;
    dqdp_edgeDv5 = (z1*(z2*0.483*dz2Dv5+dz2Dv5*(1.0+0.483*z2))+dz1Dv5*(1.0+z2*(1.0+0.483*z2)))*NUV;
    qdp_edge = z1*(1.0+z2*(1.0+0.483*z2))*NUV;

    }
    dids_edgeDv1 = ((qs_edge*dqs_edgeDv1+dqs_edgeDv1*(qs_edge+1.0))-(qdp_edge*dqdp_edgeDv1+dqdp_edgeDv1*(qdp_edge+1.0)));
    dids_edgeDv3 = ((qs_edge*dqs_edgeDv3+dqs_edgeDv3*(qs_edge+1.0))-(qdp_edge*dqdp_edgeDv3+dqdp_edgeDv3*(qdp_edge+1.0)));
    dids_edgeDv4 = ((qs_edge*dqs_edgeDv4+dqs_edgeDv4*(qs_edge+1.0))-(qdp_edge*dqdp_edgeDv4+dqdp_edgeDv4*(qdp_edge+1.0)));
    dids_edgeDv5 = ((qs_edge*dqs_edgeDv5+dqs_edgeDv5*(qs_edge+1.0))-(qdp_edge*dqdp_edgeDv5+dqdp_edgeDv5*(qdp_edge+1.0)));
    ids_edge = (qs_edge*(qs_edge+1.0)-qdp_edge*(qdp_edge+1.0));

    dIDS_edgeDv1 = (Ispec_edge*ids_edge*ddits_factorDv1+(Ispec_edge*dids_edgeDv1+dIspec_edgeDv1*ids_edge)*dits_factor);
    dIDS_edgeDv3 = (Ispec_edge*ids_edge*ddits_factorDv3+(Ispec_edge*dids_edgeDv3+dIspec_edgeDv3*ids_edge)*dits_factor);
    dIDS_edgeDv4 = (Ispec_edge*ids_edge*ddits_factorDv4+(Ispec_edge*dids_edgeDv4+dIspec_edgeDv4*ids_edge)*dits_factor);
    dIDS_edgeDv5 = (Ispec_edge*ids_edge*ddits_factorDv5+(Ispec_edge*dids_edgeDv5+dIspec_edgeDv5*ids_edge)*dits_factor);
    IDS_edge = Ispec_edge*ids_edge*dits_factor;

    dpsi_p_edgeDv1 = (dpsi_pDv1-(dgamma_edge*dpsi_pDv1-dgamma_edge*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*dsqrt_psi_pDv1)/((sqrt_psi_p+0.5*gamma_b_eff)));
    dpsi_p_edgeDv3 = (dpsi_pDv3-(dgamma_edge*dpsi_pDv3-dgamma_edge*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*(dsqrt_psi_pDv3+0.5*dgamma_b_effDv3))/((sqrt_psi_p+0.5*gamma_b_eff)));
    dpsi_p_edgeDv4 = (dpsi_pDv4-(dgamma_edge*dpsi_pDv4-dgamma_edge*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*(dsqrt_psi_pDv4+0.5*dgamma_b_effDv4))/((sqrt_psi_p+0.5*gamma_b_eff)));
    dpsi_p_edgeDv5 = (dpsi_pDv5-(dgamma_edge*dpsi_pDv5-dgamma_edge*psi_p/((sqrt_psi_p+0.5*gamma_b_eff))*(dsqrt_psi_pDv5+0.5*dgamma_b_effDv5))/((sqrt_psi_p+0.5*gamma_b_eff)));
    psi_p_edge = (psi_p-dgamma_edge*psi_p/((sqrt_psi_p+0.5*gamma_b_eff)));

    dsqrt_psi_p_edgeDv1 = 1/(2*sqrt(0.5*((psi_p_edge+1.0E-4)+sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_p_edgeDv1+1/(2*sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))*(((psi_p_edge-1.0E-4)*dpsi_p_edgeDv1+dpsi_p_edgeDv1*(psi_p_edge-1.0E-4)))));
    dsqrt_psi_p_edgeDv3 = 1/(2*sqrt(0.5*((psi_p_edge+1.0E-4)+sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_p_edgeDv3+1/(2*sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))*(((psi_p_edge-1.0E-4)*dpsi_p_edgeDv3+dpsi_p_edgeDv3*(psi_p_edge-1.0E-4)))));
    dsqrt_psi_p_edgeDv4 = 1/(2*sqrt(0.5*((psi_p_edge+1.0E-4)+sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_p_edgeDv4+1/(2*sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))*(((psi_p_edge-1.0E-4)*dpsi_p_edgeDv4+dpsi_p_edgeDv4*(psi_p_edge-1.0E-4)))));
    dsqrt_psi_p_edgeDv5 = 1/(2*sqrt(0.5*((psi_p_edge+1.0E-4)+sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))))*(0.5*(dpsi_p_edgeDv5+1/(2*sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2)))*(((psi_p_edge-1.0E-4)*dpsi_p_edgeDv5+dpsi_p_edgeDv5*(psi_p_edge-1.0E-4)))));
    sqrt_psi_p_edge = sqrt(0.5*((psi_p_edge+1.0E-4)+sqrt(((psi_p_edge-1.0E-4)*(psi_p_edge-1.0E-4)+1.0E-2))));

    dgamma_b_chsh_edgeDv3 = dgamma_b_chshDv3;
    dgamma_b_chsh_edgeDv4 = dgamma_b_chshDv4;
    dgamma_b_chsh_edgeDv5 = dgamma_b_chshDv5;
    gamma_b_chsh_edge = (gamma_b_chsh+dgamma_edge);

    dpsi_sa_tmpDv1 = ((dpsi_p_edgeDv1-dqs_edgeDv1)-dqdp_edgeDv1);
    dpsi_sa_tmpDv3 = ((dpsi_p_edgeDv3-dqs_edgeDv3)-dqdp_edgeDv3);
    dpsi_sa_tmpDv4 = ((dpsi_p_edgeDv4-dqs_edgeDv4)-dqdp_edgeDv4);
    dpsi_sa_tmpDv5 = ((dpsi_p_edgeDv5-dqs_edgeDv5)-dqdp_edgeDv5);
    psi_sa_tmp = ((psi_p_edge-qs_edge)-qdp_edge);

    dsqrt_psi_saDv1 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv1+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv1+dpsi_sa_tmpDv1*(psi_sa_tmp-1.0e-4)))));
    dsqrt_psi_saDv3 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv3+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv3+dpsi_sa_tmpDv3*(psi_sa_tmp-1.0e-4)))));
    dsqrt_psi_saDv4 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv4+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv4+dpsi_sa_tmpDv4*(psi_sa_tmp-1.0e-4)))));
    dsqrt_psi_saDv5 = 1/(2*sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))))*(0.5*(dpsi_sa_tmpDv5+1/(2*sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2)))*(((psi_sa_tmp-1.0e-4)*dpsi_sa_tmpDv5+dpsi_sa_tmpDv5*(psi_sa_tmp-1.0e-4)))));
    sqrt_psi_sa = sqrt(0.5*((psi_sa_tmp+1.0e-4)+sqrt(((psi_sa_tmp-1.0e-4)*(psi_sa_tmp-1.0e-4)+1.0E-2))));

    if(model_.TG<0){
    dz0Dv1 = (-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv1+dsqrt_psi_saDv1))/((sqrt_psi_p_edge+sqrt_psi_sa));
    dz0Dv3 = (dgamma_b_chsh_edgeDv3-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv3+dsqrt_psi_saDv3))/((sqrt_psi_p_edge+sqrt_psi_sa));
    dz0Dv4 = (dgamma_b_chsh_edgeDv4-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv4+dsqrt_psi_saDv4))/((sqrt_psi_p_edge+sqrt_psi_sa));
    dz0Dv5 = (dgamma_b_chsh_edgeDv5-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv5+dsqrt_psi_saDv5))/((sqrt_psi_p_edge+sqrt_psi_sa));
    z0 = ((1.0+dpd)+gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa)));

    dzkDv1 = dpd*dsqrt_psi_saDv1/(gamma_b_chsh_edge);
    dzkDv3 = (dpd*dsqrt_psi_saDv3-dpd*sqrt_psi_sa/(gamma_b_chsh_edge)*dgamma_b_chsh_edgeDv3)/(gamma_b_chsh_edge);
    dzkDv4 = (dpd*dsqrt_psi_saDv4-dpd*sqrt_psi_sa/(gamma_b_chsh_edge)*dgamma_b_chsh_edgeDv4)/(gamma_b_chsh_edge);
    dzkDv5 = (dpd*dsqrt_psi_saDv5-dpd*sqrt_psi_sa/(gamma_b_chsh_edge)*dgamma_b_chsh_edgeDv5)/(gamma_b_chsh_edge);
    zk = (0.5+dpd*sqrt_psi_sa/(gamma_b_chsh_edge));

    dnq_edgeDv1 = (dz0Dv1-z0/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))))*(dzkDv1+1/(2*sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2))))*(((zk*dzkDv1+dzkDv1*zk)+(z0*(dqs_edgeDv1+dqdp_edgeDv1)+dz0Dv1*(qs_edge+qdp_edge))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))));
    dnq_edgeDv3 = (dz0Dv3-z0/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))))*(dzkDv3+1/(2*sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2))))*(((zk*dzkDv3+dzkDv3*zk)+(z0*(dqs_edgeDv3+dqdp_edgeDv3)+dz0Dv3*(qs_edge+qdp_edge))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))));
    dnq_edgeDv4 = (dz0Dv4-z0/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))))*(dzkDv4+1/(2*sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2))))*(((zk*dzkDv4+dzkDv4*zk)+(z0*(dqs_edgeDv4+dqdp_edgeDv4)+dz0Dv4*(qs_edge+qdp_edge))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))));
    dnq_edgeDv5 = (dz0Dv5-z0/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))))*(dzkDv5+1/(2*sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2))))*(((zk*dzkDv5+dzkDv5*zk)+(z0*(dqs_edgeDv5+dqdp_edgeDv5)+dz0Dv5*(qs_edge+qdp_edge))/(gamma_g2)))))/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))));
    nq_edge = z0/((zk+sqrt((zk*zk+z0*(qs_edge+qdp_edge)/(gamma_g2)))));

    } else {
    dnq_edgeDv1 = (-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv1+dsqrt_psi_saDv1))/((sqrt_psi_p_edge+sqrt_psi_sa));
    dnq_edgeDv3 = (dgamma_b_chsh_edgeDv3-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv3+dsqrt_psi_saDv3))/((sqrt_psi_p_edge+sqrt_psi_sa));
    dnq_edgeDv4 = (dgamma_b_chsh_edgeDv4-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv4+dsqrt_psi_saDv4))/((sqrt_psi_p_edge+sqrt_psi_sa));
    dnq_edgeDv5 = (dgamma_b_chsh_edgeDv5-gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa))*(dsqrt_psi_p_edgeDv5+dsqrt_psi_saDv5))/((sqrt_psi_p_edge+sqrt_psi_sa));
    nq_edge = (1.0+gamma_b_chsh_edge/((sqrt_psi_p_edge+sqrt_psi_sa)));

    }
    dqsqdp_edgeDv1 = (dqs_edgeDv1+dqdp_edgeDv1);
    dqsqdp_edgeDv3 = (dqs_edgeDv3+dqdp_edgeDv3);
    dqsqdp_edgeDv4 = (dqs_edgeDv4+dqdp_edgeDv4);
    dqsqdp_edgeDv5 = (dqs_edgeDv5+dqdp_edgeDv5);
    qsqdp_edge = (qs_edge+qdp_edge);

    dqs_qdp_edgeDv1 = (dqs_edgeDv1-dqdp_edgeDv1);
    dqs_qdp_edgeDv3 = (dqs_edgeDv3-dqdp_edgeDv3);
    dqs_qdp_edgeDv4 = (dqs_edgeDv4-dqdp_edgeDv4);
    dqs_qdp_edgeDv5 = (dqs_edgeDv5-dqdp_edgeDv5);
    qs_qdp_edge = (qs_edge-qdp_edge);

    dpowqs_qdp2_edgeDv1 = (qs_qdp_edge*dqs_qdp_edgeDv1+dqs_qdp_edgeDv1*qs_qdp_edge);
    dpowqs_qdp2_edgeDv3 = (qs_qdp_edge*dqs_qdp_edgeDv3+dqs_qdp_edgeDv3*qs_qdp_edge);
    dpowqs_qdp2_edgeDv4 = (qs_qdp_edge*dqs_qdp_edgeDv4+dqs_qdp_edgeDv4*qs_qdp_edge);
    dpowqs_qdp2_edgeDv5 = (qs_qdp_edge*dqs_qdp_edgeDv5+dqs_qdp_edgeDv5*qs_qdp_edge);
    powqs_qdp2_edge = qs_qdp_edge*qs_qdp_edge;

    dqsqdpp1_edgeDv1 = dqsqdp_edgeDv1;
    dqsqdpp1_edgeDv3 = dqsqdp_edgeDv3;
    dqsqdpp1_edgeDv4 = dqsqdp_edgeDv4;
    dqsqdpp1_edgeDv5 = dqsqdp_edgeDv5;
    qsqdpp1_edge = (qsqdp_edge+1.0);

    dpowqsqdpp1_2_edgeDv1 = (-1.0/(qsqdpp1_edge*qsqdpp1_edge)*(qsqdpp1_edge*dqsqdpp1_edgeDv1+dqsqdpp1_edgeDv1*qsqdpp1_edge))/(qsqdpp1_edge*qsqdpp1_edge);
    dpowqsqdpp1_2_edgeDv3 = (-1.0/(qsqdpp1_edge*qsqdpp1_edge)*(qsqdpp1_edge*dqsqdpp1_edgeDv3+dqsqdpp1_edgeDv3*qsqdpp1_edge))/(qsqdpp1_edge*qsqdpp1_edge);
    dpowqsqdpp1_2_edgeDv4 = (-1.0/(qsqdpp1_edge*qsqdpp1_edge)*(qsqdpp1_edge*dqsqdpp1_edgeDv4+dqsqdpp1_edgeDv4*qsqdpp1_edge))/(qsqdpp1_edge*qsqdpp1_edge);
    dpowqsqdpp1_2_edgeDv5 = (-1.0/(qsqdpp1_edge*qsqdpp1_edge)*(qsqdpp1_edge*dqsqdpp1_edgeDv5+dqsqdpp1_edgeDv5*qsqdpp1_edge))/(qsqdpp1_edge*qsqdpp1_edge);
    powqsqdpp1_2_edge = 1.0/(qsqdpp1_edge*qsqdpp1_edge);

    if(psi_p_edge>2.0){
    dqS_edgeDv1 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqs_edgeDv1+dqdp_edgeDv1)+dqs_edgeDv1)+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv1+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*dpowqs_qdp2_edgeDv1+0.5*(0.8*dqs_edgeDv1+1.2*dqdp_edgeDv1)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv1*0.33333333333333333333333333333333*(((qs_edge+qdp_edge)+qs_edge)+0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    dqS_edgeDv3 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqs_edgeDv3+dqdp_edgeDv3)+dqs_edgeDv3)+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv3+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*dpowqs_qdp2_edgeDv3+0.5*(0.8*dqs_edgeDv3+1.2*dqdp_edgeDv3)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv3*0.33333333333333333333333333333333*(((qs_edge+qdp_edge)+qs_edge)+0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    dqS_edgeDv4 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqs_edgeDv4+dqdp_edgeDv4)+dqs_edgeDv4)+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv4+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*dpowqs_qdp2_edgeDv4+0.5*(0.8*dqs_edgeDv4+1.2*dqdp_edgeDv4)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv4*0.33333333333333333333333333333333*(((qs_edge+qdp_edge)+qs_edge)+0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    dqS_edgeDv5 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqs_edgeDv5+dqdp_edgeDv5)+dqs_edgeDv5)+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv5+(0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*dpowqs_qdp2_edgeDv5+0.5*(0.8*dqs_edgeDv5+1.2*dqdp_edgeDv5)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv5*0.33333333333333333333333333333333*(((qs_edge+qdp_edge)+qs_edge)+0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    qS_edge = inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((qs_edge+qdp_edge)+qs_edge)+0.5*((1.0+0.8*qs_edge)+1.2*qdp_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge);

    } else {
    qS_edge = 0.0;
    dqS_edgeDv1 = dqS_edgeDv3 = dqS_edgeDv4 = dqS_edgeDv5 = 0.0;
    }
    if(psi_p_edge>2.0){
    dqD_edgeDv1 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqdp_edgeDv1+dqs_edgeDv1)+dqdp_edgeDv1)+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv1+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*dpowqs_qdp2_edgeDv1+0.5*(0.8*dqdp_edgeDv1+1.2*dqs_edgeDv1)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv1*0.33333333333333333333333333333333*(((qdp_edge+qs_edge)+qdp_edge)+0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    dqD_edgeDv3 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqdp_edgeDv3+dqs_edgeDv3)+dqdp_edgeDv3)+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv3+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*dpowqs_qdp2_edgeDv3+0.5*(0.8*dqdp_edgeDv3+1.2*dqs_edgeDv3)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv3*0.33333333333333333333333333333333*(((qdp_edge+qs_edge)+qdp_edge)+0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    dqD_edgeDv4 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqdp_edgeDv4+dqs_edgeDv4)+dqdp_edgeDv4)+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv4+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*dpowqs_qdp2_edgeDv4+0.5*(0.8*dqdp_edgeDv4+1.2*dqs_edgeDv4)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv4*0.33333333333333333333333333333333*(((qdp_edge+qs_edge)+qdp_edge)+0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    dqD_edgeDv5 = (inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((dqdp_edgeDv5+dqs_edgeDv5)+dqdp_edgeDv5)+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*dpowqsqdpp1_2_edgeDv5+(0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*dpowqs_qdp2_edgeDv5+0.5*(0.8*dqdp_edgeDv5+1.2*dqs_edgeDv5)*powqs_qdp2_edge)*powqsqdpp1_2_edge))+inv_dqmip1*dnq_edgeDv5*0.33333333333333333333333333333333*(((qdp_edge+qs_edge)+qdp_edge)+0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge));
    qD_edge = inv_dqmip1*nq_edge*0.33333333333333333333333333333333*(((qdp_edge+qs_edge)+qdp_edge)+0.5*((1.0+0.8*qdp_edge)+1.2*qs_edge)*powqs_qdp2_edge*powqsqdpp1_2_edge);

    } else {
    qD_edge = 0.0;
    dqD_edgeDv1 = dqD_edgeDv3 = dqD_edgeDv4 = dqD_edgeDv5 = 0.0;
    }
    if(psi_p_edge>2.0){
    dv2_qgDv1 = dv2_qgDv3 = dv2_qgDv4 = dv2_qgDv5 = 0.0;
    dv1_qgDv1 = dv1_qgDv3 = dv1_qgDv4 = dv1_qgDv5 = 0.0;
    dk2Dv1 = dk2Dv3 = dk2Dv4 = dk2Dv5 = 0.0;
    dk12_3Dv1 = dk12_3Dv3 = dk12_3Dv4 = dk12_3Dv5 = 0.0;
    dk12_2Dv1 = dk12_2Dv3 = dk12_2Dv4 = dk12_2Dv5 = 0.0;
    dk12Dv1 = dk12Dv3 = dk12Dv4 = dk12Dv5 = 0.0;
    dk1Dv1 = dk1Dv3 = dk1Dv4 = dk1Dv5 = 0.0;
    if(model_.TG<0){
    dv1_qgDv1 = (dv_oDv1+2.0*dqs_edgeDv1*inv_dqmip1);
    dv1_qgDv3 = (dv_oDv3+2.0*dqs_edgeDv3*inv_dqmip1);
    dv1_qgDv4 = (dv_oDv4+2.0*dqs_edgeDv4*inv_dqmip1);
    dv1_qgDv5 = (dv_oDv5+2.0*dqs_edgeDv5*inv_dqmip1);
    v1_qg = (v_o+2.0*qs_edge*inv_dqmip1);

    dv2_qgDv1 = (dv_oDv1+2.0*dqdp_edgeDv1*inv_dqmip1);
    dv2_qgDv3 = (dv_oDv3+2.0*dqdp_edgeDv3*inv_dqmip1);
    dv2_qgDv4 = (dv_oDv4+2.0*dqdp_edgeDv4*inv_dqmip1);
    dv2_qgDv5 = (dv_oDv5+2.0*dqdp_edgeDv5*inv_dqmip1);
    v2_qg = (v_o+2.0*qdp_edge*inv_dqmip1);

    dk1Dv1 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv1/(gamma_g2));
    dk1Dv3 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv3/(gamma_g2));
    dk1Dv4 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv4/(gamma_g2));
    dk1Dv5 = 1/(2*sqrt((0.25+v1_qg/(gamma_g2))))*(dv1_qgDv5/(gamma_g2));
    k1 = sqrt((0.25+v1_qg/(gamma_g2)));

    dk2Dv1 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv1/(gamma_g2));
    dk2Dv3 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv3/(gamma_g2));
    dk2Dv4 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv4/(gamma_g2));
    dk2Dv5 = 1/(2*sqrt((0.25+v2_qg/(gamma_g2))))*(dv2_qgDv5/(gamma_g2));
    k2 = sqrt((0.25+v2_qg/(gamma_g2)));

    dk12Dv1 = (dk1Dv1+dk2Dv1);
    dk12Dv3 = (dk1Dv3+dk2Dv3);
    dk12Dv4 = (dk1Dv4+dk2Dv4);
    dk12Dv5 = (dk1Dv5+dk2Dv5);
    k12 = (k1+k2);

    dk12_2Dv1 = (k12*dk12Dv1+dk12Dv1*k12);
    dk12_2Dv3 = (k12*dk12Dv3+dk12Dv3*k12);
    dk12_2Dv4 = (k12*dk12Dv4+dk12Dv4*k12);
    dk12_2Dv5 = (k12*dk12Dv5+dk12Dv5*k12);
    k12_2 = k12*k12;

    dk12_3Dv1 = (k12_2*dk12Dv1+dk12_2Dv1*k12);
    dk12_3Dv3 = (k12_2*dk12Dv3+dk12_2Dv3*k12);
    dk12_3Dv4 = (k12_2*dk12Dv4+dk12_2Dv4*k12);
    dk12_3Dv5 = (k12_2*dk12Dv5+dk12_2Dv5*k12);
    k12_3 = k12_2*k12;

    dqG_edgeDv1 = (((dv1_qgDv1-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv1)/((1.0+2.0*k1))+(dv2_qgDv1-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv1)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(k12_3)*(0.8*(dk12_2Dv1+(k1*dk2Dv1+dk1Dv1*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1_edge)*dqsqdpp1_edgeDv1)/(qsqdpp1_edge)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2_edgeDv1-powqs_qdp2_edge/(k12_3)*dk12_3Dv1)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1_edge)+2.0/(gamma_g2))));
    dqG_edgeDv3 = (((dv1_qgDv3-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv3)/((1.0+2.0*k1))+(dv2_qgDv3-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv3)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(k12_3)*(0.8*(dk12_2Dv3+(k1*dk2Dv3+dk1Dv3*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1_edge)*dqsqdpp1_edgeDv3)/(qsqdpp1_edge)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2_edgeDv3-powqs_qdp2_edge/(k12_3)*dk12_3Dv3)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1_edge)+2.0/(gamma_g2))));
    dqG_edgeDv4 = (((dv1_qgDv4-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv4)/((1.0+2.0*k1))+(dv2_qgDv4-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv4)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(k12_3)*(0.8*(dk12_2Dv4+(k1*dk2Dv4+dk1Dv4*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1_edge)*dqsqdpp1_edgeDv4)/(qsqdpp1_edge)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2_edgeDv4-powqs_qdp2_edge/(k12_3)*dk12_3Dv4)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1_edge)+2.0/(gamma_g2))));
    dqG_edgeDv5 = (((dv1_qgDv5-v1_qg/((1.0+2.0*k1))*2.0*dk1Dv5)/((1.0+2.0*k1))+(dv2_qgDv5-v2_qg/((1.0+2.0*k2))*2.0*dk2Dv5)/((1.0+2.0*k2)))+(inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(k12_3)*(0.8*(dk12_2Dv5+(k1*dk2Dv5+dk1Dv5*k2))-0.8*(k12_2+k1*k2)/(qsqdpp1_edge)*dqsqdpp1_edgeDv5)/(qsqdpp1_edge)+inv_dqmip1*0.33333333333333333333333333333333*(dpowqs_qdp2_edgeDv5-powqs_qdp2_edge/(k12_3)*dk12_3Dv5)/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1_edge)+2.0/(gamma_g2))));
    qG_edge = ((v1_qg/((1.0+2.0*k1))+v2_qg/((1.0+2.0*k2)))+inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(k12_3)*(0.8*(k12_2+k1*k2)/(qsqdpp1_edge)+2.0/(gamma_g2)));

    } else {
    dqG_edgeDv1 = (((dv_oDv1+dqs_edgeDv1)+dqdp_edgeDv1)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2_edgeDv1-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(qsqdpp1_edge)*dqsqdpp1_edgeDv1)/(qsqdpp1_edge));
    dqG_edgeDv3 = (((dv_oDv3+dqs_edgeDv3)+dqdp_edgeDv3)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2_edgeDv3-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(qsqdpp1_edge)*dqsqdpp1_edgeDv3)/(qsqdpp1_edge));
    dqG_edgeDv4 = (((dv_oDv4+dqs_edgeDv4)+dqdp_edgeDv4)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2_edgeDv4-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(qsqdpp1_edge)*dqsqdpp1_edgeDv4)/(qsqdpp1_edge));
    dqG_edgeDv5 = (((dv_oDv5+dqs_edgeDv5)+dqdp_edgeDv5)+(inv_dqmip1*0.33333333333333333333333333333333*dpowqs_qdp2_edgeDv5-inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(qsqdpp1_edge)*dqsqdpp1_edgeDv5)/(qsqdpp1_edge));
    qG_edge = (((v_o+qs_edge)+qdp_edge)+inv_dqmip1*0.33333333333333333333333333333333*powqs_qdp2_edge/(qsqdpp1_edge));

    }
    } else {
    if(psi_p_edge>0.0){
    dqG_edgeDv1 = ((model_.TG < 0) ? (dv_oDv1-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv1/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv1);
    dqG_edgeDv3 = ((model_.TG < 0) ? (dv_oDv3-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv3/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv3);
    dqG_edgeDv4 = ((model_.TG < 0) ? (dv_oDv4-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv4/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv4);
    dqG_edgeDv5 = ((model_.TG < 0) ? (dv_oDv5-v_o/((0.5+sqrt((0.25+v_o/(gamma_g2)))))*1/(2*sqrt((0.25+v_o/(gamma_g2))))*(dv_oDv5/(gamma_g2)))/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : dv_oDv5);
    qG_edge = ((model_.TG < 0) ? v_o/((0.5+sqrt((0.25+v_o/(gamma_g2))))) : v_o);

    } else {
    dqG_edgeDv1 = ((model_.TG > 0) ? (dv_oDv1-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv1/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv1);
    dqG_edgeDv3 = ((model_.TG > 0) ? (dv_oDv3-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv3/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv3);
    dqG_edgeDv4 = ((model_.TG > 0) ? (dv_oDv4-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv4/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv4);
    dqG_edgeDv5 = ((model_.TG > 0) ? (dv_oDv5-v_o/((0.5+sqrt((0.25-v_o/(gamma_g2)))))*1/(2*sqrt((0.25-v_o/(gamma_g2))))*((-dv_oDv5/(gamma_g2))))/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : dv_oDv5);
    qG_edge = ((model_.TG > 0) ? v_o/((0.5+sqrt((0.25-v_o/(gamma_g2))))) : v_o);

    }
    }
    dqI_edgeDv1 = (dqS_edgeDv1+dqD_edgeDv1);
    dqI_edgeDv3 = (dqS_edgeDv3+dqD_edgeDv3);
    dqI_edgeDv4 = (dqS_edgeDv4+dqD_edgeDv4);
    dqI_edgeDv5 = (dqS_edgeDv5+dqD_edgeDv5);
    qI_edge = (qS_edge+qD_edge);

    dqB_edgeDv1 = (dqG_edgeDv1-dqI_edgeDv1);
    dqB_edgeDv3 = (dqG_edgeDv3-dqI_edgeDv3);
    dqB_edgeDv4 = (dqG_edgeDv4-dqI_edgeDv4);
    dqB_edgeDv5 = (dqG_edgeDv5-dqI_edgeDv5);
    qB_edge = (qG_edge-qI_edge);

    dQS_edgeDv1 = dqS_edgeDv1*Q0_edge;
    dQS_edgeDv3 = dqS_edgeDv3*Q0_edge;
    dQS_edgeDv4 = dqS_edgeDv4*Q0_edge;
    dQS_edgeDv5 = dqS_edgeDv5*Q0_edge;
    QS_edge = qS_edge*Q0_edge;

    dQD_edgeDv1 = dqD_edgeDv1*Q0_edge;
    dQD_edgeDv3 = dqD_edgeDv3*Q0_edge;
    dQD_edgeDv4 = dqD_edgeDv4*Q0_edge;
    dQD_edgeDv5 = dqD_edgeDv5*Q0_edge;
    QD_edge = qD_edge*Q0_edge;

    dQG_edgeDv1 = (-dqG_edgeDv1)*Q0_edge;
    dQG_edgeDv3 = (-dqG_edgeDv3)*Q0_edge;
    dQG_edgeDv4 = (-dqG_edgeDv4)*Q0_edge;
    dQG_edgeDv5 = (-dqG_edgeDv5)*Q0_edge;
    QG_edge = (-qG_edge)*Q0_edge;

    dQB_edgeDv1 = (((-dQS_edgeDv1)-dQD_edgeDv1)-dQG_edgeDv1);
    dQB_edgeDv3 = (((-dQS_edgeDv3)-dQD_edgeDv3)-dQG_edgeDv3);
    dQB_edgeDv4 = (((-dQS_edgeDv4)-dQD_edgeDv4)-dQG_edgeDv4);
    dQB_edgeDv5 = (((-dQS_edgeDv5)-dQD_edgeDv5)-dQG_edgeDv5);
    QB_edge = (((-QS_edge)-QD_edge)-QG_edge);

    dcontributetmpDv1 = SIGN_M*d_gt_s_flag*dIDS_edgeDv1;
    dcontributetmpDv3 = SIGN_M*d_gt_s_flag*dIDS_edgeDv3;
    dcontributetmpDv4 = SIGN_M*d_gt_s_flag*dIDS_edgeDv4;
    dcontributetmpDv5 = SIGN_M*d_gt_s_flag*dIDS_edgeDv5;
    contributetmp = SIGN_M*d_gt_s_flag*IDS_edge;

    dcontributetmporgDv1 = SIGN_M*d_gt_s_flag*dIDS_edgeDv1;
    dcontributetmporgDv3 = SIGN_M*d_gt_s_flag*dIDS_edgeDv3;
    dcontributetmporgDv4 = SIGN_M*d_gt_s_flag*dIDS_edgeDv4;
    dcontributetmporgDv5 = SIGN_M*d_gt_s_flag*dIDS_edgeDv5;
    contributetmporg = SIGN_M*d_gt_s_flag*IDS_edge;

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r5c1 += -dcontributetmpDv1;
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r5c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r5c4 += -dcontributetmpDv4;
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r5c5 += -dcontributetmpDv5;
    dDdtExp5Dv1 = dQB_edgeDv1;
    dDdtExp5Dv3 = dQB_edgeDv3;
    dDdtExp5Dv4 = dQB_edgeDv4;
    dDdtExp5Dv5 = dQB_edgeDv5;
    DdtExp5 = QB_edge;

    dDdtAns5Dv1 = 0;
    dDdtAns5Dv3 = 0;
    dDdtAns5Dv4 = 0;
    dDdtAns5Dv5 = 0;
    DdtAns5 = DdtExp5;

    dDdtAns5Dv1 = dDdtExp5Dv1 * _der0;
    dDdtAns5Dv3 = dDdtExp5Dv3 * _der0;
    dDdtAns5Dv4 = dDdtExp5Dv4 * _der0;
    dDdtAns5Dv5 = dDdtExp5Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.0*QON;
    dcontributetmpDv3 = SIGN_M*0.0*QON;
    dcontributetmpDv4 = SIGN_M*0.0*QON;
    dcontributetmpDv5 = SIGN_M*0.0*QON;
    contributetmp = SIGN_M*DdtAns5*QON;

    dcontributetmporgDv1 = SIGN_M*dDdtAns5Dv1*QON;
    dcontributetmporgDv3 = SIGN_M*dDdtAns5Dv3*QON;
    dcontributetmporgDv4 = SIGN_M*dDdtAns5Dv4*QON;
    dcontributetmporgDv5 = SIGN_M*dDdtAns5Dv5*QON;
    contributetmporg = SIGN_M*DdtAns5*QON;

    fMat_r3c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r3c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r3c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r3c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r3c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r3c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r3c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r3c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dDdtExp6Dv1 = dQD_edgeDv1;
    dDdtExp6Dv3 = dQD_edgeDv3;
    dDdtExp6Dv4 = dQD_edgeDv4;
    dDdtExp6Dv5 = dQD_edgeDv5;
    DdtExp6 = QD_edge;

    dDdtAns6Dv1 = 0;
    dDdtAns6Dv3 = 0;
    dDdtAns6Dv4 = 0;
    dDdtAns6Dv5 = 0;
    DdtAns6 = DdtExp6;

    dDdtAns6Dv1 = dDdtExp6Dv1 * _der0;
    dDdtAns6Dv3 = dDdtExp6Dv3 * _der0;
    dDdtAns6Dv4 = dDdtExp6Dv4 * _der0;
    dDdtAns6Dv5 = dDdtExp6Dv5 * _der0;
    dDdtExp7Dv1 = dQS_edgeDv1;
    dDdtExp7Dv3 = dQS_edgeDv3;
    dDdtExp7Dv4 = dQS_edgeDv4;
    dDdtExp7Dv5 = dQS_edgeDv5;
    DdtExp7 = QS_edge;

    dDdtAns7Dv1 = 0;
    dDdtAns7Dv3 = 0;
    dDdtAns7Dv4 = 0;
    dDdtAns7Dv5 = 0;
    DdtAns7 = DdtExp7;

    dDdtAns7Dv1 = dDdtExp7Dv1 * _der0;
    dDdtAns7Dv3 = dDdtExp7Dv3 * _der0;
    dDdtAns7Dv4 = dDdtExp7Dv4 * _der0;
    dDdtAns7Dv5 = dDdtExp7Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns6+(1-d_gt_s_flag)*DdtAns7)*QON;

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns6Dv1+(1-d_gt_s_flag)*dDdtAns7Dv1)*QON;
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns6Dv3+(1-d_gt_s_flag)*dDdtAns7Dv3)*QON;
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns6Dv4+(1-d_gt_s_flag)*dDdtAns7Dv4)*QON;
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns6Dv5+(1-d_gt_s_flag)*dDdtAns7Dv5)*QON;
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns6+(1-d_gt_s_flag)*DdtAns7)*QON;

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r4c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r4c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r4c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r4c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dDdtExp8Dv1 = dQS_edgeDv1;
    dDdtExp8Dv3 = dQS_edgeDv3;
    dDdtExp8Dv4 = dQS_edgeDv4;
    dDdtExp8Dv5 = dQS_edgeDv5;
    DdtExp8 = QS_edge;

    dDdtAns8Dv1 = 0;
    dDdtAns8Dv3 = 0;
    dDdtAns8Dv4 = 0;
    dDdtAns8Dv5 = 0;
    DdtAns8 = DdtExp8;

    dDdtAns8Dv1 = dDdtExp8Dv1 * _der0;
    dDdtAns8Dv3 = dDdtExp8Dv3 * _der0;
    dDdtAns8Dv4 = dDdtExp8Dv4 * _der0;
    dDdtAns8Dv5 = dDdtExp8Dv5 * _der0;
    dDdtExp9Dv1 = dQD_edgeDv1;
    dDdtExp9Dv3 = dQD_edgeDv3;
    dDdtExp9Dv4 = dQD_edgeDv4;
    dDdtExp9Dv5 = dQD_edgeDv5;
    DdtExp9 = QD_edge;

    dDdtAns9Dv1 = 0;
    dDdtAns9Dv3 = 0;
    dDdtAns9Dv4 = 0;
    dDdtAns9Dv5 = 0;
    DdtAns9 = DdtExp9;

    dDdtAns9Dv1 = dDdtExp9Dv1 * _der0;
    dDdtAns9Dv3 = dDdtExp9Dv3 * _der0;
    dDdtAns9Dv4 = dDdtExp9Dv4 * _der0;
    dDdtAns9Dv5 = dDdtExp9Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns8+(1-d_gt_s_flag)*DdtAns9)*QON;

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns8Dv1+(1-d_gt_s_flag)*dDdtAns9Dv1)*QON;
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns8Dv3+(1-d_gt_s_flag)*dDdtAns9Dv3)*QON;
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns8Dv4+(1-d_gt_s_flag)*dDdtAns9Dv4)*QON;
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns8Dv5+(1-d_gt_s_flag)*dDdtAns9Dv5)*QON;
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns8+(1-d_gt_s_flag)*DdtAns9)*QON;

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r5c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r5c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r5c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r5c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dvgsov_pDv1 = dvgsov_pDv3 = dvgsov_pDv4 = dvgsov_pDv5 = 0.0;
    dvgdov_pDv1 = dvgdov_pDv3 = dvgdov_pDv4 = dvgdov_pDv5 = 0.0;
    dv3_sovDv1 = dv3_sovDv3 = dv3_sovDv4 = dv3_sovDv5 = 0.0;
    dv3_dovDv1 = dv3_dovDv3 = dv3_dovDv4 = dv3_dovDv5 = 0.0;
    dv2b_sovDv1 = dv2b_sovDv3 = dv2b_sovDv4 = dv2b_sovDv5 = 0.0;
    dv2b_dovDv1 = dv2b_dovDv3 = dv2b_dovDv4 = dv2b_dovDv5 = 0.0;
    dv2_sovDv1 = dv2_sovDv3 = dv2_sovDv4 = dv2_sovDv5 = 0.0;
    dv2_dovDv1 = dv2_dovDv3 = dv2_dovDv4 = dv2_dovDv5 = 0.0;
    dv1_sovDv1 = dv1_sovDv3 = dv1_sovDv4 = dv1_sovDv5 = 0.0;
    dv1_dovDv1 = dv1_dovDv3 = dv1_dovDv4 = dv1_dovDv5 = 0.0;
    dv0_sovDv1 = dv0_sovDv3 = dv0_sovDv4 = dv0_sovDv5 = 0.0;
    dv0_dovDv1 = dv0_dovDv3 = dv0_dovDv4 = dv0_dovDv5 = 0.0;
    dtmpDv1 = dtmpDv3 = dtmpDv4 = dtmpDv5 = 0.0;
    dgamma_dep2_sovDv1 = dgamma_dep2_sovDv3 = dgamma_dep2_sovDv4 = dgamma_dep2_sovDv5 = 0.0;
    dgamma_dep2_dovDv1 = dgamma_dep2_dovDv3 = dgamma_dep2_dovDv4 = dgamma_dep2_dovDv5 = 0.0;
    ddpsigs0Dv1 = ddpsigs0Dv3 = ddpsigs0Dv4 = ddpsigs0Dv5 = 0.0;
    ddpsigsDv1 = ddpsigsDv3 = ddpsigsDv4 = ddpsigsDv5 = 0.0;
    ddpsigd0Dv1 = ddpsigd0Dv3 = ddpsigd0Dv4 = ddpsigd0Dv5 = 0.0;
    ddpsigdDv1 = ddpsigdDv3 = ddpsigdDv4 = ddpsigdDv5 = 0.0;
    da4_sovDv1 = da4_sovDv3 = da4_sovDv4 = da4_sovDv5 = 0.0;
    da4_dovDv1 = da4_dovDv3 = da4_dovDv4 = da4_dovDv5 = 0.0;
    if(model_.LOV>0.0){
    if(model_.TG<0){
    dvgsov_pDv1 = dvgDv1;
    dvgsov_pDv3 = (dvgDv3-model_.VOV*dvsDv3);
    dvgsov_pDv4 = (-model_.VOV*dvsDv4);
    dvgsov_pDv5 = (-model_.VOV*dvsDv5);
    vgsov_p = ((vg-model_.VOV*vs)-vfb_ov);

    if(vgsov_p>0.0){
    gamma_dep_sov = gamma_g_ov;
    gamma_acc_sov = gamma_ov;
    dv0_sovDv1 = dvgsov_pDv1;
    dv0_sovDv3 = dvgsov_pDv3;
    dv0_sovDv4 = dvgsov_pDv4;
    dv0_sovDv5 = dvgsov_pDv5;
    v0_sov = vgsov_p;

    } else {
    gamma_dep_sov = gamma_ov;
    gamma_acc_sov = gamma_g_ov;
    dv0_sovDv1 = (-dvgsov_pDv1);
    dv0_sovDv3 = (-dvgsov_pDv3);
    dv0_sovDv4 = (-dvgsov_pDv4);
    dv0_sovDv5 = (-dvgsov_pDv5);
    v0_sov = (-vgsov_p);

    }
    a0_sov = 1.0+gamma_acc_sov*(0.70710678118654752440084436210485);
    a1_sov = gamma_dep_sov/gamma_acc_sov;
    a2_sov = a0_sov/(a0_sov+a1_sov);
    a3_sov = 1.0+gamma_dep_sov*(0.70710678118654752440084436210485)+a1_sov;
    dv1_sovDv1 = dv0_sovDv1*0.5;
    dv1_sovDv3 = dv0_sovDv3*0.5;
    dv1_sovDv4 = dv0_sovDv4*0.5;
    dv1_sovDv5 = dv0_sovDv5*0.5;
    v1_sov = (v0_sov*0.5-3.0*a2_sov*a3_sov);

    ddpsigs0Dv1 = (dv1_sovDv1+1/(2*sqrt((v1_sov*v1_sov+6.0*a2_sov*v0_sov)))*(((v1_sov*dv1_sovDv1+dv1_sovDv1*v1_sov)+6.0*a2_sov*dv0_sovDv1)));
    ddpsigs0Dv3 = (dv1_sovDv3+1/(2*sqrt((v1_sov*v1_sov+6.0*a2_sov*v0_sov)))*(((v1_sov*dv1_sovDv3+dv1_sovDv3*v1_sov)+6.0*a2_sov*dv0_sovDv3)));
    ddpsigs0Dv4 = (dv1_sovDv4+1/(2*sqrt((v1_sov*v1_sov+6.0*a2_sov*v0_sov)))*(((v1_sov*dv1_sovDv4+dv1_sovDv4*v1_sov)+6.0*a2_sov*dv0_sovDv4)));
    ddpsigs0Dv5 = (dv1_sovDv5+1/(2*sqrt((v1_sov*v1_sov+6.0*a2_sov*v0_sov)))*(((v1_sov*dv1_sovDv5+dv1_sovDv5*v1_sov)+6.0*a2_sov*dv0_sovDv5)));
    dpsigs0 = (v1_sov+sqrt((v1_sov*v1_sov+6.0*a2_sov*v0_sov)));

    dgamma_dep2_sovDv1 = gamma_dep_sov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0))*(dv0_sovDv1-ddpsigs0Dv1))/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0));
    dgamma_dep2_sovDv3 = gamma_dep_sov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0))*(dv0_sovDv3-ddpsigs0Dv3))/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0));
    dgamma_dep2_sovDv4 = gamma_dep_sov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0))*(dv0_sovDv4-ddpsigs0Dv4))/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0));
    dgamma_dep2_sovDv5 = gamma_dep_sov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0))*(dv0_sovDv5-ddpsigs0Dv5))/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0));
    gamma_dep2_sov = gamma_dep_sov*(0.5+3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_sov+v0_sov)-dpsigs0)));

    da4_sovDv1 = (-exp((-dpsigs0))*((-ddpsigs0Dv1)));
    da4_sovDv3 = (-exp((-dpsigs0))*((-ddpsigs0Dv3)));
    da4_sovDv4 = (-exp((-dpsigs0))*((-ddpsigs0Dv4)));
    da4_sovDv5 = (-exp((-dpsigs0))*((-ddpsigs0Dv5)));
    a4_sov = (1.0-exp((-dpsigs0)));

    dv2_sovDv1 = (dv0_sovDv1-da4_sovDv1);
    dv2_sovDv3 = (dv0_sovDv3-da4_sovDv3);
    dv2_sovDv4 = (dv0_sovDv4-da4_sovDv4);
    dv2_sovDv5 = (dv0_sovDv5-da4_sovDv5);
    v2_sov = (v0_sov-a4_sov);

    dtmpDv1 = (dv2_sovDv1-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*(dgamma_dep2_sovDv1+1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(((gamma_dep2_sov*dgamma_dep2_sovDv1+dgamma_dep2_sovDv1*gamma_dep2_sov)+dv2_sovDv1))))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    dtmpDv3 = (dv2_sovDv3-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*(dgamma_dep2_sovDv3+1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(((gamma_dep2_sov*dgamma_dep2_sovDv3+dgamma_dep2_sovDv3*gamma_dep2_sov)+dv2_sovDv3))))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    dtmpDv4 = (dv2_sovDv4-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*(dgamma_dep2_sovDv4+1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(((gamma_dep2_sov*dgamma_dep2_sovDv4+dgamma_dep2_sovDv4*gamma_dep2_sov)+dv2_sovDv4))))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    dtmpDv5 = (dv2_sovDv5-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*(dgamma_dep2_sovDv5+1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(((gamma_dep2_sov*dgamma_dep2_sovDv5+dgamma_dep2_sovDv5*gamma_dep2_sov)+dv2_sovDv5))))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    tmp = v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));

    ddpsigsDv1 = ((tmp*dtmpDv1+dtmpDv1*tmp)+da4_sovDv1);
    ddpsigsDv3 = ((tmp*dtmpDv3+dtmpDv3*tmp)+da4_sovDv3);
    ddpsigsDv4 = ((tmp*dtmpDv4+dtmpDv4*tmp)+da4_sovDv4);
    ddpsigsDv5 = ((tmp*dtmpDv5+dtmpDv5*tmp)+da4_sovDv5);
    dpsigs = (tmp*tmp+a4_sov);

    dv2b_sovDv1 = (dv0_sovDv1-ddpsigsDv1);
    dv2b_sovDv3 = (dv0_sovDv3-ddpsigsDv3);
    dv2b_sovDv4 = (dv0_sovDv4-ddpsigsDv4);
    dv2b_sovDv5 = (dv0_sovDv5-ddpsigsDv5);
    v2b_sov = (v0_sov-dpsigs);

    dv3_sovDv1 = dv2b_sovDv1*0.5;
    dv3_sovDv3 = dv2b_sovDv3*0.5;
    dv3_sovDv4 = dv2b_sovDv4*0.5;
    dv3_sovDv5 = dv2b_sovDv5*0.5;
    v3_sov = v2b_sov*0.5;

    dtmpDv1 = dv3_sovDv1;
    dtmpDv3 = dv3_sovDv3;
    dtmpDv4 = dv3_sovDv4;
    dtmpDv5 = dv3_sovDv5;
    tmp = (v3_sov+3.0*a0_sov);

    if(vgsov_p>0.0){
    ddpsiox_sDv1 = (dv3_sovDv1+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv1+dtmpDv1*tmp)-6.0*dv2b_sovDv1)));
    ddpsiox_sDv3 = (dv3_sovDv3+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv3+dtmpDv3*tmp)-6.0*dv2b_sovDv3)));
    ddpsiox_sDv4 = (dv3_sovDv4+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv4+dtmpDv4*tmp)-6.0*dv2b_sovDv4)));
    ddpsiox_sDv5 = (dv3_sovDv5+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv5+dtmpDv5*tmp)-6.0*dv2b_sovDv5)));
    dpsiox_s = ((v3_sov-3.0*a0_sov)+sqrt((tmp*tmp-6.0*v2b_sov)));

    } else {
    ddpsiox_sDv1 = (-(dv3_sovDv1+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv1+dtmpDv1*tmp)-6.0*dv2b_sovDv1))));
    ddpsiox_sDv3 = (-(dv3_sovDv3+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv3+dtmpDv3*tmp)-6.0*dv2b_sovDv3))));
    ddpsiox_sDv4 = (-(dv3_sovDv4+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv4+dtmpDv4*tmp)-6.0*dv2b_sovDv4))));
    ddpsiox_sDv5 = (-(dv3_sovDv5+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv5+dtmpDv5*tmp)-6.0*dv2b_sovDv5))));
    dpsiox_s = (-((v3_sov-3.0*a0_sov)+sqrt((tmp*tmp-6.0*v2b_sov))));

    }
    } else {
    dvgsov_pDv1 = dvgDv1;
    dvgsov_pDv3 = (dvgDv3-model_.VOV*dvsDv3);
    dvgsov_pDv4 = (-model_.VOV*dvsDv4);
    dvgsov_pDv5 = (-model_.VOV*dvsDv5);
    vgsov_p = ((vg-model_.VOV*vs)-vfb_ov);

    dv3_sovDv1 = dv3_sovDv3 = dv3_sovDv4 = dv3_sovDv5 = 0.0;
    dv2_sovDv1 = dv2_sovDv3 = dv2_sovDv4 = dv2_sovDv5 = 0.0;
    da4_sovDv1 = da4_sovDv3 = da4_sovDv4 = da4_sovDv5 = 0.0;
    if(vgsov_p>0.0){
    gamma_acc_sov = gamma_ov;
    dv0_sovDv1 = dvgsov_pDv1;
    dv0_sovDv3 = dvgsov_pDv3;
    dv0_sovDv4 = dvgsov_pDv4;
    dv0_sovDv5 = dvgsov_pDv5;
    v0_sov = vgsov_p;

    a0_sov = 1.0+gamma_acc_sov*(0.70710678118654752440084436210485);
    dv1_sovDv1 = dv0_sovDv1*0.5;
    dv1_sovDv3 = dv0_sovDv3*0.5;
    dv1_sovDv4 = dv0_sovDv4*0.5;
    dv1_sovDv5 = dv0_sovDv5*0.5;
    v1_sov = (v0_sov*0.5-3.0*a0_sov*a0_sov);

    ddpsigs0Dv1 = (dv1_sovDv1+1/(2*sqrt(v1_sov*v1_sov))*((v1_sov*dv1_sovDv1+dv1_sovDv1*v1_sov)));
    ddpsigs0Dv3 = (dv1_sovDv3+1/(2*sqrt(v1_sov*v1_sov))*((v1_sov*dv1_sovDv3+dv1_sovDv3*v1_sov)));
    ddpsigs0Dv4 = (dv1_sovDv4+1/(2*sqrt(v1_sov*v1_sov))*((v1_sov*dv1_sovDv4+dv1_sovDv4*v1_sov)));
    ddpsigs0Dv5 = (dv1_sovDv5+1/(2*sqrt(v1_sov*v1_sov))*((v1_sov*dv1_sovDv5+dv1_sovDv5*v1_sov)));
    dpsigs0 = (v1_sov+sqrt(v1_sov*v1_sov));

    ddpsigsDv1 = (-exp((-dpsigs0))*((-ddpsigs0Dv1)));
    ddpsigsDv3 = (-exp((-dpsigs0))*((-ddpsigs0Dv3)));
    ddpsigsDv4 = (-exp((-dpsigs0))*((-ddpsigs0Dv4)));
    ddpsigsDv5 = (-exp((-dpsigs0))*((-ddpsigs0Dv5)));
    dpsigs = (1.0-exp((-dpsigs0)));

    dv2b_sovDv1 = (dv0_sovDv1-ddpsigsDv1);
    dv2b_sovDv3 = (dv0_sovDv3-ddpsigsDv3);
    dv2b_sovDv4 = (dv0_sovDv4-ddpsigsDv4);
    dv2b_sovDv5 = (dv0_sovDv5-ddpsigsDv5);
    v2b_sov = (v0_sov-dpsigs);

    dv3_sovDv1 = dv2b_sovDv1*0.5;
    dv3_sovDv3 = dv2b_sovDv3*0.5;
    dv3_sovDv4 = dv2b_sovDv4*0.5;
    dv3_sovDv5 = dv2b_sovDv5*0.5;
    v3_sov = v2b_sov*0.5;

    dtmpDv1 = dv3_sovDv1;
    dtmpDv3 = dv3_sovDv3;
    dtmpDv4 = dv3_sovDv4;
    dtmpDv5 = dv3_sovDv5;
    tmp = (v3_sov+3.0*a0_sov);

    ddpsiox_sDv1 = (dv3_sovDv1+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv1+dtmpDv1*tmp)-6.0*dv2b_sovDv1)));
    ddpsiox_sDv3 = (dv3_sovDv3+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv3+dtmpDv3*tmp)-6.0*dv2b_sovDv3)));
    ddpsiox_sDv4 = (dv3_sovDv4+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv4+dtmpDv4*tmp)-6.0*dv2b_sovDv4)));
    ddpsiox_sDv5 = (dv3_sovDv5+1/(2*sqrt((tmp*tmp-6.0*v2b_sov)))*(((tmp*dtmpDv5+dtmpDv5*tmp)-6.0*dv2b_sovDv5)));
    dpsiox_s = ((v3_sov-3.0*a0_sov)+sqrt((tmp*tmp-6.0*v2b_sov)));

    } else {
    gamma_dep_sov = gamma_ov;
    dv0_sovDv1 = (-dvgsov_pDv1);
    dv0_sovDv3 = (-dvgsov_pDv3);
    dv0_sovDv4 = (-dvgsov_pDv4);
    dv0_sovDv5 = (-dvgsov_pDv5);
    v0_sov = (-vgsov_p);

    a3_sov = 1.0+gamma_dep_sov*(0.70710678118654752440084436210485);
    dv1_sovDv1 = dv0_sovDv1*0.5;
    dv1_sovDv3 = dv0_sovDv3*0.5;
    dv1_sovDv4 = dv0_sovDv4*0.5;
    dv1_sovDv5 = dv0_sovDv5*0.5;
    v1_sov = (v0_sov*0.5-3.0*a3_sov);

    ddpsigs0Dv1 = (dv1_sovDv1+1/(2*sqrt((v1_sov*v1_sov+6.0*v0_sov)))*(((v1_sov*dv1_sovDv1+dv1_sovDv1*v1_sov)+6.0*dv0_sovDv1)));
    ddpsigs0Dv3 = (dv1_sovDv3+1/(2*sqrt((v1_sov*v1_sov+6.0*v0_sov)))*(((v1_sov*dv1_sovDv3+dv1_sovDv3*v1_sov)+6.0*dv0_sovDv3)));
    ddpsigs0Dv4 = (dv1_sovDv4+1/(2*sqrt((v1_sov*v1_sov+6.0*v0_sov)))*(((v1_sov*dv1_sovDv4+dv1_sovDv4*v1_sov)+6.0*dv0_sovDv4)));
    ddpsigs0Dv5 = (dv1_sovDv5+1/(2*sqrt((v1_sov*v1_sov+6.0*v0_sov)))*(((v1_sov*dv1_sovDv5+dv1_sovDv5*v1_sov)+6.0*dv0_sovDv5)));
    dpsigs0 = (v1_sov+sqrt((v1_sov*v1_sov+6.0*v0_sov)));

    gamma_dep2_sov = gamma_dep_sov*0.5;
    da4_sovDv1 = (-exp((-dpsigs0))*((-ddpsigs0Dv1)));
    da4_sovDv3 = (-exp((-dpsigs0))*((-ddpsigs0Dv3)));
    da4_sovDv4 = (-exp((-dpsigs0))*((-ddpsigs0Dv4)));
    da4_sovDv5 = (-exp((-dpsigs0))*((-ddpsigs0Dv5)));
    a4_sov = (1.0-exp((-dpsigs0)));

    dv2_sovDv1 = (dv0_sovDv1-da4_sovDv1);
    dv2_sovDv3 = (dv0_sovDv3-da4_sovDv3);
    dv2_sovDv4 = (dv0_sovDv4-da4_sovDv4);
    dv2_sovDv5 = (dv0_sovDv5-da4_sovDv5);
    v2_sov = (v0_sov-a4_sov);

    dtmpDv1 = (dv2_sovDv1-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(dv2_sovDv1))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    dtmpDv3 = (dv2_sovDv3-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(dv2_sovDv3))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    dtmpDv4 = (dv2_sovDv4-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(dv2_sovDv4))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    dtmpDv5 = (dv2_sovDv5-v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))))*1/(2*sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov)))*(dv2_sovDv5))/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));
    tmp = v2_sov/((gamma_dep2_sov+sqrt((gamma_dep2_sov*gamma_dep2_sov+v2_sov))));

    ddpsigsDv1 = ((tmp*dtmpDv1+dtmpDv1*tmp)+da4_sovDv1);
    ddpsigsDv3 = ((tmp*dtmpDv3+dtmpDv3*tmp)+da4_sovDv3);
    ddpsigsDv4 = ((tmp*dtmpDv4+dtmpDv4*tmp)+da4_sovDv4);
    ddpsigsDv5 = ((tmp*dtmpDv5+dtmpDv5*tmp)+da4_sovDv5);
    dpsigs = (tmp*tmp+a4_sov);

    dv2b_sovDv1 = (dv0_sovDv1-ddpsigsDv1);
    dv2b_sovDv3 = (dv0_sovDv3-ddpsigsDv3);
    dv2b_sovDv4 = (dv0_sovDv4-ddpsigsDv4);
    dv2b_sovDv5 = (dv0_sovDv5-ddpsigsDv5);
    v2b_sov = (v0_sov-dpsigs);

    ddpsiox_sDv1 = (-dv2b_sovDv1);
    ddpsiox_sDv3 = (-dv2b_sovDv3);
    ddpsiox_sDv4 = (-dv2b_sovDv4);
    ddpsiox_sDv5 = (-dv2b_sovDv5);
    dpsiox_s = (-v2b_sov);

    }
    dgamma_dep2_sovDv1 = dgamma_dep2_sovDv3 = dgamma_dep2_sovDv4 = dgamma_dep2_sovDv5 = 0.0;
    }
    if(model_.TG<0){
    dvgdov_pDv1 = dvgDv1;
    dvgdov_pDv3 = (dvgDv3-model_.VOV*dvdDv3);
    dvgdov_pDv4 = (-model_.VOV*dvdDv4);
    dvgdov_pDv5 = (-model_.VOV*dvdDv5);
    vgdov_p = ((vg-model_.VOV*vd)-vfb_ov);

    if(vgdov_p>0.0){
    gamma_dep_dov = gamma_g_ov;
    gamma_acc_dov = gamma_ov;
    dv0_dovDv1 = dvgdov_pDv1;
    dv0_dovDv3 = dvgdov_pDv3;
    dv0_dovDv4 = dvgdov_pDv4;
    dv0_dovDv5 = dvgdov_pDv5;
    v0_dov = vgdov_p;

    } else {
    gamma_dep_dov = gamma_ov;
    gamma_acc_dov = gamma_g_ov;
    dv0_dovDv1 = (-dvgdov_pDv1);
    dv0_dovDv3 = (-dvgdov_pDv3);
    dv0_dovDv4 = (-dvgdov_pDv4);
    dv0_dovDv5 = (-dvgdov_pDv5);
    v0_dov = (-vgdov_p);

    }
    a0_dov = 1.0+gamma_acc_dov*(0.70710678118654752440084436210485);
    a1_dov = gamma_dep_dov/gamma_acc_dov;
    a2_dov = a0_dov/(a0_dov+a1_dov);
    a3_dov = 1.0+gamma_dep_dov*(0.70710678118654752440084436210485)+a1_dov;
    dv1_dovDv1 = dv0_dovDv1*0.5;
    dv1_dovDv3 = dv0_dovDv3*0.5;
    dv1_dovDv4 = dv0_dovDv4*0.5;
    dv1_dovDv5 = dv0_dovDv5*0.5;
    v1_dov = (v0_dov*0.5-3.0*a2_dov*a3_dov);

    ddpsigd0Dv1 = (dv1_dovDv1+1/(2*sqrt((v1_dov*v1_dov+6.0*a2_dov*v0_dov)))*(((v1_dov*dv1_dovDv1+dv1_dovDv1*v1_dov)+6.0*a2_dov*dv0_dovDv1)));
    ddpsigd0Dv3 = (dv1_dovDv3+1/(2*sqrt((v1_dov*v1_dov+6.0*a2_dov*v0_dov)))*(((v1_dov*dv1_dovDv3+dv1_dovDv3*v1_dov)+6.0*a2_dov*dv0_dovDv3)));
    ddpsigd0Dv4 = (dv1_dovDv4+1/(2*sqrt((v1_dov*v1_dov+6.0*a2_dov*v0_dov)))*(((v1_dov*dv1_dovDv4+dv1_dovDv4*v1_dov)+6.0*a2_dov*dv0_dovDv4)));
    ddpsigd0Dv5 = (dv1_dovDv5+1/(2*sqrt((v1_dov*v1_dov+6.0*a2_dov*v0_dov)))*(((v1_dov*dv1_dovDv5+dv1_dovDv5*v1_dov)+6.0*a2_dov*dv0_dovDv5)));
    dpsigd0 = (v1_dov+sqrt((v1_dov*v1_dov+6.0*a2_dov*v0_dov)));

    dgamma_dep2_dovDv1 = gamma_dep_dov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0))*(dv0_dovDv1-ddpsigd0Dv1))/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0));
    dgamma_dep2_dovDv3 = gamma_dep_dov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0))*(dv0_dovDv3-ddpsigd0Dv3))/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0));
    dgamma_dep2_dovDv4 = gamma_dep_dov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0))*(dv0_dovDv4-ddpsigd0Dv4))/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0));
    dgamma_dep2_dovDv5 = gamma_dep_dov*(-3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0))*(dv0_dovDv5-ddpsigd0Dv5))/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0));
    gamma_dep2_dov = gamma_dep_dov*(0.5+3.0/(((3.0*1.4142135623730950488016887242097*gamma_acc_dov+v0_dov)-dpsigd0)));

    da4_dovDv1 = (-exp((-dpsigd0))*((-ddpsigd0Dv1)));
    da4_dovDv3 = (-exp((-dpsigd0))*((-ddpsigd0Dv3)));
    da4_dovDv4 = (-exp((-dpsigd0))*((-ddpsigd0Dv4)));
    da4_dovDv5 = (-exp((-dpsigd0))*((-ddpsigd0Dv5)));
    a4_dov = (1.0-exp((-dpsigd0)));

    dv2_dovDv1 = (dv0_dovDv1-da4_dovDv1);
    dv2_dovDv3 = (dv0_dovDv3-da4_dovDv3);
    dv2_dovDv4 = (dv0_dovDv4-da4_dovDv4);
    dv2_dovDv5 = (dv0_dovDv5-da4_dovDv5);
    v2_dov = (v0_dov-a4_dov);

    dtmpDv1 = (dv2_dovDv1-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*(dgamma_dep2_dovDv1+1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(((gamma_dep2_dov*dgamma_dep2_dovDv1+dgamma_dep2_dovDv1*gamma_dep2_dov)+dv2_dovDv1))))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    dtmpDv3 = (dv2_dovDv3-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*(dgamma_dep2_dovDv3+1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(((gamma_dep2_dov*dgamma_dep2_dovDv3+dgamma_dep2_dovDv3*gamma_dep2_dov)+dv2_dovDv3))))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    dtmpDv4 = (dv2_dovDv4-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*(dgamma_dep2_dovDv4+1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(((gamma_dep2_dov*dgamma_dep2_dovDv4+dgamma_dep2_dovDv4*gamma_dep2_dov)+dv2_dovDv4))))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    dtmpDv5 = (dv2_dovDv5-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*(dgamma_dep2_dovDv5+1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(((gamma_dep2_dov*dgamma_dep2_dovDv5+dgamma_dep2_dovDv5*gamma_dep2_dov)+dv2_dovDv5))))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    tmp = v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));

    ddpsigdDv1 = ((tmp*dtmpDv1+dtmpDv1*tmp)+da4_dovDv1);
    ddpsigdDv3 = ((tmp*dtmpDv3+dtmpDv3*tmp)+da4_dovDv3);
    ddpsigdDv4 = ((tmp*dtmpDv4+dtmpDv4*tmp)+da4_dovDv4);
    ddpsigdDv5 = ((tmp*dtmpDv5+dtmpDv5*tmp)+da4_dovDv5);
    dpsigd = (tmp*tmp+a4_dov);

    dv2b_dovDv1 = (dv0_dovDv1-ddpsigdDv1);
    dv2b_dovDv3 = (dv0_dovDv3-ddpsigdDv3);
    dv2b_dovDv4 = (dv0_dovDv4-ddpsigdDv4);
    dv2b_dovDv5 = (dv0_dovDv5-ddpsigdDv5);
    v2b_dov = (v0_dov-dpsigd);

    dv3_dovDv1 = dv2b_dovDv1*0.5;
    dv3_dovDv3 = dv2b_dovDv3*0.5;
    dv3_dovDv4 = dv2b_dovDv4*0.5;
    dv3_dovDv5 = dv2b_dovDv5*0.5;
    v3_dov = v2b_dov*0.5;

    dtmpDv1 = dv3_dovDv1;
    dtmpDv3 = dv3_dovDv3;
    dtmpDv4 = dv3_dovDv4;
    dtmpDv5 = dv3_dovDv5;
    tmp = (v3_dov+3.0*a0_dov);

    if(vgdov_p>0.0){
    ddpsiox_dDv1 = (dv3_dovDv1+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv1+dtmpDv1*tmp)-6.0*dv2b_dovDv1)));
    ddpsiox_dDv3 = (dv3_dovDv3+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv3+dtmpDv3*tmp)-6.0*dv2b_dovDv3)));
    ddpsiox_dDv4 = (dv3_dovDv4+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv4+dtmpDv4*tmp)-6.0*dv2b_dovDv4)));
    ddpsiox_dDv5 = (dv3_dovDv5+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv5+dtmpDv5*tmp)-6.0*dv2b_dovDv5)));
    dpsiox_d = ((v3_dov-3.0*a0_dov)+sqrt((tmp*tmp-6.0*v2b_dov)));

    } else {
    ddpsiox_dDv1 = (-(dv3_dovDv1+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv1+dtmpDv1*tmp)-6.0*dv2b_dovDv1))));
    ddpsiox_dDv3 = (-(dv3_dovDv3+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv3+dtmpDv3*tmp)-6.0*dv2b_dovDv3))));
    ddpsiox_dDv4 = (-(dv3_dovDv4+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv4+dtmpDv4*tmp)-6.0*dv2b_dovDv4))));
    ddpsiox_dDv5 = (-(dv3_dovDv5+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv5+dtmpDv5*tmp)-6.0*dv2b_dovDv5))));
    dpsiox_d = (-((v3_dov-3.0*a0_dov)+sqrt((tmp*tmp-6.0*v2b_dov))));

    }
    } else {
    dvgdov_pDv1 = dvgDv1;
    dvgdov_pDv3 = (dvgDv3-model_.VOV*dvdDv3);
    dvgdov_pDv4 = (-model_.VOV*dvdDv4);
    dvgdov_pDv5 = (-model_.VOV*dvdDv5);
    vgdov_p = ((vg-model_.VOV*vd)-vfb_ov);

    dv3_dovDv1 = dv3_dovDv3 = dv3_dovDv4 = dv3_dovDv5 = 0.0;
    dv2_dovDv1 = dv2_dovDv3 = dv2_dovDv4 = dv2_dovDv5 = 0.0;
    da4_dovDv1 = da4_dovDv3 = da4_dovDv4 = da4_dovDv5 = 0.0;
    if(vgdov_p>0.0){
    gamma_acc_dov = gamma_ov;
    dv0_dovDv1 = dvgdov_pDv1;
    dv0_dovDv3 = dvgdov_pDv3;
    dv0_dovDv4 = dvgdov_pDv4;
    dv0_dovDv5 = dvgdov_pDv5;
    v0_dov = vgdov_p;

    a0_dov = 1.0+gamma_acc_dov*(0.70710678118654752440084436210485);
    dv1_dovDv1 = dv0_dovDv1*0.5;
    dv1_dovDv3 = dv0_dovDv3*0.5;
    dv1_dovDv4 = dv0_dovDv4*0.5;
    dv1_dovDv5 = dv0_dovDv5*0.5;
    v1_dov = (v0_dov*0.5-3.0*a0_dov*a0_dov);

    ddpsigd0Dv1 = (dv1_dovDv1+1/(2*sqrt(v1_dov*v1_dov))*((v1_dov*dv1_dovDv1+dv1_dovDv1*v1_dov)));
    ddpsigd0Dv3 = (dv1_dovDv3+1/(2*sqrt(v1_dov*v1_dov))*((v1_dov*dv1_dovDv3+dv1_dovDv3*v1_dov)));
    ddpsigd0Dv4 = (dv1_dovDv4+1/(2*sqrt(v1_dov*v1_dov))*((v1_dov*dv1_dovDv4+dv1_dovDv4*v1_dov)));
    ddpsigd0Dv5 = (dv1_dovDv5+1/(2*sqrt(v1_dov*v1_dov))*((v1_dov*dv1_dovDv5+dv1_dovDv5*v1_dov)));
    dpsigd0 = (v1_dov+sqrt(v1_dov*v1_dov));

    ddpsigdDv1 = (-exp((-dpsigd0))*((-ddpsigd0Dv1)));
    ddpsigdDv3 = (-exp((-dpsigd0))*((-ddpsigd0Dv3)));
    ddpsigdDv4 = (-exp((-dpsigd0))*((-ddpsigd0Dv4)));
    ddpsigdDv5 = (-exp((-dpsigd0))*((-ddpsigd0Dv5)));
    dpsigd = (1.0-exp((-dpsigd0)));

    dv2b_dovDv1 = (dv0_dovDv1-ddpsigdDv1);
    dv2b_dovDv3 = (dv0_dovDv3-ddpsigdDv3);
    dv2b_dovDv4 = (dv0_dovDv4-ddpsigdDv4);
    dv2b_dovDv5 = (dv0_dovDv5-ddpsigdDv5);
    v2b_dov = (v0_dov-dpsigd);

    dv3_dovDv1 = dv2b_dovDv1*0.5;
    dv3_dovDv3 = dv2b_dovDv3*0.5;
    dv3_dovDv4 = dv2b_dovDv4*0.5;
    dv3_dovDv5 = dv2b_dovDv5*0.5;
    v3_dov = v2b_dov*0.5;

    dtmpDv1 = dv3_dovDv1;
    dtmpDv3 = dv3_dovDv3;
    dtmpDv4 = dv3_dovDv4;
    dtmpDv5 = dv3_dovDv5;
    tmp = (v3_dov+3.0*a0_dov);

    ddpsiox_dDv1 = (dv3_dovDv1+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv1+dtmpDv1*tmp)-6.0*dv2b_dovDv1)));
    ddpsiox_dDv3 = (dv3_dovDv3+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv3+dtmpDv3*tmp)-6.0*dv2b_dovDv3)));
    ddpsiox_dDv4 = (dv3_dovDv4+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv4+dtmpDv4*tmp)-6.0*dv2b_dovDv4)));
    ddpsiox_dDv5 = (dv3_dovDv5+1/(2*sqrt((tmp*tmp-6.0*v2b_dov)))*(((tmp*dtmpDv5+dtmpDv5*tmp)-6.0*dv2b_dovDv5)));
    dpsiox_d = ((v3_dov-3.0*a0_dov)+sqrt((tmp*tmp-6.0*v2b_dov)));

    } else {
    gamma_dep_dov = gamma_ov;
    dv0_dovDv1 = (-dvgdov_pDv1);
    dv0_dovDv3 = (-dvgdov_pDv3);
    dv0_dovDv4 = (-dvgdov_pDv4);
    dv0_dovDv5 = (-dvgdov_pDv5);
    v0_dov = (-vgdov_p);

    a3_dov = 1.0+gamma_dep_dov*(0.70710678118654752440084436210485);
    dv1_dovDv1 = dv0_dovDv1*0.5;
    dv1_dovDv3 = dv0_dovDv3*0.5;
    dv1_dovDv4 = dv0_dovDv4*0.5;
    dv1_dovDv5 = dv0_dovDv5*0.5;
    v1_dov = (v0_dov*0.5-3.0*a3_dov);

    ddpsigd0Dv1 = (dv1_dovDv1+1/(2*sqrt((v1_dov*v1_dov+6.0*v0_dov)))*(((v1_dov*dv1_dovDv1+dv1_dovDv1*v1_dov)+6.0*dv0_dovDv1)));
    ddpsigd0Dv3 = (dv1_dovDv3+1/(2*sqrt((v1_dov*v1_dov+6.0*v0_dov)))*(((v1_dov*dv1_dovDv3+dv1_dovDv3*v1_dov)+6.0*dv0_dovDv3)));
    ddpsigd0Dv4 = (dv1_dovDv4+1/(2*sqrt((v1_dov*v1_dov+6.0*v0_dov)))*(((v1_dov*dv1_dovDv4+dv1_dovDv4*v1_dov)+6.0*dv0_dovDv4)));
    ddpsigd0Dv5 = (dv1_dovDv5+1/(2*sqrt((v1_dov*v1_dov+6.0*v0_dov)))*(((v1_dov*dv1_dovDv5+dv1_dovDv5*v1_dov)+6.0*dv0_dovDv5)));
    dpsigd0 = (v1_dov+sqrt((v1_dov*v1_dov+6.0*v0_dov)));

    gamma_dep2_dov = gamma_dep_dov*0.5;
    da4_dovDv1 = (-exp((-dpsigd0))*((-ddpsigd0Dv1)));
    da4_dovDv3 = (-exp((-dpsigd0))*((-ddpsigd0Dv3)));
    da4_dovDv4 = (-exp((-dpsigd0))*((-ddpsigd0Dv4)));
    da4_dovDv5 = (-exp((-dpsigd0))*((-ddpsigd0Dv5)));
    a4_dov = (1.0-exp((-dpsigd0)));

    dv2_dovDv1 = (dv0_dovDv1-da4_dovDv1);
    dv2_dovDv3 = (dv0_dovDv3-da4_dovDv3);
    dv2_dovDv4 = (dv0_dovDv4-da4_dovDv4);
    dv2_dovDv5 = (dv0_dovDv5-da4_dovDv5);
    v2_dov = (v0_dov-a4_dov);

    dtmpDv1 = (dv2_dovDv1-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(dv2_dovDv1))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    dtmpDv3 = (dv2_dovDv3-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(dv2_dovDv3))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    dtmpDv4 = (dv2_dovDv4-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(dv2_dovDv4))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    dtmpDv5 = (dv2_dovDv5-v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))))*1/(2*sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov)))*(dv2_dovDv5))/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));
    tmp = v2_dov/((gamma_dep2_dov+sqrt((gamma_dep2_dov*gamma_dep2_dov+v2_dov))));

    ddpsigdDv1 = ((tmp*dtmpDv1+dtmpDv1*tmp)+da4_dovDv1);
    ddpsigdDv3 = ((tmp*dtmpDv3+dtmpDv3*tmp)+da4_dovDv3);
    ddpsigdDv4 = ((tmp*dtmpDv4+dtmpDv4*tmp)+da4_dovDv4);
    ddpsigdDv5 = ((tmp*dtmpDv5+dtmpDv5*tmp)+da4_dovDv5);
    dpsigd = (tmp*tmp+a4_dov);

    dv2b_dovDv1 = (dv0_dovDv1-ddpsigdDv1);
    dv2b_dovDv3 = (dv0_dovDv3-ddpsigdDv3);
    dv2b_dovDv4 = (dv0_dovDv4-ddpsigdDv4);
    dv2b_dovDv5 = (dv0_dovDv5-ddpsigdDv5);
    v2b_dov = (v0_dov-dpsigd);

    ddpsiox_dDv1 = (-dv2b_dovDv1);
    ddpsiox_dDv3 = (-dv2b_dovDv3);
    ddpsiox_dDv4 = (-dv2b_dovDv4);
    ddpsiox_dDv5 = (-dv2b_dovDv5);
    dpsiox_d = (-v2b_dov);

    }
    dgamma_dep2_dovDv1 = dgamma_dep2_dovDv3 = dgamma_dep2_dovDv4 = dgamma_dep2_dovDv5 = 0.0;
    }
    dQSOVDv1 = ((-Q0OV)*ddpsiox_sDv1+(-0)*dpsiox_s);
    dQSOVDv3 = ((-Q0OV)*ddpsiox_sDv3+(-0)*dpsiox_s);
    dQSOVDv4 = ((-Q0OV)*ddpsiox_sDv4+(-0)*dpsiox_s);
    dQSOVDv5 = ((-Q0OV)*ddpsiox_sDv5+(-0)*dpsiox_s);
    QSOV = (-Q0OV)*dpsiox_s;

    dQDOVDv1 = ((-Q0OV)*ddpsiox_dDv1+(-0)*dpsiox_d);
    dQDOVDv3 = ((-Q0OV)*ddpsiox_dDv3+(-0)*dpsiox_d);
    dQDOVDv4 = ((-Q0OV)*ddpsiox_dDv4+(-0)*dpsiox_d);
    dQDOVDv5 = ((-Q0OV)*ddpsiox_dDv5+(-0)*dpsiox_d);
    QDOV = (-Q0OV)*dpsiox_d;

    } else {
    dpsiox_s = 0.0;
    QSOV = 0.0;
    dpsiox_d = 0.0;
    QDOV = 0.0;
    dQDOVDv1 = dQDOVDv3 = dQDOVDv4 = dQDOVDv5 = 0.0;
    dQSOVDv1 = dQSOVDv3 = dQSOVDv4 = dQSOVDv5 = 0.0;
    ddpsiox_dDv1 = ddpsiox_dDv3 = ddpsiox_dDv4 = ddpsiox_dDv5 = 0.0;
    ddpsiox_sDv1 = ddpsiox_sDv3 = ddpsiox_sDv4 = ddpsiox_sDv5 = 0.0;
    }
    dDdtExp10Dv1 = dQDOVDv1;
    dDdtExp10Dv3 = dQDOVDv3;
    dDdtExp10Dv4 = dQDOVDv4;
    dDdtExp10Dv5 = dQDOVDv5;
    DdtExp10 = QDOV;

    dDdtAns10Dv1 = 0;
    dDdtAns10Dv3 = 0;
    dDdtAns10Dv4 = 0;
    dDdtAns10Dv5 = 0;
    DdtAns10 = DdtExp10;

    dDdtAns10Dv1 = dDdtExp10Dv1 * _der0;
    dDdtAns10Dv3 = dDdtExp10Dv3 * _der0;
    dDdtAns10Dv4 = dDdtExp10Dv4 * _der0;
    dDdtAns10Dv5 = dDdtExp10Dv5 * _der0;
    dDdtExp11Dv1 = dQSOVDv1;
    dDdtExp11Dv3 = dQSOVDv3;
    dDdtExp11Dv4 = dQSOVDv4;
    dDdtExp11Dv5 = dQSOVDv5;
    DdtExp11 = QSOV;

    dDdtAns11Dv1 = 0;
    dDdtAns11Dv3 = 0;
    dDdtAns11Dv4 = 0;
    dDdtAns11Dv5 = 0;
    DdtAns11 = DdtExp11;

    dDdtAns11Dv1 = dDdtExp11Dv1 * _der0;
    dDdtAns11Dv3 = dDdtExp11Dv3 * _der0;
    dDdtAns11Dv4 = dDdtExp11Dv4 * _der0;
    dDdtAns11Dv5 = dDdtExp11Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns10+(1-d_gt_s_flag)*DdtAns11);

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns10Dv1+(1-d_gt_s_flag)*dDdtAns11Dv1);
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns10Dv3+(1-d_gt_s_flag)*dDdtAns11Dv3);
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns10Dv4+(1-d_gt_s_flag)*dDdtAns11Dv4);
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns10Dv5+(1-d_gt_s_flag)*dDdtAns11Dv5);
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns10+(1-d_gt_s_flag)*DdtAns11);

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r4c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r4c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r4c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r4c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dDdtExp12Dv1 = dQSOVDv1;
    dDdtExp12Dv3 = dQSOVDv3;
    dDdtExp12Dv4 = dQSOVDv4;
    dDdtExp12Dv5 = dQSOVDv5;
    DdtExp12 = QSOV;

    dDdtAns12Dv1 = 0;
    dDdtAns12Dv3 = 0;
    dDdtAns12Dv4 = 0;
    dDdtAns12Dv5 = 0;
    DdtAns12 = DdtExp12;

    dDdtAns12Dv1 = dDdtExp12Dv1 * _der0;
    dDdtAns12Dv3 = dDdtExp12Dv3 * _der0;
    dDdtAns12Dv4 = dDdtExp12Dv4 * _der0;
    dDdtAns12Dv5 = dDdtExp12Dv5 * _der0;
    dDdtExp13Dv1 = dQDOVDv1;
    dDdtExp13Dv3 = dQDOVDv3;
    dDdtExp13Dv4 = dQDOVDv4;
    dDdtExp13Dv5 = dQDOVDv5;
    DdtExp13 = QDOV;

    dDdtAns13Dv1 = 0;
    dDdtAns13Dv3 = 0;
    dDdtAns13Dv4 = 0;
    dDdtAns13Dv5 = 0;
    DdtAns13 = DdtExp13;

    dDdtAns13Dv1 = dDdtExp13Dv1 * _der0;
    dDdtAns13Dv3 = dDdtExp13Dv3 * _der0;
    dDdtAns13Dv4 = dDdtExp13Dv4 * _der0;
    dDdtAns13Dv5 = dDdtExp13Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns12+(1-d_gt_s_flag)*DdtAns13);

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns12Dv1+(1-d_gt_s_flag)*dDdtAns13Dv1);
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns12Dv3+(1-d_gt_s_flag)*dDdtAns13Dv3);
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns12Dv4+(1-d_gt_s_flag)*dDdtAns13Dv4);
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns12Dv5+(1-d_gt_s_flag)*dDdtAns13Dv5);
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns12+(1-d_gt_s_flag)*DdtAns13);

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r5c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r5c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r5c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r5c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    if(model_.KJF!=0.0){
    dtmpDv1 = (-(dpsi_pDv1-2.0*dqsDv1));
    dtmpDv3 = (dvsDv3-(dpsi_pDv3-2.0*dqsDv3));
    dtmpDv4 = (dvsDv4-(dpsi_pDv4-2.0*dqsDv4));
    dtmpDv5 = (dvsDv5-(dpsi_pDv5-2.0*dqsDv5));
    tmp = (((vbi+model_.VFR/(UT))+vs)-(psi_p-2.0*qs));

    dQSFRDv1 = Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vs)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv1+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv1+dtmpDv1*tmp))));
    dQSFRDv3 = (Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vs)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv3+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv3+dtmpDv3*tmp))))+Weffc*NF*model_.KJF*model_.CJF*UT*dvsDv3*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))));
    dQSFRDv4 = (Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vs)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv4+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv4+dtmpDv4*tmp))))+Weffc*NF*model_.KJF*model_.CJF*UT*dvsDv4*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))));
    dQSFRDv5 = (Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vs)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv5+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv5+dtmpDv5*tmp))))+Weffc*NF*model_.KJF*model_.CJF*UT*dvsDv5*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))));
    QSFR = Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vs)*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR))));

    dtmpDv1 = (dvdpDv1-(dpsi_pDv1-2.0*dqdpDv1));
    dtmpDv3 = (dvdpDv3-(dpsi_pDv3-2.0*dqdpDv3));
    dtmpDv4 = (dvdpDv4-(dpsi_pDv4-2.0*dqdpDv4));
    dtmpDv5 = (dvdpDv5-(dpsi_pDv5-2.0*dqdpDv5));
    tmp = (((vbi+model_.VFR/(UT))+vdp)-(psi_p-2.0*qdp));

    dQDFRDv1 = (Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vdp)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv1+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv1+dtmpDv1*tmp))))+Weffc*NF*model_.KJF*model_.CJF*UT*dvdpDv1*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))));
    dQDFRDv3 = (Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vdp)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv3+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv3+dtmpDv3*tmp))))+Weffc*NF*model_.KJF*model_.CJF*UT*dvdpDv3*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))));
    dQDFRDv4 = (Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vdp)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv4+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv4+dtmpDv4*tmp))))+Weffc*NF*model_.KJF*model_.CJF*UT*dvdpDv4*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))));
    dQDFRDv5 = (Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vdp)*1/(2*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))))*(UT*0.5*(dtmpDv5+1/(2*sqrt((tmp*tmp+model_.DFR)))*((tmp*dtmpDv5+dtmpDv5*tmp))))+Weffc*NF*model_.KJF*model_.CJF*UT*dvdpDv5*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR)))));
    QDFR = Weffc*NF*model_.KJF*(1.0+model_.CJF*UT*vdp)*sqrt(UT*0.5*(tmp+sqrt((tmp*tmp+model_.DFR))));

    } else {
    QSFR = 0.0;
    QDFR = 0.0;
    dQDFRDv1 = dQDFRDv3 = dQDFRDv4 = dQDFRDv5 = 0.0;
    dQSFRDv1 = dQSFRDv3 = dQSFRDv4 = dQSFRDv5 = 0.0;
    }
    dDdtExp14Dv1 = dQDFRDv1;
    dDdtExp14Dv3 = dQDFRDv3;
    dDdtExp14Dv4 = dQDFRDv4;
    dDdtExp14Dv5 = dQDFRDv5;
    DdtExp14 = QDFR;

    dDdtAns14Dv1 = 0;
    dDdtAns14Dv3 = 0;
    dDdtAns14Dv4 = 0;
    dDdtAns14Dv5 = 0;
    DdtAns14 = DdtExp14;

    dDdtAns14Dv1 = dDdtExp14Dv1 * _der0;
    dDdtAns14Dv3 = dDdtExp14Dv3 * _der0;
    dDdtAns14Dv4 = dDdtExp14Dv4 * _der0;
    dDdtAns14Dv5 = dDdtExp14Dv5 * _der0;
    dDdtExp15Dv1 = dQSFRDv1;
    dDdtExp15Dv3 = dQSFRDv3;
    dDdtExp15Dv4 = dQSFRDv4;
    dDdtExp15Dv5 = dQSFRDv5;
    DdtExp15 = QSFR;

    dDdtAns15Dv1 = 0;
    dDdtAns15Dv3 = 0;
    dDdtAns15Dv4 = 0;
    dDdtAns15Dv5 = 0;
    DdtAns15 = DdtExp15;

    dDdtAns15Dv1 = dDdtExp15Dv1 * _der0;
    dDdtAns15Dv3 = dDdtExp15Dv3 * _der0;
    dDdtAns15Dv4 = dDdtExp15Dv4 * _der0;
    dDdtAns15Dv5 = dDdtExp15Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns14+(1-d_gt_s_flag)*DdtAns15);

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns14Dv1+(1-d_gt_s_flag)*dDdtAns15Dv1);
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns14Dv3+(1-d_gt_s_flag)*dDdtAns15Dv3);
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns14Dv4+(1-d_gt_s_flag)*dDdtAns15Dv4);
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns14Dv5+(1-d_gt_s_flag)*dDdtAns15Dv5);
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns14+(1-d_gt_s_flag)*DdtAns15);

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r4c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r4c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r4c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r4c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dDdtExp16Dv1 = dQSFRDv1;
    dDdtExp16Dv3 = dQSFRDv3;
    dDdtExp16Dv4 = dQSFRDv4;
    dDdtExp16Dv5 = dQSFRDv5;
    DdtExp16 = QSFR;

    dDdtAns16Dv1 = 0;
    dDdtAns16Dv3 = 0;
    dDdtAns16Dv4 = 0;
    dDdtAns16Dv5 = 0;
    DdtAns16 = DdtExp16;

    dDdtAns16Dv1 = dDdtExp16Dv1 * _der0;
    dDdtAns16Dv3 = dDdtExp16Dv3 * _der0;
    dDdtAns16Dv4 = dDdtExp16Dv4 * _der0;
    dDdtAns16Dv5 = dDdtExp16Dv5 * _der0;
    dDdtExp17Dv1 = dQDFRDv1;
    dDdtExp17Dv3 = dQDFRDv3;
    dDdtExp17Dv4 = dQDFRDv4;
    dDdtExp17Dv5 = dQDFRDv5;
    DdtExp17 = QDFR;

    dDdtAns17Dv1 = 0;
    dDdtAns17Dv3 = 0;
    dDdtAns17Dv4 = 0;
    dDdtAns17Dv5 = 0;
    DdtAns17 = DdtExp17;

    dDdtAns17Dv1 = dDdtExp17Dv1 * _der0;
    dDdtAns17Dv3 = dDdtExp17Dv3 * _der0;
    dDdtAns17Dv4 = dDdtExp17Dv4 * _der0;
    dDdtAns17Dv5 = dDdtExp17Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0);
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns16+(1-d_gt_s_flag)*DdtAns17);

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns16Dv1+(1-d_gt_s_flag)*dDdtAns17Dv1);
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns16Dv3+(1-d_gt_s_flag)*dDdtAns17Dv3);
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns16Dv4+(1-d_gt_s_flag)*dDdtAns17Dv4);
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns16Dv5+(1-d_gt_s_flag)*dDdtAns17Dv5);
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns16+(1-d_gt_s_flag)*DdtAns17);

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r5c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r5c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r5c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r5c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dvgseDv1 = (dpsi_pDv1-2.0*dqsDv1);
    dvgseDv3 = (dpsi_pDv3-2.0*dqsDv3);
    dvgseDv4 = (dpsi_pDv4-2.0*dqsDv4);
    dvgseDv5 = (dpsi_pDv5-2.0*dqsDv5);
    vgse = ((vfb+psi_p)-2.0*qs);

    dtmp1Dv1 = (dvdpDv1-dvgseDv1)*UT;
    dtmp1Dv3 = ((dvdpDv3-dvsDv3)-dvgseDv3)*UT;
    dtmp1Dv4 = ((dvdpDv4-dvsDv4)-dvgseDv4)*UT;
    dtmp1Dv5 = ((dvdpDv5-dvsDv5)-dvgseDv5)*UT;
    tmp1 = (((vdp-vs)-vgse)*UT-model_.EGIDL);

    dtmp2Dv1 = dtmp2Dv3 = dtmp2Dv4 = dtmp2Dv5 = 0.0;
    if(tmp1<1.0e-10){
    IGIDL = 0.0;
    dIGIDLDv1 = dIGIDLDv3 = dIGIDLDv4 = dIGIDLDv5 = 0.0;
    } else {
    dtmp2Dv1 = (vdp*vdp*dvdpDv1+(vdp*dvdpDv1+dvdpDv1*vdp)*vdp)*UT3;
    dtmp2Dv3 = (vdp*vdp*dvdpDv3+(vdp*dvdpDv3+dvdpDv3*vdp)*vdp)*UT3;
    dtmp2Dv4 = (vdp*vdp*dvdpDv4+(vdp*dvdpDv4+dvdpDv4*vdp)*vdp)*UT3;
    dtmp2Dv5 = (vdp*vdp*dvdpDv5+(vdp*dvdpDv5+dvdpDv5*vdp)*vdp)*UT3;
    tmp2 = vdp*vdp*vdp*UT3;

    dIGIDLDv1 = ((model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*dtmp2Dv1+(model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv1)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2)-model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2))*dtmp2Dv1)/((model_.CGIDL+tmp2));
    dIGIDLDv3 = ((model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*dtmp2Dv3+(model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv3)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv3/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2)-model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2))*dtmp2Dv3)/((model_.CGIDL+tmp2));
    dIGIDLDv4 = ((model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*dtmp2Dv4+(model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv4)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv4/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2)-model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2))*dtmp2Dv4)/((model_.CGIDL+tmp2));
    dIGIDLDv5 = ((model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*dtmp2Dv5+(model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv5)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv5/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2)-model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2))*dtmp2Dv5)/((model_.CGIDL+tmp2));
    IGIDL = model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2));

    }
    dvgdeDv1 = (dpsi_pDv1-2.0*dqdpDv1);
    dvgdeDv3 = (dpsi_pDv3-2.0*dqdpDv3);
    dvgdeDv4 = (dpsi_pDv4-2.0*dqdpDv4);
    dvgdeDv5 = (dpsi_pDv5-2.0*dqdpDv5);
    vgde = ((vfb+psi_p)-2.0*qdp);

    dtmp1Dv1 = ((-dvdpDv1)-dvgdeDv1)*UT;
    dtmp1Dv3 = ((dvsDv3-dvdpDv3)-dvgdeDv3)*UT;
    dtmp1Dv4 = ((dvsDv4-dvdpDv4)-dvgdeDv4)*UT;
    dtmp1Dv5 = ((dvsDv5-dvdpDv5)-dvgdeDv5)*UT;
    tmp1 = (((vs-vdp)-vgde)*UT-model_.EGIDL);

    if(tmp1<1.0e-10){
    IGISL = 0.0;
    dIGISLDv1 = dIGISLDv3 = dIGISLDv4 = dIGISLDv5 = 0.0;
    } else {
    dtmp2Dv3 = (vs*vs*dvsDv3+(vs*dvsDv3+dvsDv3*vs)*vs)*UT3;
    dtmp2Dv4 = (vs*vs*dvsDv4+(vs*dvsDv4+dvsDv4*vs)*vs)*UT3;
    dtmp2Dv5 = (vs*vs*dvsDv5+(vs*dvsDv5+dvsDv5*vs)*vs)*UT3;
    tmp2 = vs*vs*vs*UT3;

    dIGISLDv1 = (model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv1)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2/((model_.CGIDL+tmp2));
    dIGISLDv3 = ((model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*dtmp2Dv3+(model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv3)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv3/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2)-model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2))*dtmp2Dv3)/((model_.CGIDL+tmp2));
    dIGISLDv4 = ((model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*dtmp2Dv4+(model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv4)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv4/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2)-model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2))*dtmp2Dv4)/((model_.CGIDL+tmp2));
    dIGISLDv5 = ((model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*dtmp2Dv5+(model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*(((-0)-(-3.0*TOX*model_.BGIDL)/(tmp1)*dtmp1Dv5)/(tmp1))+model_.AGIDL*WeffNF*dtmp1Dv5/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1)))*tmp2)-model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2))*dtmp2Dv5)/((model_.CGIDL+tmp2));
    IGISL = model_.AGIDL*WeffNF*tmp1/(3.0*TOX)*exp((-3.0*TOX*model_.BGIDL)/(tmp1))*tmp2/((model_.CGIDL+tmp2));

    dtmp2Dv1 = 0.0;
    }
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv1+(1-d_gt_s_flag)*dIGISLDv1);
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv3+(1-d_gt_s_flag)*dIGISLDv3);
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv4+(1-d_gt_s_flag)*dIGISLDv4);
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv5+(1-d_gt_s_flag)*dIGISLDv5);
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*IGIDL+(1-d_gt_s_flag)*IGISL);

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv1+(1-d_gt_s_flag)*dIGISLDv1);
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv3+(1-d_gt_s_flag)*dIGISLDv3);
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv4+(1-d_gt_s_flag)*dIGISLDv4);
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGIDLDv5+(1-d_gt_s_flag)*dIGISLDv5);
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*IGIDL+(1-d_gt_s_flag)*IGISL);

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r3c1 += -dcontributetmpDv1;
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r3c4 += -dcontributetmpDv4;
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r3c5 += -dcontributetmpDv5;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv1+(1-d_gt_s_flag)*dIGIDLDv1);
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv3+(1-d_gt_s_flag)*dIGIDLDv3);
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv4+(1-d_gt_s_flag)*dIGIDLDv4);
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv5+(1-d_gt_s_flag)*dIGIDLDv5);
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*IGISL+(1-d_gt_s_flag)*IGIDL);

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv1+(1-d_gt_s_flag)*dIGIDLDv1);
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv3+(1-d_gt_s_flag)*dIGIDLDv3);
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv4+(1-d_gt_s_flag)*dIGIDLDv4);
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dIGISLDv5+(1-d_gt_s_flag)*dIGIDLDv5);
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*IGISL+(1-d_gt_s_flag)*IGIDL);

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r3c1 += -dcontributetmpDv1;
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r3c4 += -dcontributetmpDv4;
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r3c5 += -dcontributetmpDv5;
    dv2_igDv1 = dv2_igDv3 = dv2_igDv4 = dv2_igDv5 = 0.0;
    dv1_igDv1 = dv1_igDv3 = dv1_igDv4 = dv1_igDv5 = 0.0;
    ds1_pxDv1 = ds1_pxDv3 = ds1_pxDv4 = ds1_pxDv5 = 0.0;
    dpsi_xr_ov_sDv1 = dpsi_xr_ov_sDv3 = dpsi_xr_ov_sDv4 = dpsi_xr_ov_sDv5 = 0.0;
    dpsi_xr_ov_dDv1 = dpsi_xr_ov_dDv3 = dpsi_xr_ov_dDv4 = dpsi_xr_ov_dDv5 = 0.0;
    dpsi_xDv1 = dpsi_xDv3 = dpsi_xDv4 = dpsi_xDv5 = 0.0;
    dpsi_oxr_ov_sDv1 = dpsi_oxr_ov_sDv3 = dpsi_oxr_ov_sDv4 = dpsi_oxr_ov_sDv5 = 0.0;
    dpsi_oxr_ov_dDv1 = dpsi_oxr_ov_dDv3 = dpsi_oxr_ov_dDv4 = dpsi_oxr_ov_dDv5 = 0.0;
    dpsi_oxDv1 = dpsi_oxDv3 = dpsi_oxDv4 = dpsi_oxDv5 = 0.0;
    dp_tun_sovDv1 = dp_tun_sovDv3 = dp_tun_sovDv4 = dp_tun_sovDv5 = 0.0;
    dp_tun_dovDv1 = dp_tun_dovDv3 = dp_tun_dovDv4 = dp_tun_dovDv5 = 0.0;
    dp_tunDv1 = dp_tunDv3 = dp_tunDv4 = dp_tunDv5 = 0.0;
    dnigsDv1 = dnigsDv3 = dnigsDv4 = dnigsDv5 = 0.0;
    dnigdDv1 = dnigdDv3 = dnigdDv4 = dnigdDv5 = 0.0;
    dnigcDv1 = dnigcDv3 = dnigcDv4 = dnigcDv5 = 0.0;
    digoDv1 = digoDv3 = digoDv4 = digoDv5 = 0.0;
    ddq_dksiDv1 = ddq_dksiDv3 = ddq_dksiDv4 = ddq_dksiDv5 = 0.0;
    dd_psi_dqDv1 = dd_psi_dqDv3 = dd_psi_dqDv4 = dd_psi_dqDv5 = 0.0;
    db_gcDv1 = db_gcDv3 = db_gcDv4 = db_gcDv5 = 0.0;
    da_gcDv1 = da_gcDv3 = da_gcDv4 = da_gcDv5 = 0.0;
    if(model_.KG>0.0){
    dv2_igDv1 = dv2_igDv3 = dv2_igDv4 = dv2_igDv5 = 0.0;
    dv1_igDv1 = dv1_igDv3 = dv1_igDv4 = dv1_igDv5 = 0.0;
    if(((psi_p>0)&&(model_.TG<0))||((psi_p<0)&&(model_.TG>0))){
    dv1_igDv1 = 1/(2*sqrt((0.25+(v_o+2.0*qs)/(gamma_g2))))*((dv_oDv1+2.0*dqsDv1)/(gamma_g2));
    dv1_igDv3 = 1/(2*sqrt((0.25+(v_o+2.0*qs)/(gamma_g2))))*((dv_oDv3+2.0*dqsDv3)/(gamma_g2));
    dv1_igDv4 = 1/(2*sqrt((0.25+(v_o+2.0*qs)/(gamma_g2))))*((dv_oDv4+2.0*dqsDv4)/(gamma_g2));
    dv1_igDv5 = 1/(2*sqrt((0.25+(v_o+2.0*qs)/(gamma_g2))))*((dv_oDv5+2.0*dqsDv5)/(gamma_g2));
    v1_ig = sqrt((0.25+(v_o+2.0*qs)/(gamma_g2)));

    dv2_igDv1 = dv1_igDv1;
    dv2_igDv3 = dv1_igDv3;
    dv2_igDv4 = dv1_igDv4;
    dv2_igDv5 = dv1_igDv5;
    v2_ig = (0.5+v1_ig);

    dpsi_oxDv1 = ((dv_oDv1+2.0*dqsDv1)-(v_o+2.0*qs)/(v2_ig)*dv2_igDv1)/(v2_ig);
    dpsi_oxDv3 = ((dv_oDv3+2.0*dqsDv3)-(v_o+2.0*qs)/(v2_ig)*dv2_igDv3)/(v2_ig);
    dpsi_oxDv4 = ((dv_oDv4+2.0*dqsDv4)-(v_o+2.0*qs)/(v2_ig)*dv2_igDv4)/(v2_ig);
    dpsi_oxDv5 = ((dv_oDv5+2.0*dqsDv5)-(v_o+2.0*qs)/(v2_ig)*dv2_igDv5)/(v2_ig);
    psi_ox = (v_o+2.0*qs)/(v2_ig);

    dd_psi_dqDv1 = (2.0/(v2_ig)*(-((dv_oDv1+2.0*dqsDv1)-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)*(2.0*v1_ig*dv2_igDv1+2.0*dv1_igDv1*v2_ig)*gamma_g2)/(2.0*v1_ig*v2_ig*gamma_g2))+(-2.0/(v2_ig)*dv2_igDv1)/(v2_ig)*(1.0-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)));
    dd_psi_dqDv3 = (2.0/(v2_ig)*(-((dv_oDv3+2.0*dqsDv3)-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)*(2.0*v1_ig*dv2_igDv3+2.0*dv1_igDv3*v2_ig)*gamma_g2)/(2.0*v1_ig*v2_ig*gamma_g2))+(-2.0/(v2_ig)*dv2_igDv3)/(v2_ig)*(1.0-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)));
    dd_psi_dqDv4 = (2.0/(v2_ig)*(-((dv_oDv4+2.0*dqsDv4)-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)*(2.0*v1_ig*dv2_igDv4+2.0*dv1_igDv4*v2_ig)*gamma_g2)/(2.0*v1_ig*v2_ig*gamma_g2))+(-2.0/(v2_ig)*dv2_igDv4)/(v2_ig)*(1.0-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)));
    dd_psi_dqDv5 = (2.0/(v2_ig)*(-((dv_oDv5+2.0*dqsDv5)-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)*(2.0*v1_ig*dv2_igDv5+2.0*dv1_igDv5*v2_ig)*gamma_g2)/(2.0*v1_ig*v2_ig*gamma_g2))+(-2.0/(v2_ig)*dv2_igDv5)/(v2_ig)*(1.0-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2)));
    d_psi_dq = 2.0/(v2_ig)*(1.0-(v_o+2.0*qs)/(2.0*v1_ig*v2_ig*gamma_g2));

    } else {
    dpsi_oxDv1 = (dv_oDv1+2.0*dqsDv1);
    dpsi_oxDv3 = (dv_oDv3+2.0*dqsDv3);
    dpsi_oxDv4 = (dv_oDv4+2.0*dqsDv4);
    dpsi_oxDv5 = (dv_oDv5+2.0*dqsDv5);
    psi_ox = (v_o+2.0*qs);

    d_psi_dq = 2.0;
    dd_psi_dqDv1 = dd_psi_dqDv3 = dd_psi_dqDv4 = dd_psi_dqDv5 = 0.0;
    }
    dpsi_xDv1 = ((psi_ox>=0.0)?1:-1)*(dpsi_oxDv1)/(xb);
    dpsi_xDv3 = ((psi_ox>=0.0)?1:-1)*(dpsi_oxDv3)/(xb);
    dpsi_xDv4 = ((psi_ox>=0.0)?1:-1)*(dpsi_oxDv4)/(xb);
    dpsi_xDv5 = ((psi_ox>=0.0)?1:-1)*(dpsi_oxDv5)/(xb);
    psi_x = fabs(psi_ox)/(xb);

    ds1_pxDv1 = ds1_pxDv3 = ds1_pxDv4 = ds1_pxDv5 = 0.0;
    if(psi_x<1.0){
    ds1_pxDv1 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv1));
    ds1_pxDv3 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv3));
    ds1_pxDv4 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv4));
    ds1_pxDv5 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv5));
    s1_px = sqrt((1.0-psi_x));

    dp_tunDv1 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv1)/((1.0+s1_px))+ds1_pxDv1)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tunDv3 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv3)/((1.0+s1_px))+ds1_pxDv3)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tunDv4 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv4)/((1.0+s1_px))+ds1_pxDv4)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tunDv5 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv5)/((1.0+s1_px))+ds1_pxDv5)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    p_tun = exp((-ub)*(1.0/((1.0+s1_px))+s1_px));

    } else {
    dp_tunDv1 = exp((-ub)/(psi_x))*(((-0)-(-ub)/(psi_x)*dpsi_xDv1)/(psi_x));
    dp_tunDv3 = exp((-ub)/(psi_x))*(((-0)-(-ub)/(psi_x)*dpsi_xDv3)/(psi_x));
    dp_tunDv4 = exp((-ub)/(psi_x))*(((-0)-(-ub)/(psi_x)*dpsi_xDv4)/(psi_x));
    dp_tunDv5 = exp((-ub)/(psi_x))*(((-0)-(-ub)/(psi_x)*dpsi_xDv5)/(psi_x));
    p_tun = exp((-ub)/(psi_x));

    }
    digoDv1 = (qs*psi_ox*dp_tunDv1+(qs*dpsi_oxDv1+dqsDv1*psi_ox)*p_tun);
    digoDv3 = (qs*psi_ox*dp_tunDv3+(qs*dpsi_oxDv3+dqsDv3*psi_ox)*p_tun);
    digoDv4 = (qs*psi_ox*dp_tunDv4+(qs*dpsi_oxDv4+dqsDv4*psi_ox)*p_tun);
    digoDv5 = (qs*psi_ox*dp_tunDv5+(qs*dpsi_oxDv5+dqsDv5*psi_ox)*p_tun);
    igo = qs*psi_ox*p_tun;

    ddq_dksiDv1 = ddq_dksiDv3 = ddq_dksiDv4 = ddq_dksiDv5 = 0.0;
    db_gcDv1 = db_gcDv3 = db_gcDv4 = db_gcDv5 = 0.0;
    da_gcDv1 = da_gcDv3 = da_gcDv4 = da_gcDv5 = 0.0;
    if((vs==vd)||(psi_ox==0.0)){
    dnigcDv1 = (igo*dnqDv1+digoDv1*nq);
    dnigcDv3 = (igo*dnqDv3+digoDv3*nq);
    dnigcDv4 = (igo*dnqDv4+digoDv4*nq);
    dnigcDv5 = (igo*dnqDv5+digoDv5*nq);
    nigc = igo*nq;

    dnigsDv1 = dnigcDv1*0.5;
    dnigsDv3 = dnigcDv3*0.5;
    dnigsDv4 = dnigcDv4*0.5;
    dnigsDv5 = dnigcDv5*0.5;
    nigs = nigc*0.5;

    dnigdDv1 = dnigsDv1;
    dnigdDv3 = dnigsDv3;
    dnigdDv4 = dnigsDv4;
    dnigdDv5 = dnigsDv5;
    nigd = nigs;

    } else {
    ddq_dksiDv1 = ((dirpDv1-dif_Dv1)-(irp-if_)/((2.0*qs+1.0))*2.0*dqsDv1)/((2.0*qs+1.0));
    ddq_dksiDv3 = ((dirpDv3-dif_Dv3)-(irp-if_)/((2.0*qs+1.0))*2.0*dqsDv3)/((2.0*qs+1.0));
    ddq_dksiDv4 = ((dirpDv4-dif_Dv4)-(irp-if_)/((2.0*qs+1.0))*2.0*dqsDv4)/((2.0*qs+1.0));
    ddq_dksiDv5 = ((dirpDv5-dif_Dv5)-(irp-if_)/((2.0*qs+1.0))*2.0*dqsDv5)/((2.0*qs+1.0));
    dq_dksi = (irp-if_)/((2.0*qs+1.0));

    da_gcDv1 = (dq_dksi*((-1.0/(qs)*dqsDv1)/(qs)+(dd_psi_dqDv1-d_psi_dq/(psi_ox)*dpsi_oxDv1)/(psi_ox))+ddq_dksiDv1*(1.0/(qs)+d_psi_dq/(psi_ox)));
    da_gcDv3 = (dq_dksi*((-1.0/(qs)*dqsDv3)/(qs)+(dd_psi_dqDv3-d_psi_dq/(psi_ox)*dpsi_oxDv3)/(psi_ox))+ddq_dksiDv3*(1.0/(qs)+d_psi_dq/(psi_ox)));
    da_gcDv4 = (dq_dksi*((-1.0/(qs)*dqsDv4)/(qs)+(dd_psi_dqDv4-d_psi_dq/(psi_ox)*dpsi_oxDv4)/(psi_ox))+ddq_dksiDv4*(1.0/(qs)+d_psi_dq/(psi_ox)));
    da_gcDv5 = (dq_dksi*((-1.0/(qs)*dqsDv5)/(qs)+(dd_psi_dqDv5-d_psi_dq/(psi_ox)*dpsi_oxDv5)/(psi_ox))+ddq_dksiDv5*(1.0/(qs)+d_psi_dq/(psi_ox)));
    a_gc = dq_dksi*(1.0/(qs)+d_psi_dq/(psi_ox));

    ds1_pxDv1 = ds1_pxDv3 = ds1_pxDv4 = ds1_pxDv5 = 0.0;
    if(psi_x<1.0){
    ds1_pxDv1 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv1));
    ds1_pxDv3 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv3));
    ds1_pxDv4 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv4));
    ds1_pxDv5 = 1/(2*sqrt((1.0-psi_x)))*((-dpsi_xDv5));
    s1_px = sqrt((1.0-psi_x));

    if(psi_ox>0.0){
    db_gcDv1 = ((dq_dksi*d_psi_dq*ub/(xb)*dpsi_xDv1+(dq_dksi*dd_psi_dqDv1+ddq_dksiDv1*d_psi_dq)*ub/(xb)*(3.0+psi_x))-dq_dksi*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv1+2.0*ds1_pxDv1*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    db_gcDv3 = ((dq_dksi*d_psi_dq*ub/(xb)*dpsi_xDv3+(dq_dksi*dd_psi_dqDv3+ddq_dksiDv3*d_psi_dq)*ub/(xb)*(3.0+psi_x))-dq_dksi*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv3+2.0*ds1_pxDv3*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    db_gcDv4 = ((dq_dksi*d_psi_dq*ub/(xb)*dpsi_xDv4+(dq_dksi*dd_psi_dqDv4+ddq_dksiDv4*d_psi_dq)*ub/(xb)*(3.0+psi_x))-dq_dksi*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv4+2.0*ds1_pxDv4*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    db_gcDv5 = ((dq_dksi*d_psi_dq*ub/(xb)*dpsi_xDv5+(dq_dksi*dd_psi_dqDv5+ddq_dksiDv5*d_psi_dq)*ub/(xb)*(3.0+psi_x))-dq_dksi*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv5+2.0*ds1_pxDv5*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    b_gc = dq_dksi*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)));

    } else {
    db_gcDv1 = (((-dq_dksi)*d_psi_dq*ub/(xb)*dpsi_xDv1+((-dq_dksi)*dd_psi_dqDv1+(-ddq_dksiDv1)*d_psi_dq)*ub/(xb)*(3.0+psi_x))-(-dq_dksi)*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv1+2.0*ds1_pxDv1*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    db_gcDv3 = (((-dq_dksi)*d_psi_dq*ub/(xb)*dpsi_xDv3+((-dq_dksi)*dd_psi_dqDv3+(-ddq_dksiDv3)*d_psi_dq)*ub/(xb)*(3.0+psi_x))-(-dq_dksi)*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv3+2.0*ds1_pxDv3*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    db_gcDv4 = (((-dq_dksi)*d_psi_dq*ub/(xb)*dpsi_xDv4+((-dq_dksi)*dd_psi_dqDv4+(-ddq_dksiDv4)*d_psi_dq)*ub/(xb)*(3.0+psi_x))-(-dq_dksi)*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv4+2.0*ds1_pxDv4*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    db_gcDv5 = (((-dq_dksi)*d_psi_dq*ub/(xb)*dpsi_xDv5+((-dq_dksi)*dd_psi_dqDv5+(-ddq_dksiDv5)*d_psi_dq)*ub/(xb)*(3.0+psi_x))-(-dq_dksi)*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)))*(2.0*s1_px*dpsi_xDv5+2.0*ds1_pxDv5*(2.0+psi_x)))/((4.0+2.0*s1_px*(2.0+psi_x)));
    b_gc = (-dq_dksi)*d_psi_dq*ub/(xb)*(3.0+psi_x)/((4.0+2.0*s1_px*(2.0+psi_x)));

    }
    } else {
    db_gcDv1 = ((dq_dksi*dd_psi_dqDv1+ddq_dksiDv1*d_psi_dq)*ub-dq_dksi*d_psi_dq*ub/(psi_x*psi_ox)*(psi_x*dpsi_oxDv1+dpsi_xDv1*psi_ox))/(psi_x*psi_ox);
    db_gcDv3 = ((dq_dksi*dd_psi_dqDv3+ddq_dksiDv3*d_psi_dq)*ub-dq_dksi*d_psi_dq*ub/(psi_x*psi_ox)*(psi_x*dpsi_oxDv3+dpsi_xDv3*psi_ox))/(psi_x*psi_ox);
    db_gcDv4 = ((dq_dksi*dd_psi_dqDv4+ddq_dksiDv4*d_psi_dq)*ub-dq_dksi*d_psi_dq*ub/(psi_x*psi_ox)*(psi_x*dpsi_oxDv4+dpsi_xDv4*psi_ox))/(psi_x*psi_ox);
    db_gcDv5 = ((dq_dksi*dd_psi_dqDv5+ddq_dksiDv5*d_psi_dq)*ub-dq_dksi*d_psi_dq*ub/(psi_x*psi_ox)*(psi_x*dpsi_oxDv5+dpsi_xDv5*psi_ox))/(psi_x*psi_ox);
    b_gc = dq_dksi*d_psi_dq*ub/(psi_x*psi_ox);

    }
    dnigcDv1 = ((nq*igo*da_gcDv1+(nq*digoDv1+dnqDv1*igo)*(2.0+a_gc))-nq*igo*(2.0+a_gc)/((2.0-b_gc))*(-db_gcDv1))/((2.0-b_gc));
    dnigcDv3 = ((nq*igo*da_gcDv3+(nq*digoDv3+dnqDv3*igo)*(2.0+a_gc))-nq*igo*(2.0+a_gc)/((2.0-b_gc))*(-db_gcDv3))/((2.0-b_gc));
    dnigcDv4 = ((nq*igo*da_gcDv4+(nq*digoDv4+dnqDv4*igo)*(2.0+a_gc))-nq*igo*(2.0+a_gc)/((2.0-b_gc))*(-db_gcDv4))/((2.0-b_gc));
    dnigcDv5 = ((nq*igo*da_gcDv5+(nq*digoDv5+dnqDv5*igo)*(2.0+a_gc))-nq*igo*(2.0+a_gc)/((2.0-b_gc))*(-db_gcDv5))/((2.0-b_gc));
    nigc = nq*igo*(2.0+a_gc)/((2.0-b_gc));

    dnigsDv1 = ((0.5*nq*igo*da_gcDv1+(0.5*nq*digoDv1+0.5*dnqDv1*igo)*(3.0+a_gc))-0.5*nq*igo*(3.0+a_gc)/((3.0-b_gc))*(-db_gcDv1))/((3.0-b_gc));
    dnigsDv3 = ((0.5*nq*igo*da_gcDv3+(0.5*nq*digoDv3+0.5*dnqDv3*igo)*(3.0+a_gc))-0.5*nq*igo*(3.0+a_gc)/((3.0-b_gc))*(-db_gcDv3))/((3.0-b_gc));
    dnigsDv4 = ((0.5*nq*igo*da_gcDv4+(0.5*nq*digoDv4+0.5*dnqDv4*igo)*(3.0+a_gc))-0.5*nq*igo*(3.0+a_gc)/((3.0-b_gc))*(-db_gcDv4))/((3.0-b_gc));
    dnigsDv5 = ((0.5*nq*igo*da_gcDv5+(0.5*nq*digoDv5+0.5*dnqDv5*igo)*(3.0+a_gc))-0.5*nq*igo*(3.0+a_gc)/((3.0-b_gc))*(-db_gcDv5))/((3.0-b_gc));
    nigs = 0.5*nq*igo*(3.0+a_gc)/((3.0-b_gc));

    dnigdDv1 = (dnigcDv1-dnigsDv1);
    dnigdDv3 = (dnigcDv3-dnigsDv3);
    dnigdDv4 = (dnigcDv4-dnigsDv4);
    dnigdDv5 = (dnigcDv5-dnigsDv5);
    nigd = (nigc-nigs);

    }
    if(vg>vfb){
    IGB = 0.0;
    dIGDv1 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigcDv1/(TOX2);
    dIGDv3 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigcDv3/(TOX2);
    dIGDv4 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigcDv4/(TOX2);
    dIGDv5 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigcDv5/(TOX2);
    IG = 2.0*model_.KG*WeffNF*Leff*UT2*nigc/(TOX2);

    dIGDDv1 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigdDv1/(TOX2);
    dIGDDv3 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigdDv3/(TOX2);
    dIGDDv4 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigdDv4/(TOX2);
    dIGDDv5 = 2.0*model_.KG*WeffNF*Leff*UT2*dnigdDv5/(TOX2);
    IGD = 2.0*model_.KG*WeffNF*Leff*UT2*nigd/(TOX2);

    dIGSDv1 = (dIGDv1-dIGDDv1);
    dIGSDv3 = (dIGDv3-dIGDDv3);
    dIGSDv4 = (dIGDv4-dIGDDv4);
    dIGSDv5 = (dIGDv5-dIGDDv5);
    IGS = (IG-IGD);

    dIGBDv1 = dIGBDv3 = dIGBDv4 = dIGBDv5 = 0.0;
    } else {
    dIGBDv1 = (model_.KG*WeffNF*Leff*psi_ox*fabs(psi_ox)*UT2*dp_tunDv1+(model_.KG*WeffNF*Leff*psi_ox*((psi_ox>=0.0)?1:-1)*(dpsi_oxDv1)+model_.KG*WeffNF*Leff*dpsi_oxDv1*fabs(psi_ox))*UT2*p_tun)/(TOX2);
    dIGBDv3 = (model_.KG*WeffNF*Leff*psi_ox*fabs(psi_ox)*UT2*dp_tunDv3+(model_.KG*WeffNF*Leff*psi_ox*((psi_ox>=0.0)?1:-1)*(dpsi_oxDv3)+model_.KG*WeffNF*Leff*dpsi_oxDv3*fabs(psi_ox))*UT2*p_tun)/(TOX2);
    dIGBDv4 = (model_.KG*WeffNF*Leff*psi_ox*fabs(psi_ox)*UT2*dp_tunDv4+(model_.KG*WeffNF*Leff*psi_ox*((psi_ox>=0.0)?1:-1)*(dpsi_oxDv4)+model_.KG*WeffNF*Leff*dpsi_oxDv4*fabs(psi_ox))*UT2*p_tun)/(TOX2);
    dIGBDv5 = (model_.KG*WeffNF*Leff*psi_ox*fabs(psi_ox)*UT2*dp_tunDv5+(model_.KG*WeffNF*Leff*psi_ox*((psi_ox>=0.0)?1:-1)*(dpsi_oxDv5)+model_.KG*WeffNF*Leff*dpsi_oxDv5*fabs(psi_ox))*UT2*p_tun)/(TOX2);
    IGB = model_.KG*WeffNF*Leff*psi_ox*fabs(psi_ox)*UT2*p_tun/(TOX2);

    IG = 0.0;
    IGD = 0.0;
    IGS = 0.0;
    dIGDv1 = dIGDv3 = dIGDv4 = dIGDv5 = 0.0;
    dIGDDv1 = dIGDDv3 = dIGDDv4 = dIGDDv5 = 0.0;
    dIGSDv1 = dIGSDv3 = dIGSDv4 = dIGSDv5 = 0.0;
    }
    dpsi_xr_ov_sDv1 = dpsi_xr_ov_sDv3 = dpsi_xr_ov_sDv4 = dpsi_xr_ov_sDv5 = 0.0;
    dpsi_xr_ov_dDv1 = dpsi_xr_ov_dDv3 = dpsi_xr_ov_dDv4 = dpsi_xr_ov_dDv5 = 0.0;
    dpsi_oxr_ov_sDv1 = dpsi_oxr_ov_sDv3 = dpsi_oxr_ov_sDv4 = dpsi_oxr_ov_sDv5 = 0.0;
    dpsi_oxr_ov_dDv1 = dpsi_oxr_ov_dDv3 = dpsi_oxr_ov_dDv4 = dpsi_oxr_ov_dDv5 = 0.0;
    dp_tun_sovDv1 = dp_tun_sovDv3 = dp_tun_sovDv4 = dp_tun_sovDv5 = 0.0;
    dp_tun_dovDv1 = dp_tun_dovDv3 = dp_tun_dovDv4 = dp_tun_dovDv5 = 0.0;
    if(model_.LOVIG!=0){
    dpsi_oxr_ov_sDv1 = (((vg-vs) > vfb_ov) ? (dvgDv1-pow((sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25)))*(dvgDv1)) : (dvgDv1+pow((sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25)))*((-dvgDv1))));
    dpsi_oxr_ov_sDv3 = (((vg-vs) > vfb_ov) ? ((dvgDv3-dvsDv3)-pow((sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25)))*((dvgDv3-dvsDv3))) : ((dvgDv3-dvsDv3)+pow((sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25)))*(((-dvgDv3)+dvsDv3))));
    dpsi_oxr_ov_sDv4 = (((vg-vs) > vfb_ov) ? ((-dvsDv4)-pow((sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25)))*((-dvsDv4))) : ((-dvsDv4)+pow((sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25)))*(((-0)+dvsDv4))));
    dpsi_oxr_ov_sDv5 = (((vg-vs) > vfb_ov) ? ((-dvsDv5)-pow((sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25)))*((-dvsDv5))) : ((-dvsDv5)+pow((sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25)))*(((-0)+dvsDv5))));
    psi_oxr_ov_s = (((vg-vs) > vfb_ov) ? ((vg-vs)-pow((sqrt((((vg-vs)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5),2.0)) : ((vg-vs)+pow((sqrt(((((-vg)+vs)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5),2.0)));

    dpsi_xr_ov_sDv1 = ((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv1)/(xb);
    dpsi_xr_ov_sDv3 = ((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv3)/(xb);
    dpsi_xr_ov_sDv4 = ((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv4)/(xb);
    dpsi_xr_ov_sDv5 = ((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv5)/(xb);
    psi_xr_ov_s = fabs(psi_oxr_ov_s)/(xb);

    ds1_pxDv1 = ds1_pxDv3 = ds1_pxDv4 = ds1_pxDv5 = 0.0;
    if(psi_xr_ov_s<1.0){
    ds1_pxDv1 = 1/(2*sqrt((1.0-psi_xr_ov_s)))*((-dpsi_xr_ov_sDv1));
    ds1_pxDv3 = 1/(2*sqrt((1.0-psi_xr_ov_s)))*((-dpsi_xr_ov_sDv3));
    ds1_pxDv4 = 1/(2*sqrt((1.0-psi_xr_ov_s)))*((-dpsi_xr_ov_sDv4));
    ds1_pxDv5 = 1/(2*sqrt((1.0-psi_xr_ov_s)))*((-dpsi_xr_ov_sDv5));
    s1_px = sqrt((1.0-psi_xr_ov_s));

    dp_tun_sovDv1 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv1)/((1.0+s1_px))+ds1_pxDv1)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tun_sovDv3 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv3)/((1.0+s1_px))+ds1_pxDv3)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tun_sovDv4 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv4)/((1.0+s1_px))+ds1_pxDv4)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tun_sovDv5 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv5)/((1.0+s1_px))+ds1_pxDv5)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    p_tun_sov = exp((-ub)*(1.0/((1.0+s1_px))+s1_px));

    } else {
    dp_tun_sovDv1 = exp((-ub)/(psi_xr_ov_s))*(((-0)-(-ub)/(psi_xr_ov_s)*dpsi_xr_ov_sDv1)/(psi_xr_ov_s));
    dp_tun_sovDv3 = exp((-ub)/(psi_xr_ov_s))*(((-0)-(-ub)/(psi_xr_ov_s)*dpsi_xr_ov_sDv3)/(psi_xr_ov_s));
    dp_tun_sovDv4 = exp((-ub)/(psi_xr_ov_s))*(((-0)-(-ub)/(psi_xr_ov_s)*dpsi_xr_ov_sDv4)/(psi_xr_ov_s));
    dp_tun_sovDv5 = exp((-ub)/(psi_xr_ov_s))*(((-0)-(-ub)/(psi_xr_ov_s)*dpsi_xr_ov_sDv5)/(psi_xr_ov_s));
    p_tun_sov = exp((-ub)/(psi_xr_ov_s));

    }
    dIGSOVDv1 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*fabs(psi_oxr_ov_s)*UT2*dp_tun_sovDv1+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv1)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_sDv1*fabs(psi_oxr_ov_s))*UT2*p_tun_sov)/(TOX2);
    dIGSOVDv3 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*fabs(psi_oxr_ov_s)*UT2*dp_tun_sovDv3+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv3)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_sDv3*fabs(psi_oxr_ov_s))*UT2*p_tun_sov)/(TOX2);
    dIGSOVDv4 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*fabs(psi_oxr_ov_s)*UT2*dp_tun_sovDv4+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv4)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_sDv4*fabs(psi_oxr_ov_s))*UT2*p_tun_sov)/(TOX2);
    dIGSOVDv5 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*fabs(psi_oxr_ov_s)*UT2*dp_tun_sovDv5+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*((psi_oxr_ov_s>=0.0)?1:-1)*(dpsi_oxr_ov_sDv5)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_sDv5*fabs(psi_oxr_ov_s))*UT2*p_tun_sov)/(TOX2);
    IGSOV = model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_s*fabs(psi_oxr_ov_s)*UT2*p_tun_sov/(TOX2);

    dpsi_oxr_ov_dDv1 = (((vg-vd) > vfb_ov) ? (dvgDv1-pow((sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25)))*(dvgDv1)) : (dvgDv1+pow((sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25)))*((-dvgDv1))));
    dpsi_oxr_ov_dDv3 = (((vg-vd) > vfb_ov) ? ((dvgDv3-dvdDv3)-pow((sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25)))*((dvgDv3-dvdDv3))) : ((dvgDv3-dvdDv3)+pow((sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25)))*(((-dvgDv3)+dvdDv3))));
    dpsi_oxr_ov_dDv4 = (((vg-vd) > vfb_ov) ? ((-dvdDv4)-pow((sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25)))*((-dvdDv4))) : ((-dvdDv4)+pow((sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25)))*(((-0)+dvdDv4))));
    dpsi_oxr_ov_dDv5 = (((vg-vd) > vfb_ov) ? ((-dvdDv5)-pow((sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5), 2.0-1)*2.0*1/(2*sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25)))*((-dvdDv5))) : ((-dvdDv5)+pow((sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5), 2.0-1)*2.0*1/(2*sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25)))*(((-0)+dvdDv5))));
    psi_oxr_ov_d = (((vg-vd) > vfb_ov) ? ((vg-vd)-pow((sqrt((((vg-vd)-vfb_ov)+gamma_g2*0.25))-gamma_g*0.5),2.0)) : ((vg-vd)+pow((sqrt(((((-vg)+vd)+vfb_ov)+gamma_ov2*0.25))-gamma_ov*0.5),2.0)));

    dpsi_xr_ov_dDv1 = ((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv1)/(xb);
    dpsi_xr_ov_dDv3 = ((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv3)/(xb);
    dpsi_xr_ov_dDv4 = ((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv4)/(xb);
    dpsi_xr_ov_dDv5 = ((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv5)/(xb);
    psi_xr_ov_d = fabs(psi_oxr_ov_d)/(xb);

    if(psi_xr_ov_d<1.0){
    ds1_pxDv1 = 1/(2*sqrt((1.0-psi_xr_ov_d)))*((-dpsi_xr_ov_dDv1));
    ds1_pxDv3 = 1/(2*sqrt((1.0-psi_xr_ov_d)))*((-dpsi_xr_ov_dDv3));
    ds1_pxDv4 = 1/(2*sqrt((1.0-psi_xr_ov_d)))*((-dpsi_xr_ov_dDv4));
    ds1_pxDv5 = 1/(2*sqrt((1.0-psi_xr_ov_d)))*((-dpsi_xr_ov_dDv5));
    s1_px = sqrt((1.0-psi_xr_ov_d));

    dp_tun_dovDv1 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv1)/((1.0+s1_px))+ds1_pxDv1)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tun_dovDv3 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv3)/((1.0+s1_px))+ds1_pxDv3)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tun_dovDv4 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv4)/((1.0+s1_px))+ds1_pxDv4)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    dp_tun_dovDv5 = exp((-ub)*(1.0/((1.0+s1_px))+s1_px))*(((-ub)*((-1.0/((1.0+s1_px))*ds1_pxDv5)/((1.0+s1_px))+ds1_pxDv5)+(-0)*(1.0/((1.0+s1_px))+s1_px)));
    p_tun_dov = exp((-ub)*(1.0/((1.0+s1_px))+s1_px));

    } else {
    dp_tun_dovDv1 = exp((-ub)/(psi_xr_ov_d))*(((-0)-(-ub)/(psi_xr_ov_d)*dpsi_xr_ov_dDv1)/(psi_xr_ov_d));
    dp_tun_dovDv3 = exp((-ub)/(psi_xr_ov_d))*(((-0)-(-ub)/(psi_xr_ov_d)*dpsi_xr_ov_dDv3)/(psi_xr_ov_d));
    dp_tun_dovDv4 = exp((-ub)/(psi_xr_ov_d))*(((-0)-(-ub)/(psi_xr_ov_d)*dpsi_xr_ov_dDv4)/(psi_xr_ov_d));
    dp_tun_dovDv5 = exp((-ub)/(psi_xr_ov_d))*(((-0)-(-ub)/(psi_xr_ov_d)*dpsi_xr_ov_dDv5)/(psi_xr_ov_d));
    p_tun_dov = exp((-ub)/(psi_xr_ov_d));

    }
    dIGDOVDv1 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*fabs(psi_oxr_ov_d)*UT2*dp_tun_dovDv1+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv1)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_dDv1*fabs(psi_oxr_ov_d))*UT2*p_tun_dov)/(TOX2);
    dIGDOVDv3 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*fabs(psi_oxr_ov_d)*UT2*dp_tun_dovDv3+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv3)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_dDv3*fabs(psi_oxr_ov_d))*UT2*p_tun_dov)/(TOX2);
    dIGDOVDv4 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*fabs(psi_oxr_ov_d)*UT2*dp_tun_dovDv4+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv4)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_dDv4*fabs(psi_oxr_ov_d))*UT2*p_tun_dov)/(TOX2);
    dIGDOVDv5 = (model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*fabs(psi_oxr_ov_d)*UT2*dp_tun_dovDv5+(model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*((psi_oxr_ov_d>=0.0)?1:-1)*(dpsi_oxr_ov_dDv5)+model_.KG*WeffNF*model_.LOVIG*dpsi_oxr_ov_dDv5*fabs(psi_oxr_ov_d))*UT2*p_tun_dov)/(TOX2);
    IGDOV = model_.KG*WeffNF*model_.LOVIG*psi_oxr_ov_d*fabs(psi_oxr_ov_d)*UT2*p_tun_dov/(TOX2);

    } else {
    IGSOV = 0.0;
    IGDOV = 0.0;
    dIGDOVDv1 = dIGDOVDv3 = dIGDOVDv4 = dIGDOVDv5 = 0.0;
    dIGSOVDv1 = dIGSOVDv3 = dIGSOVDv4 = dIGSOVDv5 = 0.0;
    }
    } else {
    IG = 0.0;
    IGS = 0.0;
    IGD = 0.0;
    IGB = 0.0;
    IGSOV = 0.0;
    IGDOV = 0.0;
    dIGDv1 = dIGDv3 = dIGDv4 = dIGDv5 = 0.0;
    dIGBDv1 = dIGBDv3 = dIGBDv4 = dIGBDv5 = 0.0;
    dIGDDv1 = dIGDDv3 = dIGDDv4 = dIGDDv5 = 0.0;
    dIGDOVDv1 = dIGDOVDv3 = dIGDOVDv4 = dIGDOVDv5 = 0.0;
    dIGSDv1 = dIGSDv3 = dIGSDv4 = dIGSDv5 = 0.0;
    dIGSOVDv1 = dIGSOVDv3 = dIGSOVDv4 = dIGSOVDv5 = 0.0;
    }
    dcontributetmpDv1 = ((-SIGN_M)*dIGBDv1+(-0)*IGB);
    dcontributetmpDv3 = ((-SIGN_M)*dIGBDv3+(-0)*IGB);
    dcontributetmpDv4 = ((-SIGN_M)*dIGBDv4+(-0)*IGB);
    dcontributetmpDv5 = ((-SIGN_M)*dIGBDv5+(-0)*IGB);
    contributetmp = (-SIGN_M)*IGB;

    dcontributetmporgDv1 = ((-SIGN_M)*dIGBDv1+(-0)*IGB);
    dcontributetmporgDv3 = ((-SIGN_M)*dIGBDv3+(-0)*IGB);
    dcontributetmporgDv4 = ((-SIGN_M)*dIGBDv4+(-0)*IGB);
    dcontributetmporgDv5 = ((-SIGN_M)*dIGBDv5+(-0)*IGB);
    contributetmporg = (-SIGN_M)*IGB;

    fMat_r3c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    fMat_r3c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    fMat_r3c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    fMat_r3c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    dcontributetmpDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv1+(1-d_gt_s_flag)*dIGDDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    dcontributetmpDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv3+(1-d_gt_s_flag)*dIGDDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    dcontributetmpDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv4+(1-d_gt_s_flag)*dIGDDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    dcontributetmpDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv5+(1-d_gt_s_flag)*dIGDDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    contributetmp = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD);

    dcontributetmporgDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv1+(1-d_gt_s_flag)*dIGDDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    dcontributetmporgDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv3+(1-d_gt_s_flag)*dIGDDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    dcontributetmporgDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv4+(1-d_gt_s_flag)*dIGDDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    dcontributetmporgDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSDv5+(1-d_gt_s_flag)*dIGDDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD));
    contributetmporg = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGS+(1-d_gt_s_flag)*IGD);

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    dcontributetmpDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv1+(1-d_gt_s_flag)*dIGSDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    dcontributetmpDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv3+(1-d_gt_s_flag)*dIGSDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    dcontributetmpDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv4+(1-d_gt_s_flag)*dIGSDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    dcontributetmpDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv5+(1-d_gt_s_flag)*dIGSDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    contributetmp = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS);

    dcontributetmporgDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv1+(1-d_gt_s_flag)*dIGSDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    dcontributetmporgDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv3+(1-d_gt_s_flag)*dIGSDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    dcontributetmporgDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv4+(1-d_gt_s_flag)*dIGSDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    dcontributetmporgDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDDv5+(1-d_gt_s_flag)*dIGSDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS));
    contributetmporg = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGD+(1-d_gt_s_flag)*IGS);

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    dcontributetmpDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv1+(1-d_gt_s_flag)*dIGDOVDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    dcontributetmpDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv3+(1-d_gt_s_flag)*dIGDOVDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    dcontributetmpDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv4+(1-d_gt_s_flag)*dIGDOVDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    dcontributetmpDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv5+(1-d_gt_s_flag)*dIGDOVDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    contributetmp = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV);

    dcontributetmporgDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv1+(1-d_gt_s_flag)*dIGDOVDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    dcontributetmporgDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv3+(1-d_gt_s_flag)*dIGDOVDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    dcontributetmporgDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv4+(1-d_gt_s_flag)*dIGDOVDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    dcontributetmporgDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGSOVDv5+(1-d_gt_s_flag)*dIGDOVDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV));
    contributetmporg = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGSOV+(1-d_gt_s_flag)*IGDOV);

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    dcontributetmpDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv1+(1-d_gt_s_flag)*dIGSOVDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    dcontributetmpDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv3+(1-d_gt_s_flag)*dIGSOVDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    dcontributetmpDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv4+(1-d_gt_s_flag)*dIGSOVDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    dcontributetmpDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv5+(1-d_gt_s_flag)*dIGSOVDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    contributetmp = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV);

    dcontributetmporgDv1 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv1+(1-d_gt_s_flag)*dIGSOVDv1)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    dcontributetmporgDv3 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv3+(1-d_gt_s_flag)*dIGSOVDv3)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    dcontributetmporgDv4 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv4+(1-d_gt_s_flag)*dIGSOVDv4)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    dcontributetmporgDv5 = ((-SIGN_M)*0.5*((d_gt_s_flag+1)*dIGDOVDv5+(1-d_gt_s_flag)*dIGSOVDv5)+(-0)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV));
    contributetmporg = (-SIGN_M)*0.5*((d_gt_s_flag+1)*IGDOV+(1-d_gt_s_flag)*IGSOV);

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    dv_ibDv1 = (-model_.IBN*2.0*dvdssatDv1);
    dv_ibDv3 = ((dvdDv3-dvsDv3)-model_.IBN*2.0*dvdssatDv3);
    dv_ibDv4 = ((dvdDv4-dvsDv4)-model_.IBN*2.0*dvdssatDv4);
    dv_ibDv5 = ((dvdDv5-dvsDv5)-model_.IBN*2.0*dvdssatDv5);
    v_ib = ((vd-vs)-model_.IBN*2.0*vdssat);

    if((v_ib>0.0)&&(model_.IBA>0.0)){
    dtmpDv1 = (-IBB_t*LC/(v_ib*UT)*dv_ibDv1*UT)/(v_ib*UT);
    dtmpDv3 = (-IBB_t*LC/(v_ib*UT)*dv_ibDv3*UT)/(v_ib*UT);
    dtmpDv4 = (-IBB_t*LC/(v_ib*UT)*dv_ibDv4*UT)/(v_ib*UT);
    dtmpDv5 = (-IBB_t*LC/(v_ib*UT)*dv_ibDv5*UT)/(v_ib*UT);
    tmp = IBB_t*LC/(v_ib*UT);

    if(tmp>70.0){
    IDB = 0.0;
    dIDBDv1 = dIDBDv3 = dIDBDv4 = dIDBDv5 = 0.0;
    } else {
    dIDBDv1 = (IDS*v_ib*UT*exp((-tmp))*((-dtmpDv1))+(IDS*dv_ibDv1+dIDSDv1*v_ib)*UT*exp((-tmp)))*model_.IBA/(IBB_t);
    dIDBDv3 = (IDS*v_ib*UT*exp((-tmp))*((-dtmpDv3))+(IDS*dv_ibDv3+dIDSDv3*v_ib)*UT*exp((-tmp)))*model_.IBA/(IBB_t);
    dIDBDv4 = (IDS*v_ib*UT*exp((-tmp))*((-dtmpDv4))+(IDS*dv_ibDv4+dIDSDv4*v_ib)*UT*exp((-tmp)))*model_.IBA/(IBB_t);
    dIDBDv5 = (IDS*v_ib*UT*exp((-tmp))*((-dtmpDv5))+(IDS*dv_ibDv5+dIDSDv5*v_ib)*UT*exp((-tmp)))*model_.IBA/(IBB_t);
    IDB = IDS*v_ib*UT*exp((-tmp))*model_.IBA/(IBB_t);

    }
    } else {
    IDB = 0.0;
    dIDBDv1 = dIDBDv3 = dIDBDv4 = dIDBDv5 = 0.0;
    }
    dcontributetmpDv1 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv1;
    dcontributetmpDv3 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv3;
    dcontributetmpDv4 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv4;
    dcontributetmpDv5 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv5;
    contributetmp = SIGN_M*0.5*(d_gt_s_flag+1)*IDB;

    dcontributetmporgDv1 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv1;
    dcontributetmporgDv3 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv3;
    dcontributetmporgDv4 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv4;
    dcontributetmporgDv5 = SIGN_M*0.5*(d_gt_s_flag+1)*dIDBDv5;
    contributetmporg = SIGN_M*0.5*(d_gt_s_flag+1)*IDB;

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r3c1 += -dcontributetmpDv1;
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r3c4 += -dcontributetmpDv4;
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r3c5 += -dcontributetmpDv5;
    dcontributetmpDv1 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv1;
    dcontributetmpDv3 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv3;
    dcontributetmpDv4 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv4;
    dcontributetmpDv5 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv5;
    contributetmp = SIGN_M*0.5*(1-d_gt_s_flag)*IDB;

    dcontributetmporgDv1 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv1;
    dcontributetmporgDv3 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv3;
    dcontributetmporgDv4 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv4;
    dcontributetmporgDv5 = SIGN_M*0.5*(1-d_gt_s_flag)*dIDBDv5;
    contributetmporg = SIGN_M*0.5*(1-d_gt_s_flag)*IDB;

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r3c1 += -dcontributetmpDv1;
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r3c3 += -dcontributetmpDv3;
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r3c4 += -dcontributetmpDv4;
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r3c5 += -dcontributetmpDv5;
    dtmpDv1 = e_clm*dqs_qdpDv1;
    dtmpDv3 = e_clm*dqs_qdpDv3;
    dtmpDv4 = e_clm*dqs_qdpDv4;
    dtmpDv5 = e_clm*dqs_qdpDv5;
    tmp = (1+e_clm*qs_qdp);

    dgnDv1 = (2/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((dqs2Dv1+(qs*dqdpDv1+dqsDv1*qdp))+dqdp2Dv1)+(e_clm2*i*diDv1+e_clm2*diDv1*i)*0.25)+(0.25*(e_clm*i+1)*dqsqdpDv1+0.25*e_clm*diDv1*qsqdp))+((e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*1/(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))*(((1.0E-24>fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))))?0:((((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))>=0.0)?1:-1)*(((dqsDv1-0.5*e_clm*diDv1)-((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))*(dqdpDv1-0.5*e_clm*diDv1))/(((qdp+0.5)-0.5*e_clm*i)))))+((e_clm*i-1)*0.125*e_clm2*i*dqsqdpp1Dv1+((e_clm*i-1)*0.125*e_clm2*diDv1+e_clm*diDv1*0.125*e_clm2*i)*qsqdpp1)*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))))+(-2/(tmp*tmp*qsqdpp1)*(tmp*tmp*dqsqdpp1Dv1+(tmp*dtmpDv1+dtmpDv1*tmp)*qsqdpp1))/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((qs2+qs*qdp)+qdp2)+e_clm2*i*i*0.25)+0.25*(e_clm*i+1)*qsqdp)+(e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))));
    dgnDv3 = (2/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((dqs2Dv3+(qs*dqdpDv3+dqsDv3*qdp))+dqdp2Dv3)+(e_clm2*i*diDv3+e_clm2*diDv3*i)*0.25)+(0.25*(e_clm*i+1)*dqsqdpDv3+0.25*e_clm*diDv3*qsqdp))+((e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*1/(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))*(((1.0E-24>fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))))?0:((((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))>=0.0)?1:-1)*(((dqsDv3-0.5*e_clm*diDv3)-((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))*(dqdpDv3-0.5*e_clm*diDv3))/(((qdp+0.5)-0.5*e_clm*i)))))+((e_clm*i-1)*0.125*e_clm2*i*dqsqdpp1Dv3+((e_clm*i-1)*0.125*e_clm2*diDv3+e_clm*diDv3*0.125*e_clm2*i)*qsqdpp1)*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))))+(-2/(tmp*tmp*qsqdpp1)*(tmp*tmp*dqsqdpp1Dv3+(tmp*dtmpDv3+dtmpDv3*tmp)*qsqdpp1))/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((qs2+qs*qdp)+qdp2)+e_clm2*i*i*0.25)+0.25*(e_clm*i+1)*qsqdp)+(e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))));
    dgnDv4 = (2/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((dqs2Dv4+(qs*dqdpDv4+dqsDv4*qdp))+dqdp2Dv4)+(e_clm2*i*diDv4+e_clm2*diDv4*i)*0.25)+(0.25*(e_clm*i+1)*dqsqdpDv4+0.25*e_clm*diDv4*qsqdp))+((e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*1/(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))*(((1.0E-24>fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))))?0:((((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))>=0.0)?1:-1)*(((dqsDv4-0.5*e_clm*diDv4)-((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))*(dqdpDv4-0.5*e_clm*diDv4))/(((qdp+0.5)-0.5*e_clm*i)))))+((e_clm*i-1)*0.125*e_clm2*i*dqsqdpp1Dv4+((e_clm*i-1)*0.125*e_clm2*diDv4+e_clm*diDv4*0.125*e_clm2*i)*qsqdpp1)*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))))+(-2/(tmp*tmp*qsqdpp1)*(tmp*tmp*dqsqdpp1Dv4+(tmp*dtmpDv4+dtmpDv4*tmp)*qsqdpp1))/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((qs2+qs*qdp)+qdp2)+e_clm2*i*i*0.25)+0.25*(e_clm*i+1)*qsqdp)+(e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))));
    dgnDv5 = (2/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((dqs2Dv5+(qs*dqdpDv5+dqsDv5*qdp))+dqdp2Dv5)+(e_clm2*i*diDv5+e_clm2*diDv5*i)*0.25)+(0.25*(e_clm*i+1)*dqsqdpDv5+0.25*e_clm*diDv5*qsqdp))+((e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*1/(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))*(((1.0E-24>fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))))?0:((((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))>=0.0)?1:-1)*(((dqsDv5-0.5*e_clm*diDv5)-((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))*(dqdpDv5-0.5*e_clm*diDv5))/(((qdp+0.5)-0.5*e_clm*i)))))+((e_clm*i-1)*0.125*e_clm2*i*dqsqdpp1Dv5+((e_clm*i-1)*0.125*e_clm2*diDv5+e_clm*diDv5*0.125*e_clm2*i)*qsqdpp1)*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))))+(-2/(tmp*tmp*qsqdpp1)*(tmp*tmp*dqsqdpp1Dv5+(tmp*dtmpDv5+dtmpDv5*tmp)*qsqdpp1))/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((qs2+qs*qdp)+qdp2)+e_clm2*i*i*0.25)+0.25*(e_clm*i+1)*qsqdp)+(e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i)))))));
    gn = 2/(tmp*tmp*qsqdpp1)*(((0.33333333333333333333333333333333*((qs2+qs*qdp)+qdp2)+e_clm2*i*i*0.25)+0.25*(e_clm*i+1)*qsqdp)+(e_clm*i-1)*0.125*e_clm2*i*qsqdpp1*log(max(1.0E-24,fabs(((qs+0.5)-0.5*e_clm*i)/(((qdp+0.5)-0.5*e_clm*i))))));

    dthermalDv1 = (4.0*1.3807E-23*thermocrasia*Ispec*dgnDv1+4.0*1.3807E-23*thermocrasia*dIspecDv1*gn)/(UT)*model_.TH_NOI;
    dthermalDv3 = (4.0*1.3807E-23*thermocrasia*Ispec*dgnDv3+4.0*1.3807E-23*thermocrasia*dIspecDv3*gn)/(UT)*model_.TH_NOI;
    dthermalDv4 = (4.0*1.3807E-23*thermocrasia*Ispec*dgnDv4+4.0*1.3807E-23*thermocrasia*dIspecDv4*gn)/(UT)*model_.TH_NOI;
    dthermalDv5 = (4.0*1.3807E-23*thermocrasia*Ispec*dgnDv5+4.0*1.3807E-23*thermocrasia*dIspecDv5*gn)/(UT)*model_.TH_NOI;
    thermal = 4.0*1.3807E-23*thermocrasia*Ispec*gn/(UT)*model_.TH_NOI;

    dgmgDv1 = ((Ispec/(UT)*dqs_qdpDv1+dIspecDv1/(UT)*qs_qdp)-Ispec/(UT)*qs_qdp/(nv)*dnvDv1)/(nv);
    dgmgDv3 = ((Ispec/(UT)*dqs_qdpDv3+dIspecDv3/(UT)*qs_qdp)-Ispec/(UT)*qs_qdp/(nv)*dnvDv3)/(nv);
    dgmgDv4 = ((Ispec/(UT)*dqs_qdpDv4+dIspecDv4/(UT)*qs_qdp)-Ispec/(UT)*qs_qdp/(nv)*dnvDv4)/(nv);
    dgmgDv5 = ((Ispec/(UT)*dqs_qdpDv5+dIspecDv5/(UT)*qs_qdp)-Ispec/(UT)*qs_qdp/(nv)*dnvDv5)/(nv);
    gmg = Ispec/(UT)*qs_qdp/(nv);

    flicker = model_.KF*exp(model_.EF*log(max(1.0E-24, fabs(gmg))))/(WeffNF*Leff*model_.COX*inv_dqmip1);
    domegaspecDv1 = dbetaDv1/(model_.COX)*UT/(Leff*Leff);
    domegaspecDv3 = dbetaDv3/(model_.COX)*UT/(Leff*Leff);
    domegaspecDv4 = dbetaDv4/(model_.COX)*UT/(Leff*Leff);
    domegaspecDv5 = dbetaDv5/(model_.COX)*UT/(Leff*Leff);
    omegaspec = beta/(model_.COX)*UT/(Leff*Leff);

    if(omegaspec!=0.0){
    dOMEGADv1 = (-1.0/(omegaspec)*domegaspecDv1)/(omegaspec);
    dOMEGADv3 = (-1.0/(omegaspec)*domegaspecDv3)/(omegaspec);
    dOMEGADv4 = (-1.0/(omegaspec)*domegaspecDv4)/(omegaspec);
    dOMEGADv5 = (-1.0/(omegaspec)*domegaspecDv5)/(omegaspec);
    OMEGA = 1.0/(omegaspec);

    } else {
    OMEGA = 0.0;
    dOMEGADv1 = dOMEGADv3 = dOMEGADv4 = dOMEGADv5 = 0.0;
    }
    j = 1.0;
    dxfDv1 = dqsDv1;
    dxfDv3 = dqsDv3;
    dxfDv4 = dqsDv4;
    dxfDv5 = dqsDv5;
    xf = (qs+0.5);

    dxrDv1 = dqdpDv1;
    dxrDv3 = dqdpDv3;
    dxrDv4 = dqdpDv4;
    dxrDv5 = dqdpDv5;
    xr = (qdp+0.5);

    dsnididDv1 = ((((((4.0*xf*dxfDv1+4.0*dxfDv1*xf)-3.0*dxfDv1)+(4.0*xf*dxrDv1+4.0*dxfDv1*xr))-3.0*dxrDv1)+(4.0*xr*dxrDv1+4.0*dxrDv1*xr))-((((4.0*xf*xf-3.0*xf)+4.0*xf*xr)-3.0*xr)+4.0*xr*xr)/(6.0*(xf+xr))*6.0*(dxfDv1+dxrDv1))/(6.0*(xf+xr));
    dsnididDv3 = ((((((4.0*xf*dxfDv3+4.0*dxfDv3*xf)-3.0*dxfDv3)+(4.0*xf*dxrDv3+4.0*dxfDv3*xr))-3.0*dxrDv3)+(4.0*xr*dxrDv3+4.0*dxrDv3*xr))-((((4.0*xf*xf-3.0*xf)+4.0*xf*xr)-3.0*xr)+4.0*xr*xr)/(6.0*(xf+xr))*6.0*(dxfDv3+dxrDv3))/(6.0*(xf+xr));
    dsnididDv4 = ((((((4.0*xf*dxfDv4+4.0*dxfDv4*xf)-3.0*dxfDv4)+(4.0*xf*dxrDv4+4.0*dxfDv4*xr))-3.0*dxrDv4)+(4.0*xr*dxrDv4+4.0*dxrDv4*xr))-((((4.0*xf*xf-3.0*xf)+4.0*xf*xr)-3.0*xr)+4.0*xr*xr)/(6.0*(xf+xr))*6.0*(dxfDv4+dxrDv4))/(6.0*(xf+xr));
    dsnididDv5 = ((((((4.0*xf*dxfDv5+4.0*dxfDv5*xf)-3.0*dxfDv5)+(4.0*xf*dxrDv5+4.0*dxfDv5*xr))-3.0*dxrDv5)+(4.0*xr*dxrDv5+4.0*dxrDv5*xr))-((((4.0*xf*xf-3.0*xf)+4.0*xf*xr)-3.0*xr)+4.0*xr*xr)/(6.0*(xf+xr))*6.0*(dxfDv5+dxrDv5))/(6.0*(xf+xr));
    snidid = ((((4.0*xf*xf-3.0*xf)+4.0*xf*xr)-3.0*xr)+4.0*xr*xr)/(6.0*(xf+xr));

    dsnigigDv1 = ((OMEGA*OMEGA*(((((((((16.0*xf*xf*xf*dxfDv1+(16.0*xf*xf*dxfDv1+(16.0*xf*dxfDv1+16.0*dxfDv1*xf)*xf)*xf)+(16.0*xr*xr*xr*dxrDv1+(16.0*xr*xr*dxrDv1+(16.0*xr*dxrDv1+16.0*dxrDv1*xr)*xr)*xr))+(80.0*xf*xr*xr*dxrDv1+(80.0*xf*xr*dxrDv1+(80.0*xf*dxrDv1+80.0*dxfDv1*xr)*xr)*xr))+(80.0*xf*xf*xf*dxrDv1+(80.0*xf*xf*dxfDv1+(80.0*xf*dxfDv1+80.0*dxfDv1*xf)*xf)*xr))+(168.0*xf*xf*xr*dxrDv1+(168.0*xf*xf*dxrDv1+(168.0*xf*dxfDv1+168.0*dxfDv1*xf)*xr)*xr))-(15.0*xf*xf*dxfDv1+(15.0*xf*dxfDv1+15.0*dxfDv1*xf)*xf))-(15.0*xr*xr*dxrDv1+(15.0*xr*dxrDv1+15.0*dxrDv1*xr)*xr))-(75.0*xf*xf*dxrDv1+(75.0*xf*dxfDv1+75.0*dxfDv1*xf)*xr))-(75.0*xf*xr*dxrDv1+(75.0*xf*dxrDv1+75.0*dxfDv1*xr)*xr))+(OMEGA*dOMEGADv1+dOMEGADv1*OMEGA)*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr))-OMEGA*OMEGA*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr)/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr))*(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv1+dxrDv1)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv1+dxrDv1)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(dxfDv1+dxrDv1)+(540.0*nq0*nq0*(xf+xr)*(dxfDv1+dxrDv1)+540.0*nq0*nq0*(dxfDv1+dxrDv1)*(xf+xr))*(xf+xr))*(xf+xr))*(xf+xr)))/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr));
    dsnigigDv3 = ((OMEGA*OMEGA*(((((((((16.0*xf*xf*xf*dxfDv3+(16.0*xf*xf*dxfDv3+(16.0*xf*dxfDv3+16.0*dxfDv3*xf)*xf)*xf)+(16.0*xr*xr*xr*dxrDv3+(16.0*xr*xr*dxrDv3+(16.0*xr*dxrDv3+16.0*dxrDv3*xr)*xr)*xr))+(80.0*xf*xr*xr*dxrDv3+(80.0*xf*xr*dxrDv3+(80.0*xf*dxrDv3+80.0*dxfDv3*xr)*xr)*xr))+(80.0*xf*xf*xf*dxrDv3+(80.0*xf*xf*dxfDv3+(80.0*xf*dxfDv3+80.0*dxfDv3*xf)*xf)*xr))+(168.0*xf*xf*xr*dxrDv3+(168.0*xf*xf*dxrDv3+(168.0*xf*dxfDv3+168.0*dxfDv3*xf)*xr)*xr))-(15.0*xf*xf*dxfDv3+(15.0*xf*dxfDv3+15.0*dxfDv3*xf)*xf))-(15.0*xr*xr*dxrDv3+(15.0*xr*dxrDv3+15.0*dxrDv3*xr)*xr))-(75.0*xf*xf*dxrDv3+(75.0*xf*dxfDv3+75.0*dxfDv3*xf)*xr))-(75.0*xf*xr*dxrDv3+(75.0*xf*dxrDv3+75.0*dxfDv3*xr)*xr))+(OMEGA*dOMEGADv3+dOMEGADv3*OMEGA)*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr))-OMEGA*OMEGA*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr)/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr))*(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv3+dxrDv3)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv3+dxrDv3)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(dxfDv3+dxrDv3)+(540.0*nq0*nq0*(xf+xr)*(dxfDv3+dxrDv3)+540.0*nq0*nq0*(dxfDv3+dxrDv3)*(xf+xr))*(xf+xr))*(xf+xr))*(xf+xr)))/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr));
    dsnigigDv4 = ((OMEGA*OMEGA*(((((((((16.0*xf*xf*xf*dxfDv4+(16.0*xf*xf*dxfDv4+(16.0*xf*dxfDv4+16.0*dxfDv4*xf)*xf)*xf)+(16.0*xr*xr*xr*dxrDv4+(16.0*xr*xr*dxrDv4+(16.0*xr*dxrDv4+16.0*dxrDv4*xr)*xr)*xr))+(80.0*xf*xr*xr*dxrDv4+(80.0*xf*xr*dxrDv4+(80.0*xf*dxrDv4+80.0*dxfDv4*xr)*xr)*xr))+(80.0*xf*xf*xf*dxrDv4+(80.0*xf*xf*dxfDv4+(80.0*xf*dxfDv4+80.0*dxfDv4*xf)*xf)*xr))+(168.0*xf*xf*xr*dxrDv4+(168.0*xf*xf*dxrDv4+(168.0*xf*dxfDv4+168.0*dxfDv4*xf)*xr)*xr))-(15.0*xf*xf*dxfDv4+(15.0*xf*dxfDv4+15.0*dxfDv4*xf)*xf))-(15.0*xr*xr*dxrDv4+(15.0*xr*dxrDv4+15.0*dxrDv4*xr)*xr))-(75.0*xf*xf*dxrDv4+(75.0*xf*dxfDv4+75.0*dxfDv4*xf)*xr))-(75.0*xf*xr*dxrDv4+(75.0*xf*dxrDv4+75.0*dxfDv4*xr)*xr))+(OMEGA*dOMEGADv4+dOMEGADv4*OMEGA)*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr))-OMEGA*OMEGA*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr)/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr))*(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv4+dxrDv4)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv4+dxrDv4)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(dxfDv4+dxrDv4)+(540.0*nq0*nq0*(xf+xr)*(dxfDv4+dxrDv4)+540.0*nq0*nq0*(dxfDv4+dxrDv4)*(xf+xr))*(xf+xr))*(xf+xr))*(xf+xr)))/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr));
    dsnigigDv5 = ((OMEGA*OMEGA*(((((((((16.0*xf*xf*xf*dxfDv5+(16.0*xf*xf*dxfDv5+(16.0*xf*dxfDv5+16.0*dxfDv5*xf)*xf)*xf)+(16.0*xr*xr*xr*dxrDv5+(16.0*xr*xr*dxrDv5+(16.0*xr*dxrDv5+16.0*dxrDv5*xr)*xr)*xr))+(80.0*xf*xr*xr*dxrDv5+(80.0*xf*xr*dxrDv5+(80.0*xf*dxrDv5+80.0*dxfDv5*xr)*xr)*xr))+(80.0*xf*xf*xf*dxrDv5+(80.0*xf*xf*dxfDv5+(80.0*xf*dxfDv5+80.0*dxfDv5*xf)*xf)*xr))+(168.0*xf*xf*xr*dxrDv5+(168.0*xf*xf*dxrDv5+(168.0*xf*dxfDv5+168.0*dxfDv5*xf)*xr)*xr))-(15.0*xf*xf*dxfDv5+(15.0*xf*dxfDv5+15.0*dxfDv5*xf)*xf))-(15.0*xr*xr*dxrDv5+(15.0*xr*dxrDv5+15.0*dxrDv5*xr)*xr))-(75.0*xf*xf*dxrDv5+(75.0*xf*dxfDv5+75.0*dxfDv5*xf)*xr))-(75.0*xf*xr*dxrDv5+(75.0*xf*dxrDv5+75.0*dxfDv5*xr)*xr))+(OMEGA*dOMEGADv5+dOMEGADv5*OMEGA)*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr))-OMEGA*OMEGA*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr)/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr))*(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv5+dxrDv5)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(dxfDv5+dxrDv5)+(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(dxfDv5+dxrDv5)+(540.0*nq0*nq0*(xf+xr)*(dxfDv5+dxrDv5)+540.0*nq0*nq0*(dxfDv5+dxrDv5)*(xf+xr))*(xf+xr))*(xf+xr))*(xf+xr)))/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr));
    snigig = OMEGA*OMEGA*((((((((16.0*xf*xf*xf*xf+16.0*xr*xr*xr*xr)+80.0*xf*xr*xr*xr)+80.0*xf*xf*xf*xr)+168.0*xf*xf*xr*xr)-15.0*xf*xf*xf)-15.0*xr*xr*xr)-75.0*xf*xf*xr)-75.0*xf*xr*xr)/(540.0*nq0*nq0*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr)*(xf+xr));

    dsnibibDv1 = dsnigigDv1*(nq0-1.0)*(nq0-1.0);
    dsnibibDv3 = dsnigigDv3*(nq0-1.0)*(nq0-1.0);
    dsnibibDv4 = dsnigigDv4*(nq0-1.0)*(nq0-1.0);
    dsnibibDv5 = dsnigigDv5*(nq0-1.0)*(nq0-1.0);
    snibib = snigig*(nq0-1.0)*(nq0-1.0);

    dsnigidDv1 = ((j*OMEGA/(18.0*nq0)*((xf-xr)*(((xf*dxfDv1+dxfDv1*xf)+(4.0*xf*dxrDv1+4.0*dxfDv1*xr))+(xr*dxrDv1+dxrDv1*xr))+(dxfDv1-dxrDv1)*((xf*xf+4.0*xf*xr)+xr*xr))+j*dOMEGADv1/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr))-j*OMEGA/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr)/((xf+xr)*(xf+xr)*(xf+xr))*((xf+xr)*(xf+xr)*(dxfDv1+dxrDv1)+((xf+xr)*(dxfDv1+dxrDv1)+(dxfDv1+dxrDv1)*(xf+xr))*(xf+xr)))/((xf+xr)*(xf+xr)*(xf+xr));
    dsnigidDv3 = ((j*OMEGA/(18.0*nq0)*((xf-xr)*(((xf*dxfDv3+dxfDv3*xf)+(4.0*xf*dxrDv3+4.0*dxfDv3*xr))+(xr*dxrDv3+dxrDv3*xr))+(dxfDv3-dxrDv3)*((xf*xf+4.0*xf*xr)+xr*xr))+j*dOMEGADv3/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr))-j*OMEGA/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr)/((xf+xr)*(xf+xr)*(xf+xr))*((xf+xr)*(xf+xr)*(dxfDv3+dxrDv3)+((xf+xr)*(dxfDv3+dxrDv3)+(dxfDv3+dxrDv3)*(xf+xr))*(xf+xr)))/((xf+xr)*(xf+xr)*(xf+xr));
    dsnigidDv4 = ((j*OMEGA/(18.0*nq0)*((xf-xr)*(((xf*dxfDv4+dxfDv4*xf)+(4.0*xf*dxrDv4+4.0*dxfDv4*xr))+(xr*dxrDv4+dxrDv4*xr))+(dxfDv4-dxrDv4)*((xf*xf+4.0*xf*xr)+xr*xr))+j*dOMEGADv4/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr))-j*OMEGA/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr)/((xf+xr)*(xf+xr)*(xf+xr))*((xf+xr)*(xf+xr)*(dxfDv4+dxrDv4)+((xf+xr)*(dxfDv4+dxrDv4)+(dxfDv4+dxrDv4)*(xf+xr))*(xf+xr)))/((xf+xr)*(xf+xr)*(xf+xr));
    dsnigidDv5 = ((j*OMEGA/(18.0*nq0)*((xf-xr)*(((xf*dxfDv5+dxfDv5*xf)+(4.0*xf*dxrDv5+4.0*dxfDv5*xr))+(xr*dxrDv5+dxrDv5*xr))+(dxfDv5-dxrDv5)*((xf*xf+4.0*xf*xr)+xr*xr))+j*dOMEGADv5/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr))-j*OMEGA/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr)/((xf+xr)*(xf+xr)*(xf+xr))*((xf+xr)*(xf+xr)*(dxfDv5+dxrDv5)+((xf+xr)*(dxfDv5+dxrDv5)+(dxfDv5+dxrDv5)*(xf+xr))*(xf+xr)))/((xf+xr)*(xf+xr)*(xf+xr));
    snigid = j*OMEGA/(18.0*nq0)*(xf-xr)*((xf*xf+4.0*xf*xr)+xr*xr)/((xf+xr)*(xf+xr)*(xf+xr));

    if((snidid==0.0)||(snigig==0.0)){
    c_igid = 0.0;
    dc_igidDv1 = dc_igidDv3 = dc_igidDv4 = dc_igidDv5 = 0.0;
    } else {
    dc_igidDv1 = (j*dsnigidDv1-j*snigid/(sqrt(snidid*snigig))*1/(2*sqrt(snidid*snigig))*((snidid*dsnigigDv1+dsnididDv1*snigig)))/(sqrt(snidid*snigig));
    dc_igidDv3 = (j*dsnigidDv3-j*snigid/(sqrt(snidid*snigig))*1/(2*sqrt(snidid*snigig))*((snidid*dsnigigDv3+dsnididDv3*snigig)))/(sqrt(snidid*snigig));
    dc_igidDv4 = (j*dsnigidDv4-j*snigid/(sqrt(snidid*snigig))*1/(2*sqrt(snidid*snigig))*((snidid*dsnigigDv4+dsnididDv4*snigig)))/(sqrt(snidid*snigig));
    dc_igidDv5 = (j*dsnigidDv5-j*snigid/(sqrt(snidid*snigig))*1/(2*sqrt(snidid*snigig))*((snidid*dsnigigDv5+dsnididDv5*snigig)))/(sqrt(snidid*snigig));
    c_igid = j*snigid/(sqrt(snidid*snigig));

    }
    dsnspecDv1 = 4.0*1.3807E-23*thermocrasia*dIspecDv1/(UT);
    dsnspecDv3 = 4.0*1.3807E-23*thermocrasia*dIspecDv3/(UT);
    dsnspecDv4 = 4.0*1.3807E-23*thermocrasia*dIspecDv4/(UT);
    dsnspecDv5 = 4.0*1.3807E-23*thermocrasia*dIspecDv5/(UT);
    snspec = 4.0*1.3807E-23*thermocrasia*Ispec/(UT);

    dsnididDv1 = dsnididDv1*model_.NQS_NOI;
    dsnididDv3 = dsnididDv3*model_.NQS_NOI;
    dsnididDv4 = dsnididDv4*model_.NQS_NOI;
    dsnididDv5 = dsnididDv5*model_.NQS_NOI;
    snidid = snidid*model_.NQS_NOI;

    dsnigigDv1 = dsnigigDv1*model_.NQS_NOI;
    dsnigigDv3 = dsnigigDv3*model_.NQS_NOI;
    dsnigigDv4 = dsnigigDv4*model_.NQS_NOI;
    dsnigigDv5 = dsnigigDv5*model_.NQS_NOI;
    snigig = snigig*model_.NQS_NOI;

    dsnigidDv1 = dsnigidDv1*model_.NQS_NOI;
    dsnigidDv3 = dsnigidDv3*model_.NQS_NOI;
    dsnigidDv4 = dsnigidDv4*model_.NQS_NOI;
    dsnigidDv5 = dsnigidDv5*model_.NQS_NOI;
    snigid = snigid*model_.NQS_NOI;

    dnoise_ds1Dv1 = (snidid*(-(c_igid*dc_igidDv1+dc_igidDv1*c_igid))+dsnididDv1*(1.0-c_igid*c_igid))*model_.NQS_NOI;
    dnoise_ds1Dv3 = (snidid*(-(c_igid*dc_igidDv3+dc_igidDv3*c_igid))+dsnididDv3*(1.0-c_igid*c_igid))*model_.NQS_NOI;
    dnoise_ds1Dv4 = (snidid*(-(c_igid*dc_igidDv4+dc_igidDv4*c_igid))+dsnididDv4*(1.0-c_igid*c_igid))*model_.NQS_NOI;
    dnoise_ds1Dv5 = (snidid*(-(c_igid*dc_igidDv5+dc_igidDv5*c_igid))+dsnididDv5*(1.0-c_igid*c_igid))*model_.NQS_NOI;
    noise_ds1 = snidid*(1.0-c_igid*c_igid)*model_.NQS_NOI;

    dnoise_ds2Dv1 = (c_igid*dsnididDv1+dc_igidDv1*snidid)*model_.NQS_NOI;
    dnoise_ds2Dv3 = (c_igid*dsnididDv3+dc_igidDv3*snidid)*model_.NQS_NOI;
    dnoise_ds2Dv4 = (c_igid*dsnididDv4+dc_igidDv4*snidid)*model_.NQS_NOI;
    dnoise_ds2Dv5 = (c_igid*dsnididDv5+dc_igidDv5*snidid)*model_.NQS_NOI;
    noise_ds2 = c_igid*snidid*model_.NQS_NOI;

    dnoise_gDv1 = dsnigigDv1*model_.NQS_NOI;
    dnoise_gDv3 = dsnigigDv3*model_.NQS_NOI;
    dnoise_gDv4 = dsnigigDv4*model_.NQS_NOI;
    dnoise_gDv5 = dsnigigDv5*model_.NQS_NOI;
    noise_g = snigig*model_.NQS_NOI;

    dnoise_bDv1 = dsnibibDv1*model_.NQS_NOI;
    dnoise_bDv3 = dsnibibDv3*model_.NQS_NOI;
    dnoise_bDv4 = dsnibibDv4*model_.NQS_NOI;
    dnoise_bDv5 = dsnibibDv5*model_.NQS_NOI;
    noise_b = snibib*model_.NQS_NOI;

    if(noise_ds1<=0.0){
    noise_ds1 = 0.0;
    }
    if(noise_ds2<=0.0){
    noise_ds2 = 0.0;
    }
    if(noise_g<=0.0){
    noise_g = 0.0;
    }
    if(noise_b<=0.0){
    noise_b = 0.0;
    dnoise_bDv1 = dnoise_bDv3 = dnoise_bDv4 = dnoise_bDv5 = 0.0;
    dnoise_ds1Dv1 = dnoise_ds1Dv3 = dnoise_ds1Dv4 = dnoise_ds1Dv5 = 0.0;
    dnoise_ds2Dv1 = dnoise_ds2Dv3 = dnoise_ds2Dv4 = dnoise_ds2Dv5 = 0.0;
    dnoise_gDv1 = dnoise_gDv3 = dnoise_gDv4 = dnoise_gDv5 = 0.0;
    }
    if(IG>0.0){
    dsig_shotDv1 = 2.0*1.602E-19*dIGDv1;
    dsig_shotDv3 = 2.0*1.602E-19*dIGDv3;
    dsig_shotDv4 = 2.0*1.602E-19*dIGDv4;
    dsig_shotDv5 = 2.0*1.602E-19*dIGDv5;
    sig_shot = 2.0*1.602E-19*IG;

    dsig_flickerDv1 = (model_.KGFN*IG*dIGDv1+model_.KGFN*dIGDv1*IG);
    dsig_flickerDv3 = (model_.KGFN*IG*dIGDv3+model_.KGFN*dIGDv3*IG);
    dsig_flickerDv4 = (model_.KGFN*IG*dIGDv4+model_.KGFN*dIGDv4*IG);
    dsig_flickerDv5 = (model_.KGFN*IG*dIGDv5+model_.KGFN*dIGDv5*IG);
    sig_flicker = model_.KGFN*IG*IG;

    } else {
    sig_shot = 0.0;
    sig_flicker = 0.0;
    dsig_flickerDv1 = dsig_flickerDv3 = dsig_flickerDv4 = dsig_flickerDv5 = 0.0;
    dsig_shotDv1 = dsig_shotDv3 = dsig_shotDv4 = dsig_shotDv5 = 0.0;
    }
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
    dcontributetmpDv6 = dVnoiDv6;
    contributetmp = Vnoi;

    dcontributetmporgDv6 = dVnoiDv6;
    contributetmporg = Vnoi;

    fMat_r6c6 += dcontributetmpDv6;
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
    dcontributetmpDv1 = Vnoi*dnoise_ds2Dv1;
    dcontributetmpDv3 = Vnoi*dnoise_ds2Dv3;
    dcontributetmpDv4 = Vnoi*dnoise_ds2Dv4;
    dcontributetmpDv5 = Vnoi*dnoise_ds2Dv5;
    dcontributetmpDv6 = dVnoiDv6*noise_ds2;
    contributetmp = Vnoi*noise_ds2;

    dcontributetmporgDv1 = Vnoi*dnoise_ds2Dv1;
    dcontributetmporgDv3 = Vnoi*dnoise_ds2Dv3;
    dcontributetmporgDv4 = Vnoi*dnoise_ds2Dv4;
    dcontributetmporgDv5 = Vnoi*dnoise_ds2Dv5;
    dcontributetmporgDv6 = dVnoiDv6*noise_ds2;
    contributetmporg = Vnoi*noise_ds2;

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r5c1 += -dcontributetmpDv1;
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r5c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r5c4 += -dcontributetmpDv4;
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r5c5 += -dcontributetmpDv5;
    fMat_r4c6 += dcontributetmpDv6;
    fMat_r5c6 += -dcontributetmpDv6;
    dDdtExp18Dv1 = Vnoi*dnoise_gDv1;
    dDdtExp18Dv3 = Vnoi*dnoise_gDv3;
    dDdtExp18Dv4 = Vnoi*dnoise_gDv4;
    dDdtExp18Dv5 = Vnoi*dnoise_gDv5;
    dDdtExp18Dv6 = dVnoiDv6*noise_g;
    DdtExp18 = Vnoi*noise_g;

    dDdtAns18Dv1 = 0;
    dDdtAns18Dv3 = 0;
    dDdtAns18Dv4 = 0;
    dDdtAns18Dv5 = 0;
    dDdtAns18Dv6 = 0;
    DdtAns18 = DdtExp18;

    dDdtAns18Dv1 = dDdtExp18Dv1 * _der0;
    dDdtAns18Dv3 = dDdtExp18Dv3 * _der0;
    dDdtAns18Dv4 = dDdtExp18Dv4 * _der0;
    dDdtAns18Dv5 = dDdtExp18Dv5 * _der0;
    dDdtAns18Dv6 = dDdtExp18Dv6 * _der0;
    dcontributetmpDv1 = 0.0;
    dcontributetmpDv3 = 0.0;
    dcontributetmpDv4 = 0.0;
    dcontributetmpDv5 = 0.0;
    dcontributetmpDv6 = 0.0;
    contributetmp = DdtAns18;

    dcontributetmporgDv1 = dDdtAns18Dv1;
    dcontributetmporgDv3 = dDdtAns18Dv3;
    dcontributetmporgDv4 = dDdtAns18Dv4;
    dcontributetmporgDv5 = dDdtAns18Dv5;
    dcontributetmporgDv6 = dDdtAns18Dv6;
    contributetmporg = DdtAns18;

    fMat_r1c1 += dcontributetmpDv1;
    qMat_r1c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r1c3 += dcontributetmpDv3;
    qMat_r1c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r1c4 += dcontributetmpDv4;
    qMat_r1c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r1c5 += dcontributetmpDv5;
    qMat_r1c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    fMat_r1c6 += dcontributetmpDv6;
    qMat_r1c6 += (dcontributetmporgDv6 -  dcontributetmpDv6);
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
        contributetmp = 0;
    //Derivate 0
        contributetmporg = 0;
    //Derivate 0
    dcontributetmpDv1 = SIGN_M*d_gt_s_flag*dIDSDv1;
    dcontributetmpDv3 = SIGN_M*d_gt_s_flag*dIDSDv3;
    dcontributetmpDv4 = SIGN_M*d_gt_s_flag*dIDSDv4;
    dcontributetmpDv5 = SIGN_M*d_gt_s_flag*dIDSDv5;
    contributetmp = SIGN_M*d_gt_s_flag*IDS;

    dcontributetmporgDv1 = SIGN_M*d_gt_s_flag*dIDSDv1;
    dcontributetmporgDv3 = SIGN_M*d_gt_s_flag*dIDSDv3;
    dcontributetmporgDv4 = SIGN_M*d_gt_s_flag*dIDSDv4;
    dcontributetmporgDv5 = SIGN_M*d_gt_s_flag*dIDSDv5;
    contributetmporg = SIGN_M*d_gt_s_flag*IDS;

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r5c1 += -dcontributetmpDv1;
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r5c3 += -dcontributetmpDv3;
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r5c4 += -dcontributetmpDv4;
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r5c5 += -dcontributetmpDv5;
    dDdtExp19Dv1 = dQBDv1;
    dDdtExp19Dv3 = dQBDv3;
    dDdtExp19Dv4 = dQBDv4;
    dDdtExp19Dv5 = dQBDv5;
    DdtExp19 = QB;

    dDdtAns19Dv1 = 0;
    dDdtAns19Dv3 = 0;
    dDdtAns19Dv4 = 0;
    dDdtAns19Dv5 = 0;
    DdtAns19 = DdtExp19;

    dDdtAns19Dv1 = dDdtExp19Dv1 * _der0;
    dDdtAns19Dv3 = dDdtExp19Dv3 * _der0;
    dDdtAns19Dv4 = dDdtExp19Dv4 * _der0;
    dDdtAns19Dv5 = dDdtExp19Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.0*QON;
    dcontributetmpDv3 = SIGN_M*0.0*QON;
    dcontributetmpDv4 = SIGN_M*0.0*QON;
    dcontributetmpDv5 = SIGN_M*0.0*QON;
    contributetmp = SIGN_M*DdtAns19*QON;

    dcontributetmporgDv1 = SIGN_M*dDdtAns19Dv1*QON;
    dcontributetmporgDv3 = SIGN_M*dDdtAns19Dv3*QON;
    dcontributetmporgDv4 = SIGN_M*dDdtAns19Dv4*QON;
    dcontributetmporgDv5 = SIGN_M*dDdtAns19Dv5*QON;
    contributetmporg = SIGN_M*DdtAns19*QON;

    fMat_r3c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r3c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r3c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r3c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r3c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r3c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r3c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r3c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dDdtExp20Dv1 = dQDDv1;
    dDdtExp20Dv3 = dQDDv3;
    dDdtExp20Dv4 = dQDDv4;
    dDdtExp20Dv5 = dQDDv5;
    DdtExp20 = QD;

    dDdtAns20Dv1 = 0;
    dDdtAns20Dv3 = 0;
    dDdtAns20Dv4 = 0;
    dDdtAns20Dv5 = 0;
    DdtAns20 = DdtExp20;

    dDdtAns20Dv1 = dDdtExp20Dv1 * _der0;
    dDdtAns20Dv3 = dDdtExp20Dv3 * _der0;
    dDdtAns20Dv4 = dDdtExp20Dv4 * _der0;
    dDdtAns20Dv5 = dDdtExp20Dv5 * _der0;
    dDdtExp21Dv1 = dQSDv1;
    dDdtExp21Dv3 = dQSDv3;
    dDdtExp21Dv4 = dQSDv4;
    dDdtExp21Dv5 = dQSDv5;
    DdtExp21 = QS;

    dDdtAns21Dv1 = 0;
    dDdtAns21Dv3 = 0;
    dDdtAns21Dv4 = 0;
    dDdtAns21Dv5 = 0;
    DdtAns21 = DdtExp21;

    dDdtAns21Dv1 = dDdtExp21Dv1 * _der0;
    dDdtAns21Dv3 = dDdtExp21Dv3 * _der0;
    dDdtAns21Dv4 = dDdtExp21Dv4 * _der0;
    dDdtAns21Dv5 = dDdtExp21Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns20+(1-d_gt_s_flag)*DdtAns21)*QON;

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns20Dv1+(1-d_gt_s_flag)*dDdtAns21Dv1)*QON;
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns20Dv3+(1-d_gt_s_flag)*dDdtAns21Dv3)*QON;
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns20Dv4+(1-d_gt_s_flag)*dDdtAns21Dv4)*QON;
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns20Dv5+(1-d_gt_s_flag)*dDdtAns21Dv5)*QON;
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns20+(1-d_gt_s_flag)*DdtAns21)*QON;

    fMat_r4c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r4c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r4c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r4c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r4c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r4c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r4c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r4c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    dDdtExp22Dv1 = dQSDv1;
    dDdtExp22Dv3 = dQSDv3;
    dDdtExp22Dv4 = dQSDv4;
    dDdtExp22Dv5 = dQSDv5;
    DdtExp22 = QS;

    dDdtAns22Dv1 = 0;
    dDdtAns22Dv3 = 0;
    dDdtAns22Dv4 = 0;
    dDdtAns22Dv5 = 0;
    DdtAns22 = DdtExp22;

    dDdtAns22Dv1 = dDdtExp22Dv1 * _der0;
    dDdtAns22Dv3 = dDdtExp22Dv3 * _der0;
    dDdtAns22Dv4 = dDdtExp22Dv4 * _der0;
    dDdtAns22Dv5 = dDdtExp22Dv5 * _der0;
    dDdtExp23Dv1 = dQDDv1;
    dDdtExp23Dv3 = dQDDv3;
    dDdtExp23Dv4 = dQDDv4;
    dDdtExp23Dv5 = dQDDv5;
    DdtExp23 = QD;

    dDdtAns23Dv1 = 0;
    dDdtAns23Dv3 = 0;
    dDdtAns23Dv4 = 0;
    dDdtAns23Dv5 = 0;
    DdtAns23 = DdtExp23;

    dDdtAns23Dv1 = dDdtExp23Dv1 * _der0;
    dDdtAns23Dv3 = dDdtExp23Dv3 * _der0;
    dDdtAns23Dv4 = dDdtExp23Dv4 * _der0;
    dDdtAns23Dv5 = dDdtExp23Dv5 * _der0;
    dcontributetmpDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    dcontributetmpDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*0.0+(1-d_gt_s_flag)*0.0)*QON;
    contributetmp = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns22+(1-d_gt_s_flag)*DdtAns23)*QON;

    dcontributetmporgDv1 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns22Dv1+(1-d_gt_s_flag)*dDdtAns23Dv1)*QON;
    dcontributetmporgDv3 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns22Dv3+(1-d_gt_s_flag)*dDdtAns23Dv3)*QON;
    dcontributetmporgDv4 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns22Dv4+(1-d_gt_s_flag)*dDdtAns23Dv4)*QON;
    dcontributetmporgDv5 = SIGN_M*0.5*((d_gt_s_flag+1)*dDdtAns22Dv5+(1-d_gt_s_flag)*dDdtAns23Dv5)*QON;
    contributetmporg = SIGN_M*0.5*((d_gt_s_flag+1)*DdtAns22+(1-d_gt_s_flag)*DdtAns23)*QON;

    fMat_r5c1 += dcontributetmpDv1;
    fMat_r1c1 += -dcontributetmpDv1;
    qMat_r5c1 += (dcontributetmporgDv1 -  dcontributetmpDv1);
    qMat_r1c1 -= (dcontributetmporgDv1 -  dcontributetmpDv1);
    fMat_r5c3 += dcontributetmpDv3;
    fMat_r1c3 += -dcontributetmpDv3;
    qMat_r5c3 += (dcontributetmporgDv3 -  dcontributetmpDv3);
    qMat_r1c3 -= (dcontributetmporgDv3 -  dcontributetmpDv3);
    fMat_r5c4 += dcontributetmpDv4;
    fMat_r1c4 += -dcontributetmpDv4;
    qMat_r5c4 += (dcontributetmporgDv4 -  dcontributetmpDv4);
    qMat_r1c4 -= (dcontributetmporgDv4 -  dcontributetmpDv4);
    fMat_r5c5 += dcontributetmpDv5;
    fMat_r1c5 += -dcontributetmpDv5;
    qMat_r5c5 += (dcontributetmporgDv5 -  dcontributetmpDv5);
    qMat_r1c5 -= (dcontributetmporgDv5 -  dcontributetmpDv5);
    if(model_.INFO_LEVEL>0.0){
    if(model_.INFO_LEVEL==1.0){
    }
    } else {
    }
    file = 0;
    file_info = 0;
}

bool Instance::updatePrimaryState ()
{
    bool bsuccess = true;
    bsuccess = updateIntermediateVars ();
    return bsuccess;
}

bool Instance::loadDAEQVector ()
{
    double * qVec = extData.daeQVectorRawPtr;
    qVec[d] += qRHS[0];
    qVec[g] += qRHS[1];
    qVec[s] += qRHS[2];
    qVec[b] += qRHS[3];
    qVec[di] += qRHS[4];
    qVec[si] += qRHS[5];
    qVec[noi] += qRHS[6];
    return true;
}

bool Instance::loadDAEFVector ()
{
    double * fVec = extData.daeFVectorRawPtr;
    fVec[d] += fRHS[0];
    fVec[g] += fRHS[1];
    fVec[s] += fRHS[2];
    fVec[b] += fRHS[3];
    fVec[di] += fRHS[4];
    fVec[si] += fRHS[5];
    fVec[noi] += fRHS[6];
    return true;
}

bool Instance::loadDAEdQdx ()
{
    Linear::Matrix & dQdx = *(extData.dQdxMatrixPtr);
    dQdx[d][AMatOffset_r0c0] += qMat_r0c0;
    dQdx[d][AMatOffset_r0c4] += qMat_r0c4;
    dQdx[g][AMatOffset_r1c1] += qMat_r1c1;
    dQdx[g][AMatOffset_r1c3] += qMat_r1c3;
    dQdx[g][AMatOffset_r1c4] += qMat_r1c4;
    dQdx[g][AMatOffset_r1c5] += qMat_r1c5;
    dQdx[g][AMatOffset_r1c6] += qMat_r1c6;
    dQdx[s][AMatOffset_r2c2] += qMat_r2c2;
    dQdx[s][AMatOffset_r2c5] += qMat_r2c5;
    dQdx[b][AMatOffset_r3c1] += qMat_r3c1;
    dQdx[b][AMatOffset_r3c3] += qMat_r3c3;
    dQdx[b][AMatOffset_r3c4] += qMat_r3c4;
    dQdx[b][AMatOffset_r3c5] += qMat_r3c5;
    dQdx[di][AMatOffset_r4c0] += qMat_r4c0;
    dQdx[di][AMatOffset_r4c1] += qMat_r4c1;
    dQdx[di][AMatOffset_r4c3] += qMat_r4c3;
    dQdx[di][AMatOffset_r4c4] += qMat_r4c4;
    dQdx[di][AMatOffset_r4c5] += qMat_r4c5;
    dQdx[di][AMatOffset_r4c6] += qMat_r4c6;
    dQdx[si][AMatOffset_r5c1] += qMat_r5c1;
    dQdx[si][AMatOffset_r5c2] += qMat_r5c2;
    dQdx[si][AMatOffset_r5c3] += qMat_r5c3;
    dQdx[si][AMatOffset_r5c4] += qMat_r5c4;
    dQdx[si][AMatOffset_r5c5] += qMat_r5c5;
    dQdx[si][AMatOffset_r5c6] += qMat_r5c6;
    dQdx[noi][AMatOffset_r6c6] += qMat_r6c6;
    return true;
}

bool Instance::loadDAEdFdx ()
{
    Linear::Matrix & dFdx = *(extData.dFdxMatrixPtr);
    dFdx[d][AMatOffset_r0c0] += fMat_r0c0;
    dFdx[d][AMatOffset_r0c4] += fMat_r0c4;
    dFdx[g][AMatOffset_r1c1] += fMat_r1c1;
    dFdx[g][AMatOffset_r1c3] += fMat_r1c3;
    dFdx[g][AMatOffset_r1c4] += fMat_r1c4;
    dFdx[g][AMatOffset_r1c5] += fMat_r1c5;
    dFdx[g][AMatOffset_r1c6] += fMat_r1c6;
    dFdx[s][AMatOffset_r2c2] += fMat_r2c2;
    dFdx[s][AMatOffset_r2c5] += fMat_r2c5;
    dFdx[b][AMatOffset_r3c1] += fMat_r3c1;
    dFdx[b][AMatOffset_r3c3] += fMat_r3c3;
    dFdx[b][AMatOffset_r3c4] += fMat_r3c4;
    dFdx[b][AMatOffset_r3c5] += fMat_r3c5;
    dFdx[di][AMatOffset_r4c0] += fMat_r4c0;
    dFdx[di][AMatOffset_r4c1] += fMat_r4c1;
    dFdx[di][AMatOffset_r4c3] += fMat_r4c3;
    dFdx[di][AMatOffset_r4c4] += fMat_r4c4;
    dFdx[di][AMatOffset_r4c5] += fMat_r4c5;
    dFdx[di][AMatOffset_r4c6] += fMat_r4c6;
    dFdx[si][AMatOffset_r5c1] += fMat_r5c1;
    dFdx[si][AMatOffset_r5c2] += fMat_r5c2;
    dFdx[si][AMatOffset_r5c3] += fMat_r5c3;
    dFdx[si][AMatOffset_r5c4] += fMat_r5c4;
    dFdx[si][AMatOffset_r5c5] += fMat_r5c5;
    dFdx[si][AMatOffset_r5c6] += fMat_r5c6;
    dFdx[noi][AMatOffset_r6c6] += fMat_r6c6;
    return true;
}

bool Model::processParams ()
{
}

bool Model::processInstanceParams()
{
    std::vector<Instance*>::iterator iter;
    std::vector<Instance*>::iterator first = instanceContainer.begin();
    std::vector<Instance*>::iterator last  = instanceContainer.end();

    for (iter=first; iter!=last; ++iter)
    {
        (*iter)->processParams();
    }

    return true;
}

Model::Model(
const Configuration & configuration,
  const ModelBlock &    MB,
  const FactoryBlock &  factory_block)
  : DeviceModel(MB, configuration.getModelParameters(), factory_block),
  SIGN(0.), 
  TG(0.), 
  TNOM(0.), 
  SCALE(0.), 
  QOFF(0.), 
  XL(0.), 
  XW(0.), 
  NQS_NOI(0.), 
  TH_NOI(0.), 
  INFO_LEVEL(0.), 
  AVTO(0.), 
  AGAMMA(0.), 
  AKP(0.), 
  COX(0.), 
  XJ(0.), 
  VTO(0.), 
  PHIF(0.), 
  GAMMA(0.), 
  GAMMAG(0.), 
  N0(0.), 
  VBI(0.), 
  AQMA(0.), 
  AQMI(0.), 
  ETAQM(0.), 
  KP(0.), 
  E0(0.), 
  E1(0.), 
  ETA(0.), 
  ZC(0.), 
  THC(0.), 
  LA(0.), 
  LB(0.), 
  KA(0.), 
  KB(0.), 
  WKP1(0.), 
  WKP2(0.), 
  WKP3(0.), 
  DL(0.), 
  DLC(0.), 
  DW(0.), 
  DWC(0.), 
  LDW(0.), 
  WDL(0.), 
  LL(0.), 
  LLN(0.), 
  AVT(0.), 
  LVT(0.), 
  WVT(0.), 
  AGAM(0.), 
  LGAM(0.), 
  WGAM(0.), 
  NFVTA(0.), 
  NFVTB(0.), 
  UCRIT(0.), 
  LAMBDA(0.), 
  DELTA(0.), 
  ACLM(0.), 
  LR(0.), 
  QLR(0.), 
  NLR(0.), 
  FLR(0.), 
  LETA0(0.), 
  LETA(0.), 
  LETA2(0.), 
  WETA(0.), 
  NCS(0.), 
  ETAD(0.), 
  SIGMAD(0.), 
  WR(0.), 
  QWR(0.), 
  NWR(0.), 
  FPROUT(0.), 
  PDITS(0.), 
  PDITSL(0.), 
  PDITSD(0.), 
  DDITS(0.), 
  IBA(0.), 
  IBB(0.), 
  IBN(0.), 
  XB(0.), 
  EB(0.), 
  KG(0.), 
  LOVIG(0.), 
  AGIDL(0.), 
  BGIDL(0.), 
  CGIDL(0.), 
  EGIDL(0.), 
  KF(0.), 
  AF(0.), 
  EF(0.), 
  KGFN(0.), 
  LQWR(0.), 
  LNWR(0.), 
  LWR(0.), 
  LDPHIEDGE(0.), 
  WQLR(0.), 
  WNLR(0.), 
  WLR(0.), 
  WUCRIT(0.), 
  WLAMBDA(0.), 
  WETAD(0.), 
  WE0(0.), 
  WE1(0.), 
  WRLX(0.), 
  WUCEX(0.), 
  WDPHIEDGE(0.), 
  WLDPHIEDGE(0.), 
  WLDGAMMAEDGE(0.), 
  WEDGE(0.), 
  DGAMMAEDGE(0.), 
  DPHIEDGE(0.), 
  SAREF(0.), 
  SBREF(0.), 
  WLOD(0.), 
  KKP(0.), 
  LKKP(0.), 
  WKKP(0.), 
  PKKP(0.), 
  TKKP(0.), 
  LLODKKP(0.), 
  WLODKKP(0.), 
  KVTO(0.), 
  LKVTO(0.), 
  WKVTO(0.), 
  PKVTO(0.), 
  LLODKVTO(0.), 
  WLODKVTO(0.), 
  KGAMMA(0.), 
  LODKGAMMA(0.), 
  KETAD(0.), 
  LODKETAD(0.), 
  KUCRIT(0.), 
  TETA(0.), 
  TLAMBDA(0.), 
  TCV(0.), 
  BEX(0.), 
  UCEX(0.), 
  TE0EX(0.), 
  TE1EX(0.), 
  IBBT(0.), 
  TCVL(0.), 
  TCVW(0.), 
  TCVWL(0.), 
  GAMMAOV(0.), 
  GAMMAGOV(0.), 
  VFBOV(0.), 
  LOV(0.), 
  VOV(0.), 
  CGSO(0.), 
  CGDO(0.), 
  CGBO(0.), 
  KJF(0.), 
  CJF(0.), 
  VFR(0.), 
  DFR(0.), 
  HDIF(0.), 
  RSH(0.), 
  LDIF(0.), 
  RS(0.), 
  RD(0.), 
  RLX(0.), 
  RSX(0.), 
  RDX(0.), 
  TR(0.), 
  TR2(0.), 
  GMIN(0.), 
  NJS(0.), 
  XJBVS(0.), 
  BVS(0.), 
  JSS(0.), 
  JSSWS(0.), 
  JSSWGS(0.), 
  JTSS(0.), 
  JTSSWS(0.), 
  JTSSWGS(0.), 
  NJTSS(0.), 
  NJTSSWS(0.), 
  NJTSSWGS(0.), 
  VTSS(0.), 
  VTSSWS(0.), 
  VTSSWGS(0.), 
  CJS(0.), 
  CJSWS(0.), 
  CJSWGS(0.), 
  PBS(0.), 
  PBSWS(0.), 
  PBSWGS(0.), 
  MJS(0.), 
  MJSWS(0.), 
  MJSWGS(0.), 
  XTIS(0.), 
  XTSS(0.), 
  XTSSWS(0.), 
  XTSSWGS(0.), 
  TNJTSS(0.), 
  TNJTSSWS(0.), 
  TNJTSSWGS(0.), 
  TCJ(0.), 
  TCJSW(0.), 
  TCJSWG(0.), 
  TPB(0.), 
  TPBSW(0.), 
  TPBSWG(0.), 
  NJD(0.), 
  XJBVD(0.), 
  BVD(0.), 
  JSD(0.), 
  JSSWD(0.), 
  JSSWGD(0.), 
  JTSD(0.), 
  JTSSWD(0.), 
  JTSSWGD(0.), 
  NJTSD(0.), 
  NJTSSWD(0.), 
  NJTSSWGD(0.), 
  VTSD(0.), 
  VTSSWD(0.), 
  VTSSWGD(0.), 
  CJD(0.), 
  CJSWD(0.), 
  CJSWGD(0.), 
  PBD(0.), 
  PBSWD(0.), 
  PBSWGD(0.), 
  MJD(0.), 
  MJSWD(0.), 
  MJSWGD(0.), 
  XTID(0.), 
  XTSD(0.), 
  XTSSWD(0.), 
  XTSSWGD(0.), 
  TNJTSD(0.), 
  TNJTSSWD(0.), 
  TNJTSSWGD(0.), 
  RGSH(0.), 
  GC(0.), 
  KRGL1(0.), 
  RDSBSH(0.), 
  RBWSH(0.), 
  RBN(0.), 
  RSBWSH(0.), 
  RSBN(0.), 
  RDBWSH(0.), 
  RDBN(0.), 
  RINGTYPE(0.), 
  my_dummy(false)
{
    setDefaultParams();
    setModParams(MB.params);
    updateDependentParameters();
    processParams();
}

Model::~Model ()
{
    std::vector<Instance*>::iterator iter;
    std::vector<Instance*>::iterator first = instanceContainer.begin();
    std::vector<Instance*>::iterator last  = instanceContainer.end();
    
    for (iter=first; iter!=last; ++iter)
    {
      delete (*iter);
    }
}

std::ostream &Model::printOutInstances (std::ostream &os) const
{
  std::vector<Instance*>::const_iterator iter;
  std::vector<Instance*>::const_iterator first = instanceContainer.begin();
  std::vector<Instance*>::const_iterator last  = instanceContainer.end();

  int i;
  os << std::endl;
  os << "    name     modelName  Parameters" << std::endl;

  for (i=0, iter=first; iter!=last; ++iter,++i)
 {
    os << "  " << i << ": " << (*iter)->getName() << "	";
    os << getName();
    os << std::endl;
  }

  os << std::endl;

  return os;
}

void Model::forEachInstance(DeviceInstanceOp &op) const /* override */ 
{
  for (std::vector<Instance *>::const_iterator it = instanceContainer.begin(); it != instanceContainer.end(); ++it)
    op(*it);
}

bool Model::clearTemperatureData ()
{
}
bool Master::updateState (double * solVec, double * staVec, double * stoVec)
{
    bool bsuccess = true;
    for (InstanceVector::const_iterator it = getInstanceBegin(); it != getInstanceEnd(); ++it)
    {
      Instance & mi = *(*it);
    
      bool btmp = mi.updateIntermediateVars ();
      bsuccess = bsuccess && btmp;
    }

    return bsuccess;
}

bool Master::loadDAEVectors (double * solVec, double * fVec, double *qVec,  double * bVec, double * leadF, double * leadQ, double * junctionV)
{
    for (InstanceVector::const_iterator it = getInstanceBegin(); it != getInstanceEnd(); ++it)
    {
      Instance & mi = *(*it);
  
      fVec[mi.d] += mi.fRHS[0];
      fVec[mi.g] += mi.fRHS[1];
      fVec[mi.s] += mi.fRHS[2];
      fVec[mi.b] += mi.fRHS[3];
      fVec[mi.di] += mi.fRHS[4];
      fVec[mi.si] += mi.fRHS[5];
      fVec[mi.noi] += mi.fRHS[6];
      qVec[mi.d] += mi.qRHS[0];
      qVec[mi.g] += mi.qRHS[1];
      qVec[mi.s] += mi.qRHS[2];
      qVec[mi.b] += mi.qRHS[3];
      qVec[mi.di] += mi.qRHS[4];
      qVec[mi.si] += mi.qRHS[5];
      qVec[mi.noi] += mi.qRHS[6];
    }
    return true;
}

#ifndef Xyce_NONPOINTER_MATRIX_LOAD
bool Master::loadDAEMatrices (Linear::Matrix & dFdx, Linear::Matrix & dQdx)
{
    for (InstanceVector::const_iterator it = getInstanceBegin(); it != getInstanceEnd(); ++it)
    {
      Instance & mi = *(*it);
      *mi.f_matPosition_r0c0 += mi.fMat_r0c0;
      *mi.f_matPosition_r0c4 += mi.fMat_r0c4;
      *mi.f_matPosition_r1c1 += mi.fMat_r1c1;
      *mi.f_matPosition_r1c3 += mi.fMat_r1c3;
      *mi.f_matPosition_r1c4 += mi.fMat_r1c4;
      *mi.f_matPosition_r1c5 += mi.fMat_r1c5;
      *mi.f_matPosition_r1c6 += mi.fMat_r1c6;
      *mi.f_matPosition_r2c2 += mi.fMat_r2c2;
      *mi.f_matPosition_r2c5 += mi.fMat_r2c5;
      *mi.f_matPosition_r3c1 += mi.fMat_r3c1;
      *mi.f_matPosition_r3c3 += mi.fMat_r3c3;
      *mi.f_matPosition_r3c4 += mi.fMat_r3c4;
      *mi.f_matPosition_r3c5 += mi.fMat_r3c5;
      *mi.f_matPosition_r4c0 += mi.fMat_r4c0;
      *mi.f_matPosition_r4c1 += mi.fMat_r4c1;
      *mi.f_matPosition_r4c3 += mi.fMat_r4c3;
      *mi.f_matPosition_r4c4 += mi.fMat_r4c4;
      *mi.f_matPosition_r4c5 += mi.fMat_r4c5;
      *mi.f_matPosition_r4c6 += mi.fMat_r4c6;
      *mi.f_matPosition_r5c1 += mi.fMat_r5c1;
      *mi.f_matPosition_r5c2 += mi.fMat_r5c2;
      *mi.f_matPosition_r5c3 += mi.fMat_r5c3;
      *mi.f_matPosition_r5c4 += mi.fMat_r5c4;
      *mi.f_matPosition_r5c5 += mi.fMat_r5c5;
      *mi.f_matPosition_r5c6 += mi.fMat_r5c6;
      *mi.f_matPosition_r6c6 += mi.fMat_r6c6;
      *mi.q_matPosition_r0c0 += mi.qMat_r0c0;
      *mi.q_matPosition_r0c4 += mi.qMat_r0c4;
      *mi.q_matPosition_r1c1 += mi.qMat_r1c1;
      *mi.q_matPosition_r1c3 += mi.qMat_r1c3;
      *mi.q_matPosition_r1c4 += mi.qMat_r1c4;
      *mi.q_matPosition_r1c5 += mi.qMat_r1c5;
      *mi.q_matPosition_r1c6 += mi.qMat_r1c6;
      *mi.q_matPosition_r2c2 += mi.qMat_r2c2;
      *mi.q_matPosition_r2c5 += mi.qMat_r2c5;
      *mi.q_matPosition_r3c1 += mi.qMat_r3c1;
      *mi.q_matPosition_r3c3 += mi.qMat_r3c3;
      *mi.q_matPosition_r3c4 += mi.qMat_r3c4;
      *mi.q_matPosition_r3c5 += mi.qMat_r3c5;
      *mi.q_matPosition_r4c0 += mi.qMat_r4c0;
      *mi.q_matPosition_r4c1 += mi.qMat_r4c1;
      *mi.q_matPosition_r4c3 += mi.qMat_r4c3;
      *mi.q_matPosition_r4c4 += mi.qMat_r4c4;
      *mi.q_matPosition_r4c5 += mi.qMat_r4c5;
      *mi.q_matPosition_r4c6 += mi.qMat_r4c6;
      *mi.q_matPosition_r5c1 += mi.qMat_r5c1;
      *mi.q_matPosition_r5c2 += mi.qMat_r5c2;
      *mi.q_matPosition_r5c3 += mi.qMat_r5c3;
      *mi.q_matPosition_r5c4 += mi.qMat_r5c4;
      *mi.q_matPosition_r5c5 += mi.qMat_r5c5;
      *mi.q_matPosition_r5c6 += mi.qMat_r5c6;
      *mi.q_matPosition_r6c6 += mi.qMat_r6c6;
    }
    return true;
}

#else
bool Master::loadDAEMatrices (Linear::Matrix & dFdx, Linear::Matrix & dQdx)
{
    int sizeInstances = instanceContainer_.size();
    for (int i=0; i<sizeInstances; ++i)
    {
      Instance & mi = *(instanceContainer_.at(i));

      dFdx[mi.d][AMatOffset_r0c0] += mi.fMat_r0c0;
      dFdx[mi.d][AMatOffset_r0c4] += mi.fMat_r0c4;
      dFdx[mi.g][AMatOffset_r1c1] += mi.fMat_r1c1;
      dFdx[mi.g][AMatOffset_r1c3] += mi.fMat_r1c3;
      dFdx[mi.g][AMatOffset_r1c4] += mi.fMat_r1c4;
      dFdx[mi.g][AMatOffset_r1c5] += mi.fMat_r1c5;
      dFdx[mi.g][AMatOffset_r1c6] += mi.fMat_r1c6;
      dFdx[mi.s][AMatOffset_r2c2] += mi.fMat_r2c2;
      dFdx[mi.s][AMatOffset_r2c5] += mi.fMat_r2c5;
      dFdx[mi.b][AMatOffset_r3c1] += mi.fMat_r3c1;
      dFdx[mi.b][AMatOffset_r3c3] += mi.fMat_r3c3;
      dFdx[mi.b][AMatOffset_r3c4] += mi.fMat_r3c4;
      dFdx[mi.b][AMatOffset_r3c5] += mi.fMat_r3c5;
      dFdx[mi.di][AMatOffset_r4c0] += mi.fMat_r4c0;
      dFdx[mi.di][AMatOffset_r4c1] += mi.fMat_r4c1;
      dFdx[mi.di][AMatOffset_r4c3] += mi.fMat_r4c3;
      dFdx[mi.di][AMatOffset_r4c4] += mi.fMat_r4c4;
      dFdx[mi.di][AMatOffset_r4c5] += mi.fMat_r4c5;
      dFdx[mi.di][AMatOffset_r4c6] += mi.fMat_r4c6;
      dFdx[mi.si][AMatOffset_r5c1] += mi.fMat_r5c1;
      dFdx[mi.si][AMatOffset_r5c2] += mi.fMat_r5c2;
      dFdx[mi.si][AMatOffset_r5c3] += mi.fMat_r5c3;
      dFdx[mi.si][AMatOffset_r5c4] += mi.fMat_r5c4;
      dFdx[mi.si][AMatOffset_r5c5] += mi.fMat_r5c5;
      dFdx[mi.si][AMatOffset_r5c6] += mi.fMat_r5c6;
      dFdx[mi.noi][AMatOffset_r6c6] += mi.fMat_r6c6;
      dQdx[mi.d][AMatOffset_r0c0] += mi.qMat_r0c0;
      dQdx[mi.d][AMatOffset_r0c4] += mi.qMat_r0c4;
      dQdx[mi.g][AMatOffset_r1c1] += mi.qMat_r1c1;
      dQdx[mi.g][AMatOffset_r1c3] += mi.qMat_r1c3;
      dQdx[mi.g][AMatOffset_r1c4] += mi.qMat_r1c4;
      dQdx[mi.g][AMatOffset_r1c5] += mi.qMat_r1c5;
      dQdx[mi.g][AMatOffset_r1c6] += mi.qMat_r1c6;
      dQdx[mi.s][AMatOffset_r2c2] += mi.qMat_r2c2;
      dQdx[mi.s][AMatOffset_r2c5] += mi.qMat_r2c5;
      dQdx[mi.b][AMatOffset_r3c1] += mi.qMat_r3c1;
      dQdx[mi.b][AMatOffset_r3c3] += mi.qMat_r3c3;
      dQdx[mi.b][AMatOffset_r3c4] += mi.qMat_r3c4;
      dQdx[mi.b][AMatOffset_r3c5] += mi.qMat_r3c5;
      dQdx[mi.di][AMatOffset_r4c0] += mi.qMat_r4c0;
      dQdx[mi.di][AMatOffset_r4c1] += mi.qMat_r4c1;
      dQdx[mi.di][AMatOffset_r4c3] += mi.qMat_r4c3;
      dQdx[mi.di][AMatOffset_r4c4] += mi.qMat_r4c4;
      dQdx[mi.di][AMatOffset_r4c5] += mi.qMat_r4c5;
      dQdx[mi.di][AMatOffset_r4c6] += mi.qMat_r4c6;
      dQdx[mi.si][AMatOffset_r5c1] += mi.qMat_r5c1;
      dQdx[mi.si][AMatOffset_r5c2] += mi.qMat_r5c2;
      dQdx[mi.si][AMatOffset_r5c3] += mi.qMat_r5c3;
      dQdx[mi.si][AMatOffset_r5c4] += mi.qMat_r5c4;
      dQdx[mi.si][AMatOffset_r5c5] += mi.qMat_r5c5;
      dQdx[mi.si][AMatOffset_r5c6] += mi.qMat_r5c6;
      dQdx[mi.noi][AMatOffset_r6c6] += mi.qMat_r6c6;
    }
    return true;
}

#endif

Device *Traits::factory(const Configuration &configuration, const FactoryBlock &factory_block)
{
    return new Master(configuration, factory_block, factory_block.solverState_, factory_block.deviceOptions_);
}

void registerDevice()
{
    Config<Traits>::addConfiguration()
      .registerDevice("ekv3", 1)
      .registerModelType("ekv3", 1);
}

}
}
}

extern "C"{
void registerDevice()
{
    Xyce::Device::ADMS_Device::registerDevice();
}
}

