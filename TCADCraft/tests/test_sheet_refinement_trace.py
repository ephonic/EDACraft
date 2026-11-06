"""Interval comparisons preserve a drive-edge charge impulse under dt refinement."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'benchmarks'))
from sheet_refinement_trace import compare_traces,load_record


def trace(count):
    dt=1./count;states=[dict(time_s=0.)];time=0.
    for i in range(1,count+1):
        time+=dt;q=1. if i else 0.
        displacement=1./dt if i==1 else 0.
        states.append(dict(time_s=time,dt_s=dt,phase=1,sheet_charge_C=0.,trap_charge_C=0.,
            untrapped_sheet_charge_C=0.,contact_charge_C=dict(source=-q,drain=0.),
            sheet_contact_charge_C=dict(source=0.,drain=0.),
            dielectric_contact_charge_C=dict(source=-q,drain=0.),gates=dict(top_gate=q,bottom_gate=0.),
            dielectric_energy_J=.5,conduction=dict(source=0.,drain=0.),
            total=dict(source=-displacement,drain=0.,top_gate=displacement,bottom_gate=0.),
            trap_charge_rate_A=0.,free_carrier_charge_rate_A=0.))
    row=dict(x_m=np.array([0.,1.]),y_m=np.array([0.,1.]),z_m=np.array([-1.,0.,1.]),
             sheet_index=1,material=dict(name='fixture'))
    return dict(steps_per_phase=count,phase_s=1.,contact='thermionic',dielectric=True,
        boundary='finite_side_electrodes_5nm_v1',contact_z_bounds_m=[[-.5,.5]]*2,
        checkpoints=[row,deepcopy(row)],trace=states)


class TraceComparisonTests(unittest.TestCase):
    def test_gate_impulse_matches_interval_average_and_integral(self):
        coarse,fine=trace(2),trace(4)
        self.assertEqual(coarse['trace'][1]['total']['top_gate'],2.)
        self.assertEqual(fine['trace'][2]['total']['top_gate'],0.)
        r=compare_traces(coarse,fine)
        self.assertEqual(r['interval_average_currents_and_rates']['total/top_gate']['max_absolute'],0.)
        self.assertEqual(r['cumulative_current_and_rate_integrals']['total/top_gate']['coarse_final_C'],1.)
        self.assertEqual(r['cumulative_current_and_rate_integrals']['total/top_gate']['fine_final_C'],1.)

    def test_ending_conduction_and_interval_average_are_both_reported(self):
        coarse,fine=trace(2),trace(4)
        coarse['trace'][1]['conduction']['source']=1.
        fine['trace'][1]['conduction']['source']=0.
        fine['trace'][2]['conduction']['source']=2.
        r=compare_traces(coarse,fine)
        self.assertEqual(r['interval_average_currents_and_rates']['conduction/source']['max_absolute'],0.)
        self.assertEqual(r['conduction_at_common_ending_times']['conduction/source']['max_absolute'],1.)

    def test_state_error_location_and_normalization(self):
        coarse,fine=trace(2),trace(4);fine['trace'][4]['trap_charge_C']=3e-18
        r=compare_traces(coarse,fine)['state_at_common_times']['trap_charge_C']
        self.assertEqual(r['coarse_step'],2);self.assertEqual(r['time_s'],1.)
        self.assertAlmostEqual(r['max_normalized'],3.)

    def test_rejects_different_geometry(self):
        fine=trace(4);fine['checkpoints'][0]['z_m'][0]-=.01
        with self.assertRaisesRegex(ValueError,'same-mesh'):compare_traces(trace(2),fine)

    def test_rejects_nonintegral_time_refinement(self):
        with self.assertRaisesRegex(ValueError,'integer multiple'):compare_traces(trace(2),trace(3))

    def test_rejects_different_physics_or_later_drive(self):
        for phase in (0,1):
            coarse,fine=trace(2),trace(4)
            coarse['checkpoints'][phase]['top_gate_V']=.01
            fine['checkpoints'][phase]['top_gate_V']=.02
            with self.subTest(phase=phase):
                with self.assertRaisesRegex(ValueError,'configuration or phase drive'):compare_traces(coarse,fine)

    def test_rejects_missing_phase_metadata(self):
        fine=trace(4);fine['checkpoints'].pop()
        with self.assertRaisesRegex(ValueError,'checkpoint/drive'):compare_traces(trace(2),fine)

    def test_later_phase_impulse_stays_in_its_own_coarse_interval(self):
        def two_phases(count):
            record=trace(count);dt=1./count;time=record['trace'][-1]['time_s']
            for i in range(1,count+1):
                state=deepcopy(record['trace'][count]);time+=dt
                state.update(time_s=time,phase=2)
                state['gates']['top_gate']=3.;state['contact_charge_C']['source']=-3.
                state['dielectric_contact_charge_C']['source']=-3.
                current=2./dt if i==1 else 0.
                state['total'].update(top_gate=current,source=-current)
                record['trace'].append(state)
            record['checkpoints'].append(deepcopy(record['checkpoints'][-1]))
            return record
        result=compare_traces(two_phases(2),two_phases(4))
        self.assertEqual(result['phases'],2)
        self.assertEqual(result['interval_average_currents_and_rates']['total/top_gate']['max_absolute'],0.)
        self.assertEqual(result['cumulative_current_and_rate_integrals']['total/top_gate']['fine_final_C'],3.)

    def test_rejects_incomplete_fine_pulse(self):
        fine=trace(4);fine['trace'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete fine'):compare_traces(trace(2),fine)

    def test_rejects_wrong_fine_dt_or_phase(self):
        for key,value in (('dt_s',.5),('phase',2)):
            fine=trace(4);fine['trace'][2][key]=value
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,'time/phase/dt'):compare_traces(trace(2),fine)

    def test_rejects_nonfinite_current(self):
        fine=trace(4);fine['trace'][2]['total']['source']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite scalar'):compare_traces(trace(2),fine)

    def test_rejects_changed_terminal_inventory(self):
        fine=trace(4);del fine['trace'][3]['total']['top_gate']
        with self.assertRaisesRegex(ValueError,'inconsistent current'):compare_traces(trace(2),fine)

    def test_invalid_normalization_is_rejected(self):
        for bad in (0.,-1.,float('inf'),float('nan'),True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):compare_traces(trace(2),trace(4),current_scale_A=bad)

    def test_json_npz_loader_preserves_geometry_without_product_import(self):
        with tempfile.TemporaryDirectory() as folder:
            stem=Path(folder)/'sample';np.savez(str(stem)+'.npz',z=np.array([-1.,0.,1.]))
            Path(str(stem)+'.json').write_text(json.dumps(dict(z={'__ndarray__':'z'})))
            np.testing.assert_array_equal(load_record(stem)['z'],[-1.,0.,1.])


if __name__=='__main__':unittest.main()
