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
#include "test3.h"

using std::max;
namespace Xyce {
namespace Device {
namespace ADMS_Device {
void Traits::loadInstanceParameters(ParametricData<ADMS_Device::Instance> &p)
{
}
void Traits::loadModelParameters(ParametricData<ADMS_Device::Model> &p)
{

p.addPar("INFO_LEVEL", 1.00000000e+00, &ADMS_Device::Model::INFO_LEVEL)
.setUnit(U_NONE)
.setCategory(CAT_PROCESS)
.setDescription("Desciption not available");
p.addPar("TT", 2.00000000e+00, &ADMS_Device::Model::TT)
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
p(0),
n(0),
{
numIntVars = 0;
numExtVars = 2;
numStateVars = 0;
setNumStoreVars(0);
setNumBranchDataVars(0);
numBranchDataVarsIfAllocated = 0;
if(jacStamp.empty()) {
jacStamp.resize(2);
jacStamp[0].resize(0);
jacStamp[1].resize(0);
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
p =  extLIDVec[0];
n =  extLIDVec[1];
}

void Instance::loadNodeSymbols(Util::SymbolTable &symbol_table) const
{
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
}

void Instance::setupPointers () 
{
#ifndef Xyce_NONPOINTER_MATRIX_LOAD
Linear::Matrix & dFdx = *(extData.dFdxMatrixPtr);
Linear::Matrix & dQdx = *(extData.dQdxMatrixPtr);
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
    double myadms_t1, myadms_t2;
    double Ids;
    double gds;
    double Vp = (extData.nextSolVectorRawPtr)[p];
    fRHS[0] = 0.;
    fRHS[1] = 0.;
    qRHS[0] = 0.;
    qRHS[1] = 0.;
    Ids = model_.TT*Vp;
    gds = Ids;
    ddx(Vp)
}

bool Instance::updateIntermediateVars_Jac()
{
    double _der0 = 1.0;
    double Vp =  (extData.nextSolVectorRawPtr)[p];
    double dVpDv0 = 1.;
    double Ids;
    double gds;
    double dIdsDv0, dgdsDv0;
    double contributetmp;
    double dcontributetmpDv0, dcontributetmpDv1;

    double contributetmporg;
    double dcontributetmporgDv0, dcontributetmporgDv1;


    dIdsDv0 = model_.TT*dVpDv0;
    Ids = model_.TT*Vp;

    dgdsDv0 = dIdsDv0;
    gds = Ids;

    ddx(Vp)
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
    qVec[p] += qRHS[0];
    qVec[n] += qRHS[1];
    return true;
}

bool Instance::loadDAEFVector ()
{
    double * fVec = extData.daeFVectorRawPtr;
    fVec[p] += fRHS[0];
    fVec[n] += fRHS[1];
    return true;
}

bool Instance::loadDAEdQdx ()
{
    Linear::Matrix & dQdx = *(extData.dQdxMatrixPtr);
    return true;
}

bool Instance::loadDAEdFdx ()
{
    Linear::Matrix & dFdx = *(extData.dFdxMatrixPtr);
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
  INFO_LEVEL(0.), 
  TT(0.), 
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
  
      fVec[mi.p] += mi.fRHS[0];
      fVec[mi.n] += mi.fRHS[1];
      qVec[mi.p] += mi.qRHS[0];
      qVec[mi.n] += mi.qRHS[1];
    }
    return true;
}

#ifndef Xyce_NONPOINTER_MATRIX_LOAD
bool Master::loadDAEMatrices (Linear::Matrix & dFdx, Linear::Matrix & dQdx)
{
    for (InstanceVector::const_iterator it = getInstanceBegin(); it != getInstanceEnd(); ++it)
    {
      Instance & mi = *(*it);
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
      .registerDevice("test3", 1)
      .registerModelType("test3", 1);
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

