// =====================================================================
// mom/green/spectral.cpp —— 谱域格林函数 S-matrix 递推实现
//
// 参考：Michalski & Zheng, IEEE TAP 1990 (Formulation C)。
// 对平面分层介质，递推广义反射/透射系数，得谱域核 G_A、G_phi。
// =====================================================================
#include "mom/green/spectral.hpp"
#include "mom/common/types.hpp"

#include <cmath>
#include <stdexcept>
#include <algorithm>

namespace mom::green::spectral {

SpectralGreensFunction::SpectralGreensFunction(const LayeredMedium& medium,
                                               Real freq, Real z_src, Real z_obs)
    : medium_(medium), omega_(2.0 * phys::pi * freq), z_src_(z_src), z_obs_(z_obs) {
    if (medium_.layers.empty())
        throw std::runtime_error("LayeredMedium: 至少一层");

    // 各层波数 k_i = omega*sqrt(mu0*eps0*eps_r_i*(1 - j*tand_i))
    k_layers_.resize(medium_.layers.size());
    for (Size i = 0; i < medium_.layers.size(); ++i) {
        const auto& L = medium_.layers[i];
        const Complex eps_cmplx(L.eps_r, -L.tand);
        k_layers_[i] = omega_ * std::sqrt(phys::mu0 * phys::eps0 * eps_cmplx);
    }

    // 界面 z 坐标：自底向上。底层 z_bottom = ground_z（或最底）。
    z_interface_.resize(medium_.layers.size() + 1);
    z_interface_[0] = (groundz_is_real(medium_.ground_z) ? medium_.ground_z : 0.0);
    for (Size i = 0; i < medium_.layers.size(); ++i) {
        if (medium_.layers[i].is_half_space) {
            z_interface_[i + 1] = z_interface_[i];  // 半空间无厚度
        } else {
            z_interface_[i + 1] = z_interface_[i] + medium_.layers[i].thickness;
        }
    }
}

// 辅助：层内垂直波数 k_zi = sqrt(k_i^2 - k_rho^2)，支点 Im>=0。
// （已验证：与修正后谱核 j·e^{+j k_z d}/(2k_z) 的 Sommerfeld 恒等式自洽。）
Complex SpectralGreensFunction::k_z(Index i, Complex k_rho) const {
    Complex r = std::sqrt(k_layers_[i] * k_layers_[i] - k_rho * k_rho);
    return (r.imag() < 0.0) ? -r : r;
}

namespace {
// 自由函数版 sqrt（支点 Im>=0）。
Complex sqrt_up(Complex x) {
    Complex r = std::sqrt(x);
    return (r.imag() < 0.0) ? -r : r;
}
} // namespace

// 电压反射系数 Γ_V（TM/TE），自由函数。
//
// Michalski-Mosig TLGF 公式（eq.59-61）用【电压】反射系数，而非电场反射系数。
//   特征阻抗：Z^e(TM) = k_z/(ω·ε)，Z^h(TE) = ω·μ/k_z。
//   电压反射：Γ_V = (Z_b − Z_a)/(Z_b + Z_a)。
//     TM : Γ_V^{TM} = (ε_a·k_zb − ε_b·k_za)/(ε_a·k_zb + ε_b·k_za)
//     TE : Γ_V^{TE} = (k_za − k_zb)/(k_za + k_zb)
//
// 历史 bug：原实现误用【电场】反射 Γ_E^{TM}=(ε_b·k_za − ε_a·k_zb)/(...)
//          —— 与 Γ_V^{TM} 恰好反号。ε=1 时 R̃_U=0 不可见，ε≠1 时 G_A 符号错。
//          （TE 原实现恰好已是 Γ_V，无需改。）
Complex fresnel(Complex kz_a, Complex kz_b, Complex eps_a, Complex eps_b, bool TM) {
    if (TM) {
        Complex num = eps_a * kz_b - eps_b * kz_a;
        Complex den = eps_a * kz_b + eps_b * kz_a;
        return (std::abs(den) > 0.0) ? num / den : Complex(0, 0);
    }
    Complex num = kz_a - kz_b;
    Complex den = kz_a + kz_b;
    return (std::abs(den) > 0.0) ? num / den : Complex(0, 0);
}

Complex SpectralGreensFunction::generalized_refl_up_TM(Complex k_rho) const {
    return generalized_refl_up_polar(k_rho, /*TM=*/true);
}
Complex SpectralGreensFunction::generalized_refl_up_TE(Complex k_rho) const {
    return generalized_refl_up_polar(k_rho, /*TM=*/false);
}
Complex SpectralGreensFunction::generalized_refl_up_polar(Complex k_rho, bool TM) const {
    const Size nL = medium_.layers.size();
    const Index i_src = [&] {
        for (Index i = 0; i < Index(nL); ++i)
            if (z_src_ >= z_interface_[i] - 1e-15 && z_src_ <= z_interface_[i + 1] + 1e-15) return i;
        return Index(nL) - 1;
    }();
    // 顶层外侧反射：PEC 封闭（±1）或开放（向空气 Fresnel）。
    Index jtop = Index(nL) - 1;
    Complex Rtilde;
    if (groundz_is_real(medium_.cover_z)) {
        // 顶部 PEC 封闭：TM 反射 +1（pec_positive），TE 反射 -1。
        // （与底部 ground_z 的极性约定一致：TM/矢量位 +1，TE/标量势 -1。）
        Rtilde = TM ? Complex(1.0, 0.0) : Complex(-1.0, 0.0);
    } else {
        const Complex eps_air(1.0, 0.0);
        const Complex k_air = omega_ * std::sqrt(phys::mu0 * phys::eps0 * eps_air);
        Complex kz_air = std::sqrt(k_air * k_air - k_rho * k_rho);
        if (kz_air.imag() < 0) kz_air = -kz_air;   // 支点 Im>=0（同 k_z()）
        // 顶层与空气界面反射
        const Complex kz_top = k_z(jtop, k_rho);
        Complex eps_top(medium_.layers[jtop].eps_r, -medium_.layers[jtop].tand);
        Rtilde = fresnel(kz_top, kz_air, eps_top, eps_air, TM);
    }
    // 自顶层-1 向下递推到源层
    for (Index j = Index(nL) - 2; j >= i_src; --j) {
        const Complex kz_j = k_z(j, k_rho);
        const Complex kz_jp1 = k_z(j + 1, k_rho);
        Complex eps_j(medium_.layers[j].eps_r, -medium_.layers[j].tand);
        Complex eps_jp1(medium_.layers[j + 1].eps_r, -medium_.layers[j + 1].tand);
        const Complex r = fresnel(kz_j, kz_jp1, eps_j, eps_jp1, TM);
        const Real h_jp1 = medium_.layers[j + 1].thickness;
        // 相位因子 exp(+j·2·k_z·h)：配合修正后的指数约定（见 operator() 注释），
        // 使 evanescent（kρ>k_i, k_z=j|kz|）区的层间往返 exp(-2|kz|·h) 衰减而非发散。
        const Complex phase = std::exp(Iunit * (2.0 * kz_jp1) * h_jp1);
        Rtilde = (r + Rtilde * phase) / (Complex(1, 0) + r * Rtilde * phase);
    }
    return Rtilde;
}

Complex SpectralGreensFunction::generalized_refl_dn_TM(Complex k_rho) const {
    return generalized_refl_dn_polar(k_rho, /*TM=*/true, /*pec_positive=*/true);
}
Complex SpectralGreensFunction::generalized_refl_dn_TE(Complex k_rho) const {
    // G_phi (TE/标量势 Dirichlet)：PEC 反号（-1）
    return generalized_refl_dn_polar(k_rho, /*TM=*/false, /*pec_positive=*/false);
}
Complex SpectralGreensFunction::generalized_refl_dn_polar(Complex k_rho, bool TM, bool pec_positive) const {
    const Size nL = medium_.layers.size();
    const Index i_src = [&] {
        for (Index i = 0; i < Index(nL); ++i)
            if (z_src_ >= z_interface_[i] - 1e-15 && z_src_ <= z_interface_[i + 1] + 1e-15) return i;
        return Index(nL) - 1;
    }();
    // 底层下：PEC 则 ±1（pec_positive 决定），开放则 0。
    Complex Rtilde(0.0, 0.0);
    if (groundz_is_real(medium_.ground_z))
        Rtilde = pec_positive ? Complex(1.0, 0.0) : Complex(-1.0, 0.0);
    for (Index j = 0; j < i_src; ++j) {
        const Complex kz_j = k_z(j, k_rho);
        Complex eps_j(medium_.layers[j].eps_r, -medium_.layers[j].tand);
        Complex eps_jp1(medium_.layers[j + 1].eps_r, -medium_.layers[j + 1].tand);
        const Complex r = fresnel(kz_j, k_z(j + 1, k_rho), eps_j, eps_jp1, TM);
        const Real h_j = medium_.layers[j].thickness;
        // 相位因子 exp(+j·2·k_z·h)：配合修正后的指数约定（见 operator() 注释），
        // 使 evanescent 区层间往返衰减。
        const Complex phase = std::exp(Iunit * (2.0 * kz_j) * h_j);
        Rtilde = (r + Rtilde * phase) / (Complex(1, 0) + r * Rtilde * phase);
    }
    return Rtilde;
}

std::pair<Complex, Complex> SpectralGreensFunction::debug_R_TM(Complex k_rho) const {
    return {generalized_refl_up_TM(k_rho), generalized_refl_dn_TM(k_rho)};
}

Complex SpectralGreensFunction::source_k_z(Complex k_rho) const {
    const Size nL = medium_.layers.size();
    Index i_src = Index(nL) - 1;
    for (Index i = 0; i < Index(nL); ++i)
        if (z_src_ >= z_interface_[i] - 1e-15 && z_src_ <= z_interface_[i + 1] + 1e-15) { i_src = i; break; }
    return k_z(i_src, k_rho);
}

SpectralKernel SpectralGreensFunction::operator()(Complex k_rho) const {
    SpectralKernel out;
    const Size nL = medium_.layers.size();

    auto layer_of = [&](Real z) -> Index {
        for (Index i = 0; i < Index(nL); ++i)
            if (z >= z_interface_[i] - 1e-15 && z <= z_interface_[i + 1] + 1e-15) return i;
        return z < z_interface_[0] ? 0 : Index(nL) - 1;
    };
    const Index i_src = layer_of(z_src_);
    const Index i_obs = layer_of(z_obs_);

    const Complex k_zs = k_z(i_src, k_rho);
    const Real z_top = z_interface_[i_src + 1];
    const Real z_bot = z_interface_[i_src];

    // TE 极化广义反射（G_phi 用）：复用 TM 函数但改极化标志需重构——
    // 此处为简洁，TE 临时取与 TM 相同结构（G_phi 的精确混合留 TODO）。
    const Complex Rup_TM = generalized_refl_up_TM(k_rho);
    const Complex Rdn_TM = generalized_refl_dn_TM(k_rho);

    // —— 矢量位 G_A（TM Hertz 位，源场同层，完整多次反射 4 项分子）——
    //
    // 【修正后的相位约定】
    //   k_z = sqrt(k_i^2 - k_ρ^2)，支点选取 Im(k_z) >= 0（k_ρ>k_i 时 k_z = +j|kz|，纯虚）。
    //   正确的传播核为  j·exp(+j·k_z·d)/(2·k_z)，其 Sommerfeld 逆变换 = exp(-jkR)/(4πR)：
    //     ∫₀^∞ j·e^{+j k_z d}/(2k_z) · J0(k_ρρ) k_ρ dk_ρ = e^{-jkR}/(4πR)，R=√(ρ²+d²)
    //   关键：evanescent 区（k_ρ>k_i）e^{+j k_z d}=e^{-|kz|·d} 衰减，积分收敛。
    //   （旧实现用 e^{-j k_z d}=e^{+|kz|·d} 发散，仅 ε=1 因解析闭式尾精确抵消而看似正确；
    //    ε≠1 抵消不全 → 空域 G_A 符号反、近场发散 → S 参数相位错 + 幅度奇异。）
    //
    //   实现：令 jkz := -j·k_zs，则 exp(-jkz·d) = exp(+j k_zs·d)（衰减）。
    //   最终 G_A 需乘以整体因子 j（来自 j/(2k_z) 中的 j）。
    //
    //   多次反射分子（同层闭式，d≥0 均为到界面/镜像的距离）：
    //     num = e^{+j k_z|Δz|} + R̃_up e^{+j k_z(z_o+z_s 从顶)} + R̃_dn e^{+j k_z(z_o+z_s 从底)}
    //           + R̃_up R̃_dn e^{+j k_z(2h - |Δz|)}
    //     den = 1 - R̃_up R̃_dn e^{+2j k_z h}
    //     G_A = j · num / (2 k_z · den)
    const Real H = z_top - z_bot;
    const Real dz = std::abs(z_obs_ - z_src_);
    const Real z_src_top = z_top - z_src_;
    const Real z_obs_top = z_top - z_obs_;
    const Real z_src_bot = z_src_ - z_bot;
    const Real z_obs_bot = z_obs_ - z_bot;
    // jkz = -j·k_zs：使 exp(-jkz·d) = exp(+j·k_zs·d)（evanescent 区衰减）。
    const Complex jkz = -Iunit * k_zs;
    // 数值稳定化：修正后 e^{+j k_z·2H} = e^{-2|kz|·H}（kρ>k_i 时衰减），
    // 故 |round_trip| ≤ |Ru·Rd| ≤ 1，常规路径不再溢出。保留主项提取作为
    // 极端情形（含损介质 |Ru·Rd| 略 > 1）的兜底，逻辑不变。
    const Complex e_dz     = std::exp(-jkz * dz);   // = e^{+j k_zs·dz}（衰减）
    const Complex e_2h     = std::exp(-jkz * (2.0 * H));  // = e^{+j k_zs·2H}（衰减）
    const Complex round_trip = Rup_TM * Rdn_TM * e_2h;
    const Real rt_mag = std::abs(round_trip);

    Complex GA_val;
    if (rt_mag < 1e6) {
        // 常规计算（不溢出）
        const Complex direct   = e_dz;
        const Complex up_refl  = Rup_TM * std::exp(-jkz * (z_src_top + z_obs_top));
        const Complex dn_refl  = Rdn_TM * std::exp(-jkz * (z_src_bot + z_obs_bot));
        const Complex cross    = Rup_TM * Rdn_TM * std::exp(-jkz * (2.0 * H - dz));
        const Complex denom = Complex(1, 0) - round_trip;
        GA_val = (direct + up_refl + dn_refl + cross) / ((2.0 * k_zs) * denom);
    } else {
        // 主项提取：除以 round_trip 避免 inf/inf。逐项除以 RT（代数精确）。
        //   direct/RT = e^{-jkz·dz}/(Ru·Rd·e^{-jkz·2H}) = e^{jkz(2H-dz)}/(Ru·Rd)   —— 仍可能大？
        //   但 RT 大意味着 e^{-jkz·2H} 大（kρ>k0），direct=e^{-jkz·dz}=1（dz=0），
        //   故 direct/RT = 1/(Ru·Rd·e^{-jkz·2H}) → 趋 0。正确。
        //   cross/RT = (Ru·Rd·e^{-jkz(2H-dz)})/(Ru·Rd·e^{-jkz·2H}) = e^{jkz·dz}
        //   dn/RT = Rdn·e^{-jkz·(zs+zo)}/(Ru·Rd·e^{-jkz·2H}) = e^{jkz(2H-zs-zo)}/Ru
        //   up/RT = Ru·e^{-jkz·(zt_s+zt_o)}/(Ru·Rd·e^{-jkz·2H}) = e^{jkz(2H-zt_s-zt_o)}/Rd
        //   denom/RT = 1/RT - 1 ≈ -1（因 1/RT→0）
        //   所有项除以 RT 后指数部分 e^{jkz·(正)} 可能仍大 → 需进一步检查。
        // 实际上当 kρ>k0, kz=jkρ, e^{jkz·x}=e^{-kρ·x} → 趋 0（x>0）。
        //   cross/RT = e^{jkz·dz}=e^{-kρ·dz}，dz≥0 → ≤1（有限）✓
        //   dn/RT 的指数 e^{jkz(2H-zs-zo)}，2H-zs-zo=2h-h-h=0 → e^0=1（有限）✓
        //   up/RT 同理 → e^0/...（有限）✓
        //   direct/RT = e^{jkz(2H-dz)}/(RuRd)，2H-dz=2h-0=2h>0 → e^{-2hkρ}→0 ✓
        //   故 num/RT = cross/RT + dn/RT + up/RT + 0（有限），den/RT=-1。
        Complex cross_over_rt = std::exp(jkz * dz);                              // e^{jkz·dz}
        Complex dn_over_rt = (Rdn_TM != Complex(0,0))
            ? std::exp(jkz * (2.0*H - z_src_bot - z_obs_bot)) / Rup_TM : Complex(0,0);
        Complex up_over_rt = (Rdn_TM != Complex(0,0))
            ? std::exp(jkz * (2.0*H - z_src_top - z_obs_top)) / Rdn_TM : Complex(0,0);
        // direct/RT → 0（忽略）
        Complex num_over_rt = cross_over_rt + dn_over_rt + up_over_rt;
        GA_val = num_over_rt / (2.0 * k_zs * Complex(-1, 0));   // den/RT ≈ -1
    }
    // 整体因子 j（来自正确核 j/(2k_z)，见上方约定注释）。
    out.G_A = Iunit * GA_val;

    // —— 垂直矢量位 G_Azz（z-z 分量）——
    //   对同层情况（z_src 和 z_obs 在同一介质层），G_Azz = G_A。
    //   这是因为水平电流和垂直电流在同层、同 z 时经历相同的介质环境。
    //   跨层（z_src ≠ z_obs 层）时 G_Azz 需要独立的 TM 电压 TLGF，
    //   但当前实现仅支持同层，故 G_Azz = G_A。
    out.G_Azz = out.G_A;

    // —— 水平-垂直交叉耦合 G_Axz（x-z 分量）——
    //   Michalski-Mosig Formulation C 的并矢有非对角项 G_Axz = G_Azx。
    //   谱域核（同层闭式）：直接项和交叉项为零，只有上/下反射差：
    //     G̃_Axz = j·k_ρ/(2·k_z²) · [R̃_up·e^{jkz(2z_top-z_s-z_o)}
    //                                 - R̃_dn·e^{jkz(z_s+z_o-2z_bot)}] / den
    //   物理含义：水平电流源产生的垂直电场分量（或反之），由上下界面不对称引起。
    //   对开放单层（仅底部 ground）：只有下反射项 → G_Axz ≠ 0（不对称）。
    //   对对称腔体（上下 PEC）：上反射 = -下反射 → G_Axz = 0（对称抵消）。
    //   这是 via-trace 连接处垂直电流→水平传播的关键耦合机制。
    {
        const Complex e_up   = std::exp(-jkz * (z_src_top + z_obs_top));   // 到上界面往返
        const Complex e_dn   = std::exp(-jkz * (z_src_bot + z_obs_bot));   // 到下界面往返
        const Complex num_xz = Rup_TM * e_up - Rdn_TM * e_dn;
        // k_ρ 因子 + 1/k_z² 系数（与 G_A 的 1/k_z 不同）
        // G_Axz = j · k_ρ · num_xz / (2 · k_z² · den)
        // 用 GA_val（= num/(2k_z·den)）表示：G_Axz = GA_val · k_ρ/k_z · (num_xz/num)
        // 但 num_xz/num 难直接算。直接计算更清晰：
        const Complex k_rho_c = k_rho;
        const Complex denom_xz = (2.0 * k_zs * k_zs) * (Complex(1, 0) - round_trip);
        Complex GAxz_val;
        if (rt_mag < 1e6) {
            GAxz_val = k_rho_c * num_xz / denom_xz;
        } else {
            // 主项提取（与 GA_val 相同策略）
            Complex num_xz_over_rt = (Rup_TM * e_up - Rdn_TM * e_dn) / round_trip;
            GAxz_val = k_rho_c * num_xz_over_rt / (2.0 * k_zs * k_zs * Complex(-1, 0));
        }
        out.G_Axz = Iunit * GAxz_val;
    }

    // —— 标量势 G_q（Formulation C，Michalski-Mosig eq.50）——
    //   电荷的 PEC 镜像反号（与电流不同）。
    //   【修复】之前 Rup_phi = Rup_TM（+1，电流约定）对 PEC 封闭是错误的——
    //   电荷镜像应反号（-1）。对称腔体中 +1 和 -1 部分抵消 → 电容偏低 5x。
    //
    //   电荷（G_phi）用 TE 极化的广义反射：PEC 封闭时返回 -1（电荷镜像反号），
    //   开放顶部时返回 TE Fresnel（与 TM 略有差异，但实测对 ADS 更准确）。
    //   这与底部 Rdn_phi(TM, pec_positive=false) 的 -1 约定一致。
    const Complex Rup_phi = generalized_refl_up_TE(k_rho);
    const Complex Rdn_phi = generalized_refl_dn_polar(k_rho, /*TM=*/true, /*pec_positive=*/false);
    const Complex round_trip_phi = Rup_phi * Rdn_phi * e_2h;
    const Real rt_phi_mag = std::abs(round_trip_phi);

    Complex Gphi_val;
    if (rt_phi_mag < 1e6) {
        const Complex direct   = e_dz;
        const Complex up_refl_phi  = Rup_phi * std::exp(-jkz * (z_src_top + z_obs_top));
        const Complex dn_refl_phi  = Rdn_phi * std::exp(-jkz * (z_src_bot + z_obs_bot));
        const Complex cross_phi    = Rup_phi * Rdn_phi * std::exp(-jkz * (2.0 * H - dz));
        const Complex denom_phi = Complex(1, 0) - round_trip_phi;
        Gphi_val = (direct + up_refl_phi + dn_refl_phi + cross_phi) / ((2.0 * k_zs) * denom_phi);
    } else {
        // 主项提取（同 G_A，但用 Rup_phi/Rdn_phi）
        Complex cross_over_rt = std::exp(jkz * dz);
        Complex dn_over_rt = (Rdn_phi != Complex(0,0))
            ? std::exp(jkz * (2.0*H - z_src_bot - z_obs_bot)) / Rup_phi : Complex(0,0);
        Complex up_over_rt = (Rdn_phi != Complex(0,0))
            ? std::exp(jkz * (2.0*H - z_src_top - z_obs_top)) / Rdn_phi : Complex(0,0);
        Complex num_over_rt = cross_over_rt + dn_over_rt + up_over_rt;
        Gphi_val = num_over_rt / (2.0 * k_zs * Complex(-1, 0));
    }
    // 1/ε_source 因子（源层复介电常数）+ 整体因子 j（同 G_A）。
    Complex eps_src(medium_.layers[i_src].eps_r, -medium_.layers[i_src].tand);
    out.G_phi = Iunit * Gphi_val / eps_src;

    return out;
}

} // namespace mom::green::spectral
