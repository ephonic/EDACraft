"""Execute generated C++ against an independent PMI harness, then vendor cases."""
import subprocess
import numpy as np
import pytest
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.material.sentaurus_relaxation import sentaurus_relaxation_pmi_source

PARAMETERS=dict(electron_tau0_s=3e-13,hole_tau0_s=2.5e-13,
    electron_law=Law(300.,1e21,.65,1.,.22),hole_law=Law(300.,1e21,-.4,0.,-.18))


@pytest.mark.parametrize('name,value', [('electron_tau0_s',0.),('hole_tau0_s',-1.),
    ('electron_tau0_s',True),('hole_tau0_s',np.inf),('electron_tau0_s',[1e-13]),
    ('hole_tau0_s',1j),('electron_tau0_s',np.longdouble('1e4000')),
    ('electron_law',None),('hole_law',{}),('electron_law',lambda:1)])
def test_invalid_export_parameters_rejected(name,value):
    with pytest.raises(ValueError):sentaurus_relaxation_pmi_source(**dict(PARAMETERS,**{name:value}))


@pytest.fixture(scope='module')
def executable(tmp_path_factory):
    out=tmp_path_factory.mktemp('pmi_harness')
    (out/'PMIModels.h').write_text('''#pragma once
#include <cstring>
#include <stdexcept>
struct PMI_Environment { double lattice, n_cm3, p_cm3; };
class PMI_EnergyRelaxationTime {
  PMI_Environment env;
public:
  explicit PMI_EnergyRelaxationTime(const PMI_Environment& x):env(x){}
  virtual ~PMI_EnergyRelaxationTime(){}
  virtual void Compute_tau(double,double&)=0;
  virtual void Compute_dtaudct(double,double&)=0;
  double ReadScalar(const char* s)const {
    if(!std::strcmp(s,"LatticeTemperature"))return env.lattice;
    if(!std::strcmp(s,"eDensity"))return env.n_cm3;
    if(!std::strcmp(s,"hDensity"))return env.p_cm3;
    throw std::runtime_error("wrong scalar field");
  }
};
''')
    (out/'model.C').write_text(sentaurus_relaxation_pmi_source(**PARAMETERS))
    (out/'main.C').write_text('''#include "model.C"
#include <cstdlib>
#include <iostream>
#include <memory>
#include <iomanip>
int main(int argc,char** argv){
  if(argc!=6)return 9;
  PMI_Environment env{std::atof(argv[2]),std::atof(argv[3]),std::atof(argv[4])};
  try {
    std::unique_ptr<PMI_EnergyRelaxationTime> model(argv[1][0]=='e' ?
        new_PMI_e_EnergyRelaxationTime(env):new_PMI_h_EnergyRelaxationTime(env));
    double value,derivative;model->Compute_tau(std::atof(argv[5]),value);
    model->Compute_dtaudct(std::atof(argv[5]),derivative);
    std::cout<<std::setprecision(17)<<value<<" "<<derivative;
  } catch(const std::domain_error&){return 2;}
}
''')
    binary=out/'probe';subprocess.run(['g++','-std=c++11','-O2',str(out/'main.C'),'-o',str(binary)],check=True)
    return binary


@pytest.mark.parametrize('carrier,Tl,n,p,Tc', [('e',400.,1e16,2e7,650.),
    ('h',350.,8e6,3.1622776601683795e15,270.),('e',300.,1e15,1e3,300.),
    ('h',800.,1e30,2e18,1200.)])
def test_compiled_local_values_and_ct_derivatives_match_direct_powers(executable,carrier,Tl,n,p,Tc):
    result=subprocess.run([str(executable),carrier,*map(str,(Tl,n,p,Tc))],check=True,capture_output=True,text=True)
    tau,derivative=map(float,result.stdout.split())
    if carrier=='e':expected=3e-13*(Tl/300)**.65*(Tc/300)*(n*1e6/1e21)**.22;d=expected/Tc
    else:expected=2.5e-13*(Tl/300)**(-.4)*(p*1e6/1e21)**(-.18);d=0.
    assert abs(tau/expected-1)<2e-14
    assert derivative==0. if d==0. else abs(derivative/d-1)<2e-14


@pytest.mark.parametrize('carrier,Tl,n,p,Tc', [('e',0.,1e15,1e15,400.),
    ('e',300.,0.,1e15,400.),('h',300.,1e15,-1.,400.),('e',300.,1e15,1e15,0.),
    ('h',float('nan'),1e15,1e15,400.),('e',300.,float('inf'),1e15,400.)])
def test_compiled_invalid_runtime_fields_fail_without_clipping(executable,carrier,Tl,n,p,Tc):
    result=subprocess.run([str(executable),carrier,*map(str,(Tl,n,p,Tc))],capture_output=True)
    assert result.returncode==2
