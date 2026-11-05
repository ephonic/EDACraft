#include "hfs_reference.h"
#include "structured_field.h"
#include "linearized_wkb.h"
#include "newton_solver.h"
#include "ii_driving.h"
#include "newton_density_update_333.h"
#include "polarization_flux.h"
#include "lk_material_field.h"
#include "statistics.h"
#include "density_gradient.h"
#include "newton_quantum_acceptance.h"
#include "quantum_contact.h"
#include "transport_contract.h"
#include "hfs_edge_mobility.h"
#include <iostream>
#include <cstdio>
#include <cmath>
#include <algorithm>

namespace tcad {

namespace {
void validate_newton_inputs(size_t count, const Vector& phi, const Vector& n,
                            const Vector& p, const Vector& Nc, const Vector& Nv,
                            const Vector& Eg) {
    if (phi.size() != count || n.size() != count || p.size() != count)
        throw std::invalid_argument("Newton state size mismatch");
    if (Nc.size() != count || Nv.size() != count)
        throw std::invalid_argument("Newton effective density of states is not initialized");
    if (Eg.size() != count)
        throw std::invalid_argument("Newton bandgap is not initialized");
}
// Local Kane generation depends on potential only. Include its derivative in
// both carrier rows with the same negative generation sign as the residual.
// Threshold and cap corners are not differentiable; the existing active branch
// defines the derivative (zero below threshold and beyond a positive cap).
void add_btbt_jacobian_row(SparseMatrix& J, size_t row, const Grid3D& g,
    const NewtonOptions& opt, const real_t* phi, size_t idx,
    real_t generation, real_t source_scale, real_t gap) {
    if (!opt.enable_btbt || generation == TCAD_CONST(0.0)
        || opt.btbt_continuity_scale == TCAD_CONST(0.0)) return;
    if (opt.btbt_use_nonlocal) {
        const LinearizedWKBParameters params{opt.btbt_A,opt.btbt_D,
            opt.btbt_nonlocal_mass,opt.btbt_tunnel_path_frac,opt.btbt_wkb_npts};
        const real_t weight=opt.btbt_weight.empty()?TCAD_CONST(1.0):opt.btbt_weight[idx];
        const auto source=evaluate_linearized_wkb(g,phi,idx,gap,params,weight,true);
        const real_t sign=linearized_wkb_x_field(g,phi,idx)>0?TCAD_CONST(1.0):-TCAD_CONST(1.0);
        const real_t derivative=-source_scale*opt.btbt_continuity_scale*
            source.d_generation_d_field*sign;
        structured_node_field_weights(idx,idx%g.nx,1,g.nx,g.xx,g.dx,
            [&](size_t column,real_t coefficient){J.add_entry(row,column,derivative*coefficient);});
        return;
    }
    const size_t nodes[3] = {idx%g.nx, (idx/g.nx)%g.ny, idx/(g.nx*g.ny)};
    const size_t strides[3] = {1, g.nx, g.nx*g.ny};
    const size_t counts[3] = {g.nx, g.ny, g.nz};
    const std::vector<real_t>* positions[3] = {&g.xx, &g.yx, &g.zx};
    const real_t steps[3] = {g.dx, g.dy, g.dz};
    real_t field[3];
    for (int a=0; a<3; ++a)
        field[a] = structured_node_field(phi, idx, nodes[a], strides[a], counts[a], *positions[a], steps[a]);
    const int selected = opt.btbt_field_mode>=1 && opt.btbt_field_mode<=3
        ? opt.btbt_field_mode-1 : -1;
    const real_t magnitude = selected>=0 ? abs_q(field[selected])
        : sqrt_q(field[0]*field[0]+field[1]*field[1]+field[2]*field[2]);
    if (magnitude < TCAD_CONST(1e4)
        || (opt.btbt_field_cap>TCAD_CONST(0.0) && magnitude>opt.btbt_field_cap)) return;
    real_t effective = magnitude, exponent = TCAD_CONST(1.0);
    if (opt.btbt_field_alpha != TCAD_CONST(0.0) && opt.btbt_field_ref>TCAD_CONST(0.0)) {
        effective *= pow_q(magnitude/opt.btbt_field_ref, opt.btbt_field_alpha);
        exponent += opt.btbt_field_alpha;
    }
    const real_t derivative = -source_scale*opt.btbt_continuity_scale
        * generation*(opt.btbt_D+opt.btbt_B/effective)*exponent/magnitude;
    for (int a=0; a<3; ++a) {
        if (selected>=0 && a!=selected) continue;
        const real_t direction = selected>=0
            ? (field[a]>TCAD_CONST(0.0) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0))
            : field[a]/magnitude;
        structured_node_field_weights(idx, nodes[a], strides[a], counts[a],
            *positions[a], steps[a], [&](size_t column, real_t weight) {
                J.add_entry(row, column, derivative*direction*weight);
            });
    }
}
} // namespace

NewtonSolver::NewtonSolver(const Grid3D& grid, const NewtonOptions& opt)
    : g_(grid), opt_(opt) {
    validate_ii_driving(opt_.ii_driving);
    validate_ii_reference_density(opt_.ii_refdens_n,opt_.ii_refdens_p);
    if(opt_.enable_ii && opt_.ii_driving==1) validate_ii_gqf_geometry(g_,opt_.statistics_type!=StatisticsType::BOLTZMANN || opt_.enable_quantum);
    if (opt_.enable_ii) {
        validate_ii_coefficients(opt_.ii_A_n, opt_.ii_B_n, opt_.ii_A_p, opt_.ii_B_p);
        validate_ii_floor(opt_.ii_E_floor);
    }
    if (opt_.enable_auger) validate_auger_coefficients(opt_.auger_Cn, opt_.auger_Cp);
    validate_hfs_reference_density(opt_.hfs_refdens_n,opt_.hfs_refdens_p);
    if (active_hfs_reference(opt_.hfs_enabled,opt_.hfs_driving,opt_.hfs_refdens_n,opt_.hfs_refdens_p)) validate_hfs_reference_geometry(g_,opt_.statistics_type!=StatisticsType::BOLTZMANN || opt_.enable_quantum);
    if (opt_.hfs_enabled) {
        validate_hfs_parameters(opt_.hfs_vsat_n, opt_.hfs_vsat_p,
                                opt_.hfs_beta_n, opt_.hfs_beta_p, opt_.hfs_driving);
        validate_hfs_low_field_cutoff(opt_.hfs_low_field_cutoff);
    }
    const size_t N = g_.npts();
    if (opt_.enable_btbt && opt_.btbt_use_nonlocal) {
        if (!isfinite_q(opt_.btbt_nonlocal_mass) || opt_.btbt_nonlocal_mass<=0 ||
            !isfinite_q(opt_.btbt_tunnel_path_frac) || opt_.btbt_wkb_npts<2)
            throw std::invalid_argument("invalid Newton WKB path parameters");
        validate_linearized_wkb_work(N, opt_.btbt_wkb_npts);
        if (opt_.btbt_continuity_scale!=0 && (g_.nx<2 || g_.ny!=1 || g_.nz!=1 ||
            opt_.enable_quantum || opt_.statistics_type!=StatisticsType::BOLTZMANN ||
            opt_.transient_enabled || opt_.freeze_phi || opt_.freeze_n || opt_.freeze_p))
            throw std::invalid_argument("Newton WKB feedback requires classical steady x-1D Boltzmann equations");
    }
    if (!opt_.btbt_weight.empty() && opt_.btbt_weight.size() != N)
        throw std::invalid_argument("Newton BTBT weight size mismatch");
    for (real_t weight : opt_.btbt_weight)
        if (!isfinite_q(weight))
            throw std::invalid_argument("Newton BTBT weight values must be finite");
    eps_.assign(N, EPS0 * TCAD_CONST(11.7));
    mu_n_.assign(N, TCAD_CONST(0.14));
    mu_p_.assign(N, TCAD_CONST(0.045));
    Nd_minus_Na_.assign(N, TCAD_CONST(0.0));
    charge_volume_fraction_.assign(N, TCAD_CONST(1.0));
    tau_n_.assign(N, TCAD_CONST(1e100));
    tau_p_.assign(N, TCAD_CONST(1e100));
    G_opt_.assign(N, TCAD_CONST(0.0));
}

void NewtonSolver::set_permittivity(const std::vector<real_t>& eps) {
    if (eps.size() != g_.npts())
        throw std::invalid_argument("Newton permittivity size mismatch");
    for (real_t value : eps)
        if (!isfinite_q(value))
            throw std::invalid_argument("permittivity values must be finite");
    eps_ = eps;
}

void NewtonSolver::set_edge_permittivity(
    const std::vector<real_t>& x_plus,
    const std::vector<real_t>& x_minus,
    const std::vector<real_t>& y_plus,
    const std::vector<real_t>& y_minus,
    const std::vector<real_t>& z_plus,
    const std::vector<real_t>& z_minus) {
    const size_t N = g_.npts();
    for (const auto* values : {&x_plus, &x_minus, &y_plus, &y_minus,
                               &z_plus, &z_minus}) {
        if (!values->empty() && values->size() != N)
            throw std::invalid_argument("Newton edge permittivity size mismatch");
    }
    for (const auto* values : {&x_plus, &x_minus, &y_plus, &y_minus,
                               &z_plus, &z_minus})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("edge permittivity values must be finite");
    edge_eps_x_plus_ = x_plus;
    edge_eps_x_minus_ = x_minus;
    edge_eps_y_plus_ = y_plus;
    edge_eps_y_minus_ = y_minus;
    edge_eps_z_plus_ = z_plus;
    edge_eps_z_minus_ = z_minus;
}

real_t NewtonSolver::edge_epsilon(
    size_t idx, size_t nbr,
    const std::vector<real_t>& override_values) const {
    if (override_values.size() == g_.npts() && override_values[idx] > TCAD_CONST(0.0))
        return override_values[idx];
    return TCAD_CONST(2.0) * eps_[idx] * eps_[nbr] /
           (eps_[idx] + eps_[nbr] + (lk_material_field_ ? TCAD_CONST(0.0) : TCAD_CONST(1e-30)));
}

real_t NewtonSolver::active_carrier_width(
    size_t idx, size_t j, size_t k, int axis,
    const std::vector<real_t>& mobility) const {
    // Insulating faces remove flux, not storage/source volume. Full nodal
    // widths make steady and transient rows share the same physical face.
    // Explicit fractional-charge steady models retain their historical
    // interface-node convention. This is not general cut-cell transport.
    const bool clip = !opt_.transient_enabled && legacy_carrier_widths_;
    if (axis == 1) {
        real_t w = g_.dy_cell(j);
        if (clip && j && mobility[idx-g_.nx] < EPSILON) w -= g_.dy_edge(j-1)/TCAD_CONST(2.0);
        if (clip && j+1<g_.ny && mobility[idx+g_.nx] < EPSILON) w -= g_.dy_edge(j)/TCAD_CONST(2.0);
        return w > EPSILON ? w : g_.dy_cell(j);
    }
    if (axis == 2) {
        real_t w = g_.dz_cell(k);const size_t stride=g_.nx*g_.ny;
        if (clip && k && mobility[idx-stride] < EPSILON) w -= g_.dz_edge(k-1)/TCAD_CONST(2.0);
        if (clip && k+1<g_.nz && mobility[idx+stride] < EPSILON) w -= g_.dz_edge(k)/TCAD_CONST(2.0);
        return w > EPSILON ? w : g_.dz_cell(k);
    }
    throw std::invalid_argument("active carrier width axis must be y or z");
}

void NewtonSolver::set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p) {
    if (mu_n.size() != g_.npts() || mu_p.size() != g_.npts())
        throw std::invalid_argument("mobility size mismatch");
    for (const auto* values : {&mu_n, &mu_p})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("mobility values must be finite");
    mu_n_ = mu_n; mu_p_ = mu_p;
}

void NewtonSolver::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    if (Nd_minus_Na.size() != g_.npts())
        throw std::invalid_argument("Doping size mismatch");
    for (real_t value : Nd_minus_Na)
        if (!isfinite_q(value))
            throw std::invalid_argument("Doping must be finite");
    Nd_minus_Na_ = Nd_minus_Na;
}

void NewtonSolver::set_charge_volume_fraction(
    const std::vector<real_t>& fraction) {
    if (fraction.size() != g_.npts())
        throw std::invalid_argument("charge volume fraction size mismatch");
    for (real_t value : fraction)
        if (!isfinite_q(value) || value < TCAD_CONST(0.0) || value > TCAD_CONST(1.0))
            throw std::invalid_argument("charge volume fraction must be in [0,1]");
    charge_volume_fraction_ = fraction;
    legacy_carrier_widths_ = std::any_of(fraction.begin(),fraction.end(),[](real_t v) {
        return v > TCAD_CONST(0.0) && v < TCAD_CONST(1.0);
    });
}

void NewtonSolver::set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p) {
    for (const auto* values : {&tau_n, &tau_p})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("recombination lifetime values must be finite");
    tau_n_ = tau_n; tau_p_ = tau_p;
}

void NewtonSolver::set_optical_generation(const std::vector<real_t>& G_opt) {
    for (real_t value : G_opt)
        if (!isfinite_q(value))
            throw std::invalid_argument("optical generation values must be finite");
    G_opt_ = G_opt;
}

void NewtonSolver::set_thermal_voltage(real_t VT) {
    if (!isfinite_q(VT) || VT <= TCAD_CONST(0.0))
        throw std::invalid_argument("thermal voltage must be finite and positive");
    VT_ = VT;
}

void NewtonSolver::set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv) {
    if (Nc.size() != g_.npts() || Nv.size() != g_.npts())
        throw std::invalid_argument("effective DOS size mismatch");
    for (const auto* values : {&Nc, &Nv})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("effective DOS values must be finite");
    Nc_ = Nc;
    Nv_ = Nv;
}

void NewtonSolver::set_bandgap(const std::vector<real_t>& Eg) {
    if (Eg.size() != g_.npts())
        throw std::invalid_argument("bandgap size mismatch");
    for (real_t value : Eg)
        if (!isfinite_q(value))
            throw std::invalid_argument("bandgap values must be finite");
    Eg_ = Eg;
}

void NewtonSolver::set_phi_dirichlet(const std::map<size_t, real_t>& bc) {
    for (const auto& entry : bc)
        if (entry.first >= g_.npts())
            throw std::out_of_range("potential boundary node is outside the grid");
    for (const auto& entry : bc)
        if (!isfinite_q(entry.second))
            throw std::invalid_argument("potential boundary value must be finite");
    phi_bc_ = bc;
}

void NewtonSolver::set_electron_bc(const std::map<size_t, real_t>& bc) {
    for (const auto& entry : bc)
        if (entry.first >= g_.npts())
            throw std::out_of_range("electron boundary node is outside the grid");
    for (const auto& entry : bc)
        if (!isfinite_q(entry.second) || entry.second < TCAD_CONST(0.0))
            throw std::invalid_argument("electron boundary value must be finite and nonnegative");
    n_bc_ = bc;
}

void NewtonSolver::set_hole_bc(const std::map<size_t, real_t>& bc) {
    for (const auto& entry : bc)
        if (entry.first >= g_.npts())
            throw std::out_of_range("hole boundary node is outside the grid");
    for (const auto& entry : bc)
        if (!isfinite_q(entry.second) || entry.second < TCAD_CONST(0.0))
            throw std::invalid_argument("hole boundary value must be finite and nonnegative");
    p_bc_ = bc;
}

void NewtonSolver::set_ferroelectric_polarization(const std::vector<char>& fe_mask,
                                                  const std::vector<real_t>& fe_polarization) {
    // fe_polarization is [Px,Py,Pz] interleaved per node (length 3*npts);
    // fe_mask is length npts.  Empty mask disables the FE feedback.
    const size_t N = g_.npts();
    if (!fe_mask.empty() && fe_mask.size() != N)
        throw std::invalid_argument("Newton FE mask size mismatch");
    if (fe_polarization.size() != 3*N &&
        !(fe_mask.empty() && fe_polarization.empty()))
        throw std::invalid_argument("Newton FE polarization size mismatch");
    for (real_t value : fe_polarization)
        if (!isfinite_q(value))
            throw std::invalid_argument("FE polarization values must be finite");
    fe_mask_ = fe_mask;
    fe_polarization_ = fe_polarization;
    lk_coupled_ = false;
    lk_material_field_ = false;
    lk_material_derivative_.clear();
    lk_cached_phi_.clear();
}

void NewtonSolver::set_transient_lk(const std::vector<char>& mask,
        const std::vector<real_t>& previous, real_t alpha, real_t beta,
        real_t gamma, real_t imprint, real_t depol_eps, int axis, bool material_field) {
    const size_t N = g_.npts();
    if (!opt_.transient_enabled || opt_.freeze_phi ||
        !isfinite_q(opt_.transient_dt) || opt_.transient_dt <= TCAD_CONST(0.0) ||
        mask.size() != N || previous.size() != 3*N ||
        !std::all_of(previous.begin(), previous.end(), isfinite_q) ||
        !isfinite_q(alpha) || !isfinite_q(beta) || beta <= TCAD_CONST(0.0) ||
        !isfinite_q(gamma) || gamma <= TCAD_CONST(0.0) || !isfinite_q(imprint) ||
        !isfinite_q(depol_eps) || depol_eps < TCAD_CONST(0.0) || axis < 0 || axis > 2 ||
        !isfinite_q(alpha + gamma/opt_.transient_dt) || alpha + gamma/opt_.transient_dt <= TCAD_CONST(0.0))
        throw std::invalid_argument("coupled LK requires finite coefficients, gamma/beta > 0, "
            "mesh-sized state and alpha+gamma/dt > 0 with unfrozen transient potential");
    if (material_field) {
        const size_t sizes[]={g_.nx,g_.ny,g_.nz}; int active=0;
        for(int c=0;c<3;++c) if(sizes[c]>1) { ++active; lk_material_axis_=c; }
        if(active<1 || N<3 || !edge_eps_x_plus_.empty() || !edge_eps_x_minus_.empty() ||
           !edge_eps_y_plus_.empty() || !edge_eps_y_minus_.empty() ||
           !edge_eps_z_plus_.empty() || !edge_eps_z_minus_.empty())
            throw std::invalid_argument("material-field LK Newton requires a structured grid without edge overrides");
    }
    lk_material_field_=material_field; lk_material_derivative_.clear();
    fe_mask_ = mask; lk_previous_ = previous;
    lk_alpha_ = alpha; lk_beta_ = beta; lk_gamma_ = gamma;
    lk_imprint_ = imprint; lk_depol_eps_ = depol_eps; lk_axis_ = axis;
    lk_coupled_ = true; lk_cached_phi_.clear();
}

void NewtonSolver::refresh_lk_polarization(const real_t* phi) {
    if (!lk_coupled_) return;
    const size_t N = g_.npts();
    if (lk_cached_phi_.size() == N && std::equal(lk_cached_phi_.begin(), lk_cached_phi_.end(), phi))
        return;
    if (lk_material_field_) {
        std::vector<real_t> candidate_phi(phi,phi+N);
        auto candidate=solve_lk_material_response_nd(g_,eps_,fe_mask_,lk_previous_,candidate_phi,
            lk_alpha_,lk_beta_,lk_gamma_/opt_.transient_dt,lk_imprint_,lk_depol_eps_,lk_axis_,lk_material_axis_);
        fe_polarization_=std::move(candidate); lk_cached_phi_=std::move(candidate_phi);
        lk_material_derivative_.clear(); return;
    }
    PoissonSolver kinetics(g_);
    kinetics.set_ferroelectric(fe_mask_, lk_alpha_, lk_beta_);
    kinetics.set_ferroelectric_gamma(lk_gamma_);
    kinetics.set_ferroelectric_builtin_field(lk_imprint_);
    kinetics.set_ferroelectric_depol(lk_depol_eps_);
    kinetics.set_ferroelectric_polar_axis(lk_axis_);
    kinetics.set_fe_polarization(lk_previous_);
    std::vector<real_t> candidate_phi(phi, phi+N);
    kinetics.update_ferroelectric_polarization_transient(candidate_phi, opt_.transient_dt);
    fe_polarization_ = kinetics.fe_polarization();
    lk_cached_phi_ = std::move(candidate_phi);
}

void NewtonSolver::add_lk_jacobian_row(SparseMatrix& J, size_t i, size_t j, size_t k) const {
    if (!lk_coupled_) return;
    const size_t idx = g_.index(i,j,k);
    auto node_derivative = [&](size_t node, int axis, real_t coefficient) {
        if (!fe_mask_[node]) return;
        if(lk_material_field_) {
            // Local Cartesian LK response couples only the line through node.
            // Inserting the other (exactly zero) derivatives turns sparse
            // Poisson rows into dense rows and fills the ILU graph with zeros.
            const size_t count=axis==0 ? g_.nx : axis==1 ? g_.ny : g_.nz;
            if(count==1) return;
            const size_t stride=axis==0 ? 1 : axis==1 ? g_.nx : g_.nx*g_.ny;
            const size_t coordinate=(node/stride)%count;
            const size_t first=node-coordinate*stride;
            const size_t offset=lk_material_line_offset(g_,axis)+node*count;
            for(size_t q=0;q<count;++q) {
                const size_t column=first+q*stride;
                const real_t derivative=lk_material_derivative_[offset+q];
                if(derivative!=TCAD_CONST(0.0)) J.add_entry(idx,column,coefficient*derivative);
            }
            return;
        }
        const size_t coordinate = axis == 0 ? node % g_.nx :
            axis == 1 ? (node/g_.nx) % g_.ny : node/(g_.nx*g_.ny);
        const size_t count = axis == 0 ? g_.nx : axis == 1 ? g_.ny : g_.nz;
        if (count == 1) return;
        const size_t stride = axis == 0 ? 1 : axis == 1 ? g_.nx : g_.nx*g_.ny;
        auto spacing = [&](size_t q) {
            return axis == 0 ? g_.dx_edge(q) : axis == 1 ? g_.dy_edge(q) : g_.dz_edge(q);
        };
        const size_t left = coordinate ? node-stride : node;
        const size_t right = coordinate+1 < count ? node+stride : node;
        const real_t distance = (coordinate ? spacing(coordinate-1) : TCAD_CONST(0.0)) +
                               (coordinate+1 < count ? spacing(coordinate) : TCAD_CONST(0.0));
        real_t a = lk_alpha_ + lk_gamma_/opt_.transient_dt;
        if (axis == lk_axis_ && lk_depol_eps_ > TCAD_CONST(0.0)) a += TCAD_CONST(1.0)/(lk_depol_eps_*EPS0);
        const real_t p = fe_polarization_[3*node+axis];
        const real_t susceptibility = TCAD_CONST(1.0)/(a+TCAD_CONST(3.0)*lk_beta_*p*p);
        // E=-(phi_right-phi_left)/distance, including one-sided boundaries.
        const real_t derivative = coefficient*susceptibility/distance;
        J.add_entry(idx, left, derivative);
        J.add_entry(idx, right, -derivative);
    };
    auto face = [&](size_t nbr, int axis, bool upper, real_t cell,
                    const std::vector<real_t>& values) {
        const real_t eps_face = edge_epsilon(idx, nbr, values);
        const real_t coefficient = (upper ? -TCAD_CONST(1.0) : TCAD_CONST(1.0))*eps_face/(TCAD_CONST(2.0)*cell);
        node_derivative(idx, axis, coefficient/eps_[idx]);
        node_derivative(nbr, axis, coefficient/eps_[nbr]);
    };
    if (i+1 < g_.nx) face(idx+1, 0, true, g_.dx_cell(i), edge_eps_x_plus_);
    if (i) face(idx-1, 0, false, g_.dx_cell(i), edge_eps_x_minus_);
    if (j+1 < g_.ny) face(idx+g_.nx, 1, true, g_.dy_cell(j), edge_eps_y_plus_);
    if (j) face(idx-g_.nx, 1, false, g_.dy_cell(j), edge_eps_y_minus_);
    if (k+1 < g_.nz) face(idx+g_.nx*g_.ny, 2, true, g_.dz_cell(k), edge_eps_z_plus_);
    if (k) face(idx-g_.nx*g_.ny, 2, false, g_.dz_cell(k), edge_eps_z_minus_);
}

void NewtonSolver::set_trap_charge(const std::vector<char>& trap_mask,
                                   real_t D_it, real_t E_t,
                                   const std::vector<real_t>& Q_ot) {
    // Validate the entire combined request before changing persistent charge.
    // Reuse the Poisson path's geometry and input contract, including empty
    // masks for oxide-only charge and empty oxide arrays for clearing.
    PoissonSolver trap_geometry(g_);
    trap_geometry.set_interface_traps(trap_mask, D_it, E_t);
    trap_geometry.set_oxide_traps(Q_ot);
    const real_t thickness = trap_geometry.trap_layer_thickness();
    trap_mask_ = trap_mask;
    trap_D_it_ = D_it;
    trap_E_t_ = E_t;
    Q_ot_ = Q_ot;
    trap_layer_thickness_ = thickness;
}

real_t NewtonSolver::compute_btbt_at(const real_t* phi, size_t idx) const {
    if (!opt_.enable_btbt) return TCAD_CONST(0.0);
    // Skip insulator/metal
    if (mu_n_[idx] < EPSILON) return TCAD_CONST(0.0);

    if (opt_.btbt_use_nonlocal) {
        const LinearizedWKBParameters params{opt_.btbt_A,opt_.btbt_D,
            opt_.btbt_nonlocal_mass,opt_.btbt_tunnel_path_frac,opt_.btbt_wkb_npts};
        const real_t weight=opt_.btbt_weight.empty()?TCAD_CONST(1.0):opt_.btbt_weight[idx];
        return evaluate_linearized_wkb(g_,phi,idx,Eg_[idx],params,weight).generation;
    }

    size_t i = idx % g_.nx;
    size_t j = (idx / g_.nx) % g_.ny;
    size_t k = idx / (g_.nx * g_.ny);

    const real_t Ex = structured_node_field(phi, idx, i, 1, g_.nx, g_.xx, g_.dx);
    const real_t Ey = structured_node_field(phi, idx, j, g_.nx, g_.ny, g_.yx, g_.dy);
    const real_t Ez = structured_node_field(phi, idx, k, g_.nx*g_.ny, g_.nz, g_.zx, g_.dz);

    real_t E_mag = TCAD_CONST(0.0);
    if (opt_.btbt_field_mode == 1) {
        E_mag = abs_q(Ex);
    } else if (opt_.btbt_field_mode == 2) {
        E_mag = abs_q(Ey);
    } else if (opt_.btbt_field_mode == 3) {
        E_mag = abs_q(Ez);
    } else {
        E_mag = sqrt_q(Ex*Ex + Ey*Ey + Ez*Ez);
    }
    if (opt_.btbt_field_cap > TCAD_CONST(0.0) && E_mag > opt_.btbt_field_cap) {
        E_mag = opt_.btbt_field_cap;
    }
    if (E_mag < TCAD_CONST(1.0e4)) return TCAD_CONST(0.0);
    if (opt_.btbt_field_alpha != TCAD_CONST(0.0) && opt_.btbt_field_ref > TCAD_CONST(0.0)) {
        E_mag *= pow_q(E_mag / opt_.btbt_field_ref, opt_.btbt_field_alpha);
    }

    real_t A = opt_.btbt_A * TCAD_CONST(1.0e6);  // cm^-3 -> m^-3
    real_t B = opt_.btbt_B;
    real_t D = opt_.btbt_D;
    real_t E_D = pow_q(E_mag, D);
    real_t generation = A * E_D * exp_q(-B / E_mag);
    if (!opt_.btbt_weight.empty()) generation *= opt_.btbt_weight[idx];
    return generation;
}

real_t NewtonSolver::compute_ii_at(const real_t* phi, const real_t* n,
                                   const real_t* p, size_t idx,
                                   const real_t* Qn, const real_t* Qp) const {
    // Per-node impact-ionization generation [m^-3 s^-1] via the EDGE form
    // (same convention as GummelSolver::compute_impact_ionization and
    // DeviceSimulator::compute_edge_currents).  For each of the up-to-6 edges
    // meeting at idx we add half of alpha(|E_edge|)*|J_edge|/q, matching
    // Gummel's equal endpoint deposition. Classical HFS uses the same
    // saturated edge currents as the continuity residual.
    if (!opt_.enable_ii) return TCAD_CONST(0.0);
    if (mu_n_[idx] < EPSILON && mu_p_[idx] < EPSILON) return TCAD_CONST(0.0);

    size_t i = idx % g_.nx;
    size_t j = (idx / g_.nx) % g_.ny;
    size_t k = idx / (g_.nx * g_.ny);
    const real_t VT = VT_;

    auto alpha_of = [&](real_t E_mag, real_t A, real_t B) -> real_t {
        if (E_mag < opt_.ii_E_floor) return TCAD_CONST(0.0);
        return A * exp_q(-B / E_mag);
    };

    real_t G = TCAD_CONST(0.0);

    // process one +neighbor edge: idx -> nbr (spacing d).
    auto edge = [&](size_t nbr, real_t d) {
        if (mu_n_[nbr] < EPSILON && mu_p_[nbr] < EPSILON) return;
        real_t dphi = phi[nbr] - phi[idx];
        const real_t pni = phi[idx] + Qn[idx], pnj = phi[nbr] + Qn[nbr];
        const real_t ppi = phi[idx] - Qp[idx], ppj = phi[nbr] - Qp[nbr];
        const real_t Bnm = bernoulli(-(pnj-pni)/VT), Bnp = bernoulli((pnj-pni)/VT);
        const real_t Bpm = bernoulli(-(ppj-ppi)/VT), Bpp = bernoulli((ppj-ppi)/VT);
        real_t E_edge = abs_q(dphi / d);
        const real_t Fn = opt_.ii_driving==1 ? ii_quasi_fermi_force(dphi,n[idx],n[nbr],VT,d,false,opt_.ii_refdens_n).value : E_edge;
        real_t an = alpha_of(Fn, opt_.ii_A_n, opt_.ii_B_n);
        const real_t Fp = opt_.ii_driving==1 ? ii_quasi_fermi_force(dphi,p[idx],p[nbr],VT,d,true,opt_.ii_refdens_p).value : E_edge;
        real_t ap = alpha_of(Fp, opt_.ii_A_p, opt_.ii_B_p);
        if (an == TCAD_CONST(0.0) && ap == TCAD_CONST(0.0)) return;
        real_t mu_ne = TCAD_CONST(2.0) * mu_n_[idx] * mu_n_[nbr] /
            (mu_n_[idx] + mu_n_[nbr] + TCAD_CONST(1e-30));
        real_t mu_pe = TCAD_CONST(2.0) * mu_p_[idx] * mu_p_[nbr] /
            (mu_p_[idx] + mu_p_[nbr] + TCAD_CONST(1e-30));
        if (opt_.hfs_enabled) {
            mu_ne = classical_hfs_edge_mobility(mu_ne, pni, pnj,
                n[idx], n[nbr], Nc_[idx], Nc_[nbr], VT, d,
                opt_.hfs_vsat_n, opt_.hfs_beta_n, hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, n_bc_.count(idx) || n_bc_.count(nbr)),
                opt_.hfs_low_field_cutoff, false, opt_.hfs_refdens_n).mobility;
            mu_pe = classical_hfs_edge_mobility(mu_pe, ppi, ppj,
                p[idx], p[nbr], Nv_[idx], Nv_[nbr], VT, d,
                opt_.hfs_vsat_p, opt_.hfs_beta_p, hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, p_bc_.count(idx) || p_bc_.count(nbr)),
                opt_.hfs_low_field_cutoff, true, opt_.hfs_refdens_p).mobility;
        }
        real_t Dn = mu_ne * VT / d;
        real_t Dp = mu_pe * VT / d;
        real_t Jn = QE * Dn * (n[idx] * Bnm - n[nbr] * Bnp);
        real_t Jp = QE * Dp * (p[idx] * Bpp - p[nbr] * Bpm);
        G += TCAD_CONST(0.5) * (an * abs_q(Jn) + ap * abs_q(Jp)) / QE;
    };

    if (i + 1 < g_.nx) edge(idx + 1, g_.dx_edge(i));
    if (i > 0)         edge(idx - 1, g_.dx_edge(i-1 > 0 ? i-1 : 0));
    if (j + 1 < g_.ny) edge(idx + g_.nx, g_.dy_edge(j));
    if (j > 0)         edge(idx - g_.nx, g_.dy_edge(j-1 > 0 ? j-1 : 0));
    if (k + 1 < g_.nz) edge(idx + g_.nx * g_.ny, g_.dz_edge(k));
    if (k > 0)         edge(idx - g_.nx * g_.ny, g_.dz_edge(k-1 > 0 ? k-1 : 0));
    return G;
}

void NewtonSolver::add_ii_jacobian_row(
    SparseMatrix& J, size_t row, const real_t* phi, const real_t* n,
    const real_t* p, size_t idx, real_t source_scale,
    const real_t* Qn, const real_t* Qp) const {
    if (!opt_.enable_ii) return;
    if (mu_n_[idx] < EPSILON && mu_p_[idx] < EPSILON) return;

    const size_t i = idx % g_.nx;
    const size_t j = (idx / g_.nx) % g_.ny;
    const size_t k = idx / (g_.nx * g_.ny);

    auto edge = [&](size_t nbr, real_t d) {
        if (mu_n_[nbr] < EPSILON && mu_p_[nbr] < EPSILON) return;
        const real_t dphi = phi[nbr] - phi[idx];
        const real_t E = abs_q(dphi / d);
        const bool gqf=opt_.ii_driving==1;
        const auto fn=gqf ? ii_quasi_fermi_force(dphi,n[idx],n[nbr],VT_,d,false,opt_.ii_refdens_n) : IIForce{E,0,0,0};
        const auto fp=gqf ? ii_quasi_fermi_force(dphi,p[idx],p[nbr],VT_,d,true,opt_.ii_refdens_p) : IIForce{E,0,0,0};
        if(fn.value<opt_.ii_E_floor && fp.value<opt_.ii_E_floor) return;

        const real_t pni = phi[idx] + Qn[idx], pnj = phi[nbr] + Qn[nbr];
        const real_t ppi = phi[idx] - Qp[idx], ppj = phi[nbr] - Qp[nbr];
        // Q is held fixed by the existing DG Picard/Newton linearization.
        const real_t dn = (pnj-pni)/VT_, dp = (ppj-ppi)/VT_;
        const real_t Bnm = bernoulli(-dn), Bnp = bernoulli(dn);
        const real_t Bpm = bernoulli(-dp), Bpp = bernoulli(dp);
        const real_t dBnm = -d_bernoulli_dx(-dn)/VT_, dBnp = d_bernoulli_dx(dn)/VT_;
        const real_t dBpm = -d_bernoulli_dx(-dp)/VT_, dBpp = d_bernoulli_dx(dp)/VT_;

        const real_t an = fn.value<opt_.ii_E_floor ? TCAD_CONST(0.0) : opt_.ii_A_n * exp_q(-opt_.ii_B_n / fn.value);
        const real_t dan_dF = fn.value<opt_.ii_E_floor ? TCAD_CONST(0.0) : an*opt_.ii_B_n/(fn.value*fn.value);
        const real_t ap = fp.value<opt_.ii_E_floor ? TCAD_CONST(0.0) : opt_.ii_A_p * exp_q(-opt_.ii_B_p / fp.value);
        const real_t dap_dF = fp.value<opt_.ii_E_floor ? TCAD_CONST(0.0) : ap*opt_.ii_B_p/(fp.value*fp.value);
        const real_t sign_dphi = (dphi > TCAD_CONST(0.0)) ? TCAD_CONST(1.0)
                                  : (dphi < TCAD_CONST(0.0)) ? -TCAD_CONST(1.0) : TCAD_CONST(0.0);
        const real_t dE_ddphi = sign_dphi / d;
        const real_t dan_ddphi = gqf ? dan_dF*fn.dphi : an * opt_.ii_B_n / (E * E) * dE_ddphi;
        const real_t dap_ddphi = gqf ? dap_dF*fp.dphi : ap * opt_.ii_B_p / (E * E) * dE_ddphi;

        real_t mu_ne = TCAD_CONST(2.0) * mu_n_[idx] * mu_n_[nbr] /
            (mu_n_[idx] + mu_n_[nbr] + TCAD_CONST(1e-30));
        real_t mu_pe = TCAD_CONST(2.0) * mu_p_[idx] * mu_p_[nbr] /
            (mu_p_[idx] + mu_p_[nbr] + TCAD_CONST(1e-30));
        const bool saturated = opt_.hfs_enabled;
        HfsEdgeMobility hn{mu_ne}, hp{mu_pe};
        if (saturated) {
            hn = classical_hfs_edge_mobility(mu_ne, pni, pnj,
                n[idx], n[nbr], Nc_[idx], Nc_[nbr], VT_, d,
                opt_.hfs_vsat_n, opt_.hfs_beta_n, hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, n_bc_.count(idx) || n_bc_.count(nbr)),
                opt_.hfs_low_field_cutoff, false, opt_.hfs_refdens_n);
            hp = classical_hfs_edge_mobility(mu_pe, ppi, ppj,
                p[idx], p[nbr], Nv_[idx], Nv_[nbr], VT_, d,
                opt_.hfs_vsat_p, opt_.hfs_beta_p, hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, p_bc_.count(idx) || p_bc_.count(nbr)),
                opt_.hfs_low_field_cutoff, true, opt_.hfs_refdens_p);
            mu_ne = hn.mobility; mu_pe = hp.mobility;
        }
        const real_t Dn = mu_ne * VT_ / d;
        const real_t Dp = mu_pe * VT_ / d;
        const real_t Jn = QE * Dn * (n[idx] * Bnm - n[nbr] * Bnp);
        const real_t Jp = QE * Dp * (p[idx] * Bpp - p[nbr] * Bpm);
        const real_t sign_Jn = (Jn > TCAD_CONST(0.0)) ? TCAD_CONST(1.0)
                               : (Jn < TCAD_CONST(0.0)) ? -TCAD_CONST(1.0) : TCAD_CONST(0.0);
        const real_t sign_Jp = (Jp > TCAD_CONST(0.0)) ? TCAD_CONST(1.0)
                               : (Jp < TCAD_CONST(0.0)) ? -TCAD_CONST(1.0) : TCAD_CONST(0.0);

        real_t dJn_ddphi = QE * Dn *
            (n[idx] * dBnm - n[nbr] * dBnp);
        real_t dJp_ddphi = QE * Dp *
            (p[idx] * dBpp - p[nbr] * dBpm);
        if (saturated) {
            dJn_ddphi += QE * VT_ / d * hn.dphi_j * (n[idx] * Bnm - n[nbr] * Bnp);
            dJp_ddphi += QE * VT_ / d * hp.dphi_j * (p[idx] * Bpp - p[nbr] * Bpm);
        }
        const real_t half = TCAD_CONST(0.5);
        const real_t dG_ddphi = half *
            (dan_ddphi * abs_q(Jn) + an * sign_Jn * dJn_ddphi
             + dap_ddphi * abs_q(Jp) + ap * sign_Jp * dJp_ddphi) / QE;

        real_t dG_dni = half * an * sign_Jn * Dn * Bnm;
        real_t dG_dnj = -half * an * sign_Jn * Dn * Bnp;
        real_t dG_dpi = half * ap * sign_Jp * Dp * Bpp;
        real_t dG_dpj = -half * ap * sign_Jp * Dp * Bpm;
        if (saturated) {
            const real_t sn = half * an * sign_Jn * VT_ / d * (n[idx] * Bnm - n[nbr] * Bnp);
            const real_t sp = half * ap * sign_Jp * VT_ / d * (p[idx] * Bpp - p[nbr] * Bpm);
            dG_dni += sn * hn.dcarrier_i; dG_dnj += sn * hn.dcarrier_j;
            dG_dpi += sp * hp.dcarrier_i; dG_dpj += sp * hp.dcarrier_j;
        }

        if(gqf) {
            dG_dni += half*dan_dF*fn.di*abs_q(Jn)/QE;
            dG_dnj += half*dan_dF*fn.dj*abs_q(Jn)/QE;
            dG_dpi += half*dap_dF*fp.di*abs_q(Jp)/QE;
            dG_dpj += half*dap_dF*fp.dj*abs_q(Jp)/QE;
        }

        // F_carrier contains -(G_ii-R)*source_scale.  Apply the log-space
        // chain rule here when carrier unknowns are u=log(n), v=log(p).
        const real_t ni_scale = opt_.use_log_space ? n[idx] : TCAD_CONST(1.0);
        const real_t nj_scale = opt_.use_log_space ? n[nbr] : TCAD_CONST(1.0);
        const real_t pi_scale = opt_.use_log_space ? p[idx] : TCAD_CONST(1.0);
        const real_t pj_scale = opt_.use_log_space ? p[nbr] : TCAD_CONST(1.0);
        J.add_entry(row, phi_idx(idx), source_scale * dG_ddphi);
        J.add_entry(row, phi_idx(nbr), -source_scale * dG_ddphi);
        J.add_entry(row, n_idx(idx), -source_scale * dG_dni * ni_scale);
        J.add_entry(row, n_idx(nbr), -source_scale * dG_dnj * nj_scale);
        J.add_entry(row, p_idx(idx), -source_scale * dG_dpi * pi_scale);
        J.add_entry(row, p_idx(nbr), -source_scale * dG_dpj * pj_scale);
    };

    if (i + 1 < g_.nx) edge(idx + 1, g_.dx_edge(i));
    if (i > 0) edge(idx - 1, g_.dx_edge(i - 1));
    if (j + 1 < g_.ny) edge(idx + g_.nx, g_.dy_edge(j));
    if (j > 0) edge(idx - g_.nx, g_.dy_edge(j - 1));
    if (k + 1 < g_.nz) edge(idx + g_.nx * g_.ny, g_.dz_edge(k));
    if (k > 0) edge(idx - g_.nx * g_.ny, g_.dz_edge(k - 1));
}

// Bernoulli function: B(x) = x / (exp(x) - 1)
real_t NewtonSolver::bernoulli(real_t x) {
    if (abs_q(x) < TCAD_CONST(1e-12)) return TCAD_CONST(1.0) - x / TCAD_CONST(2.0);
    if (x > TCAD_CONST(100.0)) return TCAD_CONST(0.0);
    if (x < -TCAD_CONST(100.0)) return -x;
    return x / expm1_q(x);
}

// Derivative of Bernoulli: B'(x) = (exp(x) - 1 - x*exp(x)) / (exp(x) - 1)^2
real_t NewtonSolver::d_bernoulli_dx(real_t x) {
    if (abs_q(x) < TCAD_CONST(1e-12)) return -TCAD_CONST(0.5) + x / TCAD_CONST(6.0);
    if (x > TCAD_CONST(100.0)) return TCAD_CONST(0.0);
    if (x < -TCAD_CONST(100.0)) return -TCAD_CONST(1.0);
    real_t ex = exp_q(x);
    real_t em1 = ex - TCAD_CONST(1.0);
    return (em1 - x * ex) / (em1 * em1);
}

void NewtonSolver::compute_srh_and_derivs(size_t idx, real_t n, real_t p, real_t ni,
                                          real_t& R, real_t& dR_dn, real_t& dR_dp) const {
    real_t np = n * p;
    real_t ni2 = ni * ni;
    real_t tau_n = (idx < tau_n_.size()) ? tau_n_[idx] : TCAD_CONST(1e100);
    real_t tau_p = (idx < tau_p_.size()) ? tau_p_[idx] : TCAD_CONST(1e100);
    real_t denom = tau_p * (n + ni) + tau_n * (p + ni);
    R = TCAD_CONST(0.0); dR_dn = TCAD_CONST(0.0); dR_dp = TCAD_CONST(0.0);
    if (denom > EPSILON) {
        real_t num = np - ni2;
        R = num / denom;
        dR_dn = (p * denom - num * tau_p) / (denom * denom);
        dR_dp = (n * denom - num * tau_n) / (denom * denom);
    }
    if (opt_.enable_auger) {
        const real_t excess = np - ni2;
        const real_t prefactor = opt_.auger_Cn * n + opt_.auger_Cp * p;
        R += prefactor * excess;
        dR_dn += opt_.auger_Cn * excess + prefactor * p;
        dR_dp += opt_.auger_Cp * excess + prefactor * n;
    }
}


// Independent physical convergence guard for steady one-dimensional
// transport.  The electron and hole generation terms cancel in
// div(Jn+Jp), so total conventional current must be constant within each
// contact-free section. Internal carrier reservoirs may inject current.
// A small row-equilibrated Newton correction alone is not
// sufficient: contact rows can be strongly scaled and previously allowed
// a KCL-broken state to return as converged.
bool NewtonSolver::steady_1d_kcl_ok(const std::vector<real_t>& x) const {
    const size_t N = g_.npts();
    const size_t active_axes = (g_.nx > 1) + (g_.ny > 1) + (g_.nz > 1);
    if (active_axes != 1 || N < 3 ||
        opt_.transient_enabled || opt_.freeze_n || opt_.freeze_p) {
        return true;
    }
    auto density = [&](size_t block, size_t node) -> real_t {
        real_t value = x[block * N + node];
        return opt_.use_log_space ? exp_q(value) : value;
    };
    // Use the identical Picard state as assemble_residual. Never refresh or
    // damp Q here: the guard audits the equations that just passed their gate.
    std::vector<real_t> Qn(N, TCAD_CONST(0.0)), Qp(N, TCAD_CONST(0.0));
    if (opt_.enable_quantum && !semi_mask_.empty()) {
        if (use_lagged_quantum_potential_ && lagged_Qn_.size() == N &&
            lagged_Qp_.size() == N) {
            Qn = lagged_Qn_;
            Qp = lagged_Qp_;
        } else {
            std::vector<real_t> n(N), p(N);
            for (size_t node = 0; node < N; ++node) {
                n[node] = density(1, node);
                p[node] = density(2, node);
            }
            DensityGradient dg_tmp(g_);
            dg_tmp.set_coefficients(dg_bn_, dg_bp_);
            dg_tmp.set_silicon_multivalley(
                dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
                dg_silicon_subbands_);
            dg_tmp.set_interface_distance_factor(dg_interface_distance_factor_);
            dg_tmp.set_step_boundary(
                dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
                dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
                dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
                dg_step_h_theta_);
            dg_tmp.set_semiconductor_mask(semi_mask_);
            dg_tmp.set_thermal_voltage(VT_);
            dg_tmp.quantum_potential(
                n,
                p,
                Qn, Qp);
        }
    }
    if (opt_.enable_quantum && !semi_mask_.empty()) {
        detail::pin_quantum_contacts(n_bc_, p_bc_, Qn, Qp);
    }
    auto potential = [&](size_t node, bool hole) -> real_t {
        if (!opt_.enable_quantum) return x[phi_idx(node)];
        return hole ? x[phi_idx(node)] - Qp[node] : x[phi_idx(node)] + Qn[node];
    };
    real_t jmin = TCAD_CONST(0.0), jmax = TCAD_CONST(0.0), jabs = TCAD_CONST(0.0);
    bool first = true;
    auto section_ok = [&]() {
        const real_t absolute_spread = jmax - jmin;
        const real_t relative_spread = absolute_spread / (jabs + TCAD_CONST(1e-30));
        return absolute_spread <= TCAD_CONST(1.0e-8) || relative_spread <= TCAD_CONST(1.0e-2);
    };
    const int axis = g_.nx > 1 ? 0 : (g_.ny > 1 ? 1 : 2);
    // A single active axis has contiguous node indices in every orientation.
    for (size_t i = 0; i + 1 < N; ++i) {
        size_t left = i;
        size_t right = i + 1;
        real_t d = axis == 0 ? g_.dx_edge(i) :
            (axis == 1 ? g_.dy_edge(i) : g_.dz_edge(i));
        real_t dphi = x[phi_idx(right)] - x[phi_idx(left)];
        real_t delta = dphi / VT_;
        real_t Bm = bernoulli(-delta);
        real_t Bp = bernoulli(delta);
        const real_t dn = opt_.enable_quantum
            ? (potential(right, false) - potential(left, false)) / VT_ : delta;
        const real_t dp = opt_.enable_quantum
            ? (potential(right, true) - potential(left, true)) / VT_ : delta;
        const real_t Bnm = opt_.enable_quantum ? bernoulli(-dn) : Bm;
        const real_t Bnp = opt_.enable_quantum ? bernoulli(dn) : Bp;
        const real_t Bpm = opt_.enable_quantum ? bernoulli(-dp) : Bm;
        const real_t Bpp = opt_.enable_quantum ? bernoulli(dp) : Bp;
        real_t mu_ne = TCAD_CONST(2.0) * mu_n_[left] * mu_n_[right] /
            (mu_n_[left] + mu_n_[right] + TCAD_CONST(1e-30));
        real_t mu_pe = TCAD_CONST(2.0) * mu_p_[left] * mu_p_[right] /
            (mu_p_[left] + mu_p_[right] + TCAD_CONST(1e-30));
        real_t Dn = mu_ne * VT_ / d;
        real_t Dp = mu_pe * VT_ / d;
        real_t nl = density(1, left);
        real_t nr = density(1, right);
        real_t pl = density(2, left);
        real_t pr = density(2, right);
        // Match both carriers' transport potentials and the residual HFS law.
        if(opt_.hfs_enabled) {
            auto saturated=[&](real_t diffusion,real_t mobility,
                    real_t dl,real_t dr,bool hole) {
                real_t force=abs_q(opt_.enable_quantum ?
                    potential(right,hole)-potential(left,hole) : dphi)/d;
                if(hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, (hole ? p_bc_ : n_bc_).count(left) || (hole ? p_bc_ : n_bc_).count(right))==0) {
                    const auto& dos=hole ? Nv_ : Nc_;
                    const real_t reference=hole ? opt_.hfs_refdens_p : opt_.hfs_refdens_n;
                    const real_t sign=hole ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                    const real_t ql=potential(left,hole)+sign*VT_*log_q(hfs_reference_carrier(dl,reference)/std::max(dos[left],TCAD_CONST(1.0)));
                    const real_t qr=potential(right,hole)+sign*VT_*log_q(hfs_reference_carrier(dr,reference)/std::max(dos[right],TCAD_CONST(1.0)));
                    force=abs_q(qr-ql)/d;
                }
                force=hfs_active_driving_force(force,opt_.hfs_low_field_cutoff);
                const real_t vsat=hole ? opt_.hfs_vsat_p : opt_.hfs_vsat_n;
                const real_t beta=hole ? opt_.hfs_beta_p : opt_.hfs_beta_n;
                const real_t ratio=mobility*force/vsat;
                if(ratio>TCAD_CONST(1e-12))
                    diffusion/=pow_q(TCAD_CONST(1.0)+pow_q(ratio,beta),TCAD_CONST(1.0)/beta);
                return diffusion;
            };
            Dn=saturated(Dn,mu_ne,nl,nr,false);
            Dp=saturated(Dp,mu_pe,pl,pr,true);
        }
        real_t Jn = QE * Dn * (nr * Bnp - nl * Bnm);
        real_t Jp = QE * Dp * (pl * Bpp - pr * Bpm);
        real_t Jtotal = Jn + Jp;
        if (i > 0 && (n_bc_.count(left) || p_bc_.count(left))) {
            // A carrier Dirichlet row is a reservoir, not a zero-divergence
            // equation. Finish the left section before starting the right.
            // Any unconstrained species at this node retains its original
            // full residual gate; this KCL check never replaces that gate.
            if (!section_ok()) return false;
            first = true;
            jabs = TCAD_CONST(0.0);
        }
        if (first) {
            jmin = jmax = Jtotal;
            first = false;
        } else {
            jmin = std::min(jmin, Jtotal);
            jmax = std::max(jmax, Jtotal);
        }
        jabs = std::max(jabs, abs_q(Jtotal));
    }
    // Relative KCL is ill-conditioned around equilibrium, while a power
    // threshold can hide a large non-conservative leakage current in a
    // weak field.  Use a mixed absolute/relative test: round-off-scale
    // equilibrium current passes absolutely; a conducting state must be
    // spatially constant to 1%.  Continuing Newton beyond its scaled-row
    // tolerance is essential for drift/diffusion cancellation at abrupt
    // high-doping junctions.
    return section_ok();
}

void NewtonSolver::refresh_lagged_quantum_potential(
    const std::vector<real_t>& x) {
    const size_t N = g_.npts();
    const std::vector<real_t> old_Qn = lagged_Qn_;
    const std::vector<real_t> old_Qp = lagged_Qp_;
    if (!opt_.enable_quantum || semi_mask_.empty()) {
        lagged_Qn_.clear();
        lagged_Qp_.clear();
        return;
    }

    std::vector<real_t> n(N), p(N);
    for (size_t i = 0; i < N; ++i) {
        if (opt_.use_log_space) {
            n[i] = exp_q(x[n_idx(i)]);
            p[i] = exp_q(x[p_idx(i)]);
        } else {
            n[i] = x[n_idx(i)];
            p[i] = x[p_idx(i)];
        }
    }
    DensityGradient dg_tmp(g_);
    dg_tmp.set_coefficients(dg_bn_, dg_bp_);
    dg_tmp.set_silicon_multivalley(
        dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
        dg_silicon_subbands_);
    dg_tmp.set_interface_distance_factor(dg_interface_distance_factor_);
    dg_tmp.set_step_boundary(
        dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
        dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
        dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
        dg_step_h_theta_);
    dg_tmp.set_semiconductor_mask(semi_mask_);
    dg_tmp.set_thermal_voltage(VT_);
    std::vector<real_t> next_Qn, next_Qp;
    dg_tmp.quantum_potential(n, p, next_Qn, next_Qp);
    if (old_Qn.size() == N && old_Qp.size() == N) {
        // Outer DG Picard damping.  A fully converged fixed-Q carrier state
        // can imply a large undamped Q jump; applying that jump in one shot
        // re-excites the same limit cycle Newton was asked to rescue.  Match
        // the stable production Gummel quantum damping and let repeated
        // residual-gated refreshes approach Q(n,p) transactionally.
        constexpr real_t quantum_damping = TCAD_CONST(0.2);
        lagged_Qn_.resize(N);
        lagged_Qp_.resize(N);
        for (size_t i = 0; i < N; ++i) {
            lagged_Qn_[i] = old_Qn[i] +
                quantum_damping * (next_Qn[i] - old_Qn[i]);
            lagged_Qp_[i] = old_Qp[i] +
                quantum_damping * (next_Qp[i] - old_Qp[i]);
        }
    } else {
        lagged_Qn_ = std::move(next_Qn);
        lagged_Qp_ = std::move(next_Qp);
    }
    detail::pin_quantum_contacts(n_bc_, p_bc_, lagged_Qn_, lagged_Qp_);
}

void NewtonSolver::assemble_residual(const std::vector<real_t>& x, std::vector<real_t>& F) {
    const size_t N = g_.npts();
    F.assign(3 * N, TCAD_CONST(0.0));

    // Extract phi, n, p from x.  In log-space mode the carrier blocks hold
    // u=log(n), v=log(p); we materialise the linear densities into temporaries
    // so every residual formula (SG flux, Poisson, SRH, BE) is evaluated on
    // true n, p — identical physics to the linear-space path.  See audit §18.
    const real_t* phi = x.data();
    refresh_lk_polarization(phi);
    std::vector<real_t> n_lin, p_lin;
    const real_t* n;
    const real_t* p;
    if (opt_.use_log_space) {
        n_lin.resize(N);
        p_lin.resize(N);
        const real_t* u = x.data() + N;
        const real_t* v = x.data() + 2 * N;
        for (size_t i = 0; i < N; ++i) {
            n_lin[i] = exp_q(u[i]);
            p_lin[i] = exp_q(v[i]);
        }
        n = n_lin.data();
        p = p_lin.data();
    } else {
        n = x.data() + N;
        p = x.data() + 2 * N;
    }

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], opt_.temperature, Nc_[i], Nv_[i], opt_.statistics_type);
    }

    // --- DG quantum potential (lagged: computed from current n,p) ---
    // Qn modifies the Poisson charge (n → n*exp(Qn/VT)) and the continuity
    // SG potential (φ → φ+Qn).  The Jacobian treats Qn as constant (lagged),
    // which adds a few Newton iterations but avoids the 5-equation block.
    std::vector<real_t> Qn_dg, Qp_dg;
    std::vector<real_t> n_dg(N), p_dg(N);  // DG-corrected densities for Poisson
    if (opt_.enable_quantum && !semi_mask_.empty() &&
        use_lagged_quantum_potential_ && lagged_Qn_.size() == N &&
        lagged_Qp_.size() == N) {
        Qn_dg = lagged_Qn_;
        Qp_dg = lagged_Qp_;
        n_dg.assign(n, n + N);
        p_dg.assign(p, p + N);
    } else if (opt_.enable_quantum && !semi_mask_.empty()) {
        DensityGradient dg_tmp(g_);
        dg_tmp.set_coefficients(dg_bn_, dg_bp_);
        dg_tmp.set_silicon_multivalley(
            dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
            dg_silicon_subbands_);
        dg_tmp.set_interface_distance_factor(dg_interface_distance_factor_);
        dg_tmp.set_step_boundary(
            dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
            dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
            dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
            dg_step_h_theta_);
        dg_tmp.set_semiconductor_mask(semi_mask_);
        dg_tmp.set_thermal_voltage(VT_);
        dg_tmp.quantum_potential(
            std::vector<real_t>(n, n + N),
            std::vector<real_t>(p, p + N),
            Qn_dg, Qp_dg);
        // n and p are the physical quantum-corrected carrier densities.  Q is
        // already included in the SG transport potential below; multiplying
        // the Poisson charge by exp(Q/VT) again double-counted confinement.
        n_dg.assign(n, n + N);
        p_dg.assign(p, p + N);
    } else {
        n_dg.assign(n, n + N);
        p_dg.assign(p, p + N);
        Qn_dg.assign(N, TCAD_CONST(0.0));
        Qp_dg.assign(N, TCAD_CONST(0.0));
    }

    if (opt_.enable_quantum && !semi_mask_.empty()) {
        detail::pin_quantum_contacts(n_bc_, p_bc_, Qn_dg, Qp_dg);
    }

    // --- Poisson residual ---  Uses DG-corrected charge n_dg, p_dg
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (phi_bc_.count(idx)) {
                    F[phi_idx(idx)] = phi[idx] - phi_bc_.at(idx);
                    continue;
                }
                if (opt_.freeze_phi) {
                    // Frozen-phi mode: pin phi to its current value so the
                    // Newton solve reduces to a 2-block (n,p) system.  See
                    // NewtonOptions::freeze_phi / audit §17.
                    F[phi_idx(idx)] = TCAD_CONST(0.0);
                    continue;
                }
                // Finite difference Laplacian with position-dependent epsilon
                real_t center = TCAD_CONST(0.0), sum = TCAD_CONST(0.0);
                auto add_link = [&](size_t nbr, real_t edge_cell,
                                    const std::vector<real_t>& edge_values) {
                    real_t eps_avg = edge_epsilon(idx, nbr, edge_values);
                    real_t c = eps_avg / edge_cell;
                    center += c;
                    sum += c * phi[nbr];
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i) * g_.dx_cell(i), edge_eps_x_plus_);
                if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1) * g_.dx_cell(i), edge_eps_x_minus_);
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j) * g_.dy_cell(j), edge_eps_y_plus_);
                if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1) * g_.dy_cell(j), edge_eps_y_minus_);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k) * g_.dz_cell(k), edge_eps_z_plus_);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz_edge(k-1) * g_.dz_cell(k), edge_eps_z_minus_);
                real_t rhs_poisson = sum - center * phi[idx] +
                    QE * charge_volume_fraction_[idx] *
                    (p_dg[idx] - n_dg[idx] + Nd_minus_Na_[idx]);
                // F = div(eps*grad(phi)) + rho_free - div(P).
                // The same face closure as Poisson includes bound charge
                // on both sides of the FE/linear-dielectric interface.
                auto fe_edge_eps = [&](int axis, bool upper, size_t node, size_t nbr) {
                    const auto& values = axis == 0
                        ? (upper ? edge_eps_x_plus_ : edge_eps_x_minus_)
                        : axis == 1 ? (upper ? edge_eps_y_plus_ : edge_eps_y_minus_)
                                    : (upper ? edge_eps_z_plus_ : edge_eps_z_minus_);
                    return edge_epsilon(node, nbr, values);
                };
                rhs_poisson -= polarization_divergence(g_, fe_mask_,
                    fe_polarization_, eps_, i, j, k, fe_edge_eps);
                // Interface/bulk trap charge (P6), mirroring PoissonSolver.
                // Q_it = -q * D_it * dE * (f_t - 0.5), Q_ot = persistent [C/m^3].
                if (!trap_mask_.empty() && idx < trap_mask_.size() && trap_mask_[idx]) {
                    const real_t kT_eV = VT_; // configured thermal energy in eV
                    real_t f_t = TCAD_CONST(1.0) / (TCAD_CONST(1.0) +
                        exp_q((trap_E_t_ - phi[idx]) / kT_eV));
                    real_t D_it_m2 = trap_D_it_ * TCAD_CONST(1.0e4);
                    const real_t thickness = trap_layer_thickness_ > TCAD_CONST(0.0)
                        ? trap_layer_thickness_ : g_.dx;
                    real_t Q_it = -QE * D_it_m2 * (f_t - TCAD_CONST(0.5)) / thickness;
                    rhs_poisson += Q_it;   // physical rho in F = A*phi + rho - div(P)
                }
                if (!Q_ot_.empty() && idx < Q_ot_.size()) {
                    rhs_poisson += Q_ot_[idx];
                }
                F[phi_idx(idx)] = rhs_poisson;
            }
        }
    }

    // --- Electron continuity residual ---
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (n_bc_.count(idx)) {
                    // Ohmic contact: n follows phi via Boltzmann relation
                    // n = ni*exp((phi-EFn)/VT).  This replaces the Dirichlet
                    // n=NSD BC with a self-consistent coupling.
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        real_t EFn = ohmic_EFn_.count(idx) ? ohmic_EFn_.at(idx) : TCAD_CONST(0.0);
                        real_t ni_local = ohmic_ni_;
                        real_t arg = (phi[idx] - EFn) / VT_;
                        if (arg > TCAD_CONST(50.0)) arg = TCAD_CONST(50.0);
                        if (arg < -TCAD_CONST(50.0)) arg = -TCAD_CONST(50.0);
                        real_t n_target = ni_local * exp_q(arg);
                        if (opt_.use_log_space) {
                            F[n_idx(idx)] = x[n_idx(idx)] - log_q(n_target);
                        } else {
                            F[n_idx(idx)] = n[idx] - n_target;
                        }
                    } else if (opt_.use_log_space) {
                        // A legal zero-density contact needs the same finite
                        // log floor as solve()'s initial state conversion.
                        F[n_idx(idx)] = x[n_idx(idx)] -
                            log_q(std::max(n_bc_.at(idx), TCAD_CONST(1e-300)));
                    } else {
                        F[n_idx(idx)] = n[idx] - n_bc_.at(idx);
                    }
                    continue;
                }
                if (!inactive_n_.empty() && inactive_n_[idx]) {
                    F[n_idx(idx)] = TCAD_CONST(0.0);
                    continue;
                }
                if (opt_.freeze_n) {
                    // Frozen-n mode: pin n to its current value.  See
                    // NewtonOptions::freeze_n / audit §17.
                    F[n_idx(idx)] = TCAD_CONST(0.0);
                    continue;
                }
                if (mu_n_[idx] < EPSILON) {
                    // Insulator: pin carriers to the same global numerical
                    // floor used by Gummel and by the linear-space positivity
                    // clamp.  The former hard-coded 1e-30 target disagreed
                    // with EPSILON=1e-20 by ten decades, so every oxide node
                    // entered log-Newton with an artificial residual ln(1e10)
                    // and dominated the line-search merit.
                    if (opt_.use_log_space) {
                        F[n_idx(idx)] = x[n_idx(idx)] - log_q(EPSILON);
                    } else {
                        F[n_idx(idx)] = n[idx] - EPSILON;
                    }
                    continue;
                }
                real_t center = TCAD_CONST(0.0), flux_sum = TCAD_CONST(0.0);
                const real_t w_y = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 1, mu_n_);
                const real_t w_z = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 2, mu_n_);
                auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                    if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = (phi[nbr] + Qn_dg[nbr]) - (phi[idx] + Qn_dg[idx]);
                    real_t B_minus = bernoulli(-dphi / VT_);
                    real_t B_plus = bernoulli(dphi / VT_);
                    // Edge mobility: HARMONIC mean (current conservation fix,
                    // see gummel_solver.cpp electron block comment).
                    real_t mu_e = TCAD_CONST(2.0) * mu_n_[idx] * mu_n_[nbr] / (mu_n_[idx] + mu_n_[nbr] + TCAD_CONST(1e-30));
                    // High-field saturation (must mirror the Gummel edge and
                    // the current post-processing, otherwise Newton-primary
                    // solves are inconsistent with terminal-current HFS and
                    // the electrothermal KCL gate rejects every state).
                    if (opt_.hfs_enabled) {
                        real_t force;
                        if (hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, n_bc_.count(idx) || n_bc_.count(nbr)) == 1) {
                            force = abs_q(dphi) / dx;
                        } else {
                            real_t efn_i = (phi[idx] + Qn_dg[idx])
                                - VT_ * log_q(hfs_reference_carrier(n[idx], opt_.hfs_refdens_n) / std::max(Nc_[idx], TCAD_CONST(1.0)));
                            real_t efn_j = (phi[nbr] + Qn_dg[nbr])
                                - VT_ * log_q(hfs_reference_carrier(n[nbr], opt_.hfs_refdens_n) / std::max(Nc_[nbr], TCAD_CONST(1.0)));
                            force = abs_q(efn_j - efn_i) / dx;
                        }
                        force = hfs_active_driving_force(force, opt_.hfs_low_field_cutoff);
                        real_t ratio = mu_e * force / opt_.hfs_vsat_n;
                        if (ratio > TCAD_CONST(1.0e-12)) {
                            real_t b = opt_.hfs_beta_n;
                            mu_e /= pow_q(TCAD_CONST(1.0) + pow_q(ratio, b), TCAD_CONST(1.0) / b);
                        }
                    }
                    // Face-area weighting (see gummel_solver.cpp comment).
                    real_t D = w * mu_e * VT_ / dx;
                    real_t a_ii = D * B_minus;
                    real_t a_ij = -D * B_plus;
                    center += a_ii;
                    flux_sum += a_ij * n[nbr];
                    return a_ii;
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), TCAD_CONST(1.0));
                if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), TCAD_CONST(1.0));
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                real_t R = TCAD_CONST(0.0), dRdn, dRdp;
                compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : TCAD_CONST(0.0);
                if (opt_.enable_btbt) {
                    G += opt_.btbt_continuity_scale * compute_btbt_at(phi, idx);
                }
                if (opt_.enable_ii)   G += compute_ii_at(phi, n, p, idx, Qn_dg.data(), Qp_dg.data());
                real_t source_scale = g_.dx_cell(i);
                F[n_idx(idx)] = center * n[idx] + flux_sum - (G - R) * source_scale;
                // Backward-Euler transient term: +(n - n_prev)/dt * dx.
                //
                // The whole carrier residual is in CELL-INTEGRATED units [m^-2 s^-1]:
                // the SG flux  center*n  (center = mu*VT/dx [m/s]) is m^-2 s^-1, and
                // the source (G-R)*dx is m^-2 s^-1.  The BE rate (n-n_prev)/dt is
                // [m^-3 s^-1], so it MUST be multiplied by the same source_scale=dx
                // to be dimensionally consistent.  (The Gummel path at
                // gummel_solver.cpp:336 has this dx scaling; audit §14's claim that
                // "source_scale=dx makes BE too weak" was backwards — without dx the
                // BE term is ~1e8x too strong and over-pins n=n_prev.)  With the
                // correct scaling the BE diagonal dx/dt ~ 1e3 sits below the SRH
                // source R*dx ~ 1e9, giving the expected slow multi-step relaxation.
                if (opt_.transient_enabled && idx < opt_.n_prev.size()) {
                    F[n_idx(idx)] += (n[idx] - opt_.n_prev[idx]) / opt_.transient_dt * source_scale;
                }
            }
        }
    }

    // --- Hole continuity residual ---
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (p_bc_.count(idx)) {
                    // Ohmic: p follows phi via Boltzmann p = ni*exp(-(phi+EFp)/VT)
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        real_t EFp = ohmic_EFp_.count(idx) ? ohmic_EFp_.at(idx) : TCAD_CONST(0.0);
                        real_t arg = -(phi[idx] + EFp) / VT_;
                        if (arg > TCAD_CONST(50.0)) arg = TCAD_CONST(50.0);
                        if (arg < -TCAD_CONST(50.0)) arg = -TCAD_CONST(50.0);
                        real_t p_target = ohmic_ni_ * exp_q(arg);
                        if (opt_.use_log_space) {
                            F[p_idx(idx)] = x[p_idx(idx)] - log_q(p_target);
                        } else {
                            F[p_idx(idx)] = p[idx] - p_target;
                        }
                    } else if (opt_.use_log_space) {
                        F[p_idx(idx)] = x[p_idx(idx)] -
                            log_q(std::max(p_bc_.at(idx), TCAD_CONST(1e-300)));
                    } else {
                        F[p_idx(idx)] = p[idx] - p_bc_.at(idx);
                    }
                    continue;
                }
                if (!inactive_p_.empty() && inactive_p_[idx]) {
                    F[p_idx(idx)] = TCAD_CONST(0.0);
                    continue;
                }
                if (opt_.freeze_p) {
                    F[p_idx(idx)] = TCAD_CONST(0.0);
                    continue;
                }
                if (mu_p_[idx] < EPSILON) {
                    if (opt_.use_log_space) {
                        F[p_idx(idx)] = x[p_idx(idx)] - log_q(EPSILON);
                    } else {
                        F[p_idx(idx)] = p[idx] - EPSILON;
                    }
                    continue;
                }
                real_t center = TCAD_CONST(0.0), flux_sum = TCAD_CONST(0.0);
                const real_t w_y = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 1, mu_p_);
                const real_t w_z = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 2, mu_p_);
                auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                    if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = (phi[nbr] - Qp_dg[nbr]) - (phi[idx] - Qp_dg[idx]);
                    real_t B_plus = bernoulli(dphi / VT_);
                    real_t B_minus = bernoulli(-dphi / VT_);
                    // Edge mobility: HARMONIC mean (current conservation fix).
                    real_t mu_e = TCAD_CONST(2.0) * mu_p_[idx] * mu_p_[nbr] / (mu_p_[idx] + mu_p_[nbr] + TCAD_CONST(1e-30));
                    // High-field saturation (hole edge; see electron block).
                    if (opt_.hfs_enabled) {
                        real_t force;
                        if (hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, p_bc_.count(idx) || p_bc_.count(nbr)) == 1) {
                            force = abs_q(dphi) / dx;
                        } else {
                            real_t efp_i = (phi[idx] - Qp_dg[idx])
                                + VT_ * log_q(hfs_reference_carrier(p[idx], opt_.hfs_refdens_p) / std::max(Nv_[idx], TCAD_CONST(1.0)));
                            real_t efp_j = (phi[nbr] - Qp_dg[nbr])
                                + VT_ * log_q(hfs_reference_carrier(p[nbr], opt_.hfs_refdens_p) / std::max(Nv_[nbr], TCAD_CONST(1.0)));
                            force = abs_q(efp_j - efp_i) / dx;
                        }
                        force = hfs_active_driving_force(force, opt_.hfs_low_field_cutoff);
                        real_t ratio = mu_e * force / opt_.hfs_vsat_p;
                        if (ratio > TCAD_CONST(1.0e-12)) {
                            real_t b = opt_.hfs_beta_p;
                            mu_e /= pow_q(TCAD_CONST(1.0) + pow_q(ratio, b), TCAD_CONST(1.0) / b);
                        }
                    }
                    real_t D = w * mu_e * VT_ / dx;
                    real_t a_ii = D * B_plus;
                    real_t a_ij = -D * B_minus;
                    center += a_ii;
                    flux_sum += a_ij * p[nbr];
                    return a_ii;
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), TCAD_CONST(1.0));
                if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), TCAD_CONST(1.0));
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                real_t R = TCAD_CONST(0.0), dRdn, dRdp;
                compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : TCAD_CONST(0.0);
                if (opt_.enable_btbt) {
                    G += opt_.btbt_continuity_scale * compute_btbt_at(phi, idx);
                }
                if (opt_.enable_ii)   G += compute_ii_at(phi, n, p, idx, Qn_dg.data(), Qp_dg.data());
                real_t source_scale = g_.dx_cell(i);
                F[p_idx(idx)] = center * p[idx] + flux_sum - (G - R) * source_scale;
                // Backward-Euler transient term (see electron block above):
                // scaled by source_scale=dx for dimensional consistency.
                if (opt_.transient_enabled && idx < opt_.p_prev.size()) {
                    F[p_idx(idx)] += (p[idx] - opt_.p_prev[idx]) / opt_.transient_dt * source_scale;
                }
            }
        }
    }
}


void NewtonSolver::assemble_jacobian(const std::vector<real_t>& x, SparseMatrix& J) {
    const size_t N = g_.npts();
    J = SparseMatrix(3 * N);

    const real_t* phi = x.data();
    refresh_lk_polarization(phi);
    if(lk_material_field_ && lk_material_derivative_.empty())
        lk_material_derivative_=lk_material_susceptibility_lines(g_,eps_,fe_mask_,fe_polarization_,
            lk_alpha_,lk_beta_,lk_gamma_/opt_.transient_dt,lk_depol_eps_,lk_axis_,lk_material_axis_);
    // Linearise carrier blocks for log-space (see assemble_residual).  The
    // chain rule turns every dF/dn into dF/du = dF/dn * n (and dF/dp into
    // dF/dv = dF/dp * p).  See audit §18.
    std::vector<real_t> n_lin, p_lin;
    const real_t* n;
    const real_t* p;
    if (opt_.use_log_space) {
        n_lin.resize(N);
        p_lin.resize(N);
        const real_t* u = x.data() + N;
        const real_t* v = x.data() + 2 * N;
        for (size_t i = 0; i < N; ++i) {
            n_lin[i] = exp_q(u[i]);
            p_lin[i] = exp_q(v[i]);
        }
        n = n_lin.data();
        p = p_lin.data();
    } else {
        n = x.data() + N;
        p = x.data() + 2 * N;
    }

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], opt_.temperature, Nc_[i], Nv_[i], opt_.statistics_type);
    }

    // Evaluate the lagged DG transport potential at the same state as the
    // residual.  dQ/dn is intentionally omitted (Picard/Newton hybrid), but
    // Bernoulli coefficients must use phi+/-Q for a consistent descent step.
    std::vector<real_t> Qn_dg(N, TCAD_CONST(0.0)), Qp_dg(N, TCAD_CONST(0.0));
    if (opt_.enable_quantum && !semi_mask_.empty() &&
        use_lagged_quantum_potential_ && lagged_Qn_.size() == N &&
        lagged_Qp_.size() == N) {
        Qn_dg = lagged_Qn_;
        Qp_dg = lagged_Qp_;
    } else if (opt_.enable_quantum && !semi_mask_.empty()) {
        DensityGradient dg_tmp(g_);
        dg_tmp.set_coefficients(dg_bn_, dg_bp_);
        dg_tmp.set_silicon_multivalley(
            dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
            dg_silicon_subbands_);
        dg_tmp.set_interface_distance_factor(dg_interface_distance_factor_);
        dg_tmp.set_step_boundary(
            dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
            dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
            dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
            dg_step_h_theta_);
        dg_tmp.set_semiconductor_mask(semi_mask_);
        dg_tmp.set_thermal_voltage(VT_);
        dg_tmp.quantum_potential(std::vector<real_t>(n, n + N),
                                 std::vector<real_t>(p, p + N),
                                 Qn_dg, Qp_dg);
    }
    if (opt_.enable_quantum && !semi_mask_.empty()) {
        detail::pin_quantum_contacts(n_bc_, p_bc_, Qn_dg, Qp_dg);
    }

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                size_t i_phi = phi_idx(idx);
                size_t i_n = n_idx(idx);
                size_t i_p = p_idx(idx);

                // Dirichlet BC rows: identity
                if (phi_bc_.count(idx)) {
                    J.add_entry(i_phi, i_phi, TCAD_CONST(1.0));
                } else if (opt_.freeze_phi) {
                    // Frozen-phi: identity row, no phi<>carrier coupling.
                    J.add_entry(i_phi, i_phi, TCAD_CONST(1.0));
                } else {
                    // Poisson row
                    real_t center = TCAD_CONST(0.0);
                    auto add_link = [&](size_t nbr, real_t edge_cell,
                                        const std::vector<real_t>& edge_values) {
                        real_t eps_avg = edge_epsilon(idx, nbr, edge_values);
                        real_t c = eps_avg / edge_cell;
                        center += c;
                        J.add_entry(i_phi, phi_idx(nbr), c);
                    };
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i) * g_.dx_cell(i), edge_eps_x_plus_);
                    if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1) * g_.dx_cell(i), edge_eps_x_minus_);
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j) * g_.dy_cell(j), edge_eps_y_plus_);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1) * g_.dy_cell(j), edge_eps_y_minus_);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k) * g_.dz_cell(k), edge_eps_z_plus_);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz_edge(k-1) * g_.dz_cell(k), edge_eps_z_minus_);
                    J.add_entry(i_phi, i_phi, -center);
                    add_lk_jacobian_row(J, i, j, k);
                    if (!trap_mask_.empty() && idx < trap_mask_.size() &&
                        trap_mask_[idx]) {
                        const real_t kT_eV = VT_; // configured thermal energy in eV
                        const real_t f_t = TCAD_CONST(1.0) / (TCAD_CONST(1.0) +
                            exp_q((trap_E_t_ - phi[idx]) / kT_eV));
                        const real_t thickness = trap_layer_thickness_ > TCAD_CONST(0.0)
                            ? trap_layer_thickness_ : g_.dx;
                        // Derivative of physical Q_it in the Poisson residual.
                        J.add_entry(i_phi, i_phi,
                            -QE * trap_D_it_ * TCAD_CONST(1.0e4) * f_t * (TCAD_CONST(1.0) - f_t) /
                            (thickness * kT_eV));
                    }
                    // Poisson<>carrier coupling.  Chain rule in log-space:
                    // dF/du = dF/dn * n, dF/dv = dF/dp * p.  See audit §18.
                    if (opt_.use_log_space) {
                        J.add_entry(i_phi, i_n,
                                    -QE * charge_volume_fraction_[idx] * n[idx]);
                        J.add_entry(i_phi, i_p,
                                     QE * charge_volume_fraction_[idx] * p[idx]);
                    } else {
                        J.add_entry(i_phi, i_n,
                                    -QE * charge_volume_fraction_[idx]);
                        J.add_entry(i_phi, i_p,
                                     QE * charge_volume_fraction_[idx]);
                    }
                }

                if (n_bc_.count(idx)) {
                    J.add_entry(i_n, i_n, TCAD_CONST(1.0));
                    // Ohmic: n follows phi, dF[n]/d[phi] = -1/VT
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        J.add_entry(i_n, i_phi, -TCAD_CONST(1.0) / VT_);
                    }
                } else if (!inactive_n_.empty() && inactive_n_[idx]) {
                    J.add_entry(i_n, i_n, TCAD_CONST(1.0));
                } else if (opt_.freeze_n) {
                    J.add_entry(i_n, i_n, TCAD_CONST(1.0));
                } else if (mu_n_[idx] < EPSILON) {
                    J.add_entry(i_n, i_n, TCAD_CONST(1.0));
                } else {
                    // Electron continuity row.
                    // Log-space chain rule (audit §18): dF/du = dF/dn * n,
                    // dF/dv = dF/dp * p.  Phi derivatives are unchanged (phi is
                    // not log-transformed).  sn/sp are the self-node scales.
                    real_t sn = opt_.use_log_space ? n[idx] : TCAD_CONST(1.0);
                    real_t sp = opt_.use_log_space ? p[idx] : TCAD_CONST(1.0);
                    real_t center = TCAD_CONST(0.0);
                    real_t dF_dphi_i = TCAD_CONST(0.0);
                    const real_t w_y = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 1, mu_n_);
                    const real_t w_z = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 2, mu_n_);
                    auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                        if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                        real_t dphi = (phi[nbr] + Qn_dg[nbr]) -
                                         (phi[idx] + Qn_dg[idx]);
                        real_t x_val = dphi / VT_;
                        real_t B_minus = bernoulli(-x_val);
                        real_t B_plus = bernoulli(x_val);
                        // Edge mobility: HARMONIC mean (matches residual).
                        real_t mu_e = TCAD_CONST(2.0) * mu_n_[idx] * mu_n_[nbr] / (mu_n_[idx] + mu_n_[nbr] + TCAD_CONST(1e-30));
                        // HFS reduction with ANALYTIC dmu coupling (A15):
                        // - electric_field driving: force = |dphi|/dx, the
                        //   derivative lands in the PHI columns and is
                        //   merged into dflux_dphi_{i,j}.
                        // - grad_quasi_fermi driving: force = |Efn_j-Efn_i|/dx
                        //   with Efn = phi+Q-VT*ln(n/Nc); in log-space the
                        //   derivative lands in the U (=log n) columns:
                        //   dforce/du_j = -sign*VT/dx, dforce/du_i =
                        //   +sign*VT/dx; merged into the carrier entries.
                        real_t mu0_edge = mu_e;
                        real_t dmu_dF = TCAD_CONST(0.0);
                        real_t force_sign = TCAD_CONST(0.0);
                        if (opt_.hfs_enabled) {
                            real_t force;
                            if (hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, n_bc_.count(idx) || n_bc_.count(nbr)) == 1) {
                                force = abs_q(dphi) / dx;
                                force_sign = (dphi >= TCAD_CONST(0.0)) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                            } else {
                                real_t efn_i = (phi[idx] + Qn_dg[idx])
                                    - VT_ * log_q(hfs_reference_carrier(n[idx], opt_.hfs_refdens_n) / std::max(Nc_[idx], TCAD_CONST(1.0)));
                                real_t efn_j = (phi[nbr] + Qn_dg[nbr])
                                    - VT_ * log_q(hfs_reference_carrier(n[nbr], opt_.hfs_refdens_n) / std::max(Nc_[nbr], TCAD_CONST(1.0)));
                                force = abs_q(efn_j - efn_i) / dx;
                                force_sign = (efn_j - efn_i >= TCAD_CONST(0.0)) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                            }
                            force = hfs_active_driving_force(force, opt_.hfs_low_field_cutoff);
                            real_t ratio = mu_e * force / opt_.hfs_vsat_n;
                            if (ratio > TCAD_CONST(1.0e-12)) {
                                real_t b = opt_.hfs_beta_n;
                                mu_e /= pow_q(TCAD_CONST(1.0) + pow_q(ratio, b), TCAD_CONST(1.0) / b);
                                real_t rb = pow_q(ratio, b);
                                dmu_dF = -(mu0_edge * mu0_edge
                                           / opt_.hfs_vsat_n)
                                    * pow_q(ratio, b - TCAD_CONST(1.0))
                                    * pow_q(TCAD_CONST(1.0) + rb, -TCAD_CONST(1.0) / b - TCAD_CONST(1.0));
                            }
                        }
                        real_t D = w * mu_e * VT_ / dx;
                        real_t a_ii = D * B_minus;
                        real_t a_ij = -D * B_plus;
                        // GQF coupling corrections to the U columns
                        // (electron edge): dflux/du_k += dD/du_k*edge_carrier
                        // with dD/du_k = (w*VT/dx)*dmu_dF*(dforce/du_k).
                        real_t gqf_ij_corr = TCAD_CONST(0.0);
                        if (dmu_dF != TCAD_CONST(0.0) && hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, n_bc_.count(idx) || n_bc_.count(nbr)) == 0) {
                            real_t edge_carrier =
                                n[idx] * B_minus - n[nbr] * B_plus;
                            real_t base = (w * VT_ / dx) * dmu_dF
                                * (-force_sign * VT_ / dx);
                            gqf_ij_corr = base * edge_carrier;
                            gqf_ij_corr = hfs_reference_chain(gqf_ij_corr, n[nbr], opt_.hfs_refdens_n, opt_.use_log_space);
                        }
                        center += a_ii;
                        real_t nbr_scale = opt_.use_log_space ? n[nbr] : TCAD_CONST(1.0);
                        J.add_entry(i_n, n_idx(nbr),
                                    a_ij * nbr_scale + gqf_ij_corr);
                        real_t gqf_ii_corr = TCAD_CONST(0.0);
                        if (dmu_dF != TCAD_CONST(0.0) && hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, n_bc_.count(idx) || n_bc_.count(nbr)) == 0) {
                            // u_i column (center): dforce/du_i = +sign*VT/dx.
                            // Added as its OWN entry: `center` is multiplied
                            // by the log-space chain scale sn downstream, but
                            // this term is already dF/du (direct).
                            real_t edge_carrier =
                                n[idx] * B_minus - n[nbr] * B_plus;
                            gqf_ii_corr = (w * VT_ / dx) * dmu_dF
                                * (force_sign * VT_ / dx) * edge_carrier;
                            gqf_ii_corr = hfs_reference_chain(gqf_ii_corr, n[idx], opt_.hfs_refdens_n, opt_.use_log_space);
                            J.add_entry(i_n, i_n, gqf_ii_corr);
                        }
                        // phi derivatives with the A15 merged mobility
                        // coupling (electric_field driving only):
                        // d/dphi_k [ D(phi) * (n_i*Bm - n_j*Bp) ]
                        //   = Bernoulli part  +  dD/dphi_k * edge_carrier.
                        real_t dBm = d_bernoulli_dx(-x_val);
                        real_t dBp = d_bernoulli_dx(x_val);
                        real_t dflux_dphi_i = D / VT_ * (n[idx] * dBm + n[nbr] * dBp);
                        real_t dflux_dphi_j = -D / VT_ * (n[idx] * dBm + n[nbr] * dBp);
                        if (dmu_dF != TCAD_CONST(0.0)) {
                            // PHI-column coupling: dEfn/dphi = 1 in BOTH
                            // driving modes (the GQF force contains phi),
                            // so this is not electric_field-only.  A16b:
                            // omitting it for GQF left F[n] d/dphi entries
                            // 7-15% wrong at the depletion edges -- the
                            // residual Jacobian error that stalls Newton.
                            real_t edge_carrier =
                                n[idx] * B_minus - n[nbr] * B_plus;
                            real_t dD_dF = (w * VT_ / (dx * dx)) * dmu_dF;
                            dflux_dphi_i += -force_sign * dD_dF * edge_carrier;
                            dflux_dphi_j += force_sign * dD_dF * edge_carrier;
                        }
                        dF_dphi_i += dflux_dphi_i;
                        J.add_entry(i_n, phi_idx(nbr), dflux_dphi_j);
                        return a_ii;
                    };
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), TCAD_CONST(1.0));
                    if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), TCAD_CONST(1.0));
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                    // Self carrier column scaled by sn; phi column unscaled.
                    J.add_entry(i_n, i_n, center * sn);
                    J.add_entry(i_n, i_phi, dF_dphi_i);
                    real_t R, dRdn, dRdp;
                    compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                    real_t source_scale = g_.dx_cell(i);
                    J.add_entry(i_n, i_n, dRdn * source_scale * sn);
                    J.add_entry(i_n, i_p, dRdp * source_scale * sp);
                    if (opt_.enable_btbt)
                        add_btbt_jacobian_row(J, i_n, g_, opt_, phi, idx,
                            compute_btbt_at(phi, idx), source_scale, Eg_[idx]);
                    add_ii_jacobian_row(
                        J, i_n, phi, n, p, idx, source_scale, Qn_dg.data(), Qp_dg.data());
                    // BE transient: d[(n-n_prev)/dt*dx]/dn = +dx/dt; in log-space
                    // d/du = +dx/dt * n.  See audit §18.
                    if (opt_.transient_enabled) {
                        J.add_entry(i_n, i_n, source_scale / opt_.transient_dt * sn);
                    }
                }

                if (p_bc_.count(idx)) {
                    J.add_entry(i_p, i_p, TCAD_CONST(1.0));
                    // Ohmic: p follows phi, dF[p]/d[phi] = +1/VT
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        J.add_entry(i_p, i_phi, TCAD_CONST(1.0) / VT_);
                    }
                } else if (!inactive_p_.empty() && inactive_p_[idx]) {
                    J.add_entry(i_p, i_p, TCAD_CONST(1.0));
                } else if (opt_.freeze_p) {
                    J.add_entry(i_p, i_p, TCAD_CONST(1.0));
                } else if (mu_p_[idx] < EPSILON) {
                    J.add_entry(i_p, i_p, TCAD_CONST(1.0));
                } else {
                    // Hole continuity row.  Log-space chain rule (audit §18):
                    // dF/du = dF/dn * n, dF/dv = dF/dp * p.  sn/sp self scales.
                    real_t sn = opt_.use_log_space ? n[idx] : TCAD_CONST(1.0);
                    real_t sp = opt_.use_log_space ? p[idx] : TCAD_CONST(1.0);
                    real_t center = TCAD_CONST(0.0);
                    real_t dF_dphi_i = TCAD_CONST(0.0);
                    const real_t w_y = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 1, mu_p_);
                    const real_t w_z = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 2, mu_p_);
                    auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                        if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                        real_t dphi = (phi[nbr] - Qp_dg[nbr]) -
                                         (phi[idx] - Qp_dg[idx]);
                        real_t x_val = dphi / VT_;
                        real_t B_plus = bernoulli(x_val);
                        real_t B_minus = bernoulli(-x_val);
                        // Edge mobility: HARMONIC mean (matches residual).
                        real_t mu_e = TCAD_CONST(2.0) * mu_p_[idx] * mu_p_[nbr] / (mu_p_[idx] + mu_p_[nbr] + TCAD_CONST(1e-30));
                        // A15 merged analytic dmu coupling (holes; see the
                        // electron site for the full derivation -- GQF
                        // driving lands in the V (=log p) columns).
                        real_t mu0_edge = mu_e;
                        real_t dmu_dF = TCAD_CONST(0.0);
                        real_t force_sign = TCAD_CONST(0.0);
                        if (opt_.hfs_enabled) {
                            real_t force;
                            if (hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, p_bc_.count(idx) || p_bc_.count(nbr)) == 1) {
                                force = abs_q(dphi) / dx;
                                force_sign = (dphi >= TCAD_CONST(0.0)) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                            } else {
                                real_t efp_i = (phi[idx] - Qp_dg[idx])
                                    + VT_ * log_q(hfs_reference_carrier(p[idx], opt_.hfs_refdens_p) / std::max(Nv_[idx], TCAD_CONST(1.0)));
                                real_t efp_j = (phi[nbr] - Qp_dg[nbr])
                                    + VT_ * log_q(hfs_reference_carrier(p[nbr], opt_.hfs_refdens_p) / std::max(Nv_[nbr], TCAD_CONST(1.0)));
                                force = abs_q(efp_j - efp_i) / dx;
                                force_sign = (efp_j - efp_i >= TCAD_CONST(0.0)) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                            }
                            force = hfs_active_driving_force(force, opt_.hfs_low_field_cutoff);
                            real_t ratio = mu_e * force / opt_.hfs_vsat_p;
                            if (ratio > TCAD_CONST(1.0e-12)) {
                                real_t b = opt_.hfs_beta_p;
                                mu_e /= pow_q(TCAD_CONST(1.0) + pow_q(ratio, b), TCAD_CONST(1.0) / b);
                                real_t rb = pow_q(ratio, b);
                                dmu_dF = -(mu0_edge * mu0_edge
                                           / opt_.hfs_vsat_p)
                                    * pow_q(ratio, b - TCAD_CONST(1.0))
                                    * pow_q(TCAD_CONST(1.0) + rb, -TCAD_CONST(1.0) / b - TCAD_CONST(1.0));
                            }
                        }
                        real_t D = w * mu_e * VT_ / dx;
                        real_t a_ii = D * B_plus;
                        real_t a_ij = -D * B_minus;
                        // GQF coupling corrections to the V columns (holes):
                        // Efp = phi - Q + VT*ln(p/Nv) -> dEfp/dv = +VT.
                        real_t gqf_ij_corr = TCAD_CONST(0.0);
                        if (dmu_dF != TCAD_CONST(0.0) && hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, p_bc_.count(idx) || p_bc_.count(nbr)) == 0) {
                            real_t edge_carrier =
                                p[idx] * B_plus - p[nbr] * B_minus;
                            real_t base = (w * VT_ / dx) * dmu_dF
                                * (force_sign * VT_ / dx);
                            gqf_ij_corr = base * edge_carrier;
                            gqf_ij_corr = hfs_reference_chain(gqf_ij_corr, p[nbr], opt_.hfs_refdens_p, opt_.use_log_space);
                        }
                        center += a_ii;
                        real_t nbr_scale = opt_.use_log_space ? p[nbr] : TCAD_CONST(1.0);
                        J.add_entry(i_p, p_idx(nbr),
                                    a_ij * nbr_scale + gqf_ij_corr);
                        if (dmu_dF != TCAD_CONST(0.0) && hfs_edge_driving(opt_.hfs_driving, opt_.hfs_qf_at_contacts, p_bc_.count(idx) || p_bc_.count(nbr)) == 0) {
                            // v_i column: Efp = phi - Q + VT*ln(p/Nv) ->
                            // dEfp/dv = +VT; own entry (not via center*sp).
                            real_t edge_carrier =
                                p[idx] * B_plus - p[nbr] * B_minus;
                            real_t gqf_ii_corr = (w * VT_ / dx) * dmu_dF
                                * (-force_sign * VT_ / dx) * edge_carrier;
                            gqf_ii_corr = hfs_reference_chain(gqf_ii_corr, p[idx], opt_.hfs_refdens_p, opt_.use_log_space);
                            J.add_entry(i_p, i_p, gqf_ii_corr);
                        }
                        // phi derivatives with the A15 merged mobility
                        // coupling (electric_field driving; hole signs).
                        real_t dBp = d_bernoulli_dx(x_val);
                        real_t dBm = d_bernoulli_dx(-x_val);
                        real_t dflux_dphi_i = -D / VT_ * (p[idx] * dBp + p[nbr] * dBm);
                        real_t dflux_dphi_j = D / VT_ * (p[idx] * dBp + p[nbr] * dBm);
                        if (dmu_dF != TCAD_CONST(0.0)) {
                            // PHI-column coupling (A16b): dEfp/dphi = 1 in
                            // BOTH driving modes.  NOTE the coupling-term
                            // sign is carrier-type-INDEPENDENT (unlike the
                            // Bernoulli base terms): dD/dphi_k is the same
                            // physical derivative for electrons and holes,
                            // so the pattern matches the electron site.
                            real_t edge_carrier =
                                p[idx] * B_plus - p[nbr] * B_minus;
                            real_t dD_dF = (w * VT_ / (dx * dx)) * dmu_dF;
                            dflux_dphi_i += -force_sign * dD_dF * edge_carrier;
                            dflux_dphi_j += force_sign * dD_dF * edge_carrier;
                        }
                        dF_dphi_i += dflux_dphi_i;
                        J.add_entry(i_p, phi_idx(nbr), dflux_dphi_j);
                        return a_ii;
                    };
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), TCAD_CONST(1.0));
                    if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), TCAD_CONST(1.0));
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                    J.add_entry(i_p, i_p, center * sp);
                    J.add_entry(i_p, i_phi, dF_dphi_i);
                    real_t R, dRdn, dRdp;
                    compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                    real_t source_scale = g_.dx_cell(i);
                    J.add_entry(i_p, i_n, dRdn * source_scale * sn);
                    J.add_entry(i_p, i_p, dRdp * source_scale * sp);
                    if (opt_.enable_btbt)
                        add_btbt_jacobian_row(J, i_p, g_, opt_, phi, idx,
                            compute_btbt_at(phi, idx), source_scale, Eg_[idx]);
                    add_ii_jacobian_row(
                        J, i_p, phi, n, p, idx, source_scale, Qn_dg.data(), Qp_dg.data());
                    // BE transient: d[(p-p_prev)/dt*dx]/dp = +dx/dt; in log-space
                    // d/dv = +dx/dt * p.  See audit §18.
                    if (opt_.transient_enabled) {
                        J.add_entry(i_p, i_p, source_scale / opt_.transient_dt * sp);
                    }
                }
            }
        }
    }
    J.finalize();
}

bool NewtonSolver::solve(std::vector<real_t>& phi,
                         std::vector<real_t>& n,
                         std::vector<real_t>& p) {
    validate_newton_inputs(g_.npts(), phi, n, p, Nc_, Nv_, Eg_);
    if(opt_.enable_ii && opt_.ii_driving==1) {
        validate_ii_gqf_geometry(g_,lk_coupled_ || std::any_of(fe_mask_.begin(),fe_mask_.end(),[](char v){return v!=0;}));
        validate_ii_gqf_material(g_.npts(),Nc_,Nv_,Eg_,mu_n_,mu_p_);
    }
    if (active_hfs_reference(opt_.hfs_enabled,opt_.hfs_driving,opt_.hfs_refdens_n,opt_.hfs_refdens_p)) {
        validate_hfs_reference_geometry(g_,lk_coupled_ || std::any_of(fe_mask_.begin(),fe_mask_.end(),[](char v){return v!=0;}));
        validate_hfs_reference_material(g_.npts(),Nc_,Nv_,Eg_,mu_n_,mu_p_);
    }
    residuals_.clear();
    nonlinear_samples_.clear();
    const size_t N = g_.npts();
    const bool classical_steady =
        !opt_.transient_enabled && !opt_.enable_quantum &&
        !opt_.freeze_phi && !opt_.freeze_n && !opt_.freeze_p &&
        opt_.statistics_type == StatisticsType::BOLTZMANN;
    const bool classical_qf_trust = opt_.use_log_space && classical_steady;
    auto finite_values = [](const std::vector<real_t>& values) {
        return std::all_of(values.begin(), values.end(), [](real_t value) {
            return std::isfinite((double)value);
        });
    };
    if (!finite_values(phi) || !finite_values(n) || !finite_values(p)) {
        std::cerr << "Newton rejected non-finite initial state\n";
        return false;
    }
    // A zero mobile population has no finite logarithmic coordinate. Mapping
    // it to 1e-300 makes dF/dlog(n)=n*dF/dn effectively singular: even a
    // finite generation source can require a correction above DBL_MAX, or
    // a clipped log step can leave the residual unchanged for every trial.
    // Bootstrap this classical 1-D entry state in physical density coordinates.
    // The copy retains every material/source/contact and the same tolerances;
    // its residual, linear backward-error and KCL gates still decide success.
    // Keep the configured coordinate policy on this object for later solves.
    bool zero_mobile_population = false;
    bool tiny_mobile_population = false;
    const bool classical_1d = classical_steady &&
        int(g_.nx > 1) + int(g_.ny > 1) + int(g_.nz > 1) == 1;
    if (classical_1d) {
        for (size_t i = 0; i < N; ++i) {
            if (ohmic_nodes_.count(i)) continue;
            zero_mobile_population = zero_mobile_population ||
                (!n_bc_.count(i) && mu_n_[i] >= EPSILON && n[i] == TCAD_CONST(0.0)) ||
                (!p_bc_.count(i) && mu_p_[i] >= EPSILON && p[i] == TCAD_CONST(0.0));
            // Use the same unit density reference as the linear-density
            // merit below. A numerical EPSILON cutoff misses depleted seeds
            // above 1e-20 that still cannot advance under log trust clipping.
            tiny_mobile_population = tiny_mobile_population ||
                (!n_bc_.count(i) && mu_n_[i] >= EPSILON && n[i] > TCAD_CONST(0.0) && n[i] < TCAD_CONST(1.0)) ||
                (!p_bc_.count(i) && mu_p_[i] >= EPSILON && p[i] > TCAD_CONST(0.0) && p[i] < TCAD_CONST(1.0));
        }
    }
    // Additive classical startup must resolve the actual generated density,
    // including a solution below EPSILON. A unit-density error reference can
    // otherwise accept an unchanged zero state or repeatedly re-enter log
    // recovery without making progress. Also support direct additive solves
    // of this same small-population problem; no hidden option is required.
    const bool small_density_startup = classical_1d && !opt_.use_log_space &&
        !opt_.use_log_damping && (zero_mobile_population || tiny_mobile_population);
    tiny_mobile_population = tiny_mobile_population && opt_.use_log_space;
    zero_mobile_population = zero_mobile_population && opt_.use_log_space;
    auto bootstrap_density = [&]() -> bool {
        NewtonSolver physical(*this);
        physical.opt_.use_log_space = false;
        // Include an already evaluated logarithmic base state in the budget.
        physical.opt_.max_iter = opt_.max_iter > residuals_.size()
            ? opt_.max_iter - residuals_.size() : 0;
        // Use additive density updates for both species: exponential damping
        // would still divide by a tiny positive partner population.
        physical.opt_.use_log_damping = false;
        if (opt_.verbose) std::cout << "Newton zero-population density coordinates\n";
        bool converged = physical.solve(phi, n, p);
        // Once every active population is positive, finish in the requested
        // log coordinates with their carrier-relative gate. The small-density
        // additive stage also checks its own relative continuity defect.
        bool positive_mobile_population = true;
        for (size_t i = 0; i < N; ++i) {
            if (ohmic_nodes_.count(i)) continue;
            if ((!n_bc_.count(i) && mu_n_[i] >= EPSILON && n[i] <= TCAD_CONST(0.0)) ||
                (!p_bc_.count(i) && mu_p_[i] >= EPSILON && p[i] <= TCAD_CONST(0.0)))
                positive_mobile_population = false;
        }
        residuals_.insert(residuals_.end(), physical.residuals_.begin(), physical.residuals_.end());
        nonlinear_samples_.insert(nonlinear_samples_.end(), physical.nonlinear_samples_.begin(), physical.nonlinear_samples_.end());
        if (converged && positive_mobile_population) {
            NewtonSolver logarithmic(*this);
            // Count the bootstrap residual evaluations against the caller's
            // budget; this recovery must not silently double max_iter.
            logarithmic.opt_.max_iter = opt_.max_iter > residuals_.size()
                ? opt_.max_iter - residuals_.size() : 0;
            converged = logarithmic.solve(phi, n, p);
            residuals_.insert(residuals_.end(), logarithmic.residuals_.begin(), logarithmic.residuals_.end());
            nonlinear_samples_.insert(nonlinear_samples_.end(), logarithmic.nonlinear_samples_.begin(), logarithmic.nonlinear_samples_.end());
        }
        return converged;
    };
    if (zero_mobile_population) return bootstrap_density();
    std::vector<real_t> x(3 * N);
    for (size_t i = 0; i < N; ++i) {
        x[phi_idx(i)] = phi[i];
        if (opt_.use_log_space) {
            // Convert linear densities to log-space state u=log(n), v=log(p).
            // Guard against non-positive inputs (Gummel floor of 1e-30 etc.)
            // by clamping before the log.  See audit §18.
            real_t ni = (n[i] > TCAD_CONST(1e-300)) ? n[i] : TCAD_CONST(1e-300);
            real_t pi = (p[i] > TCAD_CONST(1e-300)) ? p[i] : TCAD_CONST(1e-300);
            x[n_idx(i)] = log_q(ni);
            x[p_idx(i)] = log_q(pi);
        } else {
            x[n_idx(i)] = n[i];
            x[p_idx(i)] = p[i];
        }
    }

    inactive_n_.clear();
    inactive_p_.clear();
    if (opt_.enable_quantum && opt_.use_log_space &&
        semi_mask_.size() == N) {
        real_t mobile_scale = TCAD_CONST(1.0);
        for (size_t i = 0; i < N; ++i) {
            if (!semi_mask_[i]) continue;
            mobile_scale = std::max(mobile_scale, abs_q(n[i]));
            mobile_scale = std::max(mobile_scale, abs_q(p[i]));
        }
        // Equivalent to a carrier ErrRef: below one part in 1e10 of the
        // dominant mobile charge, a log-density correction has no resolvable
        // effect on Poisson or terminal current but can make the Jacobian
        // singular.  Preserve the accepted Gummel value at those nodes.
        const real_t carrier_error_reference = TCAD_CONST(1.0e-10) * mobile_scale;
        inactive_n_.assign(N, 0);
        inactive_p_.assign(N, 0);
        size_t inactive_n_count = 0;
        size_t inactive_p_count = 0;
        for (size_t i = 0; i < N; ++i) {
            if (!semi_mask_[i]) continue;
            if (!opt_.freeze_n && !n_bc_.count(i) &&
                n[i] < carrier_error_reference) {
                inactive_n_[i] = 1;
                ++inactive_n_count;
            }
            if (!opt_.freeze_p && !p_bc_.count(i) &&
                p[i] < carrier_error_reference) {
                inactive_p_[i] = 1;
                ++inactive_p_count;
            }
        }
        if (opt_.verbose) {
            std::cout << "Newton quantum active set: ErrRef="
                      << (double)carrier_error_reference
                      << " inactive_n=" << inactive_n_count
                      << " inactive_p=" << inactive_p_count << std::endl;
        }
    }

    std::vector<real_t> F(3 * N);
    std::vector<real_t> dx(3 * N);
    SparseMatrix J(3 * N);
    LinearSolver lin_solver({opt_.linear_solver, 10000, opt_.linear_tol, 30, false});
    const bool bounded_classical_1d = opt_.linear_solver == SolverType::GMRES &&
        N > 2000 && !opt_.enable_quantum && !opt_.transient_enabled &&
        int(g_.nx > 1) + int(g_.ny > 1) + int(g_.nz > 1) == 1;
    auto solve_direction = [&](const SparseMatrix& matrix, const Vector& rhs,
                               Vector& direction) {
        if (bounded_classical_1d &&
            lin_solver.try_banded_direct(matrix, rhs, direction)) {
            if (getenv("TCAD_LIN_DEBUG"))
                std::cerr << "[Newton bounded banded direct n=" << matrix.rows() << "]\n";
            return;
        }
        lin_solver.solve(matrix, rhs, direction);
    };


    residuals_.clear();

    // Row-equilibration scale factors (reciprocal Jacobian diagonal per row),
    // saved so the line-search can evaluate trial residuals on the SAME scaled
    // system as the linear solve.  Without this the raw ||F|| is dominated by
    // whichever node has the largest-magnitude residual, and a Newton step that
    // trades a large residual for a small one elsewhere is wrongly rejected
    // (stall).  On the equilibrated norm every row is O(1) so the step is
    // judged on its true merit.  See audit §17.
    std::vector<real_t> eq_scale;
    std::vector<real_t> residual_measure_scale;
    std::vector<real_t> col_scale;

    real_t norm_F0 = -TCAD_CONST(1.0);  // initial residual norm (set on iter 0)
    real_t blk0[3] = {-TCAD_CONST(1.0), -TCAD_CONST(1.0), -TCAD_CONST(1.0)};  // per-block initial residuals
    size_t stall_count = 0;    // consecutive line-search stalls (alpha=0)

    // Write the Newton state x back to the output (phi, n, p).  In log-space
    // the carrier blocks hold u=log(n), v=log(p) and must be exponentiated on
    // exit.  See audit §18.
    auto write_back = [&]() -> bool {
        // Last line-search trials may leave a cached rejected P. Re-evaluate
        // at the state being committed; the immutable previous P is unchanged.
        refresh_lk_polarization(x.data());
        std::vector<real_t> phi_out(N), n_out(N), p_out(N);
        for (size_t i = 0; i < N; ++i) {
            phi_out[i] = x[phi_idx(i)];
            if (opt_.use_log_space) {
                n_out[i] = exp_q(x[n_idx(i)]);
                p_out[i] = exp_q(x[p_idx(i)]);
                // Preserve exactly specified zero reservoirs at the public
                // boundary; the log floor is solely an internal coordinate.
                if (!ohmic_nodes_.count(i)) {
                    if (n_bc_.count(i) && n_bc_.at(i) == TCAD_CONST(0.0)) n_out[i] = TCAD_CONST(0.0);
                    if (p_bc_.count(i) && p_bc_.at(i) == TCAD_CONST(0.0)) p_out[i] = TCAD_CONST(0.0);
                }
            } else {
                n_out[i] = x[n_idx(i)];
                p_out[i] = x[p_idx(i)];
            }
            // Both blocked rows impose the same algebraic density floor.
            // Krylov roundoff must not turn this exact neutral constraint into
            // unequal n/p and invalidate the strict empty-insulator ledger.
            // Preserve explicit reservoirs and frozen-carrier semantics.
            if(lk_material_field_ && mu_n_[i]==TCAD_CONST(0.0) && mu_p_[i]==TCAD_CONST(0.0) &&
               !opt_.freeze_n && !opt_.freeze_p && !n_bc_.count(i) && !p_bc_.count(i))
                n_out[i]=p_out[i]=EPSILON;
        }
        if (!finite_values(phi_out) || !finite_values(n_out) ||
            !finite_values(p_out)) {
            std::cerr << "Newton refused to write back non-finite state\n";
            return false;
        }
        phi = std::move(phi_out);
        n = std::move(n_out);
        p = std::move(p_out);
        return true;
    };


    use_lagged_quantum_potential_ = false;
    lagged_Qn_.clear();
    lagged_Qp_.clear();
    size_t quantum_steps_since_refresh = 0;
    bool quantum_refresh_pending = opt_.enable_quantum;
    real_t quantum_carrier_trust = TCAD_CONST(5.0);
    for (size_t iter = 0; iter < opt_.max_iter; ++iter) {
        // Q is a Picard variable in this three-block Newton formulation: the
        // Jacobian contains derivatives with respect to phi/n/p but not dQ/dn.
        // Freeze Q for the base residual, Jacobian and every backtracking
        // trial so J*dx is a descent direction for the function actually used
        // by the line search.  Keep it fixed across an inner Newton batch,
        // then refresh and re-apply the physical convergence gate.
        use_lagged_quantum_potential_ = false;
        if (!opt_.enable_quantum || quantum_refresh_pending ||
            lagged_Qn_.size() != N || lagged_Qp_.size() != N) {
            refresh_lagged_quantum_potential(x);
            quantum_steps_since_refresh = 0;
            quantum_refresh_pending = false;
        }
        use_lagged_quantum_potential_ =
            opt_.enable_quantum && lagged_Qn_.size() == N &&
            lagged_Qp_.size() == N;
        assemble_residual(x, F);

        if (!finite_values(F)) {
            std::cerr << "Newton residual contains NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }

        assemble_jacobian(x, J);

        if (!finite_values(J.vals())) {
            std::cerr << "Newton Jacobian contains NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }

        // Per-BLOCK residual norms and per-block solution scales are computed
        // on the RAW residual below (convergence criteria keep original units).
        std::vector<real_t> F_raw(F);

        // In frozen-potential transient mode these identity rows prescribe
        // exactly zero voltage increments. Large carrier-to-voltage entries
        // can make pivoting lose those constraints despite a small GLOBAL
        // linear residual; the frozen residual itself is identically zero
        // and cannot detect the resulting voltage drift. Eliminate the known
        // zero columns before equilibration. If any voltage BC still needs a
        // correction, retain the original full system instead.
        bool zero_voltage_increment = opt_.transient_enabled && opt_.freeze_phi;
        for (size_t i = 0; i < N && zero_voltage_increment; ++i)
            zero_voltage_increment = F[phi_idx(i)] == TCAD_CONST(0.0);
        if (zero_voltage_increment) {
            const auto& rp = J.row_offsets();
            const auto& cols = J.col_indices();
            auto& vals = J.vals_mut();
            for (size_t row = N; row < 3 * N; ++row)
                for (size_t k = rp[row]; k < rp[row + 1]; ++k)
                    if (cols[k] < N) vals[k] = TCAD_CONST(0.0);
        }

        // Potential derivatives carry 1/VT and can make a continuity row
        // appear converged before its carrier-relative correction is small.
        // Measure this extra acceptance guard on the unscaled Jacobian;
        // keep the existing linear equilibration and line-search merit.
        real_t carrier_relative_linf = TCAD_CONST(0.0);
        std::vector<real_t> startup_rates(small_density_startup ? 3 * N : 0);

        // Two-sided equilibration: row scaling (1/max_entry per row) then
        // column scaling (1/max_entry per column).  Row-only scaling leaves
        // columns unbalanced — the phi column has entries from 1 (phi row)
        // to 1e-33 (n row), making the Newton step direction biased.
        // Two-sided scaling makes the matrix entries O(1) in both dimensions,
        // dramatically improving the condition number and Newton step quality.
        {
            const auto& rp = J.row_offsets();
            const auto& cols = J.col_indices();
            auto& vals = J.vals_mut();
            // Phase 1: row scaling
            eq_scale.assign(3 * N, TCAD_CONST(1.0));
            residual_measure_scale.assign(3 * N, TCAD_CONST(1.0));
            for (size_t i = 0; i < 3 * N; ++i) {
                real_t mx = TCAD_CONST(0.0);
                real_t carrier_mx = TCAD_CONST(0.0);
                const size_t row_block = i / N;
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    const size_t column_block = cols[k] / N;
                    if (column_block > 0)
                        carrier_mx = std::max(carrier_mx, abs_q(vals[k]));
                    // A frozen block has an identity equation and therefore
                    // a zero Newton update. Retained cross derivatives must not
                    // define the residual scale of an active row.  In the BE
                    // minority-carrier problem, dF_p/dphi can be ~1e11 times
                    // larger than the active dF_p/dp even though dphi is
                    // constrained to zero; including it caused norm_F<tol at
                    // iteration zero and froze the transient after ~20 steps.
                    const bool frozen_cross =
                        row_block != column_block &&
                        ((column_block == 0 && opt_.freeze_phi) ||
                         (column_block == 1 && opt_.freeze_n) ||
                         (column_block == 2 && opt_.freeze_p));
                    if (!frozen_cross)
                        mx = std::max(mx, abs_q(vals[k]));
                }
                if (classical_qf_trust && row_block > 0) {
                    const size_t node = i % N;
                    const bool electron = row_block == 1;
                    const bool prescribed = electron ? n_bc_.count(node) : p_bc_.count(node);
                    const bool immobile = electron ? mu_n_[node] < EPSILON : mu_p_[node] < EPSILON;
                    if (!prescribed && !immobile) {
                        const real_t relative = carrier_mx > TCAD_CONST(0.0)
                            ? abs_q(F[i]) / carrier_mx
                            : (abs_q(F[i]) > opt_.abs_tol ? TCAD_CONST(1.0) + opt_.tol : TCAD_CONST(0.0));
                        carrier_relative_linf = std::max(carrier_relative_linf, relative);
                    }
                }
                if (small_density_startup) startup_rates[i] = carrier_mx;
                // A tiny positive log population still has a real equation.
                // Normalize its nonzero row even below the general pivot
                // floor; otherwise an almost-equilibrium population can lose
                // its carrier columns before the linear solve sees them.
                const real_t row_floor = tiny_mobile_population && row_block > 0
                    ? TCAD_CONST(0.0) : EPSILON;
                real_t inv = (mx > row_floor) ? TCAD_CONST(1.0) / mx : TCAD_CONST(1.0);
                if (!opt_.use_log_space && row_block > 0) {
                    // With linear density unknowns, in steady as well as
                    // transient solves, 1/max(J_row) leaves the correction
                    // estimate in m^-3. An absolute tol=1e-10 m^-3 is
                    // unattainable at n~1e24 even in quad precision.
                    // Use this species' own local current/previous density to
                    // measure a relative correction. Potential derivatives
                    // must not hide an unsatisfied continuity equation: use
                    // the carrier columns to define its characteristic rate.
                    // Keep this merit/convergence measure separate from the
                    // linear matrix equilibration, so high-density scaling
                    // cannot push matrix columns below its numerical floors.
                    const size_t node = i % N;
                    const auto& previous = row_block == 1 ? opt_.n_prev : opt_.p_prev;
                    real_t density_scale = std::max(abs_q(x[i]), TCAD_CONST(1.0));
                    if (opt_.transient_enabled && previous.size() == N)
                        density_scale = std::max(density_scale, abs_q(previous[node]));
                    const real_t rate = carrier_mx > EPSILON ? carrier_mx : TCAD_CONST(1.0);
                    residual_measure_scale[i] = TCAD_CONST(1.0) / (rate * density_scale * inv);
                    if (small_density_startup && !ohmic_nodes_.count(node) &&
                        !(row_block == 1 ? n_bc_.count(node) : p_bc_.count(node)) &&
                        (row_block == 1 ? mu_n_[node] : mu_p_[node]) >= EPSILON) {
                        // F/rate estimates the missing population, rather than
                        // inventing a fixed seed. At zero it gives a unit
                        // relative defect for any nonzero generation; at the
                        // solution it uses the actual density. Keep these
                        // base-state scales fixed throughout the line search.
                        if (carrier_mx > TCAD_CONST(0.0)) {
                            density_scale = std::max(abs_q(x[i]), abs_q(F[i]) / carrier_mx);
                            if (density_scale > TCAD_CONST(0.0)) {
                                residual_measure_scale[i] = TCAD_CONST(1.0) /
                                    (carrier_mx * density_scale * inv);
                                carrier_relative_linf = std::max(carrier_relative_linf,
                                    abs_q(F[i]) / (carrier_mx * density_scale));
                            }
                        } else if (F[i] != TCAD_CONST(0.0)) {
                            carrier_relative_linf = TCAD_CONST(1.0) + opt_.tol;
                        }
                    }
                }
                eq_scale[i] = inv;
                for (size_t k = rp[i]; k < rp[i + 1]; ++k)
                    vals[k] *= inv;
                F[i] *= inv;
            }
            // Phase 2: column scaling
            col_scale.assign(3 * N, TCAD_CONST(1.0));
            for (size_t j = 0; j < 3 * N; ++j) col_scale[j] = TCAD_CONST(0.0);
            for (size_t i = 0; i < 3 * N; ++i) {
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    size_t j = cols[k];
                    col_scale[j] = std::max(col_scale[j], abs_q(vals[k]));
                }
            }
            for (size_t j = 0; j < 3 * N; ++j) {
                // Linear-density carrier columns in a coupled transient can
                // be smaller than EPSILON purely because density is measured
                // in m^-3 (e.g. derivatives ~1e-24 at n~1e24). They are not
                // absent equations. Normalize every nonzero carrier column
                // before the linear solver applies its pivot floors.
                const real_t floor = (opt_.transient_enabled || tiny_mobile_population) && j >= N
                    ? TCAD_CONST(0.0) : EPSILON;
                col_scale[j] = (col_scale[j] > floor) ? TCAD_CONST(1.0) / col_scale[j] : TCAD_CONST(1.0);
            }
            for (size_t i = 0; i < 3 * N; ++i) {
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    vals[k] *= col_scale[cols[k]];
                }
            }
        }

        // Scale factors are applied in real_t, never passed to the double
        // backend. A valid reciprocal of a tiny log column can exceed DBL_MAX
        // while the scaled matrix and RHS remain representable there.
        auto finite_scales = [](const std::vector<real_t>& values) {
            return std::all_of(values.begin(), values.end(), [](real_t value) {
                return isfinite_q(value);
            });
        };
        if (!finite_values(F) || !finite_values(J.vals()) ||
            !finite_scales(eq_scale) || !finite_scales(col_scale) ||
            !finite_values(residual_measure_scale)) {
            std::cerr << "Newton equilibration produced NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }

        // Avalanche creates electron/hole pairs with the same integrated
        // source units. A cold minority row can have a tiny transport
        // Jacobian while an initially flat potential turns on many II edges
        // during a trial. Its separate row scaling then rejects the voltage
        // progress needed to establish the generated minority population.
        // Use a common pair scale for the globalization RMS only, held fixed
        // across every trial at this base state. Keep the full Jacobian,
        // per-species L-inf/relative-carrier convergence gates and KCL below.
        // Other stiff coupled formulations retain their existing merit.
        std::vector<real_t> merit_scale(residual_measure_scale);
        const bool paired_ii_merit = classical_qf_trust && opt_.enable_ii &&
            (opt_.ii_A_n > TCAD_CONST(0.0) || opt_.ii_A_p > TCAD_CONST(0.0)) &&
            !opt_.enable_btbt && !lk_coupled_ &&
            std::none_of(fe_mask_.begin(), fe_mask_.end(), [](char v) { return v != 0; }) &&
            int(g_.nx > 1) + int(g_.ny > 1) + int(g_.nz > 1) == 1;
        if (paired_ii_merit) {
            for (size_t i = 0; i < N; ++i) {
                if (n_bc_.count(i) || p_bc_.count(i) ||
                    mu_n_[i] < EPSILON || mu_p_[i] < EPSILON) continue;
                const real_t paired = std::min(eq_scale[N+i], eq_scale[2*N+i]);
                merit_scale[N+i] = paired / eq_scale[N+i];
                merit_scale[2*N+i] = paired / eq_scale[2*N+i];
            }
        }
        if (small_density_startup) {
            // A depletion step can leave a mixture of exact zeros and small
            // positive roundoff populations. Scaling each trial row only by
            // its own population/source then rejects all directions that
            // remove those remnants: a zero row can amplify roundoff from a
            // neighbour by hundreds of decades. Use a common per-species
            // population reference for globalization only, held fixed during
            // every trial. The row-local norm, relative continuity and KCL
            // acceptance gates remain unchanged and must all be satisfied.
            real_t density_reference[2] = {TCAD_CONST(0.0), TCAD_CONST(0.0)};
            for (size_t row = N; row < 3 * N; ++row) {
                const size_t node = row % N;
                const bool electron = row < 2 * N;
                if (ohmic_nodes_.count(node) ||
                    (electron ? n_bc_.count(node) : p_bc_.count(node)) ||
                    (electron ? mu_n_[node] : mu_p_[node]) < EPSILON ||
                    startup_rates[row] <= TCAD_CONST(0.0)) continue;
                const size_t species = electron ? 0 : 1;
                density_reference[species] = std::max(density_reference[species],
                    std::max(abs_q(x[row]), abs_q(F_raw[row]) / startup_rates[row]));
            }
            for (size_t row = N; row < 3 * N; ++row) {
                const size_t node = row % N;
                const bool electron = row < 2 * N;
                const size_t species = electron ? 0 : 1;
                if (ohmic_nodes_.count(node) ||
                    (electron ? n_bc_.count(node) : p_bc_.count(node)) ||
                    (electron ? mu_n_[node] : mu_p_[node]) < EPSILON ||
                    startup_rates[row] <= TCAD_CONST(0.0) ||
                    density_reference[species] <= TCAD_CONST(0.0)) continue;
                merit_scale[row] = TCAD_CONST(1.0) /
                    (startup_rates[row] * density_reference[species] * eq_scale[row]);
            }
        }
        // Merit function: equilibrated L-inf for ALL problems (2026-08): the
        // worst scaled row, so a step is judged on every row's merit instead
        // of being dominated by the largest-magnitude rows.
        real_t norm_F = TCAD_CONST(0.0);
        real_t merit_F_sq = TCAD_CONST(0.0);
        for (size_t i = 0; i < 3 * N; ++i) {
            const real_t measured = F[i] * residual_measure_scale[i];
            norm_F = std::max(norm_F, abs_q(measured));
            const real_t merit_measured = F[i] * merit_scale[i];
            merit_F_sq += merit_measured * merit_measured;
        }
        const real_t merit_F = sqrt_q(merit_F_sq / (TCAD_CONST(3.0) * N));
        if (norm_F0 < TCAD_CONST(0.0)) norm_F0 = (norm_F > EPSILON) ? norm_F : TCAD_CONST(1.0);
        // Per-BLOCK residual norms and per-block solution scales (issues0719
        // P0-3).  A single GLOBAL convergence test lets the largest-scale
        // block mask an unconverged block: the legacy |F|/(|x|+1) test used
        // |x|~n~1e25, so Newton "converged" while the re-assembled Poisson
        // residual was 0.158.  Convergence now requires EVERY block (phi, n,
        // p) to satisfy a criterion measured against ITS OWN scale.
        real_t blk[3] = {TCAD_CONST(0.0), TCAD_CONST(0.0), TCAD_CONST(0.0)};
        // Computed on the RAW residual (F_raw) so the convergence criteria
        // keep their original units regardless of row equilibration.
        {
            for (size_t i = 0; i < 3 * N; ++i) {
                size_t b = (i < N) ? 0 : ((i < 2 * N) ? 1 : 2);
                blk[b] += F_raw[i] * F_raw[i];
            }
            for (int b = 0; b < 3; ++b) blk[b] = sqrt_q(blk[b]);
        }
        if (blk0[0] < TCAD_CONST(0.0)) {
            for (int b = 0; b < 3; ++b)
                blk0[b] = (blk[b] > EPSILON) ? blk[b] : norm_F0;
        }
        real_t rel_res = TCAD_CONST(0.0);
        for (int b = 0; b < 3; ++b)
            rel_res = std::max(rel_res, blk[b] / blk0[b]);
        residuals_.push_back(rel_res);
        if (opt_.record_nonlinear_history)
            nonlinear_samples_.push_back({rel_res, blk[0], blk[1], blk[2], merit_F, norm_F});

        if (opt_.verbose) {
            size_t worst_row = 0;
            real_t worst_scaled = TCAD_CONST(0.0);
            for (size_t i = 0; i < 3 * N; ++i) {
                real_t scaled = abs_q(F[i] * residual_measure_scale[i]);
                if (scaled > worst_scaled) {
                    worst_scaled = scaled;
                    worst_row = i;
                }
            }
            const char* worst_block = (worst_row < N) ? "phi"
                                      : (worst_row < 2 * N) ? "n" : "p";
            size_t worst_node = worst_row % N;
            real_t row_max = (eq_scale[worst_row] > EPSILON)
                ? TCAD_CONST(1.0) / eq_scale[worst_row] : TCAD_CONST(0.0);
            std::cout << "Newton iter " << iter
                      << "  |F|=" << (double)norm_F
                      << "  |F|/|F0|=" << (double)rel_res
                      << "  worst=" << worst_block << "[" << worst_node << "]"
                      << " raw=" << (double)F_raw[worst_row]
                      << " rowmax=" << (double)row_max
                      << "  blk=(" << (double)blk[0] << ","
                      << (double)blk[1] << "," << (double)blk[2] << ")"
                      << std::endl;
        }

        // Convergence test (issues0719 P0-3): EVERY block must satisfy one
        // of the true-residual criteria measured against ITS OWN scale:
        //   conv_abs  : ||F_b|| < abs_tol;
        //   conv_rel  : ||F_b|| < tol * ||F_b,0|| (improvement from start);
        //   conv_step : ||F_b|| < tol * (max|x_b| + 1) (residual small
        //               relative to the block's own solution scale).
        // The legacy GLOBAL |F|/(|x|+1) test was killed by the n~1e25
        // carrier scale: it passed with an O(0.1) relative Poisson residual
        // — "iteration stopped changing" masquerading as "equations
        // satisfied".  Per block, the phi rows are tested against the
        // voltage scale and the carrier rows against the carrier scale, so
        // no block can hide behind another.
        bool all_abs = true;
        for (int b = 0; b < 3; ++b) {
            if (!(blk[b] < opt_.abs_tol)) all_abs = false;
        }
        // The carrier residual is cell-integrated flux [m^-2 s^-1], whereas
        // xsc is density [m^-3]; comparing blk to tol*xsc is dimensionally
        // invalid and accepted KCL-broken reverse-junction states.  The
        // row-equilibrated infinity norm is a Newton-correction estimate in
        // each row's natural unknown units and supplies the scale-independent
        // convergence test.  Relative reduction alone is also insufficient:
        // a huge initial residual can improve by 1e-6 and remain nonphysical.
        const bool equilibrated_ok = norm_F < opt_.tol;
        const bool carrier_relative_ok = !(classical_qf_trust || small_density_startup) ||
            carrier_relative_linf < opt_.tol;
        if ((all_abs || equilibrated_ok) && carrier_relative_ok && steady_1d_kcl_ok(x)) {
            // A fixed-Q inner Newton solution is not yet a self-consistent DG
            // solution if x has moved since Q was assembled.  Refresh Q and
            // require the same physical residual gate once more.  Only a
            // state that passes immediately after that refresh may return.
            if (use_lagged_quantum_potential_ &&
                quantum_steps_since_refresh > 0) {
                quantum_refresh_pending = true;
                continue;
            }
            // Damped Picard Q can pass before the undamped physical DG
            // equations do. Reassemble at Q(n,p), using this iteration's
            // unchanged residual scales and KCL threshold, before returning.
            // A rejected probe leaves the frozen transport state intact;
            // the next outer iteration applies the usual damped refresh.
            if (use_lagged_quantum_potential_ &&
                !detail::fresh_quantum_acceptance(
                    use_lagged_quantum_potential_, N, eq_scale,
                    residual_measure_scale, opt_.abs_tol, opt_.tol,
                    [&](std::vector<real_t>& physical_F) {
                        assemble_residual(x, physical_F);
                    },
                    [&]() { return steady_1d_kcl_ok(x); })) {
                quantum_refresh_pending = true;
                continue;
            }
            if (opt_.verbose) std::cout << "Newton converged in " << iter << " iterations.\n";
            return write_back();
        }

        // Keep a near-equilibrium tiny population in log coordinates. Only
        // an unsatisfied first base state needing more than the existing
        // five-unit carrier trust bound uses physical-density startup. This
        // avoids replacing a valid tiny population by the linear-space floor.
        if (iter == 0 && tiny_mobile_population &&
            carrier_relative_linf > TCAD_CONST(5.0))
            return bootstrap_density();

        // Solve J * dx = -F  (F already scaled above when transient)
        Vector rhs(3 * N);
        for (size_t i = 0; i < 3 * N; ++i) rhs[i] = -F[i];
        dx.assign(3 * N, TCAD_CONST(0.0));
        try {
            solve_direction(J, rhs, dx);
        } catch (const std::exception& e) {
            std::cerr << "Newton linear solve failed: " << e.what() << std::endl;
            return false;
        }
        // A Krylov iteration limit is not a usable Newton direction.  Some
        // portable linear backends historically returned their best guess
        // without signalling failure, which allowed enormous null-space-like
        // log-density updates to reach the trust limiter and shrink every
        // physical update to zero.  Audit the actual equilibrated system
        // before undoing column scaling.  This also guards external solvers
        // against a successful status paired with an inaccurate solution.
        {
            real_t relative_linear_error = TCAD_CONST(0.0);
            size_t refinement_steps = 0;
            const real_t linear_acceptance =
                opt_.enable_quantum ? TCAD_CONST(1.0e-3) : TCAD_CONST(1.0e-6);
            for (; refinement_steps <= 3; ++refinement_steps) {
                const Vector Jdx = J.apply(dx);
                Vector correction_rhs(3 * N);
                real_t linear_error = TCAD_CONST(0.0);
                real_t rhs_scale = TCAD_CONST(0.0);
                for (size_t i = 0; i < 3 * N; ++i) {
                    const real_t defect = Jdx[i] + F[i];
                    correction_rhs[i] = -defect;
                    linear_error = std::max(linear_error, abs_q(defect));
                    rhs_scale = std::max(rhs_scale, abs_q(F[i]));
                }
                relative_linear_error =
                    linear_error / std::max(rhs_scale, EPSILON);
                if (!std::isfinite((double)relative_linear_error) ||
                    relative_linear_error <= linear_acceptance ||
                    refinement_steps == 3) {
                    break;
                }
                // Reuse the same sparse factorisation on the quad-computed
                // defect.  This is mixed-precision iterative refinement: the
                // external solve remains fast double precision, while the
                // backward-error measurement and correction RHS retain the
                // assembled real_t precision.
                Vector correction(3 * N, TCAD_CONST(0.0));
                try {
                    solve_direction(J, correction_rhs, correction);
                } catch (const std::exception& e) {
                    std::cerr << "Newton linear refinement failed: "
                              << e.what() << std::endl;
                    return false;
                }
                for (size_t i = 0; i < 3 * N; ++i)
                    dx[i] += correction[i];
            }
            if (opt_.verbose) {
                std::cout << "    [linear] relative_residual="
                          << (double)relative_linear_error
                          << "  refinements=" << refinement_steps
                          << std::endl;
            }
            // PETSc/SuperLU operates in double precision after the quad
            // assembly has been equilibrated.  Classical Newton retains a
            // 1e-6 backward-error gate.  The active-set/trust-region quantum
            // path permits a standard 1e-3 inexact-Newton forcing term because
            // every trial is still accepted by the full nonlinear residual;
            // silent Krylov failures are many orders larger.
            if (!std::isfinite((double)relative_linear_error) ||
                relative_linear_error > linear_acceptance) {
                std::cerr << "Newton linear solve residual too large: "
                          << (double)relative_linear_error << std::endl;
                return false;
            }
        }
        // Undo column scaling: dx_unscaled[j] = dx_scaled[j] * col_scale[j]
        for (size_t j = 0; j < 3 * N; ++j) dx[j] *= col_scale[j];
        if (!finite_values(dx)) {
            std::cerr << "Newton step contains NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }
        // For a severely overpopulated depleted node, Newton in log(n) gives
        // dn/n approximately -1 on every iteration: an exponential update
        // then removes only one e-fold, even for an affine transport equation.
        // Use the already qualified additive startup when the first actual
        // Newton direction would remove at least the existing 90% additive
        // trust fraction. Do not extrapolate from an absolute small residual,
        // alter the requested update policy, or spend an extra solve budget.
        if (iter == 0 && tiny_mobile_population) {
            bool strong_depletion = false;
            for (size_t i = 0; i < N; ++i) {
                if (ohmic_nodes_.count(i)) continue;
                if ((!n_bc_.count(i) && mu_n_[i] >= EPSILON &&
                     n[i] > TCAD_CONST(0.0) && n[i] < TCAD_CONST(1.0) &&
                     dx[n_idx(i)] <= -TCAD_CONST(0.9)) ||
                    (!p_bc_.count(i) && mu_p_[i] >= EPSILON &&
                     p[i] > TCAD_CONST(0.0) && p[i] < TCAD_CONST(1.0) &&
                     dx[p_idx(i)] <= -TCAD_CONST(0.9))) {
                    strong_depletion = true;
                    break;
                }
            }
            if (strong_depletion) return bootstrap_density();
        }
        // Componentwise quasi-Fermi clipping can destroy descent for either
        // density update. Preserve the Newton direction for a uniformly scaled
        // second search only when the original search makes no progress.
        // The classical x-1D WKB source has a qualified potential Jacobian;
        // its full residual also audits every uniformly scaled trial. Local
        // Kane and nonzero avalanche retain their prior source restrictions.
        // With both II amplitudes exactly zero, the
        // generation and every source derivative vanish for any legal B;
        // that inactive model must not block the source-free descent search.
        const bool nonzero_ii_source = opt_.enable_ii &&
            (opt_.ii_A_n > TCAD_CONST(0.0) || opt_.ii_A_p > TCAD_CONST(0.0));
        const bool direction_descent =
            (opt_.additive_log_density_update || (opt_.hfs_enabled && paired_ii_merit) ||
             (!nonzero_ii_source && (!opt_.enable_btbt || opt_.btbt_use_nonlocal))) &&
            classical_qf_trust &&
            int(g_.nx > 1) + int(g_.ny > 1) + int(g_.nz > 1) == 1 &&
            opt_.damping > TCAD_CONST(0.0) && opt_.damping <= TCAD_CONST(1.0);
        const std::vector<real_t> descent_direction_336(
            direction_descent ? dx : std::vector<real_t>());
        // Bank-Rose style log-space step clamp (issues0719 follow-up,
        // plan0728 §1.1): in log-space an unclamped carrier update du
        // explodes the linearised densities (n = exp(u)).  Far from the
        // solution the Newton direction can have |du| ~ 1e8, so EVERY
        // backtracking fraction down to ~1e-3 still overflows/increases
        // ||F|| and the line search stalls permanently at alpha=0 — even
        // though the direction is a mathematically exact descent direction
        // (verified by FD Jacobian checks).  Clamping the carrier update
        // magnitude keeps exp(du) bounded so the direction becomes usable.
        // Apply the trust bound per component.  A single near-null-space
        // minority-carrier node must not shrink every physical phi/n/p update;
        // the full residual line search below validates this inexact direction.
        // In the additive policy dx[n,p] represents dn/n, dp/p. A log/QF
        // clamp can leave a large negative relative update and force tiny
        // fractions that deplete one carrier before the potential advances.
        // Bound relative density increments directly for the paired-II merit;
        // the full residual search and physical convergence gates still apply.
        // HFS exponential updates bound du directly in [-5,5], preserving
        // u += alpha*du; they do not use relative-density positivity limits.
        const bool additive_pair_direction = paired_ii_merit && opt_.additive_log_density_update;
        const bool paired_carrier_direction = additive_pair_direction || (paired_ii_merit && opt_.hfs_enabled);
        if (paired_carrier_direction) {
            real_t phi_fraction = TCAD_CONST(1.0);
            for (size_t row = 0; row < N; ++row)
                if (abs_q(dx[row]) > TCAD_CONST(1.0))
                    phi_fraction = std::min(phi_fraction, TCAD_CONST(1.0)/abs_q(dx[row]));
            for (size_t row = 0; row < N; ++row) dx[row] *= phi_fraction;
            for (size_t row = N; row < 3*N; ++row) {
                const size_t node = row % N;
                const bool electron = row < 2*N;
                const bool prescribed = !ohmic_nodes_.count(node) &&
                    (electron ? n_bc_.count(node) : p_bc_.count(node));
                const bool immobile = electron ? mu_n_[node] < EPSILON : mu_p_[node] < EPSILON;
                // Keep known identity-row corrections, including zero/floor
                // contacts, on their existing unconstrained update path.
                if (prescribed || immobile) continue;
                dx[row] = std::max(opt_.additive_log_density_update ? -TCAD_CONST(0.9) : -TCAD_CONST(5.0),
                                   std::min(TCAD_CONST(5.0), dx[row]));
            }
            if (opt_.verbose) std::cout << (opt_.additive_log_density_update ?
                "    [additive II trust]" : "    [exponential II trust]") << std::endl;
        }
        if (opt_.use_log_space && !paired_carrier_direction) {
            real_t du_max = TCAD_CONST(0.0);
            size_t du_node = 0;
            const char* du_block = "n";
            for (size_t i = N; i < 3 * N; ++i) {
                if (abs_q(dx[i]) > du_max) {
                    du_max = abs_q(dx[i]);
                    du_node = i % N;
                    du_block = (i < 2 * N) ? "n" : "p";
                }
            }
            real_t dphi_max = TCAD_CONST(0.0);
            size_t dphi_node = 0;
            for (size_t i = 0; i < N; ++i) {
                if (abs_q(dx[i]) > dphi_max) {
                    dphi_max = abs_q(dx[i]);
                    dphi_node = i;
                }
            }
            const real_t U_MAX = opt_.enable_quantum
                ? quantum_carrier_trust : TCAD_CONST(5.0);
            const real_t PHI_MAX = TCAD_CONST(1.0);   // max electrostatic step [V]
            size_t clipped_phi = 0;
            size_t clipped_carrier = 0;
            real_t global_scale = TCAD_CONST(1.0);
            real_t phi_block_scale = TCAD_CONST(1.0);
            // Preserve the spatial Poisson direction while allowing a
            // near-null carrier at one node to take a bounded log step.
            // This also applies to classical DD: globally scaling by that
            // carrier's correction can reduce all electrical updates to
            // roundoff and stall a perfectly accurate linear solve.
            // Bound the quasi-Fermi increment and restore the bounded
            // electrostatic increment. Independent clipping would break
            // dlog(n)=dphi/VT and dlog(p)=-dphi/VT at equilibrium.
            const bool qf_trust = classical_qf_trust;
            const std::vector<real_t> raw_step(qf_trust ? dx : std::vector<real_t>());
            if (dphi_max > PHI_MAX) {
                phi_block_scale = PHI_MAX / dphi_max;
                for (size_t i = 0; i < N; ++i)
                    dx[i] *= phi_block_scale;
                clipped_phi = N;
            }
            for (size_t i = N; i < 3 * N; ++i) {
                const size_t node = i % N;
                const bool electron = i < 2*N;
                const bool fixed_contact = !ohmic_nodes_.count(node) &&
                    (electron ? n_bc_.count(node) : p_bc_.count(node));
                const bool immobile = electron ? mu_n_[node] < EPSILON
                                               : mu_p_[node] < EPSILON;
                // Identity log rows have a known finite target. Clipping a
                // zero-to-floor correction (ln(1e280)) to 5 would consume
                // >120 iterations without improving transport accuracy.
                if (fixed_contact || immobile) continue;
                const real_t sign = electron ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                real_t transport_step = qf_trust ? raw_step[i] - sign*raw_step[node]/VT_ : dx[i];
                if (abs_q(transport_step) > U_MAX) {
                    transport_step = transport_step < TCAD_CONST(0.0) ? -U_MAX : U_MAX;
                    ++clipped_carrier;
                }
                dx[i] = qf_trust ? transport_step + sign*dx[node]/VT_ : transport_step;
            }
            if (opt_.verbose &&
                (clipped_phi || clipped_carrier || global_scale < TCAD_CONST(1.0))) {
                std::cout << "    [trust] clipped_phi=" << clipped_phi
                          << "  clipped_carrier=" << clipped_carrier
                          << "  carrier_limit=" << (double)U_MAX
                          << "  phi_scale=" << (double)phi_block_scale
                          << "  global_scale=" << (double)global_scale
                          << "  max_dphi=" << (double)dphi_max
                          << "@" << dphi_node
                          << "  max_d" << du_block << "=" << (double)du_max
                          << "@" << du_node << std::endl;
            }
        }
        // Helper: apply update (linear or exponential for carriers).
        // In log-space the carrier blocks already hold u=log(n), so a plain
        // additive Newton step u += du is the correct exponential update
        // (positivity is automatic: exp(u+du) > 0).  The use_log_damping path
        // (which divides dx[n]/x[n]) is for linear-space states and must NOT
        // fire here.  See audit §18.
        const bool additive_density_333 = opt_.additive_log_density_update;
        auto apply_update = [&](real_t a, std::vector<real_t>& x_out) -> bool {
            for (size_t i = 0; i < N; ++i) {
                x_out[phi_idx(i)] = x[phi_idx(i)] + a * dx[phi_idx(i)];
                if (opt_.use_log_space) {
                    // Additive in log-space == multiplicative in linear space.
                    if (additive_density_333) {
                        if (!additive_density_log_update_333(x[n_idx(i)],a*dx[n_idx(i)],x_out[n_idx(i)]) ||
                            !additive_density_log_update_333(x[p_idx(i)],a*dx[p_idx(i)],x_out[p_idx(i)])) return false;
                    } else {
                        x_out[n_idx(i)] = x[n_idx(i)] + a * dx[n_idx(i)];
                        x_out[p_idx(i)] = x[p_idx(i)] + a * dx[p_idx(i)];
                    }
                } else if (opt_.use_log_damping) {
                    // Dirichlet, immobile and frozen rows are linear identity
                    // constraints. An exponential update divides by zero for
                    // legal zero-density contacts/insulators (even at a=0).
                    // A pristine mobile density likewise needs an additive
                    // first update before relative damping becomes meaningful.
                    auto carrier_update = [&](size_t row, bool constrained) {
                        if (constrained || x[row] <= EPSILON)
                            return std::max(TCAD_CONST(0.0), x[row] + a * dx[row]);
                        return x[row] * exp_q(a * dx[row] / x[row]);
                    };
                    x_out[n_idx(i)] = carrier_update(n_idx(i),
                        n_bc_.count(i) || opt_.freeze_n || mu_n_[i] < EPSILON);
                    x_out[p_idx(i)] = carrier_update(p_idx(i),
                        p_bc_.count(i) || opt_.freeze_p || mu_p_[i] < EPSILON);
                } else {
                    x_out[n_idx(i)] = x[n_idx(i)] + a * dx[n_idx(i)];
                    x_out[p_idx(i)] = x[p_idx(i)] + a * dx[p_idx(i)];
                    // Apply identical positivity constraints to trial and
                    // committed states. Exact zero reservoirs are legal and
                    // must not acquire the free-node density floor.
                    const real_t n_floor = small_density_startup || (!ohmic_nodes_.count(i) &&
                        n_bc_.count(i) && n_bc_.at(i) == TCAD_CONST(0.0)
                        ) ? TCAD_CONST(0.0) : EPSILON;
                    const real_t p_floor = small_density_startup || (!ohmic_nodes_.count(i) &&
                        p_bc_.count(i) && p_bc_.at(i) == TCAD_CONST(0.0)
                        ) ? TCAD_CONST(0.0) : EPSILON;
                    x_out[n_idx(i)] = std::max(n_floor, x_out[n_idx(i)]);
                    x_out[p_idx(i)] = std::max(p_floor, x_out[p_idx(i)]);

                }
            }
            return true;
        };

        // Line search / damping.  Backtracking from alpha=1 (full Newton step),
        // accepting the step with the smallest residual.  If NO step improves on
        // the current residual we still take the best-found (least-bad) step so
        // Newton can keep trying — but we cap it to avoid a catastrophic blow-up.
        real_t alpha = opt_.damping;
        if (opt_.use_line_search) {
            real_t best_alpha = TCAD_CONST(0.0);       // 0 = "take no step" if nothing helps
            real_t best_merit = merit_F;     // must beat the current RMS merit
            for (size_t ls = 0; ls < opt_.line_search_max; ++ls) {
                std::vector<real_t> x_try(3 * N);
                if (!apply_update(alpha, x_try)) {
                    alpha *= TCAD_CONST(0.5);
                    if (alpha < opt_.min_damping) break;
                    continue;
                }
                std::vector<real_t> F_try(3 * N);
                assemble_residual(x_try, F_try);
                if (!finite_values(x_try) || !finite_values(F_try)) {
                    alpha *= TCAD_CONST(0.5);
                    if (alpha < opt_.min_damping) break;
                    continue;
                }
                // Apply the SAME row-equilibration as the baseline so the
                // trial norm is comparable to norm_F (2026-08: now always on).
                for (size_t i = 0; i < 3 * N; ++i)
                    F_try[i] *= eq_scale[i] * residual_measure_scale[i];
                // RMS globalization merit plus an L-inf growth guard.
                real_t norm_try = TCAD_CONST(0.0);
                real_t merit_try_sq = TCAD_CONST(0.0);
                for (size_t i = 0; i < 3 * N; ++i) {
                    norm_try = std::max(norm_try, abs_q(F_try[i]));
                    const real_t v = small_density_startup
                        ? F_try[i] * merit_scale[i] / residual_measure_scale[i]
                        : (paired_ii_merit ? F_try[i] * merit_scale[i] : F_try[i]);
                    merit_try_sq += v * v;
                }
                const real_t merit_try =
                    sqrt_q(merit_try_sq / (TCAD_CONST(3.0) * N));
                // Use RMS to make progress when one SG cancellation row sits
                // on an L-inf plateau, but never permit the worst row to grow
                // materially.  Final convergence remains the strict L-inf
                // gate above, so this changes globalization, not accuracy.
                // A contact row can grow while the full row-equilibrated
                // RMS merit decreases. For the classical 1-D log-density
                // formulation, an additional 5% L-inf envelope can reject
                // every default step despite a strictly descending RMS.
                // Use the RMS line-search criterion for this formulation;
                // keep the L-inf envelope for other formulations. Final
                // convergence and physical KCL retain their strict gates.
                // Applicability depends on the formulation, not grid size.
                const bool classical_1d_merit = classical_qf_trust &&
                    int(g_.nx > 1) + int(g_.ny > 1) + int(g_.nz > 1) == 1;
                if (merit_try < best_merit &&
                    (classical_1d_merit || small_density_startup ||
                     norm_try <= TCAD_CONST(1.05) * norm_F)) {
                    best_merit = merit_try;
                    best_alpha = alpha;
                }
                alpha *= TCAD_CONST(0.5);
                if (alpha < opt_.min_damping) break;
            }
            alpha = best_alpha;  // 0 if no step improved => stall, not blow-up
            // A stalled transient must meet the same requested residual gate
            // as every other accepted step. A separate 3% "good-enough" exit
            // previously bypassed an arbitrarily tighter caller tolerance.
        }

        const bool hfs_rescue_stalled_371 = opt_.use_line_search && direction_descent &&
            paired_ii_merit && opt_.hfs_enabled && alpha == TCAD_CONST(0.0);
        if (opt_.use_line_search && direction_descent &&
            alpha == TCAD_CONST(0.0)) {
            const std::vector<real_t> clipped_direction_336(dx);
            real_t scale_336 = TCAD_CONST(1.0);
            for (size_t row = 0; row < 3*N; ++row) {
                const real_t d = descent_direction_336[row];
                if (row < N && abs_q(d) > TCAD_CONST(1.0))
                    scale_336 = std::min(scale_336, TCAD_CONST(1.0)/abs_q(d));
                if (row >= N && opt_.additive_log_density_update && d < -TCAD_CONST(0.9))
                    scale_336 = std::min(scale_336, -TCAD_CONST(0.9)/d);
                // Exponential updates retain u += alpha*du. Bound the actual
                // log increment in both signs without changing its direction;
                // the additive policy keeps its existing positivity bound.
                if (row >= N && !opt_.additive_log_density_update && abs_q(d) > TCAD_CONST(5.0))
                    scale_336 = std::min(scale_336, TCAD_CONST(5.0)/abs_q(d));
            }
            dx = descent_direction_336;
            for (real_t& d : dx) d *= scale_336;
            real_t best_merit_336 = merit_F;
            real_t trial_alpha_336 = opt_.damping;
            for (size_t ls = 0; ls < opt_.line_search_max; ++ls) {
                std::vector<real_t> x_try(3*N);
                if (apply_update(trial_alpha_336,x_try)) {
                    std::vector<real_t> f_try(3*N);
                    assemble_residual(x_try,f_try);
                    if (finite_values(x_try) && finite_values(f_try)) {
                        real_t sq = TCAD_CONST(0.0), linf = TCAD_CONST(0.0);
                        for (size_t row = 0; row < 3*N; ++row) {
                            const real_t v=f_try[row]*eq_scale[row]*merit_scale[row];
                            sq += v*v;
                            linf = std::max(linf,abs_q(v));
                        }
                        const real_t merit=sqrt_q(sq/(TCAD_CONST(3.0)*N));
                        // Same classical1D RMS descent criterion as the first
                        // search; final residual and physical gates unchanged.
                        if (merit < best_merit_336) {
                            best_merit_336=merit;
                            alpha=trial_alpha_336;
                        }
                    }
                }
                trial_alpha_336 *= TCAD_CONST(0.5);
                if (trial_alpha_336 < opt_.min_damping) break;
            }
            if (alpha == TCAD_CONST(0.0)) dx=clipped_direction_336;
            if (opt_.verbose)
                std::cout << "    [descent fallback] policy="
                          << (opt_.additive_log_density_update ? "additive" : "exponential")
                          << " scale=" << (double)scale_336
                          << " alpha=" << (double)alpha << std::endl;
        }
        // Compare regularized directions against the original bounded
        // fallback using the same full residual and fixed-base merit.
        if (hfs_rescue_stalled_371) {
            const Vector original_direction(dx);
            const real_t original_alpha=alpha;
            auto rescue_merit = [&](real_t step) -> real_t {
                Vector state(3*N),residual(3*N);
                if (!apply_update(step,state) || !finite_values(state)) return TCAD_CONST(1e100);
                assemble_residual(state,residual);
                if (!finite_values(residual)) return TCAD_CONST(1e100);
                real_t square=TCAD_CONST(0.0);
                for (size_t row=0; row<3*N; ++row) {
                    const real_t value=residual[row]*eq_scale[row]*merit_scale[row];
                    square+=value*value;
                }
                return sqrt_q(square/(TCAD_CONST(3.0)*N));
            };
            real_t best=alpha>TCAD_CONST(0.0) ? rescue_merit(alpha) : merit_F;
            Vector best_direction(original_direction);
            real_t chosen_regularizer=TCAD_CONST(0.0),regularizer=TCAD_CONST(1e-8);
            const auto& offsets=J.row_offsets();const auto& columns=J.col_indices();
            const auto& entries=J.vals();
            Vector coordinate_scale(3*N,TCAD_CONST(1.0));
            for (size_t j=0; j<N; ++j) coordinate_scale[j]=VT_;
            for (size_t attempt=0; attempt<10; ++attempt,regularizer*=TCAD_CONST(10.0)) {
                SparseMatrix shifted(3*N);
                for (size_t row=0; row<3*N; ++row) {
                    real_t row_scale=TCAD_CONST(0.0);
                    for (size_t k=offsets[row]; k<offsets[row+1]; ++k) {
                        const size_t col=columns[k];
                        const real_t value=entries[k]/col_scale[col]*coordinate_scale[col];
                        shifted.add_entry(row,col,value);row_scale=std::max(row_scale,abs_q(value));
                    }
                    const size_t node=row%N;
                    const bool prescribed=row<N ? phi_bc_.count(node) :
                        (row<2*N ? n_bc_.count(node) : p_bc_.count(node));
                    if (!prescribed) shifted.add_entry(row,row,(row<N ? -regularizer : regularizer)*row_scale);
                }
                shifted.finalize();Vector direction(3*N,TCAD_CONST(0.0)),rhs_shift(3*N);
                for (size_t row=0; row<3*N; ++row) rhs_shift[row]=-F[row];
                try { solve_direction(shifted,rhs_shift,direction); }
                catch (const std::exception&) { continue; }
                if (!finite_values(direction)) continue;
                const Vector product=shifted.apply(direction);
                real_t error=TCAD_CONST(0.0),scale=TCAD_CONST(0.0);
                for (size_t row=0; row<3*N; ++row) {
                    error=std::max(error,abs_q(product[row]+F[row]));
                    scale=std::max(scale,abs_q(F[row]));dx[row]=coordinate_scale[row]*direction[row];
                }
                if (error>TCAD_CONST(1e-6)*std::max(scale,EPSILON)) continue;
                real_t phi_fraction=TCAD_CONST(1.0);
                for (size_t row=0; row<N; ++row)
                    if (abs_q(dx[row])>TCAD_CONST(1.0)) phi_fraction=std::min(phi_fraction,TCAD_CONST(1.0)/abs_q(dx[row]));
                for (size_t row=0; row<N; ++row) dx[row]*=phi_fraction;
                for (size_t row=N; row<3*N; ++row) {
                    const size_t node=row%N;const bool electron=row<2*N;
                    const bool prescribed=electron ? n_bc_.count(node) : p_bc_.count(node);
                    const bool immobile=electron ? mu_n_[node]<EPSILON : mu_p_[node]<EPSILON;
                    if (!prescribed && !immobile) dx[row]=std::max(opt_.additive_log_density_update ? -TCAD_CONST(0.9) : -TCAD_CONST(5.0),std::min(TCAD_CONST(5.0),dx[row]));
                }
                real_t trial=opt_.damping;
                for (size_t ls=0; ls<opt_.line_search_max; ++ls) {
                    const real_t merit=rescue_merit(trial);
                    if (merit<best) {best=merit;alpha=trial;best_direction=dx;chosen_regularizer=regularizer;}
                    trial*=TCAD_CONST(0.5);if (trial<opt_.min_damping) break;
                }
            }
            dx=best_direction;
            if (opt_.verbose) std::cout << "    [HFS shifted direction] lambda="
                << (double)chosen_regularizer << " alpha=" << (double)alpha
                << " original_alpha=" << (double)original_alpha << std::endl;
        }
        // Apply final update (alpha=0 => no change, Newton stalls cleanly)
        if (!apply_update(alpha, x)) return false;
        if (!finite_values(x)) {
            std::cerr << "Newton update produced NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }
        if (use_lagged_quantum_potential_ && alpha > TCAD_CONST(0.0)) {
            ++quantum_steps_since_refresh;
            if (alpha >= TCAD_CONST(0.5)) {
                quantum_carrier_trust = std::min(
                    TCAD_CONST(5.0), TCAD_CONST(1.25) * quantum_carrier_trust);
            }
        } else if (use_lagged_quantum_potential_ && alpha == TCAD_CONST(0.0)) {
            // Keep Q fixed and contract only the rejected carrier trust
            // region.  Refreshing Q here changes the nonlinear target before
            // the fixed-Q equations have converged and re-enters the DG cycle.
            quantum_carrier_trust = std::max(
                TCAD_CONST(0.1), TCAD_CONST(0.5) * quantum_carrier_trust);
        }
        if (opt_.verbose) {
            real_t dx_max = TCAD_CONST(0.0);
            for (size_t i = 0; i < 3 * N; ++i) dx_max = std::max(dx_max, abs_q(dx[i]));
            std::cout << "    [ls] alpha=" << (double)alpha
                      << "  |dx|_max=" << (double)dx_max << std::endl;
        }
        // Stall watchdog: with alpha=0 the state cannot change, so further
        // iterations only burn max_iter re-evaluating the same residual.
        // Declare the honest failure early (issues0719 P0-3 follow-up — a
        // stalled Newton previously ground through 1000 iterations per bias
        // point).
        stall_count = (alpha == TCAD_CONST(0.0)) ? stall_count + 1 : 0;
        if (stall_count >= 10) {
            std::cerr << "Newton stalled (line search made no progress for "
                      << stall_count << " consecutive iterations); "
                      << "declaring non-convergence\n";
            write_back();
            return false;
        }
    }

    std::cerr << "Newton did not converge within max_iter\n";
    write_back();
    return false;
}

void NewtonSolver::debug_solve_probe(const std::vector<real_t>& phi,
                                     const std::vector<real_t>& n,
                                     const std::vector<real_t>& p) {
    validate_newton_inputs(g_.npts(), phi, n, p, Nc_, Nv_, Eg_);
    const size_t N = g_.npts();
    std::vector<real_t> x(3 * N);
    for (size_t i = 0; i < N; ++i) {
        x[phi_idx(i)] = phi[i];
        if (opt_.use_log_space) {
            real_t ni = (n[i] > TCAD_CONST(1e-300)) ? n[i] : TCAD_CONST(1e-300);
            real_t pi = (p[i] > TCAD_CONST(1e-300)) ? p[i] : TCAD_CONST(1e-300);
            x[n_idx(i)] = log_q(ni);
            x[p_idx(i)] = log_q(pi);
        } else {
            x[n_idx(i)] = n[i];
            x[p_idx(i)] = p[i];
        }
    }
    std::vector<real_t> F(3 * N), F1(3 * N);
    assemble_residual(x, F);
    SparseMatrix J(3 * N);
    assemble_jacobian(x, J);
    LinearSolver lin_solver({opt_.linear_solver, 10000, opt_.linear_tol, 30, false});
    Vector rhs(3 * N), dxv(3 * N);
    for (size_t i = 0; i < 3 * N; ++i) rhs[i] = -F[i];
    dxv.assign(3 * N, TCAD_CONST(0.0));
    try {
        lin_solver.solve(J, rhs, dxv);
    } catch (const std::exception& e) {
        std::printf("[probe] linear solve FAILED: %s\n", e.what());
        return;
    }
    std::vector<real_t> dx(3 * N);
    for (size_t i = 0; i < 3 * N; ++i) dx[i] = dxv[i];
    // Solve accuracy: ||J dx + F|| / ||F||
    std::vector<real_t> Jdx(3 * N, TCAD_CONST(0.0));
    const auto& rp = J.row_offsets();
    const auto& cols = J.col_indices();
    const auto& vals = J.vals();
    for (size_t i = 0; i < 3 * N; ++i)
        for (size_t k = rp[i]; k < rp[i + 1]; ++k)
            Jdx[i] += vals[k] * dx[cols[k]];
    real_t num = TCAD_CONST(0.0), den = TCAD_CONST(0.0), dxmax = TCAD_CONST(0.0);
    for (size_t i = 0; i < 3 * N; ++i) {
        num += (Jdx[i] + F[i]) * (Jdx[i] + F[i]);
        den += F[i] * F[i];
        dxmax = std::max(dxmax, abs_q(dx[i]));
    }
    std::printf("[probe] |F|=%.6g  |J*dx+F|/|F|=%.6g  |dx|max=%.6g\n",
                (double)sqrt_q(den), (double)sqrt_q(num / (den + TCAD_CONST(1e-300))),
                (double)dxmax);
    // Directional residual along the Newton step.
    const double alphas[] = {1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125,
                             0.015625, 0.0078125, 0.00390625};
    for (double a : alphas) {
        std::vector<real_t> xt(3 * N);
        for (size_t i = 0; i < 3 * N; ++i) xt[i] = x[i] + (real_t)a * dx[i];
        assemble_residual(xt, F1);
        real_t n1 = TCAD_CONST(0.0);
        for (size_t i = 0; i < 3 * N; ++i) n1 += F1[i] * F1[i];
        std::printf("[probe] a=%.6g  |F(x+a*dx)|=%.10g\n", a, (double)sqrt_q(n1));
    }
}

size_t NewtonSolver::debug_fd_jacobian_check(const std::vector<real_t>& phi,
                                             const std::vector<real_t>& n,
                                             const std::vector<real_t>& p,
                                             double rel_tol,
                                             size_t max_report) {
    validate_newton_inputs(g_.npts(), phi, n, p, Nc_, Nv_, Eg_);
    const size_t N = g_.npts();
    // Build the Newton state x exactly as solve() does.
    std::vector<real_t> x(3 * N);
    for (size_t i = 0; i < N; ++i) {
        x[phi_idx(i)] = phi[i];
        if (opt_.use_log_space) {
            real_t ni = (n[i] > TCAD_CONST(1e-300)) ? n[i] : TCAD_CONST(1e-300);
            real_t pi = (p[i] > TCAD_CONST(1e-300)) ? p[i] : TCAD_CONST(1e-300);
            x[n_idx(i)] = log_q(ni);
            x[p_idx(i)] = log_q(pi);
        } else {
            x[n_idx(i)] = n[i];
            x[p_idx(i)] = p[i];
        }
    }
    std::vector<real_t> F0(3 * N), F1(3 * N), Fminus(3 * N);
    assemble_residual(x, F0);
    SparseMatrix J(3 * N);
    assemble_jacobian(x, J);
    const auto& rp = J.row_offsets();
    const auto& cols = J.col_indices();
    const auto& vals = J.vals();

    struct Bad { double err; size_t row, col; double jan, fdm; };
    std::vector<Bad> bad;
    size_t n_bad = 0, n_checked = 0;

    for (size_t j = 0; j < 3 * N; ++j) {
        // Central differences balance O(h^2) truncation against O(eps/h)
        // cancellation. The old fixed forward step was too small for x87.
        real_t scale = std::max(abs_q(x[j]), real_t(TCAD_CONST(1.0)));
        real_t h = std::max(TCAD_CONST(1e-10),
            pow_q(epsilon_q(), TCAD_CONST(1.0)/TCAD_CONST(3.0))) * scale;
        std::vector<real_t> xp = x;
        xp[j] += h;
        assemble_residual(xp, F1);
        xp[j] = x[j] - h;
        assemble_residual(xp, Fminus);
        // Compare every J entry in column j against the FD derivative.
        for (size_t i = 0; i < 3 * N; ++i) {
            real_t fd = (F1[i] - Fminus[i]) / (TCAD_CONST(2.0)*h);
            // Find J(i,j) in the CSR structure.
            real_t jan = TCAD_CONST(0.0);
            bool present = false;
            for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                if (cols[k] == j) { jan = vals[k]; present = true; break; }
            }
            if (!present && abs_q(fd) < TCAD_CONST(1e-12) * (abs_q(F0[i]) + TCAD_CONST(1.0))) continue;
            real_t denom = std::max(abs_q(fd), abs_q(jan));
            if (denom < TCAD_CONST(1e-12) * (abs_q(F0[i]) + TCAD_CONST(1.0))) continue;  // both ~0
            real_t err = abs_q(jan - fd) / denom;
            ++n_checked;
            if ((double)err > rel_tol) {
                ++n_bad;
                bad.push_back({(double)err, i, j, (double)jan, (double)fd});
            }
        }
    }
    std::sort(bad.begin(), bad.end(),
              [](const Bad& a, const Bad& b) { return a.err > b.err; });
    auto name_of = [&](size_t v, size_t& node) -> const char* {
        if (v < N) { node = v; return "phi"; }
        if (v < 2 * N) { node = v - N; return "n"; }
        node = v - 2 * N; return "p";
    };
    std::cout << "[fd-jac] state N=" << N
              << " log_space=" << (opt_.use_log_space ? 1 : 0)
              << " checked=" << n_checked << " mismatched=" << n_bad << "\n";
    size_t shown = 0;
    for (const auto& b : bad) {
        if (shown++ >= max_report) break;
        size_t rn, cn;
        const char* rb = name_of(b.row, rn);
        const char* cb = name_of(b.col, cn);
        // Node -> (i,j,k) for geometry context.
        size_t ri = rn % g_.nx, rj = (rn / g_.nx) % g_.ny, rk = rn / (g_.nx * g_.ny);
        size_t ci = cn % g_.nx, cj = (cn / g_.nx) % g_.ny, ck = cn / (g_.nx * g_.ny);
        std::printf("  err=%.3g  F[%s(%zu,%zu,%zu)] d/dx[%s(%zu,%zu,%zu)]"
                    "  J=%.6g  FD=%.6g\n",
                    b.err, rb, ri, rj, rk, cb, ci, cj, ck, b.jan, b.fdm);
    }
    return n_bad;
}

}  // namespace tcad
