// =====================================================================
// mom/common/vec3.hpp —— 三维向量（实/复）小工具
// 仅作几何与格林函数点积使用；线性代数大规模运算走 Eigen。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include <cmath>

namespace mom {

// 实三维点
struct Vec3 {
    Real x{0.0}, y{0.0}, z{0.0};

    Vec3() = default;
    Vec3(Real x_, Real y_, Real z_) : x(x_), y(y_), z(z_) {}

    Vec3 operator+(const Vec3& o) const { return {x + o.x, y + o.y, z + o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x - o.x, y - o.y, z - o.z}; }
    Vec3 operator*(Real s)        const { return {x * s, y * s, z * s}; }
    Vec3& operator+=(const Vec3& o) { x += o.x; y += o.y; z += o.z; return *this; }
    Vec3& operator-=(const Vec3& o) { x -= o.x; y -= o.y; z -= o.z; return *this; }
};

inline Real dot(const Vec3& a, const Vec3& b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}
inline Real norm(const Vec3& a) { return std::sqrt(dot(a, a)); }
inline Real dist(const Vec3& a, const Vec3& b) { return norm(a - b); }
inline Vec3 operator*(Real s, const Vec3& v) { return v * s; }

} // namespace mom
