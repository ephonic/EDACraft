"""Explicit measured limit checks, with no inferred model equivalence."""
from collections.abc import Mapping
import numpy as np
from .base import BaseValidationTest, ValidationResult, measured_field, _get
from .cross_validation import _runners, _tolerance
from .convergence import _sequence, _fresh, _record
from .reference import ReferenceComparisonTest


def _scalar(result,name):
    value=measured_field(result,name)
    if value.shape != ():
        raise ValueError(f'{name} must be a real scalar')
    return float(value)


def _switch(result,name,expected):
    value=_get(result,name)
    if not isinstance(value,(bool,np.bool_)) or bool(value)!=expected:
        raise ValueError(f'{name} must explicitly be {expected}')


class LimitingCaseTest(BaseValidationTest):
    """Compare declared limit/reference runners on fresh simulators.

    No implicit setter guesses, analytic-current proxies, threshold extraction,
    or cross-temperature comparisons. runners map limit/reference to runner(sim),
    or runner(sim, thickness_m) for thin_oxide. Runners must return actual fields
    and condition metadata (see validation README). Metadata is caller supplied;
    a pass verifies numerical agreement under a declared protocol only.
    """
    _fields={'no_ferroelectric':('phi','n','p','P'), 'no_traps':('phi','n','p'),
             'high_temperature':('n','p'), 'thin_oxide':('tunneling_current_A',),
             'nls_to_lk':('P',), 'preisach_to_lk':('P',)}

    def __init__(self,limit_type,tolerance=.05,limit_params=None,*,runners=None,
                 fields=None,atol=None,reference_source=None):
        super().__init__(f'Limiting Case Test ({limit_type})')
        if limit_type not in self._fields:
            raise ValueError(f'unknown limit_type: {limit_type}')
        self.limit_type=limit_type
        self.tolerance=_tolerance(tolerance)
        self.runners=_runners(runners,('limit','reference'))
        if limit_params is None: limit_params={}
        if not isinstance(limit_params,Mapping):
            raise ValueError('limit_params must be a mapping')
        allowed={'high_temperature':{'temperature_K'},'thin_oxide':{'thicknesses_m','bias_V'}}.get(limit_type,set())
        if set(limit_params)-allowed:
            raise ValueError('unknown or unused limit parameters')
        self.limit_params=dict(limit_params)
        self.temperature_K=_tolerance(limit_params.get('temperature_K',1000.))
        self.thicknesses_m=_sequence(limit_params.get('thicknesses_m'),[5e-9,2e-9,1e-9,.5e-9],
                                    3,positive=True,direction='down')
        bias=np.asarray(limit_params.get('bias_V',1.))
        if (bias.shape!=() or bias.dtype.kind not in 'iuf' or not np.isfinite(bias)
                or not np.isfinite(float(bias)) or float(bias)==0.):
            raise ValueError('bias_V must be a finite nonzero real scalar')
        self.bias_V=float(bias)
        fields=self._fields[limit_type] if fields is None else fields
        if not isinstance(fields,(list,tuple)) or not set(self._fields[limit_type]).issubset(fields):
            raise ValueError('fields must include all required limit measurements')
        if reference_source is not None and (not isinstance(reference_source,str) or not reference_source.strip()):
            raise ValueError('reference_source must be explicit and nonempty')
        if runners is not None and reference_source is None:
            raise ValueError('explicit runners require reference_source')
        self.reference_source=reference_source
        # Reuse the canonical reference-budget validation and avoid a second
        # convention for zero crossings, extreme scales or field extraction.
        config=ReferenceComparisonTest(lambda:None,lambda:None,fields=fields,rtol=self.tolerance,
            atol=atol,reference_source=reference_source or 'unavailable explicit reference')
        self.fields=config.fields
        self.atol=config.atol

    def _condition(self,result,side,thickness):
        enabled=side=='limit'
        if self.limit_type in ('no_ferroelectric','no_traps'):
            if any(np.any(measured_field(result,field)<0.) for field in ('n','p')):
                raise ValueError('carrier density must be nonnegative')
        if self.limit_type=='no_ferroelectric':
            _switch(result,'ferroelectric_enabled',enabled)
            if _scalar(result,'ferroelectric_active_nodes')!=0. or np.any(measured_field(result,'P')!=0.):
                raise ValueError('the zero-active-volume FE limit requires zero active nodes and zero P')
        elif self.limit_type=='no_traps':
            _switch(result,'traps_enabled',enabled)
            bulk=measured_field(result,'oxide_trap_charge_C_m3')
            if (_scalar(result,'trap_density_m2_eV')!=0. or np.any(bulk!=0.) or
                    bulk.shape!=measured_field(result,'phi').shape):
                raise ValueError('the zero-interface-trap limit requires zero interface density and zero bulk trap charge on both sides')
        elif self.limit_type=='high_temperature':
            _switch(result,'quantum_enabled',enabled)
            if _scalar(result,'temperature_K')!=self.temperature_K:
                raise ValueError('quantum and classical measurements must share the requested temperature_K')
            n,p=measured_field(result,'n'),measured_field(result,'p')
            if np.any(n<0.) or np.any(p<0.) or not (np.any(n>0.) or np.any(p>0.)):
                raise ValueError('quantum carrier comparison requires nonnegative, nonzero carrier evidence')
        elif self.limit_type=='thin_oxide':
            if (_scalar(result,'oxide_thickness_m')!=thickness or
                    _scalar(result,'bias_V')!=self.bias_V):
                raise ValueError('both thin-oxide measurements must match thickness and bias')
            _scalar(result,'tunneling_current_A')

    def run(self,device_builder):
        details=dict(limit_type=self.limit_type,reference_source=self.reference_source,
            physical_validated=False,constitutive_equivalence_validated=False,
            reference_authenticity_validated=False,numerical_agreement_validated=False,
            global_temporal_error_validated=False,comparisons=[])
        if self.limit_type in ('nls_to_lk','preisach_to_lk'):
            details['unsupported']=True
            return ValidationResult(self.name,False,'No specified constitutive limit or parameter mapping '
                'establishes NLS/Preisach equivalence to LK.',details)
        if self.runners is None:
            details['unsupported']=True
            return ValidationResult(self.name,False,'Explicit limit/reference runners and measured '
                'condition metadata are required; default runs cannot establish this limit.',details)
        try:
            instances,records=[],[]
            coordinates=self.thicknesses_m if self.limit_type=='thin_oxide' else [None]
            reference_currents=[]
            for thickness in coordinates:
                pair=[]
                for side in ('limit','reference'):
                    sim=_fresh(device_builder,instances)
                    result=(self.runners[side](sim,thickness) if thickness is not None else self.runners[side](sim))
                    _record(result,records)
                    self._condition(result,side,thickness)
                    pair.append(result)
                actual,reference=pair
                comparison=ReferenceComparisonTest(lambda:actual,lambda:reference,fields=self.fields,
                    rtol=self.tolerance,atol=self.atol,reference_source=self.reference_source).run()
                details['comparisons'].append(dict(thickness_m=thickness,passed=comparison.passed,
                    message=comparison.message,field_error_ratios=comparison.details['field_error_ratios']))
                if self.limit_type=='thin_oxide':
                    reference_currents.append(_scalar(reference,'tunneling_current_A'))
            if self.limit_type=='thin_oxide' and (not any(i!=0. for i in reference_currents)
                    or all(i==reference_currents[0] for i in reference_currents)):
                details['inconclusive']=True
                raise ValueError('constant or zero reference current cannot establish thickness dependence')
            passed=all(comparison['passed'] for comparison in details['comparisons'])
            details['numerical_agreement_validated']=passed
            return ValidationResult(self.name,passed,'Declared limit/reference numerical comparison: '
                                    f'{len(coordinates)} condition(s)',details)
        except Exception as error:
            return ValidationResult(self.name,False,f'unavailable/failed limit evidence: {error}',details)
