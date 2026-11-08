"""Interval comparisons preserve a drive-edge charge impulse under dt refinement."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'benchmarks'))
from sheet_refinement_trace import compare_traces,compare_time_orders,load_record


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

    def test_trace_loader_retains_initial_state_and_all_drives(self):
        with tempfile.TemporaryDirectory() as folder:
            stem=Path(folder)/'sample'
            np.savez(str(stem)+'.npz',initial=np.array([.1,.2]),dynamic=np.ones(10000),drive=np.array([.3,.4]))
            metadata=dict(checkpoints=[dict(result=dict(phi_V={'__ndarray__':'initial'})),
                dict(top_gate_V={'__ndarray__':'drive'},result=dict(phi_V={'__ndarray__':'dynamic'}),
                     previous=dict(phi_V={'__ndarray__':'initial'}))],trace=[{'time_s':0.}])
            Path(str(stem)+'.json').write_text(json.dumps(metadata))
            full=load_record(stem);lean=load_record(stem,trace_only=True)
            np.testing.assert_array_equal(lean['checkpoints'][0]['result']['phi_V'],[.1,.2])
            np.testing.assert_array_equal(lean['checkpoints'][1]['top_gate_V'],[.3,.4])
            self.assertNotIn('result',lean['checkpoints'][1]);self.assertNotIn('previous',lean['checkpoints'][1])
            self.assertEqual(full['checkpoints'][1]['result']['phi_V'].size,10000)
            self.assertEqual(full['trace'],lean['trace'])

    def test_trace_loader_preserves_comparison_results(self):
        with tempfile.TemporaryDirectory() as folder:
            full=[];lean=[]
            for n in (2,4,8):
                record=trace(n);record['checkpoints'][0]['result']={'phi_V':[.1]}
                record['checkpoints'][1]['result']={'phi_V':[.2]}
                stem=Path(folder)/str(n);np.savez(str(stem)+'.npz')
                Path(str(stem)+'.json').write_text(json.dumps(record,default=lambda a:a.tolist()))
                full.append(load_record(stem));lean.append(load_record(stem,trace_only=True))
            self.assertEqual(compare_time_orders(*full),compare_time_orders(*lean))
            self.assertEqual(compare_traces(*full[:2]),compare_traces(*lean[:2]))


class ThreeResolutionTests(unittest.TestCase):
    def test_first_and_second_order_use_identical_observation_support(self):
        for order in (1,2):
            records=[trace(n) for n in (2,4,8)]
            for record in records:
                dt=record['phase_s']/record['steps_per_phase']
                for row in record['trace'][1:]:row['trap_charge_C']=1e-18*dt**order*row['time_s']
            result=compare_time_orders(*records)
            q=result['state_at_common_times']['trap_charge_C']
            with self.subTest(order=order):
                self.assertAlmostEqual(q['observed_order'],order)
                self.assertAlmostEqual(q['increment_ratio'],2.**-order)
                self.assertEqual(q['coarse_to_middle']['coarse_step'],2)
                self.assertEqual(q['middle_to_fine']['coarse_step'],2)
                self.assertEqual(result['common_accepted_ending_times'],2)

    def test_drive_impulse_is_not_reported_as_time_error(self):
        result=compare_time_orders(trace(2),trace(4),trace(8))
        q=result['interval_average_currents_and_rates']['total/top_gate']
        self.assertEqual(q['coarse_to_middle']['max_absolute'],0.)
        self.assertEqual(q['middle_to_fine']['max_absolute'],0.)
        self.assertIsNone(q['observed_order']);self.assertFalse(q['roundoff_resolved'])

    def test_order_excludes_intermediate_times_outside_common_support(self):
        records=[trace(n) for n in (2,4,8)]
        for record in records:
            dt=1./record['steps_per_phase']
            for row in record['trace'][1:]:row['trap_charge_C']=1e-18*dt*row['time_s']
        records[1]['trace'][1]['trap_charge_C']=1.
        records[2]['trace'][2]['trap_charge_C']=-1.
        q=compare_time_orders(*records)['state_at_common_times']['trap_charge_C']
        self.assertAlmostEqual(q['observed_order'],1.)

    def test_accumulated_clock_spread_is_reported_without_relaxing_adjacent_gate(self):
        records=[]
        for n in (128,256,512):
            record=trace(n);record['phase_s']=20e-12;dt=20e-12/n
            template=deepcopy(record['trace'][-1]);record['trace']=[dict(time_s=0.)];time=0.
            for i in range(3*n):
                time+=dt;row=deepcopy(template);row.update(time_s=time,dt_s=dt,phase=i//n+1)
                record['trace'].append(row)
            record['checkpoints']=[deepcopy(record['checkpoints'][0]) for _ in range(4)]
            records.append(record)
        result=compare_time_orders(*records)
        self.assertTrue(all(x<1e-24 for x in result['adjacent_max_time_differences_s']))
        self.assertGreater(result['max_three_way_accumulated_time_spread_s'],1e-24)
        self.assertLess(result['max_three_way_accumulated_time_spread_s'],2e-24)
        self.assertEqual(result['adjacent_time_atol_s'],1e-24)

    def test_rate_and_cumulative_charge_have_known_first_order(self):
        records=[trace(n) for n in (2,4,8)]
        for record in records:
            for row in record['trace'][1:]:row['conduction']['drain']=1e-7/record['steps_per_phase']
        result=compare_time_orders(*records)
        for category in ('interval_average_currents_and_rates','conduction_at_common_ending_times',
                         'cumulative_current_and_rate_integrals'):
            with self.subTest(category=category):
                self.assertAlmostEqual(result[category]['conduction/drain']['observed_order'],1.)

    def test_roundoff_floor_prevents_false_orders(self):
        records=[trace(n) for n in (2,4,8)]
        for record in records:
            for row in record['trace'][1:]:row['trap_charge_C']=1e-30/record['steps_per_phase']
        q=compare_time_orders(*records)['state_at_common_times']['trap_charge_C']
        self.assertIsNone(q['observed_order']);self.assertIsNone(q['increment_ratio'])

    def test_rejects_unequal_refinement_ratios(self):
        with self.assertRaisesRegex(ValueError,'same refinement ratio'):
            compare_time_orders(trace(2),trace(4),trace(16))

    def test_rejects_different_initial_physical_states(self):
        records=[trace(n) for n in (2,4,8)]
        for record in records:record['checkpoints'][0]['result']={'phi_V':np.array([0.])}
        records[-1]['checkpoints'][0]['result']['phi_V'][0]=.01
        with self.assertRaisesRegex(ValueError,'initial physical states'):
            compare_time_orders(*records)

    def test_rejects_invalid_fine_clock_and_roundoff_floor(self):
        fine=trace(8);fine['trace'][-1]['time_s']+=1e-3
        with self.assertRaisesRegex(ValueError,'time/phase/dt'):
            compare_time_orders(trace(2),trace(4),fine)
        with self.assertRaisesRegex(ValueError,'roundoff_floor'):
            compare_time_orders(trace(2),trace(4),trace(8),roundoff_floor=0.)


if __name__=='__main__':unittest.main()
