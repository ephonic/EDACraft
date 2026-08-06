#pragma once

#include "math_types.h"
#include <vector>
#include <array>
#include <map>
#include <cstddef>

namespace tcad {

// Mesh node: 3D position + region ID
struct MeshNode {
    real_t x, y, z;
    int region;     // material/region index (0=Si, 1=oxide, etc.)
    int contact;    // contact ID (-1 = interior, 0+ = contact)
};

// Mesh edge: connects two nodes
struct MeshEdge {
    size_t n0, n1;      // node indices
    real_t length;       // |n1 - n0|
    real_t nx, ny, nz;   // unit vector n0→n1
};

// Mesh face (2D: line segment, 3D: triangle)
// Used for contact definition and surface BCs
struct MeshFace {
    std::vector<size_t> nodes;  // node indices
    int contact;                // contact ID (-1 = interior face)
    real_t area;                // face area (length for 2D)
    real_t nx, ny, nz;          // outward normal
};

// Abstract mesh interface
class Mesh {
public:
    virtual ~Mesh() = default;
    virtual size_t npts() const = 0;
    virtual size_t nedges() const = 0;
    virtual size_t nfaces() const = 0;

    // Node access
    virtual real_t node_x(size_t i) const = 0;
    virtual real_t node_y(size_t i) const = 0;
    virtual real_t node_z(size_t i) const = 0;
    virtual int node_region(size_t i) const = 0;

    // Edge access
    virtual size_t edge_n0(size_t e) const = 0;
    virtual size_t edge_n1(size_t e) const = 0;
    virtual real_t edge_length(size_t e) const = 0;

    // Face access
    virtual int face_contact(size_t f) const = 0;
    virtual real_t face_area(size_t f) const = 0;

    // Neighbor list: for each node, list of (neighbor_node, edge_index)
    virtual const std::vector<std::pair<size_t, size_t>>& neighbors(size_t i) const = 0;

    // Permittivity at node
    virtual real_t eps(size_t i) const = 0;
};

} // namespace tcad
