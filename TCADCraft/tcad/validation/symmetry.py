"""Measured parity checks under explicit spatial or paired-drive protocols."""
from collections.abc import Mapping
import numpy as np
from .base import BaseValidationTest, ValidationResult, measured_field, _get, _MISSING
from .cross_validation import _runners
from .convergence import _callable, _fresh, _record
from .reference import ReferenceComparisonTest


class SymmetryTest(BaseValidationTest):
    """Audit caller-declared field relations, without certifying their physics.

    relations maps field -> (partner_field, +1 or -1). It must be an involution
    (e.g. phi->-phi, n->p, p->n), not an arbitrary transformation callback.
    protocol describes the conditions making that hypothesis meaningful.

    Geometric checks reflect one measured result along an explicit axis; an
    optional involutive node permutation replaces index reversal on that axis.
    The caller owns coordinates, mesh symmetry and vector-component parities.

    Paired checks need distinct positive/negative runners on fresh simulators.
    Voltage reversal requires phi->-phi and opposite nonzero bias_V controls;
    carrier exchange is optional and never inferred. FE requires P->-P,
    opposite voltage_V waveforms and identical times_s starting at zero.
    Hysteresis histories must be prepared independently, not reversed in time.
    """
    def __init__(self, symmetry_type='voltage_reversal', tolerance=1e-3, *,
                 relations=None, protocol=None, axis=None, permutation=None,
                 runner=None, runners=None, atol=None):
        super().__init__(f'Symmetry Test ({symmetry_type})')
        if symmetry_type not in ('geometric','voltage_reversal','ferroelectric'):
            raise ValueError(f'unknown symmetry_type: {symmetry_type}')
        self.symmetry_type = symmetry_type
        if protocol is not None and (not isinstance(protocol,str) or not protocol.strip()):
            raise ValueError('protocol must describe the declared symmetry conditions')
        self.protocol = protocol
        self.relations = self._relations(relations)
        if axis is not None and (not isinstance(axis,(int,np.integer)) or isinstance(axis,(bool,np.bool_))):
            raise ValueError('axis must be an integer or None')
        self.axis = None if axis is None else int(axis)
        self.permutation = None
        if permutation is not None:
            indexes = np.asarray(permutation)
            if (indexes.ndim != 1 or len(indexes)<2 or indexes.dtype.kind not in 'iu' or
                    any(isinstance(v,(bool,np.bool_)) for v in permutation) or
                    not np.array_equal(np.sort(indexes),np.arange(len(indexes)))):
                raise ValueError('permutation must be an exact integer bijection')
            indexes = indexes.astype(np.intp)
            if (not np.array_equal(indexes[indexes],np.arange(len(indexes))) or
                    np.array_equal(indexes,np.arange(len(indexes)))):
                raise ValueError('reflection permutation must be nontrivial and self-inverse')
            self.permutation = indexes.copy()
        self.runner = _callable(runner,'runner')
        self.runners = _runners(runners,('positive','negative'))
        if symmetry_type == 'geometric':
            if runners is not None:raise ValueError('geometric symmetry uses runner, not paired runners')
            if permutation is not None and axis is None:raise ValueError('permutation requires its axis')
        elif runner is not None or axis is not None or permutation is not None:
            raise ValueError('paired-drive checks use runners on explicitly aligned fields')
        mandatory = {'voltage_reversal':'phi','ferroelectric':'P'}.get(symmetry_type)
        if self.relations is not None and mandatory and self.relations.get(mandatory)!=(mandatory,-1):
            raise ValueError(f'{symmetry_type} requires {mandatory} -> -{mandatory}')
        if relations is None and atol is not None:
            raise ValueError('absolute budgets require explicit relations')
        fields=tuple(self.relations) if self.relations is not None else (mandatory or 'phi',)
        config=ReferenceComparisonTest(lambda:None,lambda:None,fields=fields,rtol=tolerance,
            atol=atol,reference_source='caller-declared symmetry protocol')
        self.tolerance,self.atol=config.rtol,config.atol

    @staticmethod
    def _relations(relations):
        if relations is None:return None
        if not isinstance(relations,Mapping) or not relations:
            raise ValueError('relations must be a nonempty field mapping')
        result={}
        reserved={'time_s','times_s','bias_V','voltage_V','valid','converged'}
        for field,relation in relations.items():
            if (not isinstance(field,str) or not field.strip() or field in reserved or
                    not isinstance(relation,(tuple,list)) or len(relation)!=2):
                raise ValueError('each relation must map a measured field to (partner_field, parity)')
            other,sign=relation
            if (not isinstance(other,str) or not isinstance(sign,(int,np.integer)) or
                    isinstance(sign,(bool,np.bool_)) or sign not in (-1,1)):
                raise ValueError('field parity must be integer +1 or -1')
            result[field]=(other,int(sign))
        for field,(other,sign) in result.items():
            if result.get(other)!=(field,sign):
                raise ValueError('field relations must be self-inverse with matching parities')
        return result

    def _reflect(self,values,result):
        if not -values.ndim <= self.axis < values.ndim:
            raise ValueError('axis is outside the measured field layout')
        axis=self.axis % values.ndim
        if _get(result,'times_s') is not _MISSING and axis==0:
            raise ValueError('geometric reflection cannot reverse the trajectory time axis')
        if values.shape[axis]<2:
            raise ValueError('reflection needs at least two points along its axis')
        if self.permutation is not None:
            if len(self.permutation)!=values.shape[axis]:
                raise ValueError('permutation length must match the measured axis exactly')
            return np.take(values,self.permutation,axis=axis)
        return np.flip(values,axis=axis)

    def _drive(self,positive,negative):
        field='voltage_V' if self.symmetry_type=='ferroelectric' else 'bias_V'
        a,b=measured_field(positive,field),measured_field(negative,field)
        if a.shape!=b.shape or not np.array_equal(a,-b) or not np.any(a!=0.):
            raise ValueError(f'{field} controls must be matching, nonzero, exact sign reversals')
        if self.symmetry_type=='ferroelectric':
            if a.ndim!=1 or len(a)<2:
                raise ValueError('FE voltage_V must be a sampled waveform with at least two points')
            for result in (positive,negative):
                times=measured_field(result,'times_s')
                polarization=measured_field(result,'P')
                if (times.shape!=a.shape or times[0]!=0. or not np.all(times[1:]>times[:-1]) or
                        not polarization.ndim or polarization.shape[0]!=len(times)):
                    raise ValueError('FE P, voltage and strictly increasing times_s must match, starting at t=0')

    def run(self,device_builder):
        details=dict(protocol=self.protocol,relations=self.relations,axis=self.axis,
            permutation=None if self.permutation is None else self.permutation.tolist(),
            numerical_symmetry_validated=False,physical_validated=False,
            symmetry_hypothesis_validated=False,reference_authenticity_validated=False,
            constitutive_equivalence_validated=False,global_temporal_error_validated=False)
        missing=self.protocol is None or self.relations is None
        missing |= self.axis is None if self.symmetry_type=='geometric' else self.runners is None
        if missing:
            details['unsupported']=True
            return ValidationResult(self.name,False,'Declare protocol, field relations and a spatial axis or paired runners',details)
        try:
            if self.symmetry_type=='geometric':
                sim=device_builder()
                positive=self.runner(sim) if self.runner else sim.run()
                negative=positive
            else:
                instances,records=[],[]
                sims=[_fresh(device_builder,instances) for _ in range(2)]
                positive,negative=[self.runners[side](sim) for side,sim in zip(('positive','negative'),sims)]
                for result in (positive,negative):_record(result,records)
                self._drive(positive,negative)
            actual,reference={},{}
            for field,(other,sign) in self.relations.items():
                actual[field]=measured_field(positive,field)
                paired=measured_field(negative,other)
                if field in ('n','p') and (np.any(actual[field]<0.) or np.any(paired<0.)):
                    raise ValueError('carrier symmetry requires nonnegative densities')
                if self.symmetry_type=='geometric':paired=self._reflect(paired,negative)
                reference[field]=sign*paired
            for clock in ('time_s','times_s'):
                for original,converted in ((positive,actual),(negative,reference)):
                    if _get(original,clock) is not _MISSING:converted[clock]=measured_field(original,clock)
            if self.symmetry_type!='geometric':
                key='P' if self.symmetry_type=='ferroelectric' else 'phi'
                if not np.any(actual[key]!=0.) or not np.any(reference[key]!=0.):
                    details['inconclusive']=True
                    raise ValueError(f'all-zero {key} cannot establish a nontrivial paired response')
            comparison=ReferenceComparisonTest(lambda:actual,lambda:reference,fields=tuple(self.relations),
                rtol=self.tolerance,atol=self.atol,reference_source=self.protocol).run()
            details.update(field_error_ratios=comparison.details['field_error_ratios'],
                rtol=self.tolerance,atol=dict(self.atol),numerical_symmetry_validated=comparison.passed)
            return ValidationResult(self.name,comparison.passed,comparison.message,details)
        except Exception as error:
            return ValidationResult(self.name,False,f'unavailable/failed symmetry evidence: {error}',details)
