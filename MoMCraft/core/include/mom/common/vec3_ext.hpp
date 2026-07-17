// =====================================================================
// mom/common/vec3_ext.hpp —— Vec3 扩展操作（RWG/3D 网格用）
//
// 不修改 vec3.hpp（避免影响已有代码），在此新增 cross/normalized/*=。
// =====================================================================
#pragma once

#include "mom/common/vec3.hpp"
#include <cmath>

namespace mom {

// 叉积（三角形法向/面积计算用）
inline Vec3 cross(const Vec3& a, const Vec3& b) {
    return Vec3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    );
}

// 单位化
inline Vec3 normalized(const Vec3& v) {
    Real n = norm(v);
    return (n > 1e-30) ? Vec3(v.x / n, v.y / n, v.z / n) : Vec3(0, 0, 0);
}

// 标量自乘
inline Vec3& operator*=(Vec3& v, Real s) {
    v.x *= s; v.y *= s; v.z *= s;
    return v;
}

// 标量除法
inline Vec3 operator/(const Vec3& v, Real s) {
    return Vec3(v.x / s, v.y / s, v.z / s);
}

} // namespace mom
