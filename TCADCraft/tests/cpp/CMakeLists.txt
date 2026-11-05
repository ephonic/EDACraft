add_executable(test_newton_poisson_consistency test_newton_poisson_consistency.cpp)
target_link_libraries(test_newton_poisson_consistency PRIVATE tcad_core)
add_test(NAME newton_poisson_consistency COMMAND test_newton_poisson_consistency)
add_executable(test_preisach_history test_preisach_history.cpp)
target_link_libraries(test_preisach_history PRIVATE tcad_core)
add_test(NAME preisach_history COMMAND test_preisach_history)
add_executable(test_nls_volume_kinetics test_nls_volume_kinetics.cpp)
target_link_libraries(test_nls_volume_kinetics PRIVATE tcad_core)
add_test(NAME nls_volume_kinetics COMMAND test_nls_volume_kinetics)
# These residuals and the 1e-28 reference tolerance require the quad backend.
if(NOT TCAD_FORCE_LONG_DOUBLE AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_executable(test_nls_zero_mean_target test_nls_zero_mean_target.cpp)
    target_link_libraries(test_nls_zero_mean_target PRIVATE tcad_core)
    add_test(NAME nls_zero_mean_target COMMAND test_nls_zero_mean_target)
    set_tests_properties(nls_zero_mean_target PROPERTIES LABELS "ferroelectric;validation" TIMEOUT 180)
    add_executable(test_nls_predictor_drive test_nls_predictor_drive.cpp)
    target_link_libraries(test_nls_predictor_drive PRIVATE tcad_core)
    add_test(NAME nls_predictor_drive COMMAND test_nls_predictor_drive)
    set_tests_properties(nls_predictor_drive PROPERTIES LABELS "ferroelectric;validation" TIMEOUT 300)
endif()
add_executable(test_fe_interface_flux test_fe_interface_flux.cpp)
target_link_libraries(test_fe_interface_flux PRIVATE tcad_core)
add_test(NAME fe_interface_flux COMMAND test_fe_interface_flux)
add_executable(test_lk_coupled_jacobian test_lk_coupled_jacobian.cpp)
target_link_libraries(test_lk_coupled_jacobian PRIVATE tcad_core)
add_test(NAME lk_coupled_jacobian COMMAND test_lk_coupled_jacobian)

add_executable(test_trap_temperature test_trap_temperature.cpp)
target_link_libraries(test_trap_temperature PRIVATE tcad_core)
add_test(NAME trap_temperature COMMAND test_trap_temperature)

add_executable(test_dense_structure test_dense_structure.cpp)
target_link_libraries(test_dense_structure PRIVATE tcad_core)
add_test(NAME dense_structure COMMAND test_dense_structure)

add_executable(test_precision_backend test_precision_backend.cpp)
target_link_libraries(test_precision_backend PRIVATE tcad_core)
add_test(NAME precision_backend COMMAND test_precision_backend)

add_executable(test_constants_profile test_constants_profile.cpp)
target_link_libraries(test_constants_profile PRIVATE tcad_core)
add_test(NAME constants_profile COMMAND test_constants_profile)

add_executable(test_continuity_chain test_continuity_chain.cpp)
target_link_libraries(test_continuity_chain PRIVATE tcad_core)
add_test(NAME continuity_chain COMMAND test_continuity_chain)

add_executable(test_neutral_poisson test_neutral_poisson.cpp)
target_link_libraries(test_neutral_poisson PRIVATE tcad_core)
add_test(NAME neutral_poisson COMMAND test_neutral_poisson)

add_executable(test_arora_mobility_limits ../native_mobility_limits.cpp)
target_link_libraries(test_arora_mobility_limits PRIVATE tcad_core)
add_test(NAME arora_mobility_limits COMMAND test_arora_mobility_limits)

add_executable(test_arora_transport_limits test_arora_transport_limits.cpp)
target_link_libraries(test_arora_transport_limits PRIVATE tcad_core)
add_test(NAME arora_transport_limits COMMAND test_arora_transport_limits)

add_executable(test_mobility_precision test_mobility_precision.cpp)
target_link_libraries(test_mobility_precision PRIVATE tcad_core)
add_test(NAME mobility_precision COMMAND test_mobility_precision
    "${CMAKE_CURRENT_SOURCE_DIR}/../data/mobility_precision.tsv")

add_executable(test_phi_freezing_control test_phi_freezing_control.cpp)
target_link_libraries(test_phi_freezing_control PRIVATE tcad_core)
add_test(NAME phi_freezing_control COMMAND test_phi_freezing_control)

add_executable(test_hfs_kcl_consistency test_hfs_kcl_consistency.cpp)
target_link_libraries(test_hfs_kcl_consistency PRIVATE tcad_core)
add_test(NAME hfs_kcl_consistency COMMAND test_hfs_kcl_consistency
    "${CMAKE_CURRENT_SOURCE_DIR}/../data/hfs_kcl_seeds.dat"
    "${CMAKE_CURRENT_BINARY_DIR}/hfs_kcl_states.jsonl")

add_executable(test_empty_sparse_matrix test_empty_sparse_matrix.cpp)
target_link_libraries(test_empty_sparse_matrix PRIVATE tcad_core)
add_test(NAME empty_sparse_matrix COMMAND test_empty_sparse_matrix)

add_executable(test_solver_backend_state test_solver_backend_state.cpp)
target_link_libraries(test_solver_backend_state PRIVATE tcad_core)
add_test(NAME solver_backend_state COMMAND test_solver_backend_state)

add_executable(test_banded_transaction test_banded_transaction.cpp)
target_link_libraries(test_banded_transaction PRIVATE tcad_core)
add_test(NAME banded_transaction COMMAND test_banded_transaction)

add_executable(test_portable_band portable_band_probe.cpp)
target_link_libraries(test_portable_band PRIVATE tcad_core)
foreach(mode ordinary pivot asymmetric species disconnected dense)
    add_test(NAME portable_band_${mode} COMMAND test_portable_band ${mode})
    set_tests_properties(portable_band_${mode} PROPERTIES ENVIRONMENT "TCAD_LIN_DEBUG=1")
endforeach()

add_executable(test_gummel_banded test_gummel_banded.cpp)
target_link_libraries(test_gummel_banded PRIVATE tcad_core)
foreach(mode cached retry primary refusal_recover refusal_fail dense_small explicit_dense threshold)
    add_test(NAME gummel_banded_${mode} COMMAND test_gummel_banded ${mode})
    set_tests_properties(gummel_banded_${mode} PROPERTIES
        ENVIRONMENT "TCAD_LIN_DEBUG=1" TIMEOUT 30)
endforeach()

add_executable(test_newton_density_update test_newton_density_update.cpp
    ../../src/device_simulator_double.cpp)
target_link_libraries(test_newton_density_update PRIVATE tcad_core)
add_test(NAME newton_density_update COMMAND test_newton_density_update)

add_executable(test_transport_parameter_guard test_transport_parameter_guard.cpp
    ../../src/device_simulator_double.cpp)
target_link_libraries(test_transport_parameter_guard PRIVATE tcad_core)
add_test(NAME transport_parameter_guard COMMAND test_transport_parameter_guard)

add_executable(test_raw_option_guard test_raw_option_guard.cpp
    ../../src/device_simulator_double.cpp)
target_link_libraries(test_raw_option_guard PRIVATE tcad_core)
add_test(NAME raw_option_guard COMMAND test_raw_option_guard)

add_executable(test_hfs_low_field_cutoff test_hfs_low_field_cutoff.cpp
    ../../src/device_simulator_double.cpp)
target_link_libraries(test_hfs_low_field_cutoff PRIVATE tcad_core)
add_test(NAME hfs_low_field_cutoff COMMAND test_hfs_low_field_cutoff)

add_executable(test_ii_driving test_ii_driving.cpp)
target_link_libraries(test_ii_driving PRIVATE tcad_core)
add_test(NAME ii_driving COMMAND test_ii_driving)

add_executable(test_hfs_reference_density test_hfs_reference_density.cpp)
target_link_libraries(test_hfs_reference_density PRIVATE tcad_core)
add_test(NAME hfs_reference_density COMMAND test_hfs_reference_density)

add_executable(test_hfs_contact_policy test_hfs_contact_policy.cpp)
target_link_libraries(test_hfs_contact_policy PRIVATE tcad_core)
add_test(NAME hfs_contact_policy COMMAND test_hfs_contact_policy)

add_executable(test_hfs_ii_current test_hfs_ii_current.cpp)
target_link_libraries(test_hfs_ii_current PRIVATE tcad_core)
add_test(NAME hfs_ii_current COMMAND test_hfs_ii_current)

add_executable(test_ii_field_floor test_ii_field_floor.cpp
    ../../src/device_simulator_double.cpp)
target_link_libraries(test_ii_field_floor PRIVATE tcad_core)
add_test(NAME ii_field_floor COMMAND test_ii_field_floor)

add_executable(test_newton_banded test_newton_banded.cpp)
target_link_libraries(test_newton_banded PRIVATE tcad_core)
foreach(mode x y z carriers threshold quantum transient 2d other_backend)
    add_test(NAME newton_banded_${mode} COMMAND test_newton_banded ${mode})
    set_tests_properties(newton_banded_${mode} PROPERTIES
        ENVIRONMENT "TCAD_LIN_DEBUG=1" TIMEOUT 30)
endforeach()

# Current Newton guard qualification. Historical replay snapshots live in
# docs/validation; these targets exercise the current core by default.
foreach(name quantum_newton_kcl quantum_fresh_acceptance quantum_contact axis_kcl contact_kcl)
    add_executable(test_${name} test_${name}.cpp)
    target_link_libraries(test_${name} PRIVATE tcad_core)
    add_test(NAME ${name} COMMAND test_${name})
    set_tests_properties(${name} PROPERTIES LABELS "newton;quantum;kcl" TIMEOUT 600)
endforeach()

# Complete the current test_*.cpp registration; standalone probe programs
# retain their existing purpose and invocation contracts.
foreach(name fermi_trial_domain fermi_one_sided_domain)
    add_executable(test_${name} test_${name}.cpp)
    target_link_libraries(test_${name} PRIVATE tcad_core)
    add_test(NAME ${name} COMMAND test_${name})
    set_tests_properties(${name} PROPERTIES LABELS "fermi;newton;domain" TIMEOUT 60)
endforeach()
foreach(name quantum_ii_current quantum_returned_audit)
    add_executable(test_${name} test_${name}.cpp)
    target_link_libraries(test_${name} PRIVATE tcad_core)
    add_test(NAME ${name} COMMAND test_${name})
    set_tests_properties(${name} PROPERTIES LABELS "quantum;newton;audit" TIMEOUT 600)
endforeach()

# Normalized carrier-statistics primitive; independent integral reference.
add_executable(test_fermi_half test_fermi_half.cpp)
target_compile_definitions(test_fermi_half PRIVATE TCAD_FERMI_INTEGRATION=1)
target_link_libraries(test_fermi_half PRIVATE tcad_core)
add_test(NAME fermi_half COMMAND test_fermi_half)
set_tests_properties(fermi_half PROPERTIES LABELS "fermi;statistics" TIMEOUT 120)

# Physical unscaled diagnostics must exclude iteration stabilization.
add_executable(test_physical_raw_residual test_physical_raw_residual.cpp)
target_link_libraries(test_physical_raw_residual PRIVATE tcad_core)
add_test(NAME physical_raw_residual COMMAND test_physical_raw_residual)
add_test(NAME physical_raw_residual_invalid COMMAND test_physical_raw_residual invalid)
set_tests_properties(physical_raw_residual physical_raw_residual_invalid PROPERTIES
    LABELS "poisson;residual;physical" TIMEOUT 120)

add_executable(test_fd_intrinsic test_fd_intrinsic.cpp)
target_link_libraries(test_fd_intrinsic PRIVATE tcad_core)
add_test(NAME fd_intrinsic COMMAND test_fd_intrinsic)
add_test(NAME fd_intrinsic_invalid COMMAND test_fd_intrinsic invalid)
set_tests_properties(fd_intrinsic fd_intrinsic_invalid PROPERTIES
    LABELS "fermi;intrinsic;neutrality" TIMEOUT 300)

# Strong Auger pair decay must satisfy the original backward Euler balance.
add_executable(test_auger_implicit test_auger_implicit.cpp)
target_link_libraries(test_auger_implicit PRIVATE tcad_core)
add_test(NAME auger_implicit COMMAND test_auger_implicit)
set_tests_properties(auger_implicit PROPERTIES LABELS "auger;continuity;transient" TIMEOUT 120)

# Public classical Auger transient wiring and adaptive time-step control.
add_executable(test_public_auger_transient test_public_auger_transient.cpp)
target_link_libraries(test_public_auger_transient PRIVATE tcad_core)
add_test(NAME public_auger_transient COMMAND test_public_auger_transient)
add_test(NAME public_auger_transient_invalid COMMAND test_public_auger_transient invalid)
set_tests_properties(public_auger_transient public_auger_transient_invalid PROPERTIES
    LABELS "auger;transient;public" TIMEOUT 180)

add_executable(test_poisson_dirichlet_contract test_poisson_dirichlet_contract.cpp)
target_link_libraries(test_poisson_dirichlet_contract PRIVATE tcad_core)
add_test(NAME poisson_dirichlet_contract COMMAND test_poisson_dirichlet_contract)
set_tests_properties(poisson_dirichlet_contract PROPERTIES
    LABELS "poisson;thermal;boundary;validation" TIMEOUT 120)

add_executable(test_native_doping_contract test_native_doping_contract.cpp)
target_link_libraries(test_native_doping_contract PRIVATE tcad_core)
add_test(NAME native_doping_contract COMMAND test_native_doping_contract)
set_tests_properties(native_doping_contract PROPERTIES
    LABELS "poisson;gummel;doping;validation" TIMEOUT 120)

add_executable(test_native_fe_finiteness test_native_fe_finiteness.cpp)
target_link_libraries(test_native_fe_finiteness PRIVATE tcad_core)
add_test(NAME native_fe_finiteness COMMAND test_native_fe_finiteness)
set_tests_properties(native_fe_finiteness PROPERTIES
    LABELS "poisson;gummel;ferroelectric;validation" TIMEOUT 120)

add_executable(test_native_permittivity_contract test_native_permittivity_contract.cpp)
target_link_libraries(test_native_permittivity_contract PRIVATE tcad_core)
add_test(NAME native_permittivity_contract COMMAND test_native_permittivity_contract)
set_tests_properties(native_permittivity_contract PROPERTIES
    LABELS "poisson;gummel;thermal;permittivity;validation" TIMEOUT 120)

add_executable(test_newton_permittivity_contract test_newton_permittivity_contract.cpp)
target_link_libraries(test_newton_permittivity_contract PRIVATE tcad_core)
add_test(NAME newton_permittivity_contract COMMAND test_newton_permittivity_contract)
set_tests_properties(newton_permittivity_contract PROPERTIES
    LABELS "newton;permittivity;validation" TIMEOUT 120)

add_executable(test_newton_doping_contract test_newton_doping_contract.cpp)
target_link_libraries(test_newton_doping_contract PRIVATE tcad_core)
add_test(NAME newton_doping_contract COMMAND test_newton_doping_contract)
set_tests_properties(newton_doping_contract PROPERTIES
    LABELS "newton;doping;validation" TIMEOUT 120)

add_executable(test_newton_pair_material_contract test_newton_pair_material_contract.cpp)
target_link_libraries(test_newton_pair_material_contract PRIVATE tcad_core)
add_test(NAME newton_pair_material_contract COMMAND test_newton_pair_material_contract)
set_tests_properties(newton_pair_material_contract PROPERTIES
    LABELS "newton;transport;srh;validation" TIMEOUT 120)

add_executable(test_newton_source_material_contract test_newton_source_material_contract.cpp)
target_link_libraries(test_newton_source_material_contract PRIVATE tcad_core)
add_test(NAME newton_source_material_contract COMMAND test_newton_source_material_contract)
set_tests_properties(newton_source_material_contract PROPERTIES
    LABELS "newton;generation;bandgap;fraction;validation" TIMEOUT 120)

add_executable(test_newton_steady_density test_newton_steady_density.cpp)
target_link_libraries(test_newton_steady_density PRIVATE tcad_core)
add_test(NAME newton_steady_density COMMAND test_newton_steady_density)
set_tests_properties(newton_steady_density PROPERTIES
    LABELS "newton;steady;transport;srh;convergence" TIMEOUT 180)

add_executable(test_newton_boundary_contract test_newton_boundary_contract.cpp)
target_link_libraries(test_newton_boundary_contract PRIVATE tcad_core)
add_test(NAME newton_boundary_contract COMMAND test_newton_boundary_contract)
set_tests_properties(newton_boundary_contract PROPERTIES
    LABELS "newton;boundary;contacts;validation" TIMEOUT 180)

add_executable(test_newton_ohmic_contract test_newton_ohmic_contract.cpp)
target_link_libraries(test_newton_ohmic_contract PRIVATE tcad_core)
add_test(NAME newton_ohmic_contract COMMAND test_newton_ohmic_contract)
set_tests_properties(newton_ohmic_contract PROPERTIES
    LABELS "newton;ohmic;contacts;validation" TIMEOUT 180)

add_executable(test_ohmic_entry_contract test_ohmic_entry_contract.cpp)
target_link_libraries(test_ohmic_entry_contract PRIVATE tcad_core)
add_test(NAME ohmic_entry_contract COMMAND test_ohmic_entry_contract)
set_tests_properties(ohmic_entry_contract PROPERTIES
    LABELS "ohmic;poisson;gummel;device;validation" TIMEOUT 180)

add_executable(test_trap_entry_contract test_trap_entry_contract.cpp)
target_link_libraries(test_trap_entry_contract PRIVATE tcad_core)
add_test(NAME trap_entry_contract COMMAND test_trap_entry_contract)
set_tests_properties(trap_entry_contract PROPERTIES
    LABELS "poisson;newton;traps;validation" TIMEOUT 180)

add_executable(test_newton_input_contract test_newton_input_contract.cpp)
target_link_libraries(test_newton_input_contract PRIVATE tcad_core)
add_test(NAME newton_input_contract COMMAND test_newton_input_contract)
set_tests_properties(newton_input_contract PROPERTIES
    LABELS "newton;initialization;validation" TIMEOUT 180)

add_executable(test_newton_fe_contract test_newton_fe_contract.cpp)
target_link_libraries(test_newton_fe_contract PRIVATE tcad_core)
add_test(NAME newton_fe_contract COMMAND test_newton_fe_contract)
set_tests_properties(newton_fe_contract PROPERTIES
    LABELS "newton;ferroelectric;validation" TIMEOUT 180)

add_executable(test_poisson_fe_history_contract test_poisson_fe_history_contract.cpp)
target_link_libraries(test_poisson_fe_history_contract PRIVATE tcad_core)
add_test(NAME poisson_fe_history_contract COMMAND test_poisson_fe_history_contract)
set_tests_properties(poisson_fe_history_contract PROPERTIES
    LABELS "poisson;ferroelectric;validation" TIMEOUT 180)

add_executable(test_fe_turning_stack_contract test_fe_turning_stack_contract.cpp)
target_link_libraries(test_fe_turning_stack_contract PRIVATE tcad_core)
add_test(NAME fe_turning_stack_contract COMMAND test_fe_turning_stack_contract)
set_tests_properties(fe_turning_stack_contract PROPERTIES
    LABELS "poisson;ferroelectric;validation" TIMEOUT 180)

add_executable(test_fe_potential_contract test_fe_potential_contract.cpp)
target_link_libraries(test_fe_potential_contract PRIVATE tcad_core)
add_test(NAME fe_potential_contract COMMAND test_fe_potential_contract)
set_tests_properties(fe_potential_contract PROPERTIES
    LABELS "poisson;ferroelectric;validation" TIMEOUT 180)

add_executable(test_lk_clear_contract test_lk_clear_contract.cpp)
target_link_libraries(test_lk_clear_contract PRIVATE tcad_core)
add_test(NAME lk_clear_contract COMMAND test_lk_clear_contract)
set_tests_properties(lk_clear_contract PROPERTIES
    LABELS "poisson;ferroelectric;validation" TIMEOUT 180)

add_executable(test_dg_mask_contract test_dg_mask_contract.cpp)
target_link_libraries(test_dg_mask_contract PRIVATE tcad_core)
add_test(NAME dg_mask_contract COMMAND test_dg_mask_contract)
set_tests_properties(dg_mask_contract PROPERTIES
    LABELS "quantum;density-gradient;validation" TIMEOUT 180)

add_executable(test_newton_mask_contract test_newton_mask_contract.cpp)
target_link_libraries(test_newton_mask_contract PRIVATE tcad_core)
add_test(NAME newton_mask_contract COMMAND test_newton_mask_contract)
set_tests_properties(newton_mask_contract PROPERTIES
    LABELS "newton;quantum;validation" TIMEOUT 180)

add_executable(test_dg_parameter_finiteness test_dg_parameter_finiteness.cpp)
target_link_libraries(test_dg_parameter_finiteness PRIVATE tcad_core)
add_test(NAME dg_parameter_finiteness COMMAND test_dg_parameter_finiteness)
set_tests_properties(dg_parameter_finiteness PROPERTIES
    LABELS "quantum;parameters;validation" TIMEOUT 300)

add_executable(test_gummel_entry_contract test_gummel_entry_contract.cpp)
target_link_libraries(test_gummel_entry_contract PRIVATE tcad_core)
add_test(NAME gummel_entry_contract COMMAND test_gummel_entry_contract)
set_tests_properties(gummel_entry_contract PROPERTIES LABELS "transport;parameters;validation" TIMEOUT 300)

add_executable(test_gummel_solve_shape test_gummel_solve_shape.cpp)
target_link_libraries(test_gummel_solve_shape PRIVATE tcad_core)
add_test(NAME gummel_solve_shape COMMAND test_gummel_solve_shape)
set_tests_properties(gummel_solve_shape PROPERTIES LABELS "transport;parameters;validation" TIMEOUT 300)

add_executable(test_quantum_array_finiteness test_quantum_array_finiteness.cpp)
target_link_libraries(test_quantum_array_finiteness PRIVATE tcad_core)
add_test(NAME quantum_array_finiteness COMMAND test_quantum_array_finiteness)
set_tests_properties(quantum_array_finiteness PROPERTIES LABELS "transport;parameters;validation" TIMEOUT 300)

add_executable(test_gummel_postprocess_shape test_gummel_postprocess_shape.cpp)
target_link_libraries(test_gummel_postprocess_shape PRIVATE tcad_core)
add_test(NAME gummel_postprocess_shape COMMAND test_gummel_postprocess_shape)
set_tests_properties(gummel_postprocess_shape PROPERTIES LABELS "transport;parameters;validation" TIMEOUT 300)

add_executable(test_postprocess_finiteness test_postprocess_finiteness.cpp)
target_link_libraries(test_postprocess_finiteness PRIVATE tcad_core)
add_test(NAME postprocess_finiteness COMMAND test_postprocess_finiteness)
set_tests_properties(postprocess_finiteness PROPERTIES LABELS "transport;parameters;validation" TIMEOUT 300)

add_executable(test_nonuniform_field test_nonuniform_field.cpp)
target_link_libraries(test_nonuniform_field PRIVATE tcad_core)
add_test(NAME nonuniform_field COMMAND test_nonuniform_field)
set_tests_properties(nonuniform_field PROPERTIES LABELS "transport;mesh;validation" TIMEOUT 300)

add_executable(test_nonuniform_wkb test_nonuniform_wkb.cpp)
target_link_libraries(test_nonuniform_wkb PRIVATE tcad_core)
add_test(NAME nonuniform_wkb COMMAND test_nonuniform_wkb)
set_tests_properties(nonuniform_wkb PROPERTIES LABELS "transport;mesh;validation" TIMEOUT 300)

add_executable(test_newton_btbt_mesh test_newton_btbt_mesh.cpp)
target_link_libraries(test_newton_btbt_mesh PRIVATE tcad_core)
add_test(NAME newton_btbt_mesh COMMAND test_newton_btbt_mesh)
set_tests_properties(newton_btbt_mesh PROPERTIES LABELS "transport;mesh;validation" TIMEOUT 300)

add_executable(test_btbt_solver_contract test_btbt_solver_contract.cpp)
target_link_libraries(test_btbt_solver_contract PRIVATE tcad_core)
add_test(NAME btbt_solver_contract COMMAND test_btbt_solver_contract)
set_tests_properties(btbt_solver_contract PROPERTIES LABELS "transport;validation" TIMEOUT 300)

add_executable(test_wkb_cutoff_boundaries test_wkb_cutoff_boundaries.cpp)
target_link_libraries(test_wkb_cutoff_boundaries PRIVATE tcad_core)
add_test(NAME wkb_cutoff_boundaries COMMAND test_wkb_cutoff_boundaries)
set_tests_properties(wkb_cutoff_boundaries PROPERTIES LABELS "transport;wkb;validation" TIMEOUT 180)

add_executable(test_grid_size_overflow test_grid_size_overflow.cpp)
target_link_libraries(test_grid_size_overflow PRIVATE tcad_core)
add_test(NAME grid_size_overflow COMMAND test_grid_size_overflow)
set_tests_properties(grid_size_overflow PROPERTIES LABELS "grid;validation" TIMEOUT 180)
